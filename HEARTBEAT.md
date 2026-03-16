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

## 🚨 Pendientes urgentes — reportar a Vicci (14 mar 2026)

### 🔴 PRs para mergear — 24 ABIERTOS

| PR | Días | Descripción | Urgencia |
|----|------|-------------|----------|
| [#24](https://github.com/vicci420/ezcontact-sales/pull/24) | 6 | lead-finder site crawl (fix 0 leads bug) | 🔴 CRÍTICO — sin esto, 0 leads/noche |
| [#19](https://github.com/vicci420/ezcontact-sales/pull/19) | 11 | tennis-reservation a master | 🔴 CRÍTICO — cron activo |
| [#25](https://github.com/vicci420/ezcontact-sales/pull/25) | 6 | tennis exit code fix (false errors) | 🔴 Merge con #19 |
| [#27](https://github.com/vicci420/ezcontact-sales/pull/27) | 5 | morning-brief-v2.py | 🟡 Brief WhatsApp-friendly |
| [#26](https://github.com/vicci420/ezcontact-sales/pull/26) | 6 | send-saludtotal-outreach.py | 🟡 Para próximo envío |

> ⚠️ Hay **24 PRs abiertos** — el más viejo tiene 40 días. Ver: github.com/vicci420/ezcontact-sales/pulls

### 🩺 SaludTotal outreach — sin respuestas
- 68 emails enviados 10 mar CDMX
- **6 días transcurridos** (144+ horas)
- Estado: preocupante pero no alarmante para B2B médico
- Siguiente check: miércoles 18 marzo (si 0 respuestas, considerar follow-up)

### 🔴 VETME (contacto@vetme.mx) — **25 días esperando**
- Respondieron 19 feb: "Con gusto podemos tener una llamada, ¿cuándo?"
- Draft: `prospectos/pending-replies/vetme-reply-2026-03-07.md`
- **Lead frío por abandono** — necesita reactivación urgente
- **Acción:** ¿Aprueba Vicci enviar disculpa + proponer fecha?

### 🔴 Idiomas CUC — **19 días sin respuesta**
- Elsa pidió el 25 feb: "¿me puedes marcar?" o "dame tu teléfono"
- Draft listo: `prospectos/pending-replies/idiomascuc-callback-2026-03-11.md`
- Tel de Elsa: **5551892059** (también 5551892058)
- **Lead caliente** — ya pasó por demo, tiene dudas puntuales
- **Acción:** ¿Victor la marca directamente? El email ya no es suficiente.

### 🟡 Otros drafts listos
- TentenPie: `prospectos/pending-replies/tentenpie-reagendar-2026-03-07.md`
- Rivalia Estudio: `prospectos/pending-replies/rivalia-estudio-2026-03-08.md`
- Chopo: `prospectos/pending-replies/chopo-reencuadre-2026-03-09.md`

### 📱 Signups recientes — 15 mar (3 MX, 2 LATAM)
- 🇲🇽 **Elida Sosa** (Miscelánea y gorditas Niky) — juame1987@gmail.com | +528421161419 ⭐ NEGOCIO REAL
- 🇲🇽 **David Cantera** (Papus) — canteradavid26@gmail.com | +529516542200 ⭐ POTENCIAL
- 🇲🇽 Claudia Georgina Ávila — cgeorgina6@hotmail.com | +523310004965
- 🇨🇴 jesusperoso, Marileza (Barbería chop)

### ⚠️ Zapier error — Untitled Zap fallando
- Error: `(#132001) Template name does not exist in the translation`
- **Acción:** Revisar https://zapier.com/editor/353006109/published

---

## 🌙 Trabajo nocturno completado (16 mar 2026 — 10pm CDMX del 15)

- ✅ Tennis: Lunes 16 mar confirmado — Cancha 1, Folio 155635, Mauricio Baeza
- ✅ 7 respuestas de prospectos pendientes (sin cambios desde hace días)
- ✅ 5 signups detectados (3 MX, 2 LATAM) — Elida Sosa + David Cantera mejores leads
- ⚠️ SaludTotal: 6 días desde envío (10 mar), 0 respuestas detectadas
- ⚠️ Lead-finder NO ejecuta (PR #24 sin merge) — 0 leads nuevos
- ⚠️ 24 PRs abiertos — situación crítica, bloquea automatización
- ✅ Memoria escrita: `memory/2026-03-16.md`

### 🔴 Prospectos con respuesta más antigua:
- VETME: **25 días** esperando
- Idiomas CUC: **19 días** esperando
- TentenPie / Rivalia / Chopo: 10-19 días
