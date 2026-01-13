/**
 * MSW Server for Node.js (Vitest) testing
 *
 * This sets up a mock server that intercepts all HTTP requests
 * during tests and responds with mock data.
 */

import { setupServer } from 'msw/node';
import { handlers, resetMockData } from './handlers';

// Create the mock server with all handlers
export const server = setupServer(...handlers);

// Re-export handlers and reset function for test customization
export { handlers, resetMockData };

/**
 * Helper to add custom handlers for specific tests
 * @param customHandlers - Additional handlers to use
 */
export function useCustomHandlers(...customHandlers: Parameters<typeof server.use>) {
  server.use(...customHandlers);
}
