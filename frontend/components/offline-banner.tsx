'use client';

import { WifiOff } from 'lucide-react';
import { useIsOnline } from '@/lib/hooks/use-is-online';

/**
 * Reactive banner shown while the device is offline. Offline access is
 * read-only: the persisted query cache serves previously fetched data, while
 * create/edit actions are unavailable until the connection returns.
 */
export function OfflineBanner() {
  const isOnline = useIsOnline();

  if (isOnline) {
    return null;
  }

  return (
    <div
      role="status"
      className="flex items-center gap-2 bg-amber-500/15 px-4 py-2 text-sm text-amber-700 dark:text-amber-400"
    >
      <WifiOff className="h-4 w-4 shrink-0" aria-hidden="true" />
      <span>
        Você está offline — exibindo dados salvos. Criar e editar ficam indisponíveis até reconectar.
      </span>
    </div>
  );
}
