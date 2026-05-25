#!/usr/bin/env python3
"""
Lead Scraper EZContact - Busca emails de negocios en CDMX
Verticales: spa, dental, fitness, idiomas, cocina, inmobiliaria, veterinaria, etc.

v3 - Personalización Dinámica:
  - Extrae nombre del negocio de cada sitio (og:site_name, title, dominio)
  - Guarda business_name en leads JSON para personalizar emails
  - Lista de ya-contactados desde archivo persistente (memory/already-sent.json)
  - 130+ sitios en 25+ verticales
  - Auto-skip de duplicados entre corridas
"""

import requests
import re
import time
import json
import os
from datetime import datetime
from urllib.parse import urljoin, urlparse

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
}

EMAIL_REGEX = re.compile(r'\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b')

EXCLUDE_DOMAINS = {
    "example.com", "test.com", "sentry.io", "ueni.com", "yourname.com",
    "wordpress.com", "wixpress.com", "squarespace.com", "godaddy.com",
    "google.com", "facebook.com", "instagram.com", "twitter.com",
    "youtube.com", "gmail.com", "hotmail.com", "yahoo.com", "outlook.com",
    "w3.org", "schema.org", "gmbstart.com", "schedulista.com",
    "dominio.com", "domain.com", "yourcompany.com", "tuempresa.com",
    "correo.com", "email.com", "mail.com",
}

EXCLUDE_PATTERNS = [
    'wix', 'square', 'shopify', 'wordpress', 'example', 'test@', 'demo@',
    'usuario@', 'icono-ml', '20contacto', 'user@', 'info@domain',
]

ALREADY_SENT_FILE = "/home/ubuntu/clawd/memory/already-sent.json"

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
        with open(ALREADY_SENT_FILE, 'w') as f:
            json.dump({
                "emails": sorted(list(sent_set)),
                "last_updated": datetime.now().strftime('%Y-%m-%d')
            }, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Warning: no pude guardar already-sent: {e}")


# ============================================================
# Extracción de nombre de negocio (Personalización Dinámica)
# ============================================================

# Palabras genéricas que no aportan como nombre de negocio
_GENERIC_NAMES = {
    'inicio', 'home', 'bienvenido', 'bienvenidos', 'index', 'pagina', 'página',
    'sitio', 'web', 'contacto', 'nosotros', 'about', 'empresa', 'tienda',
    'mx', 'com', 'net', 'org', 'info', 'gob', 'edu',
}

def extract_business_name(html_text, base_url=""):
    """
    Extrae el nombre del negocio del HTML de la página.
    Jerarquía: og:site_name > twitter:site > <title> limpio > dominio.
    Retorna string con el nombre, o "" si no encontró nada confiable.
    """
    candidates = []

    # 1. og:site_name (más confiable — es el nombre explícito del sitio)
    for pattern in [
        r'<meta[^>]+property=["\']og:site_name["\'][^>]+content=["\']([^"\']{2,60})["\']',
        r'<meta[^>]+content=["\']([^"\']{2,60})["\'][^>]+property=["\']og:site_name["\']',
    ]:
        m = re.search(pattern, html_text, re.I)
        if m:
            name = m.group(1).strip()
            if name and name.lower() not in _GENERIC_NAMES:
                candidates.append(name)
                break

    # 2. twitter:site o application-name
    for pattern in [
        r'<meta[^>]+name=["\']application-name["\'][^>]+content=["\']([^"\']{2,60})["\']',
        r'<meta[^>]+content=["\']([^"\']{2,60})["\'][^>]+name=["\']application-name["\']',
    ]:
        m = re.search(pattern, html_text, re.I)
        if m:
            name = m.group(1).strip()
            if name and name.lower() not in _GENERIC_NAMES:
                candidates.append(name)
                break

    # 3. <title> limpio
    m = re.search(r'<title[^>]*>\s*([^<]{2,80}?)\s*</title>', html_text, re.I | re.S)
    if m:
        title = m.group(1).strip()
        # Eliminar sufijos después de separadores comunes
        for sep in [' | ', ' - ', ' – ', ' — ', ' · ', ' :: ', ' / ']:
            if sep in title:
                title = title.split(sep)[0].strip()
        if 2 <= len(title) <= 60 and title.lower() not in _GENERIC_NAMES:
            candidates.append(title)

    # 4. Fallback: dominio limpio (siempre disponible)
    try:
        domain = urlparse(base_url).netloc.replace('www.', '')
        # Tomar solo la parte antes del primer punto
        name = domain.split('.')[0]
        if len(name) > 2:
            # Convertir guiones/underscores a espacios y capitalizar
            name = name.replace('-', ' ').replace('_', ' ').title()
            candidates.append(name)
    except Exception:
        pass

    # Devolver el primer candidato válido
    return candidates[0] if candidates else ""


# ============================================================
# 130+ sitios en 25+ verticales — CDMX y zona metropolitana
# ============================================================
SEARCH_TARGETS = [
    # --- Yoga / Pilates ---
    ("https://www.bikramyogamexico.com/", "Yoga"),
    ("https://www.yogaenred.com/", "Yoga"),
    ("https://www.hotyogacdmx.com/", "Yoga"),
    ("https://pilatescondesa.com/", "Pilates"),
    ("https://www.pilatesreforma.com.mx/", "Pilates"),
    ("https://www.corepilatesmx.com/", "Pilates"),
    ("https://www.studiosoulmx.com/", "Pilates"),
    ("https://www.pilatescenter.com.mx/", "Pilates"),

    # --- Fitness / Gym ---
            ("https://www.evolutionfitness.com.mx/", "Gimnasio"),
    ("https://www.ironbodyfit.mx/", "Gimnasio"),
    ("https://www.clubdeportivomx.com/", "Gimnasio"),
    ("https://cf4.com.mx/", "CrossFit"),
    ("https://inpeak.fit/", "Fitness"),
    ("https://www.crossfitrederadmx.com/", "CrossFit"),
    ("https://www.boxingclub.com.mx/", "Artes Marciales"),
    ("https://www.academiataekyondo.mx/", "Artes Marciales"),

    # --- Spa / Bienestar ---
    ("https://www.spaenmexico.com.mx/", "Spa"),
    ("https://www.desertikaspa.com/", "Spa"),
    ("https://www.spalaxavitus.com/", "Spa"),
    ("https://rainforestmassagespa.com.mx/", "Spa"),
    ("https://www.endharma.com/", "Spa"),
    ("https://www.spapalacio.com.mx/", "Spa"),
    ("https://www.mandarina.mx/", "Spa"),
    ("https://www.etereo.mx/", "Spa"),
    ("https://www.cielo.mx/", "Spa"),

    # --- Dental ---
    ("https://laclinicadental.org/", "Dental"),
    ("https://www.clinicadrdiente.com/", "Dental"),
    ("https://www.implantesdentalesmm.com/", "Dental"),
    ("https://www.odontologiaintegral.com.mx/", "Dental"),
    ("https://www.dentalpolanco.com/", "Dental"),
    ("https://www.clinicadentalroma.com/", "Dental"),
    ("https://www.dentistascdmx.com/", "Dental"),
    ("https://www.sonrisacdmx.com/", "Dental"),

    # --- Dermatología / Estética ---
    ("https://marialinda.mx/", "Dermatología"),
    ("https://studioderma.mx/", "Dermatología"),
    ("https://dermedical.com.mx/", "Dermatología"),
    ("https://www.centroobesidad.com/", "Medicina Estética"),
    ("https://www.cidiface.com/", "Medicina Estética"),
    ("https://www.dermapolanco.com/", "Dermatología"),
    ("https://www.clinicaesthetique.com.mx/", "Medicina Estética"),
    ("https://www.depilacionlaser.com.mx/", "Estética"),

    # --- Fisioterapia / Rehab ---
    ("https://www.therapy.com.mx/", "Fisioterapia"),
    ("https://www.equilibriodinamico.mx/", "Fisioterapia"),
    ("https://rehabilitacion.holfer.com/", "Fisioterapia"),
    ("https://www.fisioterapiacdmx.com/", "Fisioterapia"),
    ("https://www.clinicarehabilitacion.mx/", "Fisioterapia"),
    ("https://www.sportsphysio.com.mx/", "Fisioterapia"),

    # --- Psicología / Coaching ---
    ("https://www.centropsi.mx/", "Psicología"),
    ("https://www.psicologiaybienestar.mx/", "Psicología"),
    ("https://www.mindfulnessmexico.com.mx/", "Coaching"),
    ("https://www.coachingejecutivo.com.mx/", "Coaching"),
    ("https://www.institutocoaching.mx/", "Coaching"),
    ("https://www.terapiacdmx.com/", "Psicología"),

    # --- Nutrición / Dietética ---
    ("https://www.nutriologacdmx.com/", "Nutrición"),
    ("https://www.centrodenutriciony.com/", "Nutrición"),
    ("https://www.nutrisalud.mx/", "Nutrición"),
    ("https://www.dietistamx.com/", "Nutrición"),

    # --- Veterinaria ---
    ("https://cemegatos.com.mx/", "Veterinaria"),
    ("https://www.vetalia.com.mx/", "Veterinaria"),
    ("https://www.hospitalveterinariopolanco.com/", "Veterinaria"),
    ("https://www.clinicavet.mx/", "Veterinaria"),
    ("https://www.vetmex.com.mx/", "Veterinaria"),
    ("https://www.perrosaparatos.com/", "Veterinaria"),
    ("https://www.mascotas.mx/", "Veterinaria"),

    # --- Guarderías / Preescolar ---
    ("https://www.guarderiaskidsclub.com.mx/", "Guardería"),
    ("https://www.centroinfantilmx.com/", "Guardería"),
    ("https://www.kinder.mx/", "Guardería"),
    ("https://www.guarderiasmontessori.mx/", "Guardería"),
    ("https://www.casadelosninosmx.com/", "Guardería"),
    ("https://www.preschoolmx.com/", "Guardería"),

    # --- Escuelas / Idiomas ---
    ("https://ihmexico.mx/", "Idiomas"),
        ("https://theangloacademy.mx/", "Idiomas"),
    ("https://www.harmon-hall.edu.mx/", "Idiomas"),
    ("https://www.proeducacion.com.mx/", "Idiomas"),
    ("https://escueladeinglescdmx.com/", "Idiomas"),
    ("https://www.cfn.edu.mx/", "Escuela"),
    ("https://www.exea.edu.mx/", "Escuela"),
    ("https://www.colegiocuauhtemoc.edu.mx/", "Escuela"),
    ("https://www.colegiomadero.edu.mx/", "Escuela"),
    ("https://www.britishschool.com.mx/", "Escuela"),

    # --- Cocina / Gastronomía ---
    ("https://www.esgamex.com/", "Cocina"),
    ("https://ismm.com.mx/", "Cocina"),
    ("https://ambrosiacentroculinario.edu.mx/", "Cocina"),
    ("https://www.lacocinadesofiarestaurante.com/", "Restaurante"),
    ("https://www.escueladecocinacdmx.com/", "Cocina"),
        ("https://www.arteculinariomx.com/", "Cocina"),

    # --- Catering / Eventos ---
    ("https://berlioz.mx/", "Catering"),
    ("https://www.latelierdecuisine.mx/", "Catering"),
    ("https://tentenpie.mx/", "Catering"),
    ("https://www.cateringmex.com/", "Catering"),
    ("https://www.fiestasydecoracion.mx/", "Eventos"),
    ("https://www.organizaciondeeventos.mx/", "Eventos"),
    ("https://www.eventospremium.com.mx/", "Eventos"),
    ("https://www.banquetesroyal.mx/", "Catering"),

    # --- Fotografía / Video ---
    ("https://fifteenstudio.com.mx/", "Fotografía"),
    ("https://celebrastudio.com/", "Fotografía"),
    ("https://www.fotografocdmx.com/", "Fotografía"),
    ("https://www.fotostudiomx.com/", "Fotografía"),
    ("https://www.videoboda.mx/", "Fotografía"),
    ("https://www.studiofotomx.com/", "Fotografía"),

    # --- Natación ---
    ("https://www.ccnatacion.com/", "Natación"),
    ("https://natacionmorsas.com/", "Natación"),
    ("https://www.zwemmen.mx/", "Natación"),
    ("https://www.clubnatacion.mx/", "Natación"),
    ("https://www.aquacdmx.com/", "Natación"),

    # --- Lavandería / Tintorería ---
    ("https://tintoretto.mx/", "Tintorería"),
    ("https://aspen.com.mx/", "Tintorería"),
    ("https://lavify.mx/", "Lavandería"),
    ("https://www.lavanderiaexpress.mx/", "Lavandería"),
    ("https://www.tintorerialazo.com/", "Tintorería"),
    ("https://www.cleanmaster.com.mx/", "Lavandería"),

    # --- Mudanzas ---
    ("https://www.mudanzasyfletes.org/", "Mudanzas"),
    ("https://www.sandovalfletesymudanzas.mx/", "Mudanzas"),
    ("https://mudandote.mx/", "Mudanzas"),
    ("https://www.transportesymudanzasloschavez.com/", "Mudanzas"),
    ("https://www.mudanzasmx.com/", "Mudanzas"),
    ("https://www.fasterfletes.com.mx/", "Mudanzas"),

    # --- Inmobiliaria ---
            ("https://www.inmobiliariamx.com/", "Inmobiliaria"),
    ("https://www.propiedades.com/mexico/", "Inmobiliaria"),
    ("https://www.viveinmuebles.mx/", "Inmobiliaria"),
    ("https://www.casasydepartamentos.com.mx/", "Inmobiliaria"),

    # --- Despachos Contables / Legales ---
    ("https://www.contadorescdmx.com/", "Contabilidad"),
    ("https://www.fiscalistas.mx/", "Contabilidad"),
    ("https://www.bufetecontable.mx/", "Contabilidad"),
    ("https://www.abogadoscdmx.com/", "Legal"),
    ("https://www.despacholegal.mx/", "Legal"),
    ("https://www.licenciadosmx.com/", "Legal"),

    # --- Agencias de Marketing ---
    ("https://www.agenciadigitalmx.com/", "Marketing"),
    ("https://www.marketingcdmx.mx/", "Marketing"),
    ("https://www.disenoweb.mx/", "Marketing"),
    ("https://www.socialmediadmx.com/", "Marketing"),

    # --- Viajes / Turismo ---
    ("https://www.travelium.com.mx/", "Viajes"),
    ("https://travelviajes.com.mx/", "Viajes"),
    ("https://www.agenciadeviajes.mx/", "Viajes"),
    ("https://www.turismocorporativo.mx/", "Viajes"),
    ("https://www.viajesexecutive.com.mx/", "Viajes"),

    # --- Laboratorios / Análisis Clínicos ---
    ("https://www.laboratorio.com.mx/", "Laboratorio"),
    ("https://www.labsanalisis.mx/", "Laboratorio"),
    ("https://www.clinicalab.mx/", "Laboratorio"),
    ("https://www.laboclinico.mx/", "Laboratorio"),

    # --- Música / Escuelas de Música ---
    ("https://www.escuelademusica.mx/", "Música"),
    ("https://www.musicdacademy.com.mx/", "Música"),
    ("https://www.conservatoriomx.edu.mx/", "Música"),
    ("https://www.studiomusica.mx/", "Música"),
    ("https://www.guitarracdmx.com/", "Música"),
    ("https://www.pianoclasescdmx.com/", "Música"),
    ("https://www.bossanova.com.mx/", "Música"),
    ("https://www.clasesbateria.mx/", "Música"),
    ("https://www.musiccenter.com.mx/", "Música"),
    ("https://www.escueladecantocdmx.com/", "Música"),

    # --- Fotografía / Estudio (adicionales) ---
    ("https://www.fotografomatrimonio.mx/", "Fotografía"),
    ("https://www.estudiosdefotografia.mx/", "Fotografía"),
    ("https://www.fotografosboda.com.mx/", "Fotografía"),
    ("https://www.fotografiacomercial.mx/", "Fotografía"),
    ("https://www.fotograforetrato.mx/", "Fotografía"),
    ("https://www.estudiofotografiamx.com/", "Fotografía"),
    ("https://www.fotografiaproductos.mx/", "Fotografía"),
    ("https://www.fotografiaembarazo.mx/", "Fotografía"),

    # --- Arquitectura / Diseño de Interiores ---
    ("https://www.arquitectoscdmx.com/", "Arquitectura"),
    ("https://www.disenodeinteriores.mx/", "Arquitectura"),
    ("https://www.estudiodearquitectura.mx/", "Arquitectura"),
    ("https://www.arquitecturamx.com/", "Arquitectura"),
    ("https://www.interiorismomx.com/", "Diseño de Interiores"),
    ("https://www.decoraciondeinteriores.mx/", "Diseño de Interiores"),
    ("https://www.disenadordeinteriores.mx/", "Diseño de Interiores"),
    ("https://www.remodelacionhogar.mx/", "Remodelación"),
    ("https://www.constructoramx.com/", "Construcción"),
    ("https://www.obrasnegras.mx/", "Construcción"),

    # --- Restaurantes Delivery / Dark Kitchen ---
    ("https://www.darkKitchenmx.com/", "Restaurante Delivery"),
    ("https://www.foodtruckmx.com/", "Restaurante Delivery"),
    ("https://www.comidaadistancia.mx/", "Restaurante Delivery"),
    ("https://www.sushideliverycdmx.com/", "Restaurante Delivery"),
    ("https://www.pizzadeliverymx.com/", "Restaurante Delivery"),
    ("https://www.hamburguesasdelivery.mx/", "Restaurante Delivery"),
    ("https://www.comidasaludabledelivery.mx/", "Restaurante Delivery"),
    ("https://www.tacodeliverycdmx.com/", "Restaurante Delivery"),
    ("https://www.burritosdelivery.mx/", "Restaurante Delivery"),
    ("https://www.ensaladasdelivery.mx/", "Restaurante Delivery"),

    # --- Salones de Belleza / Estética ---
    ("https://www.salondebellezmx.com/", "Salón de Belleza"),
    ("https://www.peluqueriacdmx.com/", "Salón de Belleza"),
    ("https://www.barberiacdmx.com/", "Barbería"),
    ("https://www.nailscdmx.com/", "Uñas"),
    ("https://www.maquillajecdmx.com/", "Maquillaje"),
    ("https://www.extensionesdecabello.mx/", "Salón de Belleza"),
    ("https://www.keratinabrasil.mx/", "Salón de Belleza"),
    ("https://www.lashescdmx.com/", "Extensiones Pestañas"),
    ("https://www.esteticacanina.mx/", "Estética Canina"),
    ("https://www.grooming.mx/", "Estética Canina"),

    # --- Talleres Mecánicos / Autoservicios ---
    ("https://www.tallermecanicocdmx.com/", "Taller Mecánico"),
    ("https://www.servicioauto.mx/", "Taller Mecánico"),
    ("https://www.mecanicaexpress.mx/", "Taller Mecánico"),
    ("https://www.hojalateriapintura.mx/", "Hojalatería"),
    ("https://www.alineacionybalanceo.mx/", "Taller Mecánico"),
    ("https://www.vultanizadoracdmx.com/", "Vulcanizadora"),
    ("https://www.lavadodeautos.mx/", "Lavado de Autos"),
    ("https://www.detailingcdmx.com/", "Detailing Autos"),
    ("https://www.diagnosticoautomotriz.mx/", "Taller Mecánico"),
    ("https://www.mecanicoadomicilio.mx/", "Taller Mecánico"),

    # --- Seguros ---
    ("https://www.agentedeseguros.mx/", "Seguros"),
    ("https://www.segurosmx.com/", "Seguros"),
    ("https://www.segurosdeauto.mx/", "Seguros"),
    ("https://www.segurosdevida.mx/", "Seguros"),
    ("https://www.segurossalud.mx/", "Seguros"),
    ("https://www.segurosempresariales.mx/", "Seguros"),
    ("https://www.brokerdeseguros.mx/", "Seguros"),
    ("https://www.microseguros.mx/", "Seguros"),

    # --- Clínicas Médicas Generales ---
    ("https://www.clinicamedica.mx/", "Clínica Médica"),
    ("https://www.medicogeneralcdmx.com/", "Clínica Médica"),
    ("https://www.clinicafamiliar.mx/", "Clínica Médica"),
    ("https://www.consultoriomedicocdmx.com/", "Clínica Médica"),
    ("https://www.clinicaintegral.mx/", "Clínica Médica"),
    ("https://www.centromedico.mx/", "Clínica Médica"),
    ("https://www.clinicadediabetes.mx/", "Clínica Médica"),
    ("https://www.clinicacardiologia.mx/", "Clínica Médica"),
    ("https://www.clinicaginecologia.mx/", "Ginecología"),
    ("https://www.clinicapediatrica.mx/", "Pediatría"),

    # --- Veterinaria (nuevos) ---
    ("https://centroveterinariomexico.mx/", "Veterinaria"),
    ("https://banfield.com.mx/", "Veterinaria"),
    ("https://cemegatos.com.mx/", "Veterinaria"),
    ("https://hospitalveterinariodelta.com.mx/", "Veterinaria"),
    ("https://www.centroveterinario.com.mx/", "Veterinaria"),
    ("https://www.clinicaveterinariacdmx.mx/", "Veterinaria"),
    ("https://www.vetcare.com.mx/", "Veterinaria"),
    ("https://www.hospitalveterinario.mx/", "Veterinaria"),

    # --- Reclutamiento / HR ---
    ("https://cornerstonegroup.mx/", "Reclutamiento"),
    ("https://headhuntersmexico.com.mx/", "Reclutamiento"),
    ("https://headhunting.mx/", "Reclutamiento"),
    ("https://www.hrmexico.com.mx/", "Reclutamiento"),
    ("https://www.reclutamientocdmx.com.mx/", "Reclutamiento"),
    ("https://www.humanasolutions.mx/", "Reclutamiento"),
    ("https://www.kapitalhrmexico.mx/", "Reclutamiento"),
    ("https://www.konceptahrm.com.mx/", "Reclutamiento"),

    # --- Medicina Estética ---
    ("https://www.mordi.com.mx/", "Medicina Estética"),
    ("https://www.clinicaestetica.mx/", "Medicina Estética"),
    ("https://www.dermika.mx/", "Medicina Estética"),
    ("https://www.esteticamedica.mx/", "Medicina Estética"),
    ("https://www.skincare.mx/", "Medicina Estética"),
    ("https://www.rejuvenecimientofacial.mx/", "Medicina Estética"),
    ("https://www.clinicapolanco.mx/", "Medicina Estética"),
    ("https://www.centrodermatologico.mx/", "Medicina Estética"),

    # --- Clínicas Fertilidad / Reproducción ---
    ("https://www.clinicafertilidad.mx/", "Fertilidad"),
    ("https://www.institutoreproduccion.mx/", "Fertilidad"),
    ("https://www.fertimed.mx/", "Fertilidad"),
    ("https://www.concebir.mx/", "Fertilidad"),
    ("https://www.reproductivamexico.mx/", "Fertilidad"),

    # --- Escuelas de Manejo ---
    ("https://www.autoescuela.mx/", "Escuela Manejo"),
    ("https://www.escuelademanejo.mx/", "Escuela Manejo"),
    ("https://www.cursodemanejo.mx/", "Escuela Manejo"),
    ("https://www.autoescuelacdmx.mx/", "Escuela Manejo"),

    # --- Artes Marciales / MMA ---
    ("https://www.academiakarate.mx/", "Artes Marciales"),
    ("https://www.mmamexico.mx/", "Artes Marciales"),
    ("https://www.taekwondomexico.mx/", "Artes Marciales"),
    ("https://www.judomexico.mx/", "Artes Marciales"),
    ("https://www.boxeocdmx.mx/", "Artes Marciales"),
    ("https://www.academiadefensa.mx/", "Artes Marciales"),

    # --- Capacitación Empresarial / Cursos ---
    ("https://www.capacitacionempresarial.mx/", "Capacitación"),
    ("https://www.cursosempresariales.mx/", "Capacitación"),
    ("https://www.institutocapacitacion.mx/", "Capacitación"),
    ("https://www.cursoscdmx.mx/", "Capacitación"),
    ("https://www.desarrolloempresarial.mx/", "Capacitación"),

    # --- Notarías / Legal ---
    ("https://www.notariacdmx.mx/", "Notaría"),
    ("https://www.notariapublica.mx/", "Notaría"),
    ("https://www.abogadosmexico.mx/", "Legal"),
    ("https://www.despacholegal.mx/", "Legal"),
    ("https://www.bufetejuridico.mx/", "Legal"),
    ("https://www.abogadoscdmx.mx/", "Legal"),

    # --- Psicología / Terapia ---
    ("https://www.psicologocdmx.mx/", "Psicología"),
    ("https://www.terapiapsicologica.mx/", "Psicología"),
    ("https://www.consultoriopsicologico.mx/", "Psicología"),
    ("https://www.psicologiaintegral.mx/", "Psicología"),
    ("https://www.centrodeterapia.mx/", "Psicología"),

    # --- Medicina Alternativa ---
    ("https://www.homeopatia.mx/", "Medicina Alternativa"),
    ("https://www.acupunturamexico.mx/", "Medicina Alternativa"),
    ("https://www.naturopatia.mx/", "Medicina Alternativa"),
    ("https://www.medicinaalternativa.mx/", "Medicina Alternativa"),
    ("https://www.clinicaholisticamexico.mx/", "Medicina Alternativa"),

    # --- Dental (Guadalajara / Monterrey) ---
    ("https://www.clinicadentalgdl.mx/", "Dental GDL"),
    ("https://www.dentistagonzalez.mx/", "Dental MTY"),
    ("https://www.clinicadentalpolanco.mx/", "Dental CDMX"),
    ("https://www.dentistadeconfianza.mx/", "Dental"),
    ("https://www.implantesdentales.mx/", "Dental"),
    ("https://www.ortodonciacdmx.mx/", "Dental"),

    # --- Fitness Guadalajara / Monterrey ---
    ("https://www.gymgdl.mx/", "Fitness GDL"),
    ("https://www.fitnessmty.mx/", "Fitness MTY"),
    ("https://www.crossfitgdl.mx/", "CrossFit GDL"),
    ("https://www.crossfitmty.mx/", "CrossFit MTY"),
    ("https://www.pilatesgdl.mx/", "Pilates GDL"),

    # --- Guarderías / Estancias Infantiles ---
    ("https://www.guarderiaprivada.mx/", "Guardería"),
    ("https://www.estanciainfantil.mx/", "Guardería"),
    ("https://www.kinder.mx/", "Guardería"),
    ("https://www.jardindeninos.mx/", "Guardería"),
    ("https://www.centroinfantil.mx/", "Guardería"),

    # --- Laboratorios Clínicos (nuevos) ---
    ("https://www.laboratoriomedico.mx/", "Laboratorio"),
    ("https://www.analisisclinicosgdl.mx/", "Laboratorio GDL"),
    ("https://www.laboratoriointegral.mx/", "Laboratorio"),
    ("https://www.laboratoriosnacional.mx/", "Laboratorio"),

    # --- Agencias de Marketing Digital ---
    ("https://www.agenciadigital.mx/", "Marketing Digital"),
    ("https://www.marketingdigitalmexico.mx/", "Marketing Digital"),
    ("https://www.publicidadcdmx.mx/", "Marketing Digital"),
    ("https://www.agenciaseo.mx/", "Marketing Digital"),
    ("https://www.agenciacreativa.mx/", "Marketing Digital"),
    ("https://www.socialmediamexico.mx/", "Marketing Digital"),

    # --- Spa Guadalajara / Monterrey ---
    ("https://www.spagdl.mx/", "Spa GDL"),
    ("https://www.spamty.mx/", "Spa MTY"),
    ("https://www.bienestarygdl.mx/", "Spa GDL"),
    ("https://www.masajesterapeuticos.mx/", "Spa"),
    ("https://www.centrobienestar.mx/", "Spa"),

    # --- Seguros (nuevos) ---
    ("https://www.agentesdeseguros.mx/", "Seguros"),
    ("https://www.segurosempresariales.mx/", "Seguros"),
    ("https://www.corredordeseguros.mx/", "Seguros"),

    # --- Escuelas Privadas Primaria/Secundaria ---
    ("https://www.colegioprivado.mx/", "Colegio"),
    ("https://www.colegiocdmx.mx/", "Colegio"),
    ("https://www.institutoeducativo.mx/", "Colegio"),
    ("https://www.primariaprivada.mx/", "Colegio"),

    # --- Tiendas de Productos Naturales / Salud ---
    ("https://www.tiendanatural.mx/", "Productos Naturales"),
    ("https://www.organicosmexico.mx/", "Productos Naturales"),
    ("https://www.productosorganicos.mx/", "Productos Naturales"),
    ("https://www.herbolaria.mx/", "Herbolaria"),
    ("https://www.suplementosdeportivos.mx/", "Suplementos"),

    # --- Diseño de Interiores / Decoración ---
    ("https://www.decoraciondeinteriores.mx/", "Diseño Interior"),
    ("https://www.interiorismomexico.mx/", "Diseño Interior"),
    ("https://www.mueblesadomicilio.mx/", "Muebles"),
    ("https://www.estudiotapatiointeriorismo.mx/", "Diseño Interior"),

    # --- Logística / Paquetería PYME ---
    ("https://www.mensajeriamexico.mx/", "Logística"),
    ("https://www.paqueteriaexpress.mx/", "Logística"),
    ("https://www.enviosexpress.mx/", "Logística"),
    ("https://www.transportedemercancias.mx/", "Logística"),
]

# Extra URLs to try (contact pages)
CONTACT_PATHS = ["/contacto", "/contact", "/contacto/", "/contact/", "/nosotros", "/about"]

def get_emails_from_url(url, already_sent, timeout=8):
    """Fetch URL and extract new emails. Returns (emails, html_text) tuple."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        if r.status_code != 200:
            return [], ""
        text = r.text
        emails = EMAIL_REGEX.findall(text)
        valid = []
        for e in emails:
            e = e.lower().strip('.')
            domain = e.split('@')[1]
            # Solo emails con dominio .mx (negocios mexicanos)
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
        return valid, text
    except Exception:
        return [], ""

def scrape_site(base_url, vertical, already_sent):
    """Try main page and contact page. Returns list of (email, vertical, source, business_name)."""
    emails, html = get_emails_from_url(base_url, already_sent)
    page_html = html  # HTML de la página principal (para extraer nombre)

    if not emails:
        for path in CONTACT_PATHS:
            url = urljoin(base_url, path)
            emails, subpage_html = get_emails_from_url(url, already_sent)
            if emails:
                # Preferir HTML de la página principal para extraer nombre
                if not page_html:
                    page_html = subpage_html
                break
        time.sleep(0.5)

    # Extraer nombre del negocio del HTML de la página principal
    business_name = extract_business_name(page_html, base_url) if page_html else ""

    return [(e, vertical, base_url, business_name) for e in emails]

def main():
    today = datetime.now().strftime('%Y-%m-%d')
    output_file = f"/home/ubuntu/clawd/prospectos/leads-auto-{today}.json"

    # Cargar historial de ya-enviados
    already_sent = load_already_sent()

    # Cargar dominios descubiertos dinámicamente (domain-discovery.py)
    dynamic_targets = []
    discovered_file = "/home/ubuntu/clawd/prospectos/discovered-domains.json"
    if os.path.exists(discovered_file):
        try:
            with open(discovered_file) as f:
                disc = json.load(f)
            existing_urls = {u for u, _ in SEARCH_TARGETS}
            for item in disc.get("discovered", []):
                if item["url"] not in existing_urls:
                    dynamic_targets.append((item["url"], item.get("vertical", "Dinámico")))
        except Exception:
            pass

    all_targets = SEARCH_TARGETS + dynamic_targets

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Ya enviados: {len(already_sent)} emails (skip automático)")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Sitios estáticos: {len(SEARCH_TARGETS)} | Dinámicos: {len(dynamic_targets)} | Total: {len(all_targets)}\n")

    all_leads = []
    seen_today = set()

    # Cargar leads ya encontrados hoy (por si script fue interrumpido antes)
    if os.path.exists(output_file):
        try:
            with open(output_file) as f:
                existing = json.load(f)
            for lead in existing:
                seen_today.add(lead['email'])
                all_leads.append(lead)
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Resumiendo: {len(all_leads)} leads ya encontrados hoy")
        except Exception:
            pass

    def save_leads():
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, 'w') as f:
            json.dump(all_leads, f, indent=2, ensure_ascii=False)

    for i, (url, vertical) in enumerate(all_targets):
        domain = urlparse(url).netloc
        print(f"[{i+1}/{len(all_targets)}] {domain}...", end=" ", flush=True)

        results = scrape_site(url, vertical, already_sent | seen_today)

        if results:
            for e, v, u, bname in results:
                seen_today.add(e)
                lead = {"email": e, "vertical": v, "source": u}
                if bname:
                    lead["business_name"] = bname
                all_leads.append(lead)
                name_tag = f" [{bname}]" if bname else ""
                print(f"✅ {e}{name_tag}", end=" ")
            print()
            # Guardar incrementalmente cada vez que se encuentran leads
            save_leads()
        else:
            print("—")

        time.sleep(0.8)  # Polite delay

    # Save final
    save_leads()

    print(f"\n✅ {len(all_leads)} leads NUEVOS encontrados → {output_file}")
    print(f"   (skip: {len(already_sent)} ya enviados anteriormente)\n")

    return all_leads

if __name__ == "__main__":
    leads = main()

    # Resumen por vertical
    by_vertical = {}
    for l in leads:
        by_vertical.setdefault(l['vertical'], []).append(l['email'])

    print("Resumen por vertical:")
    for v, emails in sorted(by_vertical.items()):
        print(f"  {v}: {', '.join(emails)}")
