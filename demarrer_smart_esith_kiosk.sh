#!/usr/bin/env bash
# ==============================================================================
# SMART ESITH v2.0 - Démarrage rapide en mode Kiosk TV (Raspberry Pi 4)
# ==============================================================================

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
# Si lancé au démarrage de la Raspberry Pi, attendre que l'environnement d'affichage soit initialisé
for i in {1..15}; do
    if [ -n "$DISPLAY" ] || [ -n "$WAYLAND_DISPLAY" ]; then
        break
    fi
    sleep 1
done

if [ -z "$DISPLAY" ] && [ -z "$WAYLAND_DISPLAY" ]; then
    export DISPLAY=:0
fi

exec "$SCRIPT_DIR/demarrer_smart_esith.sh" --kiosk

