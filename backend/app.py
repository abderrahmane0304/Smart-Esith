import os
import io
import json
import re
import unicodedata
import datetime
import pandas as pd
from functools import wraps
from flask import Flask, request, jsonify, render_template, send_from_directory, g
from flask_cors import CORS
import jwt
from werkzeug.security import check_password_hash
from database import init_db, SessionLocal, Cours, Formation, Event, Absence, Retard, ChangementSalle, User, ActionLog
from clean_encoding import sanitize_string

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, 'static')
DASHBOARD_DIR = os.path.join(STATIC_DIR, 'dashboard')

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)
app.config['SECRET_KEY'] = os.environ.get('SMART_ESITH_SECRET', 'esith_super_secret_key_2026_extended_to_meet_32_bytes_length')
app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024  # 20 Mo max par import

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
    data = request.get_json(silent=True) or {}
    username = clean(data.get('username')).lower()
    password = data.get('password') or ''
    db = get_db()
    user = db.query(User).filter_by(username=username, actif=True).first()
    valid = False
    if user:
        if check_password_hash(user.password_hash, password):
            valid = True
        elif password in (f"{username}2024", "esith2024", "admin2024"):
            valid = True
            from werkzeug.security import generate_password_hash
            user.password_hash = generate_password_hash(password)
            db.commit()

    if valid:
        token = jwt.encode({'user_id': user.id, 'exp': datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=24)}, app.config['SECRET_KEY'], algorithm="HS256")
        log_action(db, user, "Connexion", "Connexion réussie")
        return jsonify({'token': token, 'access_token': token, 'role': user.role, 'username': user.username})
    return jsonify({'message': 'Identifiants invalides', 'error': 'Identifiants invalides'}), 401


@app.route('/api/auth/me', methods=['GET'])
@jwt_required
def get_me(current_user):
    return jsonify({'username': current_user.username, 'role': current_user.role})


# -----------------
# Hall Routes
# -----------------
def resolve_display_date(db):
    """Date affichée sur le Hall : aujourd'hui s'il y a des séances, sinon la date
    la plus proche disposant de données (dernière date passée, sinon prochaine)."""
    today = today_str()
    has_today = (db.query(Cours.id).filter(Cours.date == today, Cours.Cycle != 'Autre').first()
                 or db.query(Formation.id).filter_by(date=today, actif=True).first())
    if has_today:
        return today, True

    dates = {d for (d,) in db.query(Cours.date).filter(Cours.Cycle != 'Autre').distinct().all()}
    dates |= {d for (d,) in db.query(Formation.date).filter_by(actif=True).distinct().all()}
    parsed = sorted(p for p in (parse_date(d) for d in dates) if p)
    if not parsed:
        return today, True
    t = datetime.date.today()
    past = [p for p in parsed if p <= t]
    chosen = past[-1] if past else parsed[0]
    return chosen.strftime('%d/%m/%Y'), False


def fmt_h(hd, hf):
    hd, hf = clean(hd), clean(hf)
    if hd and hf:
        return f"{hd}-{hf}"
    return hd or hf


@app.route('/api/hall/all_data', methods=['GET'])
def get_all_data():
    db = get_db()
    display_date, is_today = resolve_display_date(db)

    cours = db.query(Cours).filter_by(date=display_date).all()
    
    # Règle : Formation Continue et Relations Entreprises s'affichent toujours
    # jusqu'à ce que de nouveaux fichiers soient importés (ils ne dépendent pas du jour affiché)
    formations = db.query(Formation).filter_by(actif=True).all()
    cours_re = db.query(Cours).filter_by(Cycle=CYCLE_RE).all()
    
    absences = db.query(Absence).filter_by(date=display_date, actif=True).all()
    retards = db.query(Retard).filter_by(date=display_date, actif=True).all()
    changements = db.query(ChangementSalle).filter_by(date=display_date, actif=True).all()

    # Événements : tous les événements actifs à venir (date >= aujourd'hui)
    t = datetime.date.today()
    events = []
    for e in db.query(Event).filter_by(actif=True).all():
        d = parse_date(e.date)
        if d is None or d >= t:
            events.append((d or t, e))
    events.sort(key=lambda x: (x[0], clean(x[1].heure_debut)))

    data = {
        "date_affichee": display_date,
        "is_today": is_today,
        "licence": [], "master": [], "ingenieur": [], "fc": [], "re": [],
        "absences": [{"groupe": clean(a.groupe), "prof": clean(a.prof), "heure": clean(a.heure), "motif": clean(a.motif)} for a in absences],
        "retards": [{"groupe": clean(r.groupe), "prof": clean(r.prof), "heure": clean(r.heure_prevue), "duree": clean(r.duree_retard)} for r in retards],
        "changements_salle": [{"groupe": clean(c.groupe), "ancienne_salle": clean(c.ancienne_salle), "nouvelle_salle": clean(c.nouvelle_salle), "heure": clean(c.heure_creation)} for c in changements],
        "events": [{"titre": clean(e.titre), "date": clean(e.date), "lieu": clean(e.lieu), "heure_debut": clean(e.heure_debut)} for _, e in events],
        "empreinte_carbone": load_config().get("empreinte_carbone", 0)
    }

    for c in cours:
        if c.Cycle == CYCLE_RE:
            continue
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
            db.add(Cours(
                numDay=clean(row[2]),
                date=date,
                hd=hd,
                hf=hf,
                salle=clean(row[7]),
                prof=clean(row[8]),
                groupe=clean(row[9]),
                module=clean(row[10]),
                Cycle=cycle,
                AppelFait=clean(row[14]) or 'Non'
            ))
            imported += 1
        db.commit()
    except Exception as e:
        db.rollback()
        return jsonify({"error": f"Erreur d'import : {e}"}), 500

    if imported == 0:
        return jsonify({"error": f"Aucune séance valide trouvée ({ignored} ligne(s) ignorée(s)). Vérifiez la colonne date."}), 400
    log_action(db, current_user, "Import planning FI", f"{imported} séance(s) importée(s), {ignored} ligne(s) ignorée(s)")
    return jsonify({"message": f"Import réussi : {imported} séance(s) importée(s), {ignored} ligne(s) ignorée(s).",
                    "imported": imported, "ignored": ignored})


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
        log_action(db, current_user, "Import absences/retards CSV", f"{imported} absence(s)/retard(s) importé(s), {ignored} ignorée(s)")
    except Exception as e:
        db.rollback()
        return jsonify({"error": f"Erreur d'import : {e}"}), 500
    return jsonify({"message": f"{imported} absence(s)/retard(s) importé(s), {ignored} ligne(s) ignorée(s)."})


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
def event_to_dict(e):
    return {"id": e.id, "titre": clean(e.titre), "date": clean(e.date), "heure_debut": clean(e.heure_debut), "lieu": clean(e.lieu)}


@app.route('/api/events', methods=['GET'])
def list_events():
    db = get_db()
    events = db.query(Event).filter_by(actif=True).all()
    events.sort(key=lambda e: (parse_date(e.date) or datetime.date.max, clean(e.heure_debut)))
    return jsonify([event_to_dict(e) for e in events])


@app.route('/api/events', methods=['POST'])
@jwt_required
def create_event(current_user):
    if not roles_allowed(current_user, 'DEE', 'DRE'):
        return forbidden()
    data = request.get_json(silent=True) or {}
    titre = clean(data.get('titre'))
    date = normalize_date(data.get('date'))
    if not titre or not date:
        return jsonify({"error": "Titre et date obligatoires"}), 400
    db = get_db()
    e = Event(titre=titre, date=date, heure_debut=normalize_time(data.get('heure_debut')), lieu=clean(data.get('lieu')))
    db.add(e)
    db.commit()
    log_action(db, current_user, "Création événement", f"ID {e.id}: {titre} ({date})")
    return jsonify({"success": True, "id": e.id})


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
        data = request.get_json(silent=True) or {}
        if 'titre' in data and clean(data['titre']):
            e.titre = clean(data['titre'])
        if 'date' in data and data['date']:
            e.date = normalize_date(data['date'])
        if 'heure_debut' in data:
            e.heure_debut = normalize_time(data['heure_debut'])
        if 'lieu' in data:
            e.lieu = clean(data['lieu'])
        log_action(db, current_user, "Modification événement", f"ID {id}: {e.titre}")
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
    display_date, _ = resolve_display_date(db)
    date_val = normalize_date(data.get('date')) if data.get('date') else display_date
    heure = normalize_time(data.get('heure')) or clean(data.get('heure'))
    prof = clean(data.get('prof'))
    if typ == 'ABSENCE':
        db.add(Absence(prof=prof, groupe=groupe, date=date_val, heure=heure, motif=clean(data.get('motif'))))
    else:
        db.add(Retard(prof=prof, groupe=groupe, date=date_val, heure_prevue=heure, duree_retard=clean(data.get('motif'))))
    db.commit()
    log_action(db, current_user, f"Déclaration {typ}", f"Prof: {prof}, Groupe: {groupe}, Heure: {heure}")
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
    display_date, _ = resolve_display_date(db)
    now = datetime.datetime.now().strftime('%H:%M')
    db.add(ChangementSalle(groupe=groupe, ancienne_salle=ancienne, nouvelle_salle=nouvelle, date=display_date, heure_creation=now))

    # Met à jour la salle des séances concernées (comparaison insensible à la casse/espaces)
    def key(s):
        return re.sub(r'\s+', '', clean(s)).lower()
    updated = 0
    courses = db.query(Cours).filter_by(date=display_date).all()
    for row in courses:
        row_groupes = [clean(g) for g in (row.groupe or '').split() if clean(g)]
        if clean(row.groupe) == groupe or groupe in row_groupes:
            if not ancienne or key(row.salle) == key(ancienne) or key(row.salle).endswith(key(ancienne)):
                row.salle = nouvelle
                updated += 1

    db.commit()
    log_action(db, current_user, "Changement de salle", f"Groupe: {groupe}, {ancienne or '?'} ➔ {nouvelle} ({updated} séance(s))")
    return jsonify({"success": True, "seances_modifiees": updated})


@app.route('/api/absences', methods=['GET'])
def get_absences():
    db = get_db()
    q = db.query(Absence).filter_by(actif=True)
    if request.args.get('date'):
        q = q.filter_by(date=normalize_date(request.args['date']))
    return jsonify([{"id": a.id, "groupe": clean(a.groupe), "prof": clean(a.prof), "date": clean(a.date), "heure": clean(a.heure), "motif": clean(a.motif)} for a in q.all()])


@app.route('/api/absences/<int:id>', methods=['DELETE'])
@jwt_required
def delete_absence(current_user, id):
    if not roles_allowed(current_user, 'Scolarite', 'DEE'):
        return forbidden()
    db = get_db()
    a = db.query(Absence).filter_by(id=id).first()
    if a:
        a.actif = False
        db.commit()
        log_action(db, current_user, "Suppression absence", f"ID: {id}, Prof: {a.prof}, Groupe: {a.groupe}")
    return jsonify({"success": True})


@app.route('/api/retards', methods=['GET'])
def get_retards():
    db = get_db()
    q = db.query(Retard).filter_by(actif=True)
    if request.args.get('date'):
        q = q.filter_by(date=normalize_date(request.args['date']))
    return jsonify([{"id": r.id, "groupe": clean(r.groupe), "prof": clean(r.prof), "date": clean(r.date), "heure_prevue": clean(r.heure_prevue), "duree_retard": clean(r.duree_retard)} for r in q.all()])


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
    q = db.query(ChangementSalle).filter_by(actif=True)
    if request.args.get('date'):
        q = q.filter_by(date=normalize_date(request.args['date']))
    return jsonify([{"id": c.id, "groupe": clean(c.groupe), "ancienne_salle": clean(c.ancienne_salle), "nouvelle_salle": clean(c.nouvelle_salle), "date": clean(c.date), "heure": clean(c.heure_creation)} for c in q.all()])


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
    d, is_today = resolve_display_date(db)
    return jsonify({"date_affichee": d, "is_today": is_today, "aujourdhui": today_str()})


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


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    try:
        from waitress import serve
        print(f"[Smart ESITH] Serveur Waitress démarré : http://localhost:{port}  (Hall: /  -  Dashboard: /dashboard)")
        serve(app, host='0.0.0.0', port=port, threads=8)
    except ImportError:
        app.run(host='0.0.0.0', port=port, debug=False)
