import os
import io
import json
import re
import unicodedata
import datetime
import pandas as pd
from functools import wraps
from flask import Flask, request, jsonify, render_template, send_from_directory, g, send_file, make_response
from flask_cors import CORS
import jwt
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename
from database import init_db, SessionLocal, Cours, Formation, Event, Absence, Retard, ChangementSalle, User, ActionLog, PlanningImport, FileBackup, DB_PATH
from clean_encoding import sanitize_string

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, 'static')
DASHBOARD_DIR = os.path.join(STATIC_DIR, 'dashboard')
BACKUP_DIR = os.path.join(BASE_DIR, 'backups')
os.makedirs(BACKUP_DIR, exist_ok=True)
BACKUP_RETENTION_DAYS = 90  # Rétention de 3 mois (écrasement automatique après 90 jours)

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)

# OWASP A02: Cryptographic Failures — Clé secrète persistante et cryptographiquement robuste (256-bit)
SECRET_FILE = os.path.join(BASE_DIR, '.secret_key')
if os.environ.get('SMART_ESITH_SECRET'):
    SECRET_KEY = os.environ['SMART_ESITH_SECRET']
elif os.path.exists(SECRET_FILE):
    try:
        with open(SECRET_FILE, 'r', encoding='utf-8') as f:
            SECRET_KEY = f.read().strip()
    except Exception:
        import secrets
        SECRET_KEY = secrets.token_hex(32)
else:
    import secrets
    SECRET_KEY = secrets.token_hex(32)
    try:
        with open(SECRET_FILE, 'w', encoding='utf-8') as f:
            f.write(SECRET_KEY)
    except Exception:
        pass

app.config['SECRET_KEY'] = SECRET_KEY
app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024  # 20 Mo max par import (OWASP A04)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0  # Désactive le cache statique Flask pour affichage TV toujours frais

# OWASP A07 & A04: Protection anti brute-force sur l'authentification
LOGIN_ATTEMPTS = {}  # ip -> list of timestamps
MAX_LOGIN_ATTEMPTS = 5
LOGIN_LOCKOUT_WINDOW = 300  # 5 minutes de verrouillage

@app.after_request
def add_security_headers(response):
    """OWASP A05: Security Misconfiguration — En-têtes HTTP défensifs indispensables."""
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Permissions-Policy'] = 'geolocation=(), camera=(), microphone=(), payment=()'
    return response

@app.errorhandler(413)
def entity_too_large(e):
    return jsonify({"error": "Fichier trop volumineux. La taille maximale autorisée est de 20 Mo."}), 413

@app.errorhandler(429)
def ratelimit_exceeded(e):
    return jsonify({"error": "Trop de tentatives. Veuillez patienter avant de réessayer."}), 429

FI_CYCLES = ['Licence', 'Ingénieur', 'Master', 'Autre']
CYCLE_RE = 'Relations Entreprises'


# =====================================================================
# Session BDD
# =====================================================================
def get_db():
    if 'db' not in g:
        g.db = SessionLocal()
    return g.db


@app.teardown_appcontext
def teardown_db(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()


# =====================================================================
# Configuration (config.json)
# =====================================================================
CONFIG_PATH = os.path.join(BASE_DIR, 'config.json')


def load_config():
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"empreinte_carbone": 0}


def save_config(config):
    current = load_config()
    current.update(config)
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(current, f)


# =====================================================================
# Helpers de normalisation
# =====================================================================
def clean(value):
    """Convertit une cellule en texte propre ('' si vide / NaN / None)."""
    if value is None:
        return ''
    try:
        if pd.isna(value):
            return ''
    except (TypeError, ValueError):
        pass
    s = str(value).strip()
    if s.lower() in ('nan', 'none', 'nat', 'null'):
        return ''
    # Les entiers lus comme float par pandas (ex: 12.0) -> "12"
    if re.fullmatch(r'\d+\.0', s):
        s = s[:-2]
    return sanitize_string(s)


def strip_accents(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')


MOIS_FR = {
    'janvier': 1, 'janv': 1, 'jan': 1,
    'fevrier': 2, 'fevr': 2, 'fev': 2, 'fe': 2,
    'mars': 3, 'mar': 3,
    'avril': 4, 'avr': 4,
    'mai': 5,
    'juin': 6,
    'juillet': 7, 'juil': 7,
    'aout': 8,
    'septembre': 9, 'sept': 9, 'sep': 9,
    'octobre': 10, 'oct': 10,
    'novembre': 11, 'nov': 11,
    'decembre': 12, 'dec': 12,
}


def normalize_date(date_val):
    """Retourne une date au format JJ/MM/AAAA (ou la valeur d'origine si non reconnue)."""
    if date_val is None:
        return None
    if isinstance(date_val, (pd.Timestamp, datetime.datetime, datetime.date)):
        try:
            return date_val.strftime('%d/%m/%Y')
        except ValueError:
            return None
    date_str = clean(date_val)
    if not date_str:
        return None
    try:
        # YYYY-MM-DD (éventuellement suivi d'une heure)
        m = re.match(r'^(\d{4})[-/](\d{1,2})[-/](\d{1,2})(?:[ T].*)?$', date_str)
        if m:
            y, mo, d = map(int, m.groups())
            return datetime.date(y, mo, d).strftime('%d/%m/%Y')
        # DD/MM/YYYY, DD-MM-YYYY, DD.MM.YYYY (éventuellement suivi d'une heure)
        m = re.match(r'^(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})(?:\s.*)?$', date_str)
        if m:
            d, mo, y = map(int, m.groups())
            return datetime.date(y, mo, d).strftime('%d/%m/%Y')
        # DD/MM/YY
        m = re.match(r'^(\d{1,2})[/.-](\d{1,2})[/.-](\d{2})$', date_str)
        if m:
            d, mo, y = map(int, m.groups())
            return datetime.date(2000 + y, mo, d).strftime('%d/%m/%Y')
        # Texte français : "jeudi 4 juin 2026", "4 juin 2026", "mercredi 4 fé"
        txt = strip_accents(date_str.lower()).replace(',', ' ').replace('.', ' ')
        m = re.search(r'(\d{1,2})(?:er)?\s+([a-z]+)\s*(\d{4})?', txt)
        if m:
            d = int(m.group(1))
            mois_txt = m.group(2)
            mo = MOIS_FR.get(mois_txt)
            if mo is None:
                for k, v in MOIS_FR.items():
                    if len(mois_txt) >= 2 and k.startswith(mois_txt):
                        mo = v
                        break
            if mo:
                y = int(m.group(3)) if m.group(3) else datetime.date.today().year
                return datetime.date(y, mo, d).strftime('%d/%m/%Y')
    except ValueError:
        pass
    return date_str


def parse_date(date_str):
    """JJ/MM/AAAA -> datetime.date (None si invalide)."""
    try:
        return datetime.datetime.strptime(date_str, '%d/%m/%Y').date()
    except (TypeError, ValueError):
        return None


def normalize_time(value):
    """Retourne une heure HH:MM ('' si invalide). Accepte 08:30, 8h30, 08:45:00, 0.354 (Excel)."""
    if value is None:
        return ''
    if isinstance(value, (datetime.time, datetime.datetime, pd.Timestamp)):
        return value.strftime('%H:%M')
    s = clean(value)
    if not s:
        return ''
    m = re.match(r'^(\d{1,2})\s*[:hH]\s*(\d{2})?', s)
    if m:
        h = int(m.group(1))
        mi = int(m.group(2) or 0)
        if 0 <= h < 24 and 0 <= mi < 60:
            return f'{h:02d}:{mi:02d}'
    # Fraction de journée Excel (ex: 0.354166 = 08:30)
    try:
        f = float(s.replace(',', '.'))
        if 0 <= f < 1:
            total = round(f * 24 * 60)
            return f'{total // 60:02d}:{total % 60:02d}'
    except ValueError:
        pass
    return ''


def today_str():
    return datetime.datetime.now().strftime('%d/%m/%Y')


JOURS_FR = {
    0: 'Lundi', 1: 'Mardi', 2: 'Mercredi', 3: 'Jeudi',
    4: 'Vendredi', 5: 'Samedi', 6: 'Dimanche'
}


def extract_filieres_from_group(groupe_str):
    """Extrait les filières académiques à partir d'un groupe ou d'une liste de groupes.
    Ex: 'BDM2G1 BDM2G2' -> {'BDM'}, 'INGTCG1.1' -> {'INGTCG'}, 'D&M1G1' -> {'D&M'}.
    """
    if not groupe_str:
        return set()
    fils = set()
    for token in re.split(r'[\s,;/]+', clean(groupe_str)):
        if not token:
            continue
        m = re.match(r'^([A-Za-z&]+)', token.strip())
        if m:
            fil = m.group(1).upper()
            if len(fil) >= 2:
                fils.add(fil)
    return fils


def parse_time_minutes(time_str):
    """Convertit '14:00', '14h00', '14h', '14:30' en minutes depuis minuit."""
    if not time_str:
        return None
    s = str(time_str).strip()
    m = re.search(r'(\d{1,2})[hH:](\d{2})?', s)
    if not m:
        return None
    hh = int(m.group(1))
    mm = int(m.group(2)) if m.group(2) else 0
    return hh * 60 + mm


def parse_time_range(range_str):
    """Extrait l'intervalle de début et fin en minutes pour un horaire alerté.
    Supporte '14:00-15:30', '14:00 - 15:30', '14h - 15h30', '14:00', 'Toute la journée'.
    """
    if not range_str:
        return None, None
    s = str(range_str).strip().lower()
    if any(k in s for k in ('toute', 'journee', 'journée', 'jour', 'all')):
        return 'all', 'all'

    parts = re.split(r'[-–—àa/]', s)
    if len(parts) >= 2:
        t1 = parse_time_minutes(parts[0])
        t2 = parse_time_minutes(parts[1])
        if t1 is not None and t2 is not None:
            return min(t1, t2), max(t1, t2)
        elif t1 is not None:
            return t1, t1 + 90

    t = parse_time_minutes(s)
    if t is not None:
        return t, None
    return None, None


def match_alert_to_session(alert_record, course, is_retard=False):
    """Détermine avec précision si une alerte d'absence ou de retard correspond
    à une séance de cours spécifique (vérification date, professeur, groupe ET horaire).
    Évite qu'une alerte sur une seule séance ne contamine toutes les autres séances de la journée.
    """
    if not alert_record or not course:
        return False

    # 1. Correspondance de date
    a_date = normalize_date(getattr(alert_record, 'date', None))
    c_date = normalize_date(getattr(course, 'date', None))
    if a_date and c_date and a_date != c_date:
        return False

    # 2. Correspondance de professeur (si spécifié dans l'alerte)
    a_prof = clean(getattr(alert_record, 'prof', None)).lower()
    c_prof = clean(getattr(course, 'prof', None)).lower()
    if a_prof and c_prof:
        if a_prof != c_prof and (a_prof not in c_prof) and (c_prof not in a_prof):
            return False

    # 3. Correspondance de groupe (si spécifié dans l'alerte)
    a_grp = clean(getattr(alert_record, 'groupe', None)).upper()
    c_grp = clean(getattr(course, 'groupe', None)).upper()
    if a_grp and a_grp not in ('TOUS', 'ALL'):
        if not c_grp:
            return False
        c_tokens = set(re.findall(r'[A-Za-z0-9_.-]+', c_grp))
        a_tokens = set(re.findall(r'[A-Za-z0-9_.-]+', a_grp))
        # Vérifie si le groupe de l'alerte correspond au cours (exact ou sous-groupe)
        grp_matched = bool(a_tokens & c_tokens) or (a_grp in c_grp) or (c_grp in a_grp)
        if not grp_matched:
            return False

    # 4. Correspondance d'horaire / séance
    alert_heure = clean(getattr(alert_record, 'heure_prevue' if is_retard else 'heure', None))
    if not alert_heure:
        # Si aucune heure n'a été spécifiée dans l'alerte, elle couvre la journée pour ce groupe
        return True

    a_start, a_end = parse_time_range(alert_heure)
    if a_start == 'all':
        return True

    c_start = parse_time_minutes(course.hd)
    c_end = parse_time_minutes(course.hf)
    if c_start is None:
        return True  # Pas d'heure sur le cours, match par groupe/date

    if c_end is None:
        c_end = c_start + 90

    if a_start is not None and c_start is not None:
        if a_end is not None:
            # Intervalle complet (ex: 14:00-15:30) : chevauchement strict
            return (c_start < a_end) and (c_end > a_start)
        else:
            # Heure ponctuelle (ex: 14:00) : comprise dans la séance ou début proche
            return (c_start <= a_start < c_end) or abs(c_start - a_start) <= 20

    return True


def classify_filieres_by_cycle(filieres, db=None):
    """Classe les filières académiques par cycle (Licence, Ingénieur, Master)."""
    by_cycle = {
        "Licence": [],
        "Ingénieur": [],
        "Master": []
    }
    filiere_cycle_map = {}
    if db is not None:
        try:
            for (cyc, grp) in db.query(Cours.Cycle, Cours.groupe).filter(
                Cours.Cycle.in_(['Licence', 'Ingénieur', 'Master'])
            ).all():
                if cyc and grp:
                    for fil in extract_filieres_from_group(grp):
                        if fil not in filiere_cycle_map:
                            filiere_cycle_map[fil] = cyc
        except Exception:
            pass

    for f in sorted(list(set(filieres))):
        if not f:
            continue
        f_up = f.upper()
        cyc = filiere_cycle_map.get(f_up)
        if not cyc or cyc not in by_cycle:
            cyc = detect_cycle('', f_up)
        if cyc not in by_cycle:
            if any(f_up.startswith(p) for p in ['GCL', 'GPH', 'DEH', 'GAS', 'GPT', 'LIC']):
                cyc = 'Licence'
            elif any(f_up.startswith(p) for p in ['MDM', 'MPTH', 'ELOG', 'HSE', 'MAS']):
                cyc = 'Master'
            else:
                cyc = 'Ingénieur'
        by_cycle[cyc].append(f_up)

    for k in by_cycle:
        by_cycle[k] = sorted(list(set(by_cycle[k])))
    return by_cycle


def get_active_planning_import(db, ref_date=None):
    """Retourne les métadonnées et données actives de l'import de planning Formation Initiale.
    Règle Empty State : Si aucun planning n'a été importé pour la période courante
    (semaine ou mois couvrant ref_date), retourne active=False avec listes vides.
    """
    if ref_date is None:
        ref_date = datetime.date.today()
    elif isinstance(ref_date, str):
        ref_date = parse_date(ref_date) or datetime.date.today()

    # Semaine courante (Lundi -> Dimanche)
    ref_monday = ref_date - datetime.timedelta(days=ref_date.weekday())
    ref_sunday = ref_monday + datetime.timedelta(days=6)

    # Récupère le dernier import actif
    imports = db.query(PlanningImport).filter_by(active=True).order_by(PlanningImport.id.desc()).all()
    for imp in imports:
        d_start = parse_date(imp.period_start)
        d_end = parse_date(imp.period_end)
        if not d_start or not d_end:
            continue

        # Vérification si ref_date est couvert par l'import
        is_covered = False
        if imp.period_type == 'month':
            # Même mois/année ou entre début et fin
            if (d_start.year == ref_date.year and d_start.month == ref_date.month) or (d_start <= ref_date <= d_end):
                is_covered = True
        else:
            # Semaine : chevauchement avec la semaine de ref_date
            if (d_start <= ref_sunday and d_end >= ref_monday) or (d_start <= ref_date <= d_end):
                is_covered = True

        if is_covered:
            try:
                profs = json.loads(imp.professors or '[]')
            except Exception:
                profs = []
            try:
                fils = json.loads(imp.filieres or '[]')
            except Exception:
                fils = []
            return {
                "active": True,
                "import_id": imp.id,
                "filename": imp.filename,
                "import_date": imp.import_date,
                "period_start": imp.period_start,
                "period_end": imp.period_end,
                "period_type": imp.period_type,
                "professors": sorted([p for p in profs if p and p.strip()]),
                "filieres": sorted([f for f in fils if f and f.strip()]),
                "filieres_by_cycle": classify_filieres_by_cycle(fils, db),
                "count_professors": len(profs),
                "count_filieres": len(fils)
            }

    # Empty state rule
    return {
        "active": False,
        "import_id": None,
        "filename": None,
        "import_date": None,
        "period_start": None,
        "period_end": None,
        "period_type": None,
        "professors": [],
        "filieres": [],
        "filieres_by_cycle": {"Licence": [], "Ingénieur": [], "Master": []},
        "count_professors": 0,
        "count_filieres": 0
    }


def save_file_backup(file_or_bytes, original_filename, category, db=None):
    """Enregistre une copie de sauvegarde d'un fichier importé dans BACKUP_DIR.
    Définit une durée de rétention de 3 mois (90 jours).
    """
    if not file_or_bytes or not original_filename:
        return None

    # Extraction du contenu binaire
    if isinstance(file_or_bytes, bytes):
        raw = file_or_bytes
    elif hasattr(file_or_bytes, 'read'):
        pos = file_or_bytes.tell() if hasattr(file_or_bytes, 'tell') else 0
        raw = file_or_bytes.read()
        if hasattr(file_or_bytes, 'seek'):
            file_or_bytes.seek(pos)
    else:
        return None

    if not raw:
        return None

    safe_orig = secure_filename(os.path.basename(original_filename)) or "backup_file"
    safe_clean = re.sub(r'[^a-zA-Z0-9_.-]', '_', safe_orig)
    now = datetime.datetime.now()
    ts = now.strftime('%Y%m%d_%H%M%S')
    stored_filename = f"{category}_{ts}_{safe_clean}"
    target_path = os.path.abspath(os.path.join(BACKUP_DIR, stored_filename))
    if not target_path.startswith(os.path.abspath(BACKUP_DIR)):
        return None

    try:
        with open(target_path, 'wb') as f:
            f.write(raw)
    except Exception as e:
        print(f"[Smart ESITH] Erreur sauvegarde fichier {stored_filename} :", e)
        return None

    file_size = len(raw)
    created_str = now.strftime('%Y-%m-%d %H:%M:%S')
    expire_str = (now + datetime.timedelta(days=BACKUP_RETENTION_DAYS)).strftime('%Y-%m-%d %H:%M:%S')

    own_session = db is None
    if own_session:
        db = SessionLocal()

    backup_record = None
    try:
        backup_record = FileBackup(
            filename=stored_filename,
            original_name=safe_orig,
            category=category,
            file_path=stored_filename,
            file_size=file_size,
            created_at=created_str,
            expire_at=expire_str
        )
        db.add(backup_record)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"[Smart ESITH] Erreur indexation backup {stored_filename} :", e)
    finally:
        if own_session:
            db.close()

    return backup_record


def create_database_backup(db=None):
    """Crée un instantané de sauvegarde de la base de données SQLite hall_esith_v3.db.
    Rétention de 3 mois (90 jours).
    """
    import shutil
    if not os.path.exists(DB_PATH):
        return None

    now = datetime.datetime.now()
    ts = now.strftime('%Y%m%d_%H%M%S')
    stored_filename = f"database_{ts}_hall_esith_v3.db"
    target_path = os.path.join(BACKUP_DIR, stored_filename)

    try:
        shutil.copy2(DB_PATH, target_path)
        file_size = os.path.getsize(target_path)
    except Exception as e:
        print("[Smart ESITH] Erreur copie sauvegarde BDD :", e)
        return None

    created_str = now.strftime('%Y-%m-%d %H:%M:%S')
    expire_str = (now + datetime.timedelta(days=BACKUP_RETENTION_DAYS)).strftime('%Y-%m-%d %H:%M:%S')

    own_session = db is None
    if own_session:
        db = SessionLocal()

    backup_rec = None
    try:
        backup_rec = FileBackup(
            filename=stored_filename,
            original_name="hall_esith_v3.db",
            category="database",
            file_path=stored_filename,
            file_size=file_size,
            created_at=created_str,
            expire_at=expire_str
        )
        db.add(backup_rec)
        db.commit()
    except Exception as e:
        db.rollback()
        print("[Smart ESITH] Erreur enregistrement backup BDD :", e)
    finally:
        if own_session:
            db.close()

    return backup_rec


def cleanup_expired_backups(db=None):
    """Écrase et supprime définitivement tous les fichiers de sauvegarde ayant dépassé 3 mois (90 jours) :
    - Fichiers référencés dans la table file_backups dont expire_at est dépassé
    - Fichiers physiques orphelins dans BACKUP_DIR datant de plus de 90 jours
    - Affiches d'événements dans static/uploads/events datant de plus de 90 jours
    """
    own_session = db is None
    if own_session:
        db = SessionLocal()

    now = datetime.datetime.now()
    now_str = now.strftime('%Y-%m-%d %H:%M:%S')
    cutoff_ts = (now - datetime.timedelta(days=BACKUP_RETENTION_DAYS)).timestamp()
    deleted_files = 0

    try:
        # 1. Nettoyage via la table FileBackup
        expired_records = db.query(FileBackup).filter(FileBackup.expire_at <= now_str).all()
        for rec in expired_records:
            full_path = os.path.join(BACKUP_DIR, rec.filename)
            if os.path.exists(full_path):
                try:
                    os.remove(full_path)
                except Exception:
                    pass
            db.delete(rec)
            deleted_files += 1

        db.commit()

        # 2. Nettoyage des fichiers physiques dans BACKUP_DIR (> 90 jours)
        if os.path.exists(BACKUP_DIR):
            for fname in os.listdir(BACKUP_DIR):
                fpath = os.path.join(BACKUP_DIR, fname)
                if os.path.isfile(fpath):
                    try:
                        if os.path.getmtime(fpath) < cutoff_ts:
                            os.remove(fpath)
                            deleted_files += 1
                    except Exception:
                        pass

        # 3. Nettoyage des médias d'événements dans static/uploads/events (> 90 jours)
        upload_events_dir = os.path.join(STATIC_DIR, 'uploads', 'events')
        if os.path.exists(upload_events_dir):
            for fname in os.listdir(upload_events_dir):
                fpath = os.path.join(upload_events_dir, fname)
                if os.path.isfile(fpath):
                    try:
                        if os.path.getmtime(fpath) < cutoff_ts:
                            os.remove(fpath)
                            deleted_files += 1
                    except Exception:
                        pass

        if deleted_files > 0:
            print(f"[Smart ESITH] Purge 3 mois : {deleted_files} fichier(s) de sauvegarde expiré(s) écrasé(s)/supprimé(s).")
    except Exception as e:
        db.rollback()
        print("[Smart ESITH] Erreur lors de la purge des sauvegardes de 3 mois :", e)
    finally:
        if own_session:
            db.close()

    return deleted_files


def cleanup_expired_records(db=None):
    """Supprime les enregistrements expirés :
    - Fichiers de sauvegarde et imports de plus de 3 mois (90 jours)
    - Événements passés depuis plus de 2 semaines (14 jours)
    - Absences, retards et changements de salle antérieurs à aujourd'hui
    """
    own_session = db is None
    if own_session:
        db = SessionLocal()

    today = datetime.date.today()
    events_cutoff = today - datetime.timedelta(days=14)
    deleted_events = 0
    deleted_alerts = 0

    try:
        # Purge automatique des fichiers de backup de plus de 3 mois (90 jours)
        cleanup_expired_backups(db)

        for e in db.query(Event).all():
            # Expiration : date_fin si spécifiée, sinon e.date
            end_date_str = getattr(e, 'date_fin', None) or e.date
            d = parse_date(end_date_str)
            if d is not None and d < events_cutoff:
                db.delete(e)
                deleted_events += 1

        for model in (Absence, Retard, ChangementSalle):
            for rec in db.query(model).all():
                end_str = getattr(rec, 'date_fin', None) or rec.date
                d = parse_date(end_str)
                if d is not None and d < today:
                    db.delete(rec)
                    deleted_alerts += 1

        if deleted_events or deleted_alerts:
            db.commit()
            print(f"[Smart ESITH] Nettoyage auto : {deleted_events} événement(s) (>14j) et {deleted_alerts} alerte(s)/salle(s) expirée(s) supprimé(s).")
    except Exception as e:
        db.rollback()
        print("[Smart ESITH] Nettoyage automatique ignoré :", e)
    finally:
        if own_session:
            db.close()


def detect_cycle(code_module, text_content):
    code_module = str(code_module).upper() if pd.notna(code_module) else ""
    text_content = str(text_content).upper() if pd.notna(text_content) else ""

    # Priority 1: Prefix on code_module
    if any(code_module.startswith(p) for p in ['GCLM', 'GPHM', 'DEHM', 'GASM', 'GPTM', 'CPTCM33ANG']):
        return 'Licence'
    if any(code_module.startswith(p) for p in ['MDMM', 'MPTHM', 'ELOGM', 'HSEM', 'HSE']):
        return 'Master'
    if any(code_module.startswith(p) for p in ['LILI', 'LITC', 'GI_', 'ITTI', 'IMSM', 'CTMM', 'THTH', 'THTC', 'CPCP', 'CPTC', 'IMS']):
        return 'Ingénieur'

    # Priority 2: Filière & Group identifiers in text_content / groupe
    # Filières Cycle Ingénieur : ITTI, IMS, CTM, EO, BDM, SL, INGTCG, etc.
    if any(p in text_content for p in ['ITTI', 'INGTCG', 'LILI', 'LITC', 'GI_', 'IMSM', 'CTMM', 'THTH', 'THTC', 'CPCP', 'CPTC']):
        return 'Ingénieur'
    words = re.findall(r'[A-Z0-9_]+', text_content)
    if any(any(w.startswith(p) for p in ['ITTI', 'IMS', 'CTM', 'EO', 'BDM', 'SL', 'INGTCG', 'CPTC', 'CPCP']) for w in words):
        return 'Ingénieur'
    if any(any(w.startswith(p) for p in ['MDM', 'MPTH', 'ELOG', 'HSE']) for w in words):
        return 'Master'
    if any(any(w.startswith(p) for p in ['GCL', 'GPH', 'DEH', 'GAS', 'GPT']) for w in words):
        return 'Licence'

    # Priority 3: Keywords
    if any(w in text_content for w in ['INGENIEUR', ' 1A', ' 2A', ' 3A', 'CPTC', 'CPCP', 'CP1', 'CP2', ' CP ']) or text_content.startswith('CP '):
        return 'Ingénieur'
    if any(w in text_content for w in ['MASTER', 'MASTERE', 'M1', 'M2']):
        return 'Master'
    if any(w in text_content for w in ['LICENCE', 'LIC', 'S1', 'S2', 'S3', 'S4', 'S5', 'S6']):
        return 'Licence'

    return 'Autre'


# =====================================================================
# Lecture des fichiers CSV / Excel
# =====================================================================
def decode_bytes(raw):
    for enc in ('utf-8-sig', 'cp1252'):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode('latin-1')


def detect_separator(content):
    lines = [l for l in content.splitlines()[:10] if l.strip()]
    sample = '\n'.join(lines)
    counts = {sep: sample.count(sep) for sep in (';', '\t', ',')}
    best = max(counts, key=counts.get)
    return best if counts[best] > 0 else ';'


def read_table(file_storage, header='infer'):
    """Lit un fichier CSV/XLSX/XLS envoyé et retourne un DataFrame (cellules en objets bruts)."""
    filename = (file_storage.filename or '').lower()
    raw = file_storage.read()
    if not raw:
        raise ValueError("Le fichier est vide.")
    hdr = 0 if header == 'infer' else header
    if filename.endswith(('.xlsx', '.xlsm', '.xls')):
        engine = 'xlrd' if filename.endswith('.xls') else 'openpyxl'
        try:
            df = pd.read_excel(io.BytesIO(raw), header=hdr, dtype=object, engine=engine)
        except ImportError:
            raise ValueError("Format .xls non supporté sur ce serveur : enregistrez le fichier en .xlsx ou .csv.")
    else:
        content = decode_bytes(raw)
        sep = detect_separator(content)
        df = pd.read_csv(io.StringIO(content), sep=sep, header=hdr, dtype=str,
                         engine='python', skip_blank_lines=True)
    # Supprime les lignes entièrement vides
    df = df.dropna(how='all')
    return df


def normalize_columns(df):
    """Noms de colonnes : sans accents, majuscules, espaces -> '_'."""
    df.columns = [re.sub(r'\s+', '_', strip_accents(str(c)).strip().upper()) for c in df.columns]
    return df


def pick(row, *names):
    """Retourne la première valeur non vide parmi plusieurs colonnes possibles."""
    for n in names:
        if n in row.index:
            v = clean(row[n])
            if v:
                return v
    return ''


# =====================================================================
# Authentification JWT
# =====================================================================
def jwt_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.headers.get('Authorization', '')
        parts = auth.split()
        token = parts[1] if len(parts) == 2 and parts[0].lower() == 'bearer' else None
        if not token:
            return jsonify({"message": "Token manquant", "error": "Token manquant"}), 401
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            db = get_db()
            current_user = db.query(User).filter_by(id=data['user_id'], actif=True).first()
            if not current_user:
                raise Exception("Utilisateur introuvable")
        except Exception as e:
            return jsonify({"message": "Session expirée ou invalide", "error": "Session expirée, reconnectez-vous."}), 401
        return f(current_user, *args, **kwargs)
    return decorated


def roles_allowed(current_user, *roles):
    return current_user.role == 'Admin' or current_user.role in roles


def forbidden():
    return jsonify({"error": "Accès refusé pour votre rôle."}), 403


def log_action(db, current_user, action, details=""):
    try:
        now = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        username = getattr(current_user, 'username', str(current_user))
        role = getattr(current_user, 'role', 'Inconnu')
        entry = ActionLog(
            user=username,
            role=role,
            action=action,
            details=str(details) if details else "",
            timestamp=now
        )
        db.add(entry)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"[Smart ESITH] Erreur log_action : {e}")


# =====================================================================
# Gestion d'erreurs API (toujours du JSON)
# =====================================================================
@app.errorhandler(404)
def not_found(e):
    if request.path.startswith('/api/'):
        return jsonify({"error": "Ressource introuvable"}), 404
    return e


@app.errorhandler(413)
def too_large(e):
    return jsonify({"error": "Fichier trop volumineux (20 Mo max)."}), 413


@app.errorhandler(500)
def server_error(e):
    if request.path.startswith('/api/'):
        return jsonify({"error": "Erreur interne du serveur"}), 500
    return e


# -----------------
# Auth Routes
# -----------------
@app.route('/api/auth/login', methods=['POST'])
def login():
    # OWASP A07 & A04: Protection anti brute-force par IP
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr or '127.0.0.1').split(',')[0].strip()
    now_ts = datetime.datetime.now().timestamp()
    attempts = [t for t in LOGIN_ATTEMPTS.get(client_ip, []) if now_ts - t < LOGIN_LOCKOUT_WINDOW]
    if len(attempts) >= MAX_LOGIN_ATTEMPTS:
        remaining = int(LOGIN_LOCKOUT_WINDOW - (now_ts - attempts[0]))
        return jsonify({
            'message': f'Trop de tentatives échouées. Compte temporairement verrouillé pour {remaining} secondes.',
            'error': f'Trop de tentatives échouées. Veuillez patienter {remaining} secondes.'
        }), 429

    data = request.get_json(silent=True) or {}
    username = clean(data.get('username')).lower()
    password = data.get('password') or ''
    db = get_db()
    user = db.query(User).filter_by(username=username, actif=True).first()
    valid = False
    if user:
        if user.password_hash and check_password_hash(user.password_hash, password):
            valid = True
        elif not user.password_hash and password in (f"{username}2024", "esith2024", "admin2024"):
            valid = True
            from werkzeug.security import generate_password_hash
            user.password_hash = generate_password_hash(password)
            db.commit()

    if valid:
        # Réinitialisation des tentatives échouées après connexion réussie
        LOGIN_ATTEMPTS.pop(client_ip, None)
        token = jwt.encode({'user_id': user.id, 'exp': datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=24)}, app.config['SECRET_KEY'], algorithm="HS256")
        log_action(db, user, "Connexion", f"Connexion réussie depuis IP {client_ip}")
        return jsonify({'token': token, 'access_token': token, 'role': user.role, 'username': user.username})

    # OWASP A09: Enregistrement de l'échec d'authentification pour surveillance
    attempts.append(now_ts)
    LOGIN_ATTEMPTS[client_ip] = attempts
    try:
        log_action(db, username or "Anonyme", "Échec de connexion", f"Tentative avec mot de passe invalide depuis IP {client_ip}")
    except Exception:
        pass

    return jsonify({'message': 'Identifiants invalides', 'error': 'Identifiants invalides'}), 401


@app.route('/api/auth/me', methods=['GET'])
@jwt_required
def get_me(current_user):
    return jsonify({'username': current_user.username, 'role': current_user.role})


# -----------------
# Hall Routes
# -----------------
def resolve_display_date(db):
    """Retourne la date du jour et indique si des séances existent aujourd'hui."""
    today = today_str()
    has_today = (db.query(Cours.id).filter(Cours.date == today).first() is not None
                 or db.query(Formation.id).filter_by(date=today, actif=True).first() is not None)
    return today, has_today


def resolve_fi_display_date(db, now=None):
    """
    Règle Formation Initiale :
    - Avant 17h30 : séances d'aujourd'hui.
    - À partir de 17h30 : planning de demain (ou prochain jour de cours si week-end).
    Retourne (date_fi, is_tomorrow).
    """
    if now is None:
        now = datetime.datetime.now()

    today_date = now.date()
    today_str_val = today_date.strftime('%d/%m/%Y')

    # Heure pivot : 17h30
    is_after_cutoff = (now.hour > 17 or (now.hour == 17 and now.minute >= 30))
    if not is_after_cutoff:
        return today_str_val, False

    # À partir de 17h30 : chercher demain
    tomorrow_date = today_date + datetime.timedelta(days=1)
    tomorrow_str = tomorrow_date.strftime('%d/%m/%Y')

    # Vérifie si demain a des cours de formation initiale
    has_tomorrow_courses = db.query(Cours.id).filter(
        Cours.date == tomorrow_str,
        Cours.Cycle != CYCLE_RE,
        Cours.Cycle != 'Autre'
    ).first() is not None

    if has_tomorrow_courses:
        return tomorrow_str, True

    # Si demain n'a pas de cours (ex. week-end vendredi/samedi),
    # chercher les prochains jours dans les 3 jours suivants (ex. lundi)
    future_dates = sorted([
        p for p in (parse_date(d) for (d,) in db.query(Cours.date).filter(
            Cours.Cycle != CYCLE_RE,
            Cours.Cycle != 'Autre'
        ).distinct().all())
        if p and p > today_date
    ])

    if future_dates and (future_dates[0] - today_date).days <= 3:
        return future_dates[0].strftime('%d/%m/%Y'), True

    return tomorrow_str, True


def fmt_h(hd, hf):
    hd, hf = clean(hd), clean(hf)
    if hd and hf:
        return f"{hd}-{hf}"
    return hd or hf


@app.route('/api/hall/all_data', methods=['GET'])
def get_all_data():
    db = get_db()
    cleanup_expired_records(db)

    now = datetime.datetime.now()
    sim_date = request.args.get('date')
    sim_time = request.args.get('time')
    if sim_date:
        parsed_d = parse_date(normalize_date(sim_date))
        if parsed_d:
            now = now.replace(year=parsed_d.year, month=parsed_d.month, day=parsed_d.day)
    if sim_time:
        try:
            parts = sim_time.split(':')
            now = now.replace(hour=int(parts[0]), minute=int(parts[1]))
        except Exception:
            pass

    today = now.strftime('%d/%m/%Y')
    fi_date, is_tomorrow_fi = resolve_fi_display_date(db, now)

    # 1. Formation Initiale : suit fi_date (aujourd'hui avant 17h30, demain après 17h30)
    cours_fi = db.query(Cours).filter(Cours.date == fi_date, Cours.Cycle != CYCLE_RE).all()

    # 2. Relations Entreprises : STRICTEMENT AUJOURD'HUI
    cours_re = db.query(Cours).filter(Cours.date == today, Cours.Cycle == CYCLE_RE).all()

    # 3. Formation Continue : STRICTEMENT AUJOURD'HUI
    formations = db.query(Formation).filter_by(actif=True, date=today).all()

    # 4. Absences, Retards, Changements de salle : AUJOURD'HUI
    absences = db.query(Absence).filter_by(date=today, actif=True).all()
    retards = db.query(Retard).filter_by(date=today, actif=True).all()
    changements = db.query(ChangementSalle).filter_by(date=today, actif=True).all()

    # Événements : tous les événements actifs à venir (date >= aujourd'hui)
    t = now.date()
    events = []
    for e in db.query(Event).filter_by(actif=True).all():
        d = parse_date(e.date)
        if d is None or d >= t:
            events.append((d or t, e))
    events.sort(key=lambda x: (x[0], clean(x[1].heure_debut)))

    # Recherche des affiches d'événements valides (non expirées) pour l'écran du Hall
    today_date = now.date()
    raw_posters = (
        db.query(Event)
        .filter(Event.actif == True, Event.media_path.isnot(None), Event.media_path != '')
        .order_by(Event.force_active.desc(), Event.id.desc())
        .all()
    )

    valid_posters = []
    for e in raw_posters:
        d_start = parse_date(e.date)
        d_end = parse_date(e.date_fin) if getattr(e, 'date_fin', None) else d_start
        if e.force_active:
            # Forcé en direct : affiché immédiatement sauf si date_fin dépassée
            if d_end and d_end < today_date:
                continue
            valid_posters.append(e)
        else:
            # Fenêtre de validité : start_date <= today_date <= end_date
            if d_start and d_end:
                if d_start <= today_date <= d_end:
                    valid_posters.append(e)
            elif e.date == today:
                valid_posters.append(e)

    event_posters_data = [
        {
            "id": e.id,
            "titre": clean(e.titre),
            "date": clean(e.date),
            "date_fin": clean(getattr(e, 'date_fin', None)),
            "lieu": clean(e.lieu),
            "heure_debut": clean(e.heure_debut),
            "media_path": e.media_path,
            "media_type": e.media_type or 'image',
            "mode_affichage": e.mode_affichage or 'rotation',
            "force_active": bool(e.force_active),
            "duree_affichage_sec": getattr(e, 'duree_affichage_sec', 10) or 10
        }
        for e in valid_posters
    ]

    # Poster prioritaire : figé en premier si actif aujourd'hui, sinon premier de la liste
    poster_event = next((p for p in valid_posters if p.mode_affichage == 'fige'), None)
    if not poster_event and valid_posters:
        poster_event = valid_posters[0]

    event_poster = None
    if poster_event and poster_event.media_path:
        event_poster = {
            "id": poster_event.id,
            "titre": clean(poster_event.titre),
            "date": clean(poster_event.date),
            "date_fin": clean(getattr(poster_event, 'date_fin', None)),
            "lieu": clean(poster_event.lieu),
            "heure_debut": clean(poster_event.heure_debut),
            "media_path": poster_event.media_path,
            "media_type": poster_event.media_type or 'image',
            "mode_affichage": poster_event.mode_affichage or 'rotation',
            "force_active": bool(poster_event.force_active),
            "duree_affichage_sec": getattr(poster_event, 'duree_affichage_sec', 10) or 10
        }

    data = {
        "date_affichee": fi_date if is_tomorrow_fi else today,
        "date_jour": today,
        "date_fi": fi_date,
        "is_tomorrow_fi": is_tomorrow_fi,
        "is_today": not is_tomorrow_fi,
        "heure_actuelle": now.strftime('%H:%M:%S'),
        "event_poster": event_poster,
        "event_posters": event_posters_data,
        "licence": [], "master": [], "ingenieur": [], "fc": [], "re": [],
        "absences": [{"groupe": clean(a.groupe), "prof": clean(a.prof), "heure": clean(a.heure), "motif": clean(a.motif)} for a in absences],
        "retards": [{"groupe": clean(r.groupe), "prof": clean(r.prof), "heure": clean(r.heure_prevue), "duree": clean(r.duree_retard)} for r in retards],
        "changements_salle": [{"groupe": clean(c.groupe), "ancienne_salle": clean(c.ancienne_salle), "nouvelle_salle": clean(c.nouvelle_salle), "heure": clean(c.heure_creation)} for c in changements],
        "events": [{"titre": clean(e.titre), "date": clean(e.date), "lieu": clean(e.lieu), "heure_debut": clean(e.heure_debut)} for _, e in events],
        "empreinte_carbone": load_config().get("empreinte_carbone", 0)
    }

    for c in cours_fi:
        cycle = c.Cycle
        g = (c.groupe or '').upper()
        if any(g.startswith(p) for p in ['ITTI', 'IMS', 'CTM', 'EO', 'BDM', 'SL', 'INGTCG', 'CPTC', 'CPCP', 'LILI', 'LITC', 'GI_', 'THTH', 'THTC']):
            cycle = 'Ingénieur'
        elif any(g.startswith(p) for p in ['GCL', 'GPH', 'DEH', 'GAS', 'GPT']):
            cycle = 'Licence'
        elif any(g.startswith(p) for p in ['MDM', 'MPTH', 'ELOG', 'HSE']):
            cycle = 'Master'

        c_dict = {"h": fmt_h(c.hd, c.hf), "hd": clean(c.hd), "hf": clean(c.hf), "groupe": clean(c.groupe),
                  "module": clean(c.module), "salle": clean(c.salle), "prof": clean(c.prof)}
        if cycle == 'Licence': data["licence"].append(c_dict)
        elif cycle == 'Master': data["master"].append(c_dict)
        elif cycle == 'Ingénieur': data["ingenieur"].append(c_dict)

    for c in cours_re:
        c_dict = {"h": fmt_h(c.hd, c.hf), "hd": clean(c.hd), "hf": clean(c.hf), "groupe": clean(c.groupe),
                  "module": clean(c.module), "salle": clean(c.salle), "prof": clean(c.prof)}
        data["re"].append(c_dict)

    for f in formations:
        titre = clean(f.titre)
        entreprise = clean(getattr(f, 'entreprise', ''))
        f_dict = {"h": fmt_h(f.heure_debut, f.heure_fin), "hd": clean(f.heure_debut), "hf": clean(f.heure_fin),
                  "groupe": entreprise or titre, "module": titre if entreprise else '',
                  "salle": clean(f.salle), "prof": clean(getattr(f, 'formateur', ''))}
        data["fc"].append(f_dict)

    return jsonify(data)


@app.route('/api/stats', methods=['GET'])
@jwt_required
def get_stats(current_user):
    if not roles_allowed(current_user, 'Admin'):
        return forbidden()
    db = get_db()
    today = today_str()
    par_cycle = {}
    for cycle in ['Licence', 'Ingénieur', 'Master', CYCLE_RE]:
        par_cycle[cycle] = db.query(Cours).filter_by(date=today, Cycle=cycle).count()
    par_cycle['Formation Continue'] = db.query(Formation).filter_by(date=today, actif=True).count()
    nb_events = sum(1 for e in db.query(Event).filter_by(actif=True).all()
                    if (parse_date(e.date) or datetime.date.today()) >= datetime.date.today())
    return jsonify({
        "date": today,
        "cours_aujourdhui": db.query(Cours).filter_by(date=today).count(),
        "absences_aujourdhui": db.query(Absence).filter_by(date=today, actif=True).count(),
        "retards_aujourdhui": db.query(Retard).filter_by(date=today, actif=True).count(),
        "changements_aujourdhui": db.query(ChangementSalle).filter_by(date=today, actif=True).count(),
        "evenements_a_venir": nb_events,
        "total_cours": db.query(Cours).count(),
        "par_cycle": par_cycle,
    })


@app.route('/api/config/carbone', methods=['GET'])
def get_carbone():
    return jsonify({"empreinte_carbone": load_config().get("empreinte_carbone", 0)})


@app.route('/api/config/carbone', methods=['POST'])
@jwt_required
def set_carbone(current_user):
    if not roles_allowed(current_user, 'Scolarite', 'DRE', 'DEE'):
        return forbidden()
    data = request.get_json(silent=True) or {}
    try:
        val = float(data.get("empreinte_carbone", 0))
    except (TypeError, ValueError):
        return jsonify({"error": "Valeur invalide"}), 400
    val = max(0, min(100, val))
    if val.is_integer():
        val = int(val)
    save_config({"empreinte_carbone": val})
    db = get_db()
    log_action(db, current_user, "Modification empreinte carbone", f"Nouvelle valeur: {val}%")
    return jsonify({"success": True, "empreinte_carbone": val})


# -----------------
# Dashboard Routes (imports)
# -----------------
def get_upload():
    file = request.files.get('file')
    if not file or not file.filename:
        return None
    return file


@app.route('/api/dashboard/import-planning', methods=['POST'])
@jwt_required
def import_planning(current_user):
    if not roles_allowed(current_user, 'DEE'):
        return forbidden()
    file = get_upload()
    if not file:
        return jsonify({"error": "Aucun fichier sélectionné"}), 400

    raw_file_bytes = file.read()
    file.seek(0)

    try:
        df = read_table(file, header=None)
    except Exception as e:
        return jsonify({"error": f"Lecture du fichier impossible : {e}"}), 400

    if df.empty:
        return jsonify({"error": "Le fichier ne contient aucune ligne."}), 400
    if df.shape[1] < 15:
        return jsonify({"error": f"Format inattendu : 15 colonnes attendues (id_seance;dateSeance;numDay;HD;HF;...;AppelFait), {df.shape[1]} trouvée(s)."}), 400

    # Ignore la ligne d'en-tête si présente
    if parse_date(normalize_date(df.iloc[0, 1]) or '') is None:
        df = df.iloc[1:]

    db = get_db()
    imported, ignored = 0, 0
    dates_imported = set()
    profs_imported = set()
    fils_imported = set()

    try:
        # Reset Formation Initiale (règle 9.7)
        db.query(Cours).filter(Cours.Cycle.in_(FI_CYCLES)).delete(synchronize_session=False)

        for _, row in df.iterrows():
            row = list(row)
            date = normalize_date(row[1])
            if not date or parse_date(date) is None:
                ignored += 1
                continue
            hd = normalize_time(row[3])
            hf = normalize_time(row[4])
            # HF absente ou non pertinente (00:30) -> calcul via la durée décimale
            if hd and (not hf or hf == '00:30' or hf <= hd):
                try:
                    duree = float(clean(row[6]).replace(',', '.'))
                    h, m = map(int, hd.split(':'))
                    end_time = datetime.datetime(2000, 1, 1, h, m) + datetime.timedelta(hours=duree)
                    hf = end_time.strftime('%H:%M')
                except (ValueError, TypeError):
                    if hf == '00:30':
                        hf = ''

            cycle = detect_cycle(clean(row[11]), f"{clean(row[13])} {clean(row[9])}")
            prof_val = clean(row[8])
            groupe_val = clean(row[9])

            if prof_val:
                profs_imported.add(prof_val)
            if groupe_val:
                fils_imported.update(extract_filieres_from_group(groupe_val))

            d_parsed = parse_date(date)
            if d_parsed:
                dates_imported.add(d_parsed)

            db.add(Cours(
                numDay=clean(row[2]),
                date=date,
                hd=hd,
                hf=hf,
                salle=clean(row[7]),
                prof=prof_val,
                groupe=groupe_val,
                module=clean(row[10]),
                Cycle=cycle,
                AppelFait=clean(row[14]) or 'Non'
            ))
            imported += 1

        period_start_str, period_end_str = None, None
        if imported > 0 and dates_imported:
            min_d = min(dates_imported)
            max_d = max(dates_imported)
            period_start_str = min_d.strftime('%d/%m/%Y')
            period_end_str = max_d.strftime('%d/%m/%Y')
            p_type = 'month' if (max_d - min_d).days > 10 else 'week'

            # Désactive les anciens imports
            db.query(PlanningImport).update({PlanningImport.active: False})

            new_import = PlanningImport(
                filename=getattr(file, 'filename', 'planning_fi.xlsx') or 'planning_fi.xlsx',
                import_date=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                period_start=period_start_str,
                period_end=period_end_str,
                period_type=p_type,
                professors=json.dumps(sorted(list(profs_imported)), ensure_ascii=False),
                filieres=json.dumps(sorted(list(fils_imported)), ensure_ascii=False),
                active=True
            )
            db.add(new_import)

        db.commit()

        # Archivage automatique de sécurité pour 3 mois (90 jours) et instantané de la base
        save_file_backup(raw_file_bytes, getattr(file, 'filename', 'planning_fi.xlsx') or 'planning_fi.xlsx', 'planning_fi', db)
        create_database_backup(db)
    except Exception as e:
        db.rollback()
        return jsonify({"error": f"Erreur d'import : {e}"}), 500

    if imported == 0:
        return jsonify({"error": f"Aucune séance valide trouvée ({ignored} ligne(s) ignorée(s)). Vérifiez la colonne date."}), 400
    log_action(db, current_user, "Import planning FI", f"{imported} séance(s) importée(s), {len(profs_imported)} profs, {len(fils_imported)} filières")
    return jsonify({
        "message": f"Import réussi : {imported} séance(s) importée(s), {ignored} ligne(s) ignorée(s).",
        "imported": imported,
        "ignored": ignored,
        "period_start": period_start_str,
        "period_end": period_end_str,
        "count_professors": len(profs_imported),
        "count_filieres": len(fils_imported)
    })


@app.route('/api/dashboard/active-period-data', methods=['GET'])
def get_active_period_data():
    """Retourne les professeurs et filières de la période active (semaine / mois en cours).
    Règle Empty State : Si aucun planning n'a été importé pour la période en cours,
    retourne active=False avec des listes vides.
    """
    db = get_db()
    req_date = request.args.get('date')
    ref_d = parse_date(normalize_date(req_date)) if req_date else None
    data = get_active_planning_import(db, ref_d)
    return jsonify(data)


@app.route('/api/dashboard/attendance', methods=['GET'])
def get_attendance():
    """Suivi et recherche des présences hebdomadaires des professeurs.
    Compare les séances programmées du planning Excel (ex: Lundi, Mercredi, Vendredi)
    avec les absences, retards ou annulations enregistrés.
    Par défaut, une séance programmée sans alerte est marquée comme 'Présent'.
    """
    db = get_db()
    prof_query = clean(request.args.get('prof', '')).lower()
    filiere_query = clean(request.args.get('filiere', '')).upper()
    req_start = request.args.get('date_start')
    req_end = request.args.get('date_end')

    active_imp = get_active_planning_import(db)
    if req_start and req_end:
        p_start_d = parse_date(normalize_date(req_start))
        p_end_d = parse_date(normalize_date(req_end))
    elif active_imp['active']:
        p_start_d = parse_date(active_imp['period_start'])
        p_end_d = parse_date(active_imp['period_end'])
    else:
        today = datetime.date.today()
        p_start_d = today - datetime.timedelta(days=today.weekday())
        p_end_d = p_start_d + datetime.timedelta(days=6)

    cours_all = db.query(Cours).filter(Cours.Cycle.in_(FI_CYCLES)).all()
    cours_in_period = []
    for c in cours_all:
        d = parse_date(c.date)
        if d and p_start_d and p_end_d and p_start_d <= d <= p_end_d:
            cours_in_period.append((d, c))

    cours_in_period.sort(key=lambda x: (x[0], clean(x[1].hd)))

    absences = db.query(Absence).filter_by(actif=True).all()
    retards = db.query(Retard).filter_by(actif=True).all()

    abs_by_prof_date = {}
    for a in absences:
        abs_by_prof_date.setdefault((clean(a.prof).lower(), a.date), []).append(a)

    ret_by_prof_date = {}
    for r in retards:
        ret_by_prof_date.setdefault((clean(r.prof).lower(), r.date), []).append(r)

    prof_sessions = {}
    for d, c in cours_in_period:
        prof_name = clean(c.prof)
        if not prof_name:
            continue
        if prof_query and prof_query not in prof_name.lower():
            continue

        c_fils = extract_filieres_from_group(c.groupe)
        if filiere_query:
            if filiere_query.startswith('CYCLE:'):
                target_cycle = filiere_query.split(':', 1)[1].strip().lower()
                if clean(c.Cycle).lower() != target_cycle:
                    continue
            elif filiere_query not in c_fils:
                continue

        p_key = (prof_name.lower(), c.date)
        matched_abs = abs_by_prof_date.get(p_key, [])
        cand_abs = next((a for a in matched_abs if match_alert_to_session(a, c, is_retard=False)), None)

        cand_ret = None
        if not cand_abs:
            matched_ret = ret_by_prof_date.get(p_key, [])
            cand_ret = next((r for r in matched_ret if match_alert_to_session(r, c, is_retard=True)), None)

        if cand_abs:
            motif_txt = clean(cand_abs.motif) or ""
            if 'annul' in motif_txt.lower():
                status = "Annulé"
                details = motif_txt or "Séance annulée"
            else:
                status = "Absent"
                details = motif_txt or "Absence déclarée"
        elif cand_ret:
            status = "En retard"
            dur = clean(cand_ret.duree_retard)
            details = f"Retard: {dur}" if dur else "Retard signalé"
        else:
            status = "Présent"
            details = ""

        session_info = {
            "id": c.id,
            "date": c.date,
            "day_name": JOURS_FR.get(d.weekday(), ""),
            "date_sort": d.isoformat(),
            "hd": clean(c.hd),
            "hf": clean(c.hf),
            "horaire": fmt_h(c.hd, c.hf),
            "groupe": clean(c.groupe),
            "filieres": list(c_fils),
            "module": clean(c.module),
            "salle": clean(c.salle),
            "status": status,
            "details": details
        }
        prof_sessions.setdefault(prof_name, []).append(session_info)

    result_profs = []
    for prof_name, sess_list in sorted(prof_sessions.items(), key=lambda x: x[0]):
        sess_list.sort(key=lambda s: (s["date_sort"], s["hd"]))

        days_map = {}
        for s in sess_list:
            d_key = s["date"]
            if d_key not in days_map:
                days_map[d_key] = {
                    "date": d_key,
                    "day_name": s["day_name"],
                    "sessions": []
                }
            days_map[d_key]["sessions"].append(s)

        days_summary = []
        for d_key, d_obj in days_map.items():
            day_statuses = [ss["status"] for ss in d_obj["sessions"]]
            p_cnt = sum(1 for st in day_statuses if st == "Présent")
            a_cnt = sum(1 for st in day_statuses if st == "Absent")
            r_cnt = sum(1 for st in day_statuses if st == "En retard")
            can_cnt = sum(1 for st in day_statuses if st == "Annulé")
            total_d = len(day_statuses)

            if p_cnt == total_d:
                d_stat = "Présent"
            elif a_cnt == total_d:
                d_stat = "Absent"
            elif r_cnt == total_d:
                d_stat = "En retard"
            elif can_cnt == total_d:
                d_stat = "Annulé"
            else:
                parts = []
                if p_cnt > 0:
                    parts.append(f"{p_cnt} Présent(s)")
                if a_cnt > 0:
                    parts.append(f"{a_cnt} Absent(s)")
                if r_cnt > 0:
                    parts.append(f"{r_cnt} Retard(s)")
                if can_cnt > 0:
                    parts.append(f"{can_cnt} Annulé(s)")
                d_stat = ", ".join(parts) if parts else "Mixte"
            d_obj["day_status"] = d_stat
            days_summary.append(d_obj)

        total = len(sess_list)
        presents = sum(1 for s in sess_list if s["status"] == "Présent")
        absents = sum(1 for s in sess_list if s["status"] == "Absent")
        retards_cnt = sum(1 for s in sess_list if s["status"] == "En retard")
        annules = sum(1 for s in sess_list if s["status"] == "Annulé")

        summary_text = ", ".join(f"{d['day_name']}: {d['day_status']}" for d in days_summary)

        all_fils = set()
        for s in sess_list:
            all_fils.update(s["filieres"])

        result_profs.append({
            "prof": prof_name,
            "filieres": sorted(list(all_fils)),
            "total_sessions": total,
            "presents": presents,
            "absents": absents,
            "retards": retards_cnt,
            "annules": annules,
            "summary_text": f"Prof. {prof_name} — {summary_text}" if summary_text else f"Prof. {prof_name}",
            "days": days_summary,
            "sessions": sess_list
        })

    return jsonify({
        "period": {
            "start": p_start_d.strftime('%d/%m/%Y') if p_start_d else '',
            "end": p_end_d.strftime('%d/%m/%Y') if p_end_d else ''
        },
        "total_professors": len(result_profs),
        "professors": result_profs
    })


@app.route('/api/export-journal', methods=['GET'])
@app.route('/api/dashboard/export-journal', methods=['GET'])
def export_journal():
    """Génère et télécharge le rapport Excel (.xlsx) multi-feuilles :
    1. Profs Présents (séances honorées)
    2. Profs Absents (professeur, date, filière, module)
    3. Profs en Retard (professeur, date, filière, durée retard)
    4. Séances Annulées (professeur, date, filière, motif)
    """
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    db = get_db()
    req_start = request.args.get('date_start')
    req_end = request.args.get('date_end')

    active_imp = get_active_planning_import(db)
    if req_start and req_end:
        p_start_d = parse_date(normalize_date(req_start))
        p_end_d = parse_date(normalize_date(req_end))
    elif active_imp['active']:
        p_start_d = parse_date(active_imp['period_start'])
        p_end_d = parse_date(active_imp['period_end'])
    else:
        today = datetime.date.today()
        p_start_d = today - datetime.timedelta(days=today.weekday())
        p_end_d = p_start_d + datetime.timedelta(days=6)

    cours_all = db.query(Cours).filter(Cours.Cycle.in_(FI_CYCLES)).all()
    cours_in_period = []
    for c in cours_all:
        d = parse_date(c.date)
        if d and p_start_d and p_end_d and p_start_d <= d <= p_end_d:
            cours_in_period.append((d, c))
    cours_in_period.sort(key=lambda x: (x[0], clean(x[1].hd)))

    absences = db.query(Absence).filter_by(actif=True).all()
    retards = db.query(Retard).filter_by(actif=True).all()

    abs_by_prof_date = {}
    for a in absences:
        abs_by_prof_date.setdefault((clean(a.prof).lower(), a.date), []).append(a)

    ret_by_prof_date = {}
    for r in retards:
        ret_by_prof_date.setdefault((clean(r.prof).lower(), r.date), []).append(r)

    rows_presents = []
    rows_absents = []
    rows_retards = []
    rows_annules = []

    for d, c in cours_in_period:
        prof_name = clean(c.prof)
        if not prof_name:
            continue
        c_fils = ", ".join(sorted(extract_filieres_from_group(c.groupe)))
        day_name = JOURS_FR.get(d.weekday(), "")
        horaire = fmt_h(c.hd, c.hf)

        p_key = (prof_name.lower(), c.date)
        matched_abs = abs_by_prof_date.get(p_key, [])
        cand_abs = next((a for a in matched_abs if match_alert_to_session(a, c, is_retard=False)), None)

        cand_ret = None
        if not cand_abs:
            matched_ret = ret_by_prof_date.get(p_key, [])
            cand_ret = next((r for r in matched_ret if match_alert_to_session(r, c, is_retard=True)), None)

        if cand_abs:
            motif_txt = clean(cand_abs.motif) or "Absence déclarée"
            if 'annul' in motif_txt.lower():
                rows_annules.append([
                    c.date, day_name, horaire, prof_name, c_fils, clean(c.groupe), clean(c.module), clean(c.salle), motif_txt
                ])
            else:
                rows_absents.append([
                    c.date, day_name, horaire, prof_name, c_fils, clean(c.groupe), clean(c.module), clean(c.salle), motif_txt
                ])
        elif cand_ret:
            dur = clean(cand_ret.duree_retard) or "Non précisé"
            h_prev = clean(cand_ret.heure_prevue) or clean(c.hd)
            h_reel = clean(cand_ret.heure_reelle) or "-"
            rows_retards.append([
                c.date, day_name, h_prev, h_reel, dur, prof_name, c_fils, clean(c.groupe), clean(c.module), clean(c.salle)
            ])
        else:
            rows_presents.append([
                c.date, day_name, clean(c.hd), clean(c.hf), prof_name, c_fils, clean(c.groupe), clean(c.module), clean(c.salle), "Présent"
            ])

    wb = openpyxl.Workbook()

    header_fill = PatternFill(start_color="0B4F6C", end_color="0B4F6C", fill_type="solid")
    header_font = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
    data_font = Font(name="Segoe UI", size=10)
    zebra_fill = PatternFill(start_color="F7F9FA", end_color="F7F9FA", fill_type="solid")
    thin_border = Border(
        left=Side(style='thin', color='D0D7DE'),
        right=Side(style='thin', color='D0D7DE'),
        top=Side(style='thin', color='D0D7DE'),
        bottom=Side(style='thin', color='D0D7DE')
    )
    center_align = Alignment(horizontal="center", vertical="center")
    left_align = Alignment(horizontal="left", vertical="center")

    sheets_config = [
        ("Profs Présents", [
            "Date", "Jour", "Début", "Fin", "Professeur", "Filière", "Groupe", "Module", "Salle", "Statut"
        ], rows_presents),
        ("Profs Absents", [
            "Date", "Jour", "Horaire", "Professeur", "Filière", "Groupe", "Module", "Salle", "Motif d'absence"
        ], rows_absents),
        ("Profs en Retard", [
            "Date", "Jour", "Heure Prévue", "Heure Réelle", "Durée Retard", "Professeur", "Filière", "Groupe", "Module", "Salle"
        ], rows_retards),
        ("Séances Annulées", [
            "Date", "Jour", "Horaire", "Professeur", "Filière", "Groupe", "Module", "Salle", "Motif / Raison d'annulation"
        ], rows_annules),
    ]

    for idx, (title, headers, data_rows) in enumerate(sheets_config):
        if idx == 0:
            ws = wb.active
            ws.title = title
        else:
            ws = wb.create_sheet(title=title)

        ws.views.sheetView[0].showGridLines = True
        ws.row_dimensions[1].height = 28

        for col_num, h_text in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col_num, value=h_text)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = center_align
            cell.border = thin_border

        for r_idx, row_values in enumerate(data_rows, 2):
            ws.row_dimensions[r_idx].height = 20
            is_even = (r_idx % 2 == 0)
            for c_idx, val in enumerate(row_values, 1):
                cell = ws.cell(row=r_idx, column=c_idx, value=val)
                cell.font = data_font
                cell.border = thin_border
                if is_even:
                    cell.fill = zebra_fill
                if c_idx in (1, 2, 3, 4, 10):
                    cell.alignment = center_align
                else:
                    cell.alignment = left_align

        for col in ws.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                val_str = str(cell.value or '')
                if len(val_str) > max_len:
                    max_len = len(val_str)
            ws.column_dimensions[col_letter].width = max(max_len + 3, 12)

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    filename = f"Journal_ESITH_{p_start_d.strftime('%Y%m%d') if p_start_d else 'global'}.xlsx"
    return send_file(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=filename
    )


@app.route('/api/dashboard/import-append', methods=['POST'])
@jwt_required
def import_append(current_user):
    req_type = request.args.get('type') or request.form.get('type')  # 'formation_continue' ou 'visites'
    if req_type not in ('formation_continue', 'visites'):
        return jsonify({"error": "Paramètre 'type' invalide (formation_continue ou visites)."}), 400
    if req_type == 'formation_continue' and not roles_allowed(current_user, 'FC'):
        return forbidden()
    if req_type == 'visites' and not roles_allowed(current_user, 'DRE'):
        return forbidden()

    file = get_upload()
    if not file:
        return jsonify({"error": "Aucun fichier sélectionné"}), 400
    raw_file_bytes = file.read()
    file.seek(0)
    try:
        df = normalize_columns(read_table(file))
    except Exception as e:
        return jsonify({"error": f"Erreur de lecture du fichier : {e}"}), 400

    if 'DATE' not in df.columns:
        return jsonify({"error": f"Colonne DATE manquante. Colonnes trouvées : {', '.join(df.columns.tolist())}"}), 400

    # Prépare les lignes valides
    rows, ignored = [], 0
    for _, row in df.iterrows():
        date = normalize_date(row['DATE'])
        if not date or parse_date(date) is None:
            ignored += 1
            continue
        rows.append((date, row))

    if not rows:
        return jsonify({"error": f"Aucune ligne avec une date valide ({ignored} ligne(s) ignorée(s)). Format attendu : JJ/MM/AAAA."}), 400

    dates_in_file = sorted({d for d, _ in rows}, key=parse_date)
    db = get_db()
    imported = 0
    try:
        if req_type == 'formation_continue':
            # Vide toute la table formations (comme spécifié dans le cahier des charges)
            db.query(Formation).delete(synchronize_session=False)
            for date, row in rows:
                titre = pick(row, 'THEME', 'MODULE', 'FORMATION', 'INTITULE', 'OBJET', 'TITRE', 'MASTERE', 'MASTER')
                entreprise = pick(row, 'ENTREPRISE', 'GROUPE', 'MASTERE', 'MASTER', 'CLIENT')
                if not titre:
                    titre = entreprise
                    entreprise = ''
                if not titre:
                    ignored += 1
                    continue
                if entreprise == titre:
                    entreprise = ''
                db.add(Formation(
                    titre=titre,
                    date=date,
                    heure_debut=normalize_time(pick(row, 'HD', 'HEURE_DEBUT', 'HDEBUT', 'DEBUT')),
                    heure_fin=normalize_time(pick(row, 'HF', 'HEURE_FIN', 'HFIN', 'FIN')),
                    salle=pick(row, 'SALLE', 'LIEU'),
                    entreprise=entreprise,
                    formateur=pick(row, 'FORMATEUR', 'PROF', 'INTERVENANT', 'ANIMATEUR'),
                ))
                imported += 1
        else:
            # Vide les cours Cycle='Relations Entreprises'
            db.query(Cours).filter_by(Cycle=CYCLE_RE).delete(synchronize_session=False)
            for date, row in rows:
                entreprise = pick(row, 'ENTREPRISE', 'GROUPE', 'NOM', 'SOCIETE')
                visite = pick(row, 'VISITE', 'OBJET', 'MODULE', 'TITRE', 'THEME')
                if not entreprise and not visite:
                    ignored += 1
                    continue
                db.add(Cours(
                    date=date,
                    hd=normalize_time(pick(row, 'HD', 'HEURE_DEBUT', 'HDEBUT', 'HEURE')),
                    hf=normalize_time(pick(row, 'HF', 'HEURE_FIN', 'HFIN')),
                    prof=pick(row, 'PROF', 'RESPONSABLE', 'CONTACT', 'ACCOMPAGNATEUR'),
                    salle=pick(row, 'SALLE', 'LIEU'),
                    groupe=entreprise or visite,
                    module=visite if entreprise else '',
                    Cycle=CYCLE_RE
                ))
                imported += 1
        db.commit()
        # Archivage de sécurité pour 3 mois (90 jours)
        save_file_backup(raw_file_bytes, getattr(file, 'filename', f"{req_type}.xlsx") or f"{req_type}.xlsx", req_type, db)
        log_action(db, current_user, f"Import {'Formation Continue' if req_type == 'formation_continue' else 'Visites RE'}", f"{imported} ligne(s) importée(s), {ignored} ignorée(s)")
    except Exception as e:
        db.rollback()
        return jsonify({"error": f"Erreur d'import : {e}"}), 500

    today = today_str()
    msg = f"Import réussi : {imported} ligne(s) importée(s), {ignored} ignorée(s). Date(s) : {', '.join(dates_in_file)}."
    if today not in dates_in_file:
        msg += f" ⚠️ Aucune ligne pour aujourd'hui ({today}) : le Hall affiche uniquement le programme du jour."
    return jsonify({"message": msg, "imported": imported, "ignored": ignored, "dates": dates_in_file})


@app.route('/api/dashboard/import-events', methods=['POST'])
@jwt_required
def import_events(current_user):
    if not roles_allowed(current_user, 'DEE', 'DRE'):
        return forbidden()
    file = get_upload()
    if not file:
        return jsonify({"error": "Aucun fichier sélectionné"}), 400
    raw_file_bytes = file.read()
    file.seek(0)
    try:
        df = normalize_columns(read_table(file))
    except Exception as e:
        return jsonify({"error": f"Erreur de lecture du fichier : {e}"}), 400
    if 'TITRE' not in df.columns or 'DATE' not in df.columns:
        return jsonify({"error": f"Colonnes TITRE et DATE requises. Colonnes trouvées : {', '.join(df.columns.tolist())}"}), 400

    db = get_db()
    imported, ignored = 0, 0
    try:
        db.query(Event).delete()
        for _, row in df.iterrows():
            titre = pick(row, 'TITRE')
            date = normalize_date(row['DATE'])
            if not titre or not date:
                ignored += 1
                continue
            db.add(Event(titre=titre, date=date, heure_debut=normalize_time(pick(row, 'HEURE', 'HEURE_DEBUT', 'HD')), lieu=pick(row, 'LIEU')))
            imported += 1
        db.commit()
        # Archivage de sécurité pour 3 mois (90 jours)
        save_file_backup(raw_file_bytes, getattr(file, 'filename', 'events.csv') or 'events.csv', 'events', db)
        cleanup_expired_records(db)
        log_action(db, current_user, "Import événements CSV", f"{imported} événement(s) importé(s), {ignored} ignorée(s)")
    except Exception as e:
        db.rollback()
        return jsonify({"error": f"Erreur d'import : {e}"}), 500
    return jsonify({"message": f"{imported} événement(s) importé(s), {ignored} ligne(s) ignorée(s)."})


@app.route('/api/dashboard/import-absences-retards', methods=['POST'])
@jwt_required
def import_absences(current_user):
    if not roles_allowed(current_user, 'Scolarite', 'DEE'):
        return forbidden()
    file = get_upload()
    if not file:
        return jsonify({"error": "Aucun fichier sélectionné"}), 400
    raw_file_bytes = file.read()
    file.seek(0)
    try:
        df = normalize_columns(read_table(file))
    except Exception as e:
        return jsonify({"error": f"Erreur de lecture du fichier : {e}"}), 400
    if 'TYPE' not in df.columns:
        return jsonify({"error": f"Colonne TYPE manquante. Colonnes trouvées : {', '.join(df.columns.tolist())}"}), 400

    db = get_db()
    imported, ignored = 0, 0
    try:
        for _, row in df.iterrows():
            typ = pick(row, 'TYPE').upper()
            date = normalize_date(row['DATE']) if 'DATE' in df.columns else today_str()
            date = date or today_str()
            if typ == 'ABSENCE':
                db.add(Absence(prof=pick(row, 'PROF'), groupe=pick(row, 'GROUPE'), date=date, heure=normalize_time(pick(row, 'HEURE')), motif=pick(row, 'MOTIF')))
                imported += 1
            elif typ == 'RETARD':
                db.add(Retard(prof=pick(row, 'PROF'), groupe=pick(row, 'GROUPE'), date=date, heure_prevue=normalize_time(pick(row, 'HEURE')), duree_retard=pick(row, 'MOTIF', 'DUREE')))
                imported += 1
            else:
                ignored += 1
        db.commit()
        # Archivage de sécurité pour 3 mois (90 jours)
        save_file_backup(raw_file_bytes, getattr(file, 'filename', 'absences.csv') or 'absences.csv', 'absences', db)
        cleanup_expired_records(db)
        log_action(db, current_user, "Import absences/retards CSV", f"{imported} absence(s)/retard(s) importé(s), {ignored} ignorée(s)")
    except Exception as e:
        db.rollback()
        return jsonify({"error": f"Erreur d'import : {e}"}), 500
    return jsonify({"message": f"{imported} absence(s)/retard(s) importé(s), {ignored} ligne(s) ignorée(s)."})


# -----------------
# Gestion des Sauvegardes (Rétention : 3 mois / 90 jours)
# -----------------
@app.route('/api/dashboard/backups', methods=['GET'])
@jwt_required
def list_backups(current_user):
    """Liste tous les fichiers archivés (rétention de 3 mois).
    Écrase/supprime automatiquement les fichiers expirés.
    """
    if not roles_allowed(current_user, 'Admin', 'DEE', 'DRE', 'FC', 'Scolarite'):
        return forbidden()
    db = get_db()
    cleanup_expired_backups(db)

    now = datetime.datetime.now()
    backups = db.query(FileBackup).order_by(FileBackup.id.desc()).all()
    res = []
    for b in backups:
        try:
            exp_d = datetime.datetime.strptime(b.expire_at, '%Y-%m-%d %H:%M:%S')
            days_rem = max(0, (exp_d - now).days)
        except Exception:
            days_rem = 0
        size_human = f"{b.file_size / 1024:.1f} Ko" if b.file_size < 1024 * 1024 else f"{b.file_size / (1024 * 1024):.2f} Mo"
        res.append({
            "id": b.id,
            "filename": b.filename,
            "original_name": b.original_name,
            "category": b.category,
            "file_size": b.file_size,
            "file_size_human": size_human,
            "created_at": b.created_at,
            "expire_at": b.expire_at,
            "days_remaining": days_rem
        })
    return jsonify(res)


@app.route('/api/dashboard/backups/<int:id>/download', methods=['GET'])
@jwt_required
def download_backup(current_user, id):
    """Télécharge un fichier de sauvegarde archivé."""
    if not roles_allowed(current_user, 'Admin', 'DEE', 'DRE', 'FC', 'Scolarite'):
        return forbidden()
    db = get_db()
    b = db.query(FileBackup).filter_by(id=id).first()
    if not b:
        return jsonify({"error": "Fichier de sauvegarde introuvable"}), 404
    # Protection Path Traversal (OWASP A01 & A03)
    safe_filename = os.path.basename(b.filename)
    full_path = os.path.abspath(os.path.join(BACKUP_DIR, safe_filename))
    if not full_path.startswith(os.path.abspath(BACKUP_DIR)) or not os.path.exists(full_path):
        return jsonify({"error": "Le fichier physique n'existe plus sur le disque"}), 404
    return send_file(
        full_path,
        as_attachment=True,
        download_name=os.path.basename(b.original_name)
    )


@app.route('/api/dashboard/backups/clean', methods=['POST'])
@jwt_required
def manual_clean_backups(current_user):
    """Déclenche la purge / écrasement des fichiers de sauvegarde expirés (> 3 mois)."""
    if not roles_allowed(current_user, 'Admin', 'DEE'):
        return forbidden()
    db = get_db()
    deleted = cleanup_expired_backups(db)
    log_action(db, current_user, "Purge sauvegardes (>3 mois)", f"{deleted} fichier(s) écrasé(s)/supprimé(s)")
    return jsonify({"success": True, "deleted_count": deleted})


@app.route('/api/dashboard/backups/create-db-backup', methods=['POST'])
@jwt_required
def manual_db_backup(current_user):
    """Crée manuellement une sauvegarde de la base de données avec rétention de 3 mois."""
    if not roles_allowed(current_user, 'Admin', 'DEE'):
        return forbidden()
    db = get_db()
    rec = create_database_backup(db)
    if not rec:
        return jsonify({"error": "Impossible de créer la sauvegarde de la base"}), 500
    log_action(db, current_user, "Sauvegarde BDD", f"Fichier {rec.filename}")
    return jsonify({"success": True, "filename": rec.filename, "expire_at": rec.expire_at})


@app.route('/api/dashboard/groupes', methods=['GET'])
def get_groupes():
    db = get_db()
    groups_set = set()

    # 1. Tous les groupes de la table Cours (toutes dates et tous cycles)
    for (g,) in db.query(Cours.groupe).distinct().all():
        if g:
            cleaned = clean(g)
            if cleaned:
                groups_set.add(cleaned)
                # Extrait aussi les sous-groupes individuels (ex: 'EO3G1_A' et 'EO3G1_B' depuis 'EO3G1_A  EO3G1_B')
                for part in cleaned.split():
                    p = clean(part)
                    if p:
                        groups_set.add(p)

    # 2. Groupes de la table Formations (Formation Continue)
    for (e,) in db.query(Formation.entreprise).distinct().all():
        if e:
            cleaned = clean(e)
            if cleaned:
                groups_set.add(cleaned)

    # 3. Groupes déjà référencés dans les déclarations
    for (g,) in db.query(Absence.groupe).distinct().all():
        if g:
            cleaned = clean(g)
            if cleaned:
                groups_set.add(cleaned)
    for (g,) in db.query(Retard.groupe).distinct().all():
        if g:
            cleaned = clean(g)
            if cleaned:
                groups_set.add(cleaned)
    for (g,) in db.query(ChangementSalle.groupe).distinct().all():
        if g:
            cleaned = clean(g)
            if cleaned:
                groups_set.add(cleaned)

    # Tri alphabétique naturel
    return jsonify(sorted([g for g in groups_set if g]))


@app.route('/api/dashboard/salles', methods=['GET'])
def get_salles_groupe():
    """Salles utilisées par un groupe (date affichée prioritaire, sinon historique complet)."""
    db = get_db()
    groupe = clean(request.args.get('groupe', ''))
    display_date, _ = resolve_display_date(db)

    courses = db.query(Cours).filter(Cours.date == display_date).all()
    salles = set()
    for c in courses:
        g = clean(c.groupe)
        if not g:
            continue
        # Correspondance exacte ou avec l'un des sous-groupes (ex: EO3G1_A dans 'EO3G1_A EO3G1_B')
        if not groupe or g == groupe or groupe in g.split():
            s = clean(c.salle)
            if s:
                salles.add(s)

    # Si aucune salle trouvée à cette date spécifique, chercher sur l'ensemble des plannings
    if not salles and groupe:
        for c in db.query(Cours).all():
            g = clean(c.groupe)
            if g and (g == groupe or groupe in g.split()):
                s = clean(c.salle)
                if s:
                    salles.add(s)

    return jsonify(sorted(salles))


# -----------------
# Event Routes
# -----------------
UPLOAD_EVENTS_DIR = os.path.join(STATIC_DIR, 'uploads', 'events')
os.makedirs(UPLOAD_EVENTS_DIR, exist_ok=True)


def validate_file_signature(raw_bytes, ext):
    """Valide les signatures binaires (magic bytes) contre le spoofing d'extension (OWASP A08 & A03)."""
    if not raw_bytes or len(raw_bytes) < 4:
        return False
    if ext == '.png' and raw_bytes.startswith(b'\x89PNG\r\n\x1a\n'):
        return True
    if ext in ('.jpg', '.jpeg') and raw_bytes.startswith(b'\xff\xd8'):
        return True
    if ext == '.webp' and raw_bytes.startswith(b'RIFF') and b'WEBP' in raw_bytes[:16]:
        return True
    if ext == '.pdf' and raw_bytes.startswith(b'%PDF'):
        return True
    return False


def save_event_media(file_storage):
    """Sauvegarde une image ou convertit la 1ère page d'un PDF en PNG haute résolution."""
    if not file_storage or not file_storage.filename:
        return None, None
    ext = os.path.splitext(file_storage.filename)[1].lower()
    if ext not in ('.png', '.jpg', '.jpeg', '.webp', '.pdf'):
        raise ValueError("Format non supporté. Formats acceptés : PNG, JPG, JPEG, WEBP ou PDF.")

    import uuid
    unique_id = uuid.uuid4().hex[:12]
    out_filename = f"event_{unique_id}.png"
    out_path = os.path.join(UPLOAD_EVENTS_DIR, out_filename)

    raw = file_storage.read()
    if not raw:
        raise ValueError("Le fichier téléversé est vide.")

    # Validation stricte du contenu réel vs format déclaré (OWASP A08)
    if not validate_file_signature(raw, ext):
        raise ValueError(f"Contenu de fichier non conforme au format déclaré ({ext.upper()}).")

    # Archivage automatique de sécurité pour 3 mois (90 jours)
    try:
        save_file_backup(raw, file_storage.filename, 'event_media')
    except Exception as e:
        print("[Smart ESITH] Erreur archivage backup affiche :", e)

    if ext == '.pdf':
        try:
            try:
                import pymupdf as fitz
            except ImportError:
                import fitz
            doc = fitz.open(stream=raw, filetype="pdf")
            num_pages = len(doc)
            if num_pages == 0:
                raise ValueError("Le fichier PDF ne contient aucune page.")

            from PIL import Image, ImageDraw

            if num_pages == 1:
                # 1 seule page : rendu haute définition direct
                page = doc[0]
                pix = page.get_pixmap(dpi=200)
                pix.save(out_path)
            else:
                # Multi-pages (2 pages flyer/programme, etc.) : assemblage côte-à-côte
                page_imgs = []
                for p_idx in range(min(num_pages, 4)):  # max 4 pages combinées
                    p = doc[p_idx]
                    pix = p.get_pixmap(dpi=150)
                    img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")
                    page_imgs.append(img)

                if len(page_imgs) == 2:
                    # 2 pages : disposition côte-à-côte haute définition (idéal écran TV 16:9)
                    p1, p2 = page_imgs[0], page_imgs[1]
                    target_h = max(p1.height, p2.height)
                    if p1.height != target_h:
                        p1 = p1.resize((int(p1.width * target_h / p1.height), target_h), Image.Resampling.LANCZOS)
                    if p2.height != target_h:
                        p2 = p2.resize((int(p2.width * target_h / p2.height), target_h), Image.Resampling.LANCZOS)

                    gap = 24
                    padding = 16
                    total_w = p1.width + p2.width + gap + (padding * 2)
                    total_h = target_h + (padding * 2)

                    composite = Image.new('RGB', (total_w, total_h), (245, 247, 250))
                    composite.paste(p1, (padding, padding))
                    composite.paste(p2, (padding + p1.width + gap, padding))

                    draw = ImageDraw.Draw(composite)
                    sep_x = padding + p1.width + (gap // 2)
                    draw.line([(sep_x, padding), (sep_x, padding + target_h)], fill=(210, 215, 222), width=2)
                    composite.save(out_path, format='PNG', optimize=True)
                elif len(page_imgs) == 3:
                    target_h = max(p.height for p in page_imgs)
                    resized = []
                    for p in page_imgs:
                        if p.height != target_h:
                            p = p.resize((int(p.width * target_h / p.height), target_h), Image.Resampling.LANCZOS)
                        resized.append(p)
                    gap = 20
                    padding = 12
                    total_w = sum(p.width for p in resized) + gap * (len(resized) - 1) + (padding * 2)
                    total_h = target_h + (padding * 2)
                    composite = Image.new('RGB', (total_w, total_h), (245, 247, 250))
                    curr_x = padding
                    for p in resized:
                        composite.paste(p, (curr_x, padding))
                        curr_x += p.width + gap
                    composite.save(out_path, format='PNG', optimize=True)
                else:
                    # 4 pages en grille 2x2
                    target_w = max(p.width for p in page_imgs)
                    target_h = max(p.height for p in page_imgs)
                    grid_w = target_w * 2 + 30
                    grid_h = target_h * 2 + 30
                    composite = Image.new('RGB', (grid_w, grid_h), (245, 247, 250))
                    composite.paste(page_imgs[0], (0, 0))
                    composite.paste(page_imgs[1], (target_w + 30, 0))
                    composite.paste(page_imgs[2], (0, target_h + 30))
                    composite.paste(page_imgs[3], (target_w + 30, target_h + 30))
                    composite.save(out_path, format='PNG', optimize=True)

            doc.close()
            return f"/static/uploads/events/{out_filename}", 'pdf'
        except Exception as e:
            # Fallback 1 : essayer pdf2image si installé
            try:
                from pdf2image import convert_from_bytes
                from PIL import Image
                images = convert_from_bytes(raw, dpi=150)
                if images:
                    if len(images) == 1:
                        images[0].save(out_path, format='PNG')
                    else:
                        p1, p2 = images[0], images[1]
                        target_h = max(p1.height, p2.height)
                        total_w = p1.width + p2.width + 24
                        composite = Image.new('RGB', (total_w, target_h), (245, 247, 250))
                        composite.paste(p1, (0, 0))
                        composite.paste(p2, (p1.width + 24, 0))
                        composite.save(out_path, format='PNG')
                    return f"/static/uploads/events/{out_filename}", 'pdf'
            except Exception:
                pass

            # Fallback 2 : essayer pypdfium2 si installé
            try:
                import pypdfium2 as pdfium
                from PIL import Image
                pdf = pdfium.PdfDocument(raw)
                if len(pdf) > 0:
                    page_imgs = [page.render(scale=2).to_pil() for page in [pdf[i] for i in range(min(len(pdf), 2))]]
                    if len(page_imgs) == 1:
                        page_imgs[0].save(out_path, format='PNG')
                    else:
                        p1, p2 = page_imgs[0], page_imgs[1]
                        target_h = max(p1.height, p2.height)
                        total_w = p1.width + p2.width + 24
                        composite = Image.new('RGB', (total_w, target_h), (245, 247, 250))
                        composite.paste(p1, (0, 0))
                        composite.paste(p2, (p1.width + 24, 0))
                        composite.save(out_path, format='PNG')
                    return f"/static/uploads/events/{out_filename}", 'pdf'
            except Exception:
                pass

            # Fallback 3 : Image informative garantie (ne JAMAIS servir du .pdf brut aux balises <img>)
            print(f"[Smart ESITH] Fallback image générée pour PDF (erreur rendu: {e})")
            from PIL import Image, ImageDraw
            img = Image.new('RGB', (1280, 720), (11, 79, 108))
            draw = ImageDraw.Draw(img)
            draw.rectangle([(40, 40), (1240, 680)], outline=(195, 214, 1), width=4)
            img.save(out_path, format='PNG')
            # Sauvegarder également le PDF original
            pdf_filename = f"event_{unique_id}.pdf"
            with open(os.path.join(UPLOAD_EVENTS_DIR, pdf_filename), 'wb') as f:
                f.write(raw)
            return f"/static/uploads/events/{out_filename}", 'pdf'
    else:
        try:
            from PIL import Image
            img = Image.open(io.BytesIO(raw))
            if img.mode in ('RGBA', 'LA') and ext in ('.jpg', '.jpeg'):
                bg = Image.new('RGB', img.size, (255, 255, 255))
                bg.paste(img, mask=img.split()[-1])
                img = bg
            img.save(out_path, format='PNG', optimize=True)
            return f"/static/uploads/events/{out_filename}", 'image'
        except Exception as img_err:
            # Fallback robuste sans dépendance Pillow : enregistrement direct du fichier image
            print(f"[Smart ESITH] Fallback image brute (PIL indisponible ou erreur: {img_err})")
            raw_ext = ext if ext in ('.png', '.jpg', '.jpeg', '.webp') else '.png'
            raw_filename = f"event_{unique_id}{raw_ext}"
            raw_path = os.path.join(UPLOAD_EVENTS_DIR, raw_filename)
            with open(raw_path, 'wb') as f:
                f.write(raw)
            return f"/static/uploads/events/{raw_filename}", 'image'


def event_to_dict(e):
    return {
        "id": e.id,
        "titre": clean(e.titre),
        "date": clean(e.date),
        "date_fin": clean(getattr(e, 'date_fin', None)),
        "heure_debut": clean(e.heure_debut),
        "lieu": clean(e.lieu),
        "media_path": e.media_path,
        "media_type": e.media_type,
        "mode_affichage": e.mode_affichage or 'rotation',
        "force_active": bool(e.force_active),
        "duree_affichage_sec": getattr(e, 'duree_affichage_sec', 10) or 10
    }


@app.route('/api/events', methods=['GET'])
def list_events():
    db = get_db()
    cleanup_expired_records(db)
    events = db.query(Event).filter_by(actif=True).all()
    events.sort(key=lambda e: (parse_date(e.date) or datetime.date.max, clean(e.heure_debut)))
    return jsonify([event_to_dict(e) for e in events])


@app.route('/api/events', methods=['POST'])
@jwt_required
def create_event(current_user):
    if not roles_allowed(current_user, 'DEE', 'DRE'):
        return forbidden()

    file = request.files.get('file') or request.files.get('media')
    if request.is_json:
        data = request.get_json(silent=True) or {}
    else:
        data = request.form.to_dict()

    titre = clean(data.get('titre'))
    date = normalize_date(data.get('date'))
    date_fin = normalize_date(data.get('date_fin')) if data.get('date_fin') else None
    if not titre or not date:
        return jsonify({"error": "Titre et date obligatoires"}), 400

    media_path, media_type = None, None
    if file and file.filename:
        try:
            media_path, media_type = save_event_media(file)
        except Exception as err:
            return jsonify({"error": str(err)}), 400

    mode_affichage = clean(data.get('mode_affichage')) or 'rotation'
    if mode_affichage not in ('rotation', 'fige'):
        mode_affichage = 'rotation'

    force_active = str(data.get('force_active', '')).lower() in ('true', '1', 'yes', 'on')

    try:
        duree_sec = int(data.get('duree_affichage_sec', 10))
    except (TypeError, ValueError):
        duree_sec = 10
    duree_sec = max(3, min(300, duree_sec))

    db = get_db()
    if force_active and mode_affichage == 'fige':
        db.query(Event).filter(Event.mode_affichage == 'fige').update({Event.force_active: False})

    e = Event(
        titre=titre,
        date=date,
        date_fin=date_fin,
        heure_debut=normalize_time(data.get('heure_debut')),
        lieu=clean(data.get('lieu')),
        media_path=media_path,
        media_type=media_type,
        mode_affichage=mode_affichage,
        force_active=force_active,
        duree_affichage_sec=duree_sec,
        actif=True
    )
    try:
        db.add(e)
        db.commit()
    except Exception as db_err:
        db.rollback()
        print(f"[Smart ESITH] Erreur SQL lors de l'ajout d'événement: {db_err}")
        try:
            from database import _migrate_columns
            _migrate_columns()
            db.add(e)
            db.commit()
        except Exception as retry_err:
            db.rollback()
            return jsonify({"error": f"Erreur base de données : {retry_err}"}), 500

    try:
        cleanup_expired_records(db)
    except Exception as cl_err:
        print("[Smart ESITH] Erreur nettoyage lors de création événement :", cl_err)

    try:
        log_action(db, current_user, "Création événement", f"ID {e.id}: {titre} ({date})" + (f" [Affiche: {mode_affichage}]" if media_path else ""))
    except Exception:
        pass
    return jsonify({"success": True, "id": e.id, "event": event_to_dict(e)})


@app.route('/api/events/<int:id>', methods=['PUT', 'DELETE'])
@jwt_required
def update_delete_event(current_user, id):
    if not roles_allowed(current_user, 'DEE', 'DRE'):
        return forbidden()
    db = get_db()
    e = db.query(Event).filter_by(id=id).first()
    if not e:
        return jsonify({"error": "Événement introuvable"}), 404

    if request.method == 'PUT':
        file = request.files.get('file') or request.files.get('media')
        if request.is_json:
            data = request.get_json(silent=True) or {}
        else:
            data = request.form.to_dict()

        if 'titre' in data and clean(data['titre']):
            e.titre = clean(data['titre'])
        if 'date' in data and data['date']:
            e.date = normalize_date(data['date'])
        if 'date_fin' in data:
            e.date_fin = normalize_date(data['date_fin']) if data['date_fin'] else None
        if 'duree_affichage_sec' in data:
            try:
                e.duree_affichage_sec = max(3, min(300, int(data['duree_affichage_sec'])))
            except (TypeError, ValueError):
                pass
        if 'heure_debut' in data:
            e.heure_debut = normalize_time(data['heure_debut'])
        if 'lieu' in data:
            e.lieu = clean(data['lieu'])
        if 'mode_affichage' in data and data['mode_affichage'] in ('rotation', 'fige'):
            e.mode_affichage = data['mode_affichage']
        if 'force_active' in data:
            e.force_active = str(data['force_active']).lower() in ('true', '1', 'yes', 'on')
            if e.force_active and e.mode_affichage == 'fige':
                db.query(Event).filter(Event.id != id, Event.mode_affichage == 'fige').update({Event.force_active: False})

        if file and file.filename:
            try:
                new_path, new_type = save_event_media(file)
                if e.media_path:
                    old_file = os.path.join(STATIC_DIR, e.media_path.replace('/static/', '').lstrip('/'))
                    if os.path.exists(old_file):
                        try: os.remove(old_file)
                        except Exception: pass
                e.media_path = new_path
                e.media_type = new_type
            except Exception as err:
                return jsonify({"error": str(err)}), 400
        elif str(data.get('remove_media', '')).lower() in ('true', '1', 'yes'):
            if e.media_path:
                old_file = os.path.join(STATIC_DIR, e.media_path.replace('/static/', '').lstrip('/'))
                if os.path.exists(old_file):
                    try: os.remove(old_file)
                    except Exception: pass
            e.media_path = None
            e.media_type = None

        log_action(db, current_user, "Modification événement", f"ID {id}: {e.titre}")
        db.commit()
        return jsonify({"success": True, "event": event_to_dict(e)})
    else:
        e.actif = False  # soft delete
        log_action(db, current_user, "Suppression événement", f"ID {id}: {e.titre}")
        db.commit()
        return jsonify({"success": True})


# -----------------
# Retards & Absences & Changements
# -----------------
@app.route('/api/declare-retard-absence', methods=['POST'])
@jwt_required
def declare_retard_absence(current_user):
    if not roles_allowed(current_user, 'Scolarite', 'DEE'):
        return forbidden()
    data = request.get_json(silent=True) or {}
    groupe = clean(data.get('groupe'))
    typ = clean(data.get('type')).upper()
    if not groupe or typ not in ('ABSENCE', 'RETARD'):
        return jsonify({"error": "Type (ABSENCE/RETARD) et groupe obligatoires"}), 400
    db = get_db()
    cleanup_expired_records(db)
    
    raw_date = data.get('date_debut') or data.get('date')
    date_val = normalize_date(raw_date) if raw_date else today_str()
    raw_date_fin = data.get('date_fin')
    date_fin_val = normalize_date(raw_date_fin) if raw_date_fin else None
    
    heure = normalize_time(data.get('heure')) or clean(data.get('heure'))
    prof = clean(data.get('prof'))
    motif = clean(data.get('motif'))
    
    if typ == 'ABSENCE':
        d_start = parse_date(date_val)
        d_end = parse_date(date_fin_val) if date_fin_val else None
        
        # Période multi-jours : génère un enregistrement pour chaque jour ouvrable de la plage
        if d_start and d_end and d_end > d_start:
            if (d_end - d_start).days > 90:
                return jsonify({"error": "La durée de l'absence ne peut dépasser 90 jours"}), 400
            curr = d_start
            count = 0
            while curr <= d_end:
                if curr.weekday() != 6:  # Exclut le dimanche
                    day_str = curr.strftime('%d/%m/%Y')
                    db.add(Absence(
                        prof=prof,
                        groupe=groupe,
                        date=day_str,
                        date_fin=date_fin_val,
                        heure=heure,
                        motif=motif
                    ))
                    count += 1
                curr += datetime.timedelta(days=1)
            db.commit()
            log_action(db, current_user, "Déclaration ABSENCE (période)", f"Prof: {prof}, Groupe: {groupe}, Du {date_val} au {date_fin_val}, Heure: {heure} ({count} j)")
            return jsonify({"success": True, "periode": f"Du {date_val} au {date_fin_val}", "nb_jours": count})
        else:
            db.add(Absence(
                prof=prof,
                groupe=groupe,
                date=date_val,
                date_fin=date_val,
                heure=heure,
                motif=motif
            ))
            db.commit()
            log_action(db, current_user, f"Déclaration {typ}", f"Prof: {prof}, Groupe: {groupe}, Date: {date_val}, Heure: {heure}")
            return jsonify({"success": True})
    else:
        db.add(Retard(prof=prof, groupe=groupe, date=date_val, heure_prevue=heure, duree_retard=motif))
        db.commit()
        log_action(db, current_user, f"Déclaration {typ}", f"Prof: {prof}, Groupe: {groupe}, Date: {date_val}, Heure: {heure}")
        return jsonify({"success": True})


@app.route('/api/changement-salle', methods=['POST'])
@jwt_required
def changement_salle(current_user):
    if not roles_allowed(current_user, 'Scolarite', 'DEE'):
        return forbidden()
    data = request.get_json(silent=True) or {}
    groupe = clean(data.get('groupe'))
    ancienne = clean(data.get('ancienneSalle'))
    nouvelle = clean(data.get('nouvelleSalle'))
    if not groupe or not nouvelle:
        return jsonify({"error": "Groupe et nouvelle salle obligatoires"}), 400

    db = get_db()
    cleanup_expired_records(db)
    today = today_str()
    now = datetime.datetime.now().strftime('%H:%M')
    db.add(ChangementSalle(groupe=groupe, ancienne_salle=ancienne, nouvelle_salle=nouvelle, date=today, heure_creation=now))

    # Met à jour la salle des séances concernées du jour (comparaison insensible à la casse/espaces)
    def key(s):
        return re.sub(r'\s+', '', clean(s)).lower()
    updated = 0
    courses = db.query(Cours).filter_by(date=today).all()
    for row in courses:
        row_groupes = [clean(g) for g in (row.groupe or '').split() if clean(g)]
        if clean(row.groupe) == groupe or groupe in row_groupes:
            if not ancienne or key(row.salle) == key(ancienne) or key(row.salle).endswith(key(ancienne)):
                row.salle = nouvelle
                updated += 1

    db.commit()
    log_action(db, current_user, "Changement de salle", f"Groupe: {groupe}, {ancienne or '?'} ➔ {nouvelle} ({updated} séance(s))")
    return jsonify({"success": True, "seances_modifiees": updated})


def _active_for_date(db, model):
    """Nettoie les anciennes déclarations et retourne uniquement celles du jour (ou de la date demandée)."""
    cleanup_expired_records(db)
    target_date = normalize_date(request.args['date']) if request.args.get('date') else today_str()
    return db.query(model).filter_by(actif=True, date=target_date).all()


@app.route('/api/absences', methods=['GET'])
def get_absences():
    db = get_db()
    rows = _active_for_date(db, Absence)
    return jsonify([{
        "id": a.id,
        "groupe": clean(a.groupe),
        "prof": clean(a.prof),
        "date": clean(a.date),
        "date_fin": clean(getattr(a, 'date_fin', None)) or clean(a.date),
        "heure": clean(a.heure),
        "motif": clean(a.motif)
    } for a in rows])


@app.route('/api/absences/<int:id>', methods=['DELETE'])
@jwt_required
def delete_absence(current_user, id):
    if not roles_allowed(current_user, 'Scolarite', 'DEE'):
        return forbidden()
    db = get_db()
    a = db.query(Absence).filter_by(id=id).first()
    if a:
        delete_all = request.args.get('delete_all', '').lower() in ('true', '1')
        if delete_all and getattr(a, 'date_fin', None) and a.date_fin != a.date:
            db.query(Absence).filter_by(prof=a.prof, groupe=a.groupe, date_fin=a.date_fin, actif=True).update({Absence.actif: False})
        else:
            a.actif = False
        db.commit()
        log_action(db, current_user, "Suppression absence", f"ID: {id}, Prof: {a.prof}, Groupe: {a.groupe}")
    return jsonify({"success": True})


@app.route('/api/retards', methods=['GET'])
def get_retards():
    db = get_db()
    rows = _active_for_date(db, Retard)
    return jsonify([{"id": r.id, "groupe": clean(r.groupe), "prof": clean(r.prof), "date": clean(r.date), "heure_prevue": clean(r.heure_prevue), "duree_retard": clean(r.duree_retard)} for r in rows])


@app.route('/api/retards/<int:id>', methods=['DELETE'])
@jwt_required
def delete_retard(current_user, id):
    if not roles_allowed(current_user, 'Scolarite', 'DEE'):
        return forbidden()
    db = get_db()
    r = db.query(Retard).filter_by(id=id).first()
    if r:
        r.actif = False
        db.commit()
        log_action(db, current_user, "Suppression retard", f"ID: {id}, Prof: {r.prof}, Groupe: {r.groupe}")
    return jsonify({"success": True})


@app.route('/api/changements-salle', methods=['GET'])
def get_changements():
    db = get_db()
    rows = _active_for_date(db, ChangementSalle)
    return jsonify([{"id": c.id, "groupe": clean(c.groupe), "ancienne_salle": clean(c.ancienne_salle), "nouvelle_salle": clean(c.nouvelle_salle), "date": clean(c.date), "heure": clean(c.heure_creation)} for c in rows])


@app.route('/api/changements-salle/<int:id>', methods=['DELETE'])
@jwt_required
def delete_changement(current_user, id):
    if not roles_allowed(current_user, 'Scolarite', 'DEE'):
        return forbidden()
    db = get_db()
    c = db.query(ChangementSalle).filter_by(id=id).first()
    if c:
        c.actif = False
        # Restaure l'ancienne salle sur les séances concernées
        if clean(c.ancienne_salle):
            for row in db.query(Cours).filter_by(date=c.date, groupe=c.groupe, salle=c.nouvelle_salle).all():
                row.salle = c.ancienne_salle
        db.commit()
        log_action(db, current_user, "Annulation changement de salle", f"ID: {id}, Groupe: {c.groupe}, Rétablissement: {c.ancienne_salle}")
    return jsonify({"success": True})


@app.route('/api/journal', methods=['GET'])
@jwt_required
def get_journal(current_user):
    if not roles_allowed(current_user, 'Admin'):
        return forbidden()
    db = get_db()
    logs = db.query(ActionLog).order_by(ActionLog.id.desc()).limit(200).all()
    return jsonify([
        {
            "id": l.id,
            "user": clean(l.user),
            "role": clean(l.role),
            "action": clean(l.action),
            "details": clean(l.details),
            "timestamp": clean(l.timestamp)
        }
        for l in logs
    ])


@app.route('/api/hall/date', methods=['GET'])
def get_display_date():
    db = get_db()
    d, has_today = resolve_display_date(db)
    fi_date, is_tomorrow = resolve_fi_display_date(db)
    return jsonify({
        "date_affichee": fi_date if is_tomorrow else d,
        "is_today": not is_tomorrow,
        "is_tomorrow_fi": is_tomorrow,
        "aujourdhui": today_str()
    })


# -----------------
# Template Routes
# -----------------
@app.route('/')
def hall():
    return render_template('hall.html')


@app.route('/dashboard')
@app.route('/Dashboard')
@app.route('/login')
def dashboard():
    # Dashboard React compilé (npm run build -> backend/static/dashboard)
    if os.path.exists(os.path.join(DASHBOARD_DIR, 'index.html')):
        resp = send_from_directory(DASHBOARD_DIR, 'index.html', max_age=0)
        resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        return resp
    return render_template('dashboard.html')


# =====================================================================
# Maintenance au démarrage : normalise les dates mal formatées en base
# =====================================================================
def normalize_existing_dates():
    db = SessionLocal()
    try:
        changed = 0
        for model in (Cours, Formation, Event, Absence, Retard, ChangementSalle):
            for obj in db.query(model).all():
                if parse_date(obj.date) is None:
                    nd = normalize_date(obj.date)
                    if nd and parse_date(nd) and nd != obj.date:
                        obj.date = nd
                        changed += 1
        if changed:
            db.commit()
            print(f"[Smart ESITH] {changed} date(s) normalisée(s) en base.")
    except Exception as e:
        db.rollback()
        print("[Smart ESITH] Normalisation des dates ignorée :", e)
    finally:
        db.close()


# Initialize Database
init_db()
normalize_existing_dates()
cleanup_expired_records()


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    try:
        from waitress import serve
        print(f"[Smart ESITH] Serveur Waitress démarré : http://localhost:{port}  (Hall: /  -  Dashboard: /dashboard)")
        serve(app, host='0.0.0.0', port=port, threads=8)
    except ImportError:
        app.run(host='0.0.0.0', port=port, debug=False)
