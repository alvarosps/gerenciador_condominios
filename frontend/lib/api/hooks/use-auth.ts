import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../client';
import { useAuthStore, type User } from '@/store/auth-store';

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
 * Authentication response from backend (JWT token endpoint)
 */
export interface AuthResponse {
  access: string;
  refresh: string;
}

/**
 * Token refresh response
 */
export interface RefreshTokenResponse {
  access: string;
}

/**
 * Hook for user login with JWT
 */
export function useLogin() {
  const setTokens = useAuthStore((state) => state.setTokens);

  return useMutation({
    mutationFn: async (credentials: LoginCredentials) => {
      const { data } = await apiClient.post<AuthResponse>('/auth/token/', credentials);
      return data;
    },
    onSuccess: (data) => {
      // Store tokens in Zustand store
      setTokens(data.access, data.refresh);

      // Also store in localStorage for API client interceptor
      if (typeof window !== 'undefined') {
        localStorage.setItem('access_token', data.access);
        localStorage.setItem('refresh_token', data.refresh);

        // Set cookie for middleware auth check (24 hour expiry)
        document.cookie = `access_token=${data.access}; path=/; max-age=31536000; SameSite=Lax`;
      }
    },
  });
}

/**
 * Hook for user registration
 */
export function useRegister() {
  return useMutation({
    mutationFn: async (registerData: RegisterData) => {
      const { data } = await apiClient.post<AuthResponse>('/auth/register/', registerData);
      return data;
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
      // Call backend logout endpoint
      await apiClient.post('/auth/logout/');
    },
    onSuccess: () => {
      // Clear auth state
      clearAuth();

      // Clear tokens from localStorage and cookie
      if (typeof window !== 'undefined') {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');

        // Clear cookie by setting expired date
        document.cookie = 'access_token=; path=/; max-age=0; SameSite=Lax';
      }

      // Clear all cached queries
      queryClient.clear();

      // Redirect to login
      window.location.href = '/login';
    },
    onError: () => {
      // Even if backend logout fails, clear client state
      clearAuth();

      if (typeof window !== 'undefined') {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');

        // Clear cookie by setting expired date
        document.cookie = 'access_token=; path=/; max-age=0; SameSite=Lax';
      }

      queryClient.clear();
      window.location.href = '/login';
    },
  });
}

/**
 * Hook to refresh JWT token
 */
export function useRefreshToken() {
  const setToken = useAuthStore((state) => state.setToken);

  return useMutation({
    mutationFn: async (refreshToken: string) => {
      const { data } = await apiClient.post<RefreshTokenResponse>('/auth/token/refresh/', {
        refresh: refreshToken,
      });
      return data;
    },
    onSuccess: (data) => {
      // Update token in store
      setToken(data.access);

      // Update token in localStorage and cookie
      if (typeof window !== 'undefined') {
        localStorage.setItem('access_token', data.access);

        // Update cookie for middleware auth check (24 hour expiry)
        document.cookie = `access_token=${data.access}; path=/; max-age=31536000; SameSite=Lax`;
      }
    },
  });
}

/**
 * Hook to get current user profile
 */
export function useCurrentUser() {
  const user = useAuthStore((state) => state.user);

  return useQuery({
    queryKey: ['current-user'],
    queryFn: async () => {
      const { data } = await apiClient.get<User>('/auth/user/');
      return data;
    },
    enabled: !!user,
    initialData: user || undefined,
  });
}

/**
 * Hook to initiate Google OAuth login
 * Returns a function that redirects to Google OAuth
 */
export function useGoogleLogin() {
  return () => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';
    window.location.href = `${apiUrl}/auth/google/`;
  };
}
