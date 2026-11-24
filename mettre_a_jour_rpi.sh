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
echo "🛑 [1/5] Arrêt forcé des processus existants..."
if command -v fuser >/dev/null 2>&1; then
    fuser -k -9 5001/tcp 2>/dev/null || true
fi
pkill -9 -f "python.*app\.py" 2>/dev/null || true
pkill -9 -f "chromium.*5001" 2>/dev/null || true
pkill -9 -f "chromium.*--kiosk" 2>/dev/null || true
sleep 1

# 2. Sauvegarde stricte de la base de données de production et des médias uploadés
echo "🛡️ [2/5] Protection et sauvegarde des données locales du Raspberry Pi..."
DB_FILE="$SCRIPT_DIR/backend/hall_esith_v3.db"
BACKUP_DIR="$SCRIPT_DIR/backend/backups"
PRESERVE_DB="/tmp/smart_esith_prod_db_preserve.db"
PRESERVE_UPLOADS="/tmp/smart_esith_prod_uploads_preserve"

mkdir -p "$BACKUP_DIR" 2>/dev/null || true
rm -f "$PRESERVE_DB" 2>/dev/null || true
rm -rf "$PRESERVE_UPLOADS" 2>/dev/null || true

# Sauvegarder la base existante de la Raspberry Pi
if [ -f "$DB_FILE" ] && [ -s "$DB_FILE" ]; then
    TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
    cp -p "$DB_FILE" "$BACKUP_DIR/rpi_prod_backup_${TIMESTAMP}.db" 2>/dev/null || true
    cp -p "$DB_FILE" "$PRESERVE_DB"
    echo "   ✅ Base locale sécurisée (Archive : rpi_prod_backup_${TIMESTAMP}.db)"
fi

# Sauvegarder les affiches/médias uploadés
if [ -d "$SCRIPT_DIR/backend/static/uploads" ]; then
    mkdir -p "$PRESERVE_UPLOADS"
    cp -rp "$SCRIPT_DIR/backend/static/uploads"/* "$PRESERVE_UPLOADS"/ 2>/dev/null || true
fi

# 3. Récupération des dernières modifications de code depuis GitHub
echo "📥 [3/5] Synchronisation du code depuis GitHub (git fetch & reset --hard)..."
git fetch origin main
git reset --hard origin/main
echo "   ✅ Code synchronisé à 100% avec origin/main."

# 4. Restauration garantie de la base de production et des données locales
echo "🛡️ [4/5] Restauration et sanctuarisation de la base de production..."
if [ -f "$PRESERVE_DB" ]; then
    cp -pf "$PRESERVE_DB" "$DB_FILE"
    rm -f "$PRESERVE_DB"
    echo "   ✅ Base de production du Raspberry Pi restaurée et préservée intacte."
elif [ ! -f "$DB_FILE" ] && [ -f "$SCRIPT_DIR/backend/hall_esith_v3.seed.db" ]; then
    echo "🌱 Initialisation d'une nouvelle base à partir du modèle seed..."
    cp -p "$SCRIPT_DIR/backend/hall_esith_v3.seed.db" "$DB_FILE"
fi

# Restaurer les affiches et médias uploadés
if [ -d "$PRESERVE_UPLOADS" ]; then
    mkdir -p "$SCRIPT_DIR/backend/static/uploads"
    cp -rpn "$PRESERVE_UPLOADS"/* "$SCRIPT_DIR/backend/static/uploads"/ 2>/dev/null || true
    rm -rf "$PRESERVE_UPLOADS"
fi

# Empêcher Git de toucher ou d'écraser la base locale lors de futurs pulls
git update-index --assume-unchanged backend/hall_esith_v3.db 2>/dev/null || true
git update-index --skip-worktree backend/hall_esith_v3.db 2>/dev/null || true

# Nettoyer les vieilles archives de sauvegarde (conserver les 25 plus récentes)
ls -1t "$BACKUP_DIR"/rpi_prod_backup_*.db 2>/dev/null | tail -n +26 | xargs -r rm -f 2>/dev/null || true

# Permissions d'exécution et création des dossiers uploads/backups
chmod +x *.sh 2>/dev/null || true
mkdir -p "$SCRIPT_DIR/backend/static/uploads/events" "$SCRIPT_DIR/backend/backups" 2>/dev/null || true
chmod -R 777 "$SCRIPT_DIR/backend/static/uploads" "$SCRIPT_DIR/backend/backups" 2>/dev/null || true

# Nettoyage du cache Chromium du profil Kiosk
rm -rf /tmp/smart_esith_kiosk_*/Default/Cache /tmp/smart_esith_kiosk_*/Default/"Code Cache" 2>/dev/null || true

# 5. Mise à jour des dépendances Python & PDF
echo "📦 [5/5] Vérification des dépendances Python & convertisseurs PDF..."
if command -v apt-get >/dev/null 2>&1; then
    sudo apt-get install -y --no-install-recommends python3-fitz poppler-utils 2>/dev/null || true
fi
if [ -f "$SCRIPT_DIR/backend/venv/bin/pip" ]; then
    "$SCRIPT_DIR/backend/venv/bin/pip" install -r "$SCRIPT_DIR/backend/requirements.txt" --quiet || "$SCRIPT_DIR/backend/venv/bin/pip" install Pillow openpyxl pymupdf pypdfium2 --quiet || true
    echo "   ✅ Dépendances Python et PDF à jour (Pillow, PyMuPDF, etc.)."
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
