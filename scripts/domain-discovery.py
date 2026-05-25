#!/usr/bin/env python3
"""
Domain Discovery — EZContact Lead Generation v2
Busca sitios web de negocios PYME por vertical usando múltiples buscadores.

Mejoras v2:
  - Rotación de User-Agents para evitar rate-limiting
  - Bing HTML como motor primario (DuckDuckGo bloqueado en servidor)
  - Filtro de cadenas grandes / plataformas / directorios mejorado
  - Filtro de calidad: prioriza dominios .mx y .com.mx
  - Cache de queries para no repetir búsquedas recientes

Uso:
    python3 domain-discovery.py
    python3 domain-discovery.py --limit 50
    python3 domain-discovery.py --engine bing|ddg

Salida: prospectos/discovered-domains.json
"""

import requests
import re
import json
import time
import random
import argparse
import hashlib
from datetime import datetime
from urllib.parse import quote_plus, urlparse

OUTPUT_FILE = "/home/ubuntu/clawd/prospectos/discovered-domains.json"
EXISTING_SCRAPER = "/home/ubuntu/clawd/scripts/lead-scraper.py"
QUERY_CACHE_FILE = "/home/ubuntu/clawd/prospectos/discovery-query-cache.json"

# Rotación de User-Agents para evitar detección
USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_2) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
]


def get_headers():
    """Retorna headers con User-Agent rotado aleatoriamente."""
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "es-MX,es;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
    }


# Verticales + ciudades para búsqueda dinámica
SEARCH_QUERIES = [
    # Restaurantes / Catering
    ("catering corporativo box lunch CDMX cotización email", "Catering"),
    ("dark kitchen cocina virtual CDMX pedidos contacto", "Restaurante/Dark Kitchen"),
    ("pastelería personalizada CDMX pedidos whatsapp email", "Pastelería"),
    ("panadería artesanal CDMX pedidos contacto", "Panadería"),
    # Fitness / Bienestar
    ("pilates reformer CDMX clases boutique contacto email", "Pilates"),
    ("yoga estudio CDMX inscripciones clases email contacto", "Yoga"),
    ("crossfit box CDMX membresías contacto", "Crossfit"),
    ("spinning indoor cycling CDMX membresías email", "Fitness"),
    ("centro meditación mindfulness CDMX sesiones contacto", "Meditación"),
    # Spa / Estética
    ("spa tratamientos CDMX reservaciones whatsapp email", "Spa"),
    ("clínica estética facial CDMX citas contacto", "Clínica Estética"),
    ("centro de depilación láser CDMX citas email", "Depilación"),
    ("peluquería salón belleza CDMX citas whatsapp email", "Salón de Belleza"),
    ("barbería premium CDMX citas cortes email", "Barbería"),
    # Educación
    ("escuela danza baile adultos CDMX clases email", "Escuela de Baile"),
    ("academia música guitarra piano CDMX clases email", "Escuela de Música"),
    ("escuela cocina gastronomía CDMX cursos inscripción", "Escuela de Cocina"),
    ("idiomas inglés francés CDMX adultos clases contacto", "Idiomas"),
    ("guardería kinder privado CDMX inscripciones contacto", "Guardería/Kinder"),
    ("tutoría clases particulares CDMX universitarios contacto email", "Tutoría"),
    # Salud
    ("clínica dental odontología CDMX citas email", "Dental"),
    ("clínica nutrición dietista CDMX citas email whatsapp", "Nutrición"),
    ("psicólogo terapeuta CDMX citas privadas contacto email", "Psicología"),
    ("fisioterapia rehabilitación CDMX citas email", "Fisioterapia"),
    # Mascotas
    ("veterinaria clínica mascotas CDMX citas contacto email", "Veterinaria"),
    ("guardería hotel perros CDMX reservaciones email", "Pet Hotel"),
    ("grooming estética canina CDMX citas whatsapp email", "Grooming"),
    # Servicios profesionales
    ("agencia marketing digital PYME CDMX cotización email", "Marketing Digital"),
    ("fotografía eventos bodas CDMX cotización email", "Fotografía"),
    ("diseño gráfico branding CDMX cotización email", "Diseño"),
    ("mudanzas flete CDMX cotización whatsapp email", "Mudanzas"),
    # Monterrey
    ("clínica dental Monterrey citas email contacto", "Dental MTY"),
    ("spa masajes Monterrey reservaciones email", "Spa MTY"),
    ("guardería privada Monterrey inscripciones contacto", "Guardería MTY"),
]

# Dominios completos a excluir — plataformas, directorios, gobierno, cadenas grandes
EXCLUDE_DOMAINS = {
    # Gobierno
    "gob.mx", "cdmx.gob.mx", "cultura.cdmx.gob.mx", "dif.cdmx.gob.mx",
    "inba.gob.mx", "sectur.gob.mx", "proteccioncivil.gob.mx",
    # Redes sociales
    "google.com", "facebook.com", "instagram.com", "twitter.com", "x.com",
    "youtube.com", "linkedin.com", "tiktok.com", "pinterest.com",
    # Directorios / Agregadores
    "yelp.com", "yelp.com.mx", "tripadvisor.com", "tripadvisor.com.mx",
    "foursquare.com", "mercadolibre.com", "amazon.com.mx", "amazon.com",
    "superprof.mx", "superprof.es", "superprof.com",
    "doctoralia.com", "doctoralia.com.mx", "zocdoc.com",
    "topdoctors.mx", "doctoranytime.mx",
    "kinders.info", "edutory.mx", "mejoresmexico.com",
    "donde.com.mx", "paginas.mx", "soyempresa.com", "empresas10.com",
    "sortlist.mx", "clutch.co", "goodfirms.co",
    "cronoshare.com.mx", "bodasesor.com",
    "monitornutricional.com",
    # Plataformas de delivery / booking
    "ubereats.com", "rappi.com.mx", "rappi.com", "didi.mx", "didifood.mx",
    "cornershop.com", "booking.com", "airbnb.com", "expedia.com",
    "despegar.com",
    # Plataformas educativas
    "udemy.com", "coursera.com", "hotmart.com", "classesvip.com",
    "tusclases.mx",
    # Builders web
    "wix.com", "shopify.com", "squarespace.com", "wordpress.com",
    "webnode.com", "jimdo.com", "godaddy.com",
    # Freelance / trabajo
    "workana.com", "freelancer.com", "upwork.com", "fiverr.com",
    # Promo / cupones
    "groupon.com", "cuponidad.com",
    # Otros
    "wikipedia.org", "bing.com", "yahoo.com", "duckduckgo.com",
    "lp.resto.marketing",
    # Cadenas grandes (no son PYME)
    "italiannis.com.mx", "taqueriaorinoco.com", "sanborns.com.mx",
    "walmart.com.mx", "liverpool.com.mx", "palaciodhierro.com",
    "smartfit.com", "sport-city.com.mx", "gold-gym.com.mx",
    "divadance.com",  # Franquicia gringa
}

# Palabras en dominio que indican NO es PYME individual
EXCLUDE_KEYWORDS_IN_DOMAIN = [
    "uber", "rappi", "didi", "cornershop", "booking", "airbnb",
    "directorio", "directory", "paginas", "listado", "encuentra",
    "busca", "comparador", "marketplace", "plataforma",
    "wix", "shopify", "wordpress", "weebly",
    "clasifik", "clasificado", "anunci",
    "smartfit", "sportcity", "bodytech",
]

# Palabras en el nombre de la empresa que indican cadena grande (skip)
CHAIN_KEYWORDS = [
    "nacional", "grupo", "corporativo", "international", "internacional",
    "holdings", "franquicia", "sucursales", "cadena",
]


def search_bing(query, max_results=8):
    """Busca en Bing HTML y extrae URLs de resultados orgánicos."""
    urls = []
    try:
        encoded = quote_plus(query)
        url = f"https://www.bing.com/search?q={encoded}&setlang=es-MX&cc=MX&count=20"
        r = requests.get(url, headers=get_headers(), timeout=12)
        if r.status_code != 200:
            return urls
        # Extraer URLs de resultados Bing
        # Patrón 1: href en citación de resultado
        pattern = re.compile(r'<cite[^>]*>([^<]+)</cite>')
        found_cites = pattern.findall(r.text)
        # Patrón 2: href directo en resultado
        pattern2 = re.compile(r'<a[^>]+href="(https?://(?!www\.bing)[^"]+)"[^>]*class="[^"]*tilk[^"]*"')
        found_hrefs = pattern2.findall(r.text)
        # Patrón 3: data-url
        pattern3 = re.compile(r'data-url="(https?://[^"]+)"')
        found_data = pattern3.findall(r.text)

        all_found = found_hrefs + found_data
        for raw in all_found:
            raw = raw.strip()
            if not raw.startswith('http'):
                continue
            parsed = urlparse(raw)
            domain = parsed.netloc.lower().replace('www.', '')
            if not domain:
                continue
            # Filtrar exclusiones
            if any(excl in domain for excl in EXCLUDE_DOMAINS):
                continue
            if any(kw in domain for kw in EXCLUDE_KEYWORDS_IN_DOMAIN):
                continue
            # Preferir .mx
            clean_url = f"https://www.{domain}/" if not raw.endswith('/') else f"https://www.{domain}/"
            if clean_url not in urls:
                urls.append(clean_url)
            if len(urls) >= max_results:
                break
    except Exception as e:
        pass
    return urls


def search_duckduckgo_lite(query, max_results=6):
    """Intenta DuckDuckGo Lite como fallback — puede estar bloqueado."""
    urls = []
    try:
        encoded = quote_plus(query)
        url = f"https://lite.duckduckgo.com/lite/?q={encoded}&kl=mx-es"
        r = requests.get(url, headers=get_headers(), timeout=10)
        if r.status_code not in (200, 202):
            return urls
        if len(r.text) < 1000:  # respuesta vacía / bloqueada
            return urls
        # Extraer hrefs
        found = re.findall(r'href="(https?://(?!duckduckgo\.com)[^"]+)"', r.text)
        for raw in found[:max_results * 3]:
            parsed = urlparse(raw)
            domain = parsed.netloc.lower().replace('www.', '')
            if not domain:
                continue
            if any(excl in domain for excl in EXCLUDE_DOMAINS):
                continue
            if any(kw in domain for kw in EXCLUDE_KEYWORDS_IN_DOMAIN):
                continue
            clean_url = f"https://www.{domain}/"
            if clean_url not in urls:
                urls.append(clean_url)
            if len(urls) >= max_results:
                break
    except:
        pass
    return urls


def load_query_cache():
    """Carga cache de queries ejecutadas para no repetir en 7 días."""
    try:
        with open(QUERY_CACHE_FILE) as f:
            return json.load(f)
    except:
        return {}


def save_query_cache(cache):
    """Guarda cache de queries."""
    import os
    os.makedirs("/home/ubuntu/clawd/prospectos", exist_ok=True)
    with open(QUERY_CACHE_FILE, 'w') as f:
        json.dump(cache, f, indent=2)


def query_hash(query):
    return hashlib.md5(query.encode()).hexdigest()[:12]


def load_existing_urls():
    """Carga URLs que ya están en el scraper principal."""
    existing = set()
    try:
        with open(EXISTING_SCRAPER) as f:
            content = f.read()
        found = re.findall(r'"(https?://[^"]+)"', content)
        for u in found:
            parsed = urlparse(u)
            existing.add(parsed.netloc.lower().replace('www.', ''))
    except:
        pass
    return existing


def load_discovered():
    """Carga URLs ya descubiertas previamente."""
    try:
        with open(OUTPUT_FILE) as f:
            return json.load(f)
    except:
        return {"discovered": [], "last_updated": None}


def save_discovered(data):
    import os
    os.makedirs("/home/ubuntu/clawd/prospectos", exist_ok=True)
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def is_likely_pyme(url):
    """Heurística rápida: ¿parece PYME individual vs cadena grande?"""
    domain = urlparse(url).netloc.lower()
    # Preferir dominios .mx — más probablemente PYME local
    if '.mx' in domain:
        return True, "dominio .mx"
    # Si tiene keywords de cadena en dominio
    for kw in CHAIN_KEYWORDS:
        if kw in domain:
            return False, f"keyword cadena: {kw}"
    return True, "ok"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--limit', type=int, default=len(SEARCH_QUERIES),
                        help='Número de queries a ejecutar')
    parser.add_argument('--engine', choices=['bing', 'ddg', 'both'], default='bing',
                        help='Motor de búsqueda a usar')
    parser.add_argument('--force', action='store_true',
                        help='Ignorar cache y re-ejecutar todas las queries')
    args = parser.parse_args()

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Domain Discovery v2 iniciado")
    print(f"  Motor: {args.engine} | Queries: {args.limit}")

    existing_domains = load_existing_urls()
    discovered_data = load_discovered()
    already_known = {urlparse(d['url']).netloc.lower().replace('www.', '')
                     for d in discovered_data.get('discovered', [])}
    already_known.update(existing_domains)

    query_cache = load_query_cache() if not args.force else {}
    now_ts = datetime.now().timestamp()
    CACHE_TTL = 7 * 24 * 3600  # 7 días

    queries = SEARCH_QUERIES[:args.limit]
    new_found = []
    total = 0
    skipped_cache = 0

    for i, (query, vertical) in enumerate(queries, 1):
        qh = query_hash(query)
        # Skip si fue ejecutada recientemente
        if qh in query_cache and (now_ts - query_cache[qh]['ts']) < CACHE_TTL and not args.force:
            skipped_cache += 1
            continue

        print(f"  [{i}/{len(queries)}] {vertical}: {query[:55]}...")

        urls = []
        if args.engine in ('bing', 'both'):
            urls = search_bing(query, max_results=8)
        if not urls and args.engine in ('ddg', 'both'):
            urls = search_duckduckgo_lite(query, max_results=6)

        added = 0
        for url in urls:
            domain = urlparse(url).netloc.lower().replace('www.', '')
            if domain not in already_known:
                pyme_ok, reason = is_likely_pyme(url)
                entry = {
                    "url": url,
                    "vertical": vertical,
                    "discovered": datetime.now().isoformat()[:10],
                    "pyme_score": "high" if pyme_ok else "low",
                }
                new_found.append(entry)
                already_known.add(domain)
                added += 1
                total += 1
        print(f"    → {added} nuevos dominios")

        # Guardar en cache
        query_cache[qh] = {"query": query, "ts": now_ts, "found": added}

        # Rate limit cortesía
        time.sleep(random.uniform(1.5, 3.0))

    if skipped_cache > 0:
        print(f"\n  ℹ️  {skipped_cache} queries saltadas (cache < 7 días). Usa --force para re-ejecutar.")

    if new_found:
        discovered_data['discovered'] = discovered_data.get('discovered', []) + new_found
        discovered_data['last_updated'] = datetime.now().isoformat()
        save_discovered(discovered_data)
        save_query_cache(query_cache)
        print(f"\n✅ {total} nuevos dominios guardados en {OUTPUT_FILE}")
        print(f"   Total acumulado: {len(discovered_data['discovered'])}")
    else:
        save_query_cache(query_cache)
        print("\n⚠️  No se encontraron dominios nuevos esta corrida")

    return total


if __name__ == '__main__':
    main()
