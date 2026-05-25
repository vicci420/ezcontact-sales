#!/usr/bin/env python3
"""
reply-auto-handler.py — Categoriza respuestas de prospectos automáticamente.

Escanea inbox de katia@ezcontact.mx, clasifica respuestas de prospectos en:
  - not_interested / unsubscribe  → agrega a blacklist, no más follow-up
  - demo / meeting                → genera draft de confirmación
  - interested                    → genera draft de next steps
  - question                      → genera draft de respuesta
  - unclear                       → marcar para revisión manual

Output:
  memory/reply-report-YYYY-MM-DD.md  — reporte del día
  memory/already-sent.json            — blacklist actualizada con rechazos
  memory/handled-replies.json         — IDs procesados (idempotente)

Uso:
    python3 scripts/reply-auto-handler.py
    python3 scripts/reply-auto-handler.py --dry-run
"""

import subprocess
import json
import os
import re
import argparse
from datetime import datetime
from zoneinfo import ZoneInfo

CDMX           = ZoneInfo('America/Mexico_City')
NOW            = datetime.now(CDMX)
TODAY          = NOW.strftime('%Y-%m-%d')

ALREADY_SENT   = '/home/ubuntu/clawd/memory/already-sent.json'
HANDLED_FILE   = '/home/ubuntu/clawd/memory/handled-replies.json'
REPORT_PATH    = f'/home/ubuntu/clawd/memory/reply-report-{TODAY}.md'

# ─── Palabras clave por categoría ─────────────────────────────────────────────

KEYWORDS_NOT_INTERESTED = [
    r'\bno\s+(me\s+interesa|estamos\s+interesados|nos\s+interesa)\b',
    r'\bno\s+interesad[oa]\b',
    r'\bno\s+interest\b',
    r'\bno\s+gracias\b',
    r'\bpor\s+favor\s+(no|remov|quita|elimina)\b',
    r'\bno\s+aplica\b',
    r'\bno\s+es\s+para\s+nosotros\b',
    r'\bgracias?\s+pero\s+no\b',
    r'\bno\s+requeri\b',
    r'\bno\s+necesit\b',
]

KEYWORDS_UNSUBSCRIBE = [
    r'\bno\s+(me\s+)?mand(e|es|en)\b',
    r'\bno\s+moles\b',
    r'\bbajarme\s+de\b',
    r'\bdar\s+de\s+baja\b',
    r'\bunsubscri\b',
    r'\bremov(e|erme|er\s+mi)\b',
    r'\bnot\s+interested\b',
    r'\bstop\b',
    r'\bspam\b',
]

KEYWORDS_DEMO = [
    r'\bdemo\b',
    r'\bllama(da|rnos|rme)?\b',
    r'\breuni[oó]n\b',
    r'\bcita\b',
    r'\bvideollamada\b',
    r'\bcuándo\b.{0,30}(disponible|tiempo|puedes)',
    r'\bhora(rio)?\b',
    r'\bcuándo\b.{0,20}hablamos',
    r'\bmartes\b|\blunes\b|\bmi[eé]rcoles\b|\bjueves\b|\bviernes\b',
    r'\b(10|11|12|1|2|3|4|5)\s*(am|pm)\b',
]

KEYWORDS_INTERESTED = [
    r'\bme\s+interesa\b',
    r'\binteresante\b',
    r'\bquiero\s+(saber|conocer|ver|más)\b',
    r'\bcómo\s+funciona\b',
    r'\bcuánto\s+cuesta\b',
    r'\bprecio\b|\bcosto\b|\btarifa\b',
    r'\binfo(rmación)?\b',
    r'\bmás\s+detalle\b',
    r'\bplatique\b',
    r'\bcuéntame\b',
]

KEYWORDS_QUESTION = [
    r'\?',
    r'\bqué\b.{0,40}\?',
    r'\bcómo\b.{0,40}\?',
    r'\bcuándo\b.{0,40}\?',
    r'\bquién\b.{0,40}\?',
]


# ─── Helpers ──────────────────────────────────────────────────────────────────

def run(cmd: list, timeout=15) -> str:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.stdout
    except Exception:
        return ""


def load_json(path: str, default):
    if not os.path.exists(path):
        return default
    try:
        return json.load(open(path))
    except Exception:
        return default


def save_json(path: str, data):
    with open(path, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def himalaya_list(page_size=50) -> list:
    out = run(['himalaya', 'envelope', 'list', '-a', 'katia', '-o', 'json',
               '-s', str(page_size)])
    try:
        return json.loads(out) if out.strip() else []
    except Exception:
        return []


def himalaya_read(msg_id: str) -> str:
    out = run(['himalaya', 'message', 'read', '-a', 'katia', '-o', 'json',
               str(msg_id)], timeout=20)
    try:
        body = json.loads(out) if out.strip() else ""
        return body if isinstance(body, str) else str(body)
    except Exception:
        return out


def extract_reply_only(body: str) -> str:
    """Extrae solo la parte nueva del reply (antes del separador de cita)."""
    separators = [
        r'\n[-_]{4,}',                     # línea de guiones
        r'\n(De:|From:|En|On).{5,}escribi',  # "De: X escribió"
        r'\n>+\s',                          # quote con >
        r'\nMensaje original',
        r'\nOriginal Message',
    ]
    for sep in separators:
        match = re.search(sep, body, re.IGNORECASE)
        if match:
            body = body[:match.start()]
    return body.strip()


def classify(text: str) -> str:
    """Clasifica el texto de un reply. Prioridad: unsubscribe > not_interested > demo > interested > question > unclear."""
    t = text.lower()

    for pat in KEYWORDS_UNSUBSCRIBE:
        if re.search(pat, t, re.IGNORECASE):
            return 'unsubscribe'

    for pat in KEYWORDS_NOT_INTERESTED:
        if re.search(pat, t, re.IGNORECASE):
            return 'not_interested'

    for pat in KEYWORDS_DEMO:
        if re.search(pat, t, re.IGNORECASE):
            return 'demo'

    for pat in KEYWORDS_INTERESTED:
        if re.search(pat, t, re.IGNORECASE):
            return 'interested'

    for pat in KEYWORDS_QUESTION:
        if re.search(pat, t, re.IGNORECASE):
            return 'question'

    return 'unclear'


def generate_draft(category: str, from_email: str, from_name: str,
                   subject: str, reply_text: str) -> str:
    """Genera un borrador de respuesta según la categoría."""
    name = from_name.split()[0] if from_name else "equipo"

    if category == 'not_interested':
        return f"""Para: {from_email}
Asunto: Re: {subject}

Hola {name},

Gracias por responder y por tomarte el tiempo. Entendido, no hay problema.

Si en el futuro cambia algo o quieren explorar opciones de automatización,
con gusto los apoyo.

¡Éxito en sus proyectos!

--
Katia Lozano
Ejecutiva Comercial | EZContact
📧 katia@ezcontact.mx
📱 wa.me/5215523455698
"""

    if category == 'unsubscribe':
        return f"""Para: {from_email}
Asunto: Re: {subject}

Hola,

Con gusto los retiro de nuestra lista. Disculpen la molestia.

No recibirán más correos de nuestra parte.

--
Katia Lozano
Ejecutiva Comercial | EZContact
📧 katia@ezcontact.mx
"""

    if category == 'demo':
        return f"""Para: {from_email}
Asunto: Re: {subject}

Hola {name},

Perfecto, con mucho gusto.

Aquí está mi agenda para que elijas el horario que mejor les acomode:
👉 https://calendly.com/ezcontact/demo

La llamada dura 15-20 minutos. Les muestro cómo EZContact funciona
aplicado específicamente a su negocio.

Nos vemos pronto,

--
Katia Lozano
Ejecutiva Comercial | EZContact
📧 katia@ezcontact.mx
📱 wa.me/5215523455698
🌐 www.ezcontact.mx
"""

    if category == 'interested':
        return f"""Para: {from_email}
Asunto: Re: {subject}

Hola {name},

Gracias por el interés. Con gusto les cuento más.

EZContact es una plataforma de IA para WhatsApp que permite automatizar
respuestas, calificar prospectos y transferir a agente humano cuando se necesita.
Los planes van desde $1,500 MXN/mes dependiendo del volumen de conversaciones.

¿Les gustaría ver una demo de 15 minutos? Pueden agendar aquí:
👉 https://calendly.com/ezcontact/demo

--
Katia Lozano
Ejecutiva Comercial | EZContact
📧 katia@ezcontact.mx
📱 wa.me/5215523455698
"""

    if category == 'question':
        return f"""Para: {from_email}
Asunto: Re: {subject}

Hola {name},

Con gusto. [RESPUESTA PERSONALIZADA PENDIENTE — revisar pregunta]

⚠️  DRAFT automático — revisar antes de enviar

--
Katia Lozano
Ejecutiva Comercial | EZContact
📧 katia@ezcontact.mx
📱 wa.me/5215523455698
"""

    return ""  # 'unclear' — no auto-draft


# ─── Blacklist helpers ─────────────────────────────────────────────────────────

def add_to_blacklist(email: str, reason: str):
    data = load_json(ALREADY_SENT, {"emails": [], "last_updated": TODAY})
    emails = set(data.get("emails", []))
    emails.add(email.lower().strip())
    data["emails"] = sorted(list(emails))
    data["last_updated"] = TODAY
    data.setdefault("blacklist_log", []).append({
        "email": email, "reason": reason, "date": TODAY
    })
    save_json(ALREADY_SENT, data)


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"  Reply Auto-Handler — {NOW.strftime('%Y-%m-%d %H:%M CDMX')}")
    print(f"  Dry-run: {args.dry_run}")
    print(f"{'='*60}\n")

    handled = set(load_json(HANDLED_FILE, []))
    already_sent_data = load_json(ALREADY_SENT, {"emails": []})
    known_senders = set(already_sent_data.get("emails", []))
    internal = {'katia@ezcontact.mx', 'victor@ezcontact.mx',
                'victor.arredondo.ambriz@gmail.com'}
    junk_domains = {'linkedin.com', 'gmail.com', 'accounts.google.com',
                    'amazon.com', 'notifications-noreply', 'messages-noreply'}

    emails = himalaya_list(page_size=50)
    results = []

    for e in emails:
        msg_id  = str(e.get('id', ''))
        subject = e.get('subject', '')
        from_info = e.get('from', {})
        from_email = from_info.get('addr', '').lower()
        from_name  = from_info.get('name', '')
        is_seen    = 'Seen' in e.get('flags', [])

        if msg_id in handled:
            continue
        if from_email in internal:
            continue
        if any(j in from_email for j in junk_domains):
            continue
        if not from_email or '@' not in from_email:
            continue
        # Solo procesar si el email es reply (tiene "Re:" o "RE:")
        if not re.match(r'^RE?:', subject, re.IGNORECASE):
            continue

        body = himalaya_read(msg_id)
        reply_text = extract_reply_only(body)
        category = classify(reply_text)
        draft = generate_draft(category, from_email, from_name, subject, reply_text)

        result = {
            'id': msg_id,
            'from': from_email,
            'name': from_name,
            'subject': subject,
            'category': category,
            'reply_preview': reply_text[:200],
            'draft': draft,
        }
        results.append(result)

        if not args.dry_run:
            handled.add(msg_id)
            if category in ('not_interested', 'unsubscribe'):
                add_to_blacklist(from_email, category)
                print(f"  🚫 [{msg_id}] {from_email} → {category} (blacklisted)")
            else:
                print(f"  💬 [{msg_id}] {from_email} → {category}")
        else:
            print(f"  [DRY] [{msg_id}] {from_email} → {category}")

    # Guardar handled
    if not args.dry_run:
        save_json(HANDLED_FILE, sorted(list(handled)))

    # Generar reporte
    report_lines = [
        f"# 📨 Reply Auto-Handler — {TODAY}\n",
        f"**Procesados:** {len(results)} replies\n",
        f"**Dry-run:** {args.dry_run}\n\n",
    ]

    by_category = {}
    for r in results:
        by_category.setdefault(r['category'], []).append(r)

    labels = {
        'not_interested': '🚫 No interesados (blacklisted)',
        'unsubscribe':    '🔇 Unsuscribe (blacklisted)',
        'demo':           '📅 Quieren demo',
        'interested':     '🔥 Interesados',
        'question':       '❓ Tienen preguntas',
        'unclear':        '🤷 Sin clasificar',
    }

    for cat, label in labels.items():
        items = by_category.get(cat, [])
        if not items:
            continue
        report_lines.append(f"## {label}\n")
        for r in items:
            report_lines.append(f"### {r['name'] or r['from']} <{r['from']}>\n")
            report_lines.append(f"- **Asunto:** {r['subject']}\n")
            report_lines.append(f"- **Preview:** {r['reply_preview'][:150]}\n")
            if r['draft']:
                report_lines.append(f"\n**Draft respuesta:**\n```\n{r['draft']}\n```\n")
            report_lines.append("\n")

    report_text = "\n".join(report_lines)
    with open(REPORT_PATH, 'w') as f:
        f.write(report_text)

    print(f"\n✅ Reporte guardado: {REPORT_PATH}")
    print(f"   Categorías: { {k: len(v) for k, v in by_category.items()} }")

    # Summary
    n_action = sum(len(by_category.get(c, [])) for c in ('demo', 'interested', 'question'))
    n_blacklist = sum(len(by_category.get(c, [])) for c in ('not_interested', 'unsubscribe'))
    if n_action:
        print(f"\n🔴 {n_action} respuestas necesitan follow-up — revisar {REPORT_PATH}")
    if n_blacklist:
        print(f"🚫 {n_blacklist} emails blacklisted automáticamente")


if __name__ == '__main__':
    main()
