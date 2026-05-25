# Guía de Merge — PRs Pendientes

> Actualizado: 4 marzo 2026  
> **14 PRs abiertos.** Este doc explica qué mergear, en qué orden, y por qué.

---

## ⚡ TL;DR — Mergea en este orden

```
1  → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10 → 11 → 12 → 13 → 14
```

Cada PR depende del anterior. Si solo quieres hacer los más importantes:

**Top 3 que más impactan hoy:**
- PR #11 — lead-scraper v3 (fix encoding malformados)
- PR #13 — send-outreach email quality (filtro antes de enviar)
- PR #14 — reply-auto-handler (clasifica respuestas automáticamente)

---

## 📋 PRs en Orden de Merge

### Grupo A — Fundación (merge juntos, sin orden crítico)

| PR | Título corto | Qué hace | Urgencia |
|----|-------------|----------|---------|
| #1 | TRACKING.md | Pipeline tracking structure | Baja |
| #2 | Sales docs | SPIN, Hormozi, book study | Baja |
| #3 | Sales Ops | Métricas, objeciones, cierre | Media |
| #4 | Follow-up templates | 6 escenarios de follow-up | Media |
| #5 | Demo script 15min | Estructura demo, objeciones | Alta |

### Grupo B — Scripts de Prospección

| PR | Título corto | Qué hace | Urgencia |
|----|-------------|----------|---------|
| #6 | Domain discovery | Soluciona agotamiento scraper | Alta |
| #7 | Personalización dinámica | Nombre negocio en subject/greeting | Alta |
| #8 | Demo TentenPie prep | Reply-categorizer base | Media |
| #9 | Domain discovery v2 | Bing + user-agent + query cache | Alta |

### Grupo C — Fixes críticos (MERGEAR PRIMERO de este grupo)

| PR | Título corto | Qué hace | Urgencia |
|----|-------------|----------|---------|
| #10 | Contrato Elsa CUC | Draft contrato EZContact | Media |
| #11 | lead-scraper v3 | **FIX: emails malformados** | 🔴 Urgente |
| #12 | Tennis logging | Log de reservaciones a archivo | Baja |
| #13 | send-outreach quality | **FIX: filtra emails antes de enviar** | 🔴 Urgente |
| #14 | reply-auto-handler | **NUEVO: clasifica respuestas auto** | 🔴 Urgente |

---

## 🔴 Los 3 más importantes (detail)

### PR #11 — lead-scraper v3
**Problema que resuelve:** El scraper estaba generando emails malformados:
`u003eadmin@empresa.mx`, `administraci%c3%b3n@empresa.mx`

**Fixes:**
- Decodifica HTML entities antes de extraer emails
- Filtra emails con chars inválidos (%, \u003e, etc.)
- Extrae `business_name` del `<title>` de la página

**Merge en:** base = `feature/scraper-domain-filter` (PR #9)

---

### PR #13 — send-outreach email quality
**Problema que resuelve:** Emails malformados pasaban al envío aunque el scraper los filtrara.

**Fixes:**
- `is_valid_email()` — valida antes de enviar (URL-encoded, HTML entities, prefijos numéricos)
- `extract_business_name()` — ahora usa campo `business_name` de los leads
  - Antes: subjects genéricos "Pregunta rápida — Dancecenter"
  - Ahora: "Pregunta rápida — Dance Center"

**Merge en:** base = `feature/fix-email-encoding-3mar` (PR #11)

---

### PR #14 — reply-auto-handler  
**Problema que resuelve:** Respuestas de prospectos llegan al inbox sin procesamiento.
Esta noche encontré 3 sin revisar: CUC quiere callback, TentenPie quiere demo, Rivalia rechazó.

**Lo que hace automáticamente:**
| Respuesta | Acción |
|-----------|--------|
| "No estamos interesados" | Agrega a blacklist (no vuelve a recibir emails) |
| "Unsubscribe" | Agrega a blacklist |
| "¿Cuándo podemos ver la demo?" | 🔴 Alerta + draft de confirmación |
| "Me puedes marcar al tel?" | 🔴 Alerta + draft con WhatsApp |
| "¿Cuánto cuesta?" | 🟡 Alerta + draft con precios |

**Cómo correr:**
```bash
python3 scripts/reply-auto-handler.py --dry-run  # primero prueba
python3 scripts/reply-auto-handler.py            # luego ejecuta
```

**Merge en:** base = `feature/send-outreach-email-quality` (PR #13)

---

## 📝 Notas para Vicci

1. **Por qué hay tantos PRs sin merge:** Las ramas se construyen unas sobre otras.
   Para mergear #14 necesitas primero #13, que necesita #11, que necesita #9...

2. **Lo que puedes ignorar por ahora:** PRs #1-#5 son solo documentación.
   No afectan al sistema operativo.

3. **Lo que SÍ necesitas hoy:** PRs #11, #13, #14 arreglan bugs reales
   que están afectando el outreach diario.

4. **Después del merge:** Los scripts cambiados son:
   - `scripts/lead-scraper.py`
   - `scripts/send-outreach.py`
   - `scripts/reply-auto-handler.py` (nuevo)
   
   Necesitas copiar manualmente los scripts mergeados a `/home/ubuntu/clawd/scripts/`
   ya que el repo no hace deploy automático.

---

*Generado por Katia durante turno nocturno 4-mar-2026*
