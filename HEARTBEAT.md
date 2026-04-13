# HEARTBEAT.md

## Chequeos obligatorios cada heartbeat

### 🔴 Monitoreo de Cron Jobs (CRÍTICO)
Verificar que los recordatorios se estén ejecutando:
1. Correr `cron list` 
2. Si algún job tiene `lastRunAtMs` > 24 horas atrás → ALERTAR a Vicci inmediatamente
3. No asumir que "todo está bien" — verificar datos reales

### 🔴 Verificación de Reservaciones Tennis (CRÍTICO)
Después de cualquier reservación de tennis:
1. SIEMPRE verificar en TusApartadosCelular.php que la reserva EXISTE
2. NO reportar éxito hasta confirmar que aparece en el sistema
3. Si no aparece → la reservación NO se hizo, sin importar lo que dijo el script

## 🌙 Trabajo nocturno automático (10pm-6am CDMX)

1. **Detección de respuestas:** Correr `python3 scripts/prospect-reply-detector.py` — detecta prospectos que respondieron
2. **Prospección:** Correr `python3 scripts/lead-finder-dynamic.py` — busca emails nuevos en verticales definidas
3. **Signups:** Correr `python3 scripts/new-signup-tracker.py` — detecta nuevos registros EZContact
4. **🔴 NUNCA enviar correos de noche** — solo guardar leads en archivo
5. **Registrar en** `memory/YYYY-MM-DD.md` cuántos leads encontrados y listos para enviar
6. **NO agregar a ClickUp de noche** — esperar confirmación de envío

⚠️ Instrucción de Vicci (21 feb 2026): Los correos de outreach los envía Vicci manualmente o mediante cron de 9am CDMX cuando él lo apruebe. KATIA NO ENVÍA CORREOS DE OUTREACH SOLA.

---

## 🚨 Pendientes urgentes — reportar a Vicci (13 abr 2026)

### 🎾 Tennis
**⚠️ Cada fin de semana:** Preguntarle a Vicci con quién juega la próxima semana y actualizar TOOLS.md

**Semana 14-18 abril:**
- Lunes: Mauricio Baeza (7606) ✅ ya reservado
- Martes: Alejandro Navarro (6525)
- Miércoles: Yanel (7436)
- Jueves: Bruno Palomino (7600)
- Viernes: Carlos Toledo (7238)

### 🔴 PRs para mergear — 25 ABIERTOS (68 días el más viejo)

| PR | Días | Descripción | Urgencia |
|----|------|-------------|----------|
| [#24](https://github.com/vicci420/ezcontact-sales/pull/24) | 34 | lead-finder site crawl (fix 0 leads bug) | 🔴 Sin esto = 0 leads/noche |
| [#28](https://github.com/vicci420/ezcontact-sales/pull/28) | 19 | tennis verify fix (false positives) | 🟡 Estabilidad |
| [#25](https://github.com/vicci420/ezcontact-sales/pull/25) | 34 | tennis exit code fix | 🟡 Crons marcan "error" |
| [#19](https://github.com/vicci420/ezcontact-sales/pull/19) | 39 | tennis-reservation a master | 🟡 Script estable |

> ⚠️ **25 PRs abiertos** — el más viejo tiene **68 días**. Ver: github.com/vicci420/ezcontact-sales/pulls

### 🩺 SaludTotal outreach — campaña fallida
- 68 emails enviados 10 mar CDMX
- **34 días transcurridos** — 0 respuestas
- **Acción:** Nueva estrategia necesaria

### 🔴 Pipeline comercial MUERTO
Prospectos con respuesta perdidos (>20 días sin seguimiento):
- Chopo, VETME, Idiomas CUC, TentenPie, Rivalia

**Sin leads frescos hasta merge de PR #24.**

### 📱 Signups MX recientes (6-7 abril)
- 🇲🇽 **Gabriela** (Gabriela) — wa.me/526143453699 ⭐ NUEVO
- 🇲🇽 **Pablo** (Fresa) — wa.me/527271005206 ⭐ NUEVO

### ✅ Crons
- tennis/morning-brief marcan "error" pero funcionan (bug exit code PR #25)
- babypool-notify, meditacion-9pm, trabajo-nocturno: OK

---

## 🌙 Trabajo nocturno completado (13 abr 2026 — 10pm CDMX del 12 abr)

### ✅ Trabajo completado:
- 1 signup nuevo detectado (Lautaro, Argentina)
- 7 respuestas prospectos verificadas (todos perdidos >30 días, sin cambios)
- Memoria escrita: `memory/2026-04-13.md`
- Lead-finder: sigue bloqueado (PR #24 pendiente merge — **34 días**)
- 25 PRs abiertos (**68 días el más viejo**)

### 📱 Signups MX pendientes seguimiento:
1. **Karla** (Bazar karly) — wa.me/527821975137 🇲🇽 11 abr
2. **auttec** (auttec) — wa.me/527721616547 🇲🇽 10 abr
3. **Jose Lopez** (Viajes Carrillo) — wa.me/526633242086 🇲🇽 10 abr

### 📱 Signup LATAM nuevo:
- 🇦🇷 **Lautaro** (mágico) — wa.me/5491122872837 12 abr
