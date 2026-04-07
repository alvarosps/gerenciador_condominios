import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../client';
import { useAuthStore, type User } from '@/store/auth-store';
import { queryKeys } from '@/lib/api/query-keys';

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
      window.location.href = '/login';
    },
    onError: () => {
      // Even if backend logout fails, clear client state
      clearAuth();
      queryClient.clear();
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
 * Hook to initiate Google OAuth login
 * Returns a function that redirects to Google OAuth
 */
export function useGoogleLogin() {
  return () => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8008/api';
    window.location.href = `${apiUrl}/auth/google/`;
  };
}
