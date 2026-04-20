'use client';

import { useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { handleError } from '@/lib/utils/error-handler';

export const dynamic = 'force-dynamic';

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Log the error to an error reporting service
    handleError(error, 'ErrorBoundary');
  }, [error]);

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <div className="text-center space-y-4">
        <h1 className="text-6xl font-bold mb-4">500</h1>
        <p className="text-xl text-muted-foreground mb-8">
          Desculpe, algo deu errado.
        </p>
        <Button onClick={() => reset()} size="lg">
          Tentar Novamente
        </Button>
      </div>
    </div>
  );
}
