#!/usr/bin/env bash
# ==============================================================================
# SMART ESITH v2.0 - Script de démarrage rapide pour Raspberry Pi 4
# Équivalent de DEMARRER_SMART_ESITH.bat sous Linux / Raspberry Pi OS
# ==============================================================================

# Obtenir le chemin absolu du dossier du projet
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
BACKEND_DIR="$SCRIPT_DIR/backend"
PORT="${PORT:-5001}"
URL="http://localhost:${PORT}"

# Vérifier si le mode Kiosk plein écran est demandé (--kiosk ou variable KIOSK=1)
IS_KIOSK=0
if [ "$1" = "--kiosk" ] || [ "$KIOSK" = "1" ]; then
    IS_KIOSK=1
fi

echo "=========================================================="
echo "   🚀 DÉMARRAGE SMART ESITH v2.0 (Raspberry Pi 4)        "
echo "=========================================================="
echo "Dossier projet : $SCRIPT_DIR"
echo "Port           : $PORT"
if [ "$IS_KIOSK" -eq 1 ]; then
    echo "Mode affichage : 📺 Kiosk TV Plein Écran (Hall)"
else
    echo "Mode affichage : 🌐 Fenêtre standard"
fi
echo "=========================================================="
echo ""

# 1. Vérification de Python 3
if ! command -v python3 >/dev/null 2>&1; then
    echo "❌ Erreur : Python 3 n'est pas installé !"
    echo "Veuillez exécuter : sudo apt update && sudo apt install -y python3 python3-pip python3-venv"
    echo ""
    read -p "Appuyez sur Entrée pour fermer..."
    exit 1
fi

# 2. Accès au dossier backend
cd "$BACKEND_DIR" || {
    echo "❌ Erreur : Dossier backend introuvable à : $BACKEND_DIR"
    exit 1
}

# 3. Création de l'environnement virtuel (venv) si inexistant
if [ ! -d "venv" ]; then
    echo "📦 Création de l'environnement virtuel (venv)..."
    python3 -m venv venv 2>/dev/null || {
        echo "⚠️ Échec de création du venv avec python3 -m venv."
        echo "Installation de python3-venv requise :"
        echo "  sudo apt update && sudo apt install -y python3-venv python3-pip"
        read -p "Appuyez sur Entrée pour quitter..."
        exit 1
    }
fi

# 4. Activation de l'environnement virtuel
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
else
    echo "❌ venv/bin/activate introuvable."
    exit 1
fi

# 5. Vérification rapide des dépendances (optimisée pour la rapidité au boot du Pi)
echo "🔍 Vérification des dépendances Python..."
if ! python -c "import flask, waitress, pandas, sqlalchemy, openpyxl, jwt" 2>/dev/null; then
    echo "📦 Installation / mise à jour des dépendances depuis requirements.txt..."
    pip install -r requirements.txt --quiet
    if [ $? -ne 0 ]; then
        echo "❌ Erreur lors de l'installation des dépendances."
        read -p "Appuyez sur Entrée pour fermer..."
        exit 1
    fi
else
    echo "✅ Dépendances Python déjà prêtes."
fi

# Récupération de l'adresse IP locale du Raspberry Pi pour accès réseau
IP_LOCALE=$(hostname -I 2>/dev/null | awk '{print $1}')

echo ""
echo "=========================================================="
echo "✅ SERVEUR PRÊT À DÉMARRER"
echo "🌐 Accès local (sur ce Raspberry Pi) :"
echo "   - Écran Hall (TV) : $URL/"
echo "   - Dashboard       : $URL/dashboard"
if [ -n "$IP_LOCALE" ]; then
    echo ""
    echo "📡 Accès réseau local (depuis PC Scolarité/Admin) :"
    echo "   - Dashboard       : http://${IP_LOCALE}:${PORT}/dashboard"
    echo "   - Écran Hall      : http://${IP_LOCALE}:${PORT}/"
fi
echo "=========================================================="
echo "💡 Pour arrêter le serveur, fermez cette fenêtre ou faites Ctrl+C."
echo ""

# 6. Ouverture automatique du navigateur dès que le serveur écoute
(
    # Attendre que le port soit actif (timeout 30s)
    for i in {1..30}; do
        if python -c "import socket; s = socket.socket(); s.connect(('127.0.0.1', $PORT)); s.close()" 2>/dev/null; then
            break
        fi
        sleep 1
    done

    # Détection du navigateur installé
    BROWSER_BIN=""
    if command -v chromium-browser >/dev/null 2>&1; then
        BROWSER_BIN="chromium-browser"
    elif command -v chromium >/dev/null 2>&1; then
        BROWSER_BIN="chromium"
    elif command -v firefox >/dev/null 2>&1; then
        BROWSER_BIN="firefox"
    elif command -v xdg-open >/dev/null 2>&1; then
        BROWSER_BIN="xdg-open"
    fi

    if [ -n "$BROWSER_BIN" ]; then
        if [ "$IS_KIOSK" -eq 1 ]; then
            echo "📺 Démarrage de Chromium en mode Kiosk plein écran..."
            $BROWSER_BIN --noerrdialogs \
                         --disable-infobars \
                         --check-for-update-interval=31536000 \
                         --disable-session-crashed-bubble \
                         --kiosk "$URL" >/dev/null 2>&1 &
        else
            echo "🌐 Démarrage du navigateur..."
            if [ "$BROWSER_BIN" = "xdg-open" ]; then
                xdg-open "$URL" >/dev/null 2>&1 &
            else
                $BROWSER_BIN --app="$URL" >/dev/null 2>&1 || $BROWSER_BIN "$URL" >/dev/null 2>&1 &
            fi
        fi
    fi
) &

# 7. Exécution de l'application Smart ESITH (Waitress en production)
exec python app.py

