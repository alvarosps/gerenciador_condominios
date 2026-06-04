/**
 * Config assertions for the shared queryClient defaults that drive offline
 * behavior. Read-only access to the real client's default options.
 */

import { describe, it, expect } from 'vitest';
import { queryClient } from '../query-client';

describe('queryClient offline defaults', () => {
  it('serves cached queries offline (networkMode offlineFirst)', () => {
    expect(queryClient.getDefaultOptions().queries?.networkMode).toBe('offlineFirst');
  });

  it('keeps gcTime >= 24h so the persisted cache survives until rehydration', () => {
    expect(queryClient.getDefaultOptions().queries?.gcTime).toBe(1000 * 60 * 60 * 24);
  });

  it('makes mutations fail fast offline instead of queuing (networkMode always)', () => {
    expect(queryClient.getDefaultOptions().mutations?.networkMode).toBe('always');
  });
});
