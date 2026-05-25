#!/usr/bin/env python3
"""
reply-handler.py — Procesa respuestas al outreach de EZContact

Escanea inbox de katia@ezcontact.mx, categoriza respuestas y:
  - NO INTERESADO → agrega a blacklist, sin acción
  - INTERESADO/PREGUNTA → genera draft de respuesta + alerta
  - DESUSCRIPCIÓN → agrega a blacklist, no enviar más

Uso:
    python3 scripts/reply-handler.py            # procesa y reporta
    python3 scripts/reply-handler.py --dry-run  # sin escribir archivos
    python3 scripts/reply-handler.py --limit 20 # procesa X emails

Output:
    memory/reply-report-YYYY-MM-DD.md     — reporte del día
    memory/already-sent.json              — actualizado con blacklist
    memory/reply-drafts-YYYY-MM-DD.md    — borradores de respuesta
"""

import subprocess
import json
import re
import os
import argparse
from datetime import datetime
from zoneinfo import ZoneInfo

# ─── Config ──────────────────────────────────────────────────────────────────
CDMX = ZoneInfo('America/Mexico_City')
TODAY = datetime.now(CDMX).strftime('%Y-%m-%d')

ALREADY_SENT_FILE = '/home/ubuntu/clawd/memory/already-sent.json'
REPORT_FILE       = f'/home/ubuntu/clawd/memory/reply-report-{TODAY}.md'
DRAFTS_FILE       = f'/home/ubuntu/clawd/memory/reply-drafts-{TODAY}.md'
PROCESSED_FILE    = '/home/ubuntu/clawd/memory/processed-replies.json'

KATIA_EMAIL   = 'katia@ezcontact.mx'
VICTOR_EMAIL  = 'victor@ezcontact.mx'
CALENDLY_LINK = 'https://calendly.com/ezcontact/demo'

# Remitentes internos / junk a ignorar
INTERNAL_SENDERS = {
    'katia@ezcontact.mx', 'victor@ezcontact.mx',
    'victor.arredondo.ambriz@gmail.com', 'n4m4ster@gmail.com',
    'victor.arredondo@tecnologiaslozano.com',
}
JUNK_DOMAINS = {
    'linkedin.com', 'google.com', 'accounts.google.com',
    'amazon.com', 'amazon.com.mx', 'sentry.io',
    'calendar.google.com', 'noreply.github.com',
}

# ─── Señales de categorización ────────────────────────────────────────────────
NOT_INTERESTED_SIGNALS = [
    r'\bno (estamos|estoy|me encuentro)? ?interesad[ao]s?\b',
    r'\bno (nos|me) interesa\b',
    r'\bno (estamos|estoy) en posici[oó]n\b',
    r'\bno es algo que busquemos\b',
    r'\bno gracias\b',
    r'\bgracias? (por|pero)\b.*\bno\b',
    r'\bno (nos|les) necesitamos?\b',
    r'\bno (nos|les) aplica\b',
    r'\bnot interested\b',
    r'\bremove me\b',
    r'\bdesuscrib[ei]r?\b',
    r'\bdar de baja\b',
    r'\bno (me|nos) (contacten?|escriban?|manden?)\b',
    r'\bstop\b',
    r'\bunsubscribe\b',
]

INTERESTED_SIGNALS = [
    r'\bme interesa\b',
    r'\bnos interesa\b',
    r'\bquiero (saber|ver|conocer|una demo?)\b',
    r'\bme gustar[ií]a\b',
    r'\bcu[aá]nto cuesta\b',
    r'\bprecios?\b',
    r'\bcuánto vale\b',
    r'\bagend',
    r'\bcita\b',
    r'\bllam[ae]m?os?\b',
    r'\bpodemos (hablar|platicar|reunirnos?)\b',
    r'\b(cuándo|cuando) (podemos|pueden)\b',
    r'\bdemo\b',
    r'\bpresentación\b',
    r'\bcómo funciona\b',
    r'\bqué incluye\b',
    r'\bm[aá]s informaci[oó]n\b',
    r'\bmore info\b',
]

QUESTION_SIGNALS = [
    r'\?',
    r'\bcómo\b',
    r'\bcu[aá]nto\b',
    r'\bqu[eé] (es|hace|incluye|ofrece)\b',
]

# ─── Helpers ─────────────────────────────────────────────────────────────────
def load_already_sent() -> set:
    if not os.path.exists(ALREADY_SENT_FILE):
        return set()
    try:
        return set(json.load(open(ALREADY_SENT_FILE)).get('emails', []))
    except Exception:
        return set()

def save_already_sent(sent_set: set):
    data = {'emails': sorted(list(sent_set)), 'last_updated': TODAY}
    with open(ALREADY_SENT_FILE, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def load_processed() -> set:
    if not os.path.exists(PROCESSED_FILE):
        return set()
    try:
        return set(json.load(open(PROCESSED_FILE)).get('ids', []))
    except Exception:
        return set()

def save_processed(processed: set):
    data = {'ids': sorted(list(processed)), 'last_updated': TODAY}
    with open(PROCESSED_FILE, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def himalaya_list(page_size=50) -> list:
    result = subprocess.run(
        ['himalaya', 'envelope', 'list', '-a', 'katia', '-o', 'json',
         '-s', str(page_size)],
        capture_output=True, text=True, timeout=30
    )
    if result.returncode == 0 and result.stdout.strip():
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            return []
    return []

def himalaya_read(msg_id: str) -> str:
    result = subprocess.run(
        ['himalaya', 'message', 'read', '-a', 'katia', '-o', 'json', str(msg_id)],
        capture_output=True, text=True, timeout=15
    )
    if result.returncode == 0 and result.stdout.strip():
        try:
            return json.loads(result.stdout)
        except Exception:
            return result.stdout
    return ''

def categorize(text: str) -> str:
    """Devuelve: NOT_INTERESTED | INTERESTED | QUESTION | NEUTRAL"""
    text_lower = text.lower()
    
    # Not interested tiene prioridad (evitar falsos positivos)
    for signal in NOT_INTERESTED_SIGNALS:
        if re.search(signal, text_lower):
            return 'NOT_INTERESTED'
    
    for signal in INTERESTED_SIGNALS:
        if re.search(signal, text_lower):
            return 'INTERESTED'
    
    for signal in QUESTION_SIGNALS:
        if re.search(signal, text_lower):
            return 'QUESTION'
    
    return 'NEUTRAL'

def build_draft(category: str, sender_name: str, business_name: str, original_text: str) -> str:
    """Genera borrador de respuesta según categoría."""
    name = sender_name.split()[0] if sender_name else 'Estimado/a'
    biz  = f' de {business_name}' if business_name else ''
    
    if category == 'INTERESTED':
        return f"""Hola {name},

Gracias por responder. Me da mucho gusto que les pueda ser útil.

Para que vea cómo funciona aplicado exactamente a {business_name or 'su negocio'}, le agendo una demo de 15 minutos sin compromiso:

👉 {CALENDLY_LINK}

También podemos coordinarlo por aquí si prefiere. ¿Qué días y horarios le quedan mejor?

Saludos,

--
Katia Lozano
Ejecutiva Comercial | EZContact
📧 katia@ezcontact.mx
📱 wa.me/5215523455698
🌐 www.ezcontact.mx"""

    elif category == 'QUESTION':
        return f"""Hola {name},

Con gusto le explico.

[COMPLETAR: responder la pregunta específica sobre {business_name or 'su negocio'}]

Si quiere verlo en acción, podemos agendar 15 minutos para una demo directa a su caso:
👉 {CALENDLY_LINK}

¿Alguna otra duda?

Saludos,

--
Katia Lozano
Ejecutiva Comercial | EZContact
📧 katia@ezcontact.mx
📱 wa.me/5215523455698
🌐 www.ezcontact.mx"""

    return ''

def is_reply_to_outreach(subject: str) -> bool:
    """Detecta si el email es una respuesta a nuestro outreach."""
    subject_lower = subject.lower()
    outreach_subjects = [
        're: pregunta rápida', 're: automatiza', 're: whatsapp', 
        're: inteligencia artificial', 're: siguientes pasos',
        're: ezcontact', 'r: pregunta rápida',
    ]
    return any(s in subject_lower for s in outreach_subjects)

def is_junk_sender(addr: str) -> bool:
    if not addr:
        return True
    addr_lower = addr.lower()
    if addr_lower in INTERNAL_SENDERS:
        return True
    domain = addr_lower.split('@')[-1] if '@' in addr_lower else ''
    return domain in JUNK_DOMAINS

# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description='Procesa respuestas al outreach EZContact')
    parser.add_argument('--dry-run', action='store_true', help='Sin escribir archivos')
    parser.add_argument('--limit', type=int, default=50, help='Max emails a revisar')
    args = parser.parse_args()

    print(f"\n{'='*55}")
    print(f"  EZContact Reply Handler — {TODAY}")
    print(f"  Dry-run: {args.dry_run}")
    print(f"{'='*55}\n")

    already_sent = load_already_sent()
    processed    = load_processed()

    emails = himalaya_list(page_size=args.limit)
    print(f"📬 Emails en inbox: {len(emails)}\n")

    results = {
        'NOT_INTERESTED': [],
        'INTERESTED':     [],
        'QUESTION':       [],
        'NEUTRAL':        [],
    }

    for envelope in emails:
        msg_id   = str(envelope.get('id', ''))
        subject  = envelope.get('subject', '')
        from_obj = envelope.get('from', {})
        from_addr = from_obj.get('addr', '').lower().strip()
        from_name = from_obj.get('name', '')

        # Ignorar ya procesados
        if msg_id in processed:
            continue

        # Ignorar junk y internos
        if is_junk_sender(from_addr):
            continue

        # Solo procesar respuestas a nuestro outreach
        if not is_reply_to_outreach(subject):
            continue

        # Leer cuerpo del email
        body = himalaya_read(msg_id)
        if not body:
            continue

        # Obtener solo la parte nueva (antes del primer "----" o "De:")
        body_text = body if isinstance(body, str) else str(body)
        # Truncar al primer mensaje original (quitar quoted text)
        for separator in ['________________________________', '-----Mensaje original', '--- On ', '> ']:
            if separator in body_text:
                body_text = body_text.split(separator)[0]

        category = categorize(body_text)
        
        # Extraer nombre del negocio del dominio
        domain = from_addr.split('@')[-1] if '@' in from_addr else ''
        biz_from_domain = re.sub(r'\.(com\.mx|edu\.mx|org\.mx|net\.mx|mx|com)$', '', domain).replace('-', ' ').title()

        result = {
            'id':       msg_id,
            'from':     from_addr,
            'name':     from_name,
            'business': biz_from_domain,
            'subject':  subject,
            'category': category,
            'snippet':  body_text.strip()[:200],
        }

        results[category].append(result)
        processed.add(msg_id)

        status_icon = {'NOT_INTERESTED': '❌', 'INTERESTED': '🔥', 'QUESTION': '❓', 'NEUTRAL': '🔘'}
        print(f"  {status_icon.get(category, '?')} [{category}] {from_addr}")
        print(f"      Subj: {subject}")
        print(f"      → {body_text.strip()[:100]!r}\n")

        # Agregar a blacklist si no interesado/desuscripción
        if category == 'NOT_INTERESTED':
            already_sent.add(from_addr)
            print(f"      → Agregado a blacklist ✓")

    # ─── Guardar ─────────────────────────────────────────────────────────────
    total = sum(len(v) for v in results.values())
    print(f"\n{'='*55}")
    print(f"  Resumen: {total} respuestas procesadas")
    print(f"  🔥 Interesados:     {len(results['INTERESTED'])}")
    print(f"  ❓ Preguntas:       {len(results['QUESTION'])}")
    print(f"  ❌ No interesados:  {len(results['NOT_INTERESTED'])}")
    print(f"  🔘 Neutros:         {len(results['NEUTRAL'])}")
    print(f"{'='*55}\n")

    if not args.dry_run:
        save_already_sent(already_sent)
        save_processed(processed)

        # Escribir reporte
        report_lines = [f"# Reply Report — {TODAY}\n\n"]
        report_lines.append(f"**Total:** {total} respuestas nuevas\n\n")

        for cat, emoji, title in [
            ('INTERESTED', '🔥', 'Interesados — Acción inmediata'),
            ('QUESTION',   '❓', 'Preguntas — Responder hoy'),
            ('NOT_INTERESTED', '❌', 'No interesados — Cerrados'),
            ('NEUTRAL',    '🔘', 'Neutros — Revisar manualmente'),
        ]:
            if results[cat]:
                report_lines.append(f"## {emoji} {title}\n\n")
                for r in results[cat]:
                    report_lines.append(f"- **{r['from']}** ({r['business']})\n")
                    report_lines.append(f"  - Asunto: {r['subject']}\n")
                    report_lines.append(f"  - Snippet: _{r['snippet'][:120]}_\n\n")

        with open(REPORT_FILE, 'w') as f:
            f.writelines(report_lines)

        # Escribir borradores para interesados y preguntas
        if results['INTERESTED'] or results['QUESTION']:
            draft_lines = [f"# Reply Drafts — {TODAY}\n\n",
                           "> Borradores auto-generados. Revisar y personalizar antes de enviar.\n\n"]
            for cat in ['INTERESTED', 'QUESTION']:
                for r in results[cat]:
                    draft = build_draft(cat, r['name'], r['business'], r['snippet'])
                    if draft:
                        draft_lines.append(f"## ↩️ Para: {r['from']} ({r['business']})\n\n")
                        draft_lines.append(f"```\n{draft}\n```\n\n")
            with open(DRAFTS_FILE, 'w') as f:
                f.writelines(draft_lines)
            print(f"✅ Borradores guardados en: {DRAFTS_FILE}")

        print(f"✅ Reporte guardado en: {REPORT_FILE}")

    return total

if __name__ == '__main__':
    main()
