#!/usr/bin/env bash
# ==============================================================================
# SMART ESITH v2.0 - Script d'arrêt rapide pour Raspberry Pi 4
# ==============================================================================

PORT="${PORT:-5001}"

echo "=========================================================="
echo "   🛑 ARRÊT DU SERVEUR SMART ESITH (Port $PORT)           "
echo "=========================================================="

FOUND=0

# Recherche du PID par port 5001
if command -v lsof >/dev/null 2>&1; then
    PID=$(lsof -ti:$PORT 2>/dev/null)
elif command -v fuser >/dev/null 2>&1; then
    PID=$(fuser $PORT/tcp 2>/dev/null | awk '{print $1}')
fi

# Si non trouvé par port, recherche par nom de processus
if [ -z "$PID" ]; then
    PID=$(pgrep -f "python.*app\.py" | head -n 1)
fi

if [ -n "$PID" ]; then
    echo "Fermeture du processus PID: $PID ..."
    kill "$PID" 2>/dev/null
    sleep 1
    if kill -0 "$PID" 2>/dev/null; then
        echo "Forçage de l'arrêt..."
        kill -9 "$PID" 2>/dev/null
    fi
    echo "✅ Smart ESITH a été arrêté avec succès."
    FOUND=1
fi

# Fermeture optionnelle des fenêtres Chromium en mode Kiosk de Smart ESITH
pkill -f "chromium.*5001" 2>/dev/null && echo "✅ Fenêtre d'affichage fermée."

if [ $FOUND -eq 0 ]; then
    echo "ℹ️ Aucun processus Smart ESITH en cours d'exécution sur le port $PORT."
fi

echo "=========================================================="
sleep 2

