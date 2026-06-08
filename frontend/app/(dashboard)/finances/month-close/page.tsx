'use client';

import { useState, useEffect, useCallback } from 'react';
import { Lock, Unlock } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';
import { DataTable, type Column } from '@/components/tables/data-table';
import { AmountDisplay } from '@/components/ui/amount-display';
import { cn } from '@/lib/utils';
import {
  useCondoMonthCloses,
  useCloseMonth,
  useReopenMonth,
} from '@/lib/api/hooks/use-condo-month-closes';
import { useAuthStore } from '@/store/auth-store';
import { formatDate } from '@/lib/utils/formatters';
import { formatReferenceMonth } from '@/lib/utils/finances';
import { getErrorMessage, handleError } from '@/lib/utils/error-handler';
import type { CondoMonthClose } from '@/lib/schemas/finances/condo-month-close.schema';
import { MonthCloseActionDialog } from './_components/month-close-action-dialog';

function createColumns(handlers: {
  onClose: (record: CondoMonthClose) => void;
  onReopen: (record: CondoMonthClose) => void;
  isStaff: boolean;
}): Column<CondoMonthClose>[] {
  return [
    {
      title: 'Mês de Referência',
      key: 'reference_month',
      primary: true,
      render: (_, rec) => formatReferenceMonth(rec.reference_month),
      sorter: (a, b) => a.reference_month.localeCompare(b.reference_month),
    },
    {
      title: 'Status',
      key: 'status',
      width: 110,
      render: (_, rec) => (
        <Badge
          className={cn(
            'inline-flex items-center gap-1',
            rec.status === 'closed' ? 'bg-success/10 text-success' : 'bg-warning/10 text-warning',
          )}
        >
          {rec.status === 'closed' ? <Lock className="h-3 w-3" /> : <Unlock className="h-3 w-3" />}
          {rec.status === 'closed' ? 'Fechado' : 'Aberto'}
        </Badge>
      ),
    },
    {
      title: 'Resultado',
      key: 'net_result',
      width: 150,
      render: (_, rec) => <AmountDisplay amount={rec.net_result} autoTone />,
    },
    {
      title: 'Caixa Final',
      key: 'cash_balance_end',
      width: 150,
      render: (_, rec) => <AmountDisplay amount={rec.cash_balance_end} tone="info" />,
    },
    {
      title: 'Reserva Final',
      key: 'reserve_balance_end',
      width: 150,
      render: (_, rec) => <AmountDisplay amount={rec.reserve_balance_end} tone="info" />,
    },
    {
      title: 'Fechado em',
      key: 'closed_at',
      width: 130,
      render: (_, rec) =>
        rec.closed_at ? formatDate(rec.closed_at) : <span className="text-muted-foreground">-</span>,
    },
    ...(handlers.isStaff
      ? [
          {
            title: 'Ações',
            key: 'actions',
            width: 130,
            isActions: true,
            fixed: 'right' as const,
            render: (_: unknown, rec: CondoMonthClose) => (
              <div className="flex gap-1">
                {rec.status === 'open' ? (
                  <Button
                    size="sm"
                    variant="outline"
                    aria-label="Fechar mês"
                    onClick={() => handlers.onClose(rec)}
                  >
                    Fechar
                  </Button>
                ) : (
                  <Button
                    size="sm"
                    variant="outline"
                    aria-label="Reabrir mês"
                    onClick={() => handlers.onReopen(rec)}
                  >
                    Reabrir
                  </Button>
                )}
              </div>
            ),
          },
        ]
      : []),
  ];
}

export default function MonthClosePage() {
  const { user } = useAuthStore();
  const isStaff = user?.is_staff ?? false;

  const { data: closes, isLoading, error } = useCondoMonthCloses();
  const closeMutation = useCloseMonth();
  const reopenMutation = useReopenMonth();

  const [dialogRecord, setDialogRecord] = useState<CondoMonthClose | null>(null);
  const [dialogAction, setDialogAction] = useState<'close' | 'reopen'>('close');

  useEffect(() => {
    if (error) toast.error('Erro ao carregar fechamentos mensais');
  }, [error]);

  const openCloseDialog = useCallback((record: CondoMonthClose) => {
    setDialogRecord(record);
    setDialogAction('close');
  }, []);

  const openReopenDialog = useCallback((record: CondoMonthClose) => {
    setDialogRecord(record);
    setDialogAction('reopen');
  }, []);

  const handleConfirm = async () => {
    if (!dialogRecord?.reference_month) return;
    const [year, month] = dialogRecord.reference_month.split('-').map(Number);
    try {
      if (dialogAction === 'close') {
        await closeMutation.mutateAsync({ year: year ?? 0, month: month ?? 0 });
        toast.success('Mês fechado com sucesso');
      } else {
        await reopenMutation.mutateAsync({ year: year ?? 0, month: month ?? 0 });
        toast.success('Mês reaberto com sucesso');
      }
      setDialogRecord(null);
    } catch (err) {
      // Surface the backend's PT message (gap / already-closed / not-found) — the chronological
      // guard lives in the service, the front only displays it (design §4.7/§18).
      toast.error(
        getErrorMessage(err, dialogAction === 'close' ? 'Erro ao fechar mês' : 'Erro ao reabrir mês'),
      );
      handleError(err, 'MonthClosePage.handleConfirm');
    }
  };

  const columns = createColumns({
    onClose: openCloseDialog,
    onReopen: openReopenDialog,
    isStaff,
  });

  const isPending = closeMutation.isPending || reopenMutation.isPending;

  return (
    <div>
      <div className="mb-4 flex justify-between items-center flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold">Fechamento Mensal</h1>
          <p className="text-muted-foreground mt-1">
            Histórico de fechamentos e saldos do condomínio
          </p>
        </div>
      </div>

      <DataTable<CondoMonthClose>
        columns={columns}
        dataSource={closes}
        loading={isLoading}
        rowKey="id"
      />

      <MonthCloseActionDialog
        open={dialogRecord !== null}
        close={dialogRecord}
        action={dialogAction}
        isPending={isPending}
        onConfirm={() => { void handleConfirm(); }}
        onCancel={() => setDialogRecord(null)}
      />
    </div>
  );
}
