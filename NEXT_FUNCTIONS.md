# Funciones pendientes — AudioRep

Este archivo registra funcionalidades que fueron consideradas pero que no pudieron implementarse al momento, junto con el motivo y los requisitos necesarios para hacerlas en el futuro.

---

## Radio FM real (sintonización de señal en vivo)

**Descripción:**
Permitir que AudioRep sintonice emisoras de FM del aire en tiempo real, usando el rango de frecuencias estándar (88.0–108.0 MHz), sin depender de streams de internet.

**Por qué no se implementó:**
Requiere hardware específico no disponible al momento del desarrollo. Una PC estándar no puede recibir señales FM por sí sola.

**Requisitos para implementarla:**

- **Hardware investigado:** dongle RTL-SDR con chipset **RTL2832U + R820T2** (sintonizador). Rango real: ~24 MHz a 1766 MHz. El aparato disponible en MercadoLibre Argentina ("receptor SDR 30 MHz a 1.7 GHz 820T2") es exactamente este combo. Es el SDR con mejor soporte en Python/Windows que existe.
- **Driver (Windows):** instalar **Zadig** → seleccionar el dispositivo RTL2832U → aplicar driver `WinUSB` o `libusb-win32`. Gratuito, bien mantenido.
- **Driver (Linux):** `sudo apt install rtl-sdr` (incluye `librtlsdr` y `rtl_fm`).
- **Librería Python:** `pyrtlsdr` (wrapper de `librtlsdr`, instalable con pip). En Windows requiere `librtlsdr.dll` y `libusb-1.0.dll` en el PATH o junto al ejecutable.

**Stack de implementación:**

```
pyrtlsdr  →  IQ samples raw  →  demodulación FM (numpy/scipy)  →  audio PCM  →  VLC / sounddevice
```

1. **`core/interfaces.py`** — agregar protocolo `IRadioTuner` con métodos `tune(freq_mhz)`, `scan()`, `stop()`.
2. **`services/rtlsdr_service.py`** — `RtlSdrService(QObject)` con un worker `_RtlSdrWorker(QThread)` que lee samples continuamente y emite audio demodulado.
3. **`ui/widgets/`** — extender el `RadioPanel` existente para distinguir entre modo "internet" y modo "FM real (SDR)".
4. **Detección en runtime** — detectar si hay un dispositivo RTL-SDR conectado al arrancar y habilitar el modo FM real solo si está disponible.
5. **RDS (bonus)** — decodificar RDS para mostrar el nombre de la emisora en el panel.

**Notas adicionales:**
- La demodulación FM por software sobre datos IQ es código conocido y bien documentado; hay ejemplos listos con `numpy`/`scipy`.
- Convendría tener una librería alternativa como `rtlsdr-scanner` para el scan automático de estaciones.
- La antena incluida con los dongles genéricos es suficiente para pruebas; para uso real conviene una antena VHF dedicada.
