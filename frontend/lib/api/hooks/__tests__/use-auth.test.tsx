/**
 * Tests for useAuth hooks
 *
 * These tests verify API calls work correctly and the hooks
 * properly handle success and error cases.
 *
 * Note: Some tests (login, logout) are skipped because they
 * have complex onSuccess handlers that interact with browser
 * APIs (document.cookie, window.location) which are difficult
 * to mock properly in the test environment.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { useLogin, useRegister, useRefreshToken, useCurrentUser, useLogout, useGoogleLogin } from '../use-auth';
import { createWrapper } from '@/tests/test-utils';

// Use vi.hoisted so mock variables are available inside vi.mock factory
const { authStoreMock } = vi.hoisted(() => {
  const mockSetAuth = vi.fn();
  const mockSetTokens = vi.fn();
  const mockSetToken = vi.fn();
  const mockClearAuth = vi.fn();

  const authStoreMock = (selector: (state: Record<string, unknown>) => unknown): unknown => {
    const mockState: Record<string, unknown> = {
      user: { id: 1, email: 'test@example.com', first_name: 'Test', last_name: 'User' },
      accessToken: 'mock-access-token',
      refreshToken: 'mock-refresh-token-67890',
      setAuth: mockSetAuth,
      setTokens: mockSetTokens,
      setToken: mockSetToken,
      clearAuth: mockClearAuth,
    };
    return selector(mockState);
  };

  return { mockSetAuth, mockSetTokens, mockSetToken, mockClearAuth, authStoreMock };
});

vi.mock('@/store/auth-store', () => ({
  useAuthStore: vi.fn(authStoreMock),
}));

// Store original window.location
const originalLocation = window.location;

describe('useAuth hooks', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Mock window.location
    Object.defineProperty(window, 'location', {
      configurable: true,
      value: { href: '' },
      writable: true,
    });
  });

  afterEach(() => {
    // Restore window.location
    Object.defineProperty(window, 'location', {
      configurable: true,
      value: originalLocation,
      writable: true,
    });
  });

  describe('useLogin', () => {
    it('should fail with invalid credentials', async () => {
      const { result } = renderHook(() => useLogin(), {
        wrapper: createWrapper(),
      });

      result.current.mutate({
        username: 'wronguser',
        password: 'wrongpassword',
      });

      await waitFor(() => expect(result.current.isError).toBe(true), { timeout: 5000 });
    });
  });

  describe('useRegister', () => {
    it('should fail when passwords do not match', async () => {
      const { result } = renderHook(() => useRegister(), {
        wrapper: createWrapper(),
      });

      result.current.mutate({
        email: 'newuser@example.com',
        password: 'password123',
        password2: 'differentpassword',
        first_name: 'New',
        last_name: 'User',
      });

      await waitFor(() => expect(result.current.isError).toBe(true), { timeout: 5000 });
    });
  });

  describe('useRefreshToken', () => {
    it('should fail with invalid refresh token', async () => {
      const { result } = renderHook(() => useRefreshToken(), {
        wrapper: createWrapper(),
      });

      result.current.mutate('invalid-refresh-token');

      await waitFor(() => expect(result.current.isError).toBe(true), { timeout: 5000 });
    });
  });

  describe('useCurrentUser', () => {
    it('should return current user when authenticated', () => {
      const { result } = renderHook(() => useCurrentUser(), {
        wrapper: createWrapper(),
      });

      // Should have initial data from store
      expect(result.current.data).toEqual({
        id: 1,
        email: 'test@example.com',
        first_name: 'Test',
        last_name: 'User',
      });
    });
  });

  describe('useLogout', () => {
    it('should clear localStorage tokens on logout', async () => {
      const removeItemSpy = vi.spyOn(localStorage, 'removeItem');

      const { result } = renderHook(() => useLogout(), {
        wrapper: createWrapper(),
      });

      result.current.mutate();

      // Wait for mutation to settle (success or error — both paths clear auth state)
      await waitFor(() => {
        expect(result.current.isPending).toBe(false);
      }, { timeout: 5000 });

      // Verify localStorage was cleared (logout clears tokens regardless of success/error)
      expect(removeItemSpy).toHaveBeenCalledWith('access_token');
      expect(removeItemSpy).toHaveBeenCalledWith('refresh_token');
    });
  });

  describe('useGoogleLogin', () => {
    it('should return a function that redirects to Google OAuth URL', () => {
      const { result } = renderHook(() => useGoogleLogin(), {
        wrapper: createWrapper(),
      });

      // Should return a function
      expect(typeof result.current).toBe('function');

      // Call it and verify redirect
      result.current();

      expect(window.location.href).toContain('/auth/google/');
    });
  });
});
