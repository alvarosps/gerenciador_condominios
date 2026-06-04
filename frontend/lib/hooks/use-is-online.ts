'use client';

import { useEffect, useState } from 'react';

/**
 * Reactive online/offline status from the browser. Returns true while the
 * device reports connectivity.
 *
 * Single source for offline-aware UI (offline banner, disabled destructive
 * actions). Offline access is read-only: queries serve the persisted cache,
 * but create/edit/delete are gated so they never silently queue.
 *
 * SSR-safe: starts `true` (server has no `navigator`) and corrects on mount.
 */
export function useIsOnline(): boolean {
  const [isOnline, setIsOnline] = useState(true);

  useEffect(() => {
    const update = (): void => {
      setIsOnline(navigator.onLine);
    };

    update();
    window.addEventListener('online', update);
    window.addEventListener('offline', update);

    return () => {
      window.removeEventListener('online', update);
      window.removeEventListener('offline', update);
    };
  }, []);

  return isOnline;
}
