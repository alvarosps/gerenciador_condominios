'use client';

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

interface Props {
  open: boolean;
  close: CondoMonthClose | null;
  action: 'close' | 'reopen';
  isPending: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export function MonthCloseActionDialog({
  open,
  close,
  action,
  isPending,
  onConfirm,
  onCancel,
}: Props) {
  const isClose = action === 'close';
  const label = close ? formatReferenceMonth(close.reference_month) : '';

  return (
    <AlertDialog open={open} onOpenChange={(v) => { if (!v) onCancel(); }}>
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
        <AlertDialogFooter>
          <AlertDialogCancel onClick={onCancel} disabled={isPending}>
            Cancelar
          </AlertDialogCancel>
          <AlertDialogAction onClick={onConfirm} disabled={isPending}>
            {isPending ? 'Aguarde...' : isClose ? 'Fechar mês' : 'Reabrir mês'}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
