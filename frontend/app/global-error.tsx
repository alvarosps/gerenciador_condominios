'use client';

export default function GlobalError({
  error,
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
            <p className="text-gray-600 mb-6">{error?.message || 'Erro inesperado'}</p>
            <button
              onClick={() => reset()}
              className="bg-blue-500 text-white px-6 py-2 rounded hover:bg-blue-600"
            >
              Tentar novamente
            </button>
          </div>
        </div>
      </body>
    </html>
  );
}
