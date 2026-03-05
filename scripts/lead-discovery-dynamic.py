#!/usr/bin/env python3
"""
Lead Discovery Dinámico — EZContact
Usa Brave Search API para encontrar negocios NUEVOS en CDMX/ZM
en lugar de URLs hardcodeadas que se agotan.

Versión 1.0 — 4 mar 2026

Uso:
    python3 scripts/lead-discovery-dynamic.py
    python3 scripts/lead-discovery-dynamic.py --limit 50
    python3 scripts/lead-discovery-dynamic.py --vertical "yoga" --city "Monterrey"

Diferencia con lead-scraper.py:
  - No usa URLs hardcodeadas → nunca se agota
  - Usa Brave Search para descubrir sitios nuevos cada día
  - Rota queries de búsqueda para encontrar negocios distintos
  - Guarda en el mismo formato que lead-scraper.py
"""

import requests
import re
import time
import json
import os
import html as html_module
import random
import argparse
from datetime import datetime
from urllib.parse import urljoin, urlparse, unquote

# ─── Config ───────────────────────────────────────────────────────────────────
TODAY             = datetime.now().strftime('%Y-%m-%d')
OUTPUT_DIR        = "/home/ubuntu/clawd/prospectos"
OUTPUT_FILE       = f"{OUTPUT_DIR}/leads-auto-{TODAY}.json"
ALREADY_SENT_FILE = "/home/ubuntu/clawd/memory/already-sent.json"
BRAVE_API_KEY     = None   # se carga desde vault
MAX_LEADS_DEFAULT = 80
DELAY_BETWEEN     = 0.8

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# ─── Verticales con queries de búsqueda ───────────────────────────────────────
VERTICALS = {
    "Yoga / Pilates": [
        "studio yoga CDMX contacto",
        "clases pilates Ciudad de México email",
        "yoga reformer Mexico City sitio web",
        "pilates aereo CDMX contact",
        "hot yoga Mexico DF",
        "studio yoga Guadalajara email",
        "pilates Monterrey contacto",
        "yoga prenatal CDMX",
        "meditacion mindfulness CDMX",
        "barre fitness Mexico",
    ],
    "Fitness / Gym": [
        "gimnasio boutique CDMX contacto",
        "CrossFit box Mexico email",
        "functional training Mexico City",
        "box gym Polanco Condesa Roma email",
        "entrenamiento personal CDMX",
        "gym privado CDMX contacto",
        "studio fitness Mexico email",
        "HIIT studio CDMX",
        "gimnasio Guadalajara email contacto",
        "personal trainer Mexico site:.mx",
    ],
    "Spa / Bienestar": [
        "spa day CDMX contacto email",
        "masajes relajantes Mexico City",
        "spa relajacion Roma Condesa email",
        "centro bienestar CDMX contacto",
        "masajes corporativos CDMX",
        "spa Polanco email contacto",
        "aromaterapia CDMX sitio",
        "wellness center Mexico City contact",
        "flotation therapy Mexico",
        "crioterapia CDMX",
    ],
    "Clínicas / Nutrición": [
        "nutriologa CDMX contacto email",
        "clinica nutricion Mexico City",
        "dietista CDMX sitio web email",
        "perdida de peso CDMX clinica",
        "nutricion deportiva Mexico email",
        "clinica bienestar CDMX email",
        "medicina funcional CDMX contacto",
        "coach nutricion Mexico",
        "tratamiento obesidad CDMX clinica",
        "nutrologa Mexico sitio web",
    ],
    "Veterinaria": [
        "veterinaria CDMX contacto email",
        "clinica veterinaria Mexico City site:.mx",
        "hospital veterinario CDMX email",
        "veterinaria mascotas Roma Condesa email",
        "veterinaria Guadalajara email",
        "clinica veterinaria Monterrey contacto",
        "pet grooming Mexico City email",
        "veterinaria 24 horas CDMX",
        "veterinaria Coyoacan contacto",
        "especialista mascotas Mexico email",
    ],
    "Escuelas / Idiomas": [
        "escuela idiomas CDMX email contacto",
        "curso ingles Mexico email",
        "academia idiomas Mexico City site:.mx",
        "centro idiomas CDMX contacto",
        "escuela frances CDMX email",
        "aleman CDMX academia email",
        "escuela idiomas Guadalajara contacto",
        "language school Mexico City email",
        "escuela idiomas Monterrey email",
        "ingles ejecutivo CDMX contacto",
    ],
    "Restaurantes / Catering": [
        "catering corporativo CDMX email",
        "box lunch empresas CDMX contacto",
        "servicio alimentos CDMX email",
        "catering eventos Mexico City",
        "comida para oficina CDMX contacto",
        "restaurant privado CDMX email",
        "catering boda Mexico City email",
        "food service empresarial CDMX",
        "cocina industrial CDMX email",
        "catering Guadalajara contacto email",
    ],
    "Inmobiliarias": [
        "inmobiliaria CDMX email contacto",
        "agencia inmobiliaria Mexico City site:.mx",
        "bienes raices CDMX email",
        "inmobiliaria Roma Condesa Polanco contacto",
        "renta departamentos CDMX agencia email",
        "inmobiliaria Guadalajara email",
        "agente inmobiliario Mexico email",
        "broker inmobiliario CDMX",
        "desarrolladora inmobiliaria Mexico email",
        "inmobiliaria Monterrey contacto email",
    ],
    "Reclutamiento / HR": [
        "agencia reclutamiento CDMX email",
        "headhunter Mexico contacto",
        "consultora RH Mexico City email",
        "reclutamiento ejecutivo CDMX",
        "agencia empleo Mexico email",
        "HR consulting Mexico City contacto",
        "outplacement Mexico email",
        "staffing agency Mexico City",
        "bolsa trabajo CDMX agencia email",
        "reclutamiento TI Mexico email",
    ],
    "Escuelas Privadas": [
        "colegio privado CDMX contacto email",
        "escuela primaria privada Mexico City",
        "colegio bilingue CDMX email",
        "preescolar privado CDMX contacto",
        "secundaria privada Mexico City email",
        "colegio privado Guadalajara email",
        "escuela privada Monterrey contacto",
        "liceo privado CDMX email",
        "preparatoria privada CDMX",
        "colegio americano Mexico email",
    ],
}

# Ciudades para rotar
CITIES = ["CDMX", "Guadalajara", "Monterrey", "Puebla", "Querétaro", "León"]

# ─── Email patterns ───────────────────────────────────────────────────────────
EMAIL_REGEX  = re.compile(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}')
TITLE_REGEX  = re.compile(r'<title[^>]*>(.*?)</title>', re.IGNORECASE | re.DOTALL)

JUNK_DOMAINS = {
    'sentry.io', 'sentry.wixpress.com', 'example.com', 'example.mx',
    'test.com', 'amazonaws.com', 'cloudfront.net',
    'facebook.com', 'instagram.com', 'twitter.com', 'youtube.com',
    'google.com', 'gmail.com', 'hotmail.com', 'outlook.com',
    'wixpress.com', 'squarespace.com', 'shopify.com',
    'mailchimp.com', 'hubspot.com', 'zendesk.com',
    # Medios / periódicos (no son prospectos)
    'jornada.com.mx', 'cronica.com.mx', 'reforma.com', 'eluniversal.com.mx',
    'milenio.com', 'excelsior.com.mx', 'proceso.com.mx', 'infobae.com',
    'expansion.mx', 'forbes.com.mx', 'cnn.com', 'vanguardia.com.mx',
    'tvazteca.com', 'televisa.com', 'ejecentral.com.mx', 'sopitas.com',
    'lanzadigital.com', 'laverdadnoticias.com',
    # Directorios / plataformas (no son prospectos directos)
    'superprof.mx', 'cronoshare.com', 'habitissimo.com.mx',
    'homify.mx', 'thumbtack.com', 'workana.com',
    'medicbook.com.mx', 'doctoralia.mx',
    # Grandes corporativos (no target EZContact)
    'smartfit.com', 'sportcity.com.mx', 'totalplay.com.mx',
    'planseguro.com.mx', 'bbva.com', 'banamex.com',
}

# Dominios raíz de medios para filtro rápido por substring
MEDIA_SUBSTRINGS = {
    'noticias', 'periodico', 'diario', 'redaccion', 'editorial',
    'prensa', 'gaceta', 'correo', 'tribuna',
}

def load_already_sent():
    if not os.path.exists(ALREADY_SENT_FILE):
        return set()
    try:
        return set(json.load(open(ALREADY_SENT_FILE)).get("emails", []))
    except Exception:
        return set()

def save_already_sent(new_emails: set):
    """Agrega nuevos emails al already-sent (sin sobrescribir los existentes)."""
    existing = load_already_sent()
    merged = existing | new_emails
    try:
        with open(ALREADY_SENT_FILE, 'w') as f:
            json.dump({
                "emails": sorted(list(merged)),
                "last_updated": datetime.now().strftime('%Y-%m-%d')
            }, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"⚠️  No pude guardar already-sent: {e}")

def get_brave_api_key():
    """Obtiene la Brave API key desde vault."""
    try:
        import subprocess
        r = subprocess.run(['vault', 'get', 'api/brave'], capture_output=True, text=True, timeout=10)
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    except Exception:
        pass
    # Fallback: variable de entorno
    return os.environ.get('BRAVE_API_KEY')

def brave_search(query: str, count: int = 10) -> list:
    """
    Busca en Brave Search y devuelve lista de URLs.
    Requiere: vault get api/brave
    """
    api_key = BRAVE_API_KEY or get_brave_api_key()
    if not api_key:
        return []
    try:
        resp = requests.get(
            "https://api.search.brave.com/res/v1/web/search",
            headers={
                "Accept": "application/json",
                "Accept-Encoding": "gzip",
                "X-Subscription-Token": api_key,
            },
            params={
                "q": query,
                "count": count,
                "country": "mx",
                "search_lang": "es",
                "ui_lang": "es-MX",
                "safesearch": "off",
                "freshness": "pm",   # últimas 4 semanas
            },
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            results = data.get("web", {}).get("results", [])
            return [r["url"] for r in results if "url" in r]
    except Exception as e:
        pass
    return []

def is_valid_email(email: str) -> bool:
    """Valida que el email sea limpio y enviable."""
    if not email or "@" not in email:
        return False
    if "%" in email:
        return False
    if re.search(r'u[0-9a-f]{4}|&[a-z]+;|&#\d+;', email, re.IGNORECASE):
        return False
    local = email.split("@")[0]
    if re.match(r'^\d+', local):
        return False
    if not re.match(r'^[a-zA-Z0-9._%+\-]+$', local):
        return False
    domain = email.split("@")[1]
    if "." not in domain:
        return False
    if domain in JUNK_DOMAINS:
        return False
    if re.search(r'noreply|no-reply|donotreply|mailer-daemon', email, re.IGNORECASE):
        return False
    return True

def extract_business_name(text: str, fallback_url: str) -> str:
    """Extrae nombre del negocio del title HTML."""
    match = TITLE_REGEX.search(text)
    if match:
        raw = match.group(1)
        raw = html_module.unescape(raw)
        raw = re.sub(r'<[^>]+>', '', raw)
        raw = re.sub(r'\s+', ' ', raw).strip()
        # Limpiar sufijos comunes
        raw = re.sub(r'\s*[|–\-—]\s*(Inicio|Home|Bienvenido|México|CDMX|MX).*$', '', raw, flags=re.IGNORECASE)
        if 3 < len(raw) < 60:
            return raw
    # Fallback: dominio limpio
    try:
        domain = urlparse(fallback_url).netloc
        name = re.sub(r'^www\.', '', domain)
        name = re.sub(r'\.(com\.mx|edu\.mx|org\.mx|mx|com)$', '', name)
        return re.sub(r'[-_]', ' ', name).title()
    except Exception:
        return ""

def get_emails_from_url(url, already_sent, timeout=10):
    """Visita una URL y extrae emails válidos."""
    try:
        domain = urlparse(url).netloc
        if any(junk in domain for junk in JUNK_DOMAINS):
            return []
        r = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        if r.status_code != 200:
            return []
        # Decodificar HTML entities y URL-encoding
        text = r.text
        text = html_module.unescape(unquote(text))
        biz_name = extract_business_name(text, url)
        emails = set(EMAIL_REGEX.findall(text))
        leads = []
        for raw_email in emails:
            email = raw_email.lower().strip()
            if not is_valid_email(email):
                continue
            email_domain = email.split("@")[1]
            # Preferir emails del mismo dominio del sitio
            site_domain = urlparse(url).netloc.replace("www.", "")
            if email_domain != site_domain and not site_domain.endswith(email_domain):
                continue  # saltar emails de terceros
            if email in already_sent:
                continue
            leads.append({
                "email": email,
                "business_name": biz_name,
                "source": url,
            })
        return leads
    except Exception:
        return []

def main():
    parser = argparse.ArgumentParser(description="Dynamic lead discovery via Brave Search")
    parser.add_argument("--limit", type=int, default=MAX_LEADS_DEFAULT)
    parser.add_argument("--vertical", type=str, default=None, help="Filtrar a una vertical")
    parser.add_argument("--city", type=str, default=None, help="Ciudad específica")
    args = parser.parse_args()

    print(f"🔍 Lead Discovery Dinámico v1.0 — {TODAY}")
    print(f"   Máximo leads: {args.limit}")

    api_key = get_brave_api_key()
    if not api_key:
        print("⚠️  No se encontró Brave API key (vault get api/brave)")
        print("   Ejecuta: vault set api/brave <TU_API_KEY>")
        print("   Obten clave gratis en: https://api.search.brave.com/")
        return

    already_sent = load_already_sent()
    all_leads = []
    seen_emails = set(already_sent)

    # Cargar leads ya encontrados hoy
    if os.path.exists(OUTPUT_FILE):
        try:
            existing = json.load(open(OUTPUT_FILE))
            all_leads = existing
            for l in existing:
                seen_emails.add(l["email"])
        except Exception:
            pass

    # Seleccionar verticales
    verticals_to_use = VERTICALS
    if args.vertical:
        verticals_to_use = {k: v for k, v in VERTICALS.items() if args.vertical.lower() in k.lower()}
        if not verticals_to_use:
            verticals_to_use = VERTICALS

    total_new = 0
    total_urls_checked = 0

    # Rotar verticales y queries aleatoriamente para variedad
    items = list(verticals_to_use.items())
    random.shuffle(items)

    for vertical_name, queries in items:
        if total_new >= args.limit:
            break

        # Tomar 2-3 queries aleatorias de esta vertical
        selected_queries = random.sample(queries, min(3, len(queries)))

        # Si hay ciudad especificada, agregar a queries
        if args.city:
            selected_queries = [f"{q} {args.city}" for q in selected_queries]

        print(f"\n🏢 {vertical_name}:")

        for query in selected_queries:
            if total_new >= args.limit:
                break

            urls = brave_search(query, count=10)
            if not urls:
                time.sleep(0.5)
                continue

            for url in urls:
                if total_new >= args.limit:
                    break
                try:
                    domain = urlparse(url).netloc.lower()

                    # ⚡ FILTRO CRÍTICO: solo sitios .mx (prospectos mexicanos)
                    # Acepta: empresa.com.mx, empresa.mx, empresa.org.mx
                    if not (domain.endswith('.mx') or '.com.mx' in domain):
                        continue

                    # Saltar medios por substring en dominio
                    if any(sub in domain for sub in MEDIA_SUBSTRINGS):
                        continue

                    # Skip if already scraped this domain today
                    if any(l.get("source", "").startswith(f"https://{domain}") or
                           l.get("source", "").startswith(f"http://{domain}")
                           for l in all_leads):
                        continue

                    leads = get_emails_from_url(url, seen_emails)
                    total_urls_checked += 1

                    for lead in leads:
                        lead["vertical"] = vertical_name
                        all_leads.append(lead)
                        seen_emails.add(lead["email"])
                        total_new += 1
                        biz = lead.get("business_name", "?")[:30]
                        print(f"   ✉️  {lead['email']} — {biz}")

                    time.sleep(DELAY_BETWEEN)
                except Exception:
                    continue

            time.sleep(0.5)  # entre queries

    # Guardar resultados
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(all_leads, f, indent=2, ensure_ascii=False)

    print(f"\n📊 Resumen:")
    print(f"   URLs revisadas: {total_urls_checked}")
    print(f"   Leads nuevos:   {total_new}")
    print(f"   Total en archivo: {len(all_leads)}")
    print(f"   Archivo: {OUTPUT_FILE}")

    if total_new == 0:
        print("\n⚠️  0 leads encontrados. Posibles causas:")
        print("   1. Brave API key inválida o quota agotada")
        print("   2. Todos los negocios encontrados ya están en blacklist")
        print("   3. Los sitios encontrados no tienen emails visibles")


if __name__ == "__main__":
    main()
