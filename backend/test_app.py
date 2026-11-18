import pytest
import os
import json
import datetime
import io
import openpyxl
from app import (
    app, normalize_date, detect_cycle, init_db, SessionLocal,
    User, Cours, Event, Absence, Retard, PlanningImport, FileBackup,
    extract_filieres_from_group, get_active_planning_import,
    BACKUP_DIR, BACKUP_RETENTION_DAYS, save_file_backup,
    create_database_backup, cleanup_expired_backups
)

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


def test_re_and_fc_follow_display_date(client):
    from database import SessionLocal, Cours, Formation
    from app import CYCLE_RE, today_str
    db = SessionLocal()
    today_s = today_str()
    other_s = "01/01/2030"

    try:
        # Ajout de cours RE et Formation : 1 pour aujourd'hui, 1 pour une autre date
        c_today = Cours(date=today_s, salle="S_TODAY", groupe="__TEST_RE_TODAY__", Cycle=CYCLE_RE)
        c_other = Cours(date=other_s, salle="S_OTHER", groupe="__TEST_RE_OTHER__", Cycle=CYCLE_RE)
        f_today = Formation(titre="__TEST_FC_TODAY__", date=today_s, salle="S_FC1", actif=True)
        f_other = Formation(titre="__TEST_FC_OTHER__", date=other_s, salle="S_FC2", actif=True)
        db.add_all([c_today, c_other, f_today, f_other])
        db.commit()

        res = client.get('/api/hall/all_data')
        assert res.status_code == 200
        data = res.get_json()

        # RE doit contenir uniquement la session du jour
        re_groupes = [r['groupe'] for r in data.get('re', [])]
        assert "__TEST_RE_TODAY__" in re_groupes
        assert "__TEST_RE_OTHER__" not in re_groupes

        # FC doit contenir uniquement la formation du jour
        fc_modules = [f['module'] or f['groupe'] for f in data.get('fc', [])]
        assert "__TEST_FC_TODAY__" in fc_modules
        assert "__TEST_FC_OTHER__" not in fc_modules

    finally:
        for c in db.query(Cours).filter(Cours.groupe.in_(["__TEST_RE_TODAY__", "__TEST_RE_OTHER__"])).all():
            db.delete(c)
        for f in db.query(Formation).filter(Formation.titre.in_(["__TEST_FC_TODAY__", "__TEST_FC_OTHER__"])).all():
            db.delete(f)
        db.commit()
        db.close()


def test_event_poster_upload_and_modes(client):
    from database import SessionLocal, Event
    import io
    from PIL import Image

    # 1. Login as Admin
    login_res = client.post('/api/auth/login', json={"username": "admin", "password": "admin2024"})
    token = login_res.get_json()['token']
    auth_header = {"Authorization": f"Bearer {token}"}

    # Create dummy image
    img_byte_arr = io.BytesIO()
    img = Image.new('RGB', (800, 600), color=(11, 79, 108))
    img.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)

    event_id = None
    created_file = None
    try:
        # Création d'événement avec affiche en mode 'fige' et force_active=True
        data = {
            'titre': '__TEST_CONFERENCE_ANNUELLE__',
            'date': '15/12/2030',
            'heure_debut': '09:00',
            'lieu': 'Grand Amphi',
            'mode_affichage': 'fige',
            'force_active': 'true',
            'file': (img_byte_arr, 'affiche_test.png')
        }
        res = client.post('/api/events', data=data, content_type='multipart/form-data', headers=auth_header)
        assert res.status_code == 200, f"Error: {res.get_json()}"
        res_data = res.get_json()
        assert res_data['success'] is True
        event_id = res_data['id']

        # Vérification via GET /api/events
        list_res = client.get('/api/events')
        assert list_res.status_code == 200
        found = [e for e in list_res.get_json() if e['id'] == event_id]
        assert len(found) == 1
        ev = found[0]
        assert ev['mode_affichage'] == 'fige'
        assert ev['force_active'] is True
        assert ev['media_path'] is not None
        assert ev['media_path'].startswith('/static/uploads/events/')
        created_file = ev['media_path']

        # Vérification via /api/hall/all_data
        hall_res = client.get('/api/hall/all_data')
        assert hall_res.status_code == 200
        hall_data = hall_res.get_json()
        poster = hall_data.get('event_poster')
        assert poster is not None
        assert poster['titre'] == '__TEST_CONFERENCE_ANNUELLE__'
        assert poster['mode_affichage'] == 'fige'
        assert poster['force_active'] is True

        # Basculer en mode rotation
        put_res = client.put(f'/api/events/{event_id}', json={'mode_affichage': 'rotation'}, headers=auth_header)
        assert put_res.status_code == 200
        hall_data2 = client.get('/api/hall/all_data').get_json()
        assert hall_data2['event_poster']['mode_affichage'] == 'rotation'

        # Test upload PDF
        import fitz
        pdf_doc = fitz.open()
        pdf_page = pdf_doc.new_page(width=1920, height=1080)
        pdf_page.insert_text(fitz.Point(100, 200), "TEST PDF ESITH", fontsize=36)
        pdf_bytes = pdf_doc.tobytes()
        pdf_doc.close()

        pdf_data = {
            'titre': '__TEST_PDF_EVENT__',
            'date': '16/12/2030',
            'file': (io.BytesIO(pdf_bytes), 'programme.pdf'),
            'mode_affichage': 'rotation'
        }
        pdf_res = client.post('/api/events', data=pdf_data, content_type='multipart/form-data', headers=auth_header)
        assert pdf_res.status_code == 200
        pdf_res_data = pdf_res.get_json()
        assert pdf_res_data['success'] is True
        pdf_event_id = pdf_res_data['id']
        pdf_ev = [e for e in client.get('/api/events').get_json() if e['id'] == pdf_event_id][0]
        assert pdf_ev['media_type'] == 'pdf'
        assert pdf_ev['media_path'].endswith('.png')  # Bien converti en PNG pour la TV
        client.delete(f'/api/events/{pdf_event_id}', headers=auth_header)

    finally:
        if event_id:
            client.delete(f'/api/events/{event_id}', headers=auth_header)
        db = SessionLocal()
        for e in db.query(Event).filter(Event.titre == '__TEST_CONFERENCE_ANNUELLE__').all():
            db.delete(e)
        db.commit()
        db.close()
        if created_file:
            real_path = os.path.join(os.path.dirname(__file__), created_file.lstrip('/'))
            if os.path.exists(real_path):
                try: os.remove(real_path)
                except Exception: pass


def test_re_and_fc_only_today(client):
    from app import Cours, Formation, today_str, SessionLocal, CYCLE_RE
    db = SessionLocal()
    today = today_str()
    yesterday = (datetime.date.today() - datetime.timedelta(days=1)).strftime('%d/%m/%Y')

    # Nettoyage préalable des tests
    db.query(Cours).filter(Cours.module.in_(['__TEST_RE_TODAY__', '__TEST_RE_PAST__'])).delete()
    db.commit()

    try:
        # Visite RE aujourd'hui
        c_today = Cours(
            date=today, Cycle=CYCLE_RE, groupe='ENTREPRISE_TEST_TODAY',
            module='__TEST_RE_TODAY__', salle='SALLE_RE', hd='10:00', hf='12:00'
        )
        # Visite RE hier (ne doit JAMAIS apparaître)
        c_past = Cours(
            date=yesterday, Cycle=CYCLE_RE, groupe='ENTREPRISE_TEST_PAST',
            module='__TEST_RE_PAST__', salle='SALLE_RE', hd='10:00', hf='12:00'
        )
        db.add_all([c_today, c_past])
        db.commit()

        res = client.get('/api/hall/all_data').get_json()
        re_modules = [c['module'] for c in res.get('re', [])]
        assert '__TEST_RE_TODAY__' in re_modules
        assert '__TEST_RE_PAST__' not in re_modules

    finally:
        db.query(Cours).filter(Cours.module.in_(['__TEST_RE_TODAY__', '__TEST_RE_PAST__'])).delete()
        db.commit()
        db.close()


def test_fi_cutoff_17h30(client):
    from app import Cours, today_str, SessionLocal
    db = SessionLocal()
    today = today_str()
    tomorrow = (datetime.date.today() + datetime.timedelta(days=1)).strftime('%d/%m/%Y')

    db.query(Cours).filter(Cours.module.in_(['__TEST_FI_TODAY__', '__TEST_FI_TOMORROW__'])).delete()
    db.commit()

    try:
        c_today = Cours(
            date=today, Cycle='Licence', groupe='GCL1',
            module='__TEST_FI_TODAY__', salle='S1', hd='09:00', hf='11:00'
        )
        c_tomorrow = Cours(
            date=tomorrow, Cycle='Licence', groupe='GCL1',
            module='__TEST_FI_TOMORROW__', salle='S2', hd='08:30', hf='10:30'
        )
        db.add_all([c_today, c_tomorrow])
        db.commit()

        # Simulation 14h00 (avant 17h30) -> Affiche aujourd'hui
        res_before = client.get(f'/api/hall/all_data?date={today}&time=14:00').get_json()
        assert res_before['is_tomorrow_fi'] is False
        assert res_before['date_fi'] == today
        licence_mods_before = [c['module'] for c in res_before.get('licence', [])]
        assert '__TEST_FI_TODAY__' in licence_mods_before
        assert '__TEST_FI_TOMORROW__' not in licence_mods_before

        # Simulation 17h35 (à partir de 17h30) -> Affiche demain
        res_after = client.get(f'/api/hall/all_data?date={today}&time=17:35').get_json()
        assert res_after['is_tomorrow_fi'] is True
        assert res_after['date_fi'] == tomorrow
        licence_mods_after = [c['module'] for c in res_after.get('licence', [])]
        assert '__TEST_FI_TOMORROW__' in licence_mods_after
        assert '__TEST_FI_TODAY__' not in licence_mods_after

    finally:
        db.query(Cours).filter(Cours.module.in_(['__TEST_FI_TODAY__', '__TEST_FI_TOMORROW__'])).delete()
        db.commit()
        db.close()


def test_feature1_dynamic_excel_import_and_active_period(client):
    """Vérifie l'extraction dynamique des professeurs & filières et la règle de l'état vide."""
    # Test extraction des filières à partir de groupes variés
    assert extract_filieres_from_group("BDM2G1 BDM2G2") == {"BDM"}
    assert extract_filieres_from_group("INGTCG1.1 INGTCG1.2") == {"INGTCG"}
    assert extract_filieres_from_group("D&M1G1") == {"D&M"}
    assert extract_filieres_from_group("EO3G1_A  EO3G1_B") == {"EO"}
    assert extract_filieres_from_group("SL2G1 / SL2G2") == {"SL"}

    # Test endpoint /api/dashboard/active-period-data pour la période courante
    res = client.get('/api/dashboard/active-period-data')
    assert res.status_code == 200
    data = res.get_json()
    assert data['active'] is True
    assert data['count_professors'] > 0
    assert data['count_filieres'] > 0
    assert 'BDM' in data['filieres']
    assert isinstance(data['professors'], list)

    # Test règle Empty State : une date d'une autre période ne doit pas renvoyer d'anciennes données
    res_empty = client.get('/api/dashboard/active-period-data?date=01/01/2024')
    assert res_empty.status_code == 200
    data_empty = res_empty.get_json()
    assert data_empty['active'] is False
    assert data_empty['professors'] == []
    assert data_empty['filieres'] == []
    assert data_empty['count_professors'] == 0
    assert data_empty['count_filieres'] == 0


def test_feature2_weekly_professor_attendance_tracking_and_search(client):
    """Vérifie le calcul Schedule vs Actuals et la recherche par nom de professeur."""
    db = SessionLocal()
    test_prof = "PROF_TEST_ATTENDANCE"
    test_date1 = "16/11/2026"
    test_date2 = "17/11/2026"
    test_date3 = "18/11/2026"

    # Nettoyage initial
    db.query(Cours).filter(Cours.prof == test_prof).delete()
    db.query(Absence).filter(Absence.prof == test_prof).delete()
    db.query(Retard).filter(Retard.prof == test_prof).delete()
    db.commit()

    try:
        # Séance 1 : lundi -> Présent par défaut (aucun retard ni absence)
        c1 = Cours(date=test_date1, Cycle='Licence', prof=test_prof, groupe='CTM1G1', module='Module1', salle='S1', hd='08:30', hf='10:00')
        # Séance 2 : mardi -> avec absence enregistrée -> Absent
        c2 = Cours(date=test_date2, Cycle='Licence', prof=test_prof, groupe='CTM1G1', module='Module2', salle='S2', hd='10:15', hf='11:45')
        # Séance 3 : mercredi -> avec retard enregistré -> En retard
        c3 = Cours(date=test_date3, Cycle='Licence', prof=test_prof, groupe='CTM1G1', module='Module3', salle='S3', hd='14:00', hf='15:30')
        db.add_all([c1, c2, c3])

        # Enregistrement de l'absence pour mardi
        abs_rec = Absence(prof=test_prof, groupe='CTM1G1', date=test_date2, heure='10:15', motif='Congé maladie')
        # Enregistrement du retard pour mercredi
        ret_rec = Retard(prof=test_prof, groupe='CTM1G1', date=test_date3, heure_prevue='14:00', duree_retard='20 min')
        db.add_all([abs_rec, ret_rec])
        db.commit()

        # Recherche de l'enseignant via l'API
        res = client.get(f'/api/dashboard/attendance?prof={test_prof}&date_start=16/11/2026&date_end=21/11/2026')
        assert res.status_code == 200
        data = res.get_json()
        assert data['total_professors'] == 1
        prof_info = data['professors'][0]
        assert prof_info['prof'] == test_prof
        assert prof_info['total_sessions'] == 3
        assert prof_info['presents'] == 1
        assert prof_info['absents'] == 1
        assert prof_info['retards'] == 1

        # Vérification du résumé jour par jour
        summary = prof_info['summary_text']
        assert "Lundi: Présent" in summary
        assert "Mardi: Absent" in summary
        assert "Mercredi: En retard" in summary

    finally:
        db.query(Cours).filter(Cours.prof == test_prof).delete()
        db.query(Absence).filter(Absence.prof == test_prof).delete()
        db.query(Retard).filter(Retard.prof == test_prof).delete()
        db.commit()
        db.close()


def test_feature3_final_journal_export_excel(client):
    """Vérifie la génération et le téléchargement du journal Excel multi-feuilles."""
    res = client.get('/api/export-journal')
    assert res.status_code == 200
    assert 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' in res.headers.get('Content-Type', '')

    # Chargement du classeur Excel en mémoire
    wb = openpyxl.load_workbook(io.BytesIO(res.data))
    sheet_names = wb.sheetnames

    # Vérification stricte des 4 onglets demandés
    assert 'Profs Présents' in sheet_names
    assert 'Profs Absents' in sheet_names
    assert 'Profs en Retard' in sheet_names
    assert 'Séances Annulées' in sheet_names

    # Vérification des colonnes de chaque feuille
    ws_pres = wb['Profs Présents']
    headers_pres = [cell.value for cell in ws_pres[1]]
    assert 'Professeur' in headers_pres
    assert 'Statut' in headers_pres

    ws_abs = wb['Profs Absents']
    headers_abs = [cell.value for cell in ws_abs[1]]
    assert 'Professeur' in headers_abs
    assert 'Date' in headers_abs

    ws_ret = wb['Profs en Retard']
    headers_ret = [cell.value for cell in ws_ret[1]]
    assert 'Professeur' in headers_ret
    assert 'Durée Retard' in headers_ret

    ws_ann = wb['Séances Annulées']
    headers_ann = [cell.value for cell in ws_ann[1]]
    assert 'Professeur' in headers_ann
    assert "Motif / Raison d'annulation" in headers_ann


def test_feature4_event_posters_carousel_and_expiration(client):
    """Vérifie les affiches d'événements, le support start/end date, la durée et l'auto-masquage."""
    db = SessionLocal()
    today_d = datetime.date.today()
    today_str_val = today_d.strftime('%d/%m/%Y')
    past_d = (today_d - datetime.timedelta(days=5)).strftime('%d/%m/%Y')
    future_d = (today_d + datetime.timedelta(days=5)).strftime('%d/%m/%Y')

    test_titre_active = "__TEST_POSTER_ACTIVE__"
    test_titre_expired = "__TEST_POSTER_EXPIRED__"

    db.query(Event).filter(Event.titre.in_([test_titre_active, test_titre_expired])).delete()
    db.commit()

    try:
        # Affiche 1 : Active aujourd'hui (date de début aujourd'hui, date de fin dans 5 jours)
        e_active = Event(
            titre=test_titre_active,
            date=today_str_val,
            date_fin=future_d,
            media_path="/static/uploads/events/test_active.png",
            media_type="image",
            mode_affichage="rotation",
            duree_affichage_sec=12,
            actif=True
        )

        # Affiche 2 : Expirée (date début et fin passées depuis 5 jours)
        e_expired = Event(
            titre=test_titre_expired,
            date=past_d,
            date_fin=past_d,
            media_path="/static/uploads/events/test_expired.png",
            media_type="image",
            mode_affichage="rotation",
            duree_affichage_sec=8,
            actif=True
        )

        db.add_all([e_active, e_expired])
        db.commit()

        # Appel de l'API /api/hall/all_data
        res = client.get('/api/hall/all_data')
        assert res.status_code == 200
        data = res.get_json()

        # Vérifie que event_posters contient la liste des affiches valides
        assert 'event_posters' in data
        posters = data['event_posters']
        poster_titles = [p['titre'] for p in posters]

        # L'affiche active doit être présente avec sa durée
        assert test_titre_active in poster_titles
        active_poster_obj = next(p for p in posters if p['titre'] == test_titre_active)
        assert active_poster_obj['duree_affichage_sec'] == 12
        assert active_poster_obj['date_fin'] == future_d

        # L'affiche expirée doit être automatiquement masquée
        assert test_titre_expired not in poster_titles

    finally:
        db.query(Event).filter(Event.titre.in_([test_titre_active, test_titre_expired])).delete()
        db.commit()
        db.close()


def test_backup_retention_and_purge(client):
    """Vérifie l'archivage 3 mois (90 jours) et l'écrasement/purge automatique des fichiers expirés."""
    assert BACKUP_RETENTION_DAYS == 90
    db = SessionLocal()

    # Connexion Admin
    res_login = client.post('/api/auth/login', json={"username": "admin", "password": "admin2024"})
    assert res_login.status_code == 200
    token = res_login.get_json()['token']
    auth_header = {"Authorization": f"Bearer {token}"}

    test_content = b"TEST BACKUP FILE RETENTION 3 MOIS ESITH"
    test_orig_name = "test_planning_semaine_42.xlsx"
    created_records = []
    created_files = []

    try:
        # 1. Sauvegarde d'un fichier et vérification de la rétention 90 jours
        rec = save_file_backup(test_content, test_orig_name, "planning_fi", db)
        assert rec is not None
        assert rec.id is not None
        created_records.append(rec.id)
        assert rec.original_name == test_orig_name
        assert rec.category == "planning_fi"
        assert rec.file_size == len(test_content)

        created_dt = datetime.datetime.strptime(rec.created_at, '%Y-%m-%d %H:%M:%S')
        expire_dt = datetime.datetime.strptime(rec.expire_at, '%Y-%m-%d %H:%M:%S')
        delta_days = (expire_dt - created_dt).days
        assert delta_days == 90

        file_full_path = os.path.join(BACKUP_DIR, rec.filename)
        assert os.path.exists(file_full_path)
        created_files.append(file_full_path)
        with open(file_full_path, 'rb') as f:
            assert f.read() == test_content

        # 2. Endpoint de liste des sauvegardes GET /api/dashboard/backups
        res_list = client.get('/api/dashboard/backups', headers=auth_header)
        assert res_list.status_code == 200
        backups_data = res_list.get_json()
        target_item = next((b for b in backups_data if b['id'] == rec.id), None)
        assert target_item is not None
        assert target_item['days_remaining'] in (89, 90)
        assert 'file_size_human' in target_item

        # 3. Endpoint de téléchargement GET /api/dashboard/backups/<id>/download
        res_dl = client.get(f'/api/dashboard/backups/{rec.id}/download', headers=auth_header)
        assert res_dl.status_code == 200
        assert res_dl.data == test_content

        # 4. Instantané base de données POST /api/dashboard/backups/create-db-backup
        res_db_snap = client.post('/api/dashboard/backups/create-db-backup', headers=auth_header)
        assert res_db_snap.status_code == 200
        snap_data = res_db_snap.get_json()
        assert snap_data['success'] is True
        snap_file = os.path.join(BACKUP_DIR, snap_data['filename'])
        assert os.path.exists(snap_file)
        created_files.append(snap_file)

        # 5. Simulation d'un fichier expiré (> 3 mois / 90 jours) pour vérifier l'écrasement / suppression
        expired_filename = "planning_fi_expired_test_file.xlsx"
        expired_path = os.path.join(BACKUP_DIR, expired_filename)
        with open(expired_path, 'wb') as f:
            f.write(b"OLD EXPIRED DATA OVER 3 MONTHS")
        created_files.append(expired_path)

        old_date = datetime.datetime.now() - datetime.timedelta(days=100)
        old_expire = datetime.datetime.now() - datetime.timedelta(days=10)
        old_rec = FileBackup(
            filename=expired_filename,
            original_name="old_import.xlsx",
            category="planning_fi",
            file_path=expired_filename,
            file_size=30,
            created_at=old_date.strftime('%Y-%m-%d %H:%M:%S'),
            expire_at=old_expire.strftime('%Y-%m-%d %H:%M:%S')
        )
        db.add(old_rec)
        db.commit()
        created_records.append(old_rec.id)

        # Exécuter le nettoyage / écrasement automatique
        deleted_count = cleanup_expired_backups(db)
        assert deleted_count >= 1

        # Vérifier que le fichier expiré a été écrasé/supprimé du disque
        assert not os.path.exists(expired_path)

        # Vérifier que l'enregistrement expiré a été supprimé de la base de données
        check_db_rec = db.query(FileBackup).filter_by(id=old_rec.id).first()
        assert check_db_rec is None

        # Vérifier que le fichier actif (récent) est toujours intact et n'a pas été supprimé
        assert os.path.exists(file_full_path)
        check_active_rec = db.query(FileBackup).filter_by(id=rec.id).first()
        assert check_active_rec is not None

        # 6. Endpoint de purge manuelle POST /api/dashboard/backups/clean
        res_clean = client.post('/api/dashboard/backups/clean', headers=auth_header)
        assert res_clean.status_code == 200
        assert res_clean.get_json()['success'] is True

    finally:
        for r_id in created_records:
            try:
                db.query(FileBackup).filter_by(id=r_id).delete()
            except Exception:
                pass
        db.commit()
        db.close()
        for f_path in created_files:
            if os.path.exists(f_path):
                try:
                    os.remove(f_path)
                except Exception:
                    pass
def test_retard_duration_in_hall_data(client):
    """Vérifie que la durée de retard est bien fournie dans l'API hall pour affichage dans la pilule"""
    res_login = client.post('/api/auth/login', json={"username": "admin", "password": "admin2024"})
    token = res_login.get_json()['token']
    auth_header = {"Authorization": f"Bearer {token}"}

    today = datetime.datetime.now().strftime("%d/%m/%Y")
    payload = {
        "type": "RETARD",
        "prof": "Prof. Test Retard",
        "groupe": "CTM1G1",
        "heure": "08:30",
        "motif": "15 min",
        "date": today
    }
    res_decl = client.post('/api/declare-retard-absence', json=payload, headers=auth_header)
    assert res_decl.status_code == 200

    db = SessionLocal()
    retard_obj = db.query(Retard).filter_by(groupe="CTM1G1", date=today, actif=True).first()
    assert retard_obj is not None
    assert retard_obj.duree_retard == "15 min"
    retard_id = retard_obj.id
    db.close()

    try:
        hall_res = client.get('/api/hall/all_data')
        assert hall_res.status_code == 200
        data = hall_res.get_json()
        assert 'retards' in data
        retard_match = next((r for r in data['retards'] if r['groupe'] == 'CTM1G1'), None)
        assert retard_match is not None
        assert retard_match['duree'] == "15 min"
        assert retard_match['prof'] == "Prof. Test Retard"
    finally:
        del_res = client.delete(f'/api/retards/{retard_id}', headers=auth_header)
        assert del_res.status_code == 200


