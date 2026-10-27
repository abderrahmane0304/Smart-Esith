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

  return (
    <div className="mt-4">
      <h6>Événements Actifs</h6>
      <ul className="list-group">
        {events.map(e => (
          <li key={e.id} className="list-group-item d-flex justify-content-between align-items-center flex-wrap gap-2 py-2">
            <div className="text-break me-2">
              <span className="fw-semibold">{e.titre}</span>
              <span className="text-muted small ms-2">• {e.date} {e.heure_debut ? `à ${e.heure_debut}` : ''}</span>
            </div>
            <button className="btn btn-sm btn-outline-danger flex-shrink-0" onClick={() => handleDelete(e.id)}>Supprimer</button>
          </li>
        ))}
      </ul>
    </div>
  );
};

export default EventList;
