# 🎓 Smart ESITH v2.0
### Système d'Affichage Dynamique Intelligent — ESITH Casablanca

Smart ESITH est un système d'information visuel en temps réel destiné à afficher le programme pédagogique, les retards, les absences, les changements de salle et les événements institutionnels sur un grand écran TV dans le hall de l'ESITH, accompagné d'un tableau de bord de gestion pour les équipes administratives et pédagogiques.

---

## ⚡ Démarrage Rapide

### 🪟 Sur Windows
Double-cliquez simplement sur le fichier :
```
DEMARRER_SMART_ESITH.bat
```
Le serveur s'initialise, configure l'environnement virtuel et ouvre automatiquement votre navigateur sur `http://localhost:5001`.

---

### 🍓 Sur Raspberry Pi 4 (Écran TV Hall)
Un ensemble de scripts a été spécialement conçu pour Raspberry Pi OS :

1. **Installation du bouton sur le Bureau (en 1 commande) :**
   ```bash
   bash installer_rpi.sh
   ```
   Cela crée les boutons avec l'icône ESITH directement sur votre Bureau.

2. **Démarrage au quotidien :**
   - Double-cliquez sur l'icône **"Smart ESITH"** sur votre bureau.
   - Ou pour l'écran TV en plein écran : double-cliquez sur **"Smart ESITH (Kiosk TV)"**.
   - Ou en ligne de commande : `./demarrer_smart_esith.sh`

👉 Consultez le guide complet : [GUIDE_RASPBERRY_PI.md](GUIDE_RASPBERRY_PI.md)

---

## 🌐 Adresses des Interfaces

- **Écran d'affichage Hall (TV)** : `http://localhost:5001/`
- **Dashboard de Gestion (Admin / Scolarité)** : `http://localhost:5001/dashboard`
- **Accès réseau local** : `http://<IP_DU_SERVEUR>:5001/dashboard`

---

## 🏗️ Structure du Projet

```
Smart Esith v2/
├── backend/                   # API REST Flask + Base de données SQLite
│   ├── app.py                 # Serveur principal (Waitress)
│   ├── database.py            # Modèles SQLAlchemy
│   ├── requirements.txt       # Dépendances Python
│   ├── static/                # Fichiers statiques et build React
│   └── templates/             # Template écran Hall
├── frontend-dashboard/        # Dashboard React 19 + Vite/CRA
├── DEMARRER_SMART_ESITH.bat   # Démarrage rapide Windows
├── demarrer_smart_esith.sh    # Démarrage rapide Raspberry Pi 4
├── installer_rpi.sh           # Installeur bouton Bureau Raspberry Pi 4
├── arreter_smart_esith.sh     # Arrêt propre Raspberry Pi 4
├── GUIDE_RASPBERRY_PI.md      # Guide complet d'utilisation Raspberry Pi 4
└── cahier_specifications...   # Spécifications détaillées du système
```

