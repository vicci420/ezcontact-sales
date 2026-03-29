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

## 🚨 Pendientes urgentes — reportar a Vicci (29 mar 2026)

### 🏖️ Fin de semana — no hay tennis
- Domingo 29 mar: No hay reservación (hoy)
- **Próxima reservación:** Lunes 31 mar (cron 5:59am CDMX)

### 🔴 Signup MX prioritario — Hotel Westin
- **Juan Gabriel** — wa.me/525573975683
- Signup 28 mar — lead B2B potencialmente alto valor

### 🔴 PRs para mergear — 25 ABIERTOS

| PR | Días | Descripción | Urgencia |
|----|------|-------------|----------|
| [#28](https://github.com/vicci420/ezcontact-sales/pull/28) | 3 | tennis verify fix (false positives) | 🔴 Merge ASAP |
| [#24](https://github.com/vicci420/ezcontact-sales/pull/24) | 18 | lead-finder site crawl (fix 0 leads bug) | 🔴 Sin esto = 0 leads/noche |
| [#19](https://github.com/vicci420/ezcontact-sales/pull/19) | 23 | tennis-reservation a master | 🔴 Cron activo |
| [#25](https://github.com/vicci420/ezcontact-sales/pull/25) | 18 | tennis exit code fix | 🔴 Merge con #19 |
| [#27](https://github.com/vicci420/ezcontact-sales/pull/27) | 17 | morning-brief-v2.py | 🟡 Nice to have |
| [#26](https://github.com/vicci420/ezcontact-sales/pull/26) | 18 | send-saludtotal-outreach.py | 🟡 Para próximo envío |

> ⚠️ Hay **25 PRs abiertos** — el más viejo tiene **52 días**. Ver: github.com/vicci420/ezcontact-sales/pulls

### 🩺 SaludTotal outreach — sin respuestas
- 68 emails enviados 10 mar CDMX
- **18 días transcurridos** — campaña fallida
- **Acción:** Considerar nueva estrategia o follow-up diferente

### 🔴 TODOS los prospectos con respuesta están PERDIDOS
- **Chopo** (22d), **VETME** (37d), **Idiomas CUC** (31d), **TentenPie** (31d), **Rivalia** (31d)

**Pipeline comercial muerto.** Urgente mergear PR #24 para generar leads frescos.

### 📱 Signups recientes — 27 mar (6 nuevos)
- 🇲🇽 **Alma Corral** (Fuller) — amircano018@gmail.com
- 🇨🇱 Bella Millar (Camique) — +56986822986
- 🇨🇴 Beatriz López — +573225427699
- 🇻🇪 Victor Acosta (Anavic) — +584146050739
- 🇨🇴 Samary (Inguenser) — +523105799874
- 🇦🇷 Romeo (romefutstore_) — +541150222025

### ✅ Crons OK
- Todos los crons reportan status `ok` al 28 mar

---

## 🌙 Trabajo nocturno completado (29 mar 2026 — 10pm CDMX del 28)

### ✅ Trabajo completado:
- 5 signups detectados (2 MX + 3 LATAM)
- 7 respuestas prospectos verificadas (todos perdidos >20 días)
- Emails revisados: sin urgentes
- Memoria escrita: `memory/2026-03-29.md`
- Seguimientos actualizados: `memory/seguimientos-activos.md`
- Lead-finder: bloqueado (PR #24 pendiente merge)

### 📱 Signups MX para seguimiento:
1. **Juan Gabriel — Hotel Westin** (28 mar) — wa.me/525573975683 ⭐
2. Alma Corral — Fuller (27 mar) — wa.me/526181539933
