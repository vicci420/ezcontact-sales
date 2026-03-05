#!/usr/bin/env python3
"""
Club Junior Tennis Reservation Automation
Reserves a court at 7:00 AM for the next day (Mon-Fri)

Flow:
  5:59 AM CDMX → Pre-login (session ready)
  6:00:00 AM   → Fire reservation immediately (no login delay)

Run at 5:59 AM CDMX to be ready when reservations open at 6:00 AM

FIXED 2026-02-18: Correct API flow discovered:
- TipoApartado=2 for doubles (not 4)
- Field is Username2 (not Usuario2)
- Submit button is Grabar=Seleccionar

IMPROVED 2026-02-19: Added verification step
- After reservation, verifies it exists in TusApartadosCelular.php
- Never reports success without verification
"""

import requests
import re
import sys
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# Configuration
BASE_URL = "http://reservacionesjuniorclub.com/JuniorServicios"
LOGIN_URL = f"{BASE_URL}/Usuarios/Login.php"
APARTAR_URL = f"{BASE_URL}/Miembros/TenisCelular/Apartar.php"

USER = "10194"
PASSWORD = "junior"

# Weekly partners (membership numbers and internal IDs)
PARTNERS = {
    0: ("Mauricio Baeza Licón", "7606", None),      # Monday
    1: ("Carlos Alberto Sánchez", "7621", None),     # Tuesday
    2: ("Alejandro Navarro Bernardo", "6525", None), # Wednesday
    3: ("Rafael Quezada Garcia", "7597", "10332"),   # Thursday - ID confirmed
    4: ("Ivan Velazquez Fiesco", "6970", None),      # Friday
}

# Court priority order
COURT_PRIORITY = [3, 2, 8, 6, 10, 4, 5, 7, 9, 1]

# Verification URL
APARTADOS_URL = f"{BASE_URL}/Miembros/TusApartadosCelular.php"

def wait_until_6am():
    """Wait until exactly 6:00:00 AM CDMX before attempting reservation"""
    cdmx = ZoneInfo('America/Mexico_City')
    now = datetime.now(cdmx)
    target = now.replace(hour=6, minute=0, second=0, microsecond=0)
    
    # If it's already past 6am, no need to wait
    if now >= target:
        print(f"✓ Already past 6:00 AM CDMX ({now.strftime('%H:%M:%S')})")
        return
    
    wait_seconds = (target - now).total_seconds()
    if wait_seconds > 0 and wait_seconds < 120:  # Only wait if less than 2 minutes
        print(f"⏳ Waiting {wait_seconds:.1f} seconds until 6:00:00 AM CDMX...")
        time.sleep(wait_seconds)
        print(f"✓ It's now 6:00 AM CDMX - GO!")

def get_tomorrow():
    """Get tomorrow's date in CDMX timezone"""
    cdmx = ZoneInfo('America/Mexico_City')
    now = datetime.now(cdmx)
    return now + timedelta(days=1)

def login(session):
    """Login to the system"""
    session.post(LOGIN_URL, data={"Usuario": USER, "Password": PASSWORD})
    return 'PHPSESSID' in session.cookies.get_dict()

def _court_base_data(cancha, fecha, dia_semana):
    """Base POST data for court reservation — CORRECT parameters verified 2026-02-22."""
    return {
        'DiaSemana': str(dia_semana),  # 1=Monday ... 5=Friday (weekday+1)
        'Cancha':    str(cancha),
        'Fecha':     fecha,            # YYYY-MM-DD format
        'Hora':      '700',            # FIXED 2026-02-27: '7' causes "Unexpected response" outside 6am window; '700' works correctly
        'Duracion':  '75',
        'Horario':   '0700',           # NOT '07:00 - 08:15' — use '0700'
        'Clases':    '0',
    }

def reserve_court(session, cancha, fecha, partner_membership, dia_semana):
    """Complete full reservation flow for a court.
    
    Correct POST sequence discovered 2026-02-22:
      1. Select court → expect TipoApartado selection page
      2. Select type (TipoApartado=2 for doubles)
      3. Search partner by membership → get internal Username2 id
      4. Complete with Username2 + Grabar=Seleccionar
    """
    base = _court_base_data(cancha, fecha, dia_semana)

    # Step 1: Select court
    r1 = session.post(APARTAR_URL, data=base, timeout=15)
    if 'TipoApartado' not in r1.text:
        return r1.text, None   # court blocked or bad response

    # Step 2: Select Dobles (TipoApartado=2)
    session.post(APARTAR_URL, data={**base, 'TipoApartado': '2'}, timeout=15)

    # Step 3: Search for partner
    r3 = session.post(APARTAR_URL, data={
        **base, 'TipoApartado': '2',
        'Buscar': partner_membership, 'BuscarM': 'Buscar'
    }, timeout=15)

    match = re.search(r'name="Username2" value="(\d+)"', r3.text)
    if not match:
        return r3.text, None

    partner_id = match.group(1)

    # Step 4: Complete reservation
    r4 = session.post(APARTAR_URL, data={
        **base, 'TipoApartado': '2',
        'Username2': partner_id, 'Grabar': 'Seleccionar'
    }, timeout=15)

    return r4.text, partner_id

def verify_reservation(session, folio, fecha=None):
    """
    CRITICAL: Verify reservation exists in 'Tus Apartados'
    This prevents false success reports (learned hard way 2026-02-18)
    
    Fixed 2026-02-23: Added date fallback in case folio regex captured wrong number.
    Searches by folio first, then by fecha (YYYY-MM-DD) as fallback.
    """
    try:
        resp = session.get(APARTADOS_URL)
        html = resp.text
        
        # Primary: search by folio
        if folio and folio in html:
            print(f"✓ VERIFIED: Folio {folio} found in Tus Apartados")
            return True
        
        # Fallback: search by date (YYYY-MM-DD format)
        if fecha and fecha in html:
            print(f"✓ VERIFIED (by date): {fecha} found in Tus Apartados (folio match failed)")
            return True
        
        print(f"⚠ WARNING: Folio {folio} / fecha {fecha} NOT found in Tus Apartados")
        print(f"  → Check manually at TusApartadosCelular.php")
        return False
    except Exception as e:
        print(f"⚠ Verification error: {e}")
        return False

def main():
    tomorrow = get_tomorrow()
    weekday = tomorrow.weekday()

    # Only reserve for weekdays — check BEFORE doing anything
    if weekday > 4:
        print(f"Tomorrow is weekend - no reservation needed")
        return {"status": "skip", "reason": "weekend"}

    partner_name, partner_membership, _ = PARTNERS[weekday]
    fecha = tomorrow.strftime('%Y-%m-%d')  # YYYY-MM-DD — format verified 2026-02-22
    dia_semana = weekday + 1              # System uses 1=Mon ... 5=Fri
    dia = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes'][weekday]

    print(f"=== Club Junior Tennis Reservation ===")
    print(f"Date: {fecha} ({dia})")
    print(f"Time: 07:00")
    print(f"Partner: {partner_name} ({partner_membership})")
    print(f"Court priority: {COURT_PRIORITY}")
    print()

    # PRE-LOGIN at 5:59 AM — session ready before reservations open
    session = requests.Session()
    if not login(session):
        print("ERROR: Login failed at 5:59 AM")
        return {"status": "error", "reason": "login_failed"}
    print("✓ Pre-login successful at 5:59 AM — session ready")

    # Wait until exactly 6:00:00 AM CDMX (when reservations open)
    wait_until_6am()

    # Try courts in priority order
    for cancha in COURT_PRIORITY:
        print(f"Trying court {cancha}...")
        
        result, partner_id = reserve_court(session, cancha, fecha, partner_membership, dia_semana)
        
        # Check results
        if "Se completo el apartado" in result:
            # Match folio: look for 5+ digit number after 'Folio' keyword
            # Using \d{5,} to avoid capturing short codes like dates or times
            folio_match = re.search(r'Folio[:\s#]*(\d{5,})', result, re.IGNORECASE)
            folio = folio_match.group(1) if folio_match else None
            print(f"✓ CLAIMED SUCCESS: Reserved court {cancha}, Folio: {folio}")
            
            # CRITICAL: Verify the reservation actually exists
            if verify_reservation(session, folio, fecha=fecha):
                return {
                    "status": "success",
                    "court": cancha,
                    "date": fecha,
                    "time": "07:00",
                    "partner": partner_name,
                    "folio": folio,
                    "verified": True
                }
            else:
                print(f"⚠ VERIFICATION FAILED: Folio {folio} / fecha {fecha} not confirmed!")
                return {
                    "status": "unverified",
                    "court": cancha,
                    "date": fecha,
                    "time": "07:00",
                    "partner": partner_name,
                    "folio": folio,
                    "verified": False,
                    "warning": "Claimed success but verification failed - CHECK MANUALLY"
                }
        elif "apartado en horario continuo" in result.lower():
            # ⚠️ IGNORAR este mensaje — NO significa reservación exitosa
            # Continuar con siguiente cancha
            print(f"  Court {cancha}: 'horario continuo' msg — ignoring, trying next...")
        elif "ocupad" in result.lower() or "no disponible" in result.lower():
            print(f"  Court {cancha} not available")
        else:
            print(f"  Unexpected response, trying next...")
        
        # Fresh session for next attempt
        session = requests.Session()
        login(session)
    
    print("ERROR: Could not reserve any court")
    return {"status": "error", "reason": "no_courts_available"}

def write_log(result):
    """Escribe resultado al log de tennis para seguimiento histórico."""
    import os
    from datetime import datetime, timezone
    LOG_FILE = "/home/ubuntu/clawd/memory/tennis-log.txt"
    now_utc = datetime.now(timezone.utc).strftime("%a %b %d %H:%M:%S UTC %Y")
    status = result.get("status", "unknown")
    if status == "success":
        court = result.get("court", "?")
        folio = result.get("folio", "?")
        date = result.get("date", "?")
        msg = f"Cron tennis OK — {date} 07:00 Cancha {court} Folio {folio}"
    elif status == "unverified":
        court = result.get("court", "?")
        folio = result.get("folio", "?")
        date = result.get("date", "?")
        msg = f"Cron tennis UNVERIFIED — {date} Cancha {court} Folio {folio} — CHECK MANUALLY"
    elif status == "skip":
        reason = result.get("reason", "skip")
        msg = f"Cron tennis SKIP — {reason}"
    else:
        reason = result.get("reason", "unknown error")
        msg = f"Cron tennis FAIL — {reason}"
    try:
        with open(LOG_FILE, "a") as f:
            f.write(f"{now_utc}: {msg}\n")
        print(f"[LOG] {msg}")
    except Exception as e:
        print(f"[LOG ERROR] Could not write to log: {e}")


if __name__ == "__main__":
    result = main()
    print(f"\nResult: {result}")
    write_log(result)

    # Exit codes:
    # 0 = success (verified) or skip (weekend/already reserved)
    # 1 = error (no courts, login failed)
    # 2 = unverified (claimed success but verification failed)
    if result.get("status") == "success" and result.get("verified"):
        sys.exit(0)
    elif result.get("status") == "skip":
        sys.exit(0)
    elif result.get("status") == "unverified":
        sys.exit(2)  # Special code for manual verification needed
    else:
        sys.exit(1)
