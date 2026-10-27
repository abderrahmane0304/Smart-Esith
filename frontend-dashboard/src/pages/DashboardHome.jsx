import React, { useContext, useState, useEffect } from 'react';
import { AuthContext } from '../context/AuthContext';
import ImportCSV from '../components/ImportCSV';
import EventList from '../components/EventList';
import apiClient from '../api/apiClient';
import '../styles/dashboard.css';

const DashboardHome = () => {
  const { user, logout } = useContext(AuthContext);
  const [groupes, setGroupes] = useState([]);
  const [message, setMessage] = useState('');
  const [messageType, setMessageType] = useState('success');
  const [activeTab, setActiveTab] = useState('accueil');
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  const selectTab = (tab) => {
    setActiveTab(tab);
    setMobileOpen(false);
  };
  const [eventListKey, setEventListKey] = useState(0);
  const [activeAlertes, setActiveAlertes] = useState({ retards: [], absences: [], salles: [] });
  
  // Forms states
  const [raData, setRaData] = useState({ type: 'ABSENCE', groupe: '', heure: '', motif: '', prof: '' });
  const [salleData, setSalleData] = useState({ groupe: '', ancienneSalle: '', nouvelleSalle: '' });
  const [eventData, setEventData] = useState({ titre: '', date: '', heure_debut: '', lieu: '' });
  const [carbone, setCarbone] = useState(0);
  const [stats, setStats] = useState(null);
  const [logs, setLogs] = useState([]);
  const [logFilter, setLogFilter] = useState('');
  const [sallesGroupe, setSallesGroupe] = useState([]);
  const [raCustomGroup, setRaCustomGroup] = useState(false);
  const [salleCustomGroup, setSalleCustomGroup] = useState(false);

  const showNotification = (text, type = 'success') => {
    setMessage(text);
    setMessageType(type);
  };

  const fetchGroupes = async () => {
    try {
      const res = await apiClient.get('/dashboard/groupes');
      setGroupes(res.data || []);
    } catch (err) {
      console.error(err);
    }
  };

  const handleGroupeSalleChange = async (groupe) => {
    setSalleData(prev => ({ ...prev, groupe }));
    if (!groupe) {
      setSallesGroupe([]);
      return;
    }
    try {
      const res = await apiClient.get(`/dashboard/salles?groupe=${encodeURIComponent(groupe)}`);
      const list = res.data || [];
      setSallesGroupe(list);
      // Auto-remplit l'ancienne salle si une seule est trouvée et le champ est vide
      if (list.length === 1 && !salleData.ancienneSalle) {
        setSalleData(prev => ({ ...prev, groupe, ancienneSalle: list[0] }));
      }
    } catch (err) {
      console.error(err);
    }
  };

  const fetchAlertes = async () => {
    try {
      const [resR, resA, resS] = await Promise.all([
        apiClient.get('/retards'),
        apiClient.get('/absences'),
        apiClient.get('/changements-salle'),
      ]);
      setActiveAlertes({
        retards: resR.data || [],
        absences: resA.data || [],
        salles: resS.data || [],
      });
    } catch (err) {
      console.error(err);
    }
  };

  const fetchStats = async () => {
    try {
      const res = await apiClient.get('/stats');
      setStats(res.data);
    } catch (err) {
      console.error(err);
    }
  };

  const fetchJournal = async () => {
    try {
      const res = await apiClient.get('/journal');
      setLogs(res.data || []);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    const fetchCarbone = async () => {
      try {
        const res = await apiClient.get('/config/carbone');
        setCarbone(res.data.empreinte_carbone || 0);
      } catch (err) {}
    };
    fetchGroupes();
    fetchCarbone();
  }, []);

  useEffect(() => {
    if (activeTab === 'alertes') {
      fetchAlertes();
      fetchGroupes();
    } else if (activeTab === 'statistiques') {
      fetchStats();
    } else if (activeTab === 'journal') {
      fetchJournal();
    }
  }, [activeTab]);

  const handleRA = async (e) => {
    e.preventDefault();
    try {
      await apiClient.post('/declare-retard-absence', raData);
      showNotification(`${raData.type === 'ABSENCE' ? 'Absence' : 'Retard'} (${raData.prof || 'Professeur'}) déclaré avec succès pour le groupe ${raData.groupe}`, 'success');
      setRaData({ ...raData, motif: '', heure: '', prof: '' });
      fetchAlertes();
    } catch (err) {
      console.error(err);
      const detail = err.response?.data?.error || err.response?.data?.message || 'Erreur lors de la déclaration';
      showNotification(detail, 'danger');
    }
  };

  const handleSalle = async (e) => {
    e.preventDefault();
    try {
      const res = await apiClient.post('/changement-salle', salleData);
      const count = res.data?.seances_modifiees || 0;
      showNotification(`Changement de salle appliqué avec succès pour ${salleData.groupe} (${count} séance(s) mise(s) à jour)`, 'success');
      setSalleData({ groupe: '', ancienneSalle: '', nouvelleSalle: '' });
      fetchAlertes();
    } catch (err) {
      console.error(err);
      const detail = err.response?.data?.error || err.response?.data?.message || 'Erreur de modification de salle';
      showNotification(detail, 'danger');
    }
  };

  const handleDeleteRetard = async (id) => {
    if (window.confirm('Supprimer ce retard ?')) {
      try {
        await apiClient.delete(`/retards/${id}`);
        showNotification('Retard supprimé avec succès', 'success');
        fetchAlertes();
      } catch (err) {
        showNotification(err.response?.data?.error || 'Erreur lors de la suppression', 'danger');
      }
    }
  };

  const handleDeleteAbsence = async (id) => {
    if (window.confirm('Supprimer cette absence ?')) {
      try {
        await apiClient.delete(`/absences/${id}`);
        showNotification('Absence supprimée avec succès', 'success');
        fetchAlertes();
      } catch (err) {
        showNotification(err.response?.data?.error || 'Erreur lors de la suppression', 'danger');
      }
    }
  };

  const handleDeleteSalle = async (id) => {
    if (window.confirm('Annuler ce changement de salle ?')) {
      try {
        await apiClient.delete(`/changements-salle/${id}`);
        showNotification('Changement de salle annulé avec succès', 'success');
        fetchAlertes();
      } catch (err) {
        showNotification(err.response?.data?.error || 'Erreur lors de l\'annulation', 'danger');
      }
    }
  };

  const handleEvent = async (e) => {
    e.preventDefault();
    try {
      await apiClient.post('/events', eventData);
      showNotification('Événement ajouté avec succès', 'success');
      setEventData({ titre: '', date: '', heure_debut: '', lieu: '' });
      setEventListKey(prev => prev + 1); // Force EventList refresh
    } catch (err) {
      console.error(err);
      showNotification(err.response?.data?.error || 'Erreur lors de l\'ajout', 'danger');
    }
  };

  const handleCarbone = async (e) => {
    e.preventDefault();
    try {
      await apiClient.post('/config/carbone', { empreinte_carbone: Number(carbone) });
      showNotification('Empreinte carbone mise à jour !', 'success');
    } catch (err) {
      showNotification(err.response?.data?.error || 'Erreur de mise à jour', 'danger');
    }
  };

  const canAccess = (roles) => roles.includes(user.role) || user.role === 'Admin';

  return (
    <div className="dash-layout">
      {/* Mobile Backdrop */}
      <div 
        className={`dash-backdrop ${mobileOpen ? 'show' : ''}`} 
        onClick={() => setMobileOpen(false)} 
        aria-hidden="true"
      />

      {/* Sidebar */}
      <aside className={`dash-sidebar ${sidebarCollapsed ? 'collapsed' : ''} ${mobileOpen ? 'mobile-open' : ''}`}>
        <div className="p-3 text-center border-bottom flex-shrink-0 bg-white position-relative">
          <div className="d-flex align-items-center justify-content-between mb-2">
            <span className="d-none d-lg-block" style={{ width: '28px' }}></span>
            <img 
              src="/static/esith-couleur-600x315-cropped-2.png" 
              alt="ESITH" 
              className="sidebar-logo mx-auto" 
              style={{ height: '65px', objectFit: 'contain', transition: 'height 0.2s' }} 
            />
            {/* Desktop collapse toggle */}
            <button 
              type="button" 
              className="sidebar-toggle-btn d-none d-lg-inline-flex" 
              onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
              title={sidebarCollapsed ? "Agrandir le menu" : "Réduire le menu"}
              aria-label={sidebarCollapsed ? "Agrandir le menu" : "Réduire le menu"}
            >
              {sidebarCollapsed ? '▶' : '◀'}
            </button>
            {/* Mobile close button */}
            <button 
              type="button" 
              className="btn-close d-lg-none" 
              onClick={() => setMobileOpen(false)}
              aria-label="Fermer le menu"
            />
          </div>
          <div className="role-badge mx-auto" style={{ width: 'fit-content' }}>{user.role}</div>
        </div>
        
        <div className="list-group list-group-flush dash-menu-list p-2 p-lg-3 gap-2">
          <button 
            onClick={() => selectTab('accueil')} 
            className={`list-group-item list-group-item-action rounded dash-menu-item ${activeTab === 'accueil' ? 'active' : ''}`}
            title="Tableau de bord"
          >
            <span className="dash-menu-icon me-2">📊</span>
            <span className="dash-menu-text">Tableau de bord</span>
          </button>
          
          {canAccess(['DEE']) && (
            <button 
              onClick={() => selectTab('planning')} 
              className={`list-group-item list-group-item-action rounded dash-menu-item ${activeTab === 'planning' ? 'active' : ''}`}
              title="Imports Plannings"
            >
              <span className="dash-menu-icon me-2">📋</span>
              <span className="dash-menu-text">Imports Plannings</span>
            </button>
          )}

          {canAccess(['Scolarite', 'DEE']) && (
            <button 
              onClick={() => selectTab('alertes')} 
              className={`list-group-item list-group-item-action rounded dash-menu-item ${activeTab === 'alertes' ? 'active' : ''}`}
              title="Alertes & Salles"
            >
              <span className="dash-menu-icon me-2">🔔</span>
              <span className="dash-menu-text">Alertes & Salles</span>
            </button>
          )}

          {canAccess(['DEE', 'DRE']) && (
            <button 
              onClick={() => selectTab('evenements')} 
              className={`list-group-item list-group-item-action rounded dash-menu-item ${activeTab === 'evenements' ? 'active' : ''}`}
              title="Événements"
            >
              <span className="dash-menu-icon me-2">📅</span>
              <span className="dash-menu-text">Événements</span>
            </button>
          )}

          {canAccess(['DRE']) && (
            <button 
              onClick={() => selectTab('re')} 
              className={`list-group-item list-group-item-action rounded dash-menu-item ${activeTab === 're' ? 'active' : ''}`}
              title="Relations Entreprises"
            >
              <span className="dash-menu-icon me-2">🏢</span>
              <span className="dash-menu-text">Relations Entreprises</span>
            </button>
          )}

          {canAccess(['FC']) && (
            <button 
              onClick={() => selectTab('fc')} 
              className={`list-group-item list-group-item-action rounded dash-menu-item ${activeTab === 'fc' ? 'active' : ''}`}
              title="Formation Continue"
            >
              <span className="dash-menu-icon me-2">📚</span>
              <span className="dash-menu-text">Formation Continue</span>
            </button>
          )}

          {user.role === 'Admin' && (
            <>
              <button 
                onClick={() => selectTab('statistiques')} 
                className={`list-group-item list-group-item-action rounded dash-menu-item ${activeTab === 'statistiques' ? 'active' : ''}`}
                title="Statistiques"
              >
                <span className="dash-menu-icon me-2">📈</span>
                <span className="dash-menu-text">Statistiques</span>
              </button>
              <button 
                onClick={() => selectTab('journal')} 
                className={`list-group-item list-group-item-action rounded dash-menu-item ${activeTab === 'journal' ? 'active' : ''}`}
                title="Journal d'actions"
              >
                <span className="dash-menu-icon me-2">📜</span>
                <span className="dash-menu-text">Journal d'actions</span>
              </button>
            </>
          )}
        </div>
        
        <div className="p-3 border-top text-center bg-white flex-shrink-0 mt-auto">
          <button 
            className="btn btn-logout w-100 rounded-pill d-flex align-items-center justify-content-center gap-2 py-2" 
            onClick={logout}
            title="Déconnexion"
          >
            <span>🚪</span>
            <span className="btn-logout-text">Déconnexion</span>
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="dash-main">
        <header className="dash-topbar">
          <div className="d-flex align-items-center gap-3">
            {/* Mobile Hamburger Button */}
            <button 
              type="button" 
              className="dash-hamburger d-lg-none" 
              onClick={() => setMobileOpen(true)}
              aria-label="Ouvrir le menu"
            >
              ☰
            </button>
            <div>
              <h2 className="dash-title mb-0 fs-4 fs-md-3">Bienvenue, {user.username} 👋</h2>
              <span className="text-muted small">
                Session active • Rôle : <strong style={{ color: '#0B4F6C' }}>{user.role}</strong>
              </span>
            </div>
          </div>
          <div className="d-flex align-items-center gap-2">
            <span className="dash-tab-badge d-none d-sm-inline-block">
              {activeTab === 'accueil' && '📊 Tableau de bord'}
              {activeTab === 'planning' && '📋 Imports Plannings'}
              {activeTab === 'alertes' && '🔔 Alertes & Salles'}
              {activeTab === 'evenements' && '📅 Événements'}
              {activeTab === 're' && '🏢 Relations Entreprises'}
              {activeTab === 'fc' && '📚 Formation Continue'}
              {activeTab === 'statistiques' && '📈 Statistiques'}
              {activeTab === 'journal' && '📜 Journal d\'actions'}
            </span>
          </div>
        </header>

        <div className="dash-scroll-content">
          {message && (
            <div
              className={`alert ${messageType === 'danger' ? 'alert-danger' : 'alert-success'} alert-dismissible fade show shadow-sm border-0`}
              style={
                messageType === 'danger'
                  ? { backgroundColor: '#f8d7da', color: '#842029', fontWeight: '600', border: '1px solid #f5c2c7' }
                  : { backgroundColor: '#D4E24C', color: '#0B4F6C', fontWeight: '600' }
              }
            >
              <span className="me-2">{messageType === 'danger' ? '⚠️' : '✅'}</span>
              {message}
              <button type="button" className="btn-close" onClick={() => setMessage('')}></button>
            </div>
          )}

          <div className="row">
          {/* ACCUEIL */}
          {activeTab === 'accueil' && (
            <div className="col-12">
              <div className="dash-card p-4 mb-4">
                <div className="card-header-accent bg-primary"></div>
                <div className="card-body">
                  <h4 className="fw-bold mb-3" style={{ color: '#0B4F6C' }}>Vue d'ensemble</h4>
                  <p className="text-muted fs-5">Sélectionnez une option dans le menu latéral pour gérer l'affichage dynamique du Hall ESITH.</p>
                </div>
              </div>

              {canAccess(['Admin', 'Scolarite', 'DRE']) && (
                <div className="dash-card p-4">
                  <div className="card-header-accent" style={{ backgroundColor: '#c3d601' }}></div>
                  <div className="card-body">
                    <h5 className="fw-bold mb-4" style={{ color: '#0B4F6C' }}>Paramètres d'affichage</h5>
                    <form onSubmit={handleCarbone} className="d-flex flex-wrap align-items-center gap-3">
                      <label className="fw-bold fs-5">Empreinte Carbone (%) :</label>
                      <input type="number" min="0" max="100" className="dash-input" style={{ width: '120px', fontSize: '1.2rem' }} value={carbone} onChange={e => setCarbone(e.target.value)} />
                      <button type="submit" className="btn-pistachio px-4 fw-bold">Mettre à jour</button>
                    </form>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* PLANNINGS */}
          {activeTab === 'planning' && canAccess(['DEE']) && (
            <div className="col-12">
              <div className="dash-card p-4">
                <div className="card-header-accent" style={{ backgroundColor: '#8e44ad' }}></div>
                <div className="card-body">
                  <h4 className="fw-bold mb-4" style={{ color: '#0B4F6C' }}>Plannings Formation Initiale</h4>
                  <ImportCSV endpoint="/dashboard/import-planning" title="Importer le fichier CSV/Excel" />
                </div>
              </div>
            </div>
          )}

          {/* ALERTES (Scolarite & DEE) */}
          {activeTab === 'alertes' && canAccess(['Scolarite', 'DEE']) && (
            <div className="col-12">
              <div className="row g-4">
                <div className="col-md-6">
                  <div className="dash-card p-4 h-100">
                    <div className="card-header-accent" style={{ backgroundColor: '#f39c12' }}></div>
                    <div className="card-body">
                      <h5 className="fw-bold mb-4" style={{ color: '#0B4F6C' }}>Déclarer Retard ou Absence</h5>
                      <form onSubmit={handleRA}>
                        <div className="mb-3">
                          <select className="dash-input w-100 form-select" value={raData.type} onChange={e=>setRaData({...raData, type: e.target.value})}>
                            <option value="ABSENCE">Absence Professeur</option>
                            <option value="RETARD">Retard Professeur</option>
                          </select>
                        </div>
                        <div className="mb-3">
                          <input type="text" className="dash-input w-100" placeholder="Nom du professeur" required value={raData.prof} onChange={e=>setRaData({...raData, prof: e.target.value})} />
                        </div>
                        <div className="mb-3">
                          {!raCustomGroup ? (
                            <select 
                              className="dash-input w-100 form-select" 
                              value={raData.groupe} 
                              onChange={e => {
                                if (e.target.value === '__custom__') {
                                  setRaCustomGroup(true);
                                  setRaData({ ...raData, groupe: '' });
                                } else {
                                  setRaData({ ...raData, groupe: e.target.value });
                                }
                              }} 
                              required
                            >
                              <option value="">Sélectionner un groupe ({groupes.length} disponibles)</option>
                              {groupes.map(g => <option key={g} value={g}>{g}</option>)}
                              <option value="__custom__">➕ Autre groupe (saisie manuelle)...</option>
                            </select>
                          ) : (
                            <div className="input-group">
                              <input 
                                type="text" 
                                className="dash-input form-control" 
                                placeholder="Nom du groupe personnalisé (ex: ITTI3G1)" 
                                value={raData.groupe} 
                                onChange={e => setRaData({ ...raData, groupe: e.target.value })} 
                                required 
                              />
                              <button 
                                type="button" 
                                className="btn btn-outline-secondary" 
                                onClick={() => { setRaCustomGroup(false); setRaData({ ...raData, groupe: '' }); }}
                                title="Revenir à la liste déroulante"
                              >
                                📋 Choisir dans la liste
                              </button>
                            </div>
                          )}
                        </div>
                        <div className="mb-3">
                          <input type="text" className="dash-input w-100" placeholder="Heure (ex: 10:00)" value={raData.heure} onChange={e=>setRaData({...raData, heure: e.target.value})} required />
                        </div>
                        <div className="mb-4">
                          <input type="text" className="dash-input w-100" placeholder="Motif ou Durée du retard" value={raData.motif} onChange={e=>setRaData({...raData, motif: e.target.value})} required />
                        </div>
                        <button type="submit" className="btn-pistachio w-100">Publier l'alerte</button>
                      </form>
                    </div>
                  </div>
                </div>
                
                <div className="col-md-6">
                  <div className="dash-card p-4 h-100">
                    <div className="card-header-accent" style={{ backgroundColor: '#145a32' }}></div>
                    <div className="card-body">
                      <h5 className="fw-bold mb-4" style={{ color: '#0B4F6C' }}>Changement de salle</h5>
                      <form onSubmit={handleSalle}>
                        <div className="mb-3">
                          {!salleCustomGroup ? (
                            <select 
                              className="dash-input w-100 form-select" 
                              value={salleData.groupe} 
                              onChange={e => {
                                if (e.target.value === '__custom__') {
                                  setSalleCustomGroup(true);
                                  setSalleData({ ...salleData, groupe: '' });
                                } else {
                                  handleGroupeSalleChange(e.target.value);
                                }
                              }} 
                              required
                            >
                              <option value="">Sélectionner le groupe concerné ({groupes.length} disponibles)</option>
                              {groupes.map(g => <option key={g} value={g}>{g}</option>)}
                              <option value="__custom__">➕ Autre groupe (saisie manuelle)...</option>
                            </select>
                          ) : (
                            <div className="input-group">
                              <input 
                                type="text" 
                                className="dash-input form-control" 
                                placeholder="Nom du groupe personnalisé (ex: ITTI3G1)" 
                                value={salleData.groupe} 
                                onChange={e => handleGroupeSalleChange(e.target.value)} 
                                required 
                              />
                              <button 
                                type="button" 
                                className="btn btn-outline-secondary" 
                                onClick={() => { setSalleCustomGroup(false); setSalleData({ ...salleData, groupe: '' }); }}
                                title="Revenir à la liste déroulante"
                              >
                                📋 Choisir dans la liste
                              </button>
                            </div>
                          )}
                        </div>
                        <div className="mb-3">
                          <input 
                            type="text" 
                            className="dash-input w-100" 
                            placeholder={sallesGroupe.length > 0 ? `Ancienne Salle (détectée : ${sallesGroupe.join(', ')})` : "Ancienne Salle"} 
                            list="anciennes-salles-list"
                            value={salleData.ancienneSalle} 
                            onChange={e => setSalleData({...salleData, ancienneSalle: e.target.value})} 
                            required 
                          />
                          <datalist id="anciennes-salles-list">
                            {sallesGroupe.map(s => <option key={s} value={s} />)}
                          </datalist>
                          {sallesGroupe.length > 0 && (
                            <div className="form-text small text-muted mt-1">
                              📍 Salle(s) programmée(s) : <strong>{sallesGroupe.join(', ')}</strong>
                            </div>
                          )}
                        </div>
                        <div className="mb-4">
                          <input type="text" className="dash-input w-100" placeholder="Nouvelle Salle" value={salleData.nouvelleSalle} onChange={e=>setSalleData({...salleData, nouvelleSalle: e.target.value})} required />
                        </div>
                        <button type="submit" className="btn-premium w-100">Appliquer le changement</button>
                      </form>
                    </div>
                  </div>
                </div>

                {/* Liste des déclarations en cours */}
                <div className="col-12 mt-3">
                  <div className="dash-card p-4">
                    <div className="card-header-accent" style={{ backgroundColor: '#2c3e50' }}></div>
                    <div className="card-body">
                      <div className="d-flex justify-content-between align-items-center mb-4">
                        <h5 className="fw-bold m-0" style={{ color: '#0B4F6C' }}>Alertes & Déclarations en cours d'affichage</h5>
                        <button type="button" className="btn btn-sm btn-outline-secondary" onClick={fetchAlertes}>
                          🔄 Rafraîchir
                        </button>
                      </div>

                      <div className="dash-alertes-grid">
                        {/* Retards */}
                        <div>
                          <h6 className="fw-bold text-warning mb-3">⏱️ Retards Professeurs ({activeAlertes.retards.length})</h6>
                          {activeAlertes.retards.length === 0 ? (
                            <p className="text-muted small">Aucun retard déclaré</p>
                          ) : (
                            <ul className="list-group list-group-flush">
                              {activeAlertes.retards.map(r => (
                                <li key={r.id} className="list-group-item d-flex justify-content-between align-items-center flex-wrap gap-2 px-0 py-2 border-bottom">
                                  <div className="text-break me-2">
                                    <span className="fw-bold">{r.prof}</span> <span className="badge bg-secondary ms-1">{r.groupe}</span>
                                    <div className="text-muted small">Heure: {r.heure_prevue} • Retard: {r.duree_retard || 'Non précisé'}</div>
                                  </div>
                                  <button className="btn btn-sm btn-outline-danger flex-shrink-0" onClick={() => handleDeleteRetard(r.id)}>Supprimer</button>
                                </li>
                              ))}
                            </ul>
                          )}
                        </div>

                        {/* Absences */}
                        <div>
                          <h6 className="fw-bold text-danger mb-3">🚫 Absences Professeurs ({activeAlertes.absences.length})</h6>
                          {activeAlertes.absences.length === 0 ? (
                            <p className="text-muted small">Aucune absence déclarée</p>
                          ) : (
                            <ul className="list-group list-group-flush">
                              {activeAlertes.absences.map(a => (
                                <li key={a.id} className="list-group-item d-flex justify-content-between align-items-center flex-wrap gap-2 px-0 py-2 border-bottom">
                                  <div className="text-break me-2">
                                    <span className="fw-bold">{a.prof}</span> <span className="badge bg-secondary ms-1">{a.groupe}</span>
                                    <div className="text-muted small">Heure: {a.heure} • Motif: {a.motif || 'Non précisé'}</div>
                                  </div>
                                  <button className="btn btn-sm btn-outline-danger flex-shrink-0" onClick={() => handleDeleteAbsence(a.id)}>Supprimer</button>
                                </li>
                              ))}
                            </ul>
                          )}
                        </div>

                        {/* Changements de Salle */}
                        <div>
                          <h6 className="fw-bold mb-3" style={{ color: '#145a32' }}>📍 Changements de Salle ({activeAlertes.salles.length})</h6>
                          {activeAlertes.salles.length === 0 ? (
                            <p className="text-muted small">Aucun changement de salle</p>
                          ) : (
                            <ul className="list-group list-group-flush">
                              {activeAlertes.salles.map(s => (
                                <li key={s.id} className="list-group-item d-flex justify-content-between align-items-center flex-wrap gap-2 px-0 py-2 border-bottom">
                                  <div className="text-break me-2">
                                    <span className="badge me-1" style={{ backgroundColor: '#145a32', color: '#ffffff' }}>{s.groupe}</span>
                                    <span className="text-decoration-line-through text-muted small">{s.ancienne_salle || s.ancienneSalle}</span>
                                    <span className="mx-1">➔</span>
                                    <span className="fw-bold" style={{ color: '#145a32' }}>{s.nouvelle_salle || s.nouvelleSalle}</span>
                                  </div>
                                  <button className="btn btn-sm btn-outline-danger flex-shrink-0" onClick={() => handleDeleteSalle(s.id)}>Annuler</button>
                                </li>
                              ))}
                            </ul>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ÉVÉNEMENTS (DEE & DRE) */}
          {activeTab === 'evenements' && canAccess(['DEE', 'DRE']) && (
            <div className="col-12">
              <div className="dash-card p-4 mb-4">
                <div className="card-header-accent" style={{ backgroundColor: '#c3d601' }}></div>
                <div className="card-body">
                  <h5 className="fw-bold mb-4" style={{ color: '#0B4F6C' }}>Créer un événement (Bandeau défilant)</h5>
                  <form onSubmit={handleEvent} className="row g-3 mb-4">
                    <div className="col-12 col-md-6">
                      <input type="text" className="dash-input w-100" placeholder="Titre de l'événement" required value={eventData.titre} onChange={e=>setEventData({...eventData, titre: e.target.value})}/>
                    </div>
                    <div className="col-12 col-sm-6 col-md-3">
                      <input type="date" className="dash-input w-100" required value={eventData.date} onChange={e=>setEventData({...eventData, date: e.target.value})}/>
                    </div>
                    <div className="col-12 col-sm-6 col-md-3">
                      <input type="time" className="dash-input w-100" value={eventData.heure_debut} onChange={e=>setEventData({...eventData, heure_debut: e.target.value})}/>
                    </div>
                    <div className="col-12 col-md-9">
                      <input type="text" className="dash-input w-100" placeholder="Lieu (Optionnel)" value={eventData.lieu} onChange={e=>setEventData({...eventData, lieu: e.target.value})}/>
                    </div>
                    <div className="col-12 col-md-3">
                      <button type="submit" className="btn-premium w-100 py-2">Ajouter</button>
                    </div>
                  </form>
                </div>
              </div>
              
              <div className="dash-card p-4">
                <div className="card-body">
                  <EventList key={eventListKey} />
                </div>
              </div>
            </div>
          )}

          {/* FC */}
          {activeTab === 'fc' && canAccess(['FC']) && (
            <div className="col-12">
              <div className="dash-card p-4">
                <div className="card-header-accent" style={{ backgroundColor: '#e74c3c' }}></div>
                <div className="card-body">
                  <h4 className="fw-bold mb-4" style={{ color: '#0B4F6C' }}>Formation Continue</h4>
                  <ImportCSV endpoint="/dashboard/import-append" typeParam="formation_continue" title="Importer le Planning FC" />
                </div>
              </div>
            </div>
          )}

          {/* RE (Relations Entreprises) */}
          {activeTab === 're' && canAccess(['DRE']) && (
            <div className="col-12">
              <div className="dash-card p-4">
                <div className="card-header-accent" style={{ backgroundColor: '#9b59b6' }}></div>
                <div className="card-body">
                  <h4 className="fw-bold mb-4" style={{ color: '#0B4F6C' }}>Relations Entreprises (Visites)</h4>
                  <ImportCSV endpoint="/dashboard/import-append" typeParam="visites" title="Importer le Planning RE" />
                </div>
              </div>
            </div>
          )}

          {/* STATISTIQUES (Admin) */}
          {activeTab === 'statistiques' && user.role === 'Admin' && (
            <div className="col-12">
              <div className="dash-card p-4 mb-4 position-relative">
                <div className="card-header-accent" style={{ backgroundColor: '#0B4F6C' }}></div>
                <div className="card-body">
                  <div className="d-flex justify-content-between align-items-center mb-4 flex-wrap gap-2">
                    <div>
                      <h4 className="fw-bold mb-1" style={{ color: '#0B4F6C' }}>Statistiques Générales</h4>
                      <p className="text-muted small mb-0">Données en temps réel de la base Smart ESITH (Date : {stats?.date || 'Aujourd\'hui'})</p>
                    </div>
                    <button type="button" className="btn btn-sm btn-outline-secondary" onClick={fetchStats}>
                      🔄 Rafraîchir
                    </button>
                  </div>

                  {stats ? (
                    <>
                      <div className="dash-kpi-grid mb-4">
                        <div className="dash-kpi-card" style={{ borderLeft: '4px solid #0B4F6C' }}>
                          <div className="text-muted small fw-bold text-uppercase">Séances Aujourd'hui</div>
                          <div className="dash-kpi-value" style={{ color: '#0B4F6C' }}>{stats.cours_aujourdhui}</div>
                        </div>
                        <div className="dash-kpi-card" style={{ borderLeft: '4px solid #34495e' }}>
                          <div className="text-muted small fw-bold text-uppercase">Total Séances Base</div>
                          <div className="dash-kpi-value text-secondary">{stats.total_cours}</div>
                        </div>
                        <div className="dash-kpi-card" style={{ borderLeft: '4px solid #c3d601' }}>
                          <div className="text-muted small fw-bold text-uppercase">Événements à Venir</div>
                          <div className="dash-kpi-value" style={{ color: '#7a8700' }}>{stats.evenements_a_venir}</div>
                        </div>
                        <div className="dash-kpi-card" style={{ borderLeft: '4px solid #e74c3c', backgroundColor: '#fdf2f2' }}>
                          <div className="text-muted small fw-bold text-uppercase">Absences Déclarées</div>
                          <div className="dash-kpi-value text-danger">{stats.absences_aujourdhui}</div>
                        </div>
                        <div className="dash-kpi-card" style={{ borderLeft: '4px solid #f39c12', backgroundColor: '#fef9ee' }}>
                          <div className="text-muted small fw-bold text-uppercase">Retards Déclarés</div>
                          <div className="dash-kpi-value text-warning">{stats.retards_aujourdhui}</div>
                        </div>
                        <div className="dash-kpi-card" style={{ borderLeft: '4px solid #145a32', backgroundColor: '#f0f9f4' }}>
                          <div className="text-muted small fw-bold text-uppercase">Changements Salle</div>
                          <div className="dash-kpi-value" style={{ color: '#145a32' }}>{stats.changements_aujourdhui}</div>
                        </div>
                      </div>

                      <div className="p-4 rounded border bg-light">
                        <h5 className="fw-bold mb-3" style={{ color: '#0B4F6C' }}>Séances du jour par Cycle / Type</h5>
                        <div className="dash-cycle-grid">
                          {stats.par_cycle && Object.entries(stats.par_cycle).map(([cycle, count]) => (
                            <div key={cycle} className="d-flex justify-content-between align-items-center p-2 bg-white rounded shadow-sm">
                              <span className="fw-bold text-truncate me-2">{cycle}</span>
                              <span className="badge bg-primary rounded-pill px-3 py-2 flex-shrink-0">{count}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    </>
                  ) : (
                    <div className="text-center py-4 text-muted">Chargement des statistiques...</div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* JOURNAL D'ACTIONS (Admin) */}
          {activeTab === 'journal' && user.role === 'Admin' && (
            <div className="col-12">
              <div className="dash-card p-4 position-relative">
                <div className="card-header-accent" style={{ backgroundColor: '#2c3e50' }}></div>
                <div className="card-body">
                  <div className="d-flex flex-wrap justify-content-between align-items-center gap-3 mb-4">
                    <div>
                      <h4 className="fw-bold mb-1" style={{ color: '#0B4F6C' }}>Journal d'actions & d'Audit</h4>
                      <p className="text-muted small mb-0">Historique des opérations effectuées sur la plateforme</p>
                    </div>
                    <div className="d-flex gap-2">
                      <input
                        type="text"
                        className="dash-input flex-grow-1"
                        style={{ maxWidth: '320px', minWidth: '160px', padding: '6px 12px' }}
                        placeholder="Filtrer les actions..."
                        value={logFilter}
                        onChange={(e) => setLogFilter(e.target.value)}
                      />
                      <button type="button" className="btn btn-sm btn-outline-secondary" onClick={fetchJournal}>
                        🔄 Rafraîchir
                      </button>
                    </div>
                  </div>

                  <div className="table-responsive" style={{ maxHeight: '550px', overflowY: 'auto' }}>
                    <table className="table table-hover align-middle mb-0">
                      <thead className="table-light sticky-top">
                        <tr>
                          <th style={{ width: '160px' }}>Date & Heure</th>
                          <th style={{ width: '140px' }}>Utilisateur</th>
                          <th style={{ width: '110px' }}>Rôle</th>
                          <th style={{ width: '220px' }}>Action</th>
                          <th>Détails</th>
                        </tr>
                      </thead>
                      <tbody>
                        {logs
                          .filter((l) => {
                            if (!logFilter) return true;
                            const term = logFilter.toLowerCase();
                            return (
                              (l.user || '').toLowerCase().includes(term) ||
                              (l.action || '').toLowerCase().includes(term) ||
                              (l.details || '').toLowerCase().includes(term) ||
                              (l.role || '').toLowerCase().includes(term)
                            );
                          })
                          .map((l) => (
                            <tr key={l.id}>
                              <td className="small text-muted">{l.timestamp}</td>
                              <td className="fw-bold">{l.user}</td>
                              <td>
                                <span className="badge bg-secondary">{l.role}</span>
                              </td>
                              <td className="fw-semibold" style={{ color: '#0B4F6C' }}>{l.action}</td>
                              <td className="small text-muted">{l.details}</td>
                            </tr>
                          ))}
                        {logs.length === 0 && (
                          <tr>
                            <td colSpan="5" className="text-center py-4 text-muted">
                              Aucune action enregistrée pour le moment.
                            </td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            </div>
          )}

          </div>
        </div>
      </main>
    </div>
  );
};

export default DashboardHome;
