import axios, { type AxiosError, type InternalAxiosRequestConfig } from 'axios';

let refreshPromise: Promise<void> | null = null;

const REQUEST_TIMEOUT_MS = 30_000;

export const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8008/api',
  timeout: REQUEST_TIMEOUT_MS,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
});

/**
 * Response interceptor - Handle 401 errors by refreshing the HttpOnly cookie token
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

        // Deduplicate concurrent refresh calls — only one request goes out
        // Cookies are sent automatically via withCredentials
        refreshPromise ??= axios
          .post(
            `${process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8008/api'}/auth/token/refresh/`,
            {},
            { withCredentials: true }
          )
          .then(() => undefined)
          .finally(() => {
            refreshPromise = null;
          });

        await refreshPromise;

        // Retry the original request — new access cookie is now set
        return await apiClient(originalRequest);
      } catch (refreshError) {
        // Refresh failed - clear auth state and redirect to login
        if (typeof window !== 'undefined') {
          // Also clear Zustand store (imported dynamically to avoid circular dependency)
          const { useAuthStore } = await import('@/store/auth-store');
          useAuthStore.getState().clearAuth();

          window.location.href = '/login';
        }

        return Promise.reject(
          refreshError instanceof Error ? refreshError : new Error(String(refreshError))
        );
      }
    }

    return Promise.reject(error instanceof Error ? error : new Error(String(error)));
  }
);
