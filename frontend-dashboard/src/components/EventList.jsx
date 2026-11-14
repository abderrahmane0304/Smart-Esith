import React, { useState, useEffect } from 'react';
import apiClient from '../api/apiClient';

const EventList = () => {
  const [events, setEvents] = useState([]);
  
  const fetchEvents = async () => {
    try {
      const res = await apiClient.get('/events');
      setEvents(res.data);
    } catch (err) { console.error(err); }
  };

  useEffect(() => { fetchEvents(); }, []);

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
    <div className="mt-4">
      <div className="d-flex justify-content-between align-items-baseline flex-wrap gap-2 mb-2">
        <h6 className="m-0 fw-bold" style={{ color: '#0B4F6C' }}>Événements & Affiches d'Accueil Actifs</h6>
        <small className="text-muted">Suppression automatique 2 semaines après la date</small>
      </div>
      {events.length === 0 ? (
        <div className="text-muted small py-3">Aucun événement enregistré.</div>
      ) : (
        <ul className="list-group">
          {events.map(e => (
            <li key={e.id} className="list-group-item d-flex justify-content-between align-items-center flex-wrap gap-2 py-2">
              <div className="text-break me-2">
                <span className="fw-semibold">{e.titre}</span>
                <span className="text-muted small ms-2">• {e.date} {e.heure_debut ? `à ${e.heure_debut}` : ''} {e.lieu ? `(${e.lieu})` : ''}</span>
                
                <div className="d-flex flex-wrap gap-1 mt-1">
                  {e.media_path ? (
                    <>
                      <a href={e.media_path} target="_blank" rel="noopener noreferrer" className="badge bg-primary text-decoration-none">
                        👁️ Voir l'affiche ({e.media_type ? e.media_type.toUpperCase() : 'IMG'})
                      </a>
                      <span className={`badge ${e.mode_affichage === 'fige' ? 'bg-danger' : 'bg-info text-dark'}`}>
                        {e.mode_affichage === 'fige' ? '📌 Figé toute la journée' : '🔄 En rotation'}
                      </span>
                      {e.force_active && (
                        <span className="badge bg-warning text-dark">
                          ⚡ Forcé en direct
                        </span>
                      )}
                    </>
                  ) : (
                    <span className="badge bg-light text-muted border">Bandeau défilant seul</span>
                  )}
                </div>
              </div>

              <div className="d-flex align-items-center gap-1 flex-wrap">
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
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

export default EventList;
