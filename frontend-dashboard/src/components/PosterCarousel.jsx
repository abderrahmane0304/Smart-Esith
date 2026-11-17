import React, { useState, useEffect } from 'react';

const PosterCarousel = ({ posters = [] }) => {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(true);

  const activePosters = posters.filter(p => p.media_path);

  useEffect(() => {
    if (!isPlaying || activePosters.length <= 1) return;
    const current = activePosters[currentIndex] || {};
    const durationMs = Math.max(3000, (current.duree_affichage_sec || 10) * 1000);

    const timer = setTimeout(() => {
      setCurrentIndex((prev) => (prev + 1) % activePosters.length);
    }, durationMs);

    return () => clearTimeout(timer);
  }, [currentIndex, isPlaying, activePosters]);

  if (activePosters.length === 0) {
    return (
      <div className="p-4 text-center bg-light rounded border text-muted">
        <div style={{ fontSize: '2rem' }}>🖼️</div>
        <div className="small mt-2">Aucune affiche d'événement active pour le moment.</div>
      </div>
    );
  }

  const current = activePosters[currentIndex] || activePosters[0];

  const handlePrev = () => {
    setCurrentIndex((prev) => (prev - 1 + activePosters.length) % activePosters.length);
  };

  const handleNext = () => {
    setCurrentIndex((prev) => (prev + 1) % activePosters.length);
  };

  return (
    <div className="poster-carousel-card rounded border bg-white shadow-sm overflow-hidden mb-4">
      <div className="d-flex justify-content-between align-items-center px-3 py-2 bg-light border-bottom flex-wrap gap-2">
        <div className="d-flex align-items-center gap-2">
          <span className="badge bg-primary">Affiches Écran TV</span>
          <span className="fw-bold small" style={{ color: '#0B4F6C' }}>
            {currentIndex + 1} / {activePosters.length} — {current.titre}
          </span>
        </div>
        <div className="d-flex align-items-center gap-2">
          <button
            type="button"
            className="btn btn-sm btn-outline-secondary"
            onClick={() => setIsPlaying(!isPlaying)}
            title={isPlaying ? 'Mettre en pause' : 'Lecture automatique'}
          >
            {isPlaying ? '⏸️ Pause' : '▶️ Lecture'}
          </button>
          <button
            type="button"
            className="btn btn-sm btn-outline-dark"
            onClick={handlePrev}
            disabled={activePosters.length <= 1}
          >
            ◀
          </button>
          <button
            type="button"
            className="btn btn-sm btn-outline-dark"
            onClick={handleNext}
            disabled={activePosters.length <= 1}
          >
            ▶
          </button>
          <a
            href={current.media_path}
            target="_blank"
            rel="noopener noreferrer"
            className="btn btn-sm btn-outline-primary"
            title="Ouvrir l'affiche originale"
          >
            ⤢ Plein écran
          </a>
        </div>
      </div>

      {/* Zone d'affichage responsive avec object-fit: contain */}
      <div
        className="poster-viewport d-flex align-items-center justify-content-center p-3 position-relative"
        style={{
          minHeight: '380px',
          maxHeight: '520px',
          backgroundColor: '#0a192f',
          overflow: 'hidden',
        }}
      >
        <img
          key={current.id || current.media_path}
          src={current.media_path}
          alt={current.titre || 'Affiche événement'}
          style={{
            maxWidth: '100%',
            maxHeight: '480px',
            width: 'auto',
            height: 'auto',
            objectFit: 'contain',
            borderRadius: '10px',
            boxShadow: '0 8px 30px rgba(0, 0, 0, 0.4)',
            transition: 'opacity 0.3s ease',
          }}
        />

        {/* Indicateurs / Dots */}
        {activePosters.length > 1 && (
          <div
            className="position-absolute bottom-0 mb-3 d-flex gap-2 px-3 py-1 rounded-pill"
            style={{
              backgroundColor: 'rgba(11, 79, 108, 0.75)',
              backdropFilter: 'blur(6px)',
              zIndex: 2,
            }}
          >
            {activePosters.map((_, idx) => (
              <button
                key={idx}
                type="button"
                className="btn p-0 border-0"
                style={{
                  width: idx === currentIndex ? '22px' : '8px',
                  height: '8px',
                  borderRadius: '4px',
                  backgroundColor: idx === currentIndex ? '#c3d601' : 'rgba(255, 255, 255, 0.5)',
                  transition: 'all 0.3s ease',
                  cursor: 'pointer',
                }}
                onClick={() => setCurrentIndex(idx)}
                aria-label={`Aller à l'affiche ${idx + 1}`}
              />
            ))}
          </div>
        )}
      </div>

      {/* Informations et métadonnées de l'affiche */}
      <div className="px-3 py-2 bg-light border-top d-flex justify-content-between align-items-center flex-wrap gap-2">
        <div className="d-flex align-items-center gap-2 flex-wrap small">
          <span className="fw-semibold text-dark">
            📅 {current.date}
            {current.date_fin && current.date_fin !== current.date ? ` ➔ ${current.date_fin}` : ''}
          </span>
          {current.heure_debut && <span className="text-muted">• Heure: {current.heure_debut}</span>}
          {current.lieu && <span className="text-muted">• Lieu: {current.lieu}</span>}
          <span className="badge bg-secondary">
            ⏱️ {current.duree_affichage_sec || 10}s sur écran TV
          </span>
        </div>
        <div className="d-flex gap-1">
          <span className={`badge ${current.mode_affichage === 'fige' ? 'bg-danger' : 'bg-info text-dark'}`}>
            {current.mode_affichage === 'fige' ? '📌 Figé toute la journée' : '🔄 En rotation avec les cours'}
          </span>
          {current.force_active && <span className="badge bg-warning text-dark">⚡ Forcé en direct</span>}
        </div>
      </div>
    </div>
  );
};

export default PosterCarousel;
