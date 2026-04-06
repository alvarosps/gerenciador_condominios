'use client';

import { useCallback, useState } from 'react';
import {
  AlertTriangle,
  CalendarCheck,
  ChevronLeft,
  ChevronRight,
  DollarSign,
  Loader2,
  Rocket,
  RotateCcw,
  Users,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import {
  useAdvanceMonth,
  useMonthPreview,
  useMonthSnapshotDetail,
  useMonthSnapshots,
  useMonthStatus,
  useRollbackMonth,
  type MonthSnapshotSummary,
} from '@/lib/api/hooks/use-month-advance';
import { formatCurrency, formatMonthYear } from '@/lib/utils/formatters';
import { MonthStatusCard } from './_components/month-status-card';
import { AdvanceDialog } from './_components/advance-dialog';
import { RollbackDialog } from './_components/rollback-dialog';
import { SnapshotSummary } from './_components/snapshot-summary';
import { SnapshotHistory } from './_components/snapshot-history';

const MONTH_NAMES = [
  'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
  'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro',
];

function NextMonthPreviewCard({ year, month }: { year: number; month: number }) {
  const { data: preview, isLoading } = useMonthPreview(year, month);

  const nextMonth = month === 12 ? 1 : month + 1;
  const nextYear = month === 12 ? year + 1 : year;
  const nextMonthLabel = formatMonthYear(nextYear, nextMonth);

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <Skeleton className="h-5 w-48" />
        </CardHeader>
        <CardContent className="space-y-2">
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-3/4" />
        </CardContent>
      </Card>
    );
  }

  if (!preview) return null;

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base flex items-center gap-2">
          <CalendarCheck className="h-4 w-4 text-muted-foreground" />
          Prévia: {nextMonthLabel}
        </CardTitle>
        <CardDescription>Informações sobre o próximo mês</CardDescription>
      </CardHeader>

      <CardContent className="space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-sm">
            <DollarSign className="h-4 w-4 text-muted-foreground" />
            <span>Aluguel esperado</span>
          </div>
          <span className="text-sm font-medium text-info">
            {formatCurrency(preview.expected_rent_total)}
          </span>
        </div>

        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-sm">
            <Users className="h-4 w-4 text-muted-foreground" />
            <span>Contratos ativos</span>
          </div>
          <Badge variant="secondary">{preview.active_leases_count}</Badge>
        </div>

        {preview.upcoming_installments_count > 0 && (
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-sm">
              <AlertTriangle className="h-4 w-4 text-muted-foreground" />
              <span>Parcelas vencendo</span>
            </div>
            <div className="text-right">
              <Badge variant="secondary">{preview.upcoming_installments_count}</Badge>
              <p className="text-xs text-muted-foreground mt-0.5">
                {formatCurrency(preview.upcoming_installments_total)}
              </p>
            </div>
          </div>
        )}

        {preview.manual_reminders.length > 0 && (
          <div className="pt-1 border-t">
            <p className="text-xs font-medium text-muted-foreground mb-1">Lembretes</p>
            <ul className="space-y-0.5">
              {preview.manual_reminders.map((reminder, index) => (
                <li key={index} className="text-xs text-muted-foreground flex items-start gap-1">
                  <span className="text-warning mt-0.5">•</span>
                  {reminder}
                </li>
              ))}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default function MonthAdvancePage() {
  const now = new Date();
  const [year, setYear] = useState(now.getFullYear());
  const [month, setMonth] = useState(now.getMonth() + 1);
  const [advanceDialogOpen, setAdvanceDialogOpen] = useState(false);
  const [rollbackDialogOpen, setRollbackDialogOpen] = useState(false);
  const [selectedSnapshot, setSelectedSnapshot] = useState<MonthSnapshotSummary | null>(null);

  const { data: status, isLoading: isStatusLoading } = useMonthStatus(year, month);
  const { data: snapshots, isLoading: isSnapshotsLoading } = useMonthSnapshots(year);

  const selectedSnapshotYear = selectedSnapshot
    ? new Date(selectedSnapshot.reference_month + 'T00:00:00').getFullYear()
    : year;
  const selectedSnapshotMonth = selectedSnapshot
    ? new Date(selectedSnapshot.reference_month + 'T00:00:00').getMonth() + 1
    : month;

  const { data: snapshotDetail, isLoading: isDetailLoading } = useMonthSnapshotDetail(
    selectedSnapshotYear,
    selectedSnapshotMonth,
  );

  const advanceMutation = useAdvanceMonth();
  const rollbackMutation = useRollbackMonth();

  const goToPrevMonth = useCallback(() => {
    setMonth((prev) => {
      if (prev === 1) {
        setYear((y) => y - 1);
        return 12;
      }
      return prev - 1;
    });
  }, []);

  const goToNextMonth = useCallback(() => {
    setMonth((prev) => {
      if (prev === 12) {
        setYear((y) => y + 1);
        return 1;
      }
      return prev + 1;
    });
  }, []);

  const handleAdvanceConfirm = useCallback(
    async (force: boolean, notes: string) => {
      await advanceMutation.mutateAsync({ year, month, force, notes });
      setAdvanceDialogOpen(false);
    },
    [advanceMutation, year, month],
  );

  const handleRollbackConfirm = useCallback(async () => {
    await rollbackMutation.mutateAsync({ year, month, confirm: true });
    setRollbackDialogOpen(false);
  }, [rollbackMutation, year, month]);

  const handleSelectSnapshot = useCallback((snapshot: MonthSnapshotSummary) => {
    setSelectedSnapshot((prev) => (prev?.id === snapshot.id ? null : snapshot));
  }, []);

  const monthLabel = MONTH_NAMES[month - 1] ?? '';
  const isCurrentMonthFinalized = status?.is_finalized ?? false;

  const lastFinalized = snapshots
    ?.filter((s) => s.is_finalized)
    .sort((a, b) => b.reference_month.localeCompare(a.reference_month))[0];

  const isLastFinalizedMonth =
    lastFinalized?.reference_month ===
    `${String(year)}-${String(month).padStart(2, '0')}-01`;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold">Avanço de Mês</h1>
          <p className="text-muted-foreground mt-1">
            Finalize meses e gerencie o histórico financeiro
          </p>
        </div>

        {/* Month Selector */}
        <div className="flex items-center gap-2">
          <Button variant="outline" size="icon" onClick={goToPrevMonth} aria-label="Mês anterior">
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <span className="text-lg font-semibold min-w-[160px] text-center">
            {monthLabel} {year}
          </span>
          <Button variant="outline" size="icon" onClick={goToNextMonth} aria-label="Próximo mês">
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Main content grid */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Left column: Status + Actions */}
        <div className="space-y-4">
          <MonthStatusCard
            status={status}
            isLoading={isStatusLoading}
            year={year}
            month={month}
          />

          {/* Action Buttons */}
          <div className="flex gap-3">
            {!isCurrentMonthFinalized && (
              <Button
                className="flex-1 bg-success hover:bg-success/90"
                onClick={() => setAdvanceDialogOpen(true)}
                disabled={isStatusLoading || advanceMutation.isPending}
              >
                {advanceMutation.isPending ? (
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                ) : (
                  <Rocket className="h-4 w-4 mr-2" />
                )}
                Finalizar Mês
              </Button>
            )}

            {isCurrentMonthFinalized && isLastFinalizedMonth && (
              <Button
                variant="destructive"
                className="flex-1"
                onClick={() => setRollbackDialogOpen(true)}
                disabled={rollbackMutation.isPending}
              >
                {rollbackMutation.isPending ? (
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                ) : (
                  <RotateCcw className="h-4 w-4 mr-2" />
                )}
                Reverter Mês
              </Button>
            )}
          </div>

          {/* Next Month Preview */}
          {!isCurrentMonthFinalized && <NextMonthPreviewCard year={year} month={month} />}
        </div>

        {/* Right column: Snapshot detail or empty state */}
        <div>
          {isDetailLoading && selectedSnapshot && (
            <Card>
              <CardHeader>
                <Skeleton className="h-5 w-48" />
              </CardHeader>
              <CardContent className="space-y-2">
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-3/4" />
              </CardContent>
            </Card>
          )}

          {snapshotDetail && !isDetailLoading && (
            <SnapshotSummary snapshot={snapshotDetail} />
          )}

          {!selectedSnapshot && isCurrentMonthFinalized && status?.snapshot_id && (
            <Card>
              <CardContent className="pt-6">
                <p className="text-center text-sm text-muted-foreground">
                  Selecione um mês no histórico para ver o resumo detalhado
                </p>
              </CardContent>
            </Card>
          )}
        </div>
      </div>

      {/* History */}
      <SnapshotHistory
        snapshots={snapshots}
        isLoading={isSnapshotsLoading}
        onSelectSnapshot={handleSelectSnapshot}
        selectedId={selectedSnapshot?.id ?? null}
      />

      {/* Dialogs */}
      <AdvanceDialog
        open={advanceDialogOpen}
        onClose={() => setAdvanceDialogOpen(false)}
        onConfirm={(force, notes) => void handleAdvanceConfirm(force, notes)}
        year={year}
        month={month}
        status={status}
        isPending={advanceMutation.isPending}
      />

      <RollbackDialog
        open={rollbackDialogOpen}
        onClose={() => setRollbackDialogOpen(false)}
        onConfirm={() => void handleRollbackConfirm()}
        year={year}
        month={month}
        isPending={rollbackMutation.isPending}
      />
    </div>
  );
}
