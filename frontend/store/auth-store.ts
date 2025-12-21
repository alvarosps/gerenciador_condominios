import { create } from 'zustand';
import { persist } from 'zustand/middleware';

/**
 * User interface matching backend User model
 */
export interface User {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
}

/**
 * Authentication state interface
 */
interface AuthState {
  token: string | null;
  refreshToken: string | null;
  user: User | null;
  isAuthenticated: boolean;

  // Actions
  setAuth: (token: string, refreshToken: string, user: User) => void;
  setToken: (token: string) => void;
  setUser: (user: User) => void;
  clearAuth: () => void;
}

/**
 * Zustand store for authentication state
 * Persisted to localStorage for session persistence
 */
export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      refreshToken: null,
      user: null,
      isAuthenticated: false,

      setAuth: (token, refreshToken, user) =>
        set({
          token,
          refreshToken,
          user,
          isAuthenticated: true,
        }),

      setToken: (token) =>
        set({
          token,
        }),

      setUser: (user) =>
        set({
          user,
        }),

      clearAuth: () =>
        set({
          token: null,
          refreshToken: null,
          user: null,
          isAuthenticated: false,
        }),
    }),
    {
      name: 'auth-storage',
      // Only persist essential data
      partialize: (state) => ({
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);
