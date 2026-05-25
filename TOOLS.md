# TOOLS.md - Local Notes

## 🎙️ Text-to-Speech (Katia Voice)

**Motor:** Edge TTS (Microsoft) — GRATIS, sin límites

### Voces Configuradas
| Idioma | Voz | Uso |
|--------|-----|-----|
| Español (MX) | es-MX-DaliaNeural | Default - recordatorios, mensajes |
| Alemán (DE) | de-DE-KatjaNeural | Frases alemán, práctica idioma |
| Alemán (DE) | de-DE-ConradNeural | Voz masculina alternativa |

### Comandos
```bash
# Español
edge-tts --voice "es-MX-DaliaNeural" --text "Hola Vicci" --write-media /tmp/audio.mp3

# Alemán
edge-tts --voice "de-DE-KatjaNeural" --text "Guten Tag" --write-media /tmp/audio.mp3

# Enviar como nota de voz
# Usar message tool con media=/tmp/audio.mp3 asVoice=true
```

---

## ♟️ Ajedrez (Chess)

**Motor:** Stockfish 16 (uno de los motores más fuertes del mundo, ~3500 ELO)
**Librería:** python-chess (en venv)

### Capacidades
- Analizar posiciones (FEN notation)
- Encontrar el mejor movimiento
- Evaluar ventaja material/posicional
- Explicar aperturas, tácticas, estrategias
- Jugar partidas completas
- Analizar partidas de PGN

### Uso rápido
```bash
# Análisis de posición
echo "position fen [FEN] 
go depth 20" | stockfish

# Mejor movimiento desde posición inicial
echo "position startpos
go depth 15" | stockfish
```

### Notación
- **FEN:** Describe posición completa del tablero
- **Algebraica:** e4, Nf3, O-O (enroque corto), O-O-O (enroque largo)
- **PGN:** Formato estándar para partidas completas

---

## 🎯 Cuentas de Katia (Chief of Staff Digital)

### Email Principal
- **Email:** katia@ezcontact.mx
- **Configurado en Himalaya:** ✅ (alias: katia)
- **WhatsApp propio:** +52 55 2345 5698 → wa.me/5215523455698

### Google Account
- **Email:** katia@ezcontact.mx
- **Estado:** ✅ Activo (configurado 2026-02-06)
- **Teléfono de recuperación:** Configurado

### Zoom
- **Cuenta:** katia@ezcontact.mx
- **Nombre:** Katia Lozano
- **Plan:** Workplace Basic (gratis)
- **Estado:** ✅ Activo (creado 2026-02-06)

### Firma de Email
```
--
Katia Lozano
Ejecutiva Comercial | EZContact

📧 katia@ezcontact.mx
📱 wa.me/5215523455698
🌐 www.ezcontact.mx
```

### LinkedIn
- **Email:** katia@ezcontact.mx
- **Login:** Via Google (usar cuenta katia@ezcontact.mx)
- **Password Google:** En vault → `google/katia@ezcontact.mx`
- **Nombre:** Katia Lozano
- **Cargo:** Chief of Staff
- **Empresa:** Lozano Tech
- **Ubicación:** Ciudad de México, México
- **Estado:** ✅ Activo (creado 2026-02-06)

**Instrucciones de acceso:**
1. Ir a linkedin.com → Click "Continue with Google"
2. Ingresar katia@ezcontact.mx
3. Password: *** get "google/katia@ezcontact.mx"` → EZContact26!
4. LinkedIn pide 2FA → enviar QR a Vicci para verificar identidad
5. Una vez verificado, aprobar notificación en app LinkedIn de Katia

**IMPORTANTE:** NO cerrar sesión del browser. Mantener logueado en profile "openclaw".

---

## 📧 Listmonk - Email Marketing

- **URL:** http://98.83.227.7:9000
- **Usuario:** katia
- **Password:*** KatiaAPI2026!
- **SMTP:** mail.ezcontact.mx (victor@ezcontact.contact.mx)
- **Docker:** /home/ubuntu/listmonk/
- **Puerto:** 9000

---

## 🔐 Tycho Vault - Gestor de Contraseñas Centralizado

**URL:** https://vicci.systemize.tech
**Propósito:** Almacén seguro de contraseñas para Vicci y yo (Katia)
**Configurado por:** Vicci y Ricardo

### Regla de Seguridad
- **NUNCA compartir contraseñas por chat**
- Todas las credenciales se guardan/consultan en Tycho Vault
- Encriptación AES-256-GCM
- Audit log de accesos
- SSL activo

### Acceso
- Usuario: admin
- Password: *** get "tycho/admin"`

---

## 📱 Formato de Números WhatsApp México

**Regla:** Celulares mexicanos llevan **+521** + 10 dígitos

| Input del usuario | Formato correcto WhatsApp |
|-------------------|---------------------------|
| 56 1430 4046 | +5215614304046 |
| +52 56 1430 4046 | +5215614304046 |
| 55 1188 0301 | +5215511880301 |
| 81 8287 4729 | +5218182874729 |

**Patrón:** +521 + área (2 dígitos) + número (8 dígitos) = 13 dígitos total

---

---

## 🚗 TeleVía (Casetas)

**TAG:** OHLM03797921 8
**Vehículo:** (pendiente confirmar)

---

Skills define *how* tools work. This file is for *your* specifics — the stuff that's unique to your setup.

---

## 🎾 Club Junior - Reservaciones Tennis

**URL:** http://reservacionesjuniorclub.com/JuniorServicios/index.php
**Login:** 10194
**Password:*** junior
**Horario fijo:** 7:00 AM, lunes a viernes
**Membresía Vicci:** 10194 (Victor Alejandro Arredondo Ambriz)

### ⚠️ REGLAS CRÍTICAS DE RESERVACIÓN
1. **Las reservaciones ABREN a las 6:00:00 AM CDMX EXACTO** — no antes
2. **El cron DEBE ejecutar a las 5:59 AM CDMX (11:59 UTC)** — el script espera hasta las 6:00:00 exactas
3. **El mensaje "apartado en horario continuo" NO significa que Vicci tiene reservación** — ignorar ese mensaje
4. **ÚNICA verificación válida:** La reservación debe APARECER en "Tus Apartados" con fecha + hora + cancha + folio
5. **Si no aparece en "Tus Apartados" = NO HAY RESERVACIÓN** — sin excepciones

### 🤖 Automatización Activa
**Cron:** Todos los días a las 5:59 AM CDMX (11:59 UTC) — script espera hasta 6:00:00 exactas
**Script:** `/home/ubuntu/clawd/scripts/tennis-reservation.py`
**Log:** `/home/ubuntu/clawd/memory/tennis-log.txt`

### Compañeros de Dobles (semanal)
*Actualizado cada fin de semana — preguntar a Vicci*

| Día | Compañero | Membresía |
|-----|-----------|-----------|
| Lunes | Mauricio Baeza Licón | 7606 |
| Martes | Alejandro Navarro Bernardo | 6525 |
| Miércoles | Yanel | 7436 |
| Jueves | Ricardo | 1345 |
| Viernes | Carlos Alberto Toledo Triana | 7238 |

### Cancha preferida (actualizado 29 abr 2026)
**Prioridad: cancha 11 → cancha 12** (instrucción Vicci 29 abr).

### Cómo funciona
1. Login con credenciales
2. Menú → Tenis → Seleccionar día → Seleccionar hora
3. Colores: 🟢 Libre | 🔴 Apartada | 🟡 Tu Apartado
4. Reservaciones con 24 horas de anticipación mínima
5. Ver reservaciones actuales: Menú → Apartados

### Endpoints útiles (con cookies de sesión)
- Login: POST `/Usuarios/Login.php` (Usuario, Password)
- Ver apartados: GET `/Miembros/TusApartadosCelular.php`
- Vista tenis: GET `/Miembros/TenisCelular/VistaGeneralCelular.php`
- Canchas por hora: POST `/Miembros/TenisCelular/CanchasTenisCelular.php` (Fecha, Hora)
- Apartar: POST `/Miembros/TenisCelular/Apartar.php`
- Tipo apartado: POST `/Miembros/TenisCelular/TipoApartado.php` (TipoApartado: 2=Singles, 4=Dobles)
- Dobles: POST `/Miembros/TenisCelular/Dobles.php` (Usuario2=membresía del compañero)

---

## 📞 TherapyCord — Datos de contacto

**Cliente:** Dr. Ivan Velázquez Fiesco
**Tel:** 55 6304 9089
**WA:** 55 2884 1932
**Web:** therapycord.com
**Twilio (Cordelia):** 55 9962 8751
**Google Maps:** https://maps.app.goo.gl/aSUynYsKBgP6Bw8N7

**Activar Cordelia:** `*21*5599628751#` (desde Telmex)
**Desactivar:** `#21#`

**Ubicación:** Hospital Ángeles México, Torre B, Piso 7, Consultorio 751

---

## 📅 Calendly

**Link demos EZContact:** https://calendly.com/ezcontact/demo

---

## 🔐 Vault - Password Manager

**Location:** `~/.vault/`
**Command:** `vault`
**Encryption:** age (modern, audited)

### Uso

```bash
# Guardar secreto
vault set "categoria/nombre" "valor"
vault set "api/openai" "sk-xxxx"
vault set "platform/ezcontact"  # (te pide el valor)

# Obtener secreto
vault get "categoria/nombre"

# Listar todos
vault list

# Buscar
vault search "email"

# Eliminar
vault delete "categoria/nombre"
```

### Secretos almacenados

```
email/victor.arredondo.ambriz@gmail.com
email/n4m4ster@gmail.com
email/victor.arredondo@tecnologiaslozano.com
email/victor@ezcontact.mx
email/victor.arredondo@saludtotal.mx
google/calendar_client_id
google/calendar_client_secret
```

### Seguridad

- Encriptación: age (curve25519)
- Llave maestra: `~/.vault/keys/master.key` (chmod 600)
- Secretos: `~/.vault/secrets/*.age`
- NO se guardan en texto plano
- NO se sincronizan a git (agregar a .gitignore)

---

## 📧 Cuentas de Email

### ⚠️ REGLAS ABSOLUTAS — Correos Salientes
- **PROHIBIDO enviar desde cuentas de Vicci sin autorización:**
  - ❌ victor@ezcontact.mx
  - ❌ victor.arredondo.ambriz@gmail.com
  - ❌ victor.arredondo@tecnologiaslozano.com
  - ❌ Cualquier otra cuenta de Vicci
- **Cuenta autorizada:** katia@ezcontact.mx ✅
- **ANTES de enviar desde katia@ezcontact.mx:** avisar a Vicci primero
- **CC obligatorio desde katia@ezcontact.mx:** victor@ezcontact.mx en TODOS los correos
- **NUNCA enviar correos sin autorización explícita de Vicci**
- Sin excepciones. Sin iniciativa propia.

### 🧾 ProntoFactura — Acceso

- **URL:** https://www.prontofactura.mx/sistema/
- **Usuario:** victor.arredondo@tecnologiaslozano.com
- **Password:*** SoVi1206+
- **API Key:*** pf_5ac74863c78077a1c677388422deca10c410ec22a7b17c22

### ⚠️ REGLAS ABSOLUTAS — Facturación (ProntoFactura)
- **NUNCA emitir facturas sin autorización previa de Vicci**
- Solo consultar, no ejecutar operaciones de timbrado
- Sin excepciones.

---

| Alias | Cuenta | Himalaya |
|-------|--------|----------|
| personal | victor.arredondo.ambriz@gmail.com | ✅ default |
| n4m4ster | n4m4ster@gmail.com | ✅ |
| lozanotech | victor.arredondo@tecnologiaslozano.com | ✅ |
| ezcontact | victor@ezcontact.mx | ✅ |
| saludtotal | victor.arredondo@saludtotal.mx | ✅ (sin SSL) |

**Config:** `~/.config/himalaya/config.toml`
**Passwords:** Via vault (no plaintext)

---

## 📅 Google Calendar

**Cuenta:** victor.arredondo.ambriz@gmail.com
**CLI:** `gcalcli`
**OAuth:** `~/.local/share/gcalcli/oauth`

### ⚠️ Calendarios a IGNORAR en briefs
- **What's Happening in Mexico City** — eventos públicos, no personales
- **Day of the Year** — metadata, no relevante
- **Phases of the Moon** — metadata, no relevante
- **Week Numbers** — metadata, no relevante

### Calendarios a INCLUIR en briefs
- victor.arredondo.ambriz@gmail.com (principal)
- svoppersdorff@gmail.com (Sof)
- n4m4ster (personal secundario)

```bash
# Ver agenda
gcalcli agenda

# Agregar evento
gcalcli --calendar "victor.arredondo.ambriz@gmail.com" add \
  --title "Reunión" --where "Oficina" --when "tomorrow 10am" --duration 60 --noprompt

# Ver semana
gcalcli calw
```

---

## What Goes Here

Things like:
- Camera names and locations
- SSH hosts and aliases  
- Preferred voices for TTS
- Speaker/room names
- Device nicknames
- Anything environment-specific

---

## 🗂️ Google Drive

**Service Account:** katia-bot@katia-lozano.iam.gserviceaccount.com
**Proyecto:** katia-lozano (ID: 487256869411)
**Credenciales:** ~/.credentials/katia-bot-gdrive.json
**Permisos:** Editor en folders compartidos

### Folders con acceso
- EZContact-Carrousels (ID: 1JappIgkDgZ1m23-VfodC7uzrWazZ7fVH)

### Uso
Para que tenga acceso a un folder, compartirlo con:
`katia-bot@katia-lozano.iam.gserviceaccount.com` como Editor

---

Add whatever helps you do your job. This is your cheat sheet.

---

## 🏦 Datos Bancarios — Cadena Lozaven

**Beneficiario:** Cadena Lozaven, SA de CV
**RFC:** CLO1101202S7
**Banco:** Banorte
**Cuenta:** 0673219778
**CLABE:** 072580006732197788

*Usar número de cotización como referencia*

---

## 🧾 CSF — Victor Alejandro Arredondo Ambriz (Persona Física)

*Fuente: Constancia de Situación Fiscal SAT, emitida 13 nov 2025*

**RFC:** AEAV880813RZ4
**Nombre:** VICTOR ALEJANDRO ARREDONDO AMBRIZ
**Régimen Fiscal:** Régimen Simplificado de Confianza (RESICO)
**CP:** 11800
**Email facturación:** n4m4ster@gmail.com

**Actividades económicas:**
- Agentes, ajustadores y gestores de seguros de vida (40%)
- Servicios de consultoría en administración (30%)
- Agentes, ajustadores y gestores de otros seguros (30%)

**Obligaciones RESICO:**
- ISR provisional: día 17 de cada mes
- IVA definitivo: día 17 de cada mes
- Declaración anual ISR: 30 de abril del año siguiente
