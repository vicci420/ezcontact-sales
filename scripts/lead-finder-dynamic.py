#!/usr/bin/env python3
"""
Lead Finder Dinámico — busca emails de negocios en México
usando búsquedas web reales, no lista hardcodeada.
Extrae emails directamente de resultados de búsqueda.
"""

import json
import re
import os
import sys
import time
import requests
from datetime import datetime
from urllib.parse import urlparse

ALREADY_SENT_FILE = "/home/ubuntu/clawd/memory/already-sent.json"
OUTPUT_DIR = "/home/ubuntu/clawd/prospectos"

EMAIL_REGEX = re.compile(r'\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[a-zA-Z]{2,}\b')

EXCLUDE_DOMAINS = {
    "example.com","test.com","sentry.io","ueni.com","yourname.com",
    "wordpress.com","wixpress.com","squarespace.com","godaddy.com",
    "google.com","facebook.com","instagram.com","twitter.com",
    "youtube.com","gmail.com","hotmail.com","yahoo.com","outlook.com",
    "w3.org","schema.org","gmbstart.com","schedulista.com",
    "dominio.com","domain.com","yourcompany.com","tuempresa.com",
    "correo.com","email.com","mail.com","icloud.com","live.com",
}

EXCLUDE_PATTERNS = [
    'wix','square','shopify','wordpress','example','ejemplo','test@','demo@',
    'usuario@','icono-ml','20contacto','user@','info@domain','noreply',
    'no-reply','donotreply','admin@','webmaster@','postmaster@',
    'support@','soporte@','help@','hello@sentry','privacy@',
    'contact@example','foo@','bar@','test123',
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
}

# Búsquedas: query + vertical
SEARCH_QUERIES = [
    # Salud y bienestar
    ('clínica dermatológica CDMX "contacto" "@" ".mx"', "Dermatología"),
    ('psicólogo terapia CDMX "contacto" "@" ".mx"', "Psicología"),
    ('fisioterapia rehabilitación CDMX correo "@" ".mx"', "Fisioterapia"),
    ('nutrióloga nutricionista CDMX email "@" ".mx"', "Nutrición"),
    ('clínica estética CDMX "escríbenos" "@" ".mx"', "Estética"),
    ('laboratorio análisis clínicos CDMX "@" ".mx"', "Laboratorio"),
    ('consultorio médico pediatra CDMX "@" ".mx"', "Médico"),
    ('oftalmólogo clínica visual CDMX "@" ".mx"', "Oftalmología"),
    # Fitness y deporte
    ('academia taekwondo karate CDMX email "@" ".mx"', "Artes Marciales"),
    ('box crossfit funcional CDMX contacto "@" ".mx"', "CrossFit"),
    ('entrenador personal CDMX "@" ".mx"', "Fitness"),
    ('natación clases adultos CDMX "@" ".mx"', "Natación"),
    ('yoga meditación clases CDMX "@" ".mx"', "Yoga"),
    ('spinning cycling CDMX email contacto "@" ".mx"', "Fitness"),
    # Educación
    ('escuela cocina gastronomía CDMX "@" ".mx"', "Cocina"),
    ('colegio bilingüe primaria CDMX "@" ".edu.mx"', "Escuela"),
    ('idiomas inglés japonés CDMX escuela "@" ".mx"', "Idiomas"),
    ('clases música piano guitarra CDMX "@" ".mx"', "Música"),
    ('academia danza ballet CDMX "@" ".mx"', "Danza"),
    ('clases dibujo pintura arte CDMX "@" ".mx"', "Arte"),
    # Belleza y cuidado personal
    ('salón de belleza peluquería polanco condesa "@" ".mx"', "Salón de Belleza"),
    ('barbería hombre CDMX email "@" ".mx"', "Barbería"),
    ('uñas nail studio CDMX "@" ".mx"', "Uñas"),
    ('maquillaje makeup artista CDMX "@" ".mx"', "Maquillaje"),
    ('extensiones pestañas CDMX "@" ".mx"', "Pestañas"),
    # Mascotas
    ('clínica veterinaria CDMX "@" ".mx"', "Veterinaria"),
    ('estética canina grooming CDMX "@" ".mx"', "Estética Canina"),
    ('hotel para mascotas CDMX "@" ".mx"', "Mascotas"),
    # Servicios del hogar
    ('remodelación hogar CDMX "@" ".mx"', "Remodelación"),
    ('diseño interiores decoración CDMX "@" ".mx"', "Diseño Interiores"),
    ('plomería electricista CDMX contacto "@" ".mx"', "Servicios Hogar"),
    ('mudanzas fletes CDMX email "@" ".mx"', "Mudanzas"),
    ('lavandería tintorería CDMX "@" ".mx"', "Lavandería"),
    ('jardinería paisajismo CDMX "@" ".mx"', "Jardinería"),
    # Gastronomía y eventos
    ('catering banquetes eventos CDMX "@" ".mx"', "Catering"),
    ('repostería pasteles personalizados CDMX "@" ".mx"', "Repostería"),
    ('chef a domicilio CDMX "@" ".mx"', "Gastronomía"),
    ('organizadora bodas eventos CDMX "@" ".mx"', "Eventos"),
    ('fotografía bodas CDMX estudio "@" ".mx"', "Fotografía"),
    # Autos
    ('taller mecánico CDMX cotización "@" ".mx"', "Taller Mecánico"),
    ('detailing lavado autos CDMX "@" ".mx"', "Detailing Autos"),
    # B2B y profesional
    ('despacho contable fiscal CDMX "@" ".mx"', "Contabilidad"),
    ('agencia marketing digital CDMX pymes "@" ".mx"', "Marketing"),
    ('diseño web desarrollo CDMX negocio "@" ".mx"', "Diseño Web"),
    ('consultoría recursos humanos CDMX "@" ".mx"', "RRHH"),
    ('seguros empresas CDMX agente "@" ".mx"', "Seguros"),
    # Retail y specialty
    ('tienda ropa boutique CDMX contacto "@" ".mx"', "Retail"),
    ('floristería flores CDMX "@" ".mx"', "Floristería"),
    ('papelería artículos escolares CDMX "@" ".mx"', "Papelería"),
    ('optica lentes CDMX "@" ".mx"', "Óptica"),
    ('joyería platería CDMX "@" ".mx"', "Joyería"),
]

def load_already_sent():
    if not os.path.exists(ALREADY_SENT_FILE):
        return set()
    try:
        with open(ALREADY_SENT_FILE) as f:
            data = json.load(f)
        return set(e.lower() for e in data.get("emails", []))
    except Exception:
        return set()

def is_valid_email(email, already_sent):
    e = email.lower().strip()
    if e in already_sent:
        return False
    domain = e.split('@')[-1] if '@' in e else ''
    if domain in EXCLUDE_DOMAINS:
        return False
    if not domain.endswith('.mx') and not domain.endswith('.com.mx') and \
       not domain.endswith('.edu.mx') and not domain.endswith('.net.mx') and \
       not domain.endswith('.org.mx'):
        # Allow .com only if clearly a Mexico business (heuristic: check patterns)
        if not any(kw in domain for kw in ['mexico','mex','cdmx']):
            return False
    for pat in EXCLUDE_PATTERNS:
        if pat in e:
            return False
    local = e.split('@')[0]
    if len(local) < 3:
        return False
    # Skip emails that look generic/fake
    if local in ['info','contacto','contact','hola','hello','ventas','sales',
                 'admin','administracion','rrhh','facturacion','tesoreria']:
        # Keep these — they are valid business contacts
        pass
    return True

def search_and_extract(query, vertical, brave_api_key, already_sent, found_emails):
    """Search Brave and extract emails from snippets; crawl top sites when snippet has none."""
    url = "https://api.search.brave.com/res/v1/web/search"
    params = {"q": query, "count": 10, "country": "MX", "search_lang": "es"}
    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "X-Subscription-Token": brave_api_key,
    }
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        if resp.status_code != 200:
            return []
        data = resp.json()
        results = data.get("web", {}).get("results", [])
        leads = []
        urls_to_crawl = []

        for r in results:
            # 1) Extract from snippet first (fast)
            text = r.get("description", "") + " " + r.get("title", "")
            emails_found = EMAIL_REGEX.findall(text)
            url_site = r.get("url", "")
            snippet_had_email = False
            for email in emails_found:
                email = email.lower().strip('.,;:')
                if is_valid_email(email, already_sent) and email not in found_emails:
                    found_emails.add(email)
                    leads.append({
                        "email": email,
                        "vertical": vertical,
                        "source": url_site or query,
                        "query": query,
                    })
                    snippet_had_email = True
            # 2) If no email in snippet, queue site for crawl (top 5 per query)
            if not snippet_had_email and url_site and len(urls_to_crawl) < 5:
                # Skip social media and directories — crawl actual business sites
                parsed = urlparse(url_site)
                skip_domains = {'facebook.com','instagram.com','twitter.com','yelp.com',
                                'google.com','youtube.com','wikipedia.org','linkedin.com',
                                'tripadvisor.com','mercadolibre.com','amazon.com.mx'}
                if not any(sd in parsed.netloc for sd in skip_domains):
                    urls_to_crawl.append(url_site)

        # 3) Crawl queued URLs (fetch_site_emails was previously defined but never called)
        for site_url in urls_to_crawl:
            site_leads = fetch_site_emails(site_url, vertical, already_sent, found_emails)
            for sl in site_leads:
                sl["query"] = query
            leads.extend(site_leads)
            time.sleep(0.3)  # polite crawl rate

        return leads
    except Exception as e:
        return []

def fetch_site_emails(url, vertical, already_sent, found_emails):
    """Fetch a website and extract email addresses. Limits download to 200KB for speed."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=8, allow_redirects=True, stream=True)
        # Read up to 200KB — enough to find emails in contact pages
        content = b""
        for chunk in resp.iter_content(chunk_size=8192):
            content += chunk
            if len(content) > 200_000:
                break
        text = content.decode('utf-8', errors='ignore')
        emails = EMAIL_REGEX.findall(text)
        leads = []
        for email in emails:
            email = email.lower().strip('.,;:')
            if is_valid_email(email, already_sent) and email not in found_emails:
                found_emails.add(email)
                leads.append({
                    "email": email,
                    "vertical": vertical,
                    "source": url,
                })
        return leads
    except Exception:
        return []

def main():
    # Load Brave API key from vault or env
    brave_key = None
    try:
        import subprocess
        r = subprocess.run(["vault", "get", "api/brave"], capture_output=True, text=True, timeout=5)
        brave_key = r.stdout.strip()
    except Exception:
        pass
    if not brave_key:
        brave_key = os.environ.get("BRAVE_API_KEY", "")

    already_sent = load_already_sent()
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Ya enviados: {len(already_sent)} emails (skip automático)")

    all_leads = []
    found_emails = set()

    if brave_key:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Modo búsqueda dinámica ({len(SEARCH_QUERIES)} queries)...")
        for i, (query, vertical) in enumerate(SEARCH_QUERIES, 1):
            print(f"[{i}/{len(SEARCH_QUERIES)}] {vertical}: {query[:60]}...", end=" ")
            leads = search_and_extract(query, vertical, brave_key, already_sent, found_emails)
            print(f"→ {len(leads)} emails")
            all_leads.extend(leads)
            time.sleep(0.5)
    else:
        print("⚠️  No hay Brave API key configurada. Necesitas correr: vault set api/brave <key>")
        sys.exit(1)

    # Save results
    today = datetime.now().strftime('%Y-%m-%d')
    out_path = f"{OUTPUT_DIR}/leads-dynamic-{today}.json"
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(all_leads, f, indent=2, ensure_ascii=False)

    print(f"\n✅ {len(all_leads)} leads nuevos → {out_path}")
    if all_leads:
        by_vertical = {}
        for l in all_leads:
            by_vertical[l['vertical']] = by_vertical.get(l['vertical'], 0) + 1
        print("\nPor vertical:")
        for v, n in sorted(by_vertical.items(), key=lambda x: -x[1]):
            print(f"  {v}: {n}")

if __name__ == "__main__":
    main()
