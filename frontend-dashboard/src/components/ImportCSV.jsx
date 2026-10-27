import React, { useState } from 'react';
import apiClient from '../api/apiClient';

const ImportCSV = ({ endpoint, title, typeParam }) => {
  const [file, setFile] = useState(null);
  const [message, setMessage] = useState('');

  const handleImport = async (e) => {
    e.preventDefault();
    if (!file) return;
    const formData = new FormData();
    formData.append('file', file);
    
    let url = endpoint;
    if (typeParam) url += `?type=${typeParam}`;
    
    try {
      const res = await apiClient.post(url, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      setMessage(res.data.message || 'Import réussi');
      setFile(null);
    } catch (err) {
      console.error(err);
      setMessage(err.response?.data?.error || 'Erreur lors de l\'import');
    }
  };

  return (
    <div className="card mb-3 shadow-sm">
      <div className="card-body">
        <h5 className="card-title text-primary">{title}</h5>
        <form onSubmit={handleImport} className="d-flex flex-column flex-sm-row align-items-stretch align-items-sm-center gap-3">
          <input type="file" className="form-control flex-grow-1" accept=".csv,.xlsx" onChange={(e) => setFile(e.target.files[0])} />
          <button type="submit" className="btn btn-primary text-white flex-shrink-0" disabled={!file}>Importer</button>
        </form>
        {message && <div className="mt-2 text-info">{message}</div>}
      </div>
    </div>
  );
};

export default ImportCSV;
