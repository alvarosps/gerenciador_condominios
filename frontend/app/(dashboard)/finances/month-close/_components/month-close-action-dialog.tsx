'use client';

import { useCallback, useEffect, useState } from 'react';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { formatReferenceMonth } from '@/lib/utils/finances';
import type { CondoMonthClose } from '@/lib/schemas/finances/condo-month-close.schema';
import { ClosePreflight } from './close-preflight';

interface Props {
  open: boolean;
  close: CondoMonthClose | null;
  action: 'close' | 'reopen';
  /** Competence of `close`, split from `reference_month` by the page (S76 preflight source). */
  year: number;
  month: number;
  isPending: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export function MonthCloseActionDialog({
  open,
  close,
  action,
  year,
  month,
  isPending,
  onConfirm,
  onCancel,
}: Props) {
  const isClose = action === 'close';
  const label = close ? formatReferenceMonth(close.reference_month) : '';

  // Preflight confirmation (close only): starts unconfirmed while the dialog mounts fresh, then
  // ClosePreflight reports true immediately once it resolves without open bills (or on a failed
  // fetch, informative-only per design §6) and false while open bills await the explicit checkbox.
  const [preflightConfirmed, setPreflightConfirmed] = useState(!isClose);

  useEffect(() => {
    if (open) setPreflightConfirmed(!isClose);
  }, [open, isClose]);

  const onConfirmationChange = useCallback((confirmed: boolean) => {
    setPreflightConfirmed(confirmed);
  }, []);

  const confirmDisabled = isPending || (isClose && !preflightConfirmed);

  return (
    <AlertDialog
      open={open}
      onOpenChange={(v) => {
        if (!v) onCancel();
      }}
    >
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>
            {isClose ? 'Fechar mês' : 'Reabrir mês'}: {label}
          </AlertDialogTitle>
          <AlertDialogDescription>
            {isClose
              ? 'Fechar o mês congela os saldos e impede novas movimentações. Confirma?'
              : 'Reabrir o mês permite edição das movimentações. Os saldos serão recalculados ao fechar novamente. Confirma?'}
          </AlertDialogDescription>
        </AlertDialogHeader>
        {isClose && open && (
          <ClosePreflight year={year} month={month} onConfirmationChange={onConfirmationChange} />
        )}
        <AlertDialogFooter>
          <AlertDialogCancel onClick={onCancel} disabled={isPending}>
            Cancelar
          </AlertDialogCancel>
          <AlertDialogAction onClick={onConfirm} disabled={confirmDisabled}>
            {isPending ? 'Aguarde...' : isClose ? 'Fechar mês' : 'Reabrir mês'}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
