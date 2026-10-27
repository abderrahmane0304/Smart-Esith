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

