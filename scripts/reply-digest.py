#!/usr/bin/env python3
"""
reply-digest.py — Generador de digest de respuestas de prospectos
Corre en el turno nocturno. Lee inbox katia, clasifica respuestas,
genera drafts listos para que Vicci los apruebe al despertar.

Uso: python3 scripts/reply-digest.py
Requiere: himalaya configurado con cuenta 'katia'
"""

import os
import json
import subprocess
import datetime
import re
from pathlib import Path

# ─── Config ───────────────────────────────────────────────────────────────────
WORKSPACE = Path(os.environ.get("WORKSPACE", "/home/ubuntu/clawd"))
CRM_PATH = WORKSPACE / "prospectos" / "crm-state.json"
REPLIES_DIR = WORKSPACE / "prospectos" / "pending-replies"
MEMORY_DIR = WORKSPACE / "memory"
DIGEST_PATH = MEMORY_DIR / "reply-digest.md"

# Patrones que indican respuesta positiva
POSITIVE_SIGNALS = [
    r"cuando se les acomoda",
    r"me pueden marcar",
    r"tengo interés",
    r"cuánto cuesta",
    r"cuanto cuesta",
    r"quiero ver",
    r"demo",
    r"llamada",
    r"martes",
    r"lunes",
    r"disponible",
    r"pueden mandar",
    r"más información",
    r"mas informacion",
    r"me interesa",
    r"nos interesa",
    r"con gusto",
    r"podemos ver",
    r"reagend",
]

# Patrones que indican no interesado
NEGATIVE_SIGNALS = [
    r"no estamos interesados",
    r"no me interesa",
    r"no es para nosotros",
    r"no gracias",
    r"favor de no",
    r"remover",
    r"baja de",
    r"unsubscribe",
]

# Auto-replies a ignorar
AUTORESPONDER_SIGNALS = [
    r"auto.reply",
    r"out of office",
    r"fuera de la oficina",
    r"autoresponder",
    r"noreply",
    r"no-reply",
    r"faleconosco",
    r"solicitação recebida",
    r"laboratorio.*chopo.*certeza",
    r"thanks for your email.*we will respond",
    r"gracias por tu inter.*equipo de proveedores",
]


# ─── Helpers ──────────────────────────────────────────────────────────────────

def cdmx_now():
    utc = datetime.datetime.utcnow()
    return utc - datetime.timedelta(hours=6)


def run_himalaya(args: list[str]) -> str:
    """Corre himalaya con la cuenta katia y retorna stdout."""
    cmd = ["himalaya", "message", "read", "-a", "katia"] + args
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    return result.stdout


def get_inbox_envelopes() -> list[dict]:
    """Lista los últimos 50 emails del inbox de katia."""
    result = subprocess.run(
        ["himalaya", "envelope", "list", "-a", "katia", "--output", "json", "--page-size", "50"],
        capture_output=True, text=True, timeout=30
    )
    try:
        data = json.loads(result.stdout)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


def classify_reply(subject: str, body: str, sender: str) -> str:
    """Clasifica una respuesta: positive | negative | autoresponse | unknown."""
    text = (subject + " " + body + " " + sender).lower()

    for pattern in AUTORESPONDER_SIGNALS:
        if re.search(pattern, text, re.IGNORECASE):
            return "autoresponse"

    for pattern in NEGATIVE_SIGNALS:
        if re.search(pattern, text, re.IGNORECASE):
            return "negative"

    for pattern in POSITIVE_SIGNALS:
        if re.search(pattern, text, re.IGNORECASE):
            return "positive"

    return "unknown"


def extract_prospect_name(subject: str) -> str:
    """Extrae nombre del prospecto del subject del email."""
    # Buscar patrón "— NombreEmpresa" en el subject
    match = re.search(r"—\s*(.+?)$", subject)
    if match:
        return match.group(1).strip()
    return ""


def load_crm() -> dict:
    if CRM_PATH.exists():
        return json.loads(CRM_PATH.read_text())
    return {}


def save_crm(crm: dict):
    CRM_PATH.parent.mkdir(parents=True, exist_ok=True)
    CRM_PATH.write_text(json.dumps(crm, indent=2, ensure_ascii=False))


def generate_draft_reply(empresa: str, email: str, last_reply: str, stage: str) -> str:
    """Genera un draft de respuesta contextual."""
    if stage == "positive":
        return f"""From: Katia Lozano <katia@ezcontact.mx>
To: {email}
CC: victor@ezcontact.mx
Subject: Re: [respuesta a su mensaje]

Hola,

Muchas gracias por su respuesta — con mucho gusto agendamos una llamada.

Tengo disponibilidad el **martes 10 de marzo a las 10:00am** o el **miércoles 11 a las 11:00am**. ¿Les funciona alguno?

La demo dura 15 minutos y no requiere preparación de su parte.

--
Katia Lozano
Ejecutiva Comercial | EZContact
📧 katia@ezcontact.mx
📱 wa.me/5215523455698
🌐 www.ezcontact.mx
"""
    return ""


def generate_digest(replies: list[dict]) -> str:
    """Genera el markdown del digest."""
    now = cdmx_now()
    date_str = now.strftime("%d de %B de %Y, %I:%M %p")

    positives = [r for r in replies if r["classification"] == "positive"]
    negatives = [r for r in replies if r["classification"] == "negative"]
    unknowns = [r for r in replies if r["classification"] == "unknown"]

    lines = [
        f"# 📬 Reply Digest — {date_str} CDMX",
        "",
        f"**{len(positives)} interesados** · {len(negatives)} no interesados · {len(unknowns)} sin clasificar",
        "",
        "---",
        "",
    ]

    if positives:
        lines += ["## 🔥 INTERESADOS — Responder HOY", ""]
        for r in positives:
            days_ago = (now - datetime.datetime.fromisoformat(r["date"])).days if r.get("date") else "?"
            lines += [
                f"### {r['empresa'] or r['sender']}",
                f"- **Email:** {r['email']}",
                f"- **Hace:** {days_ago} días",
                f"- **Dijeron:** _{r['snippet']}_",
                f"- **Draft:** `pending-replies/{r['draft_file']}`",
                "",
            ]

    if negatives:
        lines += ["## ❌ NO INTERESADOS — Actualizar CRM", ""]
        for r in negatives:
            lines += [
                f"- **{r['empresa'] or r['sender']}** ({r['email']}) — sacar del pipeline",
            ]
        lines += [""]

    if unknowns:
        lines += ["## 🤔 SIN CLASIFICAR — Revisar manualmente", ""]
        for r in unknowns:
            lines += [
                f"- **{r['empresa'] or r['sender']}** | _{r['snippet'][:100]}_",
            ]
        lines += [""]

    lines += [
        "---",
        "",
        f"_Generado automáticamente por reply-digest.py · {date_str} CDMX_",
    ]

    return "\n".join(lines)


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    print(f"📬 Reply Digest Generator — {cdmx_now().strftime('%Y-%m-%d %H:%M')} CDMX")
    print()

    crm = load_crm()
    envelopes = get_inbox_envelopes()
    print(f"   Revisando {len(envelopes)} emails en inbox...")

    REPLIES_DIR.mkdir(parents=True, exist_ok=True)

    processed_replies = []
    auto_count = 0

    for env in envelopes:
        subject = env.get("subject", "")
        sender = env.get("from", {})
        sender_email = ""
        if isinstance(sender, dict):
            sender_email = sender.get("addr", "")
        elif isinstance(sender, str):
            sender_email = sender

        # Solo procesar respuestas (Re: o RE:)
        if not re.match(r"^(Re:|RE:)", subject.strip()):
            continue

        msg_id = str(env.get("id", ""))

        # Leer cuerpo
        body = run_himalaya([msg_id])
        classification = classify_reply(subject, body, sender_email)

        if classification == "autoresponse":
            auto_count += 1
            continue

        # Extraer snippet (primeras 150 chars del cuerpo limpio)
        body_clean = re.sub(r"\x1b\[[0-9;]*m", "", body)  # strip ANSI
        body_lines = [l for l in body_clean.split("\n") if l.strip() and not l.startswith(">") and not l.startswith("From:")]
        snippet = " ".join(body_lines[:3])[:150]

        # Empresa desde CRM
        empresa = ""
        if sender_email in crm:
            empresa = crm[sender_email].get("empresa", "")

        # Fecha del envelope
        date_str = env.get("date", "")
        try:
            # ISO parse attempt
            date_obj = datetime.datetime.fromisoformat(date_str[:19])
        except Exception:
            date_obj = cdmx_now()

        reply_data = {
            "email": sender_email,
            "sender": sender_email,
            "empresa": empresa,
            "subject": subject,
            "snippet": snippet,
            "classification": classification,
            "date": date_obj.isoformat(),
            "draft_file": "",
        }

        # Update CRM
        if sender_email not in crm:
            crm[sender_email] = {"email": sender_email, "empresa": empresa}

        if classification == "positive":
            crm[sender_email]["stage"] = "interested"
            crm[sender_email]["reply_at"] = date_obj.isoformat()
            crm[sender_email]["last_reply"] = snippet

            # Generate and save draft
            draft = generate_draft_reply(empresa, sender_email, snippet, "positive")
            safe_name = re.sub(r"[^\w@.]", "-", sender_email)
            draft_file = f"auto-draft-{safe_name}-{cdmx_now().strftime('%Y%m%d')}.md"
            (REPLIES_DIR / draft_file).write_text(
                f"# Draft — {empresa or sender_email}\n# Status: PENDIENTE AUTORIZACIÓN DE VICCI\n\n---\n{draft}"
            )
            reply_data["draft_file"] = draft_file

        elif classification == "negative":
            crm[sender_email]["stage"] = "not_interested"
            crm[sender_email]["reply_at"] = date_obj.isoformat()

        processed_replies.append(reply_data)
        print(f"   {classification.upper():12s} — {empresa or sender_email}")

    save_crm(crm)
    print(f"\n   Autorespuestas ignoradas: {auto_count}")

    # Generate digest
    if processed_replies:
        digest = generate_digest(processed_replies)
        DIGEST_PATH.write_text(digest)
        print(f"\n✅ Digest guardado: {DIGEST_PATH}")

        positives = [r for r in processed_replies if r["classification"] == "positive"]
        print(f"\n🔥 {len(positives)} prospectos interesados — revisar con Vicci en morning brief")
    else:
        print("\n   No hay respuestas nuevas para procesar.")
        DIGEST_PATH.write_text(
            f"# 📬 Reply Digest — {cdmx_now().strftime('%d/%m/%Y')}\n\nNo hay respuestas nuevas. ✅\n"
        )


if __name__ == "__main__":
    main()
