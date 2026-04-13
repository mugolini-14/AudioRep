# Funciones pendientes — AudioRep

Este archivo registra funcionalidades que fueron consideradas pero que no pudieron implementarse al momento, junto con el motivo y los requisitos necesarios para hacerlas en el futuro.

---

## Radio FM real (sintonización de señal en vivo)

**Descripción:**
Permitir que AudioRep sintonice emisoras de FM del aire en tiempo real, usando el rango de frecuencias estándar (88.0–108.0 MHz), sin depender de streams de internet.

**Por qué no se implementó:**
Requiere hardware específico no disponible al momento del desarrollo. Una PC estándar no puede recibir señales FM por sí sola.

**Requisitos para implementarla:**

- **Hardware:** dongle RTL-SDR (basado en chipset Realtek RTL2832U), disponible por ~$20 USD. Requiere antena VHF compatible con la banda FM.
- **Driver:** driver USB `WinUSB` instalado via Zadig (Windows) o `rtl-sdr` via apt (Linux).
- **Librería Python:** `pyrtlsdr` (wrapper de `librtlsdr`). En Windows requiere además `librtlsdr.dll` y `libusb-1.0.dll` accesibles en el PATH o junto al ejecutable.

**Notas de implementación:**
- La demodulación FM se puede hacer con `scipy` o `numpy` sobre los datos IQ que devuelve el dongle.
- La reproducción del audio demodulado puede integrarse con el `PlayerService` existente o manejarse por separado.
- La UI podría reutilizar el widget de dial visual ya implementado en la versión 0.20, extendiendo el `RadioPanel` para distinguir entre modo "internet" y modo "FM real".
- Convendría detectar en tiempo de ejecución si hay un dispositivo RTL-SDR conectado y habilitar el modo FM real solo si está disponible.
