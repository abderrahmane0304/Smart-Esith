#!/usr/bin/env bash
# ==============================================================================
# SMART ESITH v2.0 - Désactivation du Démarrage Automatique au Boot (Raspberry Pi 4)
# ==============================================================================

AUTOSTART_DIR="$HOME/.config/autostart"
AUTOSTART_FILE="$AUTOSTART_DIR/smart_esith_kiosk.desktop"
OLD_AUTOSTART_FILE="$AUTOSTART_DIR/smart_esith_autostart.desktop"

rm -f "$AUTOSTART_FILE" "$OLD_AUTOSTART_FILE" 2>/dev/null || true

LXDE_AUTOSTART_FILE="$HOME/.config/lxsession/LXDE-pi/autostart"
if [ -f "$LXDE_AUTOSTART_FILE" ]; then
    sed -i '/demarrer_smart_esith_kiosk/d' "$LXDE_AUTOSTART_FILE" 2>/dev/null || true
fi

echo "=========================================================="
echo "ℹ️  Démarrage automatique désactivé avec succès."
echo "Pour le réactiver à tout moment :"
echo "  ./activer_demarrage_automatique.sh"
echo "=========================================================="
