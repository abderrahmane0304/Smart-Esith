import React, { useContext } from 'react';
import { AuthContext } from '../context/AuthContext';
import { useNavigate, Outlet, Link } from 'react-router-dom';

const Layout = () => {
  const { user, logout } = useContext(AuthContext);
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="layout-container">
      <div className="sidebar">
        <div className="sidebar-header">
          SMART ESITH
        </div>
        <ul className="sidebar-menu">
          <li><Link to="/dashboard">Accueil Dashboard</Link></li>
          {user?.role === 'Admin' && <li><Link to="/admin">Administration</Link></li>}
        </ul>
      </div>
      <div className="main-content">
        <div className="topbar">
          <div>Connecté en tant que <strong>{user?.username}</strong> ({user?.role})</div>
          <button onClick={handleLogout} className="btn" style={{backgroundColor: '#e74c3c', color: 'white'}}>Déconnexion</button>
        </div>
        <div className="page-content">
          <Outlet />
        </div>
      </div>
    </div>
  );
};

export default Layout;
