'use client';

import { useEffect, useState } from 'react';
import { WifiOff } from 'lucide-react';

/**
 * Reactive banner shown while the device is offline. Offline access is
 * read-only: the persisted query cache serves previously fetched data, but
 * mutations are paused (networkMode: 'offlineFirst'), so the message tells the
 * user they are viewing saved data.
 */
export function OfflineBanner() {
  const [isOffline, setIsOffline] = useState(false);

  useEffect(() => {
    const updateStatus = (): void => {
      setIsOffline(!navigator.onLine);
    };

    updateStatus();
    window.addEventListener('online', updateStatus);
    window.addEventListener('offline', updateStatus);

    return () => {
      window.removeEventListener('online', updateStatus);
      window.removeEventListener('offline', updateStatus);
    };
  }, []);

  if (!isOffline) {
    return null;
  }

  return (
    <div
      role="status"
      className="flex items-center gap-2 bg-amber-500/15 px-4 py-2 text-sm text-amber-700 dark:text-amber-400"
    >
      <WifiOff className="h-4 w-4 shrink-0" aria-hidden="true" />
      <span>Você está offline — exibindo dados salvos</span>
    </div>
  );
}
