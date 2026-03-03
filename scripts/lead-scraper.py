#!/usr/bin/env python3
"""
Lead Scraper EZContact — Busca emails de negocios en CDMX y ZM
Versión 3.0 — 3 mar 2026

Fixes v3:
  - Decodifica HTML entities y URL-encoded chars antes de extraer emails
  - Filtra emails con caracteres inválidos (%, \\u003e, etc.)
  - Validación estricta de email antes de guardar
  - Nombre del negocio extraído del <title> de la página
  - Already-sent persistente para no repetir
"""

import requests
import re
import time
import json
import os
import html as html_module
from datetime import datetime
from urllib.parse import urljoin, urlparse, unquote

# ─── Config ───────────────────────────────────────────────────────────────────
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# Regex para emails — solo caracteres permitidos por RFC5321
EMAIL_REGEX = re.compile(
    r'(?<![%\\>])'                          # no precedido de % \ >
    r'\b([A-Za-z0-9][A-Za-z0-9._%+\-]*'    # local part (no empieza con .)
    r'@[A-Za-z0-9.\-]+\.[A-Za-z]{2,})\b'   # dominio
)

# Regex para extraer <title>
TITLE_REGEX = re.compile(r'<title[^>]*>([^<]{3,80})</title>', re.IGNORECASE)

EXCLUDE_DOMAINS = {
    "example.com", "test.com", "sentry.io", "ueni.com", "yourname.com",
    "wordpress.com", "wixpress.com", "squarespace.com", "godaddy.com",
    "google.com", "facebook.com", "instagram.com", "twitter.com",
    "youtube.com", "gmail.com", "hotmail.com", "yahoo.com", "outlook.com",
    "w3.org", "schema.org", "gmbstart.com", "schedulista.com",
    "dominio.com", "domain.com", "yourcompany.com", "tuempresa.com",
    "correo.com", "email.com", "mail.com", "ejemplo.com",
    "wix.com", "weebly.com",
}

EXCLUDE_PATTERNS = [
    'wix', 'square', 'shopify', 'wordpress', 'example', 'test@', 'demo@',
    'usuario@', 'icono-ml', 'user@', 'info@domain', 'noreply', 'no-reply',
    'donotreply', 'example@', 'sample@', 'placeholder', 'email@email',
    'ejemplo@',
]

ALREADY_SENT_FILE = "/home/ubuntu/clawd/memory/already-sent.json"
TODAY = datetime.now().strftime('%Y-%m-%d')
OUTPUT_FILE = f"/home/ubuntu/clawd/prospectos/leads-auto-{TODAY}.json"

# ─── 130+ sitios en 25+ verticales — CDMX y ZM ────────────────────────────────
SEARCH_TARGETS = [
    # Yoga / Pilates
    ("https://www.bikramyogamexico.com/", "Yoga"),
    ("https://www.yogaenred.com/", "Yoga"),
    ("https://pilatescondesa.com/", "Pilates"),
    ("https://www.pilatesreforma.com.mx/", "Pilates"),
    ("https://www.corepilatesmx.com/", "Pilates"),
    ("https://www.studiosoulmx.com/", "Pilates"),
    ("https://www.pilatescenter.com.mx/", "Pilates"),

    # Fitness / Gym
    ("https://www.evolutionfitness.com.mx/", "Gimnasio"),
    ("https://www.ironbodyfit.mx/", "Gimnasio"),
    ("https://inpeak.fit/", "Fitness"),
    ("https://www.crossfitrederadmx.com/", "CrossFit"),
    ("https://www.boxingclub.com.mx/", "Artes Marciales"),
    ("https://www.academiataekyondo.mx/", "Artes Marciales"),

    # Spa / Bienestar
    ("https://www.desertikaspa.com/", "Spa"),
    ("https://www.spalaxavitus.com/", "Spa"),
    ("https://rainforestmassagespa.com.mx/", "Spa"),
    ("https://www.endharma.com/", "Spa"),
    ("https://www.erapamx.com/", "Spa"),
    ("https://www.mandarina.mx/", "Spa"),

    # Dental
    ("https://laclinicadental.org/", "Dental"),
    ("https://www.clinicadrdiente.com/", "Dental"),
    ("https://www.odontologiaintegral.com.mx/", "Dental"),
    ("https://www.dentalpolanco.com/", "Dental"),
    ("https://www.clinicadentalroma.com/", "Dental"),
    ("https://www.dentistascdmx.com/", "Dental"),

    # Dermatología / Estética
    ("https://marialinda.mx/", "Dermatología"),
    ("https://studioderma.mx/", "Dermatología"),
    ("https://dermedical.com.mx/", "Dermatología"),
    ("https://www.cidiface.com/", "Medicina Estética"),
    ("https://www.dermapolanco.com/", "Dermatología"),
    ("https://www.clinicaesthetique.com.mx/", "Medicina Estética"),

    # Fisioterapia
    ("https://www.therapy.com.mx/", "Fisioterapia"),
    ("https://www.equilibriodinamico.mx/", "Fisioterapia"),
    ("https://www.fisioterapiacdmx.com/", "Fisioterapia"),

    # Psicología / Coaching
    ("https://www.centropsi.mx/", "Psicología"),
    ("https://www.mindfulnessmexico.com.mx/", "Coaching"),
    ("https://www.coachingejecutivo.com.mx/", "Coaching"),
    ("https://www.institutocoaching.mx/", "Coaching"),
    ("https://www.terapiacdmx.com/", "Psicología"),

    # Nutrición
    ("https://www.nutriologacdmx.com/", "Nutrición"),
    ("https://www.nutrisalud.mx/", "Nutrición"),
    ("https://dratorres.com.mx/", "Nutrición"),

    # Veterinaria
    ("https://cemegatos.com.mx/", "Veterinaria"),
    ("https://www.vetalia.com.mx/", "Veterinaria"),
    ("https://www.hospitalveterinariopolanco.com/", "Veterinaria"),
    ("https://www.clinicavet.mx/", "Veterinaria"),
    ("https://www.vetmex.com.mx/", "Veterinaria"),

    # Guarderías / Preescolar
    ("https://www.guarderiaskidsclub.com.mx/", "Guardería"),
    ("https://www.centroinfantilmx.com/", "Guardería"),
    ("https://www.guarderiasmontessori.mx/", "Guardería"),

    # Escuelas / Idiomas
    ("https://ihmexico.mx/", "Idiomas"),
    ("https://theangloacademy.mx/", "Idiomas"),
    ("https://www.harmon-hall.edu.mx/", "Idiomas"),
    ("https://www.proeducacion.com.mx/", "Idiomas"),
    ("https://escueladeinglescdmx.com/", "Idiomas"),
    ("https://www.cfn.edu.mx/", "Escuela"),
    ("https://www.exea.edu.mx/", "Escuela"),
    ("https://www.colegiocuauhtemoc.edu.mx/", "Escuela"),
    ("https://dancecenter.com.mx/", "Escuela de Baile"),

    # Cocina / Gastronomía
    ("https://www.esgamex.com/", "Cocina"),
    ("https://ismm.com.mx/", "Cocina"),
    ("https://ambrosiacentroculinario.edu.mx/", "Cocina"),
    ("https://www.arteculinariomx.com/", "Cocina"),

    # Catering / Eventos
    ("https://berlioz.mx/", "Catering"),
    ("https://tentenpie.mx/", "Catering"),
    ("https://www.cateringmex.com/", "Catering"),
    ("https://www.fiestasydecoracion.mx/", "Eventos"),
    ("https://www.organizaciondeeventos.mx/", "Eventos"),
    ("https://www.banquetesroyal.mx/", "Catering"),
    ("https://www.luxuryevents.mx/", "Eventos"),

    # Fotografía / Video
    ("https://fifteenstudio.com.mx/", "Fotografía"),
    ("https://celebrastudio.com/", "Fotografía"),
    ("https://www.fotografocdmx.com/", "Fotografía"),
    ("https://www.videoboda.mx/", "Fotografía"),

    # Inmobiliaria
    ("https://www.coldwellbanker.com.mx/", "Inmobiliaria"),
    ("https://www.sothebysrealty.com.mx/", "Inmobiliaria"),
    ("https://www.propiedadescdmx.com/", "Inmobiliaria"),
    ("https://casas.mx/", "Inmobiliaria"),
    ("https://www.coldwellbankerpolanco.com/", "Inmobiliaria"),

    # Reclutamiento / RRHH
    ("https://www.adecco.com.mx/", "Reclutamiento"),
    ("https://www.manpowergroup.com.mx/", "Reclutamiento"),
    ("https://talentomx.com/", "Reclutamiento"),
    ("https://www.hunter-rrhh.com/", "Reclutamiento"),

    # Contabilidad / Legal
    ("https://www.fiscalistas.com.mx/", "Contabilidad"),
    ("https://www.contadorescdmx.com/", "Contabilidad"),
    ("https://www.abogadoscdmx.mx/", "Legal"),
    ("https://www.bufetejuridico.mx/", "Legal"),

    # Agencias de viaje
    ("https://www.bestday.com.mx/", "Viajes"),
    ("https://www.price.travel/", "Viajes"),
    ("https://www.mexicotravel.mx/", "Viajes"),
    ("https://www.viajeseldorado.com.mx/", "Viajes"),

    # Educación / Cursos
    ("https://www.cenhies.edu.mx/", "Educación"),
    ("https://www.unitec.edu.mx/", "Educación"),
    ("https://www.uvm.edu.mx/", "Educación"),

    # Clínicas médicas
    ("https://www.medicosapedido.com/", "Clínica"),
    ("https://www.clinicadelasalud.com.mx/", "Clínica"),
    ("https://www.topdoctors.es/mexico", "Clínica"),

    # Restaurantes / Food
    ("https://www.lacocinadesofiarestaurante.com/", "Restaurante"),
    ("https://www.paneenvia.com/", "Restaurante"),
    ("https://www.cafeninodios.mx/", "Restaurante"),

    # Transporte / Logística
    ("https://www.estafeta.com/", "Logística"),
    ("https://www.sendex.com.mx/", "Logística"),
    ("https://www.paquetexpress.com.mx/", "Logística"),

    # Lavandería / Limpieza
    ("https://www.limp-mex.com.mx/", "Lavandería"),
    ("https://lavanderiascdmx.com/", "Lavandería"),

    # Música / Arte
    ("https://www.escuelademusica.mx/", "Música"),
    ("https://www.artesaniasmx.com/", "Arte"),
    ("https://www.galeriadearte.mx/", "Arte"),

    # Tecnología / IT
    ("https://www.desarrolloweb.mx/", "Tecnología"),
    ("https://www.softwareamexico.com/", "Tecnología"),
]

# Páginas adicionales a revisar en cada sitio
CONTACT_PATHS = [
    "/contacto", "/contact", "/contacto/", "/contact/",
    "/nosotros", "/about", "/nos-contacto", "/quienes-somos",
    "/informacion/contacto",
]


def load_already_sent():
    """Carga emails ya enviados desde archivo persistente."""
    if not os.path.exists(ALREADY_SENT_FILE):
        return set()
    try:
        with open(ALREADY_SENT_FILE) as f:
            data = json.load(f)
        return set(data.get("emails", []))
    except Exception:
        return set()


def save_already_sent(sent_set):
    """Guarda emails enviados al archivo persistente."""
    try:
        existing = load_already_sent()
        merged = existing | sent_set
        with open(ALREADY_SENT_FILE, 'w') as f:
            json.dump({
                "emails": sorted(list(merged)),
                "last_updated": TODAY
            }, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Warning: no pude guardar already-sent: {e}")


def clean_text(raw_html: str) -> str:
    """Decodifica HTML entities y URL encoding para limpiar el texto antes de extraer emails."""
    # 1. Decodifica HTML entities (&amp; &gt; &#64; etc.)
    text = html_module.unescape(raw_html)
    # 2. Decodifica URL encoding (%40 → @ etc.)
    text = unquote(text)
    # 3. Quita unicode escapes literales (\u003e → >)
    text = text.replace('\\u003e', '>').replace('\\u003c', '<')
    text = text.replace('\\u0040', '@')
    return text


def is_valid_email(email: str) -> bool:
    """Validación estricta de email."""
    # No debe contener caracteres de encoding
    if any(c in email for c in ['%', '\\', '\u003e', '\u003c']):
        return False
    # El local-part no debe empezar con dígito-seguido-por-encoding
    if re.search(r'^[0-9]+[a-f]{2}', email.split('@')[0]):
        return False
    # Solo caracteres RFC5321 válidos
    if not re.match(r'^[A-Za-z0-9][A-Za-z0-9._%+\-]*@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$', email):
        return False
    # Longitud razonable
    if len(email) > 100 or len(email) < 6:
        return False
    return True


def extract_business_name(text: str, fallback_url: str) -> str:
    """Extrae nombre del negocio del <title> de la página."""
    match = TITLE_REGEX.search(text)
    if match:
        title = match.group(1).strip()
        # Limpiar separadores comunes: "Empresa | Slogan" → "Empresa"
        for sep in [' | ', ' – ', ' - ', ' :: ', ' · ']:
            if sep in title:
                title = title.split(sep)[0].strip()
        if title and len(title) > 2:
            return title
    # Fallback: extraer dominio limpio
    domain = urlparse(fallback_url).netloc
    domain = domain.replace('www.', '').split('.')[0].title()
    return domain


def get_emails_from_url(url, already_sent, timeout=10):
    """Fetch URL, decodifica y extrae emails nuevos."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        if r.status_code != 200:
            return [], ""
        raw_text = r.text
        # Extraer nombre del negocio antes de limpiar (para el title tag)
        business_name = extract_business_name(raw_text, url)
        # Limpiar texto para extracción segura de emails
        clean = clean_text(raw_text)
        # Extraer emails
        raw_emails = EMAIL_REGEX.findall(clean)
        valid = []
        for e in raw_emails:
            e = e.lower().strip('.').strip()
            # Validaciones
            if not is_valid_email(e):
                continue
            domain = e.split('@')[1]
            if not domain.endswith('.mx'):
                continue
            if domain in EXCLUDE_DOMAINS:
                continue
            if any(x in e for x in EXCLUDE_PATTERNS):
                continue
            if e in already_sent:
                continue
            if e not in valid:
                valid.append(e)
        return valid, business_name
    except Exception as ex:
        return [], ""


def scrape_site(base_url, vertical, already_sent):
    """Intenta main page y páginas de contacto."""
    emails, biz_name = get_emails_from_url(base_url, already_sent)
    if not emails:
        for path in CONTACT_PATHS:
            url = urljoin(base_url, path)
            emails, biz_name_contact = get_emails_from_url(url, already_sent)
            if emails:
                if biz_name_contact and len(biz_name_contact) > len(biz_name):
                    biz_name = biz_name_contact
                break
        time.sleep(0.3)
    results = []
    for e in emails:
        results.append({
            "email": e,
            "vertical": vertical,
            "source": base_url,
            "business_name": biz_name,
        })
    return results


def main():
    print(f"🔍 Lead Scraper EZContact v3.0 — {TODAY}")
    already_sent = load_already_sent()
    # Cargar leads ya encontrados hoy (para no duplicar entre corridas)
    seen_today = set()
    if os.path.exists(OUTPUT_FILE):
        try:
            with open(OUTPUT_FILE) as f:
                existing = json.load(f)
            seen_today = {l["email"] for l in existing}
            all_leads = existing
        except Exception:
            all_leads = []
    else:
        all_leads = []

    total_checked = 0
    total_new = 0
    start_time = time.time()

    for i, (url, vertical) in enumerate(SEARCH_TARGETS):
        domain = urlparse(url).netloc
        if total_new >= 80:  # límite diario conservador
            print(f"  ✅ Límite alcanzado ({total_new} leads)")
            break
        try:
            results = scrape_site(url, vertical, already_sent | seen_today)
            total_checked += 1
            if results:
                for lead in results:
                    all_leads.append(lead)
                    seen_today.add(lead["email"])
                    total_new += 1
                    print(f"  ✉️  {lead['email']} [{vertical}] — {lead.get('business_name', '')} ")
        except Exception as e:
            pass  # continuar aunque falle un sitio
        time.sleep(0.8)  # respetuoso con los servidores

    # Guardar resultados
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(all_leads, f, indent=2, ensure_ascii=False)

    elapsed = time.time() - start_time
    print(f"\n📊 Resumen:")
    print(f"   Sitios revisados: {total_checked}/{len(SEARCH_TARGETS)}")
    print(f"   Leads nuevos hoy: {total_new}")
    print(f"   Total en archivo: {len(all_leads)}")
    print(f"   Archivo:          {OUTPUT_FILE}")
    print(f"   Tiempo:           {elapsed:.0f}s")


if __name__ == "__main__":
    main()
