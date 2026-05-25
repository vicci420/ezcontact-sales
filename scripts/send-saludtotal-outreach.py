#!/usr/bin/env python3
"""
send-saludtotal-outreach.py — Outreach de Salud Total desde victor.arredondo@saludtotal.mx

Copy aprobado por Vicci:
  Subject: "Oye doctor, pregunta rápida"
  Texto: plano, primera persona, pain-first, argumento decreto DOF ene 2026
  Cuenta: victor.arredondo@saludtotal.mx

Uso:
    python3 scripts/send-saludtotal-outreach.py          # dry-run (sin enviar)
    python3 scripts/send-saludtotal-outreach.py --send   # envía de verdad
    python3 scripts/send-saludtotal-outreach.py --send --limit 20   # máx 20
    python3 scripts/send-saludtotal-outreach.py --test tu@correo.mx # prueba

REGLA: NO ejecutar sin confirmación explícita de Vicci.
       El cron de 10am CDMX (16:00 UTC) es el canal de envío autorizado.
"""

import smtplib
import json
import os
import argparse
import subprocess
import time
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

# ─── Config ───────────────────────────────────────────────────────────────────
SMTP_HOST  = "mail.saludtotal.mx"
SMTP_PORT  = 587
FROM_EMAIL = "victor.arredondo@saludtotal.mx"
FROM_NAME  = "Victor Arredondo"
CC_EMAIL   = "victor.arredondo.ambriz@gmail.com"   # Vicci siempre en CC

LEADS_FILE         = "/home/ubuntu/clawd/prospectos/saludtotal-combined-2026-03-08.json"
ALREADY_SENT_FILE  = "/home/ubuntu/clawd/memory/saludtotal-already-sent.json"
LOG_DIR            = "/home/ubuntu/clawd/prospectos"
DEFAULT_LIMIT      = 120
DELAY_BETWEEN      = 5   # segundos entre envíos (respetar servidor)

# ─── Emails/leads a EXCLUIR ───────────────────────────────────────────────────
# Extensiones de archivo (el regex a veces captura filenames como "email")
FAKE_EMAIL_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.webp', '.gif', '.svg',
                         '.mp4', '.mp3', '.pdf', '.zip', '.css', '.js'}

# Dominios de gobierno/instituciones públicas (no son nuestro ICP)
GOV_PATTERNS = ['.gob.mx', '.gob.rr', '.gob.', '@salud.gob', 'ssaver.gob', 'ssatab',
                'prodigy.net', '.uadec.mx', 'udg.mx', 'live.com.mx',
                '@cln.megared', '@iner.gob', 'megared.net']

# Emails dummy conocidos
DUMMY_EMAILS = {'usuario@dominio.com', 'info@mysite.com', 'info@enlistalo.com.mx',
                'info@doclink.pro'}

# Dominios de directorios/agregadores (no clínicas reales)
DIRECTORY_DOMAINS = {'doclink.pro', 'topdoctors.mx', 'doctoralia.mx',
                     'enlistalo.com.mx', 'healthgrades.com', 'nimbo-x.com'}

# Dominios/palabras clave a excluir (Vicci: NO prospectar odontólogos ni nutriólogos)
EXCLUDED_VERTICALS_KEYWORDS = [
    'dental', 'dentista', 'denti', 'odon', 'endodon', 'ortodon',
    'nutri', 'nutriol', 'nutricion', 'nutricion',
]

def is_sendable(email: str) -> bool:
    """Verifica si un email es válido y debe enviarse."""
    e = email.lower().strip()
    if e in DUMMY_EMAILS:
        return False
    local, _, domain = e.partition('@')
    if not domain:
        return False
    # Filtrar archivos con extensión (e.g. image@2x-1.webp)
    for ext in FAKE_EMAIL_EXTENSIONS:
        if domain.endswith(ext) or local.endswith(ext.lstrip('.')):
            return False
    # Local muy corto o numérico → fake
    if len(local) < 3:
        return False
    # Filtrar gobierno
    for pat in GOV_PATTERNS:
        if pat in e:
            return False
    # Filtrar directorios
    for dd in DIRECTORY_DOMAINS:
        if dd in domain:
            return False
    return True

# ─── Email copy ───────────────────────────────────────────────────────────────
SUBJECT = "Oye doctor, pregunta rápida"

EMAIL_BODY_TEMPLATE = """\
Hola,

Vi que tienes consulta en CDMX y quería hacerte una pregunta directa.

¿Ya estás usando expediente clínico electrónico? Desde enero 2026 hay un decreto del \
DOF que obliga a todos los médicos a digitalizar sus expedientes — los que no cumplan \
están en riesgo legal.

Tenemos una solución que se configura en 48 horas, desde $259/mes, y ya cumple NOM-004. \
La usan más de 500 médicos en México.

¿Vale la pena 10 minutos para ver si te sirve?

Victor Arredondo
Salud Total
victor.arredondo@saludtotal.mx
saludtotal.mx
"""

# ─── Helpers ──────────────────────────────────────────────────────────────────

def load_already_sent() -> set:
    if not os.path.exists(ALREADY_SENT_FILE):
        return set()
    try:
        with open(ALREADY_SENT_FILE) as f:
            data = json.load(f)
        return set(e.lower() for e in data.get("emails", []))
    except Exception:
        return set()


def save_already_sent(emails: set) -> None:
    data = {"emails": sorted(list(emails)),
            "updated": datetime.now().isoformat()}
    os.makedirs(os.path.dirname(ALREADY_SENT_FILE), exist_ok=True)
    with open(ALREADY_SENT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_leads() -> list:
    if not os.path.exists(LEADS_FILE):
        print(f"❌ Leads file not found: {LEADS_FILE}")
        sys.exit(1)
    with open(LEADS_FILE, encoding="utf-8") as f:
        return json.load(f)


def get_smtp_password() -> str:
    try:
        r = subprocess.run(
            ["vault", "get", "email/victor.arredondo@saludtotal.mx"],
            capture_output=True, text=True, timeout=10
        )
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    except Exception:
        pass
    return os.environ.get("SALUDTOTAL_SMTP_PASSWORD", "")


def build_message(to_email: str, business_name: str) -> MIMEMultipart:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = SUBJECT
    msg["From"]    = f"{FROM_NAME} <{FROM_EMAIL}>"
    msg["To"]      = to_email
    msg["Cc"]      = CC_EMAIL
    msg["X-Mailer"] = "SaludTotal-Outreach/1.0"

    # Plain text only (as per Vicci's approval — no HTML)
    body = EMAIL_BODY_TEMPLATE
    msg.attach(MIMEText(body, "plain", "utf-8"))
    return msg


def send_emails(leads: list, dry_run: bool, limit: int) -> dict:
    already_sent = load_already_sent()
    print(f"📊 Ya enviados: {len(already_sent)} (skip automático)")

    # Filter: already sent + quality check + vertical exclusions
    def is_lead_ok(lead):
        email = lead["email"].lower()
        biz   = (lead.get("business_name") or "").lower()
        vertical = (lead.get("vertical") or "").lower()
        combined = email + " " + biz + " " + vertical
        if not is_sendable(email):
            return False
        # Exclude verticals Vicci said NOT to prospect
        for kw in EXCLUDED_VERTICALS_KEYWORDS:
            if kw in combined:
                return False
        return True

    quality = [l for l in leads if is_lead_ok(l)]
    pending = [l for l in quality if l["email"].lower() not in already_sent]
    pending = pending[:limit]

    skipped_quality = len(leads) - len(quality)
    print(f"🚫 Filtrados (calidad baja/gob/fake/excl): {skipped_quality}")
    print(f"📬 Pendientes limpios: {len(pending)} leads (límite: {limit})")

    if not pending:
        print("✅ No hay leads nuevos. Todo enviado.")
        return {"sent": 0, "errors": 0, "skipped": len(leads) - len(pending)}

    if dry_run:
        print(f"\n[DRY RUN] Simularía enviar {len(pending)} correos:")
        for i, lead in enumerate(pending, 1):
            print(f"  {i}. {lead['email']} — {lead.get('business_name','?')[:50]}")
        print(f"\n⚠️  Para enviar de verdad: --send")
        return {"sent": 0, "errors": 0, "skipped": 0, "dry_run": True}

    # Real send
    password = get_smtp_password()
    if not password:
        print("❌ No se encontró password SMTP para saludtotal. Revisa vault.")
        sys.exit(1)

    sent = []
    errors = []

    try:
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30)
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(FROM_EMAIL, password)
        print(f"✅ SMTP conectado a {SMTP_HOST}:{SMTP_PORT}")
    except Exception as e:
        print(f"❌ Error SMTP: {e}")
        sys.exit(1)

    for i, lead in enumerate(pending, 1):
        to_email = lead["email"].lower()
        biz_name = lead.get("business_name", "")
        try:
            msg = build_message(to_email, biz_name)
            recipients = [to_email, CC_EMAIL]
            server.sendmail(FROM_EMAIL, recipients, msg.as_string())
            already_sent.add(to_email)
            sent.append({"email": to_email, "business": biz_name,
                         "sent_at": datetime.now().isoformat()})
            print(f"  ✅ [{i}/{len(pending)}] {to_email} — {biz_name[:40]}")
            if i < len(pending):
                time.sleep(DELAY_BETWEEN)
        except Exception as e:
            errors.append({"email": to_email, "error": str(e)})
            print(f"  ❌ [{i}/{len(pending)}] {to_email} — {e}")

    try:
        server.quit()
    except Exception:
        pass

    # Persist sent emails
    save_already_sent(already_sent)

    # Save log
    today = datetime.now().strftime("%Y-%m-%d")
    log_path = f"{LOG_DIR}/saludtotal-outreach-{today}.json"
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump({"sent": sent, "errors": errors,
                   "total_sent": len(already_sent),
                   "run_at": datetime.now().isoformat()}, f,
                  indent=2, ensure_ascii=False)

    return {"sent": len(sent), "errors": len(errors),
            "log": log_path, "total_historic": len(already_sent)}


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="SaludTotal email outreach")
    parser.add_argument("--send",    action="store_true", help="Enviar de verdad (default: dry-run)")
    parser.add_argument("--limit",   type=int, default=DEFAULT_LIMIT, help="Máximo de correos a enviar")
    parser.add_argument("--test",    metavar="EMAIL", help="Enviar un correo de prueba a este email")
    args = parser.parse_args()

    print(f"\n🩺 SaludTotal Outreach — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   From: {FROM_EMAIL}")
    print(f"   Leads: {LEADS_FILE}")
    print(f"   Modo: {'ENVÍO REAL' if args.send else 'DRY RUN'}\n")

    # Test mode
    if args.test:
        dry_run = not args.send
        test_lead = [{"email": args.test, "business_name": "Test Clínica"}]
        result = send_emails(test_lead, dry_run=False, limit=1)
        print(f"\n✅ Test enviado a {args.test}")
        return

    leads = load_leads()
    print(f"📋 Leads cargados: {len(leads)}")

    result = send_emails(leads, dry_run=not args.send, limit=args.limit)

    print(f"\n{'='*50}")
    if result.get("dry_run"):
        print(f"[DRY RUN] {result.get('sent', 0)} correos simulados (no enviados)")
    else:
        print(f"✅ Enviados: {result['sent']}")
        print(f"❌ Errores:  {result['errors']}")
        if result.get("log"):
            print(f"📄 Log:      {result['log']}")
        print(f"📊 Total histórico: {result.get('total_historic', 0)} emails enviados")


if __name__ == "__main__":
    main()
