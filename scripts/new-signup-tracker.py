#!/usr/bin/env python3
"""
new-signup-tracker.py — EZContact New Signup Tracker
Scans the EZContact inbox for 'Bienvenido a EZContact' emails,
extracts user data, classifies signups, and creates a daily digest.

Usage:
    python3 new-signup-tracker.py [--days 2] [--output /path/to/output.json]
"""

import subprocess
import json
import re
import sys
import os
import argparse
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

CDMX = ZoneInfo("America/Mexico_City")
UTC = timezone.utc

INTERNAL_DOMAINS = [
    "tecnologiaslozano.com",
    "ezcontact.mx",
    "saludtotal.mx",
    "lozano.tech",
]

COUNTRY_FLAGS = {
    "MX": "🇲🇽",
    "CO": "🇨🇴",
    "AR": "🇦🇷",
    "GT": "🇬🇹",
    "US": "🇺🇸",
    "ES": "🇪🇸",
    "PE": "🇵🇪",
    "CL": "🇨🇱",
    "EC": "🇪🇨",
    "VE": "🇻🇪",
    "BO": "🇧🇴",
    "PY": "🇵🇾",
    "UY": "🇺🇾",
    "CR": "🇨🇷",
    "PA": "🇵🇦",
    "HN": "🇭🇳",
    "SV": "🇸🇻",
    "NI": "🇳🇮",
    "DO": "🇩🇴",
    "CU": "🇨🇺",
}

def get_envelopes(account: str, limit: int = 50) -> list:
    """Get envelope list from himalaya."""
    try:
        result = subprocess.run(
            ["himalaya", "envelope", "list", "-a", account, "--output", "json"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            return []
        data = json.loads(result.stdout)
        return data if isinstance(data, list) else []
    except Exception as e:
        print(f"⚠️  Error listing envelopes: {e}")
        return []

def read_message(account: str, msg_id: int) -> str:
    """Read a message from himalaya."""
    try:
        result = subprocess.run(
            ["himalaya", "message", "read", "-a", account, str(msg_id)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.stdout
    except Exception as e:
        return ""

def parse_signup_email(body: str) -> dict:
    """Extract user info from a 'Bienvenido a EZContact' email body."""
    info = {}

    # Nombre del usuario
    name_match = re.search(r"¡Hola ([^!]+)!", body)
    if name_match:
        info["nombre"] = name_match.group(1).strip()

    # Email
    email_match = re.search(r"Email del usuario:\s*([^\s<\n]+)", body)
    if email_match:
        raw_email = email_match.group(1).strip()
        # Some emails come as plain text after "Email del usuario:"
        if "@" in raw_email and len(raw_email) > 4:
            info["email"] = raw_email

    # Empresa
    empresa_match = re.search(r"Empresa:\s*([^\n]+?)(?:\s+IP:|$)", body, re.MULTILINE)
    if empresa_match:
        empresa = empresa_match.group(1).strip()
        # Skip if empresa looks like an email or number
        if "@" not in empresa and not empresa.isdigit() and len(empresa) > 1:
            info["empresa"] = empresa

    # País
    country_match = re.search(r"Country:\s*([A-Z]{2})", body)
    if country_match:
        info["country"] = country_match.group(1).strip()

    # Móvil
    mobile_match = re.search(r"Mobile:\s*\+?(\d{10,15})", body)
    if mobile_match:
        info["mobile"] = "+" + mobile_match.group(1).strip()

    # IP
    ip_match = re.search(r"IP:\s*([\d.]+)", body)
    if ip_match:
        info["ip"] = ip_match.group(1).strip()

    return info

def classify_signup(info: dict) -> str:
    """Classify signup as interno, mx_externo, or latam_externo."""
    email = info.get("email", "")
    domain = email.split("@")[-1] if "@" in email else ""

    if domain in INTERNAL_DOMAINS:
        return "interno"
    if info.get("country") == "MX":
        return "mx_externo"
    return "latam_externo"

def get_priority(signup: dict) -> str:
    """Assign priority based on signup classification and empresa info."""
    classification = signup.get("classification", "")
    empresa = signup.get("empresa", "")
    country = signup.get("country", "")

    if classification == "interno":
        return "⚪ interno"
    if classification == "mx_externo":
        if empresa and "@" not in empresa:
            return "🔴 MX con empresa"
        return "🟡 MX personal"
    # LATAM
    if empresa and "@" not in empresa:
        return "🟠 LATAM con empresa"
    return "🟢 LATAM personal"

def main():
    parser = argparse.ArgumentParser(description="EZContact New Signup Tracker")
    parser.add_argument("--days", type=int, default=2, help="Days to look back (default: 2)")
    parser.add_argument("--output", type=str, default=None, help="Output JSON file path")
    parser.add_argument("--quiet", action="store_true", help="Minimal output")
    args = parser.parse_args()

    now = datetime.now(CDMX)
    lookback = now - timedelta(days=args.days)
    output_path = args.output or f"/home/ubuntu/clawd/memory/signups-{now.strftime('%Y-%m-%d')}.json"

    print(f"\n🔍 EZContact New Signup Tracker")
    print(f"   Scanning last {args.days} days (since {lookback.strftime('%Y-%m-%d %H:%M %Z')})")
    print(f"   Time: {now.strftime('%Y-%m-%d %H:%M %Z')}\n")

    # Get envelopes
    envelopes = get_envelopes("ezcontact")
    if not envelopes:
        print("⚠️  Could not retrieve envelopes from ezcontact inbox.")
        sys.exit(1)

    # Filter "Bienvenido a EZContact" emails
    signup_envelopes = [
        e for e in envelopes
        if "bienvenido" in e.get("subject", "").lower() and "ezcontact" in e.get("subject", "").lower()
    ]

    print(f"📬 Found {len(signup_envelopes)} signup notification email(s) in inbox")

    signups = []
    for env in signup_envelopes:
        msg_id = env.get("id")
        date_str = env.get("date", "")

        # Parse date for filtering
        try:
            # Date format varies: "2026-03-08 12:22-06:00"
            date_clean = date_str.replace(" ", "T") if " " in date_str else date_str
            # Handle timezone offset
            if re.search(r"[+-]\d{2}:\d{2}$", date_clean):
                signup_date = datetime.fromisoformat(date_clean)
            else:
                signup_date = datetime.fromisoformat(date_clean + "+00:00")
            signup_date_cdmx = signup_date.astimezone(CDMX)
        except Exception:
            signup_date_cdmx = now  # fallback

        if signup_date_cdmx < lookback:
            continue

        # Read message body
        body = read_message("ezcontact", msg_id)
        if not body:
            continue

        info = parse_signup_email(body)
        if not info.get("email") and not info.get("nombre"):
            continue

        signup = {
            "id": msg_id,
            "fecha": signup_date_cdmx.strftime("%Y-%m-%d %H:%M %Z"),
            "nombre": info.get("nombre", "?"),
            "email": info.get("email", "?"),
            "empresa": info.get("empresa", ""),
            "country": info.get("country", "?"),
            "mobile": info.get("mobile", ""),
            "ip": info.get("ip", ""),
        }
        signup["classification"] = classify_signup(signup)
        signup["priority"] = get_priority(signup)
        signups.append(signup)

    # Sort by priority
    priority_order = {"🔴": 0, "🟠": 1, "🟡": 2, "🟢": 3, "⚪": 4}
    signups.sort(key=lambda s: priority_order.get(s.get("priority", "")[:2], 5))

    # Summary
    total = len(signups)
    mx = [s for s in signups if s["classification"] == "mx_externo"]
    latam = [s for s in signups if s["classification"] == "latam_externo"]
    internos = [s for s in signups if s["classification"] == "interno"]

    print(f"\n📊 SIGNUPS — Últimos {args.days} días")
    print(f"   Total: {total}  |  MX: {len(mx)}  |  LATAM: {len(latam)}  |  Internos: {len(internos)}\n")

    if not signups:
        print("   (sin signups en el período)\n")
    else:
        for s in signups:
            flag = COUNTRY_FLAGS.get(s.get("country", ""), "🌐")
            empresa_str = f" — {s['empresa']}" if s.get("empresa") else ""
            mobile_str = f" | 📱 {s['mobile']}" if s.get("mobile") else ""
            print(f"   {s['priority']} {flag} {s['nombre']}{empresa_str}")
            print(f"      {s['email']}{mobile_str}")
            print(f"      {s['fecha']}\n")

    # Save to JSON
    output = {
        "generated_at": now.isoformat(),
        "days_scanned": args.days,
        "summary": {
            "total": total,
            "mx_externo": len(mx),
            "latam_externo": len(latam),
            "interno": len(internos),
        },
        "signups": signups,
    }

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"✅ Report saved to: {output_path}")

    # Action items
    action_items = [s for s in signups if s["classification"] != "interno"]
    if action_items:
        print(f"\n🎯 ACTION ITEMS ({len(action_items)} leads externos para seguimiento):")
        for s in action_items[:5]:
            flag = COUNTRY_FLAGS.get(s.get("country", ""), "🌐")
            empresa_str = f" ({s['empresa']})" if s.get("empresa") else ""
            print(f"   • {flag} {s['nombre']}{empresa_str} — {s['email']}")
        if len(action_items) > 5:
            print(f"   ... y {len(action_items) - 5} más (ver JSON)")
    print()

if __name__ == "__main__":
    main()
