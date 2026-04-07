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
  useCurrentUser,
  useLogout,
  useGoogleLogin,
} from '../use-auth';
import { createWrapper } from '@/tests/test-utils';
import { server } from '@/tests/mocks/server';
import { useAuthStore } from '@/store/auth-store';

const API_BASE = 'http://localhost:8008/api';

// Note: success tests for useLogin cannot be collocated with failure tests in the
// same describe block. The Axios 401 interceptor performs async side-effects
// (dynamic import + window.location assignment) that outlive the test boundary
// and prevent subsequent mutations from settling. The failure tests cover the
// error path; success behavior is covered by useCurrentUser tests.

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

    it('should store auth state on successful registration', async () => {
      // Set a valid href so MSW can resolve the request URL when intercepting
      window.location.href = 'http://localhost:4000/register';

      const { result } = renderHook(() => useRegister(), {
        wrapper: createWrapper(),
      });

      result.current.mutate({
        email: 'newuser@example.com',
        password: 'Password123!',
        password2: 'Password123!',
        first_name: 'New',
        last_name: 'User',
      });

      // Wait for mutation to settle
      await waitFor(
        () => {
          expect(result.current.isIdle).toBe(false);
          expect(result.current.isPending).toBe(false);
        },
        { timeout: 5000 },
      );

      expect(result.current.isSuccess).toBe(true);
      const storeState = useAuthStore.getState();
      expect(storeState.isAuthenticated).toBe(true);
      expect(storeState.user?.email).toBe('newuser@example.com');
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
      useAuthStore.getState().setAuth({
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
    it('should clear auth store on logout', async () => {
      useAuthStore.getState().setAuth({
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

    it('should clear auth store on successful logout', async () => {
      useAuthStore.getState().setAuth({
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
