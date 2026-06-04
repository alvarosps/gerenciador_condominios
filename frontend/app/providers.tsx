'use client';

import { ThemeProvider } from 'next-themes';
import { PersistQueryClientProvider } from '@tanstack/react-query-persist-client';
import { Toaster } from '@/components/ui/sonner';
import { queryClient } from '@/lib/config/query-client';
import { createIDBPersister } from '@/lib/config/persister';

const persister = createIDBPersister();

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <ThemeProvider attribute="class" defaultTheme="system" enableSystem disableTransitionOnChange>
      <PersistQueryClientProvider
        client={queryClient}
        persistOptions={{
          persister,
          maxAge: 1000 * 60 * 60 * 24,
          buster: process.env.NEXT_PUBLIC_BUILD_ID ?? 'dev',
          dehydrateOptions: {
            shouldDehydrateQuery: (query) => query.state.status === 'success',
          },
        }}
      >
        {children}
        <Toaster />
      </PersistQueryClientProvider>
    </ThemeProvider>
  );
}
