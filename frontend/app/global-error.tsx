'use client';

export default function GlobalError({
  error: _error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html lang="pt-BR">
      <body>
        <div className="flex min-h-screen items-center justify-center p-4">
          <div className="text-center">
            <h2 className="text-2xl font-bold mb-4">Algo deu errado!</h2>
            <p className="text-muted-foreground mb-6">Ocorreu um erro inesperado. Por favor, tente novamente.</p>
            <button
              onClick={() => reset()}
              className="bg-primary text-primary-foreground px-6 py-2 rounded hover:bg-primary/90"
            >
              Tentar novamente
            </button>
          </div>
        </div>
      </body>
    </html>
  );
}
