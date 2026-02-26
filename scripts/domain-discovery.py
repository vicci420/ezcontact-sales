#!/usr/bin/env python3
"""
Domain Discovery — EZContact Lead Generation
Busca sitios web de negocios por vertical usando DuckDuckGo HTML
y los agrega a un archivo supplemental de URLs para el scraper.

Uso:
    python3 domain-discovery.py
    python3 domain-discovery.py --vertical "clínica dental" --city "monterrey"
    python3 domain-discovery.py --limit 50

Salida: prospectos/discovered-domains.json
"""

import requests
import re
import json
import time
import argparse
from datetime import datetime
from urllib.parse import quote_plus, urlparse

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "es-MX,es;q=0.9",
}

OUTPUT_FILE = "/home/ubuntu/clawd/prospectos/discovered-domains.json"
EXISTING_SCRAPER = "/home/ubuntu/clawd/scripts/lead-scraper.py"

# Verticales + ciudades para búsqueda dinámica
SEARCH_QUERIES = [
    # Restaurantes / Catering
    ("restaurante delivery CDMX sitio web contacto", "Restaurante"),
    ("taqueria CDMX pedidos whatsapp contacto", "Restaurante"),
    ("catering corporativo CDMX cotización", "Catering"),
    ("dark kitchen CDMX menú contacto", "Restaurante"),
    # Clínicas
    ("clínica estética CDMX facial rejuvenecimiento contacto", "Clínica Estética"),
    ("cirugía plástica CDMX consulta contacto email", "Medicina Estética"),
    ("clínica nutrición CDMX pacientes contacto", "Nutrición"),
    ("clínica dermatología CDMX cita contacto", "Dermatología"),
    # Educación
    ("escuela baile CDMX clases contacto email", "Escuela de Baile"),
    ("academia música CDMX clases guitarra piano contacto", "Escuela de Música"),
    ("escuela cocina CDMX cursos chef contacto", "Escuela de Cocina"),
    ("idiomas inglés CDMX clases adultos contacto", "Idiomas"),
    # Servicios profesionales
    ("despacho arquitectura CDMX proyectos contacto email", "Arquitectura"),
    ("agencia marketing digital CDMX clientes cotización", "Marketing"),
    ("consultoría RRHH CDMX reclutamiento empresas contacto", "RRHH"),
    ("contaduría fiscal CDMX empresas servicios contacto", "Contabilidad"),
    ("notaría CDMX servicios legales contacto email", "Legal"),
    # Bienestar
    ("centro meditación yoga CDMX clases inscripción contacto", "Yoga"),
    ("spa masajes CDMX reservaciones contacto email", "Spa"),
    ("barbería premium CDMX cortes citas contacto", "Barbería"),
    ("tatuajes estudio CDMX cita diseño contacto", "Estudio de Tatuajes"),
    # Animales
    ("hotel perros mascotas CDMX guardería canina contacto", "Pet Hotel"),
    ("tienda mascotas CDMX accesorios comida contacto", "Pet Shop"),
    # Retail / Otros
    ("floristería CDMX envío a domicilio whatsapp contacto", "Floristería"),
    ("pastelería personalizada CDMX pedidos contacto email", "Pastelería"),
    ("joyería artesanal CDMX piezas contacto email", "Joyería"),
    ("renta salón eventos CDMX cotización contacto", "Eventos"),
    # Monterrey
    ("veterinaria Monterrey clínica mascotas contacto email", "Veterinaria MTY"),
    ("spa masajes Monterrey citas contacto email", "Spa MTY"),
    ("escuela idiomas Monterrey inglés francés contacto", "Idiomas MTY"),
    # Guadalajara
    ("clínica dental Guadalajara cita contacto email", "Dental GDL"),
    ("gimnasio crossfit Guadalajara membresías contacto", "Fitness GDL"),
    ("fotografía bodas Guadalajara cotización contacto email", "Fotografía GDL"),
]

# Dominios a excluir (directorios, redes sociales, etc.)
EXCLUDE_DOMAINS = {
    "google.com", "facebook.com", "instagram.com", "twitter.com", "youtube.com",
    "linkedin.com", "yelp.com", "tripadvisor.com", "foursquare.com",
    "mercadolibre.com", "amazon.com", "walmart.com", "liverpool.com",
    "wikipedia.org", "gobierno.mx", "gob.mx", "cdmx.gob.mx",
    "bing.com", "yahoo.com", "pinterest.com", "tiktok.com",
    "duckduckgo.com", "maps.google.com",
}


def search_duckduckgo(query, max_results=8):
    """Busca en DuckDuckGo HTML y extrae URLs de resultados."""
    urls = []
    try:
        encoded = quote_plus(query)
        url = f"https://html.duckduckgo.com/html/?q={encoded}"
        r = requests.get(url, headers=HEADERS, timeout=10)
        if r.status_code != 200:
            return urls
        # Extraer URLs de resultados orgánicos
        pattern = re.compile(r'class="result__url"[^>]*>\s*([^<\s]+)')
        found = pattern.findall(r.text)
        for raw in found:
            raw = raw.strip()
            if not raw.startswith('http'):
                raw = 'https://' + raw
            parsed = urlparse(raw)
            domain = parsed.netloc.lower().replace('www.', '')
            if not domain:
                continue
            if any(excl in domain for excl in EXCLUDE_DOMAINS):
                continue
            # Preferir dominios .mx o .com.mx
            full_url = f"https://www.{domain}/" if not raw.startswith('https://www.') else raw
            if full_url not in urls:
                urls.append(full_url)
            if len(urls) >= max_results:
                break
    except Exception as e:
        print(f"  Error buscando '{query[:40]}': {e}")
    return urls


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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--limit', type=int, default=len(SEARCH_QUERIES))
    parser.add_argument('--vertical', type=str, default=None)
    parser.add_argument('--city', type=str, default=None)
    args = parser.parse_args()

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Domain Discovery iniciado")

    existing_domains = load_existing_urls()
    discovered_data = load_discovered()
    already_known = {urlparse(d['url']).netloc.lower().replace('www.', '')
                     for d in discovered_data.get('discovered', [])}
    already_known.update(existing_domains)

    queries = SEARCH_QUERIES[:args.limit]
    new_found = []
    total = 0

    for i, (query, vertical) in enumerate(queries, 1):
        if args.vertical and args.vertical.lower() not in vertical.lower():
            continue
        print(f"  [{i}/{len(queries)}] {vertical}: {query[:50]}...")
        urls = search_duckduckgo(query, max_results=6)
        added = 0
        for url in urls:
            domain = urlparse(url).netloc.lower().replace('www.', '')
            if domain not in already_known:
                new_found.append({"url": url, "vertical": vertical, "discovered": datetime.now().isoformat()[:10]})
                already_known.add(domain)
                added += 1
                total += 1
        print(f"    → {added} nuevos dominios")
        time.sleep(1.5)  # Rate limit cortesía

    if new_found:
        discovered_data['discovered'] = discovered_data.get('discovered', []) + new_found
        discovered_data['last_updated'] = datetime.now().isoformat()
        save_discovered(discovered_data)
        print(f"\n✅ {total} nuevos dominios guardados en {OUTPUT_FILE}")
        print(f"   Total acumulado: {len(discovered_data['discovered'])}")
    else:
        print("\n⚠️  No se encontraron dominios nuevos")

    return total


if __name__ == '__main__':
    main()
