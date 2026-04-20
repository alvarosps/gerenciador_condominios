"use client";

import { AlertCircle } from "lucide-react";
import { useEffect } from "react";

import { Button } from "@/components/ui/button";
import { handleError } from "@/lib/utils/error-handler";

export default function DashboardError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    handleError(error, "ErrorBoundary");
  }, [error]);

  return (
    <div className="flex min-h-[400px] flex-col items-center justify-center gap-4">
      <AlertCircle className="h-12 w-12 text-destructive" />
      <h2 className="text-xl font-semibold">Algo deu errado</h2>
      <p className="text-muted-foreground">
        Ocorreu um erro ao carregar esta página.
      </p>
      {process.env.NODE_ENV === "development" && (
        <pre className="max-w-lg overflow-auto rounded bg-muted p-4 text-sm">
          {error.message}
        </pre>
      )}
      <Button onClick={reset}>Tentar novamente</Button>
    </div>
  );
}
