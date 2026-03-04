#!/usr/bin/env python3
"""
reply-auto-handler.py — Procesa respuestas de prospectos automáticamente

Escanea inbox de katia@ezcontact.mx, detecta respuestas a outreach,
las categoriza y ejecuta acciones:

  NOT_INTERESTED / UNSUBSCRIBE → agrega a blacklist (already-sent.json)
  INTERESTED / QUESTION        → genera alerta + draft de respuesta
  DEMO_REQUEST                 → alerta prioritaria para Vicci

Uso:
    python3 scripts/reply-auto-handler.py           # modo normal
    python3 scripts/reply-auto-handler.py --dry-run # sin escribir nada
    python3 scripts/reply-auto-handler.py --limit 30 # revisa últimos N emails
"""

import subprocess
import json
import os
import re
import argparse
from datetime import datetime
from zoneinfo import ZoneInfo

# ─── Config ──────────────────────────────────────────────────────────────────
CDMX = ZoneInfo('America/Mexico_City')
TODAY = datetime.now(CDMX).strftime('%Y-%m-%d')

ALREADY_SENT_FILE   = '/home/ubuntu/clawd/memory/already-sent.json'
ALERTS_FILE         = '/home/ubuntu/clawd/memory/prospect-alerts.md'
HANDLED_FILE        = '/home/ubuntu/clawd/memory/handled-replies.json'
LOG_FILE            = f'/home/ubuntu/clawd/memory/{TODAY}.md'
PROSPECTOS_DIR      = '/home/ubuntu/clawd/prospectos'

# Emails propios (no son respuestas de prospectos)
INTERNAL_EMAILS = {
    'katia@ezcontact.mx', 'victor@ezcontact.mx',
    'victor.arredondo.ambriz@gmail.com', 'n4m4ster@gmail.com',
}

# Dominios de spam/notificaciones (ignorar)
IGNORE_DOMAINS = {
    'linkedin.com', 'gmail.com', 'google.com', 'amazon.com.mx',
    'amazon.com', 'facebook.com', 'instagram.com', 'twitter.com',
    'noreply', 'no-reply', 'mailer-daemon', 'smartfit.com',
    'elevenlabs.io', 'hsbc.com', 'sentry.io', 'wixpress.com',
}

# ─── Clasificación de respuestas ─────────────────────────────────────────────

# NOT INTERESTED — rechazos claros
NOT_INTERESTED_PATTERNS = [
    r'\bno (estamos|estoy|me) interesad[oa]s?\b',
    r'\bno (nos|me) interesa\b',
    r'\bno (es de nuestro|es de mi) inter[eé]s\b',
    r'\bno (requerimos|necesitamos|contamos con)\b',
    r'\bno (queremos|quiero) m[aá]s informaci[oó]n\b',
    r'\bgracias,?\s*(pero\s*)?no\b',
    r'\bno gracias\b',
    r'\bpor favor (no|remov|elimina|baja|quita)\b',
    r'\b(por favor\s+)?d[eé]jenos\s*(de\s+)?contactar\b',
    r'\bno tenemos presupuesto\b',
    r'\bno (es el|este es el) momento\b',
    r'\btrabajamos con otro\b',
    r'\bya (contamos|tenemos) con\b',
]

# UNSUBSCRIBE — piden no contactar
UNSUBSCRIBE_PATTERNS = [
    r'\b(por favor\s+)?(remov[ae]|eliminame|baja|quita|d[eé]ja de|deja de|stop|unsub)\b',
    r'\bno me cont[ae]ct[eé]s?\b',
    r'\bno me mand[eé]s?\b',
    r'\bremove\s+(me|us)\s+from\b',
    r'\bunsubscribe\b',
    r'\blista negra\b',
    r'\bspam\b',
]

# INTERESTED — respuestas positivas
INTERESTED_PATTERNS = [
    r'\bme interesa\b',
    r'\bsí (me|nos) interesa\b',
    r'\bquisiera (saber|conocer|ver)\b',
    r'\b(pod[eé]mos|podr[ií]an)\s+(ver|hablar|platicar|agendar|coordinar)\b',
    r'\bcu[aá]ndo (pod[eé]mos|podr[ií]amos)\b',
    r'\bme gustar[ií]a\b',
    r'\bpor favor\s+(env[ií]a|manda|comp[ae]rt)\b',
    r'\bquiero\s+(ver|conocer|saber|una demo)\b',
    r'\b(podemos|pueden)\s+hablar\b',
]

# DEMO / MEETING request
DEMO_PATTERNS = [
    r'\b(agendar|agen[dt]emos|programar|coordinar)\s+(una\s+)?(?:reuni[oó]n|llamada|demo|cita|videollamada)\b',
    r'\b(?:una\s+)?demo\s+(?:por\s+favor|con\s+gusto|sí)\b',
    r'\bquiero\s+ver\s+(c[oó]mo\s+funciona|la\s+demo|el\s+sistema)\b',
    r'\bcuando\s+(tengan|tengas|puedan|puedas)\s+disponibilidad\b',
    r'\b(disponible|disponibilidad)\s+para\s+(una\s+)?(llamada|reuni[oó]n|demo)\b',
    r'\b\d{1,2}\s*(am|pm|:00)\b',   # menciona una hora
    r'\bmartes|mi[eé]rcoles|jueves|viernes|lunes\b',  # menciona día
]

# QUESTION — preguntas sobre el servicio
QUESTION_PATTERNS = [
    r'\bcu[aá]nto\s+(cuesta|cobran|es el precio)\b',
    r'\bqu[eé]\s+(include|incluye|ofrecen|hacen)\b',
    r'\bm[aá]s\s+informaci[oó]n\b',
    r'\bc[oó]mo\s+(funciona|trabajan|opera)\b',
    r'\bpueden\s+(enviar|mandar)\s+(informaci[oó]n|precios|cotizaci[oó]n)\b',
    r'\bpara\s+(qu[eé]\s+(vertical|industria|tipo)|cu[aá]ntas\s+empresas)\b',
    r'\btienen\s+(planes|precios|paquetes)\b',
]


def extract_reply_only(body: str) -> str:
    """
    Extrae solo la parte nueva del reply, eliminando el email original citado.
    Corta en: '-----', '________________________________', 'De:', 'From:',
    '> ', líneas que empiezan con >, '--- Original Message ---'
    """
    # Separadores comunes de email clients
    cut_patterns = [
        r'\n-{3,}',                           # --- o más guiones
        r'\n_{3,}',                           # ___ o más guiones bajos
        r'\nDe:\s',                           # Outlook en español
        r'\nFrom:\s',                         # Outlook en inglés
        r'\nOn .+ wrote:',                    # Gmail en inglés
        r'\nEl .+ escribió:',                 # Gmail en español
        r'\n>+\s',                            # Quoted lines
        r'\n-----Mensaje original-----',      # Outlook MX
        r'\n---Original Message---',
        r'\nEnviado el:',                     # Outlook reply header
        r'\nSent:',
    ]
    result = body
    for pat in cut_patterns:
        match = re.search(pat, result)
        if match:
            result = result[:match.start()]
    return result.strip()


def classify_reply(body: str) -> str:
    """Clasifica el cuerpo del email. Retorna: unsubscribe|not_interested|demo|interested|question|unknown"""
    # Solo analizar la parte nueva del reply, no el email original citado
    text = extract_reply_only(body).lower()

    for p in UNSUBSCRIBE_PATTERNS:
        if re.search(p, text, re.IGNORECASE):
            return 'unsubscribe'

    for p in NOT_INTERESTED_PATTERNS:
        if re.search(p, text, re.IGNORECASE):
            return 'not_interested'

    for p in DEMO_PATTERNS:
        if re.search(p, text, re.IGNORECASE):
            return 'demo'

    for p in INTERESTED_PATTERNS:
        if re.search(p, text, re.IGNORECASE):
            return 'interested'

    for p in QUESTION_PATTERNS:
        if re.search(p, text, re.IGNORECASE):
            return 'question'

    return 'unknown'


def should_ignore(sender_addr: str) -> bool:
    """True si el remitente debe ignorarse."""
    if not sender_addr:
        return True
    addr = sender_addr.lower()
    if addr in INTERNAL_EMAILS:
        return True
    domain = addr.split('@')[-1] if '@' in addr else addr
    for ig in IGNORE_DOMAINS:
        if ig in domain:
            return True
    return False


# ─── Draft replies ────────────────────────────────────────────────────────────

def draft_interested(sender_name: str, business: str) -> str:
    name = sender_name or 'estimado'
    biz  = business or 'su negocio'
    return f"""Hola {name},

¡Gracias por responder! Con gusto les mostramos EZContact aplicado a {biz}.

La demo es de 15 minutos y puede agendarse aquí:
https://calendly.com/ezcontact/demo

¿Les funciona esta semana?

Saludos,
Katia"""


def draft_demo_confirm(sender_name: str) -> str:
    name = sender_name or 'estimado'
    return f"""Hola {name},

Perfecto, confirmado.

Les comparto el link para agendar directamente en el horario que mejor les funcione:
https://calendly.com/ezcontact/demo

Cualquier duda estoy aquí.

Saludos,
Katia"""


def draft_question(sender_name: str) -> str:
    name = sender_name or 'estimado'
    return f"""Hola {name},

Con gusto les cuento más.

EZContact es una plataforma de IA para WhatsApp Business que automatiza respuestas, califica prospectos y agenda citas. Los planes arrancan desde $990 MXN/mes.

La forma más rápida de ver si aplica para su negocio es una demo de 15 minutos:
https://calendly.com/ezcontact/demo

¿Les funciona esta semana?

Saludos,
Katia"""


# ─── I/O helpers ─────────────────────────────────────────────────────────────

def load_already_sent() -> set:
    if not os.path.exists(ALREADY_SENT_FILE):
        return set()
    try:
        return set(json.load(open(ALREADY_SENT_FILE)).get('emails', []))
    except Exception:
        return set()


def save_already_sent(sent_set: set):
    try:
        with open(ALREADY_SENT_FILE, 'w') as f:
            json.dump({
                'emails': sorted(list(sent_set)),
                'last_updated': TODAY,
            }, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f'  ⚠️  No pude guardar already-sent: {e}')


def load_handled() -> dict:
    """Dict: msg_id → {category, handled_at}"""
    if not os.path.exists(HANDLED_FILE):
        return {}
    try:
        return json.load(open(HANDLED_FILE))
    except Exception:
        return {}


def save_handled(handled: dict):
    try:
        with open(HANDLED_FILE, 'w') as f:
            json.dump(handled, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f'  ⚠️  No pude guardar handled-replies: {e}')


def run_himalaya_list(page_size: int = 50) -> list:
    r = subprocess.run(
        ['himalaya', 'envelope', 'list', '-a', 'katia', '-o', 'json',
         '-s', str(page_size)],
        capture_output=True, text=True, timeout=20
    )
    if r.returncode == 0 and r.stdout.strip():
        try:
            return json.loads(r.stdout)
        except Exception:
            return []
    return []


def run_himalaya_read(msg_id: str) -> str:
    r = subprocess.run(
        ['himalaya', 'message', 'read', '-a', 'katia', '-o', 'json', str(msg_id)],
        capture_output=True, text=True, timeout=15
    )
    if r.returncode == 0 and r.stdout.strip():
        try:
            body = json.loads(r.stdout)
            if isinstance(body, str):
                return body
        except Exception:
            return r.stdout
    return ''


def extract_sender_name(from_field: dict) -> str:
    name = from_field.get('name', '') or ''
    # Si tiene nombre real (no solo email), usar primer nombre
    if name and '@' not in name:
        parts = name.strip().split()
        if parts:
            return parts[0].title()
    # Derivar del local part pero solo si no es genérico
    addr = from_field.get('addr', '') or ''
    local = addr.split('@')[0] if '@' in addr else ''
    generic = {'hola', 'info', 'contacto', 'ventas', 'admin', 'administracion',
               'hello', 'contact', 'mail', 'soporte', 'support', 'noreply'}
    if local and local.lower() not in generic:
        return local.replace('.', ' ').replace('_', ' ').title()
    # Derivar del dominio como último recurso
    domain = addr.split('@')[-1] if '@' in addr else ''
    biz = re.sub(r'\.(com\.mx|com|mx|edu\.mx|net\.mx)$', '', domain)
    return biz.replace('-', ' ').title() if biz else 'estimado equipo'


def append_to_log(text: str):
    with open(LOG_FILE, 'a') as f:
        f.write(f'\n{text}\n')


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='Procesa respuestas de prospectos')
    parser.add_argument('--dry-run', action='store_true', help='Sin escribir nada')
    parser.add_argument('--limit',   type=int, default=50, help='Emails a revisar')
    args = parser.parse_args()

    print(f'\n{"="*55}')
    print(f'  Reply Auto-Handler — {TODAY}')
    print(f'  Dry-run: {args.dry_run} | Limit: {args.limit}')
    print(f'{"="*55}\n')

    envelopes = run_himalaya_list(page_size=args.limit)
    if not envelopes:
        print('⚠️  No se pudieron listar emails.')
        return

    already_sent = load_already_sent()
    handled      = load_handled()

    alerts     = []
    blacklisted = []
    stats = {'not_interested': 0, 'unsubscribe': 0, 'interested': 0,
             'demo': 0, 'question': 0, 'unknown': 0, 'skipped': 0}

    for env in envelopes:
        msg_id = str(env.get('id', ''))
        if not msg_id:
            continue

        # Ya procesado antes
        if msg_id in handled:
            stats['skipped'] += 1
            continue

        from_field = env.get('from') or {}
        sender_addr = (from_field.get('addr') or '').lower().strip()
        subject = env.get('subject', '') or ''

        # Ignorar internos/spam
        if should_ignore(sender_addr):
            handled[msg_id] = {'category': 'ignored', 'handled_at': TODAY}
            continue

        # Leer cuerpo
        body = run_himalaya_read(msg_id)
        if not body:
            continue

        category = classify_reply(body)
        stats[category] = stats.get(category, 0) + 1

        sender_name  = extract_sender_name(from_field)
        # Intentar extraer nombre del negocio del dominio
        domain = sender_addr.split('@')[-1] if '@' in sender_addr else ''
        biz_name = re.sub(r'\.(com\.mx|com|mx|edu\.mx)$', '', domain).replace('-', ' ').title()

        print(f'  [{msg_id}] {sender_addr:<38} → {category.upper()}')

        if category in ('not_interested', 'unsubscribe'):
            # Agregar a blacklist
            already_sent.add(sender_addr)
            # También agregar el dominio entero si es un rechazo de empresa
            blacklisted.append(sender_addr)
            if not args.dry_run:
                save_already_sent(already_sent)

        elif category in ('interested', 'demo', 'question'):
            # Generar draft
            if category == 'demo':
                draft = draft_demo_confirm(sender_name)
            elif category == 'interested':
                draft = draft_interested(sender_name, biz_name)
            else:  # question
                draft = draft_question(sender_name)

            alerts.append({
                'priority': '🔴' if category == 'demo' else '🟡',
                'category': category,
                'msg_id':   msg_id,
                'sender':   sender_addr,
                'name':     sender_name,
                'subject':  subject,
                'draft':    draft,
            })

        # Marcar como procesado
        handled[msg_id] = {'category': category, 'handled_at': TODAY}

    if not args.dry_run:
        save_handled(handled)

    # ─── Escribir alerts ─────────────────────────────────────────────────────
    print(f'\n📊 Resumen:')
    for k, v in stats.items():
        if v > 0:
            print(f'   {k}: {v}')

    if blacklisted:
        print(f'\n🚫 Blacklisted ({len(blacklisted)}):')
        for e in blacklisted:
            print(f'   {e}')

    if alerts:
        print(f'\n🚨 Alertas ({len(alerts)}):')
        for a in alerts:
            print(f'\n  {a["priority"]} [{a["category"].upper()}] {a["sender"]}')
            print(f'     Subject: {a["subject"]}')
            print(f'     Draft:\n{a["draft"]}')

        if not args.dry_run:
            # Escribir/actualizar alerts file
            ts = datetime.now(CDMX).strftime('%Y-%m-%d %H:%M CDMX')
            lines = [f'# Prospect Alerts — {ts}\n\n']
            for a in alerts:
                lines.append(f'## {a["priority"]} {a["category"].upper()} — {a["sender"]}\n')
                lines.append(f'**Subject:** {a["subject"]}\n\n')
                lines.append(f'**Draft reply:**\n```\n{a["draft"]}\n```\n\n---\n\n')
            with open(ALERTS_FILE, 'w') as f:
                f.writelines(lines)
            print(f'\n✅ Alertas guardadas en {ALERTS_FILE}')

            # Log del día
            log_entry = f'\n## Reply Handler {ts}\n'
            log_entry += f'- Procesados: {sum(stats.values())}\n'
            log_entry += f'- Blacklisted: {", ".join(blacklisted) if blacklisted else "ninguno"}\n'
            log_entry += f'- Alertas: {len(alerts)}\n'
            append_to_log(log_entry)

    else:
        print('\n✅ Sin alertas nuevas.')

    print()


if __name__ == '__main__':
    main()
