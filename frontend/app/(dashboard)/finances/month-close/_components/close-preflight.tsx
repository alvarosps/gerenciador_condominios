'use client';

import { useEffect } from 'react';
import { AlertTriangle } from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import { Skeleton } from '@/components/ui/skeleton';
import { useMonthBoard } from '@/lib/api/hooks/use-month-board';
import { formatCurrency } from '@/lib/utils/formatters';
import type { Bill } from '@/lib/schemas/finances/bill.schema';
import type { MonthBoard } from '@/lib/schemas/finances/month-board.schema';

const PREVIEW_LIMIT = 5;

/**
 * Pure derivation of the preflight's open-bills list: every bill across the competence's `groups`
 * with a positive remainder (paid bills are excluded even though `groups` includes them by design,
 * S66 contract). Exported so it is directly testable without mounting the component.
 */
export function deriveOpenBills(board: MonthBoard): Bill[] {
  return board.groups
    .flatMap((group) => group.bills)
    .filter((bill) => (bill.amount_remaining ?? 0) > 0);
}

interface ClosePreflightProps {
  year: number;
  month: number;
  onConfirmationChange: (confirmed: boolean) => void;
}

/**
 * Informative preflight shown inside the "Fechar mês" dialog (S76, design §6): fetches the
 * competence's month_board and lists the bills still open, requiring an explicit confirmation
 * checkbox before the dialog's confirm button unlocks. A failed board fetch does NOT block
 * closing — the backend guard remains the real barrier (design constraint, "preflight é
 * informativo, não barreira").
 */
export function ClosePreflight({ year, month, onConfirmationChange }: ClosePreflightProps) {
  const { data: board, isLoading, isError } = useMonthBoard(year, month);

  const openBills = board ? deriveOpenBills(board) : [];
  const openCount = openBills.length;
  const hasOpenBills = openCount > 0;

  useEffect(() => {
    if (isLoading) return;
    if (isError || !hasOpenBills) {
      onConfirmationChange(true);
      return;
    }
    onConfirmationChange(false);
  }, [isLoading, isError, hasOpenBills, onConfirmationChange]);

  if (isLoading) {
    return (
      <div className="space-y-2">
        <Skeleton className="h-4 w-3/4" />
        <Skeleton className="h-4 w-1/2" />
      </div>
    );
  }

  if (isError) {
    return (
      <Alert variant="destructive">
        <AlertTriangle className="h-4 w-4" />
        <AlertDescription>
          Não foi possível verificar as contas em aberto desta competência.
        </AlertDescription>
      </Alert>
    );
  }

  if (!hasOpenBills) {
    return <p className="text-sm text-success">Nenhuma conta em aberto nesta competência.</p>;
  }

  const preview = openBills.slice(0, PREVIEW_LIMIT);
  const remainingTotal = board?.totals.remaining ?? '0.00';

  return (
    <div className="space-y-3">
      <Alert variant="destructive">
        <AlertTriangle className="h-4 w-4" />
        <AlertDescription>
          <span className="font-medium">{openCount} conta(s) em aberto</span> totalizando{' '}
          <span className="font-medium">{formatCurrency(remainingTotal)}</span>
          <ul className="mt-2 list-disc space-y-0.5 pl-4">
            {preview.map((bill) => (
              <li key={bill.id}>
                {bill.description} — {formatCurrency(bill.amount_remaining ?? 0)}
              </li>
            ))}
          </ul>
        </AlertDescription>
      </Alert>
      <div className="flex items-start gap-2">
        <Checkbox
          id="close-preflight-confirm"
          onCheckedChange={(checked) => onConfirmationChange(checked === true)}
        />
        <Label htmlFor="close-preflight-confirm" className="text-sm font-normal">
          Entendo que essas contas permanecerão em aberto e desejo fechar mesmo assim
        </Label>
      </div>
    </div>
  );
}
