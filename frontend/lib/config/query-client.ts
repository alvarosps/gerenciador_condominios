import { QueryClient } from '@tanstack/react-query';

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      gcTime: 1000 * 60 * 60 * 24, // 24h — must be >= persister maxAge so cache survives until rehydration
      networkMode: 'offlineFirst',
      retry: (failureCount, error) => {
        if (
          error instanceof Error &&
          'response' in error &&
          [401, 403].includes(
            (error as { response?: { status?: number } }).response?.status ?? 0
          )
        ) {
          return false;
        }
        return failureCount < 3;
      },
      refetchOnWindowFocus: true,
    },
    mutations: {
      // Offline is read-only: 'always' makes mutations fail fast when offline
      // (surfacing an error) instead of pausing into a write queue, honoring
      // the no-offline-writes decision.
      networkMode: 'always',
    },
  },
});
