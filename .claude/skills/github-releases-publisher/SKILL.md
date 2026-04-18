# Skill: GitHub Releases Publisher — Publicación de releases de AudioRep

Este archivo define el formato y procedimiento obligatorio para publicar releases en GitHub.
Debe leerse antes de ejecutar `gh release create` o `gh release upload`.

---

## Tag y título

- **Tag:** `v{X.Y.Z}` — siempre con `v` minúscula y tres componentes. Ejemplo: `v0.50.0`
- **Título:** `AudioRep {X.Y}` — sin patch, sin `v`. Ejemplo: `AudioRep 0.50`

---

## Formato del cuerpo del release

```
## Cambios en esta version

### {Título de funcionalidad o corrección}
- Descripción en formato de lista desordenada.
- Una línea por ítem. Sin saltos de línea innecesarios.

### {Otro título si aplica}
- Ítem.
- Ítem.

---

## Instalacion

### Windows 10/11
1. Descargar `AudioRep-X.Y.Z-windows.zip` y descomprimir.
2. Ejecutar `AudioRep.exe`.
No requiere ninguna instalacion adicional.

### Linux (Debian / Ubuntu)
\`\`\`
sudo dpkg -i audiorep_X.Y.Z_amd64.deb
sudo apt-get install -f
\`\`\`
Requiere VLC instalado en el sistema.
```

**Reglas del cuerpo:**
- Sin tildes ni caracteres especiales — GitHub los renderiza bien pero el texto del release debe ser legible en texto plano también.
- El separador `---` entre "Cambios" e "Instalacion" es obligatorio.
- El contenido de "Cambios" se extrae de la entrada correspondiente en `VERSION_HISTORY.md`, adaptado al tono del ejemplo (orientado al usuario, no al desarrollador).
- No incluir detalles de implementación interna (nombres de clases, archivos, threads, etc.) salvo que sean relevantes para el usuario final.

---

## Ejemplo completo

```
## Cambios en esta version

### Dropdowns unificados
- Todos los desplegables de la aplicacion (selector de lectora de CD, servicio de metadatos, formato de ripeo en Configuracion) adoptan un estilo visual unificado con flecha indicadora chevron en el lateral derecho. El estado hover/foco resalta con el color de acento violeta.

### Refactor de performance del reproductor
- Latencia de avance de pista reducida: el polling de posicion bajo de 500 ms a 200 ms.
- VU metro apaga inmediatamente al presionar Stop (en pausa mantiene el decay visual gradual).
- Actualizacion de play_count asincrona: la escritura en la base de datos al terminar cada pista se ejecuta en un hilo de fondo, eliminando el bloqueo del hilo principal en la transicion entre pistas.

---

## Instalacion

### Windows 10/11
1. Descargar `AudioRep-0.50.0-windows.zip` y descomprimir.
2. Ejecutar `AudioRep.exe`.
No requiere ninguna instalacion adicional.

### Linux (Debian / Ubuntu)
\`\`\`
sudo dpkg -i audiorep_0.50.0_amd64.deb
sudo apt-get install -f
\`\`\`
Requiere VLC instalado en el sistema.
```

---

## Comando de publicación

```bash
gh release create vX.Y.Z \
    "installers/windows/AudioRep-X.Y.Z-windows.zip" \
    "installers/linux/audiorep_X.Y.Z_amd64.deb" \
    --title "AudioRep X.Y" \
    --notes "..."
```

- El release se publica **después de que el usuario haga push** — nunca antes.
- Adjuntar siempre ambos instaladores (Windows ZIP y Linux .deb).
- Si falta algún instalador, compilarlo primero siguiendo `.claude/skills/compiler-instructions/SKILL.md`.
