/**
 * Test utilities for React component and hook testing
 *
 * Provides wrapper components with all necessary providers (QueryClient, etc.)
 * and re-exports from @testing-library/react for convenience.
 */

import React, { type ReactNode } from 'react';
import { render, type RenderOptions, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

/**
 * Create a fresh QueryClient for each test to prevent state leakage
 */
export function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
        staleTime: 0,
      },
      mutations: {
        retry: false,
      },
    },
  });
}

/**
 * Wrapper component that provides all necessary context providers
 */
interface TestWrapperProps {
  children: ReactNode;
  queryClient?: QueryClient;
}

function TestWrapper({ children, queryClient }: TestWrapperProps) {
  const client = queryClient ?? createTestQueryClient();

  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

/**
 * Custom render function that wraps components with providers
 */
interface CustomRenderOptions extends Omit<RenderOptions, 'wrapper'> {
  queryClient?: QueryClient;
}

export function renderWithProviders(
  ui: React.ReactElement,
  { queryClient, ...options }: CustomRenderOptions = {}
) {
  const client = queryClient ?? createTestQueryClient();
  const Wrapper = ({ children }: { children: ReactNode }) => (
    <TestWrapper queryClient={client}>{children}</TestWrapper>
  );

  return { ...render(ui, { wrapper: Wrapper, ...options }), queryClient: client };
}

/**
 * Wait until every background query started by a render has settled, so an in-flight request is
 * never aborted by test teardown (that abort surfaces as an MSW "request already handled" unhandled
 * rejection). Call at the end of any test whose component fires a query it does not otherwise await.
 */
export async function waitForQueriesToSettle(queryClient: QueryClient) {
  await waitFor(() => {
    if (queryClient.isFetching() > 0) throw new Error('queries still fetching');
  });
}

/**
 * Create wrapper for testing hooks with renderHook
 */
export function createWrapper(queryClient?: QueryClient) {
  const client = queryClient ?? createTestQueryClient();
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
  };
}

// Re-export everything from testing-library
export * from '@testing-library/react';
export { default as userEvent } from '@testing-library/user-event';
