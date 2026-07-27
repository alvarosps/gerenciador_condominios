'use client';

import { CalendarPlus } from 'lucide-react';
import { toast } from 'sonner';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { useGenerateMonthBills } from '@/lib/api/hooks/use-bills';
import { getErrorMessage, handleError } from '@/lib/utils/error-handler';
import { formatMonthYear } from '@/lib/utils/formatters';

interface GenerateMissingBannerProps {
  missingCount: number;
  year: number;
  month: number;
}

/**
 * Actionable banner shown when `month_board.generation.missing_count > 0` (S66): recurring
 * accounts eligible for the competence with no bill generated yet. Renders null at 0 (S74
 * contract). A 400 from a closed month shows the backend's PT message via toast (no link — that
 * is S76's preflight/actionable-toast work).
 */
export function GenerateMissingBanner({ missingCount, year, month }: GenerateMissingBannerProps) {
  const generateMonth = useGenerateMonthBills();

  if (missingCount === 0) {
    return null;
  }

  function handleGenerate() {
    generateMonth.mutate(
      { year, month },
      {
        onSuccess: (result) => {
          toast.success(`${String(result.created)} conta(s) gerada(s)`);
        },
        onError: (error) => {
          handleError(error, 'Erro ao gerar contas do mês');
          toast.error(getErrorMessage(error, 'Erro ao gerar contas do mês'));
        },
      }
    );
  }

  return (
    <Alert className="mb-4 flex flex-wrap items-center justify-between gap-3">
      <AlertDescription>
        Há {missingCount} conta(s) recorrente(s) sem fatura gerada em {formatMonthYear(year, month)}
      </AlertDescription>
      <Button variant="outline" onClick={handleGenerate} disabled={generateMonth.isPending}>
        <CalendarPlus className="mr-2 h-4 w-4" />
        {generateMonth.isPending
          ? 'Gerando...'
          : `Gerar contas faltantes (${String(missingCount)})`}
      </Button>
    </Alert>
  );
}
