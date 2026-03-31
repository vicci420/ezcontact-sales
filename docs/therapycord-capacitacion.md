# Capacitación TherapyCord
## Salud Total + EZContact (Cordelia)

---

## 📋 Objetivo
Que el equipo de TherapyCord domine el uso de Salud Total para gestión de agenda y expedientes, y entienda cómo funciona Cordelia (asistente de voz) para atención telefónica automatizada.

---

## MÓDULO 1: Salud Total — Agenda

### 1.1 Acceso al Sistema
- **URL:** saludtotal.mx
- **Usuario:** [asignado por administrador]
- **Password:** [personal, no compartir]

### 1.2 Links Directos de Agenda por Terapeuta

| Terapeuta | Link de Agenda |
|-----------|----------------|
| Lic. Montserrat | https://www.saludtotal.mx/expediente/ba_agendaMedico.php?id=ODQ1NA |
| Lic. Kevin Castellanos | https://www.saludtotal.mx/expediente/ba_agendaMedico.php?id=ODQ1MA |
| Lic. Harold Ildefonso | https://www.saludtotal.mx/expediente/ba_agendaMedico.php?id=ODQ1NQ |
| Lic. Lilia Salazar | https://www.saludtotal.mx/expediente/ba_agendaMedico.php?id=ODQ1Mw |

### 1.3 Ver Disponibilidad (manual)
1. Ir a **Agenda** en el menú principal
2. Seleccionar **terapeuta** en el filtro superior
3. Seleccionar **fecha** en el calendario
4. Los horarios disponibles aparecen en **verde**
5. Los horarios ocupados aparecen en **rojo/gris**

### 1.3 Agendar Cita Nueva
1. Click en el horario disponible (verde)
2. Buscar paciente por **teléfono** o **nombre**
   - Si no existe → "Crear nuevo paciente"
3. Confirmar datos del paciente
4. Seleccionar **tipo de cita** (Valoración / Seguimiento)
5. Agregar **notas** si es necesario
6. Click en **Guardar**
7. El sistema envía confirmación automática por WhatsApp

### 1.4 Reagendar Cita
1. Buscar la cita en la agenda (por fecha o por paciente)
2. Click en la cita
3. Seleccionar **Reagendar**
4. Elegir nueva fecha/hora
5. Confirmar cambio
6. El paciente recibe notificación automática

### 1.5 Cancelar Cita
1. Buscar la cita
2. Click en la cita
3. Seleccionar **Cancelar**
4. Indicar motivo (opcional)
5. Confirmar
6. El paciente recibe notificación

---

## MÓDULO 2: Salud Total — Expediente del Paciente

### 2.1 Datos Obligatorios
Al registrar un paciente NUEVO, siempre capturar:

| Campo | Obligatorio | Notas |
|-------|-------------|-------|
| Nombre completo | ✅ SÍ | Como aparece en identificación |
| Teléfono | ✅ SÍ | Celular para WhatsApp |
| Fecha de nacimiento | ✅ SÍ | **NUEVO REQUISITO** |
| Email | Recomendado | Para confirmaciones |
| Motivo de consulta | ✅ SÍ | Breve descripción |

### 2.2 Actualizar Fecha de Nacimiento (Pacientes Existentes)
**⚠️ TAREA PENDIENTE:** 1,943 pacientes sin fecha de nacimiento

**Proceso:**
1. Al atender paciente recurrente, preguntar: *"Para actualizar tu expediente, ¿me confirmas tu fecha de nacimiento?"*
2. Ir a **Pacientes** → Buscar por nombre/teléfono
3. Click en **Editar**
4. Agregar fecha de nacimiento
5. Guardar

**Meta:** Completar 100% de expedientes en 30 días.

### 2.3 Notas de Sesión
Después de cada sesión, el terapeuta debe registrar:
- Ejercicios realizados
- Evolución del paciente
- Plan para siguiente sesión
- Observaciones relevantes

---

## MÓDULO 3: EZContact — Cordelia (Asistente de Voz)

### 3.0 Activar/Desactivar Cordelia (Desvío de llamadas)

**Número Twilio de Cordelia:** 55 9962 8751

Para que Cordelia atienda las llamadas entrantes, se debe activar el desvío desde la línea Telmex de TherapyCord:

| Acción | Código | Desde línea Telmex |
|--------|--------|-------------------|
| **ACTIVAR** Cordelia | `*21*5599628751#` | Marcar y esperar tono de confirmación |
| **DESACTIVAR** (volver a normal) | `#21#` | Marcar y esperar tono de confirmación |
| Verificar estado | `*#21#` | Muestra si hay desvío activo |

**⚠️ IMPORTANTE:**
- El desvío se activa desde el teléfono físico de la clínica
- Una vez activado, TODAS las llamadas entrantes van a Cordelia
- Para atender manualmente, primero desactivar con `#21#`
- El desvío se mantiene activo hasta que se desactive manualmente

**Horario recomendado:**
- **Activar** al inicio del día (antes de abrir)
- **Desactivar** si hay problemas técnicos o se necesita atención humana directa

---

### 3.1 ¿Qué es Cordelia?
Cordelia es una asistente virtual que atiende llamadas telefónicas al número de TherapyCord. Puede:

✅ Agendar citas nuevas
✅ Buscar pacientes existentes
✅ Consultar disponibilidad de terapeutas
✅ Responder preguntas frecuentes (horarios, precios, ubicación)
✅ Transferir a humano cuando es necesario

### 3.2 ¿Qué NO puede hacer Cordelia?
❌ Dar diagnósticos médicos
❌ Recomendar tratamientos específicos
❌ Atender emergencias (las deriva a urgencias)
❌ Resolver quejas complejas (transfiere a humano)

### 3.3 ¿Cómo se conecta con Salud Total?
Cordelia tiene acceso directo al sistema de Salud Total mediante funciones automáticas:

1. **Buscar paciente** → Cordelia pregunta teléfono → busca en Salud Total
2. **Ver disponibilidad** → Cordelia pregunta día/terapeuta → consulta agenda
3. **Agendar cita** → Cordelia confirma datos → crea cita en Salud Total
4. **Confirmación** → Salud Total envía WhatsApp automático al paciente

### 3.4 Flujo de Reservación de Cordelia

Cordelia tiene acceso a la **base de datos completa de pacientes** de Salud Total. Esto significa que ya "conoce" a todos los pacientes existentes.

#### Paciente EXISTENTE (ya tiene citas previas)
```
1. Cordelia pregunta: "¿Me das tu número de teléfono?"
2. Paciente da su número
3. Cordelia busca en Salud Total → ENCUENTRA al paciente
4. Cordelia confirma: "Hola [nombre], veo que ya nos has visitado antes..."
5. Continúa directo a agendar (ya tiene todos los datos)
```

#### Paciente NUEVO (primera vez)
```
1. Cordelia pregunta: "¿Me das tu número de teléfono?"
2. Paciente da su número
3. Cordelia busca en Salud Total → NO lo encuentra
4. Cordelia dice: "No tengo registro con ese número. ¿Es tu primera vez con nosotros?"
5. Si confirma que es nuevo, Cordelia pide:
   - Nombre completo
   - Fecha de nacimiento ← OBLIGATORIO para crear expediente
6. Cordelia crea el paciente en Salud Total
7. Continúa a agendar la cita
```

#### Datos que Cordelia solicita según el caso

| Tipo de paciente | Teléfono | Nombre | Fecha de Nacimiento |
|------------------|----------|--------|---------------------|
| **Existente** | ✅ (para identificarlo) | Ya lo tiene | Ya lo tiene* |
| **Nuevo** | ✅ | ✅ | ✅ |

*Si un paciente existente no tiene fecha de nacimiento en su expediente, Cordelia puede pedírsela para actualizar.

#### ¿Por qué pide fecha de nacimiento?
- Es requisito de Salud Total para crear expedientes completos
- Permite identificar pacientes con nombres similares
- Necesario para reportes y estadísticas médicas

### 3.5 ¿Cuándo transfiere a humano?
- Paciente pide hablar con persona
- Emergencia médica
- Queja o frustración
- Pregunta que no puede responder
- Error técnico

**Número de transferencia:** +52 55 1188 0301

---

## MÓDULO 4: EZContact — Plataforma de Gestión

### 4.0 ¿Qué es EZContact?

EZContact es la plataforma donde se gestionan todas las conversaciones con pacientes, tanto de WhatsApp como de llamadas telefónicas (Cordelia).

**URL de acceso:** https://beta.ezcontact.mx

### 4.1 Acceso al Dashboard

1. Ir a **beta.ezcontact.mx**
2. Iniciar sesión con credenciales asignadas
3. Seleccionar la cuenta **TherapyCord**

### 4.2 Secciones Principales

| Sección | Función |
|---------|---------|
| **Conversaciones** | Ver y responder mensajes de WhatsApp |
| **Contactos** | Base de datos de pacientes |
| **Historial** | Registro de llamadas atendidas por Cordelia |
| **Configuración** | Ajustes del agente y plantillas |

### 4.3 Gestión de Conversaciones

**Ver conversaciones activas:**
1. Click en **Conversaciones** en el menú
2. Las conversaciones nuevas aparecen arriba
3. Click en una conversación para ver el historial completo

**Responder manualmente (si es necesario):**
1. Abrir la conversación
2. Escribir mensaje en el campo de texto
3. Click en **Enviar**

⚠️ **Nota:** Cordelia responde automáticamente. Solo intervenir si:
- El paciente pide hablar con una persona
- Hay un problema que Cordelia no puede resolver
- Se necesita dar información muy específica

### 4.4 Base de Contactos

Todos los pacientes que escriben por WhatsApp o llaman se registran automáticamente en EZContact.

**Ver contactos:**
1. Click en **Contactos**
2. Buscar por nombre o teléfono
3. Click en un contacto para ver:
   - Datos personales
   - Historial de conversaciones
   - Notas

**Importar contactos:**
- Se pueden importar contactos masivamente via CSV
- Formato: Nombre, Empresa, Teléfono, Nota, Email
- Teléfonos en formato: `521XXXXXXXXXX`

### 4.5 Códigos de Confirmación

Cordelia genera un **código único** para cada cita agendada.

**Formato:** `MMDD-##`
- MMDD = mes y día de la cita
- ## = número consecutivo del día

**Ejemplos:**
| Código | Significado |
|--------|-------------|
| `0404-01` | Primera cita del 4 de abril |
| `0404-02` | Segunda cita del 4 de abril |
| `0515-05` | Quinta cita del 15 de mayo |

**¿Para qué sirve?**
- El paciente lo usa para reagendar o cancelar
- Facilita identificar la cita rápidamente
- Evita confusiones con nombres similares

### 4.6 Cordelia en WhatsApp

Además de atender llamadas, Cordelia también atiende mensajes de WhatsApp automáticamente.

**Mismo flujo:**
- Identifica si es paciente nuevo o existente
- Consulta disponibilidad en Salud Total
- Agenda citas
- Envía código de confirmación
- Responde preguntas frecuentes

**Número de WhatsApp:** 55 6304 9089

---

## MÓDULO 5: Flujo Integrado

```
PACIENTE LLAMA
      ↓
CORDELIA CONTESTA
"Hola, TherapyCord, soy Cordelia..."
      ↓
IDENTIFICA NECESIDAD
(agendar / reagendar / información)
      ↓
RECOPILA DATOS
nombre → teléfono → día preferido
      ↓
CONSULTA SALUD TOTAL
(busca paciente, revisa disponibilidad)
      ↓
AGENDA CITA
(crea en Salud Total)
      ↓
CONFIRMA AL PACIENTE
"Tu cita quedó para el jueves a las 10am..."
      ↓
WHATSAPP AUTOMÁTICO
(Salud Total envía confirmación)
      ↓
RECORDATORIO 24H ANTES
(automático)
```

---

## MÓDULO 5: Checklist Diario

### Recepción / Atención
- [ ] Revisar citas del día en Salud Total
- [ ] Confirmar asistencia de pacientes (si no confirmaron por WA)
- [ ] Actualizar expedientes con fecha de nacimiento faltante
- [ ] Reportar cualquier error de Cordelia

### Terapeutas
- [ ] Revisar agenda personal del día
- [ ] Registrar notas de sesión al terminar cada paciente
- [ ] Notificar cambios de horario a recepción

### Fin del día
- [ ] Verificar citas agendadas para mañana
- [ ] Confirmar que recordatorios WA se enviaron

---

## 📞 Soporte

**Problemas con Salud Total:**
→ Contactar a soporte técnico: [PENDIENTE]

**Problemas con Cordelia/EZContact:**
→ Contactar a Victor: +52 55 1188 0301

**Dudas operativas:**
→ Dr. Ivan Velázquez o administración

---

*Documento creado: 27 marzo 2026*
*Próxima revisión: abril 2026*
