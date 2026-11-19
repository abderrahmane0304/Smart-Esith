#!/usr/bin/env bash
# ==============================================================================
# SMART ESITH v2.0 - Mise à jour rapide pour Raspberry Pi 4
# Récupère les derniers changements depuis GitHub et redémarre Smart ESITH
# ==============================================================================

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$SCRIPT_DIR"

echo "=========================================================="
echo "    🍓 MISE À JOUR SMART ESITH v2.0 (Raspberry Pi 4)     "
echo "=========================================================="
echo "Dossier : $SCRIPT_DIR"
echo ""

# 1. Arrêt forcé de tous les processus Smart ESITH et du navigateur
echo "🛑 [1/4] Arrêt forcé des processus existants..."
if command -v fuser >/dev/null 2>&1; then
    fuser -k -9 5001/tcp 2>/dev/null || true
fi
pkill -9 -f "python.*app\.py" 2>/dev/null || true
pkill -9 -f "chromium.*5001" 2>/dev/null || true
pkill -9 -f "chromium.*--kiosk" 2>/dev/null || true
sleep 1

# 2. Récupération des dernières modifications depuis GitHub avec écrasement des conflits locaux
echo "📥 [2/4] Synchronisation avec GitHub (git fetch & reset --hard)..."
git fetch origin main
git reset --hard origin/main
echo "   ✅ Code synchronisé à 100% avec origin/main."

# 3. Permissions d'exécution
chmod +x *.sh 2>/dev/null || true

# 4. Nettoyage du cache Chromium du profil Kiosk
rm -rf /tmp/smart_esith_kiosk_*/Default/Cache /tmp/smart_esith_kiosk_*/Default/"Code Cache" 2>/dev/null || true

# 5. Mise à jour des dépendances Python
echo "📦 [3/4] Vérification des dépendances Python..."
if [ -f "$SCRIPT_DIR/backend/venv/bin/pip" ]; then
    "$SCRIPT_DIR/backend/venv/bin/pip" install -r "$SCRIPT_DIR/backend/requirements.txt" --quiet
    echo "   ✅ Dépendances Python à jour."
fi

echo ""
echo "=========================================================="
echo "   🎉 MISE À JOUR TERMINÉE AVEC SUCCÈS SUR LE RASPBERRY  "
echo "=========================================================="
echo ""

# 6. Relance automatique de l'affichage
if [ "$1" = "--no-start" ]; then
    echo "Smart ESITH mis à jour. Vous pouvez le démarrer quand vous voulez avec :"
    echo "  ./demarrer_smart_esith_kiosk.sh"
else
    echo "🚀 [4/4] Redémarrage en mode Kiosk TV (Hall)..."
    sleep 1
    exec "$SCRIPT_DIR/demarrer_smart_esith_kiosk.sh"
fi
