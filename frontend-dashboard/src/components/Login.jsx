import React, { useState, useContext } from 'react';
import { AuthContext } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';

const Login = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const { login } = useContext(AuthContext);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await login(username, password);
      navigate('/dashboard');
    } catch (err) {
      console.error(err);
      setError('Identifiants invalides');
    }
  };

  return (
    <div className="login-container">
      <div className="login-card">
        <img 
          src="/static/esith-couleur-600x315-cropped-2.png" 
          alt="ESITH" 
          style={{ height: '70px', marginBottom: '20px', objectFit: 'contain' }} 
        />
        <h2>Connexion Smart ESITH</h2>
        {error && <p style={{ color: 'red' }}>{error}</p>}
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <input 
              type="text" 
              className="form-control" 
              placeholder="Nom d'utilisateur" 
              value={username} 
              onChange={(e) => setUsername(e.target.value)} 
              required 
            />
          </div>
          <div className="form-group">
            <input 
              type="password" 
              className="form-control" 
              placeholder="Mot de passe" 
              value={password} 
              onChange={(e) => setPassword(e.target.value)} 
              required 
            />
          </div>
          <button type="submit" className="btn" style={{width: '100%'}}>Se Connecter</button>
        </form>
      </div>
    </div>
  );
};

export default Login;
