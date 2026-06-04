/**
 * Tests for the IndexedDB persister and offline-related QueryClient config.
 *
 * Mocks ONLY the external boundary (idb-keyval). The persister itself is
 * exercised through its real public surface (persistClient/restoreClient/
 * removeClient) — no TanStack internals are stubbed.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { get, set, del } from 'idb-keyval';
import { createIDBPersister, QUERY_CACHE_IDB_KEY } from '../persister';
import { queryClient } from '../query-client';

vi.mock('idb-keyval', () => ({
  get: vi.fn(),
  set: vi.fn(),
  del: vi.fn(),
}));

const MAX_AGE = 1000 * 60 * 60 * 24;

describe('createIDBPersister', () => {
  beforeEach(() => {
    vi.mocked(get).mockReset();
    vi.mocked(set).mockReset();
    vi.mocked(del).mockReset();
    vi.mocked(get).mockResolvedValue(undefined);
    vi.mocked(set).mockResolvedValue(undefined);
    vi.mocked(del).mockResolvedValue(undefined);
  });

  it('returns a persister exposing the expected methods', () => {
    const persister = createIDBPersister();

    expect(typeof persister.persistClient).toBe('function');
    expect(typeof persister.restoreClient).toBe('function');
    expect(typeof persister.removeClient).toBe('function');
  });

  it('delegates setItem to idb-keyval.set when persisting the client', async () => {
    const persister = createIDBPersister();

    await persister.persistClient({
      timestamp: Date.now(),
      buster: 'test',
      clientState: { mutations: [], queries: [] },
    });

    expect(set).toHaveBeenCalledTimes(1);
    expect(vi.mocked(set).mock.calls[0]?.[0]).toBe(QUERY_CACHE_IDB_KEY);
  });

  it('delegates getItem to idb-keyval.get when restoring the client', async () => {
    const persister = createIDBPersister();

    await persister.restoreClient();

    expect(get).toHaveBeenCalledTimes(1);
    expect(get).toHaveBeenCalledWith(QUERY_CACHE_IDB_KEY);
  });

  it('delegates removeItem to idb-keyval.del when removing the client', async () => {
    const persister = createIDBPersister();

    await persister.removeClient();

    expect(del).toHaveBeenCalledTimes(1);
    expect(del).toHaveBeenCalledWith(QUERY_CACHE_IDB_KEY);
  });
});

describe('QUERY_CACHE_IDB_KEY', () => {
  it('is the cross-session contract literal', () => {
    expect(QUERY_CACHE_IDB_KEY).toBe('condominios-query-cache');
  });
});

describe('queryClient offline config', () => {
  it('keeps gcTime greater than or equal to the persister maxAge', () => {
    const { gcTime } = queryClient.getDefaultOptions().queries ?? {};

    expect(gcTime).toBeGreaterThanOrEqual(MAX_AGE);
  });

  it('uses offlineFirst networkMode', () => {
    const { networkMode } = queryClient.getDefaultOptions().queries ?? {};

    expect(networkMode).toBe('offlineFirst');
  });
});
