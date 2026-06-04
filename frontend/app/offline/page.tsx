import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Offline — Condomínios Manager',
};

export default function OfflinePage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-3 p-6 text-center">
      <h1 className="text-2xl font-semibold">Você está offline</h1>
      <p className="max-w-md text-muted-foreground">
        Não foi possível carregar esta página sem conexão. Reconecte à internet para continuar.
      </p>
    </main>
  );
}
