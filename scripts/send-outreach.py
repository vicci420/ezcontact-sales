#!/usr/bin/env python3
"""
send-outreach.py — Envía correos de prospección desde katia@ezcontact.mx
Fuente: leads de /prospectos/leads-auto-*.json y similares
Filtros: solo .mx | no duplicados | max --limit por corrida

Uso:
    python3 send-outreach.py                  # envía hasta 30 hoy
    python3 send-outreach.py --limit 50       # envía hasta 50
    python3 send-outreach.py --dry-run        # simula sin enviar
    python3 send-outreach.py --test you@mx    # prueba a tu correo
"""

import smtplib
import json
import os
import glob
import re
import argparse
import subprocess
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from urllib.parse import urlparse

# ─── Config ──────────────────────────────────────────────────────────────────
SMTP_HOST         = "mail.ezcontact.mx"
SMTP_PORT         = 587
FROM_EMAIL        = "katia@ezcontact.mx"
FROM_NAME         = "Katia Lozano"
CC_EMAIL          = "victor@ezcontact.mx"
ALREADY_SENT_FILE = "/home/ubuntu/clawd/memory/already-sent.json"
PROSPECTOS_DIR    = "/home/ubuntu/clawd/prospectos"
LOG_DIR           = "/home/ubuntu/clawd/prospectos"
DEFAULT_LIMIT     = 30
DELAY_BETWEEN     = 4   # segundos entre envíos

# ─── Plantilla de email ───────────────────────────────────────────────────────
LOGO_URL   = "https://ezcontact.ai/images/logotipo-blanco.png"
BRAND_COLOR = "#1e3a8a"   # azul oscuro EZContact
LINK_COLOR  = "#2563eb"   # azul link

SIGNATURE_HTML = f"""
<br>
<table cellpadding="0" cellspacing="0" style="width:100%;max-width:560px;margin-top:16px;font-family:Arial,sans-serif;">
  <tr>
    <td style="background:{BRAND_COLOR};padding:16px 20px;border-radius:8px;">
      <table cellpadding="0" cellspacing="0">
        <tr>
          <td style="vertical-align:middle;padding-right:16px;">
            <img src="{LOGO_URL}" alt="EZContact" style="height:28px;display:block;" />
          </td>
          <td style="border-left:1px solid rgba(255,255,255,0.25);padding-left:16px;vertical-align:middle;">
            <strong style="font-size:13px;color:#ffffff;display:block;">Katia Lozano</strong>
            <span style="font-size:12px;color:rgba(255,255,255,0.75);">Ejecutiva Comercial</span>
          </td>
        </tr>
      </table>
      <table cellpadding="0" cellspacing="0" style="margin-top:10px;">
        <tr>
          <td>
            <a href="mailto:katia@ezcontact.mx" style="font-size:12px;color:rgba(255,255,255,0.85);text-decoration:none;">katia@ezcontact.mx</a>
            &nbsp;&nbsp;·&nbsp;&nbsp;
            <a href="https://wa.me/5215523455698" style="font-size:12px;color:rgba(255,255,255,0.85);text-decoration:none;">WhatsApp</a>
            &nbsp;&nbsp;·&nbsp;&nbsp;
            <a href="https://ezcontact.mx" style="font-size:12px;color:rgba(255,255,255,0.85);text-decoration:none;">ezcontact.mx</a>
          </td>
        </tr>
      </table>
    </td>
  </tr>
</table>
"""

def build_subject(business_name: str) -> str:
    if business_name:
        return f"Pregunta rápida — {business_name}"
    return "Pregunta rápida"

def build_body_plain(business_name: str) -> str:
    greeting = f"Hola {business_name}," if business_name else "Hola,"
    return f"""{greeting}

Vi que manejan comunicación con clientes por WhatsApp. Una pregunta directa: ¿hay mensajes que se quedan sin responder porque el equipo no alcanza?

EZContact automatiza la atención en WhatsApp — el asistente responde al instante, califica prospectos y agenda citas, sin reemplazar a tu equipo.

¿Vale la pena 10 minutos? → https://calendly.com/ezcontact/demo

Quedo al pendiente.

--
Katia Lozano
Ejecutiva Comercial | EZContact
katia@ezcontact.mx
wa.me/5215523455698
www.ezcontact.mx
"""

def build_body_html(business_name: str) -> str:
    greeting = f"Hola <strong>{business_name}</strong>," if business_name else "Hola,"
    return f"""<div style="font-family:Arial,Helvetica,sans-serif;max-width:560px;color:#1a1a1a;line-height:1.6;">
<p style="margin:0 0 12px;">{greeting}</p>
<p style="margin:0 0 12px;">Vi que manejan comunicación con clientes por WhatsApp. Una pregunta directa: <strong>¿hay mensajes que se quedan sin responder porque el equipo no alcanza?</strong></p>
<p style="margin:0 0 12px;">EZContact automatiza la atención en WhatsApp — el asistente responde al instante, califica prospectos y agenda citas, sin reemplazar a tu equipo.</p>
<p style="margin:0 0 16px;"><strong>¿Vale la pena 10 minutos?</strong><br>
<a href="https://calendly.com/ezcontact/demo" style="color:{LINK_COLOR};font-weight:600;">→ Agenda demo gratuita (15 min)</a></p>
<p style="margin:0 0 4px;">Quedo al pendiente.</p>
{SIGNATURE_HTML}
</div>"""


# ─── Helpers ──────────────────────────────────────────────────────────────────
def get_smtp_password() -> str | None:
    try:
        r = subprocess.run(['vault', 'get', 'email/katia@ezcontact.mx'],
                           capture_output=True, text=True, timeout=10)
        if r.returncode == 0:
            return r.stdout.strip()
    except Exception as e:
        print(f"❌ vault error: {e}")
    return None

def load_already_sent() -> set:
    if not os.path.exists(ALREADY_SENT_FILE):
        return set()
    try:
        return set(json.load(open(ALREADY_SENT_FILE)).get("emails", []))
    except Exception:
        return set()

def save_already_sent(sent_set: set):
    try:
        with open(ALREADY_SENT_FILE, 'w') as f:
            json.dump({"emails": sorted(list(sent_set)),
                       "last_updated": datetime.now().strftime('%Y-%m-%d')}, f,
                      indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"⚠️  No pude guardar already-sent: {e}")

def load_leads(already_sent: set) -> list:
    """Carga leads únicos no enviados de todos los archivos de prospectos."""
    patterns = [
        f"{PROSPECTOS_DIR}/leads-auto-*.json",
        f"{PROSPECTOS_DIR}/leads-batch-*.json",
        f"{PROSPECTOS_DIR}/leads-outreach-*.json",
        f"{PROSPECTOS_DIR}/leads-consolidated-*.json",
    ]
    leads = []
    seen = set()
    for pattern in patterns:
        for filepath in sorted(glob.glob(pattern)):
            try:
                items = json.load(open(filepath))
                if not isinstance(items, list):
                    continue
                for item in items:
                    email = item.get("email", "").lower().strip()
                    # Validación estricta: rechaza emails malformados
                    if not is_valid_email(email):
                        continue
                    domain = email.split("@")[-1]
                    # Solo dominios mexicanos
                    if not (domain.endswith(".mx") or domain.endswith(".com.mx")):
                        continue
                    if email in already_sent or email in seen:
                        continue
                    seen.add(email)
                    leads.append(item)
            except Exception:
                continue
    return leads

def is_valid_email(email: str) -> bool:
    """
    Valida que el email sea limpio y enviable.
    Filtra: URL-encoded, entidades HTML, prefijos numéricos, formatos raros.
    """
    if not email or "@" not in email:
        return False
    # Rechazar URL-encoded (%xx)
    if "%" in email:
        return False
    # Rechazar entidades HTML (u003e, &amp;, etc.)
    if re.search(r'u[0-9a-f]{4}|&[a-z]+;|&#\d+;', email, re.IGNORECASE):
        return False
    # Rechazar emails que empiezan con dígitos antes del @
    local = email.split("@")[0]
    if re.match(r'^\d+', local):
        return False
    # Rechazar caracteres inválidos en la parte local
    if not re.match(r'^[a-zA-Z0-9._%+\-]+$', local):
        return False
    # Rechazar dominios sin punto
    domain = email.split("@")[1]
    if "." not in domain:
        return False
    # Rechazar sentry/noreply/example/test
    if re.search(r'sentry\.|noreply|no-reply|example\.|test\.', email, re.IGNORECASE):
        return False
    return True


def extract_business_name(lead: dict) -> str:
    """
    Intenta extraer el nombre del negocio del lead.
    Usa 'empresa', 'business_name', 'nombre', o el dominio del email.
    """
    # Prioridad: empresa > business_name > nombre > dominio
    if lead.get("empresa"):
        return lead["empresa"].strip()
    if lead.get("business_name"):
        # Limpiar: truncar a 40 chars max para evitar subjects muy largos
        return lead["business_name"].strip()[:40]
    if lead.get("nombre"):
        return lead["nombre"].strip()
    # Derivar del dominio del email
    email = lead.get("email", "")
    if "@" in email:
        domain = email.split("@")[1]
        # Remover .com.mx, .mx, .edu.mx etc
        name = re.sub(r'\.(com\.mx|edu\.mx|org\.mx|net\.mx|mx)$', '', domain)
        name = re.sub(r'[-_]', ' ', name)
        return name.title()
    return ""

def send_email(to_email: str, subject: str, body_plain: str, body_html: str,
               server: smtplib.SMTP) -> bool:
    try:
        msg = MIMEMultipart("alternative")
        msg["From"]    = f"{FROM_NAME} <{FROM_EMAIL}>"
        msg["To"]      = to_email
        msg["Cc"]      = CC_EMAIL
        msg["Subject"] = subject
        msg.attach(MIMEText(body_plain, "plain", "utf-8"))
        msg.attach(MIMEText(body_html, "html", "utf-8"))
        recipients = [to_email, CC_EMAIL]
        server.sendmail(FROM_EMAIL, recipients, msg.as_string())
        return True
    except Exception as e:
        print(f"   ❌ Error enviando a {to_email}: {e}")
        return False


# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Envía outreach de EZContact")
    parser.add_argument("--limit",   type=int,  default=DEFAULT_LIMIT, help="Máximo de emails a enviar")
    parser.add_argument("--dry-run", action="store_true", help="Simula sin enviar")
    parser.add_argument("--test",    type=str,  default=None, help="Envía solo a este email (prueba)")
    args = parser.parse_args()

    today = datetime.now().strftime('%Y-%m-%d')
    log_file = f"{LOG_DIR}/outreach-{today}.json"

    print(f"\n{'='*55}")
    print(f"  EZContact Outreach — {today}")
    print(f"  Límite: {args.limit} | Dry-run: {args.dry_run}")
    print(f"{'='*55}\n")

    already_sent = load_already_sent()

    # Modo test
    if args.test:
        leads = [{"email": args.test, "vertical": "Test", "source": "manual"}]
    else:
        leads = load_leads(already_sent)

    if not leads:
        print("⚠️  No hay leads nuevos para enviar hoy.")
        print(f"   Ya enviados en total: {len(already_sent)}")
        return

    leads = leads[:args.limit]
    print(f"📋 Leads a enviar: {len(leads)} (de {len(leads)} disponibles)\n")

    if args.dry_run:
        for lead in leads:
            biz = extract_business_name(lead)
            print(f"   [DRY] → {lead['email']} | {biz} | {lead.get('vertical','')}")
        print(f"\n✅ Dry-run completo — {len(leads)} emails simulados")
        return

    # Get SMTP password
    password = get_smtp_password()
    if not password:
        print("❌ No se pudo obtener la contraseña SMTP. Abortando.")
        return

    sent_log = []
    errors   = []

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(FROM_EMAIL, password)
            print(f"✅ SMTP conectado: {SMTP_HOST}:{SMTP_PORT}\n")

            for i, lead in enumerate(leads, 1):
                email = lead["email"].lower().strip()
                biz   = extract_business_name(lead)
                subj  = build_subject(biz)
                plain = build_body_plain(biz)
                html  = build_body_html(biz)

                print(f"  [{i:02d}/{len(leads)}] → {email:<40} | {biz}")

                ok = send_email(email, subj, plain, html, server)
                if ok:
                    already_sent.add(email)
                    sent_log.append({
                        "email":    email,
                        "empresa":  biz,
                        "vertical": lead.get("vertical", ""),
                        "subject":  subj,
                        "sent_at":  datetime.now().isoformat(),
                    })
                    print(f"        ✅ Enviado")
                else:
                    errors.append(email)

                if i < len(leads):
                    time.sleep(DELAY_BETWEEN)

    except Exception as e:
        print(f"\n❌ Error SMTP: {e}")

    # Guardar log del día
    existing_log = []
    if os.path.exists(log_file):
        try:
            existing_log = json.load(open(log_file))
        except Exception:
            pass
    with open(log_file, 'w') as f:
        json.dump(existing_log + sent_log, f, indent=2, ensure_ascii=False)

    # Actualizar already-sent
    save_already_sent(already_sent)

    # Resumen
    print(f"\n{'='*55}")
    print(f"  ✅ Enviados:  {len(sent_log)}")
    print(f"  ❌ Errores:   {len(errors)}")
    print(f"  📁 Log:       {log_file}")
    print(f"  📊 Total acumulado: {len(already_sent)} emails")
    print(f"{'='*55}\n")

    if errors:
        print("Errores:")
        for e in errors:
            print(f"  - {e}")


if __name__ == "__main__":
    main()
