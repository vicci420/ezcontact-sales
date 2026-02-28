#!/usr/bin/env python3
"""
Outreach sender EZContact
Lee los leads del día y envía correos desde katia@ezcontact.mx.
Auto-registra cada envío en memory/already-sent.json para evitar duplicados.

Fixes v2 (2026-02-24):
- MAX_EMAILS_PER_RUN = 60 (evita timeout de cron en 120s)
- sleep reducido a 1.0s (60 emails ≈ 75s vs 150s antes)
- Guarda already_sent cada 10 emails (no perder progreso si hay timeout)
- Busca leads file más reciente si no existe el de hoy
"""

import smtplib
import json
import time
import os
import glob
import subprocess
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from datetime import datetime, date

LOGO_PATH = "/home/ubuntu/clawd/assets/ezcontact-logo-email.jpg"

# Config
SMTP_HOST = "mail.ezcontact.mx"
SMTP_PORT = 587
SMTP_USER = "katia@ezcontact.mx"
ALREADY_SENT_FILE = "/home/ubuntu/clawd/memory/already-sent.json"
PROSPECTOS_DIR = "/home/ubuntu/clawd/prospectos"
MAX_EMAILS_PER_RUN = 60        # Límite por ejecución (cron timeout = 120s)
SLEEP_BETWEEN_EMAILS = 1.0     # Segundos entre emails (60 emails ≈ 75s total)
SAVE_INTERVAL = 10             # Guardar already_sent cada N emails enviados

SUBJECT_DEFAULT = "Pregunta rápida"

EXCLUDE_PATTERNS = [
    '@2x', 'usuario@dominio', 'email@domain', 'ejemplo@',
    'support@schedulista', '20contacto@', 'icono-ml',
    'user@', 'info@domain', 'dominio.com', 'domain.com',
    # Filtrar internacionales (no son prospectos mexicanos)
    '.edu', 'cordonbleu', 'smartfit.com', 'totalplay.com',
    '@remax.', 'australia@', 'paris@', 'london@', 'riyadh@',
    'shanghai@', 'korea@', 'taiwan@', 'malaysia@', 'peru@',
    'saopaulo@', 'ottawa@', 'thailand@', 'istanbul@', 'madrid@',
]

def get_smtp_password():
    try:
        result = subprocess.run(
            ["vault", "get", "email/katia@ezcontact.mx"],
            capture_output=True, text=True, timeout=10
        )
        return result.stdout.strip()
    except Exception as e:
        print(f"Error obteniendo password: {e}")
        return None

def load_already_sent():
    if not os.path.exists(ALREADY_SENT_FILE):
        return set()
    try:
        with open(ALREADY_SENT_FILE) as f:
            data = json.load(f)
        return set(data.get("emails", []))
    except Exception:
        return set()

def save_already_sent(sent_set):
    try:
        with open(ALREADY_SENT_FILE, 'w') as f:
            json.dump({
                "emails": sorted(list(sent_set)),
                "last_updated": datetime.now().strftime('%Y-%m-%d %H:%M')
            }, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Warning: no pude guardar already-sent: {e}")

def find_leads_file():
    """Busca el archivo de leads más reciente (hoy o el más nuevo disponible)."""
    today = date.today().strftime('%Y-%m-%d')
    today_file = f"{PROSPECTOS_DIR}/leads-auto-{today}.json"
    if os.path.exists(today_file):
        return today_file

    # Buscar el más reciente
    files = sorted(glob.glob(f"{PROSPECTOS_DIR}/leads-auto-*.json"), reverse=True)
    if files:
        print(f"No hay leads de hoy, usando más reciente: {os.path.basename(files[0])}")
        return files[0]

    return None

SIGNATURE_HTML = """
<br>
<table cellpadding="0" cellspacing="0" style="border-top:2px solid #1a7fcc;padding-top:12px;margin-top:12px;font-family:Arial,sans-serif;">
  <tr>
    <td style="padding-right:16px;border-right:1px solid #ddd;vertical-align:middle;">
      <img src="cid:ezcontact_logo" alt="EZContact" width="120" style="display:block;">
    </td>
    <td style="padding-left:16px;vertical-align:middle;">
      <div style="font-size:14px;font-weight:bold;color:#1a1a2e;">Katia Lozano</div>
      <div style="font-size:11px;color:#666;margin-bottom:5px;">Ejecutiva Comercial &nbsp;|&nbsp; EZContact</div>
      <div style="font-size:11px;color:#444;">
        ✉&nbsp;<a href="mailto:katia@ezcontact.mx" style="color:#1a7fcc;text-decoration:none;">katia@ezcontact.mx</a>
        &nbsp;&nbsp;📱&nbsp;<a href="https://wa.me/5215523455698" style="color:#1a7fcc;text-decoration:none;">WhatsApp</a>
        &nbsp;&nbsp;🌐&nbsp;<a href="https://www.ezcontact.mx" style="color:#1a7fcc;text-decoration:none;">www.ezcontact.mx</a>
      </div>
    </td>
  </tr>
</table>
"""

SIGNATURE_PLAIN = """\n--\nKatia Lozano\nEjecutiva Comercial | EZContact\nkatia@ezcontact.mx | wa.me/5215523455698 | www.ezcontact.mx"""

def personalized_subject(business_name):
    """Genera subject personalizado si hay nombre de negocio disponible."""
    if business_name and len(business_name.strip()) > 2:
        # Capitalizar correctamente (evitar TODO MAYÚSCULAS del título)
        name = business_name.strip()
        if name.isupper():
            name = name.title()
        return f"Pregunta rápida — {name}"
    return SUBJECT_DEFAULT


def personalized_greeting(business_name):
    """Genera saludo personalizado para el cuerpo del email."""
    if business_name and len(business_name.strip()) > 2:
        name = business_name.strip()
        if name.isupper():
            name = name.title()
        return f"Hola {name},"
    return "Hola,"


def _make_email(plain_body, html_body):
    """Returns (plain, html) tuple with signature appended."""
    plain = plain_body + SIGNATURE_PLAIN
    html = f'''<html><body style="font-family:Arial,sans-serif;font-size:14px;color:#222;line-height:1.7;max-width:560px;">
{html_body}
{SIGNATURE_HTML}</body></html>'''
    return plain, html

def get_email_body(vertical, business_name=""):
    """
    Genera cuerpo del email personalizado por vertical y nombre del negocio.
    El saludo 'Hola,' se reemplaza dinámicamente por el nombre del negocio cuando está disponible.
    Ejemplo: "Hola Ikigai Spa," en lugar de "Hola,"
    """
    greeting = personalized_greeting(business_name)
    v = vertical.lower()

    if any(x in v for x in ['dental', 'derma', 'fisio', 'psico', 'nutri', 'laborat', 'medicina', 'spa', 'clinica', 'salud']):
        plain, html = _make_email(
            """Hola,

La mayoría de clínicas pierde citas porque un prospecto pregunta por WhatsApp... y nadie responde a tiempo.

EZContact atiende esos mensajes por ti: agenda, confirma y da seguimiento — sin que nadie en tu equipo tenga que hacerlo.

¿Vale la pena 10 minutos para verlo?
→ https://calendly.com/ezcontact/demo""",
            "<p>Hola,</p><p>La mayoría de clínicas pierde citas porque un prospecto pregunta por WhatsApp... y nadie responde a tiempo.</p><p><strong>EZContact</strong> atiende esos mensajes por ti: agenda, confirma y da seguimiento — sin que nadie en tu equipo tenga que hacerlo.</p><p>¿Vale la pena 10 minutos para verlo?<br><a href='https://calendly.com/ezcontact/demo' style='color:#1a7fcc;'>→ Ver demo gratuita</a></p>"
        )

    elif any(x in v for x in ['veterinar']):
        plain, html = _make_email(
            """Hola,

Las veterinarias pierden dueños de mascotas que preguntan por WhatsApp pero no reciben respuesta a tiempo.

EZContact atiende esas consultas, agenda citas y da seguimiento — 24/7, sin que nadie en tu clínica tenga que hacerlo.

¿Vale la pena 10 minutos?
→ https://calendly.com/ezcontact/demo""",
            "<p>Hola,</p><p>Las veterinarias pierden dueños de mascotas que preguntan por WhatsApp pero no reciben respuesta a tiempo.</p><p><strong>EZContact</strong> atiende esas consultas, agenda citas y da seguimiento — 24/7, sin que nadie en tu clínica tenga que hacerlo.</p><p>¿Vale la pena 10 minutos?<br><a href='https://calendly.com/ezcontact/demo' style='color:#1a7fcc;'>→ Ver demo gratuita</a></p>"
        )

    elif any(x in v for x in ['yoga', 'pilates', 'gimnasio', 'crossfit', 'fitness', 'natac', 'deport']):
        plain, html = _make_email(
            """Hola,

Los gimnasios reciben más consultas de las que pueden responder. La mayoría no se convierte porque no hay seguimiento.

EZContact responde por WhatsApp, inscribe y da seguimiento automático — sin contratar a nadie más.

¿Vale la pena 10 minutos?
→ https://calendly.com/ezcontact/demo""",
            "<p>Hola,</p><p>Los gimnasios reciben más consultas de las que pueden responder. La mayoría no se convierte porque no hay seguimiento.</p><p><strong>EZContact</strong> responde por WhatsApp, inscribe y da seguimiento automático — sin contratar a nadie más.</p><p>¿Vale la pena 10 minutos?<br><a href='https://calendly.com/ezcontact/demo' style='color:#1a7fcc;'>→ Ver demo gratuita</a></p>"
        )

    elif any(x in v for x in ['escuela', 'idioma', 'colegio', 'cocina', 'guardería', 'kinder', 'educac', 'academ']):
        plain, html = _make_email(
            """Hola,

Los centros educativos pierden hasta 40% de sus prospectos porque no responden a tiempo por WhatsApp.

EZContact resuelve dudas, agenda visitas y da seguimiento automático — para que no se te escape ningún alumno potencial.

¿Vale la pena 10 minutos?
→ https://calendly.com/ezcontact/demo""",
            "<p>Hola,</p><p>Los centros educativos pierden hasta 40% de sus prospectos porque no responden a tiempo por WhatsApp.</p><p><strong>EZContact</strong> resuelve dudas, agenda visitas y da seguimiento automático — para que no se te escape ningún alumno potencial.</p><p>¿Vale la pena 10 minutos?<br><a href='https://calendly.com/ezcontact/demo' style='color:#1a7fcc;'>→ Ver demo gratuita</a></p>"
        )

    elif any(x in v for x in ['inmobiliaria', 'inmueble', 'bienes']):
        plain, html = _make_email(
            """Hola,

Un prospecto inmobiliario que no recibe respuesta en 5 minutos se va con otro agente. Siempre.

EZContact responde al instante por WhatsApp, califica al prospecto y agenda la cita — sin que tú tengas que estar disponible.

¿Vale la pena 10 minutos?
→ https://calendly.com/ezcontact/demo""",
            "<p>Hola,</p><p>Un prospecto inmobiliario que no recibe respuesta en 5 minutos se va con otro agente. Siempre.</p><p><strong>EZContact</strong> responde al instante por WhatsApp, califica al prospecto y agenda la cita — sin que tú tengas que estar disponible.</p><p>¿Vale la pena 10 minutos?<br><a href='https://calendly.com/ezcontact/demo' style='color:#1a7fcc;'>→ Ver demo gratuita</a></p>"
        )

    elif any(x in v for x in ['reclutamiento', 'recursos humanos', 'rrhh']):
        plain, html = _make_email(
            """Hola,

Los candidatos esperan respuesta inmediata. Si no llega en horas, ya aplicaron en otro lado.

EZContact automatiza la comunicación inicial por WhatsApp: confirma interés, filtra y agenda entrevistas — sin carga para tu equipo.

¿Vale la pena 10 minutos?
→ https://calendly.com/ezcontact/demo""",
            "<p>Hola,</p><p>Los candidatos esperan respuesta inmediata. Si no llega en horas, ya aplicaron en otro lado.</p><p><strong>EZContact</strong> automatiza la comunicación inicial por WhatsApp: confirma interés, filtra y agenda entrevistas — sin carga para tu equipo.</p><p>¿Vale la pena 10 minutos?<br><a href='https://calendly.com/ezcontact/demo' style='color:#1a7fcc;'>→ Ver demo gratuita</a></p>"
        )

    elif any(x in v for x in ['restaurante', 'taquería', 'taqueria', 'cafetería', 'cafeteria', 'food', 'catering']):
        plain, html = _make_email(
            """Hola,

Los restaurantes pierden reservaciones y pedidos porque WhatsApp se vuelve caótico en hora pico.

EZContact organiza los mensajes, confirma reservaciones y responde el menú — sin que tu equipo deje de atender mesas.

¿Vale la pena 10 minutos?
→ https://calendly.com/ezcontact/demo""",
            "<p>Hola,</p><p>Los restaurantes pierden reservaciones y pedidos porque WhatsApp se vuelve caótico en hora pico.</p><p><strong>EZContact</strong> organiza los mensajes, confirma reservaciones y responde el menú — sin que tu equipo deje de atender mesas.</p><p>¿Vale la pena 10 minutos?<br><a href='https://calendly.com/ezcontact/demo' style='color:#1a7fcc;'>→ Ver demo gratuita</a></p>"
        )

    else:
        plain, html = _make_email(
            """Hola,

Tu competencia ya perdió clientes hoy porque no respondió a tiempo por WhatsApp.

EZContact atiende, califica y da seguimiento automático — para que ningún mensaje quede sin respuesta.

¿Vale la pena 10 minutos?
→ https://calendly.com/ezcontact/demo""",
            "<p>Hola,</p><p>Tu competencia ya perdió clientes hoy porque no respondió a tiempo por WhatsApp.</p><p><strong>EZContact</strong> atiende, califica y da seguimiento automático — para que ningún mensaje quede sin respuesta.</p><p>¿Vale la pena 10 minutos?<br><a href='https://calendly.com/ezcontact/demo' style='color:#1a7fcc;'>→ Ver demo gratuita</a></p>"
        )

    # Inyectar saludo personalizado (reemplaza "Hola," genérico)
    plain = plain.replace("Hola,", greeting, 1)
    html = html.replace("<p>Hola,</p>", f"<p>{greeting}</p>", 1)

    return plain, html


def main():
    leads_file = find_leads_file()
    if not leads_file:
        print("No hay archivo de leads disponible.")
        return

    print(f"Leads file: {leads_file}")

    with open(leads_file) as f:
        all_leads = json.load(f)

    # Filtrar leads inválidos
    valid_leads = [
        l for l in all_leads
        if not any(x in l.get('email', '') for x in EXCLUDE_PATTERNS)
    ]

    print(f"Leads válidos: {len(valid_leads)} de {len(all_leads)} totales")

    # Obtener password
    password = get_smtp_password()
    if not password:
        print("No se pudo obtener el password SMTP. Abortando.")
        return

    # Cargar ya-enviados
    already_sent = load_already_sent()
    nuevos = [l for l in valid_leads if l['email'] not in already_sent]
    print(f"Ya enviados antes: {len(already_sent)}")
    print(f"Leads nuevos: {len(nuevos)}")

    if not nuevos:
        print("Todos los leads ya fueron enviados anteriormente.")
        return

    # Limitar a MAX_EMAILS_PER_RUN
    batch = nuevos[:MAX_EMAILS_PER_RUN]
    remaining = len(nuevos) - len(batch)
    print(f"Este run: {len(batch)} emails (máximo {MAX_EMAILS_PER_RUN})")
    if remaining > 0:
        print(f"Quedan {remaining} para próximos runs")

    sent = []
    errors = []
    since_last_save = 0

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(SMTP_USER, password)

            for lead in batch:
                email = lead.get('email', '')
                vertical = lead.get('vertical', 'General')
                business_name = lead.get('business_name', '')

                body_plain, body_html = get_email_body(vertical, business_name)
                subject = personalized_subject(business_name)

                # Outer container
                msg = MIMEMultipart('mixed')
                msg['From'] = f"Katia Lozano <{SMTP_USER}>"
                msg['To'] = email
                msg['Cc'] = "victor@ezcontact.mx"
                msg['Subject'] = subject
                msg['Reply-To'] = SMTP_USER

                # multipart/related wraps HTML + inline logo
                msg_related = MIMEMultipart('related')

                # multipart/alternative inside related (plain + html)
                msg_alt = MIMEMultipart('alternative')
                msg_alt.attach(MIMEText(body_plain, 'plain', 'utf-8'))
                msg_alt.attach(MIMEText(body_html, 'html', 'utf-8'))
                msg_related.attach(msg_alt)

                # Inline logo attachment
                try:
                    with open(LOGO_PATH, 'rb') as f:
                        logo_data = f.read()
                    logo_img = MIMEImage(logo_data, _subtype='jpeg')
                    logo_img.add_header('Content-ID', '<ezcontact_logo>')
                    logo_img.add_header('Content-Disposition', 'inline', filename='ezcontact-logo.jpg')
                    msg_related.attach(logo_img)
                except Exception:
                    pass  # If logo fails, email still sends (just without logo)

                msg.attach(msg_related)

                try:
                    server.sendmail(SMTP_USER, [email, "victor@ezcontact.mx"], msg.as_string())
                    sent.append(email)
                    already_sent.add(email)
                    since_last_save += 1
                    name_tag = f" | {business_name}" if business_name else ""
                    print(f"✅ [{vertical}{name_tag}] {email} → subj: {subject}")

                    # Guardar progreso cada SAVE_INTERVAL emails (anti-timeout)
                    if since_last_save >= SAVE_INTERVAL:
                        save_already_sent(already_sent)
                        since_last_save = 0
                        print(f"  💾 Progreso guardado ({len(already_sent)} total en historial)")

                    time.sleep(SLEEP_BETWEEN_EMAILS)

                except Exception as e:
                    errors.append(f"{email}: {e}")
                    print(f"❌ {email}: {e}")

    except Exception as e:
        print(f"Error SMTP: {e}")

    # Guardar historial actualizado (final)
    save_already_sent(already_sent)

    # Log del día
    today = date.today().strftime('%Y-%m-%d')
    log_file = f"/home/ubuntu/clawd/memory/outreach-{today}.json"
    
    # Merge con log existente si ya hubo runs hoy
    existing_sent = []
    existing_errors = []
    if os.path.exists(log_file):
        try:
            with open(log_file) as f:
                existing = json.load(f)
                existing_sent = existing.get("sent", [])
                existing_errors = existing.get("errors", [])
        except Exception:
            pass

    log_data = {
        "date": datetime.now().isoformat(),
        "sent": existing_sent + sent,
        "errors": existing_errors + errors,
        "total_sent_today": len(existing_sent) + len(sent),
        "remaining_leads": remaining
    }
    with open(log_file, 'w') as f:
        json.dump(log_data, f, indent=2, ensure_ascii=False)

    print(f"\n📊 Este run: {len(sent)} enviados, {len(errors)} errores")
    print(f"📁 Log: {log_file}")
    print(f"🔒 Historial total: {len(already_sent)} emails en already-sent.json")
    if remaining > 0:
        print(f"⏭️  {remaining} leads pendientes para próximo run")

if __name__ == "__main__":
    main()
