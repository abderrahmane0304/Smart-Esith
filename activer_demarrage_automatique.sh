#!/usr/bin/env bash
# ==============================================================================
# SMART ESITH v2.0 - Activation du Démarrage Automatique au Boot (Raspberry Pi 4)
# Lance automatiquement le serveur Smart ESITH et l'écran Kiosk TV au démarrage
# ==============================================================================

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
KIOSK_LAUNCHER="$SCRIPT_DIR/demarrer_smart_esith_kiosk.sh"
AUTOSTART_DIR="$HOME/.config/autostart"
AUTOSTART_FILE="$AUTOSTART_DIR/smart_esith_kiosk.desktop"

if [ -f "$SCRIPT_DIR/backend/static/logo-esith-header.png" ]; then
    ICON="$SCRIPT_DIR/backend/static/logo-esith-header.png"
else
    ICON="$SCRIPT_DIR/backend/static/logo-esith.png"
fi

echo "=========================================================="
echo "    🚀 ACTIVATION DU DÉMARRAGE AUTOMATIQUE (BOOT)        "
echo "=========================================================="
echo "Projet : $SCRIPT_DIR"
echo ""

# 1. Rendre exécutables les scripts nécessaires
chmod +x "$SCRIPT_DIR"/*.sh 2>/dev/null || true

# 2. Installation de l'utilitaire unclutter pour masquer la souris si nécessaire
if command -v apt-get >/dev/null 2>&1; then
    if ! command -v unclutter >/dev/null 2>&1; then
        echo "🖱️  Installation de unclutter (masquage automatique du curseur de souris)..."
        sudo apt-get update -y && sudo apt-get install -y --no-install-recommends unclutter 2>/dev/null || true
    fi
fi

# 3. Désactivation de la mise en veille écran (HDMI Always ON)
if command -v raspi-config >/dev/null 2>&1; then
    sudo raspi-config nonint do_blanking 1 2>/dev/null || true
fi

# 4. Création de l'entrée XDG Autostart (~/.config/autostart/)
mkdir -p "$AUTOSTART_DIR"

cat <<EOF > "$AUTOSTART_FILE"
[Desktop Entry]
Version=1.0
Type=Application
Name=Smart ESITH (Kiosk TV)
Comment=Démarrage automatique Smart ESITH Kiosk au démarrage du Raspberry Pi
Exec=/bin/bash "$KIOSK_LAUNCHER"
Icon=$ICON
Path=$SCRIPT_DIR
Terminal=false
Categories=Application;Education;
StartupNotify=false
X-GNOME-Autostart-enabled=true
EOF

chmod +x "$AUTOSTART_FILE" 2>/dev/null || true
if command -v gio >/dev/null 2>&1; then
    gio set "$AUTOSTART_FILE" metadata::trusted true 2>/dev/null || true
fi

# 5. Prise en charge complémentaire pour session LXDE-pi
LXDE_AUTOSTART_DIR="$HOME/.config/lxsession/LXDE-pi"
if [ -d "$LXDE_AUTOSTART_DIR" ]; then
    LXDE_AUTOSTART_FILE="$LXDE_AUTOSTART_DIR/autostart"
    if [ -f "$LXDE_AUTOSTART_FILE" ]; then
        if ! grep -q "demarrer_smart_esith_kiosk.sh" "$LXDE_AUTOSTART_FILE" 2>/dev/null; then
            echo "@/bin/bash \"$KIOSK_LAUNCHER\"" >> "$LXDE_AUTOSTART_FILE"
        fi
    fi
fi

echo "=========================================================="
echo "✅ DÉMARRAGE AUTOMATIQUE ACTIVÉ AVEC SUCCÈS !"
echo "=========================================================="
echo "Dès que la Raspberry Pi s'allume ou redémarre :"
echo "  1. Le serveur Smart ESITH se lance automatiquement en arrière-plan."
echo "  2. L'affichage dynamique du Hall s'ouvre directement en plein écran (Kiosk TV)."
echo "  3. Le pointeur de la souris est totalement invisible sur l'écran."
echo "  4. La mise en veille HDMI est désactivée (écran toujours allumé)."
echo ""
echo "Fichier configuré : $AUTOSTART_FILE"
echo "=========================================================="
