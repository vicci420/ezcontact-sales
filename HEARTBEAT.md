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

## 🚨 Pendientes urgentes — reportar a Vicci (18 mar 2026)

### 🔴 PRs para mergear — 24 ABIERTOS

| PR | Días | Descripción | Urgencia |
|----|------|-------------|----------|
| [#24](https://github.com/vicci420/ezcontact-sales/pull/24) | 8 | lead-finder site crawl (fix 0 leads bug) | 🔴 CRÍTICO — sin esto, 0 leads/noche |
| [#19](https://github.com/vicci420/ezcontact-sales/pull/19) | 13 | tennis-reservation a master | 🔴 CRÍTICO — cron activo |
| [#25](https://github.com/vicci420/ezcontact-sales/pull/25) | 8 | tennis exit code fix (false errors) | 🔴 Merge con #19 |
| [#27](https://github.com/vicci420/ezcontact-sales/pull/27) | 7 | morning-brief-v2.py | 🟡 Brief WhatsApp-friendly |
| [#26](https://github.com/vicci420/ezcontact-sales/pull/26) | 8 | send-saludtotal-outreach.py | 🟡 Para próximo envío |

> ⚠️ Hay **24 PRs abiertos** — el más viejo tiene 42 días. Ver: github.com/vicci420/ezcontact-sales/pulls

### 🩺 SaludTotal outreach — sin respuestas
- 68 emails enviados 10 mar CDMX
- **8 días transcurridos**
- Estado: Ya superó umbral típico B2B (7 días)
- **Acción:** Considerar follow-up o cambio de estrategia

### 🔴 VETME (contacto@vetme.mx) — **27 días esperando** (PERDIDO)
- Respondieron 19 feb: "Con gusto podemos tener una llamada, ¿cuándo?"
- **Lead PERDIDO por abandono**
- **Acción:** Descartar de pipeline activo

### 🔴 Idiomas CUC — **21 días sin respuesta** (FRÍO)
- Elsa pidió el 25 feb: "¿me puedes marcar?"
- Tel de Elsa: **5551892059**
- **Lead perdido — email ya no es suficiente**
- **Acción:** Solo viable si Victor la marca directamente

### 🟡 Otros drafts listos (todos ~20 días)
- TentenPie, Rivalia Estudio, Chopo — necesitan decisión

### 📱 Signups recientes — 17 mar (3 MX, 2 LATAM)
- 🇲🇽 Martinez (Petrolera) — mejor prospecto
- 🇲🇽 Derli rios (Sam snikers)
- 🇲🇽 amelia (Amelia shoes)

### ⚠️ Crons con error
- **outreach-9am** — ERROR (revisar)
- **agua-estirar-7pm** — ERROR (revisar)

---

## 🌙 Trabajo nocturno completado (18 mar 2026 — 10pm CDMX del 17)

- ✅ Tennis: Miércoles 18 mar confirmado — Cancha 3, Folio 155714, Alejandro Navarro (VERIFICADO en TusApartados)
- ✅ 7 respuestas de prospectos pendientes (SIN CAMBIOS — VETME 27d, CUC 21d)
- ✅ 5 signups detectados (3 MX, 2 LATAM)
- ⚠️ SaludTotal: 8 días desde envío (10 mar), 0 respuestas
- ⚠️ Lead-finder NO ejecuta (PR #24 sin merge) — 0 leads nuevos
- ⚠️ 24 PRs abiertos — situación crítica, bloquea automatización
- ⚠️ 2 crons con error: outreach-9am, agua-estirar-7pm
- ✅ Memoria escrita: `memory/2026-03-18.md`

### 🔴 Prospectos con respuesta más antigua:
- VETME: **27 días** esperando (PERDIDO)
- Idiomas CUC: **21 días** esperando (PERDIDO)
- TentenPie / Rivalia / Chopo: ~20 días
