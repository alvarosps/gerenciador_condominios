'use client';

import { CheckCircle2, ChevronRight } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import type { MonthSnapshotSummary } from '@/lib/api/hooks/use-month-advance';
import { formatCurrency, formatDate, formatMonthYear } from '@/lib/utils/formatters';
import { cn } from '@/lib/utils';

interface SnapshotHistoryProps {
  snapshots: MonthSnapshotSummary[] | undefined;
  isLoading: boolean;
  onSelectSnapshot: (snapshot: MonthSnapshotSummary) => void;
  selectedId: number | null;
}

function HistoryItemSkeleton() {
  return (
    <div className="flex items-center gap-3 p-3">
      <Skeleton className="h-8 w-8 rounded-full flex-shrink-0" />
      <div className="flex-1 space-y-1">
        <Skeleton className="h-4 w-32" />
        <Skeleton className="h-3 w-48" />
      </div>
      <Skeleton className="h-4 w-20" />
    </div>
  );
}

export function SnapshotHistory({
  snapshots,
  isLoading,
  onSelectSnapshot,
  selectedId,
}: SnapshotHistoryProps) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base">Histórico de Fechamentos</CardTitle>
        <CardDescription>Clique em um mês para ver o resumo detalhado</CardDescription>
      </CardHeader>

      <CardContent className="p-0">
        {isLoading && (
          <div className="divide-y">
            <HistoryItemSkeleton />
            <HistoryItemSkeleton />
            <HistoryItemSkeleton />
          </div>
        )}

        {!isLoading && (!snapshots || snapshots.length === 0) && (
          <p className="text-center text-sm text-muted-foreground py-8">
            Nenhum mês finalizado ainda
          </p>
        )}

        {!isLoading && snapshots && snapshots.length > 0 && (
          <div className="divide-y">
            {snapshots.map((snapshot) => {
              const refDate = new Date(snapshot.reference_month + 'T00:00:00');
              const monthLabel = formatMonthYear(refDate.getFullYear(), refDate.getMonth() + 1);
              const netBalance = parseFloat(snapshot.net_balance);
              const isPositive = netBalance >= 0;
              const isSelected = selectedId === snapshot.id;

              return (
                <button
                  key={snapshot.id}
                  type="button"
                  className={cn(
                    'w-full flex items-center gap-3 p-3 text-left hover:bg-muted/50 transition-colors',
                    isSelected && 'bg-muted',
                  )}
                  onClick={() => onSelectSnapshot(snapshot)}
                >
                  <div className="flex h-8 w-8 items-center justify-center rounded-full bg-success/10 flex-shrink-0">
                    <CheckCircle2 className="h-4 w-4 text-success" />
                  </div>

                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium">{monthLabel}</p>
                    <p className="text-xs text-muted-foreground truncate">
                      {snapshot.finalized_at
                        ? `Fechado em ${formatDate(snapshot.finalized_at)}`
                        : 'Data não registrada'}
                    </p>
                  </div>

                  <div className="text-right flex-shrink-0">
                    <p className="text-xs text-muted-foreground">Saldo</p>
                    <p
                      className={cn(
                        'text-sm font-semibold',
                        isPositive ? 'text-success' : 'text-destructive',
                      )}
                    >
                      {formatCurrency(snapshot.net_balance)}
                    </p>
                  </div>

                  <ChevronRight
                    className={cn(
                      'h-4 w-4 text-muted-foreground flex-shrink-0 transition-transform',
                      isSelected && 'rotate-90',
                    )}
                  />
                </button>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
