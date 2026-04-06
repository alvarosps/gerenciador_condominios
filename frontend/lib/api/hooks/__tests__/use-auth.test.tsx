/**
 * Tests for useAuth hooks
 *
 * Tests verify that hooks make correct API calls and handle success/error
 * responses. Uses MSW to intercept HTTP requests at the network boundary.
 * Uses the real Zustand auth store — reset between tests with clearAuth().
 */

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import {
  useLogin,
  useRegister,
  useRefreshToken,
  useCurrentUser,
  useLogout,
  useGoogleLogin,
} from '../use-auth';
import { createWrapper } from '@/tests/test-utils';
import { server } from '@/tests/mocks/server';
import { useAuthStore } from '@/store/auth-store';

const API_BASE = 'http://localhost:8008/api';

// Store original window.location
const originalLocation = window.location;

describe('useAuth hooks', () => {
  beforeEach(() => {
    // Reset real Zustand store before each test
    useAuthStore.getState().clearAuth();

    // Mock window.location for redirect assertions
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

    it('should succeed with valid credentials', async () => {
      // The default MSW handler returns 200 for testuser/password123
      // followed by /auth/me/ which returns user data.
      // Mutation success indicates the full flow completed without error.
      const { result } = renderHook(() => useLogin(), {
        wrapper: createWrapper(),
      });

      result.current.mutate({ username: 'testuser', password: 'password123' });

      await waitFor(
        () => expect(result.current.isError || result.current.isSuccess).toBe(true),
        { timeout: 5000 },
      );

      // The mutation should not error (invalid creds error would be isError=true)
      // The valid credentials path either succeeds or hits a downstream issue (e.g. cookie)
      // but must not return 401 "Invalid credentials"
      expect(result.current.isError).toBe(false);
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

    it('should succeed with valid refresh token', async () => {
      // The default MSW handler returns a new access token for mock-refresh-token-67890
      const { result } = renderHook(() => useRefreshToken(), {
        wrapper: createWrapper(),
      });

      result.current.mutate('mock-refresh-token-67890');

      await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

      expect(result.current.data?.access).toBe('mock-new-access-token-54321');
    });
  });

  describe('useCurrentUser', () => {
    it('should return undefined when not authenticated', () => {
      const { result } = renderHook(() => useCurrentUser(), {
        wrapper: createWrapper(),
      });

      // No user in store, query is disabled
      expect(result.current.isLoading).toBe(false);
      expect(result.current.data).toBeUndefined();
    });

    it('should return current user data when authenticated', async () => {
      // Set real store state before rendering hook
      useAuthStore.getState().setAuth('mock-token', 'mock-refresh', {
        id: 1,
        email: 'test@example.com',
        first_name: 'Test',
        last_name: 'User',
        is_staff: false,
      });

      server.use(
        http.get(`${API_BASE}/auth/me/`, () => {
          return HttpResponse.json({
            id: 1,
            email: 'test@example.com',
            first_name: 'Test',
            last_name: 'User',
            is_staff: false,
          });
        }),
      );

      const { result } = renderHook(() => useCurrentUser(), {
        wrapper: createWrapper(),
      });

      // Immediately has placeholder data from store
      expect(result.current.data?.email).toBe('test@example.com');

      await waitFor(() => expect(result.current.isSuccess).toBe(true), { timeout: 5000 });

      expect(result.current.data?.email).toBe('test@example.com');
      expect(result.current.data?.first_name).toBe('Test');
    });
  });

  describe('useLogout', () => {
    it('should clear localStorage tokens on logout', async () => {
      const removeItemSpy = localStorage.removeItem.bind(localStorage);
      const calls: string[] = [];
      Object.defineProperty(localStorage, 'removeItem', {
        configurable: true,
        value: (key: string) => {
          calls.push(key);
          removeItemSpy(key);
        },
      });

      const { result } = renderHook(() => useLogout(), {
        wrapper: createWrapper(),
      });

      result.current.mutate();

      // Wait for mutation to settle (success or error — both paths clear auth state)
      await waitFor(
        () => {
          expect(result.current.isPending).toBe(false);
        },
        { timeout: 5000 },
      );

      // Verify localStorage was cleared (logout clears tokens regardless of success/error)
      expect(calls).toContain('access_token');
      expect(calls).toContain('refresh_token');

      // Restore
      Object.defineProperty(localStorage, 'removeItem', {
        configurable: true,
        value: removeItemSpy,
      });
    });

    it('should clear auth store on successful logout', async () => {
      useAuthStore.getState().setAuth('token', 'refresh', {
        id: 1,
        email: 'test@example.com',
        first_name: 'Test',
        last_name: 'User',
        is_staff: false,
      });

      const { result } = renderHook(() => useLogout(), {
        wrapper: createWrapper(),
      });

      result.current.mutate();

      await waitFor(
        () => {
          expect(result.current.isPending).toBe(false);
        },
        { timeout: 5000 },
      );

      const storeState = useAuthStore.getState();
      expect(storeState.isAuthenticated).toBe(false);
      expect(storeState.user).toBeNull();
    });
  });

  describe('useGoogleLogin', () => {
    it('should return a function that redirects to Google OAuth URL', () => {
      const { result } = renderHook(() => useGoogleLogin(), {
        wrapper: createWrapper(),
      });

      expect(typeof result.current).toBe('function');

      result.current();

      expect(window.location.href).toContain('/auth/google/');
    });
  });
});
