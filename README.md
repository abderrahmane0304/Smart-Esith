# Smart-Esith

Système intelligent d'affichage dynamique et de gestion de plannings en temps réel pour l'**ESITH** (École Supérieure des Industries du Textile et de l'Habillement).

---

## 📋 Présentation

Smart ESITH est composé de deux modules complémentaires :

1. **Affichage Dynamique du Hall (`/hall`)** :
   - Conçu pour les écrans géants et téléviseurs du hall principal.
   - Diffusion continue des séances du jour découpées par cycle (Ingénieur, Licence, Master, Formation Continue).
   - Bandeau d'alertes en temps réel : absences de professeurs, retards et réattributions de salles.
   - Encart météo de Casablanca, horloge/date temps réel, barre d'empreinte carbone et bannières d'événements.

2. **Dashboard d'Administration (`/dashboard`)** :
   - Interface web 100 % responsive (du smartphone à l'écran 4K et Ultra-wide 21:9).
   - Gestion fine des rôles (Admin, Scolarité, DEE, DRE, Formation Continue).
   - Importation et parsing de plannings CSV / Excel.
   - Déclaration instantanée des retards, absences et changements de salle avec auto-détection et sélection parmi 90 groupes.
   - Journal d'actions et statistiques globales.

---

## 🛠️ Stack Technique

- **Backend** : Python 3, Flask, SQLAlchemy, SQLite
- **Frontend Dashboard** : React 18, Vite, Bootstrap 5, CSS Grid adaptatif
- **Affichage Hall** : HTML5, CSS3 responsive, JavaScript Vanilla

---

## 🚀 Démarrage Rapide

### 1. Installation des dépendances Backend
```bash
cd backend
python -m venv venv
venv\Scripts\activate   # Sur Windows
pip install -r requirements.txt
```

### 2. Compilation du Frontend
```bash
cd frontend-dashboard
npm install
npm run build
```

### 3. Lancer l'application
Double-cliquez sur `DEMARRER_SMART_ESITH.bat` ou lancez :
```bash
cd backend
venv\Scripts\python.exe app.py
```
L'application sera accessible sur :
- **Affichage Hall** : `http://localhost:5001/hall`
- **Dashboard d'Administration** : `http://localhost:5001/dashboard`
