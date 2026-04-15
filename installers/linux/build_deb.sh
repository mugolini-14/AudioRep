#!/usr/bin/env bash
# ============================================================
# AudioRep — Build script para .deb (Debian / Ubuntu)
#
# Requisitos en la máquina de build (Ubuntu/Debian):
#   sudo apt-get install -y python3 python3-venv python3-pip \
#       vlc libvlc-dev libchromaprint-tools ruby ruby-dev
#   sudo gem install fpm
#
# Uso:
#   bash installers/linux/build_deb.sh
#
# Salida:
#   installers/linux/audiorep_<version>_amd64.deb
# ============================================================

set -euo pipefail

# ── Rutas ────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
VENV_DIR="$PROJECT_ROOT/build/linux/venv"
STAGE_DIR="$PROJECT_ROOT/build/linux/stage"
DIST_DIR="$PROJECT_ROOT/installers/linux"

# ── Versión ───────────────────────────────────────────────────────────
VERSION="0.25.0"
APP_NAME="audiorep"
INSTALL_PATH="/opt/audiorep"

echo "=================================================="
echo " AudioRep $VERSION — Build .deb"
echo "=================================================="

# ── Paso 1: Entorno virtual ───────────────────────────────────────────
echo "[1/5] Creando entorno virtual..."
python3 -m venv "$VENV_DIR"
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

echo "[1/5] Instalando dependencias..."
pip install --quiet --upgrade pip
pip install --quiet -r "$PROJECT_ROOT/requirements.txt"
pip install --quiet pyinstaller

# ── Paso 2: PyInstaller ───────────────────────────────────────────────
echo "[2/5] Compilando con PyInstaller..."
cd "$PROJECT_ROOT"
DIST_BUILD="$PROJECT_ROOT/build/linux/dist"
python -m PyInstaller audiorep.spec \
    --distpath "$DIST_BUILD" \
    --workpath "$PROJECT_ROOT/build/linux/pyinstaller" \
    --noconfirm

deactivate

# ── Paso 3: Estructura de staging ─────────────────────────────────────
echo "[3/5] Preparando estructura de staging..."

# Copiar el directorio compilado al staging
rm -rf "$STAGE_DIR/opt/$APP_NAME"
mkdir -p "$STAGE_DIR/opt"
if [ -d "$DIST_BUILD/AudioRep" ]; then
    cp -r "$DIST_BUILD/AudioRep" "$STAGE_DIR/opt/$APP_NAME"
elif [ -d "$DIST_BUILD/audiorep" ]; then
    cp -r "$DIST_BUILD/audiorep" "$STAGE_DIR/opt/$APP_NAME"
else
    echo "ERROR: No se encontró el directorio de salida de PyInstaller en $DIST_BUILD"
    ls "$DIST_BUILD" || true
    exit 1
fi

# Crear entrada en el menú de aplicaciones
DESKTOP_DIR="$STAGE_DIR/usr/share/applications"
mkdir -p "$DESKTOP_DIR"
cat > "$DESKTOP_DIR/audiorep.desktop" <<EOF
[Desktop Entry]
Name=AudioRep
Comment=Reproductor de música local, CD y radio
Exec=$INSTALL_PATH/audiorep
Icon=$INSTALL_PATH/audiorep.png
Terminal=false
Type=Application
Categories=AudioVideo;Audio;Player;
EOF

# Wrapper script en /usr/bin para llamarlo desde la terminal
BIN_DIR="$STAGE_DIR/usr/bin"
mkdir -p "$BIN_DIR"
cat > "$BIN_DIR/audiorep" <<EOF
#!/bin/sh
exec "$INSTALL_PATH/audiorep" "\$@"
EOF
chmod +x "$BIN_DIR/audiorep"

# ── Paso 4: Empaquetar con fpm ────────────────────────────────────────
echo "[4/5] Creando paquete .deb con fpm..."
mkdir -p "$DIST_DIR"

fpm \
    --input-type dir \
    --output-type deb \
    --name "$APP_NAME" \
    --version "$VERSION" \
    --architecture amd64 \
    --maintainer "mugolini-14" \
    --description "Reproductor de música local, CD y radio por internet" \
    --url "https://github.com/mugolini-14/AudioRep" \
    --depends vlc \
    --depends "libchromaprint-tools | fpcalc" \
    --prefix / \
    --package "$DIST_DIR/${APP_NAME}_${VERSION}_amd64.deb" \
    --force \
    "$STAGE_DIR/opt/$APP_NAME=$INSTALL_PATH" \
    "$STAGE_DIR/usr/share/applications/audiorep.desktop=/usr/share/applications/audiorep.desktop" \
    "$STAGE_DIR/usr/bin/audiorep=/usr/bin/audiorep"

# ── Paso 5: Resultado ─────────────────────────────────────────────────
echo "[5/5] Listo."
DEB_FILE="$DIST_DIR/${APP_NAME}_${VERSION}_amd64.deb"
if [ -f "$DEB_FILE" ]; then
    SIZE_MB=$(du -m "$DEB_FILE" | cut -f1)
    echo ""
    echo "✓ Paquete generado: $DEB_FILE (~${SIZE_MB} MB)"
else
    echo "✗ Error: no se generó el .deb"
    exit 1
fi
