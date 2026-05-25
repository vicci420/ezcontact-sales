#!/usr/bin/env python3
"""
morning-brief.py — Generador automático de Morning Brief EZContact
Corre en el turno nocturno de Katia y produce un archivo listo para Vicci.

Uso: python3 scripts/morning-brief.py
Requiere: archivos en prospectos/pending-followups/ y memory/prospect-alerts.md
"""

import os
import json
import datetime
from pathlib import Path

# ─── Config ───────────────────────────────────────────────────────────────────
WORKSPACE = Path(os.environ.get("WORKSPACE", "/home/ubuntu/clawd"))
FOLLOWUPS_DIR = WORKSPACE / "prospectos" / "pending-followups"
MEMORY_DIR = WORKSPACE / "memory"
OUTPUT_DIR = WORKSPACE / "memory"

# ─── Helpers ──────────────────────────────────────────────────────────────────

def cdmx_now():
    """Retorna datetime en timezone CDMX (UTC-6)."""
    utc = datetime.datetime.utcnow()
    return utc - datetime.timedelta(hours=6)


def day_of_week_es(dt):
    days = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    return days[dt.weekday()]


def load_prospect_alerts():
    """Lee el último archivo de alertas de prospectos."""
    alerts_file = MEMORY_DIR / "prospect-alerts.md"
    if alerts_file.exists():
        return alerts_file.read_text()
    return ""


def load_followup_drafts():
    """Lee los drafts más recientes de follow-ups."""
    if not FOLLOWUPS_DIR.exists():
        return []
    files = sorted(FOLLOWUPS_DIR.glob("reply-drafts-*.md"), reverse=True)
    if files:
        return [(f.name, f.read_text()[:2000]) for f in files[:2]]
    return []


def load_tennis_log():
    """Lee las últimas líneas del log de tennis."""
    tennis_log = MEMORY_DIR / "tennis-log.txt"
    if tennis_log.exists():
        lines = tennis_log.read_text().strip().split("\n")
        return lines[-3:]  # Últimas 3 entradas
    return []


def generate_brief():
    now = cdmx_now()
    day = day_of_week_es(now)
    date_str = now.strftime("%d de %B de %Y")
    tomorrow = now + datetime.timedelta(days=1)
    tomorrow_day = day_of_week_es(tomorrow)

    alerts = load_prospect_alerts()
    drafts = load_followup_drafts()
    tennis = load_tennis_log()

    # Contar respuestas urgentes
    reply_count = alerts.count("RESPUESTAS DIRECTAS") and alerts.count("###")
    is_weekend = now.weekday() >= 5  # Sábado o domingo

    brief = f"""# 🌅 Morning Brief — {day} {date_str}

> Preparado por Katia a las {now.strftime('%I:%M %p')} CDMX

---

## ⚡ TOP PRIORIDADES

"""

    # Extraer prospectos calientes del alerts
    if "IDIOMAS CUC" in alerts and "ELSA" in alerts.upper():
        brief += """### 🔥 1. LLAMAR A ELSA — Idiomas CUC
- **Tel:** 55 5189 2059
- **Status:** Demo hecha el 24 feb. Quiere resolver dudas y cerrar.
- **Acción:** Llamar esta mañana. Alta probabilidad de cierre.

"""
    if "VETME" in alerts:
        brief += """### ⚠️ 2. VETME — Semanas sin respuesta
- **Email:** contacto@vetme.mx
- **Status:** Respondieron el 19 feb queriendo llamada. Sin seguimiento.
- **Acción:** Enviar draft guardado en pending-followups/

"""

    # Tennis
    brief += f"""---

## 🎾 TENNIS HOY
"""
    if tennis:
        last_log = tennis[-1]
        if "OK" in last_log and not is_weekend:
            # Extraer info del último log
            import re
            folio_match = re.search(r'Folio (\d+)', last_log)
            cancha_match = re.search(r'Cancha (\w+)', last_log)
            folio = folio_match.group(1) if folio_match else "—"
            cancha = cancha_match.group(1) if cancha_match else "—"
            brief += f"- **Cancha {cancha} — 7:00 AM** ✅ (Folio {folio})\n\n"
        elif is_weekend:
            brief += "- 🏖️ Fin de semana — sin reservación (descanso merecido)\n\n"
        else:
            brief += f"- ⚠️ Revisar log: {last_log}\n\n"
    else:
        brief += "- Sin datos de tennis disponibles\n\n"

    brief += """---

## 📊 PIPELINE ACTIVO (EZContact)

| Prospecto | Estado | Urgencia |
|-----------|--------|----------|
| Idiomas CUC (Elsa) | CALIENTE — espera llamada | 🔴 HOY |
| VETME | TIBIO — 15+ días sin follow-up | 🟡 URGENTE |
| Rivalia Estudio (Carlos Mena) | Respondió 25 feb | 🟡 Esta semana |
| TentenPie | Demo fallida — reagendar | 🟠 Esta semana |

---

## 🤖 REPOS / PRs PENDIENTES

**Mergear estos PRs en vicci420/ezcontact-sales:**

| # | Descripción | Prioridad |
|---|-------------|-----------|
| 19 | Fix: tennis script a master | 🔴 CRÍTICO |
| 17 | CRM Tracker — visibilidad pipeline | 🟡 Alta |
| 18 | Fix: filtro .mx + blacklist scraper | 🟡 Alta |
| 10 | Contrato EZContact para Elsa | 🟠 Media |

---

## 📋 PROYECTOS ACTIVOS

- **Superlative (Deal 18):** Esperando flow diagram + requerimientos Heineken
- **P1 DNSYS:** Brief en proyectos/P1-dnsys-exoskeleton.md
- **P2 COFEPRIS (Hugo):** Brief en proyectos/P2-cofepris-advisory.md
- **P3 Salud Total:** ⛔ BLOQUEADO — Katia necesita capacitación

---

"""
    brief += f"\n*Generado: {day} {date_str}, {now.strftime('%I:%M %p')} CDMX por morning-brief.py*\n"
    return brief


def main():
    now = cdmx_now()
    date_tag = now.strftime("%Y-%m-%d")
    output_file = OUTPUT_DIR / f"morning-brief-{date_tag}.md"

    print(f"📋 Generando morning brief para {now.strftime('%d/%m/%Y %H:%M')} CDMX...")

    brief = generate_brief()

    output_file.write_text(brief)
    print(f"✅ Brief guardado en: {output_file}")
    print("\n--- PREVIEW ---")
    print(brief[:500])
    print("...")


if __name__ == "__main__":
    main()
