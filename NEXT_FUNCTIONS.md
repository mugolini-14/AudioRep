# Funciones pendientes — AudioRep

Este archivo registra funcionalidades que fueron consideradas pero que no pudieron implementarse al momento, junto con el motivo y los requisitos necesarios para hacerlas en el futuro.

---

## Refactorización de performance del reproductor

~~Identificada en v0.50. Se implementaron los problemas 2, 3 y 4. Quedan pendientes:~~

✅ **Resuelto en v0.51** — Todos los problemas de performance del reproductor han sido implementados:
- Problemas 2, 3 y 4: resueltos en v0.50.
- Problema 1 (hilo RMS dedicado): resuelto en v0.51.
- Problema 5 (backpressure con log de underruns): resuelto en v0.51.

---

## Optimización de arranque del ejecutable Windows

**Descripción:**
El bundle de PyInstaller tarda varios segundos en iniciarse en Windows. Hay mejoras concretas identificadas que reducirían el tiempo de arranque sin cambios en el código de la aplicación.

**Cambios pendientes en `audiorep.spec`:**

- **Deshabilitar UPX** (`upx=False` en `EXE` y `COLLECT`) — es la mejora más significativa. UPX comprime cada `.pyd` individualmente; en un bundle de directorio, eso obliga a descomprimir cada módulo en cada arranque. El bundle quedará algo más grande en disco pero arrancará notablemente más rápido.
- **Ampliar la lista de `excludes`** — PyInstaller incluye módulos del stdlib que AudioRep no usa. Agregar:
  ```python
  "tkinter", "_tkinter",
  "pytest", "unittest", "doctest",
  "IPython", "jupyter", "notebook",
  "xml.etree.cElementTree", "lxml",
  "ftplib", "imaplib", "smtplib", "poplib", "xmlrpc", "http.server",
  "bz2", "lzma",
  "pydoc", "docutils",
  "setuptools", "pkg_resources", "distutils",
  "email", "multiprocessing",
  ```

**Recomendaciones para el usuario final (fuera del código):**
- Excluir la carpeta de instalación del antivirus (Windows Defender en particular escanea cada `.pyd` y `.dll` al cargarlos, añadiendo segundos al arranque).
- Instalar en SSD si es posible; con HDD el I/O de los ~180 archivos del `_internal/` domina el tiempo de arranque.

**Por qué no se implementó antes:**
Los cambios en el spec no afectan el código fuente, pero sí requieren un rebuild y validación de que ningún módulo excluido sea necesario en runtime. Se decidió dejarlo para una versión posterior para no demorar el release de la 0.40.

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
