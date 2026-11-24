import os
import json
import re
from sqlalchemy import create_engine, Column, Integer, String, Boolean, Text, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()

class Cours(Base):
    __tablename__ = 'cours'
    id = Column(Integer, primary_key=True, autoincrement=True)
    numDay = Column(String)
    date = Column(String, nullable=False)
    hd = Column(String)
    hf = Column(String)
    salle = Column(String)
    prof = Column(String)
    groupe = Column(String)
    module = Column(String)
    Cycle = Column(String)
    AppelFait = Column(String, default='Non')

class Formation(Base):
    __tablename__ = 'formations'
    id = Column(Integer, primary_key=True, autoincrement=True)
    titre = Column(String, nullable=False)
    date = Column(String, nullable=False)
    heure_debut = Column(String)
    heure_fin = Column(String)
    salle = Column(String)
    entreprise = Column(String)   # Entreprise / groupe / mastère concerné
    formateur = Column(String)    # Formateur / intervenant
    actif = Column(Boolean, default=True)

class Event(Base):
    __tablename__ = 'events'
    id = Column(Integer, primary_key=True, autoincrement=True)
    titre = Column(String, nullable=False)
    date = Column(String, nullable=False)
    date_fin = Column(String, nullable=True)
    heure_debut = Column(String)
    lieu = Column(String)
    media_path = Column(String)
    media_type = Column(String)
    mode_affichage = Column(String, default='rotation')
    force_active = Column(Boolean, default=False)
    duree_affichage_sec = Column(Integer, default=10)
    actif = Column(Boolean, default=True)

class PlanningImport(Base):
    """Historique et métadonnées des imports de plannings (Formation Initiale).
    Lie les professeurs et les filières actives à une période précise (semaine / mois).
    """
    __tablename__ = 'planning_imports'
    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String(255), nullable=True)
    import_date = Column(String(30), nullable=True)  # YYYY-MM-DD HH:MM:SS
    period_start = Column(String(20), nullable=True) # JJ/MM/AAAA
    period_end = Column(String(20), nullable=True)   # JJ/MM/AAAA
    period_type = Column(String(20), default='week') # 'week' ou 'month'
    professors = Column(Text, nullable=True)         # JSON string (liste de profs)
    filieres = Column(Text, nullable=True)           # JSON string (liste de filières)
    active = Column(Boolean, default=True)

class Absence(Base):
    __tablename__ = 'absences'
    id = Column(Integer, primary_key=True, autoincrement=True)
    prof = Column(String)
    groupe = Column(String)
    date = Column(String, nullable=False)
    date_fin = Column(String, nullable=True)
    heure = Column(String)
    motif = Column(String)
    actif = Column(Boolean, default=True)

class Retard(Base):
    __tablename__ = 'retards'
    id = Column(Integer, primary_key=True, autoincrement=True)
    prof = Column(String)
    groupe = Column(String)
    date = Column(String, nullable=False)
    heure_prevue = Column(String)
    heure_reelle = Column(String)
    duree_retard = Column(String)
    actif = Column(Boolean, default=True)

class ChangementSalle(Base):
    __tablename__ = 'changement_salle'
    id = Column(Integer, primary_key=True, autoincrement=True)
    groupe = Column(String)
    ancienne_salle = Column(String)
    nouvelle_salle = Column(String)
    date = Column(String, nullable=False)
    heure_creation = Column(String)
    actif = Column(Boolean, default=True)

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False)
    actif = Column(Boolean, default=True)

class ActionLog(Base):
    __tablename__ = 'action_logs'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user = Column(String, nullable=False)
    role = Column(String, nullable=False)
    action = Column(String, nullable=False)
    details = Column(String)
    timestamp = Column(String, nullable=False)

class FileBackup(Base):
    """Sauvegarde et archivage des fichiers importés (plannings, visites, affiches, bdd).
    Rétention : 3 mois (90 jours). Écrasement / suppression automatique après cette durée.
    """
    __tablename__ = 'file_backups'
    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String(255), nullable=False)        # Nom physique du fichier sur le disque
    original_name = Column(String(255), nullable=False)   # Nom d'origine uploadé
    category = Column(String(50), nullable=False)         # 'planning_fi', 'formation_continue', 'visites', 'event_media', 'database'
    file_path = Column(String(500), nullable=False)       # Chemin dans backend/backups
    file_size = Column(Integer, default=0)                # Taille en octets
    mime_type = Column(String(100), nullable=True)        # Type MIME
    created_at = Column(String(30), nullable=False)       # YYYY-MM-DD HH:MM:SS
    expire_at = Column(String(30), nullable=False)        # YYYY-MM-DD HH:MM:SS (created_at + 90 jours)


# Database Configuration
# Chemin absolu : la base est toujours celle du dossier backend, quel que soit
# le répertoire depuis lequel le serveur est lancé.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get('SMART_ESITH_DB', os.path.join(BASE_DIR, 'hall_esith_v3.db'))

# Auto-initialisation depuis le template seed si la base n'existe pas encore (nouvelle installation)
SEED_PATH = os.path.join(BASE_DIR, 'hall_esith_v3.seed.db')
if not os.path.exists(DB_PATH) and os.path.exists(SEED_PATH) and os.path.abspath(DB_PATH) != os.path.abspath(SEED_PATH):
    import shutil
    try:
        shutil.copyfile(SEED_PATH, DB_PATH)
    except Exception:
        pass

DATABASE_URL = "sqlite:///" + DB_PATH.replace('\\', '/')
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def _migrate_columns():
    """Ajoute les colonnes manquantes aux tables existantes (SQLite ne le fait pas via create_all)."""
    insp = inspect(engine)
    with engine.begin() as conn:
        for table in Base.metadata.sorted_tables:
            if not insp.has_table(table.name):
                continue
            existing = {c['name'] for c in insp.get_columns(table.name)}
            for col in table.columns:
                if col.name not in existing:
                    col_type = col.type.compile(engine.dialect)
                    conn.execute(text(f'ALTER TABLE {table.name} ADD COLUMN {col.name} {col_type}'))


def init_db():
    Base.metadata.create_all(bind=engine)
    _migrate_columns()

    # Initialize default users if table is empty
    db = SessionLocal()
    try:
        if db.query(User).count() == 0:
            import werkzeug.security as ws
            default_users = [
                User(username="scolarite", password_hash=ws.generate_password_hash("esith2024"), role="Scolarite"),
                User(username="dee", password_hash=ws.generate_password_hash("esith2024"), role="DEE"),
                User(username="dre", password_hash=ws.generate_password_hash("esith2024"), role="DRE"),
                User(username="fc", password_hash=ws.generate_password_hash("esith2024"), role="FC"),
                User(username="admin", password_hash=ws.generate_password_hash("admin2024"), role="Admin"),
            ]
            db.add_all(default_users)
            db.commit()

        # Initialiser PlanningImport si la table est vide mais des cours existent déjà
        if db.query(PlanningImport).count() == 0:
            fi_cours = db.query(Cours).filter(Cours.Cycle != 'Relations Entreprises').all()
            if fi_cours:
                import datetime
                profs_set = set()
                fils_set = set()
                dates_set = set()
                for c in fi_cours:
                    if c.prof and c.prof.strip():
                        profs_set.add(c.prof.strip())
                    if c.groupe:
                        for part in c.groupe.split():
                            m = re.match(r'^([A-Za-z&]+)', part.strip())
                            if m:
                                fils_set.add(m.group(1).upper())
                    if c.date:
                        try:
                            d = datetime.datetime.strptime(c.date, '%d/%m/%Y').date()
                            dates_set.add(d)
                        except Exception:
                            pass
                if dates_set:
                    min_d = min(dates_set)
                    max_d = max(dates_set)
                    p_type = 'month' if (max_d - min_d).days > 10 else 'week'
                    p_imp = PlanningImport(
                        filename="Import existant (initial)",
                        import_date=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        period_start=min_d.strftime('%d/%m/%Y'),
                        period_end=max_d.strftime('%d/%m/%Y'),
                        period_type=p_type,
                        professors=json.dumps(sorted(list(profs_set)), ensure_ascii=False),
                        filieres=json.dumps(sorted(list(fils_set)), ensure_ascii=False),
                        active=True
                    )
                    db.add(p_imp)
                    db.commit()
    finally:
        db.close()
