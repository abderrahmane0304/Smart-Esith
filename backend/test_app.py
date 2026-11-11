import pytest
import os
import json
import datetime
from app import app, normalize_date, detect_cycle, init_db, SessionLocal, User

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['DATABASE_URL'] = "sqlite:///:memory:"
    
    # We must mock database URL inside app.py and database.py if we want true memory,
    # but since it's hardcoded to 'hall_esith_v3.db', we will just use a test db file
    if os.path.exists('test_hall.db'):
        os.remove('test_hall.db')
        
    with app.test_client() as client:
        yield client

def test_normalize_date():
    assert normalize_date("2026-09-27 10:00:00") == "27/09/2026"
    assert normalize_date("2026-09-27") == "27/09/2026"
    assert normalize_date("27/09/2026") == "27/09/2026"
    assert normalize_date("27-09-2026") == "27/09/2026"

def test_detect_cycle():
    assert detect_cycle("GCLM12", "Maths") == "Licence"
    assert detect_cycle("MDMM12", "Management") == "Master"
    assert detect_cycle("LILI12", "Dev") == "Ingénieur"
    assert detect_cycle("", "INGENIEUR 1A") == "Ingénieur"
    assert detect_cycle("", "ITTI3G1") == "Ingénieur"
    assert detect_cycle("", "Random Module") == "Autre"

def test_login_success(client):
    res = client.post('/api/auth/login', json={
        "username": "admin",
        "password": "admin2024"
    })
    assert res.status_code == 200
    data = res.get_json()
    assert 'token' in data
    assert data['role'] == 'Admin'

def test_login_failure(client):
    res = client.post('/api/auth/login', json={
        "username": "admin",
        "password": "wrongpassword"
    })
    assert res.status_code == 401
    
def test_get_all_data(client):
    res = client.get('/api/hall/all_data')
    assert res.status_code == 200
    data = res.get_json()
    assert 'licence' in data
    assert 'events' in data
    assert 'empreinte_carbone' in data

def test_access_matrix(client):
    tokens = {}
    passwords = {
        'scolarite': 'esith2024',
        'dee': 'esith2024',
        'dre': 'esith2024',
        'fc': 'esith2024',
        'admin': 'admin2024'
    }
    for user, pwd in passwords.items():
        res = client.post('/api/auth/login', json={"username": user, "password": pwd})
        assert res.status_code == 200, f"Login failed for {user}"
        tokens[user] = res.get_json()['token']

    def header(user):
        return {"Authorization": f"Bearer {tokens[user]}"}

    # 1. Déclarer retard/absence: Scolarite (OK), DEE (OK), DRE (403), FC (403), Admin (OK)
    payload_ra = {"type": "ABSENCE", "prof": "Test Prof", "groupe": "LI3G1", "heure": "08:30", "motif": "Test"}
    assert client.post('/api/declare-retard-absence', json=payload_ra, headers=header('scolarite')).status_code == 200
    assert client.post('/api/declare-retard-absence', json=payload_ra, headers=header('dee')).status_code == 200
    assert client.post('/api/declare-retard-absence', json=payload_ra, headers=header('dre')).status_code == 403
    assert client.post('/api/declare-retard-absence', json=payload_ra, headers=header('fc')).status_code == 403
    assert client.post('/api/declare-retard-absence', json=payload_ra, headers=header('admin')).status_code == 200

    # 2. Changer salle: Scolarite (OK), DEE (OK), DRE (403), FC (403), Admin (OK)
    payload_salle = {"groupe": "LI3G1", "ancienneSalle": "A1", "nouvelleSalle": "A2"}
    assert client.post('/api/changement-salle', json=payload_salle, headers=header('scolarite')).status_code == 200
    assert client.post('/api/changement-salle', json=payload_salle, headers=header('dee')).status_code == 200
    assert client.post('/api/changement-salle', json=payload_salle, headers=header('dre')).status_code == 403
    assert client.post('/api/changement-salle', json=payload_salle, headers=header('fc')).status_code == 403
    assert client.post('/api/changement-salle', json=payload_salle, headers=header('admin')).status_code == 200

    # 3. Importer planning FI: Scolarite (403), DEE (OK / file error not 403), DRE (403), FC (403), Admin (not 403)
    assert client.post('/api/dashboard/import-planning', headers=header('scolarite')).status_code == 403
    assert client.post('/api/dashboard/import-planning', headers=header('dre')).status_code == 403
    assert client.post('/api/dashboard/import-planning', headers=header('fc')).status_code == 403
    assert client.post('/api/dashboard/import-planning', headers=header('dee')).status_code != 403
    assert client.post('/api/dashboard/import-planning', headers=header('admin')).status_code != 403

    # 4. Gérer événements: Scolarite (403), DEE (OK), DRE (OK), FC (403), Admin (OK)
    payload_event = {"titre": "Conférence Test", "date": "15/10/2026", "heure_debut": "14:00", "lieu": "Amphi"}
    assert client.post('/api/events', json=payload_event, headers=header('scolarite')).status_code == 403
    assert client.post('/api/events', json=payload_event, headers=header('fc')).status_code == 403
    assert client.post('/api/events', json=payload_event, headers=header('dee')).status_code == 200
    assert client.post('/api/events', json=payload_event, headers=header('dre')).status_code == 200
    assert client.post('/api/events', json=payload_event, headers=header('admin')).status_code == 200

    # 5. Importer visites (DRE): Scolarite (403), DEE (403), DRE (not 403), FC (403), Admin (not 403)
    assert client.post('/api/dashboard/import-append?type=visites', headers=header('scolarite')).status_code == 403
    assert client.post('/api/dashboard/import-append?type=visites', headers=header('dee')).status_code == 403
    assert client.post('/api/dashboard/import-append?type=visites', headers=header('fc')).status_code == 403
    assert client.post('/api/dashboard/import-append?type=visites', headers=header('dre')).status_code != 403
    assert client.post('/api/dashboard/import-append?type=visites', headers=header('admin')).status_code != 403

    # 6. Importer FC: Scolarite (403), DEE (403), DRE (403), FC (not 403), Admin (not 403)
    assert client.post('/api/dashboard/import-append?type=formation_continue', headers=header('scolarite')).status_code == 403
    assert client.post('/api/dashboard/import-append?type=formation_continue', headers=header('dee')).status_code == 403
    assert client.post('/api/dashboard/import-append?type=formation_continue', headers=header('dre')).status_code == 403
    assert client.post('/api/dashboard/import-append?type=formation_continue', headers=header('fc')).status_code != 403
    assert client.post('/api/dashboard/import-append?type=formation_continue', headers=header('admin')).status_code != 403

    # 7. Voir statistiques: Scolarite (403), DEE (403), DRE (403), FC (403), Admin (200)
    assert client.get('/api/stats', headers=header('scolarite')).status_code == 403
    assert client.get('/api/stats', headers=header('dee')).status_code == 403
    assert client.get('/api/stats', headers=header('dre')).status_code == 403
    assert client.get('/api/stats', headers=header('fc')).status_code == 403
    assert client.get('/api/stats', headers=header('admin')).status_code == 200

    # 8. Journal d'actions: Scolarite (403), DEE (403), DRE (403), FC (403), Admin (200)
    assert client.get('/api/journal', headers=header('scolarite')).status_code == 403
    assert client.get('/api/journal', headers=header('dee')).status_code == 403
    assert client.get('/api/journal', headers=header('dre')).status_code == 403
    assert client.get('/api/journal', headers=header('fc')).status_code == 403
    res_journal = client.get('/api/journal', headers=header('admin'))
    assert res_journal.status_code == 200
    assert isinstance(res_journal.get_json(), list)
    assert len(res_journal.get_json()) > 0  # Actions were logged above!


def test_cleanup_expired_events_and_same_day_alerts(client):
    from database import Event, Absence, Retard, ChangementSalle
    today = datetime.date.today()
    today_s = today.strftime('%d/%m/%Y')
    old_event_s = (today - datetime.timedelta(days=15)).strftime('%d/%m/%Y')
    recent_event_s = (today - datetime.timedelta(days=5)).strftime('%d/%m/%Y')
    yesterday_s = (today - datetime.timedelta(days=1)).strftime('%d/%m/%Y')
    tomorrow_s = (today + datetime.timedelta(days=1)).strftime('%d/%m/%Y')

    db = SessionLocal()
    created_ids = []
    try:
        ev_old = Event(titre="__TEST_OLD_EVENT__", date=old_event_s, heure_debut="10:00", lieu="Hall")
        ev_recent = Event(titre="__TEST_RECENT_EVENT__", date=recent_event_s, heure_debut="10:00", lieu="Hall")
        abs_old = Absence(prof="__TEST_OLD_ABS__", groupe="G1", date=yesterday_s, heure="08:30", motif="Old")
        abs_today = Absence(prof="__TEST_TODAY_ABS__", groupe="G1", date=today_s, heure="08:30", motif="Today")
        ret_old = Retard(prof="__TEST_OLD_RET__", groupe="G1", date=yesterday_s, heure_prevue="09:00", duree_retard="10m")
        sal_old = ChangementSalle(groupe="__TEST_OLD_SALLE__", ancienne_salle="A1", nouvelle_salle="A2", date=yesterday_s, heure_creation="08:00")
        sal_future = ChangementSalle(groupe="__TEST_FUT_SALLE__", ancienne_salle="A1", nouvelle_salle="A3", date=tomorrow_s, heure_creation="08:00")
        db.add_all([ev_old, ev_recent, abs_old, abs_today, ret_old, sal_old, sal_future])
        db.commit()
        created_ids = [ev_old.id, ev_recent.id, abs_old.id, abs_today.id, ret_old.id, sal_old.id, sal_future.id]

        # /api/events supprime les événements > 14 jours mais garde ceux < 14 jours
        ev_res = client.get('/api/events')
        assert ev_res.status_code == 200
        titres = [e['titre'] for e in ev_res.get_json()]
        assert "__TEST_OLD_EVENT__" not in titres
        assert "__TEST_RECENT_EVENT__" in titres
        assert db.query(Event).filter_by(id=created_ids[0]).first() is None

        # /api/absences, /api/retards, /api/changements-salle suppriment < aujourd'hui et n'affichent que aujourd'hui
        abs_res = client.get('/api/absences')
        assert abs_res.status_code == 200
        profs = [a['prof'] for a in abs_res.get_json()]
        assert "__TEST_OLD_ABS__" not in profs
        assert "__TEST_TODAY_ABS__" in profs
        assert db.query(Absence).filter_by(id=created_ids[2]).first() is None

        ret_res = client.get('/api/retards')
        assert ret_res.status_code == 200
        assert "__TEST_OLD_RET__" not in [r['prof'] for r in ret_res.get_json()]
        assert db.query(Retard).filter_by(id=created_ids[4]).first() is None

        sal_res = client.get('/api/changements-salle')
        assert sal_res.status_code == 200
        groupes_salle = [s['groupe'] for s in sal_res.get_json()]
        assert "__TEST_OLD_SALLE__" not in groupes_salle
        assert "__TEST_FUT_SALLE__" not in groupes_salle  # même jour uniquement
        assert db.query(ChangementSalle).filter_by(id=created_ids[5]).first() is None
    finally:
        for model in (Event, Absence, Retard, ChangementSalle):
            for obj in db.query(model).all():
                val = getattr(obj, 'titre', None) or getattr(obj, 'prof', None) or getattr(obj, 'groupe', None)
                if str(val).startswith("__TEST_"):
                    db.delete(obj)
        db.commit()
        db.close()

