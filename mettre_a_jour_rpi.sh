#!/usr/bin/env bash
# ==============================================================================
# SMART ESITH v2.0 - Mise à jour rapide pour Raspberry Pi 4
# Récupère les derniers changements depuis GitHub et redémarre Smart ESITH
# ==============================================================================

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$SCRIPT_DIR"

echo "=========================================================="
echo "    🍓 MISE À JOUR SMART ESITH v2.0 (Raspberry Pi 4)     "
echo "=========================================================="
echo "Dossier : $SCRIPT_DIR"
echo ""

# 1. Arrêt propre du serveur et du navigateur s'ils sont en cours
echo "🛑 [1/4] Arrêt des processus existants..."
if [ -f "$SCRIPT_DIR/arreter_smart_esith.sh" ]; then
    bash "$SCRIPT_DIR/arreter_smart_esith.sh" || true
else
    pkill -f "python.*app.py" 2>/dev/null || true
    pkill -f "chromium.*5001" 2>/dev/null || true
fi
sleep 1

# 2. Récupération des dernières modifications depuis GitHub
echo "📥 [2/4] Récupération des modifications depuis GitHub (git pull)..."
git fetch origin main
git reset --hard origin/main
echo "   ✅ Code synchronisé avec la branche main."

# 3. Permissions d'exécution
chmod +x *.sh 2>/dev/null || true

# 4. Mise à jour des dépendances Python dans l'environnement virtuel
echo "📦 [3/4] Vérification des dépendances Python..."
if [ -f "$SCRIPT_DIR/backend/venv/bin/pip" ]; then
    "$SCRIPT_DIR/backend/venv/bin/pip" install -r "$SCRIPT_DIR/backend/requirements.txt" --quiet
    echo "   ✅ Dépendances Python à jour."
elif [ -f "$SCRIPT_DIR/backend/requirements.txt" ]; then
    echo "   ℹ️ Le venv sera initialisé au prochain démarrage."
fi

echo ""
echo "=========================================================="
echo "   🎉 MISE À JOUR TERMINÉE AVEC SUCCÈS SUR LE RASPBERRY  "
echo "=========================================================="
echo ""

# 5. Relance automatique de l'affichage
if [ "$1" = "--no-start" ]; then
    echo "Smart ESITH mis à jour. Vous pouvez le démarrer quand vous voulez avec :"
    echo "  ./demarrer_smart_esith_kiosk.sh"
else
    echo "🚀 [4/4] Redémarrage en mode Kiosk TV (Hall)..."
    sleep 1
    exec "$SCRIPT_DIR/demarrer_smart_esith_kiosk.sh"
fi
