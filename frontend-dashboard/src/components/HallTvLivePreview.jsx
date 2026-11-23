import React, { useState, useEffect, useRef } from 'react';

const HallTvLivePreview = () => {
  const [iframeKey, setIframeKey] = useState(Date.now());
  const [scale, setScale] = useState(1);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  
  const containerRef = useRef(null);
  const tvMonitorRef = useRef(null);

  // Calcul dynamique de l'échelle pour afficher le 1920x1080 parfaitement
  useEffect(() => {
    const updateScale = () => {
      if (document.fullscreenElement) {
        // En plein écran navigateur : adapter en respectant le ratio 16:9
        const scaleX = window.innerWidth / 1920;
        const scaleY = window.innerHeight / 1080;
        setScale(Math.min(scaleX, scaleY));
      } else if (containerRef.current) {
        const width = containerRef.current.clientWidth;
        if (width > 0) {
          setScale(width / 1920);
        }
      }
    };

    updateScale();
    const handleResize = () => updateScale();
    window.addEventListener('resize', handleResize);

    const handleFsChange = () => {
      setIsFullscreen(Boolean(document.fullscreenElement));
      setTimeout(updateScale, 100);
    };
    document.addEventListener('fullscreenchange', handleFsChange);

    return () => {
      window.removeEventListener('resize', handleResize);
      document.removeEventListener('fullscreenchange', handleFsChange);
    };
  }, []);

  const handleRefresh = () => {
    setIsLoading(true);
    setIframeKey(Date.now());
  };

  const handleToggleFullscreen = () => {
    if (!document.fullscreenElement) {
      if (tvMonitorRef.current?.requestFullscreen) {
        tvMonitorRef.current.requestFullscreen();
      }
    } else {
      if (document.exitFullscreen) {
        document.exitFullscreen();
      }
    }
  };

  const handleOpenNewTab = () => {
    window.open('/', '_blank');
  };

  const tvHeight = Math.round(1080 * scale);
  const tvWidth = Math.round(1920 * scale);

  return (
    <div className="hall-tv-preview-page">
      {/* Barre d'en-tête */}
      <div className="dash-card p-4 mb-4">
        <div className="d-flex flex-wrap justify-content-between align-items-center gap-3">
          <div>
            <div className="d-flex align-items-center gap-2 mb-1">
              <h4 className="fw-bold mb-0" style={{ color: '#0B4F6C' }}>
                📺 Écran du Hall — Diffusion en Direct
              </h4>
              <span
                className="badge d-inline-flex align-items-center gap-1 px-3 py-1 text-uppercase"
                style={{
                  backgroundColor: '#e8f5e9',
                  color: '#2e7d32',
                  border: '1px solid #a5d6a7',
                  fontSize: '0.75rem',
                  fontWeight: 700,
                  letterSpacing: '0.5px'
                }}
              >
                <span
                  style={{
                    width: '8px',
                    height: '8px',
                    borderRadius: '50%',
                    backgroundColor: '#2e7d32',
                    display: 'inline-block',
                    boxShadow: '0 0 0 3px rgba(46, 125, 50, 0.25)'
                  }}
                />
                En direct
              </span>
            </div>
            <p className="text-muted small mb-0">
              Visualisation 1:1 en temps réel de ce qui est projeté sur le grand écran du Hall d'accueil ESITH (cours, absences, retards, changements de salle et affiches).
            </p>
          </div>

          {/* Boutons d'actions rapides */}
          <div className="d-flex align-items-center gap-2 flex-wrap">
            <button
              type="button"
              className="btn btn-sm btn-outline-secondary d-flex align-items-center gap-1 shadow-sm px-3 py-2"
              onClick={handleRefresh}
              title="Recharger le flux vidéo de l'écran Hall"
            >
              🔄 <span className="d-none d-sm-inline">Actualiser</span>
            </button>
            <button
              type="button"
              className="btn btn-sm btn-outline-primary d-flex align-items-center gap-1 shadow-sm px-3 py-2"
              onClick={handleToggleFullscreen}
              title="Agrandir en plein écran"
            >
              ⤢ <span className="d-none d-sm-inline">Plein Écran</span>
            </button>
            <button
              type="button"
              className="btn btn-sm btn-premium d-flex align-items-center gap-1 shadow-sm px-3 py-2"
              onClick={handleOpenNewTab}
              title="Ouvrir l'écran du Hall dans un nouvel onglet indépendant"
            >
              ↗️ <span>Ouvrir dans un onglet</span>
            </button>
          </div>
        </div>
      </div>

      {/* Cadre Téléviseur TV (Monitor Bezel) */}
      <div
        ref={tvMonitorRef}
        className={`tv-monitor-wrapper ${isFullscreen ? 'fullscreen-mode' : ''} mb-4`}
        style={{
          backgroundColor: '#050c18',
          borderRadius: isFullscreen ? '0px' : '16px',
          boxShadow: '0 20px 50px rgba(0, 0, 0, 0.35), 0 0 0 1px rgba(255, 255, 255, 0.1)',
          padding: isFullscreen ? '0' : '14px 14px 22px 14px',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          position: 'relative',
          transition: 'all 0.3s ease'
        }}
      >
        {/* En-tête du boîtier TV (Bezel supérieur) */}
        {!isFullscreen && (
          <div className="w-100 d-flex justify-content-between align-items-center px-3 mb-2" style={{ color: '#64748b', fontSize: '0.78rem' }}>
            <div className="d-flex align-items-center gap-2">
              <span style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: '#38bdf8', display: 'inline-block' }} />
              <span className="fw-semibold text-light font-monospace">ESITH · HALL DISPLAY TV</span>
            </div>
            <div className="d-flex align-items-center gap-3">
              <span>Full HD 1080p (Échelle: {Math.round(scale * 100)}%)</span>
              <span className="badge bg-dark border border-secondary text-light">16 : 9</span>
            </div>
          </div>
        )}

        {/* Zone de l'écran 16:9 avec iframe */}
        <div
          ref={containerRef}
          style={{
            width: isFullscreen ? `${tvWidth}px` : '100%',
            height: `${tvHeight}px`,
            position: 'relative',
            overflow: 'hidden',
            backgroundColor: '#000',
            borderRadius: isFullscreen ? '0px' : '8px',
            boxShadow: 'inset 0 0 20px rgba(0,0,0,0.8)'
          }}
        >
          {isLoading && (
            <div
              className="position-absolute top-0 start-0 w-100 h-100 d-flex flex-column align-items-center justify-content-center text-white"
              style={{ backgroundColor: 'rgba(5, 12, 24, 0.95)', zIndex: 10 }}
            >
              <div className="spinner-border text-primary mb-3" role="status" style={{ width: '3rem', height: '3rem' }}>
                <span className="visually-hidden">Chargement...</span>
              </div>
              <h6 className="fw-bold mb-1">Connexion à l'écran du Hall...</h6>
              <small className="text-white-50">Synchronisation des cours, alertes et affiches</small>
            </div>
          )}

          <iframe
            key={iframeKey}
            src="/"
            title="Écran du Hall ESITH en direct"
            onLoad={() => setIsLoading(false)}
            style={{
              width: '1920px',
              height: '1080px',
              transform: `scale(${scale})`,
              transformOrigin: 'top left',
              border: 'none',
              pointerEvents: 'auto',
              backgroundColor: '#fff'
            }}
          />
        </div>

        {/* Barre inférieure du téléviseur (LED d'alimentation et logo) */}
        {!isFullscreen && (
          <div className="w-100 d-flex justify-content-between align-items-center px-3 mt-2" style={{ color: '#475569', fontSize: '0.72rem' }}>
            <span className="text-secondary font-monospace">SMART ESITH BROADCAST SYSTEM v2.0</span>
            <div className="d-flex align-items-center gap-2">
              <span style={{ fontSize: '0.7rem', color: '#22c55e' }}>ACTIF</span>
              <span
                style={{
                  width: '7px',
                  height: '7px',
                  borderRadius: '50%',
                  backgroundColor: '#22c55e',
                  boxShadow: '0 0 6px #22c55e',
                  display: 'inline-block'
                }}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default HallTvLivePreview;
