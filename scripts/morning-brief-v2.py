#!/usr/bin/env python3
"""
morning-brief-v2.py — Brief matutino para Vicci via OpenClaw

Genera un resumen ejecutivo del pipeline y lo entrega a Vicci
en su canal de mensajería.

Cron sugerido: 6:00 AM CDMX (12:00 UTC)
"""

import os
import json
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
import re

WORKSPACE = Path(os.environ.get("WORKSPACE", "/home/ubuntu/clawd"))
MEMORY_DIR = WORKSPACE / "memory"
PENDING_REPLIES_DIR = WORKSPACE / "prospectos" / "pending-replies"

# UTC-6 para CDMX
def cdmx_now():
    return datetime.utcnow() - timedelta(hours=6)

def day_es(dt):
    days = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    return days[dt.weekday()]

def is_weekend(dt):
    return dt.weekday() >= 5

# ─── Sección: Tennis ───────────────────────────────────────────────────────────
def get_tennis_status():
    log = MEMORY_DIR / "tennis-log.txt"
    if not log.exists():
        return "⚠️ Sin datos de tennis"
    lines = log.read_text().strip().split("\n")
    # Find last non-SKIP entry
    relevant = [l for l in lines if "OK" in l or "FAIL" in l]
    if relevant:
        last = relevant[-1]
        if "OK" in last:
            # Extract folio and court
            folio_m = re.search(r'Folio (\d+)', last)
            cancha_m = re.search(r'Cancha (\d+)', last)
            fecha_m = re.search(r'(\d{4}-\d{2}-\d{2})', last)
            folio = folio_m.group(1) if folio_m else "?"
            cancha = cancha_m.group(1) if cancha_m else "?"
            fecha = fecha_m.group(1) if fecha_m else "?"
            return f"✅ Cancha {cancha} — 7am — Folio {folio}"
        elif "FAIL" in last:
            return "❌ FALLO — Sin reservación. Revisar urgente."
    return "⚠️ Sin reservación reciente"

# ─── Sección: Respuestas de prospectos ────────────────────────────────────────
def get_pending_replies():
    if not PENDING_REPLIES_DIR.exists():
        return []
    
    drafts = []
    for f in sorted(PENDING_REPLIES_DIR.glob("*.md")):
        content = f.read_text()
        # Extract key info from H1 title or filename
        title_m = re.search(r'^#\s+Draft\s+(.+)', content, re.MULTILINE)
        para_m = re.search(r'\*\*Para:\*\*\s*(.+)', content)
        
        if title_m:
            name = title_m.group(1).strip()
        else:
            # Clean up filename
            stem = f.stem
            stem = re.sub(r'-\d{4}-\d{2}-\d{2}$', '', stem)
            name = stem.replace("-", " ").title()
        
        para = para_m.group(1).strip() if para_m else name
        
        # Extract empresa/contact from title
        empresa_m = re.search(r'(?:—|–)\s*(.+?)(?:\n|$)', name)
        empresa = empresa_m.group(1).strip() if empresa_m else name
        
        drafts.append({
            "file": f.name,
            "para": para,
            "empresa": empresa,
        })
    return drafts

# ─── Sección: Signups nuevos ───────────────────────────────────────────────────
def get_new_signups():
    today = cdmx_now().strftime("%Y-%m-%d")
    yesterday = (cdmx_now() - timedelta(days=1)).strftime("%Y-%m-%d")
    
    seen_emails = set()
    signups = []
    for fname in [f"signups-{today}.json", f"signups-{yesterday}.json"]:
        fpath = MEMORY_DIR / fname
        if fpath.exists():
            try:
                data = json.loads(fpath.read_text())
                items = data if isinstance(data, list) else data.get("signups", [])
                for item in items:
                    email = item.get("email", "")
                    if email and email not in seen_emails:
                        seen_emails.add(email)
                        signups.append(item)
            except:
                pass
    return signups

# ─── Sección: PRs pendientes ───────────────────────────────────────────────────
def get_critical_prs():
    try:
        result = subprocess.run(
            ["gh", "pr", "list", "--repo", "vicci420/ezcontact-sales", 
             "--state", "open", "--limit", "100", "--json", "number,title"],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode == 0:
            prs = json.loads(result.stdout)
            return prs
    except:
        pass
    return []

# ─── Sección: Leads generados ─────────────────────────────────────────────────
def get_leads_summary():
    today = cdmx_now().strftime("%Y-%m-%d")
    count = 0
    
    # Check directory leads
    generated = WORKSPACE / "prospectos" / "generated"
    if generated.exists():
        for f in generated.glob(f"*{today}*.csv"):
            try:
                lines = f.read_text().strip().split("\n")
                count += max(0, len(lines) - 1)  # minus header
            except:
                pass
    
    # Check saludtotal
    st_file = WORKSPACE / "prospectos" / f"saludtotal-prospects-{today}.json"
    if st_file.exists():
        try:
            data = json.loads(st_file.read_text())
            count += len([l for l in data if l.get("email","") and "@" in l.get("email","") 
                         and "sentry" not in l.get("email","").lower()])
        except:
            pass
    
    return count

# ─── Generador principal ───────────────────────────────────────────────────────
def generate_brief():
    now = cdmx_now()
    dia = day_es(now)
    fecha = now.strftime("%d %b %Y")
    
    tennis = get_tennis_status()
    replies = get_pending_replies()
    prs = get_critical_prs()
    leads = get_leads_summary()
    
    # Detect if it's a work day
    is_work = not is_weekend(now)
    
    lines = []
    lines.append(f"🌅 *Buenos días Vicci* — {dia} {fecha}")
    lines.append("")
    
    # Tennis
    if is_work:
        lines.append(f"🎾 *Tennis hoy:* {tennis}")
        lines.append("")
    
    # Prioridades — Drafts pendientes
    lines.append("⚡ *Drafts pendientes de tu OK:*")
    lines.append("")
    
    if replies:
        for i, r in enumerate(replies, 1):
            empresa = r.get("empresa") or r.get("para", "?")
            lines.append(f"  {i}. {empresa}")
        lines.append("")
    else:
        lines.append("✅ Sin drafts pendientes")
        lines.append("")
    
    # PRs
    if prs:
        pr_count = len(prs)
        lines.append(f"📦 *PRs sin mergear:* {pr_count}")
        lines.append(f"  → github.com/vicci420/ezcontact-sales/pulls")
        lines.append("")
    
    # Leads
    if leads > 0:
        lines.append(f"🔍 *Leads generados anoche:* {leads}")
        lines.append("")
    
    # Signups
    signups = get_new_signups()
    if signups:
        lines.append(f"📱 *Signups nuevos ({len(signups)}):*")
        for s in signups[:3]:
            name = s.get("name") or s.get("nombre", "?")
            email = s.get("email", "")
            flag = s.get("flag", "")
            lines.append(f"  {flag} {name} — {email}")
        lines.append("")
    
    lines.append("_Que tengas buen día_ 🎯")
    
    return "\n".join(lines)


if __name__ == "__main__":
    brief = generate_brief()
    print(brief)
    
    # If --send flag is provided, send via openclaw
    if "--send" in sys.argv:
        import subprocess
        # Save to temp file for sending
        tmp = "/tmp/morning-brief-output.txt"
        with open(tmp, "w") as f:
            f.write(brief)
        print(f"\n[Brief saved to {tmp}]")
        print("[Use: openclaw message send --to vicci --text \"$(cat /tmp/morning-brief-output.txt)\"]")
