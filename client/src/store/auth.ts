import { useState, useEffect } from 'react';

// Simple auth store without zustand
let authState = {
  isAuthenticated: false,
  user: null as User | null,
  token: null as string | null,
};

const listeners = new Set<() => void>();

const notifyListeners = () => {
  listeners.forEach(listener => listener());
};

const setAuthState = (newState: Partial<typeof authState>) => {
  authState = { ...authState, ...newState };
  localStorage.setItem('auth-storage', JSON.stringify(authState));
  notifyListeners();
};

// Load from localStorage on init
const stored = localStorage.getItem('auth-storage');
if (stored) {
  try {
    authState = { ...authState, ...JSON.parse(stored) };
  } catch (e) {
    console.error('Failed to parse stored auth state:', e);
  }
}

interface User {
  id: string;
  username: string;
  email: string;
  role: string;
}

export const useAuthStore = () => {
  const [, forceUpdate] = useState({});

  useEffect(() => {
    const listener = () => forceUpdate({});
    listeners.add(listener);
    return () => listeners.delete(listener);
  }, []);

  const login = async (username: string, password: string): Promise<boolean> => {
    try {
      const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ username, password }),
      });

      const result = await response.json();

      if (result.success) {
        setAuthState({
          isAuthenticated: true,
          user: result.user,
          token: result.token,
        });
        return true;
      }

      return false;
    } catch (error) {
      console.error('Login error:', error);
      return false;
    }
  };

  const logout = async (): Promise<void> => {
    try {
      await fetch('/api/auth/logout', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });
    } catch (error) {
      console.error('Logout error:', error);
    }

    setAuthState({
      isAuthenticated: false,
      user: null,
      token: null,
    });
  };

  const checkAuth = async (): Promise<void> => {
    const { token } = authState;
    if (!token) {
      setAuthState({ isAuthenticated: false, user: null, token: null });
      return;
    }

    try {
      // For now, assume authentication is valid if token exists
      setAuthState({ isAuthenticated: true });
    } catch (error) {
      console.error('Auth check error:', error);
      setAuthState({ isAuthenticated: false, user: null, token: null });
    }
  };

  return {
    isAuthenticated: authState.isAuthenticated,
    user: authState.user,
    token: authState.token,
    login,
    logout,
    checkAuth,
  };
};