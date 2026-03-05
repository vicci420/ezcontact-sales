#!/usr/bin/env python3
"""
CRM Prospect Tracker — EZContact
Mantiene el estado de cada prospecto en el pipeline de ventas.

Estados:
  contacted       → Email enviado, sin respuesta
  replied         → Respondieron (auto-detectado por reply-detector)
  demo_scheduled  → Demo agendada (manual)
  demo_done       → Demo completada (manual)
  closed_won      → Cerrado ✅ (manual)
  closed_lost     → Rechazado ❌ (blacklist / "no me interesa")

Uso:
  python3 scripts/crm-tracker.py               # muestra pipeline completo
  python3 scripts/crm-tracker.py --update      # actualiza desde logs
  python3 scripts/crm-tracker.py --stage demo_scheduled
  python3 scripts/crm-tracker.py --today       # solo actividad de hoy
  python3 scripts/crm-tracker.py --report      # markdown report

Versión 1.0 — 5 mar 2026 | Katia Lozano / EZContact
"""

import json
import os
import re
import glob
import argparse
import imaplib
import email as email_module
import email.header
from datetime import datetime, timedelta
from pathlib import Path

# ─── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR        = Path("/home/ubuntu/clawd")
CRM_FILE        = BASE_DIR / "prospectos" / "crm-state.json"
ALREADY_SENT    = BASE_DIR / "memory" / "already-sent.json"
LOG_DIR         = BASE_DIR / "memory" / "outreach-logs"
HANDLED_REPLIES = BASE_DIR / "prospectos" / "handled-replies.json"
REPORT_FILE     = BASE_DIR / "memory" / f"crm-report-{datetime.now().strftime('%Y-%m-%d')}.md"

# ─── IMAP config ──────────────────────────────────────────────────────────────
IMAP_HOST = "mail.ezcontact.mx"
IMAP_PORT = 993
IMAP_USER = "katia@ezcontact.mx"

KNOWN_CONTACTS = {
    # email → nombre/empresa (para display)
    "administracion@idiomascuc.com": "Idiomas CUC (Elsa)",
    "info@idiomascuc.com": "Idiomas CUC (info)",
    "hola@tentenpie.mx": "TentenPie (Catering)",
    "contacto@vetme.mx": "Vetme (Veterinaria)",
    "carlosmena@rivaliaestudio.com": "Rivalia Estudio (Carlos)",
    "contacto@506dentalstudio.com": "506 Dental Studio (Gabriela)",
}

STAGE_EMOJI = {
    "contacted":       "📤",
    "replied":         "💬",
    "demo_scheduled":  "📅",
    "demo_done":       "🎯",
    "closed_won":      "✅",
    "closed_lost":     "❌",
    "unsubscribed":    "🚫",
}

STAGE_ORDER = [
    "replied", "demo_scheduled", "demo_done", "closed_won", "closed_lost",
    "unsubscribed", "contacted",
]


def load_crm() -> dict:
    """Carga el estado CRM desde archivo JSON."""
    if CRM_FILE.exists():
        try:
            return json.loads(CRM_FILE.read_text())
        except Exception:
            pass
    return {}


def save_crm(crm: dict):
    """Guarda el estado CRM."""
    CRM_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CRM_FILE, 'w', encoding='utf-8') as f:
        json.dump(crm, f, indent=2, ensure_ascii=False)


def load_sent_emails() -> list:
    """Carga todos los emails enviados desde already-sent.json y logs."""
    emails = []

    # Desde already-sent.json
    if ALREADY_SENT.exists():
        try:
            data = json.loads(ALREADY_SENT.read_text())
            for em in data.get("emails", []):
                emails.append({"email": em, "sent_at": None, "empresa": None})
        except Exception:
            pass

    # Desde logs de outreach (tienen fecha y empresa)
    for log_file in sorted(glob.glob(str(BASE_DIR / "memory" / "outreach-*.json"))):
        try:
            records = json.load(open(log_file))
            for r in records:
                em = r.get("email", "").lower().strip()
                if em:
                    emails.append({
                        "email":    em,
                        "sent_at":  r.get("sent_at"),
                        "empresa":  r.get("empresa") or r.get("business_name"),
                        "vertical": r.get("vertical"),
                    })
        except Exception:
            continue

    return emails


def get_imap_password() -> str:
    """Obtiene password IMAP desde vault."""
    try:
        import subprocess
        r = subprocess.run(
            ['vault', 'get', 'email/katia@ezcontact.mx'],
            capture_output=True, text=True, timeout=10
        )
        if r.returncode == 0:
            return r.stdout.strip()
    except Exception:
        pass
    return ""


def scan_replies(crm: dict) -> dict:
    """Escanea inbox y actualiza CRM con respuestas encontradas."""
    password = get_imap_password()
    if not password:
        print("⚠️  No se pudo obtener contraseña IMAP")
        return crm

    updated = 0
    try:
        mail = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
        mail.login(IMAP_USER, password)
        mail.select("INBOX")

        # Buscar emails recibidos en últimos 30 días
        since = (datetime.now() - timedelta(days=30)).strftime("%d-%b-%Y")
        result, data = mail.search(None, f'SINCE {since}')
        if result != 'OK':
            mail.close()
            mail.logout()
            return crm

        ids = data[0].split()
        print(f"   Escaneando {len(ids)} emails en inbox...")

        for msg_id in ids:
            try:
                result, msg_data = mail.fetch(msg_id, '(RFC822)')
                msg = email_module.message_from_bytes(msg_data[0][1])

                from_raw = msg.get("From", "")
                from_match = re.search(r'[\w._%+\-]+@[\w.\-]+\.\w+', from_raw)
                if not from_match:
                    continue

                sender = from_match.group(0).lower()

                # Ignorar nuestros propios correos
                if sender in ("katia@ezcontact.mx", "victor@ezcontact.mx"):
                    continue

                # ¿Es un prospecto de nuestro outreach?
                if sender not in crm:
                    continue

                # Solo emails .mx (prospectos mexicanos)
                sender_domain = sender.split("@")[-1]
                if not sender_domain.endswith(".mx") and sender not in KNOWN_CONTACTS:
                    continue

                subject = ""
                subj_raw = msg.get("Subject", "")
                try:
                    decoded = email_module.header.decode_header(subj_raw)
                    for part, enc in decoded:
                        if isinstance(part, bytes):
                            subject += part.decode(enc or 'utf-8', errors='replace')
                        else:
                            subject += str(part)
                except Exception:
                    subject = subj_raw

                # Extraer solo el texto de la respuesta (no el email original)
                body = ""
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        payload = part.get_payload(decode=True)
                        if payload:
                            text = payload.decode('utf-8', errors='replace')
                            # Cortar en la primera línea de "quoted text"
                            for sep in ['--- Mensaje original', '-----Original', 'De:', 'From:', '>']:
                                idx = text.find(sep)
                                if idx > 0:
                                    text = text[:idx]
                            body = text.strip()[:500]
                            break

                # Clasificar la respuesta
                body_lower = body.lower()
                subject_lower = subject.lower()

                stage = "replied"
                notes = subject

                reject_keywords = ['no me interesa', 'no estamos interesados', 'no interesa',
                                   'not interested', 'unsubscribe', 'no gracias', 'dar de baja',
                                   'eliminar', 'remove me', 'darme de baja']
                demo_keywords = ['demo', 'reunión', 'reunion', 'llamada', 'junta', 'videoconferencia',
                                 'agendar', 'martes', 'miércoles', 'jueves', 'viernes', 'lunes',
                                 '11am', '10am', '9am', 'mañana', 'next week', 'disponible']
                interest_keywords = ['interesa', 'información', 'informacion', 'saber más',
                                     'cotización', 'precio', '¿cuánto', 'dudas', 'preguntas',
                                     'marcarme', 'teléfono', 'whatsapp']

                combined = body_lower + " " + subject_lower

                if any(kw in combined for kw in reject_keywords):
                    stage = "closed_lost"
                    notes = f"Rechazó: {body[:100]}"
                elif any(kw in combined for kw in demo_keywords):
                    stage = "demo_scheduled"
                    notes = f"Mencionaron demo: {body[:100]}"
                elif any(kw in combined for kw in interest_keywords):
                    stage = "replied"
                    notes = f"Interesado: {body[:100]}"

                # Solo actualizar si es un upgrade de estado
                current_stage = crm[sender].get("stage", "contacted")
                stage_rank = STAGE_ORDER.index
                try:
                    if STAGE_ORDER.index(stage) < STAGE_ORDER.index(current_stage):
                        crm[sender]["stage"] = stage
                        crm[sender]["last_reply"] = body[:200]
                        crm[sender]["reply_subject"] = subject
                        crm[sender]["reply_at"] = datetime.now().isoformat()
                        updated += 1
                        print(f"   💬 {sender} → {stage}")
                except ValueError:
                    pass

            except Exception:
                continue

        mail.close()
        mail.logout()
        print(f"   ✅ {updated} prospectos actualizados")

    except Exception as e:
        print(f"   ❌ Error IMAP: {e}")

    return crm


def update_from_logs(crm: dict) -> dict:
    """Actualiza CRM con todos los emails enviados."""
    sent = load_sent_emails()
    new_contacts = 0

    for record in sent:
        em = record["email"]
        if not em or "@" not in em:
            continue

        # Solo prospectos mexicanos (.mx) o conocidos
        domain = em.split("@")[-1]
        if not domain.endswith(".mx") and em not in KNOWN_CONTACTS:
            continue

        # Ignorar propias cuentas
        if em in ("katia@ezcontact.mx", "victor@ezcontact.mx"):
            continue

        if em not in crm:
            crm[em] = {
                "email":    em,
                "empresa":  record.get("empresa") or KNOWN_CONTACTS.get(em, ""),
                "vertical": record.get("vertical", ""),
                "stage":    "contacted",
                "sent_at":  record.get("sent_at"),
                "reply_at": None,
                "last_reply": None,
                "notes":    "",
            }
            new_contacts += 1
        elif record.get("empresa") and not crm[em].get("empresa"):
            crm[em]["empresa"] = record["empresa"]

    if new_contacts > 0:
        print(f"   + {new_contacts} prospectos nuevos agregados al CRM")

    return crm


def set_stage(crm: dict, email_addr: str, stage: str, notes: str = "") -> dict:
    """Actualiza manualmente el stage de un prospecto."""
    em = email_addr.lower().strip()
    if em not in crm:
        print(f"❌ {em} no está en el CRM")
        return crm

    crm[em]["stage"] = stage
    crm[em]["notes"] = notes
    crm[em]["updated_at"] = datetime.now().isoformat()
    print(f"✅ {em} → {stage}")
    return crm


def print_pipeline(crm: dict, filter_stage: str = None, today_only: bool = False):
    """Muestra el pipeline organizado por etapa."""
    today = datetime.now().strftime('%Y-%m-%d')

    # Agrupar por stage
    by_stage = {}
    for em, data in crm.items():
        stage = data.get("stage", "contacted")
        if filter_stage and stage != filter_stage:
            continue
        if today_only:
            sent_today = (data.get("sent_at", "") or "").startswith(today)
            replied_today = (data.get("reply_at", "") or "").startswith(today)
            if not sent_today and not replied_today:
                continue
        by_stage.setdefault(stage, []).append(data)

    total = sum(len(v) for v in by_stage.values())
    print(f"\n{'='*55}")
    print(f"  EZContact CRM Pipeline — {today}")
    print(f"  Total prospectos: {total}")
    print(f"{'='*55}")

    for stage in STAGE_ORDER:
        contacts = by_stage.get(stage, [])
        if not contacts:
            continue
        emoji = STAGE_EMOJI.get(stage, "•")
        print(f"\n{emoji} {stage.upper()} ({len(contacts)})")
        print(f"{'─'*40}")
        for c in sorted(contacts, key=lambda x: x.get("reply_at") or x.get("sent_at") or "", reverse=True):
            em = c.get("email", "")
            biz = (c.get("empresa") or "")[:30]
            reply_snippet = (c.get("last_reply") or "")[:50]
            date_str = ""
            if c.get("reply_at"):
                date_str = c["reply_at"][:10]
            elif c.get("sent_at"):
                date_str = (c["sent_at"] or "")[:10]
            print(f"  {em:<40} {biz:<30} {date_str}")
            if reply_snippet:
                print(f"    └─ \"{reply_snippet}...\"")

    print(f"\n{'='*55}\n")


def generate_report(crm: dict) -> str:
    """Genera reporte Markdown del pipeline para morning brief."""
    today = datetime.now().strftime('%Y-%m-%d')
    lines = [
        f"# 📊 CRM EZContact — {today}",
        "",
        "## Pipeline Summary",
        "",
    ]

    # Stats por stage
    by_stage = {}
    for em, data in crm.items():
        stage = data.get("stage", "contacted")
        by_stage.setdefault(stage, []).append(data)

    total = sum(len(v) for v in by_stage.values())
    lines.append(f"**Total prospectos:** {total}")
    lines.append("")

    for stage in STAGE_ORDER:
        contacts = by_stage.get(stage, [])
        if not contacts:
            continue
        emoji = STAGE_EMOJI.get(stage, "•")
        lines.append(f"- {emoji} **{stage}:** {len(contacts)}")

    lines.extend(["", "---", "", "## 🔥 Acción Requerida"])

    # Hot leads: replied + demo_scheduled
    for priority_stage in ["demo_scheduled", "replied"]:
        contacts = by_stage.get(priority_stage, [])
        if contacts:
            lines.append(f"\n### {STAGE_EMOJI[priority_stage]} {priority_stage.upper()}")
            for c in contacts:
                em = c.get("email", "")
                biz = c.get("empresa") or KNOWN_CONTACTS.get(em, em)
                reply = (c.get("last_reply") or "")[:80]
                lines.append(f"\n**{biz}** (`{em}`)")
                if reply:
                    lines.append(f"> {reply}")
                if c.get("notes"):
                    lines.append(f"- Nota: {c['notes']}")

    lines.extend(["", "---", "", "## 📤 Contacted esta semana"])
    week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    recent_contacted = [
        c for c in by_stage.get("contacted", [])
        if (c.get("sent_at") or "") >= week_ago
    ]
    lines.append(f"{len(recent_contacted)} emails enviados en los últimos 7 días sin respuesta")

    report = "\n".join(lines)
    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"📄 Reporte guardado: {REPORT_FILE}")
    return report


def main():
    parser = argparse.ArgumentParser(description="CRM Prospect Tracker — EZContact")
    parser.add_argument("--update",   action="store_true", help="Actualiza CRM desde logs y replies")
    parser.add_argument("--stage",    type=str,  default=None, help="Filtrar por stage")
    parser.add_argument("--today",    action="store_true", help="Solo actividad de hoy")
    parser.add_argument("--report",   action="store_true", help="Genera reporte Markdown")
    parser.add_argument("--set",      type=str,  default=None, metavar="EMAIL",
                        help="Actualiza manualmente el stage de un email")
    parser.add_argument("--to-stage", type=str,  default=None, metavar="STAGE",
                        help="Nuevo stage (usar con --set)")
    parser.add_argument("--notes",    type=str,  default="", help="Notas para --set")
    args = parser.parse_args()

    print(f"\n🎯 CRM Tracker — {datetime.now().strftime('%Y-%m-%d %H:%M CDMX')}")

    crm = load_crm()
    print(f"   Prospectos en CRM: {len(crm)}")

    if args.set:
        if not args.to_stage:
            print("❌ Especifica --to-stage <stage>")
            return
        crm = set_stage(crm, args.set, args.to_stage, args.notes)
        save_crm(crm)
        return

    if args.update:
        print("\n📥 Actualizando desde logs de envío...")
        crm = update_from_logs(crm)
        print("\n📬 Escaneando inbox para replies...")
        crm = scan_replies(crm)
        save_crm(crm)
        print(f"✅ CRM guardado con {len(crm)} prospectos")

    if args.report:
        generate_report(crm)
    else:
        print_pipeline(crm, filter_stage=args.stage, today_only=args.today)


if __name__ == "__main__":
    main()
