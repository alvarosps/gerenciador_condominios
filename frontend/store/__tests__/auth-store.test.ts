import { describe, it, expect, beforeEach } from 'vitest';
import { useAuthStore, type User } from '../auth-store';

const mockUser: User = {
  id: 1,
  email: 'admin@example.com',
  first_name: 'Admin',
  last_name: 'User',
  is_staff: true,
};

describe('useAuthStore', () => {
  beforeEach(() => {
    // Reset store to initial state before each test
    useAuthStore.getState().clearAuth();
  });

  it('starts with no authentication', () => {
    const state = useAuthStore.getState();
    expect(state.user).toBeNull();
    expect(state.isAuthenticated).toBe(false);
  });

  describe('setAuth', () => {
    it('sets user and marks as authenticated', () => {
      useAuthStore.getState().setAuth(mockUser);

      const state = useAuthStore.getState();
      expect(state.user).toEqual(mockUser);
      expect(state.isAuthenticated).toBe(true);
    });
  });

  describe('setUser', () => {
    it('updates only the user', () => {
      useAuthStore.getState().setAuth(mockUser);

      const updatedUser: User = { ...mockUser, email: 'updated@example.com' };
      useAuthStore.getState().setUser(updatedUser);

      const state = useAuthStore.getState();
      expect(state.user?.email).toBe('updated@example.com');
      expect(state.isAuthenticated).toBe(true);
    });
  });

  describe('clearAuth', () => {
    it('resets all auth state to initial values', () => {
      useAuthStore.getState().setAuth(mockUser);
      useAuthStore.getState().clearAuth();

      const state = useAuthStore.getState();
      expect(state.user).toBeNull();
      expect(state.isAuthenticated).toBe(false);
    });
  });

  describe('User type', () => {
    it('stores user with non-staff flag', () => {
      const regularUser: User = {
        id: 2,
        email: 'user@example.com',
        first_name: 'Regular',
        last_name: 'User',
        is_staff: false,
      };

      useAuthStore.getState().setAuth(regularUser);
      expect(useAuthStore.getState().user?.is_staff).toBe(false);
    });
  });
});
