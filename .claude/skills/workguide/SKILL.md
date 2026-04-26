# Skill: Guía de trabajo — Release oficial de AudioRep

Este archivo es la referencia obligatoria antes de comenzar cualquier nueva versión de AudioRep.
Debe ser leído y aplicado al pie de la letra cada vez que el usuario solicite una nueva versión.

---

## PASO 0 — Proponer un plan de acción (REQUIERE APROBACIÓN — SIN EXCEPCIONES)

**Este paso es obligatorio siempre, sin excepción, tanto para mejoras como para nuevas funcionalidades.**
Antes de escribir una sola línea de código, se debe proponer un plan de acción estructurado.

El plan debe:
- Listar las funcionalidades a implementar, organizadas en **etapas numeradas** (Paso N).
- Seguir el estándar de nomenclatura del proyecto: `Paso 1`, `Paso 2`, etc., cada uno con un nombre descriptivo.
- Indicar qué archivos o capas se verán afectados en cada etapa (domain, core, services, infrastructure, ui).
- Estimar si alguna etapa tiene dependencias con otras.
- Ser presentado al usuario para su **aprobación expresa** antes de comenzar.

**No se avanza al Paso 1 hasta recibir confirmación del usuario.**
**No hay excepciones: ni para cambios "pequeños", ni para mejoras menores, ni para refactors. Siempre plan primero.**

---

## PASO 1 — Leer la documentación técnica antes de implementar

Antes de escribir código, leer los documentos técnicos del proyecto ubicados en `docs/`. Son la fuente de verdad sobre cómo está construido AudioRep y deben respetarse al pie de la letra:

| Archivo | Contenido |
|---|---|
| `docs/01_arquitectura.md` | Capas, flujo de dependencias y reglas de la arquitectura |
| `docs/02_dominio.md` | Entidades del dominio y sus atributos |
| `docs/03_interfaces.md` | Contratos (Protocols) que deben implementar la infraestructura |
| `docs/04_eventos.md` | Bus de eventos global (`app_events`) y señales disponibles |
| `docs/05_estructura_directorios.md` | Dónde va cada archivo nuevo dentro del proyecto |
| `docs/06_guia_desarrollo.md` | Guía paso a paso para agregar features siguiendo el estándar |

Si una nueva funcionalidad requiere cambios que afecten alguno de estos documentos (nuevas entidades, nuevas interfaces, nuevos eventos, etc.), **actualizar el documento correspondiente** como parte del mismo paso de implementación.

## PASO 2 — Implementar las funcionalidades aprobadas

Seguir el plan aprobado etapa por etapa. Aplicar en todo momento las convenciones del proyecto:

### Arquitectura (Clean Architecture)
```
domain → core → services ← infrastructure
                    ↑
              UI (controllers → widgets)
```
- Toda la inyección de dependencias ocurre en `main.py`.
- Los services reciben infraestructura por constructor; nunca la instancian.
- Los widgets solo emiten señales; nunca llaman a services directamente.
- Los controllers conectan señales de widgets con llamadas a services.
- Las operaciones largas se delegan a workers `QThread` internos al service.

### Convenciones clave
- Nuevos widgets → asignar `setObjectName(...)` y agregar regla en `dark.qss`.
- Nuevos services → `QObject`, workers como `_XxxWorker(QThread)` internos.
- Nuevos repositorios → implementar el protocolo `IXxxRepository` en `core/interfaces.py`.
- Nunca importar `infrastructure/` desde `services/`; solo usar interfaces de `core/`.

---

## PASO 3 — Actualizar la documentación interna del código

Al terminar la implementación:
- Actualizar el docstring de estado en `main.py` marcando los nuevos pasos como `✅`.
- Verificar que los docstrings de clases y métodos nuevos estén completos.

---

## PASO 4 — Bump de versión

Actualizar el número de versión en **cuatro lugares** (siempre los cuatro, nunca uno solo):

1. `pyproject.toml` → `version = "X.Y.Z"`
2. `main.py` → `app.setApplicationVersion("X.Y.Z")`
3. `audiorep/ui/main_window.py` → `setWindowTitle(...)` en `_setup_window()` → `"AudioRep X.Y"` (una sola llamada — el título dinámico fue eliminado en v0.59)
4. `installers/linux/build_deb.sh` → `VERSION="X.Y.Z"`

---

## PASO 5 — Actualizar README.md

El `README.md` es un documento **general del proyecto**, no específico de una versión. **No debe contener números de versión en ninguna parte** (ni en el título, ni en el cuerpo). Actualizar:

- La sección **Funciones principales**: agregar, modificar o eliminar ítems según los cambios.
- La sección **Librerías principales**: agregar nuevas dependencias si las hay.
- La sección **Herramientas de desarrollo**: actualizar si se agregaron herramientas.
- La sección **Instaladores**: actualizar la tabla con la nueva versión, fecha de compilación, nombre de archivo y tamaño. La tabla de instaladores es el **único lugar del README donde se indica el número de versión**, ya que su propósito es informar al usuario qué versión está disponible para descargar.

El historial de versiones y fechas va exclusivamente en `VERSION_HISTORY.md`.
El README debe redactarse en español, con tono descriptivo y conciso. No incluir detalles de implementación interna (eso va en `CLAUDE.md`).

---

## PASO 6 — Actualizar VERSION_HISTORY.md

Agregar una entrada **al principio del archivo** (las versiones más recientes van primero) con el siguiente formato:

```markdown
# X.Y — Nombre de la versión

**Fecha:** DD de mes de AAAA

### Agregado
- ...

### Modificado
- ...

### Eliminado
- ...
```

- Solo incluir las secciones que apliquen (si no hubo eliminaciones, omitir "Eliminado").
- El resumen debe ser claro y orientado al usuario, no al desarrollador.
- La fecha debe ser la del día en que se termina el desarrollo, no la de inicio.

---

## PASO 7 — Compilar los instaladores

**Responsabilidad del asistente.** Compilar ambos instaladores después de cada versión. Ver instrucciones completas en `CLAUDE.md`.

### Windows (.exe)
```bash
pip install -r requirements.txt
pip install pyinstaller
pyinstaller audiorep.spec \
    --distpath installers/windows \
    --workpath build/pyinstaller \
    --noconfirm
```
- Requiere VLC instalado en `C:/Program Files/VideoLAN/VLC/` en la máquina de build.
- El resultado es `installers/windows/AudioRep/AudioRep.exe` (~200+ MB, autocontenido).

### Linux (.deb)
```bash
# Desde WSL2 con Ubuntu, en la raíz del proyecto:
bash installers/linux/build_deb.sh
```
- Requiere haber instalado previamente las dependencias del sistema (ver `installers/linux/README.txt`).
- El resultado es `installers/linux/audiorep_X.Y.Z_amd64.deb`.

### Después de compilar
- Crear el ZIP del instalador de Windows: `AudioRep-X.Y.Z-windows.zip`.
  ```bash
  cd installers/windows && zip -r ../../installers/AudioRep-X.Y.Z-windows.zip AudioRep/
  ```
- El GitHub Release se crea **después de que el usuario haga push** (paso 9).

---

## PASO 8 — Verificar .gitignore y .gitattributes

Antes de que el usuario haga el commit, verificar que:

- `.gitignore` excluya correctamente: `build/`, `installers/windows/`, `installers/linux/*.deb`, `installers/*.zip`, `data/`, `.claude/`.
- `.gitattributes` no tenga archivos de texto (`.py`, `.json`, `.sh`, `.md`, etc.) configurados como LFS ni binarios.
- Si se agregaron nuevos tipos de archivo al proyecto, actualizar ambos archivos según corresponda.

---

## PASO 9 — Commit y push

**Responsabilidad del usuario.** Realizar por terminal una vez que el asistente haya completado todos los pasos anteriores.

```bash
git add <archivos>
git commit -m "AudioRep X.Y"
git push
```

El asistente espera confirmación del usuario antes de continuar con el PASO 10.

---

## PASO 10 — Publicar el GitHub Release

**Responsabilidad del asistente.** Ejecutar después de que el usuario haya confirmado que hizo push.

```bash
gh release create vX.Y.Z \
    installers/AudioRep-X.Y.Z-windows.zip \
    installers/linux/audiorep_X.Y.Z_amd64.deb \
    --title "AudioRep X.Y" \
    --notes "..."
```

El cuerpo del release debe incluir:
- Resumen de los cambios principales (extraído de `VERSION_HISTORY.md`).
- Instrucciones de instalación para Windows y Linux.

---

## Checklist de cierre de versión

- [ ] Plan aprobado por el usuario
- [ ] Funcionalidades implementadas y probadas
- [ ] Docstrings y estado en `main.py` actualizados
- [ ] Versión bumpeada en `pyproject.toml`, `main.py` y `main_window.py`
- [ ] `README.md` actualizado
- [ ] `VERSION_HISTORY.md` actualizado
- [ ] `.gitignore` y `.gitattributes` verificados/actualizados
- [ ] Instalador Windows compilado (`installers/windows/AudioRep/`) — **asistente**
- [ ] ZIP de Windows creado (`installers/AudioRep-X.Y.Z-windows.zip`) — **asistente**
- [ ] Instalador Linux compilado (`installers/linux/audiorep_X.Y.Z_amd64.deb`) — **asistente**
- [ ] Commit y push realizados — **usuario por terminal**
- [ ] GitHub Release publicado con ambos instaladores adjuntos — **asistente**
