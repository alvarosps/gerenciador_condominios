'use client';

import { useState, useEffect } from 'react';

/**
 * Hook to detect when Zustand stores have completed hydration.
 *
 * In Next.js SSR, persisted Zustand stores may show initial state before
 * localStorage values are loaded. This hook returns true once hydration
 * is complete, allowing components to show loading states until then.
 *
 * @returns {boolean} True when hydration is complete
 *
 * @example
 * ```tsx
 * const hydrated = useHydration();
 * const user = useAuthStore((state) => state.user);
 *
 * if (!hydrated) return <HeaderSkeleton />;
 * return <Header user={user} />;
 * ```
 */
export function useHydration(): boolean {
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    // Once the component mounts, hydration is complete
    setHydrated(true);
  }, []);

  return hydrated;
}
