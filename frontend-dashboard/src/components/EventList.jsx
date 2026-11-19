import React, { useState, useEffect } from 'react';
import apiClient from '../api/apiClient';
import EventTvPreview from './EventTvPreview';

const EventList = () => {
  const [events, setEvents] = useState([]);
  const [openPreviews, setOpenPreviews] = useState({});
  
  const fetchEvents = async () => {
    try {
      const res = await apiClient.get('/events');
      setEvents(res.data || []);
    } catch (err) { console.error(err); }
  };

  useEffect(() => { fetchEvents(); }, []);

  const togglePreview = (id) => {
    setOpenPreviews(prev => ({
      ...prev,
      [id]: !prev[id]
    }));
  };

  const openAllPreviews = () => {
    const all = {};
    events.forEach(e => { all[e.id] = true; });
    setOpenPreviews(all);
  };

  const closeAllPreviews = () => {
    setOpenPreviews({});
  };

  const handleDelete = async (id) => {
    if (!window.confirm("Supprimer cet événement ?")) return;
    try {
      await apiClient.delete(`/events/${id}`);
      fetchEvents();
    } catch (err) { console.error(err); }
  };

  const toggleMode = async (event) => {
    const nextMode = event.mode_affichage === 'fige' ? 'rotation' : 'fige';
    try {
      await apiClient.put(`/events/${event.id}`, { mode_affichage: nextMode });
      fetchEvents();
    } catch (err) { console.error(err); }
  };

  const toggleForceActive = async (event) => {
    try {
      await apiClient.put(`/events/${event.id}`, { force_active: !event.force_active });
      fetchEvents();
    } catch (err) { console.error(err); }
  };

  return (
    <div className="mt-2">
      {/* En-tête de la liste avec actions rapides */}
      <div className="d-flex justify-content-between align-items-center flex-wrap gap-2 mb-3">
        <div>
          <h6 className="m-0 fw-bold fs-5" style={{ color: '#0B4F6C' }}>
            Liste des Événements & Affiches Enregistrés ({events.length})
          </h6>
          <small className="text-muted">
            Masquage automatique des affiches expirées (date de fin dépassée). L'Aperçu Écran TV est accessible sous chaque événement.
          </small>
        </div>
        {events.length > 0 && (
          <div className="d-flex align-items-center gap-2">
            <button
              type="button"
              className="btn btn-sm btn-outline-secondary"
              onClick={openAllPreviews}
              title="Dérouler l'Aperçu Écran TV de tous les événements"
            >
              👁️ Tout ouvrir
            </button>
            <button
              type="button"
              className="btn btn-sm btn-outline-secondary"
              onClick={closeAllPreviews}
              title="Fermer tous les aperçus TV"
            >
              🙈 Tout fermer
            </button>
          </div>
        )}
      </div>

      {events.length === 0 ? (
        <div className="text-muted small py-4 text-center bg-light rounded border">
          Aucun événement enregistré pour le moment.
        </div>
      ) : (
        <div className="d-flex flex-column gap-3">
          {events.map(e => {
            const isOpen = Boolean(openPreviews[e.id]);
            return (
              <div
                key={e.id}
                className="card border shadow-sm rounded-3 overflow-hidden"
                style={{
                  backgroundColor: '#ffffff',
                  borderColor: isOpen ? '#c3d601' : '#e2e8f0',
                  transition: 'border-color 0.2s ease, box-shadow 0.2s ease',
                }}
              >
                <div className="card-body p-3 d-flex justify-content-between align-items-center flex-wrap gap-2">
                  <div className="text-break me-2">
                    <span className="fw-bold fs-6" style={{ color: '#0B4F6C' }}>{e.titre}</span>
                    <span className="text-muted small ms-2">
                      • {e.date}
                      {e.date_fin && e.date_fin !== e.date ? ` au ${e.date_fin}` : ''}
                      {e.heure_debut ? ` à ${e.heure_debut}` : ''} {e.lieu ? `(${e.lieu})` : ''}
                    </span>
                    
                    <div className="d-flex flex-wrap gap-1 mt-2">
                      {e.media_path ? (
                        <>
                          <span className="badge bg-primary">
                            🖼️ Affiche ({e.media_type ? e.media_type.toUpperCase() : 'IMG'})
                          </span>
                          <span className={`badge ${e.mode_affichage === 'fige' ? 'bg-danger' : 'bg-info text-dark'}`}>
                            {e.mode_affichage === 'fige' ? '📌 Figé toute la journée' : '🔄 En rotation'}
                          </span>
                          {e.force_active && (
                            <span className="badge bg-warning text-dark">
                              ⚡ Forcé en direct
                            </span>
                          )}
                          <span className="badge bg-secondary">
                            ⏱️ {e.duree_affichage_sec || 10}s
                          </span>
                        </>
                      ) : (
                        <span className="badge bg-light text-muted border">Bandeau défilant seul</span>
                      )}
                    </div>
                  </div>

                  <div className="d-flex align-items-center gap-2 flex-wrap">
                    {/* Bouton pour OUVRIR / FERMER l'Aperçu Écran TV sous cet événement */}
                    <button
                      type="button"
                      className={`btn btn-sm ${isOpen ? 'btn-pistachio text-dark fw-bold' : 'btn-outline-primary'}`}
                      onClick={() => togglePreview(e.id)}
                      title={isOpen ? "Fermer l'aperçu écran TV" : "Afficher l'aperçu écran TV sous cet événement"}
                    >
                      {isOpen ? '📺 Masquer l\'Aperçu TV ▴' : '📺 Aperçu Écran TV ▾'}
                    </button>

                    {e.media_path && (
                      <>
                        <button
                          type="button"
                          className={`btn btn-sm ${e.mode_affichage === 'fige' ? 'btn-outline-info' : 'btn-outline-secondary'}`}
                          title={e.mode_affichage === 'fige' ? 'Passer en rotation' : 'Figer toute la journée'}
                          onClick={() => toggleMode(e)}
                        >
                          {e.mode_affichage === 'fige' ? 'Basculer en Rotation' : 'Figer l\'écran'}
                        </button>
                        <button
                          type="button"
                          className={`btn btn-sm ${e.force_active ? 'btn-warning' : 'btn-outline-warning'}`}
                          title={e.force_active ? 'Désactiver le forçage' : 'Forcer l\'affichage aujourd\'hui'}
                          onClick={() => toggleForceActive(e)}
                        >
                          {e.force_active ? '⚡ Forcé ON' : '⚡ Forcer direct'}
                        </button>
                      </>
                    )}
                    <button className="btn btn-sm btn-outline-danger flex-shrink-0" onClick={() => handleDelete(e.id)}>
                      Supprimer
                    </button>
                  </div>
                </div>

                {/* APERÇU ÉCRAN TV affiché SOUS chaque événement avec possibilité de l'ouvrir ou le fermer */}
                {isOpen && (
                  <div className="px-3 pb-3 pt-0">
                    <EventTvPreview event={e} onClose={() => togglePreview(e.id)} />
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default EventList;
