#!/usr/bin/env bash
# ==============================================================================
# SMART ESITH v2.0 - Installateur du bouton de démarrage rapide
# Pour Raspberry Pi 4 (Raspberry Pi OS - Bookworm / Bullseye / Buster)
# ==============================================================================

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
LAUNCHER="$SCRIPT_DIR/demarrer_smart_esith.sh"
STOPPER="$SCRIPT_DIR/arreter_smart_esith.sh"
ICON="$SCRIPT_DIR/backend/static/logo-esith.png"

echo "=========================================================="
echo "    🎓 SMART ESITH v2.0 - INSTALLATEUR RASPBERRY PI 4    "
echo "=========================================================="
echo "Dossier détecté : $SCRIPT_DIR"
echo ""

# 1. Rendre exécutables les scripts du projet
echo "🔧 [1/4] Configuration des permissions d'exécution..."
chmod +x "$LAUNCHER" 2>/dev/null || true
if [ -f "$STOPPER" ]; then
    chmod +x "$STOPPER" 2>/dev/null || true
fi
echo "   ✅ Scripts autorisés en exécution."

# 2. Vérification des prérequis système
echo "🔍 [2/4] Vérification des paquets nécessaires..."
MISSING_PKGS=""
if ! command -v python3 >/dev/null 2>&1; then
    MISSING_PKGS="$MISSING_PKGS python3"
fi
if ! python3 -m venv --help >/dev/null 2>&1; then
    MISSING_PKGS="$MISSING_PKGS python3-venv"
fi
if ! command -v pip3 >/dev/null 2>&1 && ! command -v pip >/dev/null 2>&1; then
    MISSING_PKGS="$MISSING_PKGS python3-pip"
fi

if [ -n "$MISSING_PKGS" ]; then
    echo "   ⚠️ Paquets manquants détectés :$MISSING_PKGS"
    echo "   Tentative d'installation automatique via sudo apt..."
    sudo apt update && sudo apt install -y $MISSING_PKGS
else
    echo "   ✅ Tous les paquets système requis sont installés."
fi

# 3. Détection du dossier Bureau (Desktop / Bureau)
echo "📁 [3/4] Détection de l'emplacement du Bureau..."
DESKTOP_DIRS=()
if command -v xdg-user-dir >/dev/null 2>&1; then
    XDG_DESK="$(xdg-user-dir DESKTOP 2>/dev/null)"
    if [ -d "$XDG_DESK" ]; then
        DESKTOP_DIRS+=("$XDG_DESK")
    fi
fi
if [ -d "$HOME/Desktop" ] && [[ ! " ${DESKTOP_DIRS[@]} " =~ " $HOME/Desktop " ]]; then
    DESKTOP_DIRS+=("$HOME/Desktop")
fi
if [ -d "$HOME/Bureau" ] && [[ ! " ${DESKTOP_DIRS[@]} " =~ " $HOME/Bureau " ]]; then
    DESKTOP_DIRS+=("$HOME/Bureau")
fi

if [ ${#DESKTOP_DIRS[@]} -eq 0 ]; then
    mkdir -p "$HOME/Desktop"
    DESKTOP_DIRS+=("$HOME/Desktop")
fi

# 4. Création des boutons raccourcis (.desktop)
echo "🎨 [4/4] Création des boutons de démarrage sur le Bureau..."

for DDIR in "${DESKTOP_DIRS[@]}"; do
    # Bouton 1 : Démarrage Standard
    FILE_STD="$DDIR/Smart_ESITH.desktop"
    cat <<EOF > "$FILE_STD"
[Desktop Entry]
Version=1.0
Type=Application
Name=Smart ESITH
Comment=Démarrer Smart ESITH (Serveur + Navigateur)
Exec=$LAUNCHER
Icon=$ICON
Path=$SCRIPT_DIR
Terminal=true
Categories=Education;Application;
StartupNotify=true
EOF
    chmod +x "$FILE_STD"
    if command -v gio >/dev/null 2>&1; then
        gio set "$FILE_STD" metadata::trusted true 2>/dev/null || true
    fi

    # Bouton 2 : Démarrage Kiosk TV Hall (Plein écran automatique)
    FILE_KIOSK="$DDIR/Smart_ESITH_Kiosk_TV.desktop"
    cat <<EOF > "$FILE_KIOSK"
[Desktop Entry]
Version=1.0
Type=Application
Name=Smart ESITH (Kiosk TV)
Comment=Démarrer Smart ESITH en mode plein écran TV pour le Hall
Exec=$LAUNCHER --kiosk
Icon=$ICON
Path=$SCRIPT_DIR
Terminal=true
Categories=Education;Application;
StartupNotify=true
EOF
    chmod +x "$FILE_KIOSK"
    if command -v gio >/dev/null 2>&1; then
        gio set "$FILE_KIOSK" metadata::trusted true 2>/dev/null || true
    fi

    # Bouton 3 : Arrêt rapide
    FILE_STOP="$DDIR/Arreter_Smart_ESITH.desktop"
    cat <<EOF > "$FILE_STOP"
[Desktop Entry]
Version=1.0
Type=Application
Name=Arrêter Smart ESITH
Comment=Arrêter le serveur Smart ESITH
Exec=$STOPPER
Icon=$ICON
Path=$SCRIPT_DIR
Terminal=true
Categories=Education;Application;
StartupNotify=false
EOF
    chmod +x "$FILE_STOP"
    if command -v gio >/dev/null 2>&1; then
        gio set "$FILE_STOP" metadata::trusted true 2>/dev/null || true
    fi

    echo "   ✅ Boutons installés dans : $DDIR"
done

# Optionnel : Démarrage automatique au boot du Raspberry Pi
AUTOSTART_DIR="$HOME/.config/autostart"
if [ "$1" = "--autostart" ] || [ "$1" = "-a" ]; then
    mkdir -p "$AUTOSTART_DIR"
    cp "$FILE_KIOSK" "$AUTOSTART_DIR/smart_esith_autostart.desktop"
    echo "   🚀 Démarrage automatique activé au boot dans $AUTOSTART_DIR"
elif [ "$1" = "--no-autostart" ]; then
    rm -f "$AUTOSTART_DIR/smart_esith_autostart.desktop"
    echo "   ℹ️ Démarrage automatique désactivé."
fi

echo ""
echo "=========================================================="
echo "🎉 INSTALLATION TERMINÉE AVEC SUCCÈS !"
echo "=========================================================="
echo "Vous avez maintenant sur votre bureau Raspberry Pi :"
echo ""
echo "  1. 📌 'Smart ESITH'            -> Lance le serveur + fenêtre navigateur"
echo "  2. 📺 'Smart ESITH (Kiosk TV)'  -> Lance en plein écran TV (idéal Hall)"
echo "  3. 🛑 'Arrêter Smart ESITH'    -> Coupe le serveur en un clic"
echo ""
echo "💡 Astuce Démarrage Automatique au Boot de la Raspberry Pi :"
echo "   Pour que l'affichage démarre tout seul quand la TV s'allume :"
echo "   ./installer_rpi.sh --autostart"
echo "=========================================================="

