'use client';

import { useState, useEffect, useCallback, useMemo } from 'react';
import { ChevronLeft, ChevronRight, Lock, Unlock } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';
import { DataTable, type Column } from '@/components/tables/data-table';
import { AmountDisplay } from '@/components/ui/amount-display';
import { PageHeader } from '@/components/layouts/page-header';
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

/** Previous calendar month relative to today, as a { year, month } pair (1-indexed month). */
function previousMonth(): { year: number; month: number } {
  const now = new Date();
  const year = now.getMonth() === 0 ? now.getFullYear() - 1 : now.getFullYear();
  const month = now.getMonth() === 0 ? 12 : now.getMonth();
  return { year, month };
}

/** Build the `YYYY-MM-01` reference_month string the backend/dialog expect. */
function toReferenceMonth(year: number, month: number): string {
  return `${year}-${String(month).padStart(2, '0')}-01`;
}

/**
 * A synthetic record for a competence that has no CondoMonthClose row yet — lets the
 * existing per-row dialog/mutations drive the "close for the first time" flow from the
 * header selector (U1: the "Fechar" button only shows on rows created by a prior reopen).
 */
function buildDraftClose(year: number, month: number): CondoMonthClose {
  return {
    reference_month: toReferenceMonth(year, month),
    status: 'open',
    net_result: 0,
    cash_balance_end: 0,
    reserve_balance_end: 0,
    carry_forward_out: 0,
  };
}

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
            rec.status === 'closed' ? 'bg-success/10 text-success' : 'bg-warning/10 text-warning'
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
        rec.closed_at ? (
          formatDate(rec.closed_at)
        ) : (
          <span className="text-muted-foreground">-</span>
        ),
    },
    ...(handlers.isStaff
      ? [
          {
            title: 'Ações',
            key: 'actions',
            width: 130,
            isActions: true,
            render: (_: unknown, rec: CondoMonthClose) => (
              <div className="flex gap-1">
                {rec.status === 'open' ? (
                  <Button size="sm" variant="outline" onClick={() => handlers.onClose(rec)}>
                    Fechar
                  </Button>
                ) : (
                  <Button size="sm" variant="outline" onClick={() => handlers.onReopen(rec)}>
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
  const [selectedPeriod, setSelectedPeriod] = useState(previousMonth);

  useEffect(() => {
    if (error) toast.error('Erro ao carregar fechamentos mensais');
  }, [error]);

  const shiftSelectedMonth = (delta: number): void => {
    setSelectedPeriod((prev) => {
      const base = new Date(prev.year, prev.month - 1 + delta, 1);
      return { year: base.getFullYear(), month: base.getMonth() + 1 };
    });
  };

  const selectedReferenceMonth = toReferenceMonth(selectedPeriod.year, selectedPeriod.month);
  const selectedClose = useMemo(
    () => closes?.find((close) => close.reference_month === selectedReferenceMonth) ?? null,
    [closes, selectedReferenceMonth]
  );

  const openCloseDialog = useCallback((record: CondoMonthClose) => {
    setDialogRecord(record);
    setDialogAction('close');
  }, []);

  const openCloseDialogForSelectedMonth = useCallback((): void => {
    openCloseDialog(selectedClose ?? buildDraftClose(selectedPeriod.year, selectedPeriod.month));
  }, [openCloseDialog, selectedClose, selectedPeriod]);

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
        getErrorMessage(
          err,
          dialogAction === 'close' ? 'Erro ao fechar mês' : 'Erro ao reabrir mês'
        )
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
      <PageHeader
        title="Fechamento Mensal"
        description="Histórico de fechamentos e saldos do condomínio"
        actions={
          isStaff && (
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-1">
                <Button
                  variant="outline"
                  size="icon"
                  onClick={() => shiftSelectedMonth(-1)}
                  aria-label="Mês anterior"
                >
                  <ChevronLeft className="h-4 w-4" />
                </Button>
                <span className="min-w-[10rem] text-center text-sm font-medium">
                  {formatReferenceMonth(selectedReferenceMonth)}
                </span>
                <Button
                  variant="outline"
                  size="icon"
                  onClick={() => shiftSelectedMonth(1)}
                  aria-label="Próximo mês"
                >
                  <ChevronRight className="h-4 w-4" />
                </Button>
              </div>
              <Button
                disabled={selectedClose?.status === 'closed'}
                onClick={openCloseDialogForSelectedMonth}
              >
                Fechar mês
              </Button>
            </div>
          )
        }
      />

      {!isLoading && (closes?.length ?? 0) === 0 ? (
        <p className="rounded-md border-2 border-dashed py-12 text-center text-sm text-muted-foreground">
          {isStaff
            ? 'Nenhum fechamento ainda. Use o botão "Fechar mês" para fechar o primeiro mês.'
            : 'Nenhum fechamento ainda.'}
        </p>
      ) : (
        <DataTable<CondoMonthClose>
          columns={columns}
          dataSource={closes}
          loading={isLoading}
          rowKey="id"
        />
      )}

      <MonthCloseActionDialog
        open={dialogRecord !== null}
        close={dialogRecord}
        action={dialogAction}
        isPending={isPending}
        onConfirm={() => {
          void handleConfirm();
        }}
        onCancel={() => setDialogRecord(null)}
      />
    </div>
  );
}
