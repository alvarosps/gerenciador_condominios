import axios, { type AxiosError, type InternalAxiosRequestConfig } from 'axios';

let refreshPromise: Promise<string> | null = null;

export const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8008/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

/**
 * Request interceptor - Attach JWT token to all requests
 */
apiClient.interceptors.request.use(
  (config) => {
    // Add auth token if exists
    if (typeof window !== 'undefined') {
      const token = localStorage.getItem('access_token');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    }
    return config;
  },
  (error: AxiosError) => {
    return Promise.reject(error instanceof Error ? error : new Error(String(error)));
  }
);

/**
 * Response interceptor - Handle 401 errors and refresh token
 */
apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError & { config?: InternalAxiosRequestConfig & { _retry?: boolean } }) => {
    const originalRequest = error.config;

    // If 401 Unauthorized and we haven't retried yet
    if (error.response?.status === 401 && originalRequest && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        if (typeof window === 'undefined') {
          return await Promise.reject(error instanceof Error ? error : new Error(String(error)));
        }

        const refreshToken = localStorage.getItem('refresh_token');
        if (!refreshToken) {
          throw new Error('No refresh token available');
        }

        // Deduplicate concurrent refresh calls — only one request goes out
        refreshPromise ??= axios
          .post<{ access: string }>(
            `${process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8008/api'}/auth/token/refresh/`,
            { refresh: refreshToken }
          )
          .then((res) => res.data.access)
          .finally(() => {
            refreshPromise = null;
          });

        const newToken = await refreshPromise;

        // Store new access token
        localStorage.setItem('access_token', newToken);

        // Update the failed request with new token
        originalRequest.headers.Authorization = `Bearer ${newToken}`;

        // Retry the original request
        return await apiClient(originalRequest);
      } catch (refreshError) {
        // Refresh failed - clear auth and redirect to login
        if (typeof window !== 'undefined') {
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');

          // Also clear Zustand store (imported dynamically to avoid circular dependency)
          const { useAuthStore } = await import('@/store/auth-store');
          useAuthStore.getState().clearAuth();

          window.location.href = '/login';
        }

        return Promise.reject(refreshError instanceof Error ? refreshError : new Error(String(refreshError)));
      }
    }

    return Promise.reject(error instanceof Error ? error : new Error(String(error)));
  }
);
