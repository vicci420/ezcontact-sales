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

## 🚨 Pendientes urgentes — reportar a Vicci (26 mar 2026)

### ✅ Tennis jueves 26 — CONFIRMADO
- Cancha 8, 7:00 AM, Rafael Quezada Garcia (7597)
- Folio: 156312
- Verificado ayer en Tus Apartados ✅

### 🔴 PRs para mergear — 25 ABIERTOS

| PR | Días | Descripción | Urgencia |
|----|------|-------------|----------|
| [#28](https://github.com/vicci420/ezcontact-sales/pull/28) | 1 | tennis verify fix (false positives) | 🔴 Merge ASAP |
| [#24](https://github.com/vicci420/ezcontact-sales/pull/24) | 16 | lead-finder site crawl (fix 0 leads bug) | 🔴 Sin esto = 0 leads/noche |
| [#19](https://github.com/vicci420/ezcontact-sales/pull/19) | 21 | tennis-reservation a master | 🔴 Cron activo |
| [#25](https://github.com/vicci420/ezcontact-sales/pull/25) | 16 | tennis exit code fix | 🔴 Merge con #19 |
| [#27](https://github.com/vicci420/ezcontact-sales/pull/27) | 15 | morning-brief-v2.py | 🟡 Nice to have |
| [#26](https://github.com/vicci420/ezcontact-sales/pull/26) | 16 | send-saludtotal-outreach.py | 🟡 Para próximo envío |

> ⚠️ Hay **25 PRs abiertos** — el más viejo tiene **50 días**. Ver: github.com/vicci420/ezcontact-sales/pulls

### 🩺 SaludTotal outreach — sin respuestas
- 68 emails enviados 10 mar CDMX
- **16 días transcurridos** — campaña fallida
- **Acción:** Considerar nueva estrategia o follow-up diferente

### 🔴 TODOS los prospectos con respuesta están PERDIDOS
- **Chopo** (20d), **VETME** (35d), **Idiomas CUC** (29d), **TentenPie** (29d), **Rivalia** (29d)

**Pipeline comercial muerto.** Urgente mergear PR #24 para generar leads frescos.

### 📱 Signups recientes — 25 mar (8 nuevos)
- 🇲🇽 **Adalberto** (Eliasguangle) — wa.me/526623678227
- 🇲🇽 **Domingo Reyes López** (UDU) — wa.me/524521340083
- 🇨🇴 4 signups Colombia
- 🇨🇱 1 signup Chile
- 🇦🇷 1 signup Argentina

### ✅ Crons OK
- Todos los crons reportan status `ok` al 26 mar

---

## 🌙 Trabajo nocturno completado (26 mar 2026 — 10pm CDMX del 25)

### ✅ Tennis jueves 26 — CONFIRMADO
- Cancha 8, Folio 156312, Rafael Quezada
- Verificado ayer

### ✅ Trabajo completado:
- 8 signups detectados (2 MX + 6 LATAM)
- 7 respuestas prospectos verificadas (todos perdidos >20 días)
- Pipeline actualizado: `prospectos/pipeline-ezcontact.md`
- Emails revisados: sin urgentes (solo newsletters)
- Memoria escrita: `memory/2026-03-26.md`

### 📱 Signups MX listos para seguimiento:
- Adalberto (Eliasguangle) — adalbertomazonurias@gmail.com — wa.me/526623678227
- Domingo Reyes López (UDU) — jesusenriquereyesrangel29@gmail.com — wa.me/524521340083
- Cristopher Lazarini (Nutela, ayer) — wa.me/522221742641
- Antonia Aldama (Novedades romina, ayer) — wa.me/526311105295
