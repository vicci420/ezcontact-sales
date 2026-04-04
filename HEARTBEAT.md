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

## 🚨 Pendientes urgentes — reportar a Vicci (4 abr 2026)

### 🎾 Tennis
- ✅ Viernes 3 abril: Folio 156908, Cancha 3, 7am — OK
- Sábado/domingo: No hay tennis
- Próximo: Lunes 7 abril (cron lo reservará domingo 6 abril 6am)

### 🔴 Signup MX prioritario — Hotel Westin
- **Juan Gabriel** — wa.me/525573975683
- Signup 28 mar — lead B2B potencialmente alto valor

### 🔴 PRs para mergear — 25 ABIERTOS

| PR | Días | Descripción | Urgencia |
|----|------|-------------|----------|
| [#28](https://github.com/vicci420/ezcontact-sales/pull/28) | 7 | tennis verify fix (false positives) | 🔴 Merge ASAP |
| [#24](https://github.com/vicci420/ezcontact-sales/pull/24) | 22 | lead-finder site crawl (fix 0 leads bug) | 🔴 Sin esto = 0 leads/noche |
| [#19](https://github.com/vicci420/ezcontact-sales/pull/19) | 27 | tennis-reservation a master | 🔴 Cron activo |
| [#25](https://github.com/vicci420/ezcontact-sales/pull/25) | 22 | tennis exit code fix | 🔴 Merge con #19 |
| [#27](https://github.com/vicci420/ezcontact-sales/pull/27) | 21 | morning-brief-v2.py | 🟡 Nice to have |
| [#26](https://github.com/vicci420/ezcontact-sales/pull/26) | 22 | send-saludtotal-outreach.py | 🟡 Para próximo envío |

> ⚠️ Hay **25 PRs abiertos** — el más viejo tiene **56 días**. Ver: github.com/vicci420/ezcontact-sales/pulls

### 🩺 SaludTotal outreach — sin respuestas
- 68 emails enviados 10 mar CDMX
- **21 días transcurridos** — campaña fallida
- **Acción:** Considerar nueva estrategia o follow-up diferente

### 🔴 TODOS los prospectos con respuesta están PERDIDOS
- **Chopo** (25d), **VETME** (40d), **Idiomas CUC** (34d), **TentenPie** (34d), **Rivalia** (34d)

**Pipeline comercial muerto.** Urgente mergear PR #24 para generar leads frescos.

### 📱 Signups recientes — 3-4 abr (7 en 2 días)
- 🇦🇷 leon (leon) — +522901557040 ⭐ NUEVO
- 🇦🇷 Eliana (Quiero empezar a promocionar) — +541130189929 ⭐ NUEVO
- 🇨🇴 María Paula (Kira Bot) — +573150112845
- 🇲🇽 **Maria** (Propio) — +529171277042 ⭐ NUEVO MX
- 🇲🇽 **Graciela** (Novedades chely) — +5244431320243 ⭐ MX
- 🇲🇽 **Manuel Enrique** (Produtos a domicilio) — +529961054780 ⭐ MX
- 🇨🇴 Luisa Maria (Hortalizas) — +573171348734

### ✅ Crons
- tennis/outreach marcan "error" pero es bug exit code (PR #25)
- Demás crons OK

---

## 🌙 Trabajo nocturno completado (4 abr 2026 — 10pm CDMX del 3 abr)

### ✅ Trabajo completado:
- 7 signups detectados (2 días) — 3 MX, 4 LATAM
- 7 respuestas prospectos verificadas (todos perdidos >20 días, sin cambios)
- Tennis viernes 3 abr verificado: Cancha 3 Folio 156908 ✅
- Memoria escrita: `memory/2026-04-04.md`
- Crons verificados: tennis OK, varios recordatorios con error (bug exit code)
- Lead-finder: sigue bloqueado (PR #24 pendiente merge)

### 📱 Signups MX pendientes seguimiento:
1. **Juan Gabriel — Hotel Westin** (28 mar) — wa.me/525573975683 ⭐ Prioritario B2B
2. **Maria** (Propio) — wa.me/529171277042 🇲🇽 NUEVO
3. **Graciela** (Novedades chely) — wa.me/5244431320243 🇲🇽
4. **Manuel Enrique** (Produtos a domicilio) — wa.me/529961054780 🇲🇽
