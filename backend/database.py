import os
from sqlalchemy import create_engine, Column, Integer, String, Boolean, inspect, text
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
    heure_debut = Column(String)
    lieu = Column(String)
    actif = Column(Boolean, default=True)

class Absence(Base):
    __tablename__ = 'absences'
    id = Column(Integer, primary_key=True, autoincrement=True)
    prof = Column(String)
    groupe = Column(String)
    date = Column(String, nullable=False)
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


# Database Configuration
# Chemin absolu : la base est toujours celle du dossier backend, quel que soit
# le répertoire depuis lequel le serveur est lancé.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get('SMART_ESITH_DB', os.path.join(BASE_DIR, 'hall_esith_v3.db'))
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
    finally:
        db.close()
