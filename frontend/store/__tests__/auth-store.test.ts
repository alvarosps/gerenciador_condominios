import { describe, it, expect, beforeEach } from 'vitest';
import { useAuthStore, type User } from '../auth-store';

const mockUser: User = {
  id: 1,
  email: 'admin@example.com',
  first_name: 'Admin',
  last_name: 'User',
  is_staff: true,
};

const mockToken = 'access-token-abc123';
const mockRefreshToken = 'refresh-token-xyz789';

describe('useAuthStore', () => {
  beforeEach(() => {
    // Reset store to initial state before each test
    useAuthStore.getState().clearAuth();
  });

  it('starts with no authentication', () => {
    const state = useAuthStore.getState();
    expect(state.token).toBeNull();
    expect(state.refreshToken).toBeNull();
    expect(state.user).toBeNull();
    expect(state.isAuthenticated).toBe(false);
  });

  describe('setAuth', () => {
    it('sets token, refreshToken, user and marks as authenticated', () => {
      useAuthStore.getState().setAuth(mockToken, mockRefreshToken, mockUser);

      const state = useAuthStore.getState();
      expect(state.token).toBe(mockToken);
      expect(state.refreshToken).toBe(mockRefreshToken);
      expect(state.user).toEqual(mockUser);
      expect(state.isAuthenticated).toBe(true);
    });
  });

  describe('setToken', () => {
    it('updates only the access token', () => {
      useAuthStore.getState().setAuth(mockToken, mockRefreshToken, mockUser);
      useAuthStore.getState().setToken('new-access-token');

      const state = useAuthStore.getState();
      expect(state.token).toBe('new-access-token');
      // refreshToken should be unchanged
      expect(state.refreshToken).toBe(mockRefreshToken);
      // user should be unchanged
      expect(state.user).toEqual(mockUser);
    });
  });

  describe('setUser', () => {
    it('updates only the user', () => {
      useAuthStore.getState().setAuth(mockToken, mockRefreshToken, mockUser);

      const updatedUser: User = { ...mockUser, email: 'updated@example.com' };
      useAuthStore.getState().setUser(updatedUser);

      const state = useAuthStore.getState();
      expect(state.user?.email).toBe('updated@example.com');
      // token should be unchanged
      expect(state.token).toBe(mockToken);
    });
  });

  describe('clearAuth', () => {
    it('resets all auth state to initial values', () => {
      useAuthStore.getState().setAuth(mockToken, mockRefreshToken, mockUser);
      useAuthStore.getState().clearAuth();

      const state = useAuthStore.getState();
      expect(state.token).toBeNull();
      expect(state.refreshToken).toBeNull();
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

      useAuthStore.getState().setAuth(mockToken, mockRefreshToken, regularUser);
      expect(useAuthStore.getState().user?.is_staff).toBe(false);
    });
  });
});
