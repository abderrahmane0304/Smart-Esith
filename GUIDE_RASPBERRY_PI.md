# 🍓 Guide de Déploiement et Démarrage Rapide — Raspberry Pi 4
### Système d'Affichage Dynamique Smart ESITH v2.0

Ce guide explique comment installer et utiliser le **bouton de démarrage rapide** sur un **Raspberry Pi 4** (Raspberry Pi OS / Debian), équivalent au fichier `DEMARRER_SMART_ESITH.bat` sous Windows.

---

## 📋 1. Fichiers Disponibles pour Raspberry Pi

| Fichier | Rôle |
|---|---|
| `demarrer_smart_esith.sh` | **Script principal** de démarrage (équivalent de `.bat`) |
| `installer_rpi.sh` | **Installeur 1-clic** qui crée les boutons avec icône sur votre Bureau |
| `arreter_smart_esith.sh` | Script pour couper le serveur proprement en 1 clic |
| `Smart_ESITH.desktop` | Fichier raccourci bureau Linux |

---

## 🚀 2. Installation en 1 étape sur Raspberry Pi

Ouvrez un terminal sur votre Raspberry Pi dans le dossier du projet et lancez :

```bash
bash installer_rpi.sh
```

Cette commande va automatiquement :
1. Rendre exécutables tous les scripts (`chmod +x`).
2. Vérifier et installer les paquets système nécessaires (`python3-venv`, `python3-pip`).
3. Créer **3 boutons avec l'icône officielle ESITH** directement sur votre Bureau (`Desktop`) :
   - 📌 **Smart ESITH** : Démarre le serveur et ouvre le navigateur.
   - 📺 **Smart ESITH (Kiosk TV)** : Démarre en plein écran TV (sans barre d'URL ni bordures, idéal pour le Hall).
   - 🛑 **Arrêter Smart ESITH** : Coupe le serveur et ferme l'affichage.

---

## 🖱️ 3. Utilisation au Quotidien

### Option A : Depuis le Bureau (Interface Graphique)
- **Double-cliquez sur l'icône "Smart ESITH"** ou **"Smart ESITH (Kiosk TV)"** sur votre Bureau.
- Le terminal s'ouvre, active l'environnement Python, démarre le serveur et affiche l'écran Hall TV sur Chromium.

### Option B : Depuis le Terminal
```bash
# Lancement normal (fenêtre standard) :
./demarrer_smart_esith.sh

# Lancement en mode Kiosk plein écran (Écran TV Hall) :
./demarrer_smart_esith.sh --kiosk
```

### Pour Arrêter :
- Double-cliquez sur **"Arrêter Smart ESITH"** sur le Bureau, ou appuyez sur `Ctrl + C` dans la console.

---

## ⚡ 4. Démarrage Automatique au Démarrage de la Raspberry Pi (Autostart)

Si votre Raspberry Pi est branchée directement sur la TV du hall et que vous souhaitez qu'elle **lance automatiquement Smart ESITH dès qu'on l'allume** le matin :

```bash
./installer_rpi.sh --autostart
```

Pour désactiver l'autostart plus tard si besoin :
```bash
./installer_rpi.sh --no-autostart
```

---

## 🌐 5. Accès Réseau depuis les PC de l'Administration

Le serveur écoute sur toutes les interfaces (`0.0.0.0:5001`). Le script affiche automatiquement l'IP locale au démarrage :

- **Écran Hall TV (sur la Raspberry Pi)** : `http://localhost:5001/`
- **Dashboard de Gestion (depuis n'importe quel PC de la scolarité sur le réseau)** :
  `http://<IP_DU_RASPBERRY>:5001/dashboard`

*(Exemple : `http://192.168.1.50:5001/dashboard`)*

---

## 🛠️ Résolution des Problèmes Fréquents

1. **Permission Denied lors de l'exécution ?**
   Exécutez dans le terminal :
   ```bash
   chmod +x *.sh
   ```

2. **Avertissement de sécurité sur le fichier `.desktop` ?**
   Raspberry Pi OS peut demander confirmation au premier lancement. Cliquez sur **"Exécuter"** (ou le script `installer_rpi.sh` s'en charge avec `gio set`).

3. **Erreur d'environnement virtuel ?**
   Installez le support venv Debian :
   ```bash
   sudo apt update && sudo apt install -y python3-venv python3-pip
   ```

