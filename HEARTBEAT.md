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

## 🚨 Pendientes urgentes — reportar a Vicci (23 mar 2026)

### 🔴 PRs para mergear — 24 ABIERTOS

| PR | Días | Descripción | Urgencia |
|----|------|-------------|----------|
| [#24](https://github.com/vicci420/ezcontact-sales/pull/24) | 13 | lead-finder site crawl (fix 0 leads bug) | 🔴 CRÍTICO — sin esto, 0 leads/noche |
| [#19](https://github.com/vicci420/ezcontact-sales/pull/19) | 18 | tennis-reservation a master | 🔴 CRÍTICO — cron activo |
| [#25](https://github.com/vicci420/ezcontact-sales/pull/25) | 13 | tennis exit code fix (false errors) | 🔴 Merge con #19 |
| [#27](https://github.com/vicci420/ezcontact-sales/pull/27) | 12 | morning-brief-v2.py | 🟡 Brief WhatsApp-friendly |
| [#26](https://github.com/vicci420/ezcontact-sales/pull/26) | 13 | send-saludtotal-outreach.py | 🟡 Para próximo envío |

> ⚠️ Hay **24 PRs abiertos** — el más viejo tiene **47 días**. Ver: github.com/vicci420/ezcontact-sales/pulls

### 🩺 SaludTotal outreach — sin respuestas
- 68 emails enviados 10 mar CDMX
- **13 días transcurridos**
- Estado: Ya superó umbral típico B2B (7 días)
- **Acción:** Considerar follow-up o cambio de estrategia

### 🔴 TODOS los prospectos con respuesta están PERDIDOS
- **Chopo** (6 mar, 17d): Respuesta automática/genérica — piden "carta presentación como proveedor". No entendieron la propuesta.
- **VETME** (19 feb, 32d): Pidieron llamada que nunca se dio
- **Idiomas CUC** (25 feb, 26d): Elsa pidió que la llamaran
- **TentenPie** (25 feb, 26d): Muy frío
- **Rivalia Estudio** (25 feb, 26d): Muy frío

**Conclusión:** Pipeline de prospectos muerto. Necesitamos leads frescos → mergear PR #24.

### 📱 Signups recientes — 22 mar (2 LATAM nuevos)
**Hoy:**
- 🇦🇷 Rocio cinelli (rocio) — magalirocio38@gmail.com
- 🇨🇴 Eyleen (Enana) — eileensbgl@gmail.com

**Anteriores:**
- 🇲🇽 Yamilet Cañada Avila (Yam) — Hidalgo
- 🇲🇽 Daniela (Sabine) — Puebla
- 🇨🇴 5 signups LATAM más

### ⚠️ Crons con error
- **outreach-9am** — ERROR (solo corre L-V, revisar mañana lunes)

---

## 🌙 Trabajo nocturno completado (23 mar 2026 — 10pm CDMX del 22)

- ✅ Tennis lunes 23: CONFIRMADO — Cancha 1, Folio 156105, 7:00 AM, Mauricio
- ✅ Tennis lunes 24: Cron ejecuta domingo 23 a las 5:59am CDMX
- ✅ Compañero lunes 24: Mauricio Baeza Licón (7606), Cancha preferida: 1
- ✅ 2 signups nuevos detectados (Argentina + Colombia)
- ⚠️ Chopo = respuesta automática, no es interés real
- ⚠️ SaludTotal: 13 días desde envío (10 mar), 0 respuestas
- ⚠️ Lead-finder NO existe en master (PR #24 sin merge) — 0 leads nuevos
- ⚠️ 24 PRs abiertos — PR más viejo: 47 días
- ✅ Memoria escrita: `memory/2026-03-23.md`

### 🔴 Resumen prospectos:
- **TODOS PERDIDOS:** VETME, CUC, TentenPie, Rivalia, Chopo
- **Chopo:** Respuesta automática (no es interés real)
- **Pipeline muerto** — urgente mergear PR #24 para generar leads frescos
