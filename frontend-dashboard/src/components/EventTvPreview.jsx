import React from 'react';

const EventTvPreview = ({ event, onClose }) => {
  if (!event) return null;

  return (
    <div
      className="tv-preview-panel mt-3 rounded-3 overflow-hidden border border-secondary shadow-lg"
      style={{ backgroundColor: '#0a192f', color: '#fff' }}
    >
      {/* Barre d'en-tête de l'aperçu TV */}
      <div
        className="d-flex justify-content-between align-items-center px-3 py-2 border-bottom border-secondary flex-wrap gap-2"
        style={{ backgroundColor: '#0d223f' }}
      >
        <div className="d-flex align-items-center gap-2">
          <span className="badge" style={{ backgroundColor: '#c3d601', color: '#0B4F6C', fontWeight: 800 }}>
            📺 APERÇU ÉCRAN TV
          </span>
          <span className="fw-bold small text-white">
            {event.titre}
          </span>
        </div>
        <div className="d-flex align-items-center gap-2 flex-wrap">
          <span className={`badge ${event.mode_affichage === 'fige' ? 'bg-danger' : 'bg-info text-dark'}`}>
            {event.mode_affichage === 'fige' ? '📌 Mode Figé toute la journée' : `🔄 En rotation (${event.duree_affichage_sec || 10}s)`}
          </span>
          {event.force_active && <span className="badge bg-warning text-dark">⚡ Forcé en direct</span>}
          {event.media_path && (
            <a
              href={event.media_path}
              target="_blank"
              rel="noopener noreferrer"
              className="btn btn-sm btn-outline-light py-0 px-2 small"
              title="Ouvrir l'affiche originale en plein écran"
            >
              ⤢ Plein écran
            </a>
          )}
          {onClose && (
            <button
              type="button"
              className="btn btn-sm btn-light py-0 px-2 small fw-bold text-dark"
              onClick={onClose}
              title="Fermer cet aperçu TV"
            >
              ✖ Fermer
            </button>
          )}
        </div>
      </div>

      {/* Cadre de visualisation TV (16:9 / Plein écran) */}
      {event.media_path ? (
        <div
          className="d-flex align-items-center justify-content-center p-3 position-relative"
          style={{
            minHeight: '340px',
            maxHeight: '480px',
            backgroundColor: '#050c18',
            overflow: 'hidden',
          }}
        >
          <img
            src={event.media_path}
            alt={event.titre || 'Affiche événement'}
            style={{
              maxWidth: '100%',
              maxHeight: '450px',
              width: 'auto',
              height: 'auto',
              objectFit: 'contain',
              borderRadius: '8px',
              boxShadow: '0 8px 32px rgba(0, 0, 0, 0.6)',
              border: '1px solid rgba(255, 255, 255, 0.1)',
            }}
          />
        </div>
      ) : (
        <div className="p-4 text-center" style={{ backgroundColor: '#050c18' }}>
          <div className="text-white-50 small mb-2">
            Cet événement n'a pas d'affiche graphique et est diffusé sur le bandeau défilant du Hall :
          </div>
          <div
            className="p-3 rounded text-uppercase fw-bold shadow-sm"
            style={{
              backgroundColor: '#c3d601',
              color: '#0B4F6C',
              letterSpacing: '0.8px',
              fontSize: '1.05rem',
              display: 'inline-block',
              maxWidth: '90%',
            }}
          >
            📢 {event.titre} • {event.date}
            {event.date_fin && event.date_fin !== event.date ? ` au ${event.date_fin}` : ''}
            {event.heure_debut ? ` à ${event.heure_debut}` : ''} {event.lieu ? `(${event.lieu})` : ''}
          </div>
        </div>
      )}

      {/* Barre d'informations au bas du téléviseur */}
      <div
        className="px-3 py-2 border-top border-secondary d-flex justify-content-between align-items-center flex-wrap gap-2 text-white-50 small"
        style={{ backgroundColor: '#0d223f' }}
      >
        <div>
          📅 Dates : <strong className="text-white">{event.date}{event.date_fin && event.date_fin !== event.date ? ` au ${event.date_fin}` : ''}</strong>
          {event.heure_debut && <span> • Horaire : <strong className="text-white">{event.heure_debut}</strong></span>}
          {event.lieu && <span> • Salle/Lieu : <strong className="text-white">{event.lieu}</strong></span>}
        </div>
        <div className="d-flex align-items-center gap-2">
          <span>
            Diffusion Écran Hall :{' '}
            <strong className="text-warning">
              {event.media_path ? `${event.duree_affichage_sec || 10}s sur écran TV` : 'Bandeau ticker seul'}
            </strong>
          </span>
        </div>
      </div>
    </div>
  );
};

export default EventTvPreview;
