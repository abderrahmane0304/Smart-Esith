import React, { createContext, useState, useEffect } from 'react';
import { jwtDecode } from 'jwt-decode';
import apiClient from '../api/apiClient';

export const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(() => {
    const token = localStorage.getItem('token');
    if (token) {
      try {
        const decoded = jwtDecode(token);
        if (decoded.exp * 1000 > Date.now()) {
          const role = localStorage.getItem('role');
          const username = localStorage.getItem('username');
          return { token, role, username };
        }
      } catch (err) {
        console.error(err);
      }
    }
    return null;
  });
  const [loading, setLoading] = useState(true);

  const logout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('role');
    localStorage.removeItem('username');
    setUser(null);
  };

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (token) {
      try {
        const decoded = jwtDecode(token);
        if (decoded.exp * 1000 <= Date.now()) {
          logout();
        }
      } catch (err) {
        logout();
      }
    }
    setLoading(false);
  }, []);

  const login = async (username, password) => {
    const res = await apiClient.post('/auth/login', { username, password });
    const { token, role, username: u } = res.data;
    localStorage.setItem('token', token);
    localStorage.setItem('role', role);
    localStorage.setItem('username', u);
    setUser({ token, role, username: u });
  };

  return (
    <AuthContext.Provider value={{ user, login, logout, loading }}>
      {children}
    </AuthContext.Provider>
  );
};
