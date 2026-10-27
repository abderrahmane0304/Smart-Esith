# 📋 CAHIER DE SPÉCIFICATIONS — SMART ESITH v2.0
### Système d'Affichage Dynamique Intelligent — ESITH (École Supérieure des Industries du Textile et de l'Habillement)

> **Version** : 2.0 — Reconstruction structurée  
> **Date** : Septembre 2026  
> **Équipe** : Département IMS — Informatique et Management des Systèmes  
> **Projet** : Tableau de bord de gestion + Écran d'affichage Hall

---

## TABLE DES MATIÈRES

1. [Présentation Générale](#1-présentation-générale)
2. [Charte Graphique](#2-charte-graphique)
3. [Architecture Technique](#3-architecture-technique)
4. [Structure de Dossiers Cible](#4-structure-de-dossiers-cible)
5. [Base de Données — Schéma Complet](#5-base-de-données--schéma-complet)
6. [API REST — Contrat Complet](#6-api-rest--contrat-complet)
7. [Module 1 — Écran Hall (Affichage Public)](#7-module-1--écran-hall-affichage-public)
8. [Module 2 — Dashboard de Gestion (Multi-Rôles)](#8-module-2--dashboard-de-gestion-multi-rôles)
9. [Règles Métier Critiques](#9-règles-métier-critiques)
10. [Format des Fichiers CSV / Excel Supportés](#10-format-des-fichiers-csv--excel-supportés)
11. [Authentification & Rôles](#11-authentification--rôles)
12. [Skills & Plugins Antigravity Recommandés](#12-skills--plugins-antigravity-recommandés)
13. [Exigences Non-Fonctionnelles](#13-exigences-non-fonctionnelles)
14. [Plan de Reconstruction — Étapes Ordonnées](#14-plan-de-reconstruction--étapes-ordonnées)

---

## 1. PRÉSENTATION GÉNÉRALE

### 1.1 Contexte

Smart ESITH est un **système d'information visuel** destiné à afficher en temps réel le programme pédagogique de l'ESITH sur un grand écran TV situé dans le hall de l'établissement. Il est complété par un **dashboard de gestion interne** accessible aux différents services de l'école.

### 1.2 Objectifs Principaux

| # | Objectif |
|---|----------|
| 1 | Afficher les cours **en cours** du jour par cycle sur l'écran du hall |
| 2 | Permettre aux services de **déclarer en temps réel** les retards, absences et changements de salle |
| 3 | Centraliser la gestion des **événements institutionnels** à diffuser |
| 4 | Importer les plannings pédagogiques depuis des **fichiers CSV/Excel** |
| 5 | Afficher l'**empreinte carbone** de l'établissement |
| 6 | Offrir un **splash screen** animé au démarrage du système |

### 1.3 Utilisateurs Cibles

| Rôle | Interface | Description |
|------|-----------|-------------|
| **Public / Étudiant** | Hall (TV) | Consultation passive, affichage auto-refresh |
| **Scolarité** | Dashboard | Déclare retards/absences, modifie les salles |
| **Direction des Études (DEE)** | Dashboard | Gère les événements, importe les plannings |
| **Direction des Relations Entreprises (DRE)** | Dashboard | Gère les visites entreprises |
| **Formation Continue (FC)** | Dashboard | Gère les formations continues |
| **Administrateur** | Dashboard | Accès complet à tous les onglets + statistiques |

---

## 2. CHARTE GRAPHIQUE

### 2.1 Palette de Couleurs Officielle

```css
:root {
  /* Couleurs Primaires ESITH */
  --esith-blue:             #176387;  /* Bleu marine institutionnel */
  --esith-blue-light:       #4f8fa8;  /* Bleu clair */
  --esith-blue-dark:        #0B4F6C;  /* Bleu foncé (titres) */
  --esith-blue-login:       #01527a;  /* Bleu page connexion */

  /* Couleurs Secondaires — Accent */
  --esith-pistachio:        #D4E24C;  /* Vert pistache (accent fort) */
  --esith-pistachio-light:  #eef4b5;  /* Vert pistache clair (fond) */
  --esith-pistachio-btn:    #c3d601;  /* Boutons principaux */
  --esith-pistachio-tab:    #cddd35;  /* Onglets actifs */

  /* Couleurs d'État (Alertes Hall) */
  --alert-red:    #f23636;  /* 🔴 Cours annulé / absence */
  --alert-orange: #f38a22;  /* 🟠 Cours retardé */
  --alert-yellow: #145a32;  /* 🟢 Salle modifiée (vert foncé) */
  --alert-vert-fonce: #145a32;  /* 🟢 Salle modifiée (vert foncé) */
  --alert-mauve:  #145a32;  /* 🟢 Salle modifiée (vert foncé) */
  --alert-green:  #198754;  /* ✅ Confirmation / succès */

  /* Fonds */
  --bg-main:     #f4f8f7;   /* Fond général Hall */
  --bg-card:     #ffffff;   /* Fond cartes */
  --bg-gradient: linear-gradient(135deg, #eef4b5 0%, #e3f2fd 100%);
}
```

### 2.2 Typographie

| Usage | Police | Taille | Poids |
|-------|--------|--------|-------|
| Corps de texte | Segoe UI, Tahoma, Geneva, Verdana, sans-serif | 14–16px | 400 |
| Titres Hall | Segoe UI | 1.5–2.2rem | 700–900 |
| Heure (Hall) | Segoe UI | 1.5rem | 700 |
| Badges / Labels | Segoe UI | 0.9–1.1rem | 600 |

### 2.3 Assets Graphiques

| Fichier | Emplacement | Usage |
|---------|-------------|-------|
| `esith-couleur-600x315-cropped-2.png` | `backend/static/` | Logo ESITH officiel (Hall, Dashboard, Favicon) |
| `fond_accueil.png` | `backend/static/` | Fond écran d'accueil |

> **⚠️ Important** : Tous les logos de l'application sont unifiés avec `esith-couleur-600x315-cropped-2.png`.

### 2.4 Style des Cartes de Cours (Hall)

```css
.course-card {
  background: var(--bg-card);
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  padding: 12px;
  border-left: 5px solid var(--esith-blue);  /* Couleur selon cycle */
}
/* Couleurs bordure gauche par cycle */
.card-licence    { border-left-color: #176387; }  /* Bleu */
.card-ingenieur  { border-left-color: #8e44ad; }  /* Violet */
.card-master     { border-left-color: #d4ac0d; }  /* Or */
.card-fc         { border-left-color: #198754; }  /* Vert */
.card-re         { border-left-color: #e74c3c; }  /* Rouge vif */
```

---

## 3. ARCHITECTURE TECHNIQUE

### 3.1 Stack Technologique

```
┌─────────────────────────────────────────────────────────┐
│                    CLIENT (Navigateur)                   │
│  ┌──────────────────┐    ┌──────────────────────────┐   │
│  │  Hall (TV Screen)│    │  Dashboard (Gestion)     │   │
│  │  Vanilla JS      │    │  React 19 + CRA          │   │
│  │  CSS pur         │    │  Inline styles / CSS     │   │
│  └────────┬─────────┘    └─────────────┬────────────┘   │
└───────────│──────────────────────────── │ ───────────────┘
            │  HTTP / REST                │ HTTP / REST
┌───────────▼─────────────────────────── ▼ ───────────────┐
│                   BACKEND (Python Flask)                  │
│  app.py — Serveur WSGI (Waitress)  Port 5001             │
│  ├── Routes API REST (/api/...)                          │
│  ├── Routes Template Flask (/, /dashboard)               │
│  ├── CORS activé                                         │
│  └── Pandas pour import CSV/Excel                        │
├──────────────────────────────────────────────────────────┤
│                BASE DE DONNÉES (SQLite)                   │
│  SQLAlchemy ORM — hall_esith_v3.db                       │
│  Tables : cours, events, formations, absences,           │
│           retards, changement_salle                       │
└──────────────────────────────────────────────────────────┘
```

### 3.2 Dépendances Python (backend/requirements.txt)

```txt
flask>=3.0
flask-cors>=4.0
sqlalchemy>=2.0
pandas>=2.0
openpyxl>=3.1          # Lecture Excel (.xlsx)
waitress>=3.0          # Serveur WSGI production Windows
python-dotenv>=1.0     # Variables d'environnement
```

### 3.3 Dépendances JavaScript (frontend-dashboard/package.json)

```json
{
  "dependencies": {
    "react": "^19.x",
    "react-dom": "^19.x",
    "react-scripts": "5.0.1"
  }
}
```

> **Note v2** : Envisager la migration vers **Vite + React** pour des builds plus rapides.

---

## 4. STRUCTURE DE DOSSIERS CIBLE

```
Smart_esith_v2/
├── DEMARRER_SMART_ESITH.bat         # Script de lancement Windows
├── README.md
├── .gitignore
│
├── backend/
│   ├── app.py                       # Application Flask principale
│   ├── database.py                  # Modèles SQLAlchemy + init_db()
│   ├── config.json                  # {"empreinte_carbone": 42}
│   ├── requirements.txt
│   ├── hall_esith_v3.db             # Base SQLite (auto-créée au 1er run)
│   │
│   ├── templates/
│   │   ├── hall.html                # Page Hall (Jinja2 minimal)
│   │   ├── dashboard.html           # Shell React Dashboard
│   │   └── admin-carbone.html       # Admin empreinte carbone
│   │
│   └── static/
│       ├── logo-esith.png           # Logo ESITH unifié
│       ├── fond_accueil.png         # Fond splash/accueil
│       ├── css/
│       │   └── nouveau_hall.css     # Styles complets du Hall
│       └── js/
│           ├── nouveau_hall.js      # Logique Hall (Vanilla JS)
│           └── dash_main.js         # Bundle React (généré par build)
│
├── frontend-dashboard/              # Sources React Dashboard
│   ├── package.json
│   ├── public/
│   │   └── logo-esith.png          # Logo pour React dev server
│   └── src/
│       ├── index.js
│       ├── App.js                   # Router principal + AuthContext
│       ├── theme.css                # Variables CSS globales
│       ├── api/
│       │   └── apiClient.js         # Base URL + helpers fetch
│       ├── context/
│       │   ├── AuthContext.js       # Authentification (rôles)
│       │   ├── EventContext.js      # Gestion événements
│       │   └── ActionContext.js     # Journal d'actions (logs)
│       ├── components/
│       │   ├── Layout.js            # Wrapper commun (nav + main)
│       │   ├── Menu.js              # Sidebar / menu navigation
│       │   ├── Login.js             # Page de connexion
│       │   ├── ProtectedRoute.js    # HOC protection de routes
│       │   ├── ImportCSV.js         # Composant upload fichier
│       │   ├── RetardAbsence.js     # Formulaire retard/absence
│       │   ├── ChangementSalleForm.js # Formulaire changement salle
│       │   ├── Evenement.js         # Formulaire ajout événement
│       │   ├── EventList.jsx        # Liste événements (CRUD)
│       │   ├── AdminActivityLog.jsx # Journal des actions admin
│       │   ├── AdminHistory.jsx     # Historique modifications
│       │   ├── AdminSection.jsx     # Section admin générique
│       │   └── AdminStats.jsx       # Statistiques dashboard
│       └── pages/
│           ├── DashboardAdmin.jsx   # Admin — onglets complets
│           ├── DashboardScolarite.js # Scolarité
│           ├── DashboardDEE.js      # Direction Études
│           ├── DashboardDRE.js      # Relations Entreprises
│           ├── DashboardFormationContinue.js # FC
│           └── ModificationsList.js # Liste des modifications
│
└── data_samples/                    # Fichiers CSV de test
    ├── planning1.csv                # Format ESITH (15 colonnes)
    └── Planning formation continu.csv
```

---

## 5. BASE DE DONNÉES — SCHÉMA COMPLET

### 5.1 Table `cours`

```sql
CREATE TABLE cours (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    numDay     TEXT,                  -- "lundi", "mardi", etc.
    date       TEXT NOT NULL,         -- Format JJ/MM/AAAA
    hd         TEXT,                  -- Heure début "08:30"
    hf         TEXT,                  -- Heure fin   "10:00"
    salle      TEXT,                  -- "Salle A5", "Salle D10"
    prof       TEXT,                  -- "BENHRA Jamal"
    groupe     TEXT,                  -- "LI3G1_A" ou "CP3G1 CP3G2"
    module     TEXT,                  -- Intitulé du module
    Cycle      TEXT,                  -- Voir valeurs autorisées ci-dessous
    AppelFait  TEXT DEFAULT 'Non'     -- "Oui" / "Non"
);
```

**Valeurs autorisées pour `Cycle`** :

| Valeur | Description |
|--------|-------------|
| `Licence` | Formation initiale Licence |
| `Ingénieur` | Formation initiale Ingénieur |
| `Master` | Formation initiale Master |
| `Formation Continue` | Formation continue (DEPRECATED → table `formations`) |
| `Relations Entreprises` | Visites d'entreprises |
| `Autre` | Indéterminé après import |

### 5.2 Table `formations` (Formation Continue)

```sql
CREATE TABLE formations (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    titre       TEXT NOT NULL,   -- "Entreprise X - Module Y"
    date        TEXT NOT NULL,   -- Format JJ/MM/AAAA
    heure_debut TEXT,            -- "09:00"
    heure_fin   TEXT,            -- "12:00"
    salle       TEXT,
    actif       BOOLEAN DEFAULT TRUE
);
```

### 5.3 Table `events`

```sql
CREATE TABLE events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    titre       TEXT NOT NULL,   -- Titre de l'événement
    date        TEXT NOT NULL,   -- Format JJ/MM/AAAA
    heure_debut TEXT,            -- Heure de début
    lieu        TEXT,            -- Lieu de l'événement
    actif       BOOLEAN DEFAULT TRUE
);
```

### 5.4 Table `absences`

```sql
CREATE TABLE absences (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    prof    TEXT,            -- Nom du professeur absent
    groupe  TEXT,            -- Groupe concerné
    date    TEXT NOT NULL,   -- Format JJ/MM/AAAA
    heure   TEXT,            -- Heure du cours absent
    motif   TEXT,            -- Motif de l'absence
    actif   BOOLEAN DEFAULT TRUE   -- Soft delete
);
```

### 5.5 Table `retards`

```sql
CREATE TABLE retards (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    prof          TEXT,
    groupe        TEXT,
    date          TEXT NOT NULL,
    heure_prevue  TEXT,        -- Heure prévue du cours
    heure_reelle  TEXT,        -- Heure réelle d'arrivée
    duree_retard  TEXT,        -- Ex : "15 min", "30 min"
    actif         BOOLEAN DEFAULT TRUE
);
```

### 5.6 Table `changement_salle`

```sql
CREATE TABLE changement_salle (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    groupe         TEXT,
    ancienne_salle TEXT,
    nouvelle_salle TEXT,
    date           TEXT NOT NULL,    -- Format JJ/MM/AAAA
    heure_creation TEXT,             -- Heure du changement "HH:MM"
    actif          BOOLEAN DEFAULT TRUE
);
```

---

## 6. API REST — CONTRAT COMPLET

**Base URL** : `http://localhost:5001`

### 6.1 Routes Hall (Affichage public)

| Méthode | Endpoint | Description | Paramètres |
|---------|----------|-------------|------------|
| GET | `/api/hall/all_data` | **Données temps réel pour l'écran Hall** | — |
| GET | `/api/stats` | Statistiques générales de la BDD | — |
| GET | `/api/config/carbone` | Valeur empreinte carbone | — |
| POST | `/api/config/carbone` | Mettre à jour empreinte carbone | `{"empreinte_carbone": 42}` |

**Réponse `/api/hall/all_data`** :
```json
{
  "licence":     [{ "h": "08:30-10:00", "groupe": "LI3G1", "module": "...", "salle": "A5", "prof": "..." }],
  "master":      [...],
  "ingenieur":   [...],
  "fc":          [...],
  "re":          [...],
  "absences":    [{ "groupe": "CP3G1", "prof": "...", "heure": "08:30" }],
  "retards":     [{ "groupe": "...", "prof": "...", "heure": "..." }],
  "changements_salle": [{ "groupe": "...", "ancienne_salle": "...", "nouvelle_salle": "...", "heure": "..." }],
  "events":      [{ "titre": "...", "date": "...", "lieu": "...", "heure_debut": "..." }],
  "empreinte_carbone": 42
}
```

### 6.2 Routes Import (Dashboard)

| Méthode | Endpoint | Description | Form Data |
|---------|----------|-------------|-----------|
| POST | `/api/dashboard/import-planning` | Importe planning Formation Initiale (CSV/XLSX) | `file` |
| POST | `/api/dashboard/import-append` | Importe FC ou RE | `file`, `type=[formation_continue\|visites]` |
| POST | `/api/dashboard/import-events` | Importe événements (CSV) | `file` |
| POST | `/api/dashboard/import-absences-retards` | Importe absences/retards (CSV) | `file` |
| GET | `/api/dashboard/groupes` | Liste groupes du jour | — |

### 6.3 Routes Événements (CRUD)

| Méthode | Endpoint | Description | Body |
|---------|----------|-------------|------|
| GET | `/api/events` | Liste tous les événements actifs | — |
| POST | `/api/events` | Crée un événement | `{"titre","date","heure_debut","lieu"}` |
| PUT | `/api/events/:id` | Modifie un événement | Champs à modifier |
| DELETE | `/api/events/:id` | Soft delete un événement | — |

### 6.4 Routes Absences (CRUD)

| Méthode | Endpoint | Description | Body |
|---------|----------|-------------|------|
| GET | `/api/absences` | Liste absences actives | — |
| POST | `/api/absences` | Crée une absence | `{"prof","groupe","date","heure","motif"}` |
| DELETE | `/api/absences/:id` | Soft delete | — |

### 6.5 Routes Retards (CRUD)

| Méthode | Endpoint | Description | Body |
|---------|----------|-------------|------|
| GET | `/api/retards` | Liste retards actifs | — |
| POST | `/api/retards` | Crée un retard | `{"prof","groupe","date","heure_prevue","heure_reelle","duree_retard"}` |
| DELETE | `/api/retards/:id` | Soft delete | — |

### 6.6 Routes Opérations Temps Réel

| Méthode | Endpoint | Description | Body |
|---------|----------|-------------|------|
| POST | `/api/changement-salle` | Change salle + crée alerte | `{"groupe","ancienneSalle","nouvelleSalle"}` |
| POST | `/api/declare-retard-absence` | Déclaration rapide | `{"type":"RETARD\|ABSENCE","groupe","heure","motif"}` |

---

## 7. MODULE 1 — ÉCRAN HALL (AFFICHAGE PUBLIC)

### 7.1 Description

L'écran Hall est une page HTML servie par Flask, affichée sur un **grand écran TV** (1920×1080 recommandé). Elle se rafraîchit automatiquement toutes les **60 secondes** via JavaScript Vanilla.

### 7.2 Composants Visuels

#### A. Splash Screen (démarrage)
- Durée : **5 secondes** au premier chargement
- Éléments :
  - Fond dégradé avec glows et rayons lumineux animés
  - Bandes décoratives en haut à gauche
  - Logo ESITH centré
  - Carte date + heure (haut droite)
  - Carte empreinte carbone avec barre de progression verte
  - Titre "SMART ESITH" + slogan
  - Mention "By IMS — Informatique et Management des Systèmes"

#### B. Header Principal
```
[LOGO ESITH]     [PROGRAMME DU JOUR]          [DATE + HEURE]
                 [Cycle Actif — ex: LICENCE]
                 [Légende: 🔴 Annulé 🟠 Retardé 🟡 Salle modif.]
```

#### C. Grille de Cours (contenu principal)

```
┌─────────────┬─────────────┬─────────────┐
│   Colonne 1 │   Colonne 2 │   Colonne 3 │
│  (Groupe A) │  (Groupe B) │  (Groupe C) │
│             │             │             │
│ [HEURE]     │ [HEURE]     │ [HEURE]     │
│ [Module]    │ [Module]    │ [Module]    │
│ [Prof]      │ [Prof]      │ [Prof]      │
│ [Salle]     │ [Salle]     │ [Salle]     │
└─────────────┴─────────────┴─────────────┘
```

- **3 colonnes** par page
- **Pagination automatique** si plus de 3 groupes (rotation toutes les X secondes)
- **Alertes visuelles** :
  - Carte rouge si absence déclarée pour ce groupe
  - Carte orange si retard déclaré
  - Salle barrée + nouvelle salle en jaune si changement

#### D. Barre d'Événements (bas de page)
- Bandeau défilant en bas : `ÉVÉNEMENT : [Titre] — [Date] — [Lieu]`
- Rotation automatique entre tous les événements actifs futurs

#### E. Rotation des Cycles
La page alterne automatiquement entre :
1. **Licence** (cours en cours)
2. **Ingénieur** (cours en cours)
3. **Master** (cours en cours)
4. **Formation Continue** (si présente)
5. **Relations Entreprises** (si présente)

Chaque cycle affiché 15-30 secondes avant rotation.

### 7.3 Règles de Filtrage Temporel

| Règle | Description |
|-------|-------------|
| **Cours en cours** | `hd <= heure_actuelle < hf` (ou `hd + 1h30` si hf manquante) |
| **Buffer** | Les cours finissant depuis ≤ 60 min restent visibles |
| **Bloc actif** | Grouper les cours d'un même horaire (fenêtre ±30 min) |
| **Événements** | Masquer si `date < aujourd'hui` |
| **Alertes** | Masquer absences/retards après **4 heures** |

### 7.4 Technologies

- **HTML** : Jinja2 (template Flask) — minimal, presque pas de markup dynamique
- **CSS** : `nouveau_hall.css` — CSS Vanilla, variables CSS, animations keyframe
- **JS** : `nouveau_hall.js` — Vanilla JS, fetch API, setInterval

---

## 8. MODULE 2 — DASHBOARD DE GESTION (MULTI-RÔLES)

### 8.1 Description

Application React (`frontend-dashboard/`) servie via le bundle compilé (`dash_main.js`) intégré dans `dashboard.html`. Accessible à `http://localhost:5001/dashboard`.

### 8.2 Authentification

**Mécanisme actuel** : Authentification locale via `localStorage` (sans backend JWT)

**Comptes prédéfinis** (AuthContext) :

| Username | Password | Rôle affiché |
|----------|----------|--------------|
| `scolarite` | `esith2024` | Scolarité |
| `dee` | `esith2024` | Direction Études |
| `dre` | `esith2024` | Relations Entreprises |
| `fc` | `esith2024` | Formation Continue |
| `admin` | `admin2024` | Administrateur |

> ⚠️ **Exigence v2** : Migrer vers JWT + endpoint `/api/auth/login` pour sécuriser.

### 8.3 Layout Dashboard

```
┌─────────────────────────────────────────────────────┐
│  [LOGO]   SMART ESITH Dashboard   [Utilisateur][⊗]  │
├────────────┬────────────────────────────────────────┤
│  SIDEBAR   │              CONTENU PRINCIPAL          │
│  ─────── │                                           │
│  📊 Accueil│  [Contenu de la page active]            │
│  📋 Planning│                                        │
│  📅 Événements│                                      │
│  🔔 Alertes │                                        │
│  ⚙️ Admin  │                                        │
└────────────┴────────────────────────────────────────┘
```

### 8.4 Pages & Fonctionnalités par Rôle

#### Page : Scolarité (`DashboardScolarite`)

| Fonctionnalité | Composant | API utilisée |
|----------------|-----------|--------------|
| Déclarer un retard enseignant | `RetardAbsence` | `POST /api/retards` |
| Déclarer une absence enseignant | `RetardAbsence` | `POST /api/absences` |
| Changer de salle pour un groupe | `ChangementSalleForm` | `POST /api/changement-salle` |

**Formulaire Retard/Absence** :
- Sélection du type : `RETARD` / `ABSENCE`
- Champ groupe (texte libre ou liste déroulante depuis `/api/dashboard/groupes`)
- Champ heure prévue
- Champ motif (optionnel)
- Bouton "Déclarer" → alerte immédiate sur l'écran Hall

**Formulaire Changement de Salle** :
- Champ groupe
- Ancienne salle
- Nouvelle salle
- Bouton "Appliquer" → mise à jour immédiate DB + alerte Hall

#### Page : Direction des Études (`DashboardDEE`)

| Fonctionnalité | Composant | API utilisée |
|----------------|-----------|--------------|
| Importer planning Formation Initiale (CSV/XLSX) | `ImportCSV` | `POST /api/dashboard/import-planning` |
| Ajouter un événement manuellement | `Evenement` | `POST /api/events` |
| Voir/Supprimer les événements | `EventList` | `GET/DELETE /api/events` |

**Composant ImportCSV** :
- Input `type="file"` — accepte `.csv`, `.xlsx`, `.xls`
- Bouton "Importer"
- Feedback : "X séances importées, Y lignes ignorées"

#### Page : Relations Entreprises (`DashboardDRE`)

| Fonctionnalité | Composant | API utilisée |
|----------------|-----------|--------------|
| Importer plannings visites entreprises | `ImportCSV` | `POST /api/dashboard/import-append?type=visites` |

#### Page : Formation Continue (`DashboardFormationContinue`)

| Fonctionnalité | Composant | API utilisée |
|----------------|-----------|--------------|
| Importer planning formation continue | `ImportCSV` | `POST /api/dashboard/import-append?type=formation_continue` |

#### Page : Admin (`DashboardAdmin`)

- **Onglets** : Scolarité / DEE / DRE / FC (accès à tous les dashboards)
- **Journal d'actions** : `AdminActivityLog` — historique des actions par rôle
- **Statistiques** : `AdminStats` — total cours par cycle, cours du jour, etc.

---

## 9. RÈGLES MÉTIER CRITIQUES

### 9.1 Détection Automatique du Cycle

L'algorithme `detect_cycle()` analyse chaque ligne CSV importée :

**Priorité 1 — Préfixes des codes modules** :

| Préfixe | Cycle |
|---------|-------|
| `GCLM`, `GPHM`, `DEHM`, `GASM`, `GPTM` | Licence |
| `MDMM`, `MPTHM`, `ELOGM`, `HSEM`, `HSE` | Master |
| `LILI`, `LITC`, `GI_`, `ITTI`, `IMSM`, `CTMM`, `THTH`, `THTC`, `CPCP`, `CPTC`, `IMS` | Ingénieur |
| `CPTCM33ANG` | Exception → Licence |

**Priorité 2 — Mots-clés dans la ligne** :
- `INGENIEUR`, ` 1A`, ` 2A`, ` 3A` → Ingénieur
- `MASTER`, `MASTERE`, `M1`, `M2` → Master
- `LICENCE`, `LIC`, `S1`–`S6` → Licence

### 9.2 Normalisation des Dates

Formats acceptés à l'import :
- `JJ/MM/AAAA` (principal)
- `AAAA-MM-JJ` (ISO)
- `JJ-MM-AAAA`
- `JJ/MM/AA` (2 chiffres année → préfixe 20XX)
- `mercredi 4 fé` (texte français partiel)

Sortie normalisée : **`JJ/MM/AAAA`** systématiquement.

### 9.3 Normalisation des Heures

Formats acceptés :
- `08:30` (standard)
- `08h30`, `8H30` → converti en `08:30`
- `08:45:00` → tronqué à `08:45`
- Durée en décimale `1.5` → calculé comme `hd + 1h30`

### 9.4 Mapping des Colonnes CSV (Format ESITH Standard)

Format 15 colonnes (planning Formation Initiale) :

| Index | Colonne | Description |
|-------|---------|-------------|
| 0 | `id_seance` | Identifiant séance |
| 1 | `dateSeance` | Date du cours |
| 2 | `numDay` | Jour de la semaine |
| 3 | `HD` | Heure début |
| 4 | `HF` | Heure fin (souvent `00:30` = non pertinent) |
| 5 | `DureeMin` | Durée en minutes |
| 6 | `DureeMinDecimal` | Durée décimale (ex: 1.5 = 1h30) |
| 7 | `Salle` | Salle |
| 8 | `Prof` | Enseignant |
| 9 | `Groupe` | Groupe(s) — peut contenir plusieurs groupes séparés par espace |
| 10 | `Module` | Intitulé du module |
| 11 | `CodeModule` | Code du module (utilisé pour détecter le cycle) |
| 12 | `TypeSeance` | Cours / TD / TP |
| 13 | `Cursus` | Filière complète |
| 14 | `AppelFait` | Oui / Non |

### 9.5 Règle Calcul Heure de Fin

Si `HF` est `00:30` ou invalide, calculer via :
```python
hf = hd + DureeMinDecimal * 60 minutes
```

### 9.6 Règle Soft Delete

Toutes les suppressions sont des **soft deletes** : le champ `actif` passe à `False`. Les données ne sont jamais physiquement supprimées.

### 9.7 Règle de Reset à l'Import

| Import | Comportement |
|--------|-------------|
| Planning Formation Initiale | **Vide** tous les cours Licence/Ingénieur/Master/Autre |
| Formation Continue | **Vide** toute la table `formations` |
| Relations Entreprises | **Vide** les cours Cycle=`Relations Entreprises` |
| Événements | **Vide** toute la table `events` |

---

## 10. FORMAT DES FICHIERS CSV / EXCEL SUPPORTÉS

### 10.1 Planning Formation Initiale

**Encodages supportés** : UTF-8, latin-1, cp1252  
**Séparateurs** : `;` ou `,` (détection automatique)  
**Headers** : Optionnels (détection dynamique si absents)

```csv
id_seance;dateSeance;numDay;HD;HF;DureeMin;DureeMinDecimal;Salle;Prof;Groupe;Module;CodeModule;TypeSeance;Cursus;AppelFait
5321616;22/09/2026;lundi;14:00;00:30;01:30;1,5;Salle A5;ZAHER Aziz;CP3G1 CP3G2;Anglais;CPTCM33ANG;Cours;S5-GICPS5;Non
```

### 10.2 Formation Continue

```csv
DATE;HD;HF;ENTREPRISE;THEME;SALLE
15/10/2026;09:00;12:00;Maroc Telecom;Gestion de projet Agile;Salle B3
```

Colonnes alternatives acceptées : `MASTÈRE`, `MASTERE`, `GROUPE`, `MODULE`, `OBJET`

### 10.3 Visites Entreprises (Relations Entreprises)

```csv
DATE;HD;HF;ENTREPRISE;VISITE;SALLE;PROF
20/10/2026;14:00;17:00;ITHEMIS;Visite usine;Hall;M. Dupont
```

### 10.4 Événements

```csv
TITRE;DATE;HEURE;LIEU
Journée Portes Ouvertes;15/11/2026;10:00;Hall principal
```

### 10.5 Absences/Retards

```csv
TYPE;PROF;GROUPE;DATE;HEURE;MOTIF
ABSENCE;M. Martin;LI3G1;15/10/2026;08:30;Maladie
RETARD;Mme. Dupont;CP3G2;15/10/2026;10:30;Transport
```

---

## 11. AUTHENTIFICATION & RÔLES

### 11.1 Système Actuel (v1)

```javascript
// AuthContext.js — comptes hardcodés
const USERS = {
  scolarite: { password: "scolarite2024", role: "Scolarite" },
  dee:       { password: "dee2024", role: "DEE" },
  dre:       { password: "dre2024", role: "DRE" },
  fc:        { password: "fc2024", role: "FC" },
  admin:     { password: "admin2024", role: "Admin" },
};
```

Stockage : `localStorage.setItem('smartesith_user', JSON.stringify({username, role}))`

### 11.2 Exigences v2 (Authentification JWT)

- Endpoint `POST /api/auth/login` → retourne `access_token` (JWT)
- Endpoint `GET /api/auth/me` → retourne le profil utilisateur
- Table `users` en base : `id, username, password_hash, role, actif`
- Middleware Flask : décorateur `@jwt_required` sur les routes protégées
- Dashboard React : intercepteur axios qui ajoute le header `Authorization: Bearer <token>`

### 11.3 Matrice d'Accès

| Fonctionnalité | Scolarité | DEE | DRE | FC | Admin |
|----------------|-----------|-----|-----|----|-------|
| Déclarer retard/absence | ✅ | ✅ | ❌ | ❌ | ✅ |
| Changer salle | ✅ | ✅ | ❌ | ❌ | ✅ |
| Importer planning FI | ❌ | ✅ | ❌ | ❌ | ✅ |
| Gérer événements | ❌ | ✅ | ✅ | ❌ | ✅ |
| Importer visites | ❌ | ❌ | ✅ | ❌ | ✅ |
| Importer FC | ❌ | ❌ | ❌ | ✅ | ✅ |
| Voir statistiques | ❌ | ❌ | ❌ | ❌ | ✅ |
| Journal d'actions | ❌ | ❌ | ❌ | ❌ | ✅ |

---

## 12. SKILLS & PLUGINS ANTIGRAVITY RECOMMANDÉS

### 12.1 Skills Antigravity Nécessaires
 
Pour reconstruire ce projet efficacement avec Antigravity IDE, les skills suivants sont recommandés :

| Skill | Usage dans le projet |
|-------|---------------------|
| **`python-flask-api`** | Créer les routes REST, middleware CORS, error handlers |
| **`sqlalchemy-orm`** | Définir les modèles, migrations, sessions |
| **`react-components`** | Créer composants Login, Forms, Tables avec les patterns React 19 |
| **`vanilla-js-spa`** | Logique Hall (nouveau_hall.js) — fetch, setInterval, DOM |
| **`css-design-system`** | Variables CSS, animations keyframe, responsive |
| **`csv-parser`** | Import intelligent avec pandas, gestion encodages |

### 12.2 Plugins MCP Recommandés

| Plugin MCP | Usage |
|------------|-------|
| **`sqlite`** | Inspecter, requêter et modifier `hall_esith_v3.db` directement |
| **`chrome-devtools-mcp`** | Tester le rendu Hall sur grand écran, capturer screenshots |
| **`playwright`** | Tests end-to-end : import CSV → vérification affichage Hall |
| **`sequential-thinking`** | Planifier les phases de reconstruction dans l'ordre |

### 12.3 Configuration `.agents/rules/` Recommandée

Créer les fichiers de règles suivants dans `.agents/rules/` :

**`python_style.md`** :
```markdown
# Règles Python — Smart ESITH
- Toujours utiliser des sessions SQLAlchemy dans un bloc try/finally/session.close()
- Normaliser les dates via la fonction normalize_date() avant tout stockage
- Utiliser le soft delete (actif=False) — ne jamais DELETE physiquement
- Toujours tester plusieurs encodages CSV : utf-8, latin-1, cp1252
```

**`react_style.md`** :
```markdown
# Règles React — Smart ESITH Dashboard
- Utiliser les couleurs de la charte ESITH : #176387, #D4E24C, #0B4F6C
- Chaque formulaire doit logguer son action dans ActionContext
- Les routes protégées utilisent le composant ProtectedRoute
- Éviter les styles inline > 3 propriétés — créer un objet `styles` dédié
```

**`charte_graphique.md`** :
```markdown
# Charte Graphique ESITH
- Bleu primaire : #176387
- Accent pistache : #D4E24C
- Boutons : background #c3d601, color #01527a
- Titres : color #0B4F6C
- Fond Hall : gradient linear-gradient(135deg, #eef4b5 0%, #e3f2fd 100%)
```

### 12.4 Skill Custom à Créer : `smart-esith-rebuild`

Créer `.agents/skills/smart-esith-rebuild/SKILL.md` :

```markdown
---
name: smart-esith-rebuild
description: Guide de reconstruction du projet Smart ESITH. Contient les patterns
             d'import CSV, la logique de filtrage temporal, et les conventions de nommage.
---

## Patterns Clés

### Import CSV
Toujours lire avec pandas sans headers (`header=None`), puis appliquer detect_cycle() sur chaque ligne.

### Affichage Hall
Le refresh se fait toutes les 60 secondes via setInterval. Appeler /api/hall/all_data.

### Rotation Cycles
Ordre : Licence → Ingénieur → Master → FC → RE → (retour Licence)
Délai : 20 secondes par cycle.
```

---

## 13. EXIGENCES NON-FONCTIONNELLES

### 13.1 Performance

| Critère | Cible |
|---------|-------|
| Temps de réponse API | < 500ms |
| Refresh Hall (JS) | 60 secondes |
| Rotation cycles | 20–30 secondes par cycle |
| Splash screen | 5 secondes, puis disparaît |
| Import CSV 1000 lignes | < 5 secondes |

### 13.2 Compatibilité

| Critère | Spécification |
|---------|---------------|
| OS serveur | Windows 10/11 (Waitress) |
| Navigateur Hall | Chrome (kiosk mode recommandé) |
| Résolution TV | 1920×1080 minimum |
| Navigateur Dashboard | Chrome, Firefox, Edge (dernières versions) |
| Python | ≥ 3.10 |
| Node.js | ≥ 18.x |

### 13.3 Disponibilité

- Le serveur tourne en **mode kiosk** : démarrage automatique via `DEMARRER_SMART_ESITH.bat`
- Pas de dépendance Internet requise (tout en local)
- La base SQLite est **auto-créée** au premier démarrage

### 13.4 Maintenabilité

- Code commenté en **français**
- Toutes les constantes de configuration dans `config.json`
- Séparation stricte : logique métier dans `app.py`, données dans `database.py`
- Composants React atomiques (un composant = une responsabilité)

### 13.5 Sécurité (Exigences Minimales)

| Exigence | Priorité |
|----------|----------|
| Authentification par mot de passe | ✅ Actuel |
| JWT Tokens pour les API | 🔴 Requis v2 |
| HTTPS (TLS) | ⚠️ Recommandé si réseau public |
| Validation des entrées (injections) | 🔴 À implémenter |
| Sauvegarde BDD quotidienne | ⚠️ Recommandé |

---

## 14. PLAN DE RECONSTRUCTION — ÉTAPES ORDONNÉES

### Phase 1 — Socle Backend (Jour 1)

```
1.1  Créer structure dossiers
1.2  Écrire database.py (modèles SQLAlchemy) — 6 tables
1.3  Écrire app.py — configuration Flask de base
1.4  Implémenter normalize_date() et normalize_time()
1.5  Implémenter detect_cycle()
1.6  Tester init_db() → création hall_esith_v3.db
```

### Phase 2 — API Import (Jour 1-2)

```
2.1  Route POST /api/dashboard/import-planning
2.2  Tester avec planning1.csv (15 colonnes)
2.3  Route POST /api/dashboard/import-append (FC + RE)
2.4  Route POST /api/dashboard/import-events
2.5  Route POST /api/dashboard/import-absences-retards
```

### Phase 3 — API Temps Réel (Jour 2)

```
3.1  Route GET /api/hall/all_data (logique filtre temporal)
3.2  Route POST /api/changement-salle
3.3  Route POST /api/declare-retard-absence
3.4  CRUD Events, Absences, Retards
3.5  Route GET /api/stats
3.6  Config carbone (GET/POST /api/config/carbone)
```

### Phase 4 — Écran Hall (Jour 2-3)

```
4.1  Créer nouveau_hall.css (variables CSS + layout 3 colonnes)
4.2  Créer hall.html (structure Jinja2)
4.3  Créer nouveau_hall.js :
     - Fonction fetchData() → /api/hall/all_data
     - Fonction renderCycle(data, cycleName)
     - Fonction rotateCycles() — setInterval
     - Splash screen (5s)
     - Horloge temps réel
     - Barre événements défilante
     - Logique alertes visuelles (rouge/orange/jaune)
     - Pagination (>3 groupes → pages)
4.4  Intégrer logo et fond dans /static/
```

### Phase 5 — Dashboard React (Jour 3-4)

```
5.1  npx create-react-app frontend-dashboard
5.2  Créer theme.css (variables charte ESITH)
5.3  Créer AuthContext.js (login/logout/rôles)
5.4  Créer EventContext.js et ActionContext.js
5.5  Créer composant Login.js (style charte)
5.6  Créer composant Layout.js + Menu.js
5.7  Créer composant ProtectedRoute.js
5.8  Créer DashboardScolarite.js + RetardAbsence.js + ChangementSalleForm.js
5.9  Créer DashboardDEE.js + Evenement.js + EventList.jsx + ImportCSV.js
5.10 Créer DashboardDRE.js et DashboardFormationContinue.js
5.11 Créer DashboardAdmin.jsx + AdminActivityLog.jsx + AdminStats.jsx
5.12 Configurer App.js (routing selon rôle)
```

### Phase 6 — Intégration & Build (Jour 4)

```
6.1  npm run build → génère build/
6.2  Copier build/static/js/main.*.js → backend/static/js/dash_main.js
6.3  Créer dashboard.html (shell React)
6.4  Créer admin-carbone.html
6.5  Configurer DEMARRER_SMART_ESITH.bat
6.6  Test complet E2E : import → affichage Hall → déclaration → refresh
```

### Phase 7 — Recette (Jour 5)

```
7.1  Test import planning1.csv → vérifier cycles détectés
7.2  Test affichage Hall TV (1920×1080)
7.3  Test déclaration retard → alerte orange Hall
7.4  Test déclaration absence → alerte rouge Hall
7.5  Test changement salle → alerte jaune Hall + salle barrée
7.6  Test ajout événement → barre défilante Hall
7.7  Test rotation cycles automatique
7.8  Test splash screen 5 secondes
7.9  Test import FC + RE
7.10 Vérifier charte couleurs (bleu + pistache) sur tous les écrans
```

---

## ANNEXE A — Variables CSS Complètes

```css
:root {
  /* Primaires */
  --esith-blue:              #176387;
  --esith-blue-light:        #4f8fa8;
  --esith-blue-dark:         #0B4F6C;
  --esith-blue-login:        #01527a;

  /* Accents */
  --esith-pistachio:         #D4E24C;
  --esith-pistachio-light:   #eef4b5;
  --esith-pistachio-btn:     #c3d601;
  --esith-pistachio-tab:     #cddd35;
  --esith-pistachio-admin:   #004974;

  /* États */
  --alert-red:               #f23636;
  --alert-orange:            #f38a22;
  --alert-yellow:            #145a32;  /* 🟢 Salle modifiée (vert foncé) */
  --alert-vert-fonce:        #145a32;  /* 🟢 Salle modifiée (vert foncé) */
  --alert-mauve:             #145a32;  /* 🟢 Salle modifiée (vert foncé) */
  --alert-green:             #198754;

  /* Fonds */
  --bg-main:                 #f4f8f7;
  --bg-card:                 #ffffff;
  --bg-dashboard:            #f4f7f9;
  --bg-gradient:             linear-gradient(135deg, #eef4b5 0%, #e3f2fd 100%);

  /* Ombres */
  --shadow-card:             0 2px 8px rgba(0,0,0,0.1);
  --shadow-modal:            0 10px 30px rgba(0,0,0,0.25);
}
```

---

## ANNEXE B — Commandes de Démarrage

```bat
REM DEMARRER_SMART_ESITH.bat
@echo off
echo Démarrage Smart ESITH...
cd backend
python -m venv venv 2>nul
call venv\Scripts\activate.bat
pip install -r requirements.txt -q
echo Serveur démarré sur http://localhost:5001
start http://localhost:5001
python app.py
```

---

## ANNEXE C — Structure du Fichier `config.json`

```json
{
  "empreinte_carbone": 42
}
```

> Cette valeur représente le pourcentage d'empreinte carbone affiché sur le splash screen. Modifiable via `/admin-carbone`.

---


