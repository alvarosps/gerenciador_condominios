import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { del } from 'idb-keyval';
import { apiClient } from '../client';
import { useAuthStore, type User } from '@/store/auth-store';
import { queryKeys } from '@/lib/api/query-keys';
import { QUERY_CACHE_IDB_KEY } from '@/lib/config/persister';

/**
 * Login credentials interface
 */
export interface LoginCredentials {
  username: string;
  password: string;
}

/**
 * Registration data interface
 */
export interface RegisterData {
  email: string;
  password: string;
  password2: string;
  first_name: string;
  last_name: string;
}

/**
 * Authentication response from backend — tokens in HttpOnly cookies, user in body
 */
export interface AuthResponse {
  user: User;
}

/**
 * Registration response from backend — tokens in HttpOnly cookies, user in body
 */
export interface RegisterResponse {
  user: User;
}

/**
 * Hook for user login with HttpOnly cookie-based JWT
 */
export function useLogin() {
  const setAuth = useAuthStore((state) => state.setAuth);

  return useMutation({
    mutationFn: async (credentials: LoginCredentials) => {
      const { data } = await apiClient.post<AuthResponse>('/auth/token/', credentials);
      return data;
    },
    onSuccess: (data) => {
      setAuth(data.user);
    },
  });
}

/**
 * Hook for user registration — creates account and immediately authenticates the user
 */
export function useRegister() {
  const setAuth = useAuthStore((state) => state.setAuth);

  return useMutation({
    mutationFn: async (registerData: RegisterData) => {
      const { data } = await apiClient.post<RegisterResponse>('/auth/register/', registerData);
      return data;
    },
    onSuccess: (data) => {
      setAuth(data.user);
    },
  });
}

/**
 * Hook for user logout
 */
export function useLogout() {
  const clearAuth = useAuthStore((state) => state.clearAuth);
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async () => {
      await apiClient.post('/auth/logout/');
    },
    onSuccess: () => {
      clearAuth();
      queryClient.clear();
      // Clear the persisted cache so one user's business data does not leak to
      // another on a shared device (read-only offline cache is per-session).
      void del(QUERY_CACHE_IDB_KEY);
      window.location.href = '/login';
    },
    onError: () => {
      // Even if backend logout fails, clear client state
      clearAuth();
      queryClient.clear();
      void del(QUERY_CACHE_IDB_KEY);
      window.location.href = '/login';
    },
  });
}

/**
 * Hook to get current user profile
 */
export function useCurrentUser() {
  const user = useAuthStore((state) => state.user);

  return useQuery({
    queryKey: queryKeys.currentUser.all,
    queryFn: async () => {
      const { data } = await apiClient.get<User>('/auth/me/');
      return data;
    },
    enabled: Boolean(user),
    placeholderData: user ?? undefined,
  });
}

/**
 * Code exchange payload for the OAuth callback flow
 */
export interface OAuthExchangePayload {
  code: string;
}

/**
 * Hook to initiate Google OAuth login
 * Returns a function that redirects to the django-allauth login-start endpoint.
 * allauth lives at the backend origin under /accounts/ — NOT under the /api prefix,
 * and NOT reachable through the same-origin /api proxy — so it needs the absolute
 * backend origin from NEXT_PUBLIC_BACKEND_URL. After Google authenticates, the backend
 * hands a one-time code back to the frontend /auth/callback, which exchanges it through
 * the /api proxy (so the resulting auth cookies land same-origin on the frontend).
 */
export function useGoogleLogin() {
  return () => {
    const backendOrigin = process.env.NEXT_PUBLIC_BACKEND_URL ?? 'http://localhost:8008';
    window.location.href = `${backendOrigin}/accounts/google/login/`;
  };
}

/**
 * Hook to exchange a short-lived OAuth code (returned to the frontend callback)
 * for an authenticated session — tokens land in HttpOnly cookies, user in body.
 */
export function useExchangeOAuthCode() {
  const setAuth = useAuthStore((state) => state.setAuth);

  return useMutation({
    mutationFn: async (payload: OAuthExchangePayload) => {
      const { data } = await apiClient.post<AuthResponse>('/auth/oauth/exchange/', payload);
      return data;
    },
    onSuccess: (data) => {
      setAuth(data.user);
    },
  });
}
