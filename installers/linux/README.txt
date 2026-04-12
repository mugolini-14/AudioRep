INSTALADOR .DEB — AudioRep 0.10
================================

El paquete .deb NO puede compilarse desde Windows sin WSL instalado.
Para generarlo se necesita un sistema Linux (Ubuntu / Debian) o WSL2.

Pasos:

1. Desde Linux o WSL2, posicionarse en la raíz del proyecto:
   cd /ruta/al/proyecto/AudioRep

2. Instalar dependencias del sistema:
   sudo apt-get install python3 python3-venv python3-pip \
       ruby ruby-dev rubygems build-essential \
       vlc libvlc-dev libchromaprint-tools


3. Instalar fpm (empaquetador):
   sudo gem install fpm

4. Ejecutar el script:
   bash installers/linux/build_deb.sh

5. El archivo generado quedará en:
   installers/linux/audiorep_0.10.0_amd64.deb

6. Para instalarlo en el sistema destino:
   sudo dpkg -i audiorep_0.10.0_amd64.deb
   sudo apt-get install -f
