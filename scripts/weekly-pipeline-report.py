#!/usr/bin/env python3
"""
weekly-pipeline-report.py — Reporte semanal de pipeline EZContact
Corre cada lunes a las 6am CDMX para dar a Vicci el panorama de la semana.

Fuentes:
- prospectos/crm-state.json (cuando exista)
- memory/prospect-alerts.md (detección de respuestas)
- prospectos/leads-dynamic-*.json (leads scrapeados)
- memory/tennis-log.txt (estado del cron tennis)
- memory/*.md de la semana pasada
"""

import json
import os
import sys
import glob
from datetime import datetime, timedelta, timezone
import subprocess

# CDMX is UTC-6 (standard) / UTC-5 (DST). Using fixed offset for simplicity.
CDMX_OFFSET = timedelta(hours=-6)
CDMX_TZ = timezone(CDMX_OFFSET)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROSPECTOS_DIR = os.path.join(BASE_DIR, "prospectos")
MEMORY_DIR = os.path.join(BASE_DIR, "memory")
PENDING_DIR = os.path.join(PROSPECTOS_DIR, "pending-replies")

now_utc = datetime.now(timezone.utc)
now_cdmx = now_utc.astimezone(CDMX_TZ)
today = now_cdmx.date()
week_start = today - timedelta(days=7)


def load_leads_last_week():
    """Cuenta cuántos leads generamos esta semana."""
    total = 0
    by_day = {}
    for f in sorted(glob.glob(os.path.join(PROSPECTOS_DIR, "leads-dynamic-*.json"))):
        date_str = os.path.basename(f).replace("leads-dynamic-", "").replace(".json", "")
        try:
            d = datetime.strptime(date_str, "%Y-%m-%d").date()
            if week_start <= d <= today:
                with open(f) as fh:
                    leads = json.load(fh)
                count = len(leads)
                total += count
                by_day[date_str] = count
        except Exception:
            continue
    return total, by_day


def load_pending_replies():
    """Lee todos los drafts pendientes de aprobación."""
    drafts = []
    if not os.path.isdir(PENDING_DIR):
        return drafts
    for f in sorted(glob.glob(os.path.join(PENDING_DIR, "*.md"))):
        name = os.path.basename(f).replace(".md", "")
        with open(f) as fh:
            content = fh.read()
        # Extract company name from filename
        company = name.replace("-", " ").replace("reply", "").replace("reagendar", "").strip()
        # Check for email address in content
        email = ""
        for line in content.split("\n"):
            if "@" in line and "katia" not in line.lower() and "victor" not in line.lower():
                email = line.strip().split()[-1] if " " in line else line.strip()
                break
        drafts.append({"file": name, "company": company, "email": email})
    return drafts


def count_new_ezcontact_users():
    """Intenta contar registros recientes en EZContact via himalaya."""
    try:
        result = subprocess.run(
            ["himalaya", "envelope", "list", "-a", "ezcontact", "-n", "20"],
            capture_output=True, text=True, timeout=15
        )
        lines = result.stdout.split("\n")
        count = sum(1 for line in lines if "Bienvenido a EZContact" in line)
        return count
    except Exception:
        return 0


def load_prospect_alerts():
    """Lee el archivo de alertas de prospectos más reciente."""
    alert_file = os.path.join(MEMORY_DIR, "prospect-alerts.md")
    if not os.path.exists(alert_file):
        return 0, []
    
    with open(alert_file) as fh:
        content = fh.read()
    
    replies = []
    in_replies = False
    for line in content.split("\n"):
        if "RESPUESTAS DIRECTAS" in line:
            in_replies = True
        elif "VERIFICACIONES" in line or "OTROS" in line:
            in_replies = False
        elif in_replies and line.startswith("### "):
            company = line.replace("### ", "").strip()
            replies.append(company)
    
    return len(replies), replies


def load_tennis_status():
    """Lee el log de tennis para verificar estado del cron."""
    log_file = os.path.join(MEMORY_DIR, "tennis-log.txt")
    if not os.path.exists(log_file):
        return "desconocido"
    
    with open(log_file) as fh:
        lines = fh.readlines()
    
    recent = [l.strip() for l in lines if l.strip()][-5:]
    last = recent[-1] if recent else ""
    
    if "OK" in last:
        return "✅ OK"
    elif "SKIP" in last and "weekend" in last.lower():
        return "⏭️ Fin de semana (normal)"
    elif "FAIL" in last or "ERROR" in last:
        return "🔴 ERROR"
    return f"ℹ️ {last[:80]}"


def count_open_prs():
    """Cuenta PRs abiertos en el repo."""
    try:
        result = subprocess.run(
            ["gh", "pr", "list", "--repo", "vicci420/ezcontact-sales",
             "--state", "open", "--json", "number"],
            capture_output=True, text=True, timeout=15
        )
        prs = json.loads(result.stdout)
        return len(prs)
    except Exception:
        return -1


def generate_report():
    """Genera el reporte semanal completo."""
    print(f"📊 Generando reporte semanal ({today.strftime('%d/%m/%Y')})...")

    # Recolectar datos
    total_leads, leads_by_day = load_leads_last_week()
    pending_drafts = load_pending_replies()
    new_users = count_new_ezcontact_users()
    num_replies, reply_list = load_prospect_alerts()
    tennis_status = load_tennis_status()
    open_prs = count_open_prs()

    # Calcular promedio diario de leads
    days_with_leads = len(leads_by_day)
    avg_leads = total_leads / max(days_with_leads, 1)

    # Día de la semana para el saludo
    day_name = now_cdmx.strftime("%A")
    day_es = {
        "Monday": "Lunes", "Tuesday": "Martes", "Wednesday": "Miércoles",
        "Thursday": "Jueves", "Friday": "Viernes", "Saturday": "Sábado",
        "Sunday": "Domingo"
    }.get(day_name, day_name)
    
    month_es = {
        "January": "enero", "February": "febrero", "March": "marzo",
        "April": "abril", "May": "mayo", "June": "junio",
        "July": "julio", "August": "agosto", "September": "septiembre",
        "October": "octubre", "November": "noviembre", "December": "diciembre"
    }.get(now_cdmx.strftime("%B"), now_cdmx.strftime("%B"))

    lines = []
    lines.append(f"# 📊 Pipeline Semanal — {day_es} {today.day} de {month_es} de {today.year}")
    lines.append(f"\n> Generado por Katia · {now_cdmx.strftime('%H:%M')} CDMX\n")

    # === RESUMEN EJECUTIVO ===
    lines.append("---\n## ⚡ RESUMEN EJECUTIVO\n")
    
    urgentes = []
    if pending_drafts:
        urgentes.append(f"- 📨 **{len(pending_drafts)} respuestas de prospectos** esperando aprobación de Vicci")
    if num_replies > 0:
        urgentes.append(f"- 🎯 **{num_replies} respuestas** activas detectadas en inbox")
    if open_prs > 10:
        urgentes.append(f"- 🔧 **{open_prs} PRs** acumulados — semana ideal para mergear")
    
    if urgentes:
        for u in urgentes:
            lines.append(u)
    else:
        lines.append("✅ Sin alertas urgentes esta semana.")

    # === LEADS PIPELINE ===
    lines.append(f"\n---\n## 🔥 LEADS — Semana {week_start.strftime('%d/%m')} al {today.strftime('%d/%m')}\n")
    lines.append(f"**Total generados:** {total_leads} leads\n")
    lines.append(f"**Promedio diario:** {avg_leads:.0f} leads/día\n")
    
    if leads_by_day:
        lines.append("**Por día:**")
        for day, count in sorted(leads_by_day.items()):
            bar = "█" * min(count // 5, 20)
            lines.append(f"  - {day}: {count:3d} {bar}")
    
    lines.append(f"\n📤 **Listos para enviar esta semana:** Pendiente de autorización Vicci")

    # === PROSPECTOS CON RESPUESTA ===
    lines.append(f"\n---\n## 💬 PROSPECTOS ACTIVOS ({num_replies} con respuesta)\n")
    
    if reply_list:
        for r in reply_list:
            lines.append(f"- {r}")
    else:
        lines.append("*(No hay respuestas detectadas)*")

    # === DRAFTS PENDIENTES ===
    if pending_drafts:
        lines.append(f"\n---\n## 📝 DRAFTS PENDIENTES APROBACIÓN ({len(pending_drafts)})\n")
        for d in pending_drafts:
            lines.append(f"- **{d['company']}** — `{d['file']}.md`")
        lines.append(f"\n_Ver carpeta: `prospectos/pending-replies/`_")

    # === NUEVOS USUARIOS EZCONTACT ===
    lines.append(f"\n---\n## 🆕 NUEVOS USUARIOS EZCONTACT\n")
    lines.append(f"**Esta semana:** ~{new_users} registros detectados en inbox katia@ezcontact.mx")
    lines.append(f"\n_Para número exacto: revisar app.ezcontact.ai → Usuarios_")

    # === ESTADO TÉCNICO ===
    lines.append(f"\n---\n## 🔧 ESTADO TÉCNICO\n")
    lines.append(f"- 🎾 **Tennis cron:** {tennis_status}")
    lines.append(f"- 📋 **PRs abiertos:** {open_prs if open_prs >= 0 else 'N/A'}")
    
    if open_prs > 10:
        lines.append(f"  > ⚠️ Muchos PRs acumulados. Recomiendo mergear esta semana en orden:")
        lines.append(f"  > #19 (tennis) → #18 (scraper) → #17 (crm) → #21 (reply-digest) → resto")

    # === RECOMENDACIONES SEMANA ===
    lines.append(f"\n---\n## 🎯 PRIORIDADES ESTA SEMANA\n")
    
    prioridades = []
    if num_replies > 0:
        prioridades.append("1. **Responder prospectos activos** — calor se enfría rápido")
    if pending_drafts:
        prioridades.append(f"2. **Aprobar {len(pending_drafts)} drafts** — ya están listos, solo falta OK")
    if open_prs > 5:
        prioridades.append(f"3. **Mergear PRs** — empezar por #19 (tennis)")
    prioridades.append("4. **Prospección** — aprobar envío batch semanal de leads")
    
    for p in prioridades:
        lines.append(p)

    lines.append(f"\n---")
    lines.append(f"*Próximo reporte: lunes {(today + timedelta(days=7)).strftime('%d/%m/%Y')} 6am CDMX*")

    return "\n".join(lines)


def main():
    report = generate_report()
    
    # Guardar en memory
    out_file = os.path.join(MEMORY_DIR, f"weekly-report-{today.strftime('%Y-%m-%d')}.md")
    with open(out_file, "w") as fh:
        fh.write(report)
    
    print(f"\n✅ Reporte guardado: {out_file}")
    print(f"\n--- PREVIEW ---")
    print(report[:1500])
    print("...")
    
    return out_file


if __name__ == "__main__":
    main()
