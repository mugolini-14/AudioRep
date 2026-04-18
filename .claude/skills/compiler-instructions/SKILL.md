# Skill: Compiler Instructions — Compilación de instaladores de AudioRep

Este archivo define el procedimiento obligatorio para compilar los instaladores de AudioRep.
Debe leerse antes de ejecutar cualquier compilación (Windows o Linux).

---

## Entorno de build — Windows

### Rutas del sistema

| Recurso | Ruta |
|---|---|
| Ejecutable Python | `C:\Program Files\Python313\python.exe` |
| Scripts Python (pip, pyinstaller) | `C:\Program Files\Python313\Scripts\` |

### Shell preferido para compilar en Windows

Usar en este orden de preferencia:

1. **PowerShell** — shell preferido. Ejemplo:
   ```powershell
   Set-Location "g:\Repositorios_Propios\AudioRep"
   & "C:\Program Files\Python313\python.exe" -m PyInstaller audiorep.spec `
       --distpath installers/windows `
       --workpath build/pyinstaller `
       --noconfirm
   ```

2. **CMD** — alternativa si PowerShell falla.

3. **bash (Git Bash / MSYS2)** — última instancia. En bash, `python` y `pyinstaller` pueden no estar en el PATH; usar la ruta completa:
   ```bash
   "/c/Program Files/Python313/python.exe" -m PyInstaller audiorep.spec \
       --distpath installers/windows \
       --workpath build/pyinstaller \
       --noconfirm
   ```

> **Nota:** El alias `python` en PowerShell y CMD puede apuntar al stub del Microsoft Store (no funciona). Usar siempre la ruta completa `C:\Program Files\Python313\python.exe` o llamar via `python -m ...` desde un contexto donde `python` esté correctamente en el PATH (verificar con `python --version` antes de compilar).

### Salida del instalador Windows

- **Ejecutable:** `installers/windows/AudioRep/AudioRep.exe`
- **ZIP distribuible:** `installers/windows/AudioRep-X.Y.Z-windows.zip`

El ZIP se crea con PowerShell:
```powershell
Compress-Archive -Path "installers\windows\AudioRep" `
    -DestinationPath "installers\windows\AudioRep-X.Y.Z-windows.zip" -Force
```

---

## Entorno de build — Linux

### Shell preferido

Usar **WSL2** (Ubuntu). Si WSL2 no está disponible, buscar alternativa (máquina virtual, CI remota).

```bash
wsl bash -c "cd /mnt/g/Repositorios_Propios/AudioRep && bash installers/linux/build_deb.sh"
```

### Verificación obligatoria antes de compilar el .deb

**Antes de ejecutar `build_deb.sh`, verificar que la variable `VERSION` en el script esté actualizada.**

El script `installers/linux/build_deb.sh` tiene la versión hardcodeada en la línea:
```bash
VERSION="X.Y.Z"
```

Pasos obligatorios:
1. Leer `installers/linux/build_deb.sh` y verificar que `VERSION` coincida con la versión del release.
2. Si no coincide, actualizarla antes de ejecutar el script.
3. Recién entonces compilar.

Omitir este paso genera un `.deb` con la versión anterior, que luego hay que recompilar.

### Salida del instalador Linux

- **Paquete .deb:** `installers/linux/audiorep_X.Y.Z_amd64.deb`

---

## Checklist de compilación (por versión)

### Windows
- [ ] Verificar que el código fuente ya tiene el bump de versión (`pyproject.toml`, `main.py`, `main_window.py`)
- [ ] Ejecutar PyInstaller via PowerShell con ruta completa a Python
- [ ] Verificar que `installers/windows/AudioRep/AudioRep.exe` tiene timestamp actual
- [ ] Crear ZIP en `installers/windows/AudioRep-X.Y.Z-windows.zip`

### Linux
- [ ] Leer `installers/linux/build_deb.sh` y confirmar que `VERSION="X.Y.Z"` es correcto
- [ ] Actualizar la versión en el script si es necesario
- [ ] Ejecutar el script desde WSL2
- [ ] Verificar que `installers/linux/audiorep_X.Y.Z_amd64.deb` fue generado

---

## Recuperación de una versión no compilada

Si por alguna razón se omitió compilar los instaladores de una versión ya commiteada y pusheada, se debe recuperar el código fuente de ese commit para compilar desde él. El orden de búsqueda es:

### 1. Branch `release/{nro_version}` en el remoto

```bash
git fetch origin
git checkout release/{nro_version}
```

Ejemplo para la versión 0.49: `git checkout release/0.49`

### 2. Branch `dev` — si no existe el branch de release

```bash
git checkout dev
git log --oneline | grep "AudioRep {nro_version}"
# Anotar el hash del commit encontrado
git checkout {hash}
```

### 3. Branch `main` — como última instancia

```bash
git checkout main
git log --oneline | grep "AudioRep {nro_version}"
git checkout {hash}
```

### Procedimiento después de ubicar el commit

1. Verificar que el código en ese commit tiene la versión correcta en `pyproject.toml`.
2. Compilar los instaladores normalmente (Windows y Linux) siguiendo este SKILL.md.
3. Volver al branch original al terminar: `git checkout dev`.
4. **No hacer commits ni push** desde el estado de detached HEAD — solo compilar.

> **Importante:** Los ZIPs y .deb compilados quedan en el worktree local (`installers/`). Desde ahí se adjuntan al GitHub Release con `gh release create` o `gh release upload`.

---

## Errores conocidos y soluciones

| Error | Causa | Solución |
|---|---|---|
| `pyinstaller: command not found` (bash) | `Scripts/` no está en el PATH de bash | Usar `python -m PyInstaller` con ruta completa |
| `python: no se encontró Python` (PowerShell) | Alias del Microsoft Store | Usar ruta completa `C:\Program Files\Python313\python.exe` |
| `.deb` generado con versión anterior | `VERSION` en `build_deb.sh` no fue actualizado | Siempre verificar el script antes de compilar |
| `AudioRep.exe` con timestamp anterior | PyInstaller usó caché o el comando falló silenciosamente | Verificar el timestamp del exe después de compilar; si no cambió, revisar el log del build |
| ZIP en ubicación incorrecta | Workguide antiguo indicaba `installers/` raíz | El ZIP va en `installers/windows/`, el .deb en `installers/linux/` |
