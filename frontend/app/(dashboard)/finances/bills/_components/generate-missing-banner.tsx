'use client';

import { CalendarPlus } from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { useGenerateMonthBills } from '@/lib/api/hooks/use-bills';
import { formatMonthYear } from '@/lib/utils/formatters';

interface GenerateMissingBannerProps {
  missingCount: number;
  year: number;
  month: number;
}

/**
 * Actionable banner shown when `month_board.generation.missing_count > 0` (S66): recurring
 * accounts eligible for the competence with no bill generated yet — the contextual shortcut.
 * Renders null at 0 (S74 contract). The always-available path is the "Gerar contas do mês" action
 * in the page header (`page.tsx`) — both share the same `useGenerateMonthBills` mutation instance
 * per call site, whose success/error toast (PT, backend message on 400 closed-month) lives in the
 * hook itself (no link yet — that is S76's preflight/actionable-toast work).
 */
export function GenerateMissingBanner({ missingCount, year, month }: GenerateMissingBannerProps) {
  const generateMonth = useGenerateMonthBills();

  if (missingCount === 0) {
    return null;
  }

  function handleGenerate() {
    generateMonth.mutate({ year, month });
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
