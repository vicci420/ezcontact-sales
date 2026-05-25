#!/usr/bin/env python3
"""
reply-categorizer.py — Categoriza respuestas de prospectos automáticamente
Analiza el contenido del email y clasifica la intención del prospecto.

Categorías:
  DEMO_CONFIRMED   — Confirmaron demo/llamada con fecha y hora
  CALLBACK_REQUEST — Piden que les marquemos / dan su teléfono
  INTERESTED       — Interés claro sin fecha aún
  INFO_REQUEST     — Tienen preguntas específicas antes de decidir
  NOT_INTERESTED   — Rechazo explícito
  ANTI_SPAM        — Sistema anti-spam / verificación
  OUT_OF_OFFICE    — Fuera de oficina / autorrespuesta
  UNKNOWN          — No se puede clasificar

Uso:
  python3 reply-categorizer.py --email-body "Hola, podemos el martes 11am"
  python3 reply-categorizer.py --file prospect-reply.txt
"""

import re
import sys
import argparse
import json
from datetime import datetime

# Patrones de clasificación
PATTERNS = {
    "DEMO_CONFIRMED": [
        r"\b(lunes|martes|miércoles|jueves|viernes)\b.*\b(\d{1,2}am|\d{1,2}pm|\d{1,2}:\d{2})\b",
        r"\b(\d{1,2}am|\d{1,2}pm|\d{1,2}:\d{2})\b.*\b(lunes|martes|miércoles|jueves|viernes)\b",
        r"\bconfirm(o|amos|ada)\b.*\b(demo|llamada|reunión|cita)\b",
        r"\b(demo|llamada|reunión)\b.*\bconfirm",
        r"\bperfecto.*el (lunes|martes|miércoles|jueves|viernes|martes)\b",
        r"\b(agendad[ao]|programad[ao])\b",
        r"ver(nos|me|les).*\b(lunes|martes|miércoles|jueves|viernes)\b.*\b(\d{1,2}am|\d{1,2}pm)",
    ],
    "CALLBACK_REQUEST": [
        r"\b(márc[ae]me|llám[ae]me|marcar al|llamar al)\b",
        r"\bme pued[ée]s? (marcar|llamar)\b",
        r"\bnúmero.*(\+52|\d{10})",
        r"\b(\+52|55\s?\d{4}\s?\d{4}|\d{2,3}[\s-]\d{4}[\s-]\d{4})\b",
        r"(cuando gusten|cuando les acomode|cuando puedan).*llamar",
        r"con gusto.*llamada",
    ],
    "INTERESTED": [
        r"\b(sí|si)\s+(me interesa|nos interesa|podemos|queremos)\b",
        r"\b(interesad[ao]|interesante)\b",
        r"\bme (gustaría|gustaría)\s+(ver|saber|conocer)\b",
        r"\bademás (queremos|necesitamos|nos gustaría)\b",
        r"\b(cuándo|cuando)\s+(podemos|pueden|hay)\b",
        r"\bpodemos\s+(agendar|ver|reunirnos|hablar)\b",
        r"\b(quiero|queremos)\s+(una|la)\s+(demo|llamada|reunión|prueba)\b",
    ],
    "INFO_REQUEST": [
        r"\b(cómo|como)\s+(funciona|trabajan|operan|es)\b",
        r"\b(cuánto|cuanto)\s+(cuesta|vale|cobran)\b",
        r"\b(precio|costo|tarifa|inversión)\b",
        r"\btengo\s+(algunas|unas|varias)\s+(preguntas|dudas)\b",
        r"\bpodría[ns]?\s+(explicar|decir|mandar)\b",
        r"\bmás\s+(información|info|detalles)\b",
    ],
    "NOT_INTERESTED": [
        r"\bno\s+(estamos?|me|nos)\s+(interesad[ao]s?|interesa)\b",
        r"\bno\s+(gracias?|aplica|procede)\b",
        r"\b(por el momento|ahorita|actualmente)\s+no\b",
        r"\bya\s+(tenemos?|contamos?\s+con|usamos?)\b.*\b(similar|igual|algo así)\b",
        r"\bno\s+(requiero|requerimos|necesito|necesitamos)\b",
        r"\bno\s+(es\s+necesario|aplica\s+para)\b",
        r"\bnos\s+desuscrib",
        r"\bfavor\s+de\s+no\s+(contactar|escribir|enviar)\b",
        r"\bnos\s+retiren\s+de\b",
    ],
    "ANTI_SPAM": [
        r"\bverif(y|ication|icación)\b",
        r"verify#[a-zA-Z0-9]+",
        r"\banti.?spam\b",
        r"\bcaptcha\b",
        r"\bconfirm.*human\b",
        r"please verify.*email",
    ],
    "OUT_OF_OFFICE": [
        r"\bfuera\s+de\s+(oficina|la oficina)\b",
        r"\bout\s+of\s+office\b",
        r"\bvacacion(es)?\b",
        r"\brespuesta\s+automática\b",
        r"\bauto.?reply\b",
        r"\bregreso\s+(el|a)\b",
    ],
}

# Acción recomendada por categoría
ACTIONS = {
    "DEMO_CONFIRMED": "🟢 CONFIRMAR — Responder y enviar link de Zoom. Preparar demo personalizada.",
    "CALLBACK_REQUEST": "🔥 LLAMAR — Marcar al número proporcionado. Máximo 24h de espera.",
    "INTERESTED": "📞 AGENDAR — Proponer 2-3 fechas concretas para demo.",
    "INFO_REQUEST": "📧 RESPONDER — Contestar preguntas directamente + proponer demo.",
    "NOT_INTERESTED": "❌ CERRAR — Marcar como 'no interesado' en pipeline. No contactar más.",
    "ANTI_SPAM": "🔐 VERIFICAR — Completar verificación anti-spam del prospecto.",
    "OUT_OF_OFFICE": "⏳ ESPERAR — Volver a contactar en la fecha que indica el email.",
    "UNKNOWN": "👀 REVISAR — Clasificación manual necesaria.",
}

PRIORITY = {
    "DEMO_CONFIRMED": 1,
    "CALLBACK_REQUEST": 2,
    "INTERESTED": 3,
    "INFO_REQUEST": 4,
    "NOT_INTERESTED": 5,
    "ANTI_SPAM": 6,
    "OUT_OF_OFFICE": 7,
    "UNKNOWN": 8,
}


def categorize_email(text: str) -> dict:
    """Categoriza el texto de un email y devuelve resultado."""
    text_lower = text.lower()
    matches = {}

    for category, patterns in PATTERNS.items():
        match_count = 0
        matched_patterns = []
        for pattern in patterns:
            if re.search(pattern, text_lower, re.IGNORECASE | re.UNICODE):
                match_count += 1
                matched_patterns.append(pattern)
        if match_count > 0:
            matches[category] = {
                "count": match_count,
                "patterns": matched_patterns[:3],  # top 3
            }

    # Determinar categoría ganadora por prioridad
    if not matches:
        winner = "UNKNOWN"
    else:
        winner = min(matches.keys(), key=lambda c: PRIORITY.get(c, 99))

    # Extraer teléfono si hay callback request
    phone = None
    phone_match = re.search(
        r"(\+52\s*\d{2}\s*\d{4}\s*\d{4}|\d{2,3}[\s\-]\d{4}[\s\-]\d{4}|\d{10})",
        text,
    )
    if phone_match:
        phone = phone_match.group(1).strip()

    # Extraer día/hora si hay demo confirmada
    time_info = None
    days = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
    for day in days:
        if day in text_lower:
            time_match = re.search(
                rf"{day}[^\n]{{0,30}}(\d{{1,2}}(?::\d{{2}})?(?:am|pm)?)",
                text_lower,
                re.IGNORECASE,
            )
            if time_match:
                time_info = f"{day.capitalize()} {time_match.group(1)}"
                break
            elif re.search(
                r"\d{1,2}(?::\d{2})?(?:am|pm)", text_lower
            ):
                hour_match = re.search(
                    r"(\d{1,2}(?::\d{2})?(?:am|pm))", text_lower
                )
                time_info = f"{day.capitalize()} {hour_match.group(1) if hour_match else ''}"
                break

    return {
        "category": winner,
        "action": ACTIONS[winner],
        "priority": PRIORITY[winner],
        "all_matches": matches,
        "phone_found": phone,
        "time_found": time_info,
        "analyzed_at": datetime.now().isoformat(),
    }


def analyze_batch(emails: list) -> list:
    """Analiza un batch de emails y los ordena por prioridad."""
    results = []
    for email in emails:
        result = categorize_email(email.get("body", ""))
        result.update({
            "id": email.get("id"),
            "from": email.get("from"),
            "subject": email.get("subject"),
            "date": email.get("date"),
        })
        results.append(result)

    # Ordenar por prioridad
    results.sort(key=lambda x: x["priority"])
    return results


def print_result(result: dict, verbose: bool = False):
    """Imprime el resultado de forma legible."""
    icons = {
        "DEMO_CONFIRMED": "🟢",
        "CALLBACK_REQUEST": "🔥",
        "INTERESTED": "📞",
        "INFO_REQUEST": "📧",
        "NOT_INTERESTED": "❌",
        "ANTI_SPAM": "🔐",
        "OUT_OF_OFFICE": "⏳",
        "UNKNOWN": "👀",
    }

    cat = result["category"]
    icon = icons.get(cat, "❓")

    print(f"\n{'='*60}")
    if result.get("from"):
        print(f"From: {result['from']}")
    if result.get("subject"):
        print(f"Subject: {result['subject']}")
    print(f"\n{icon} CATEGORÍA: {cat}")
    print(f"   Acción: {result['action']}")

    if result.get("phone_found"):
        print(f"   📱 Teléfono detectado: {result['phone_found']}")
    if result.get("time_found"):
        print(f"   🗓️  Horario detectado: {result['time_found']}")

    if verbose and result.get("all_matches"):
        print(f"\n   Patrones detectados:")
        for cat_name, data in result["all_matches"].items():
            print(f"   • {cat_name}: {data['count']} match(es)")


def main():
    parser = argparse.ArgumentParser(description="Categoriza respuestas de prospectos")
    parser.add_argument("--email-body", "-e", help="Texto del email a analizar")
    parser.add_argument("--file", "-f", help="Archivo con el texto del email")
    parser.add_argument("--json", "-j", action="store_true", help="Output en JSON")
    parser.add_argument("--verbose", "-v", action="store_true", help="Mostrar detalles")
    parser.add_argument("--batch", "-b", help="Archivo JSON con batch de emails")
    args = parser.parse_args()

    if args.batch:
        with open(args.batch) as f:
            emails = json.load(f)
        results = analyze_batch(emails)
        if args.json:
            print(json.dumps(results, ensure_ascii=False, indent=2))
        else:
            for r in results:
                print_result(r, args.verbose)
    elif args.email_body or args.file:
        if args.file:
            with open(args.file) as f:
                body = f.read()
        else:
            body = args.email_body
        result = categorize_email(body)
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print_result(result, args.verbose)
    else:
        # Leer de stdin
        body = sys.stdin.read()
        result = categorize_email(body)
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print_result(result, args.verbose)


if __name__ == "__main__":
    main()
