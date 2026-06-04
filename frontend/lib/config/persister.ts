import { createAsyncStoragePersister } from '@tanstack/query-async-storage-persister';
import { get, set, del } from 'idb-keyval';

/**
 * IndexedDB key for the persisted TanStack Query cache. Single source of truth —
 * the persister writes here and the logout flow clears it (DRY).
 */
export const QUERY_CACHE_IDB_KEY = 'condominios-query-cache';

/**
 * Persister that stores the dehydrated query cache in IndexedDB via idb-keyval,
 * enabling read-only offline access to previously fetched data.
 */
export function createIDBPersister() {
  return createAsyncStoragePersister({
    key: QUERY_CACHE_IDB_KEY,
    storage: {
      getItem: (key: string) => get<string>(key),
      setItem: (key: string, value: string) => set(key, value),
      removeItem: (key: string) => del(key),
    },
  });
}
