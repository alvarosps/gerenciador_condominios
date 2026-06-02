'use client';

import { Building2, Check, Clock } from 'lucide-react';
import { formatCurrency, formatMonthYear } from '@/lib/utils/formatters';
import type { RentCalendarStats } from '@/lib/api/hooks/use-rent-calendar';

interface RentStatsPanelProps {
  stats: RentCalendarStats;
  year: number;
  month: number;
}

export function RentStatsPanel({ stats, year, month }: RentStatsPanelProps) {
  const pendingCount = stats.due_count - stats.paid_count;

  return (
    <div className="flex flex-col gap-3">
      <div className="rounded-lg border border-border bg-card p-3">
        <div className="text-xs uppercase tracking-wide text-muted-foreground">Mês</div>
        <div className="text-lg font-semibold">{formatMonthYear(year, month)}</div>
      </div>

      <div className="rounded-lg border border-success/20 bg-success/10 p-3">
        <div className="flex items-center gap-1.5 text-xs font-medium text-success">
          <Check className="h-3.5 w-3.5" />
          Recebido até hoje
        </div>
        <div className="mt-1 text-2xl font-bold text-success">
          {formatCurrency(stats.received_total)}
        </div>
        <div className="text-[11px] text-muted-foreground">
          {stats.paid_count} de {stats.due_count} aluguéis pagos
        </div>
      </div>

      <div className="rounded-lg border border-amber-500/20 bg-amber-500/10 p-3">
        <div className="flex items-center gap-1.5 text-xs font-medium text-amber-600 dark:text-amber-400">
          <Clock className="h-3.5 w-3.5" />
          A receber ainda
        </div>
        <div className="mt-1 text-2xl font-bold text-amber-600 dark:text-amber-400">
          {formatCurrency(stats.to_receive_total)}
        </div>
        <div className="text-[11px] text-muted-foreground">
          {pendingCount} pendentes
          {stats.overdue_count > 0 && (
            <>
              {' · '}
              <span className="font-medium text-destructive">
                {stats.overdue_count} em atraso (+{formatCurrency(stats.overdue_total_fee)} multa)
              </span>
            </>
          )}
        </div>
      </div>

      <div className="rounded-lg border border-border bg-card p-3">
        <div className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
          <Building2 className="h-3.5 w-3.5" />
          Kitnets não alugados
        </div>
        <div className="mt-1 flex items-baseline gap-2">
          <span className="text-2xl font-bold">{stats.vacant_kitnets_count}</span>
          <span className="text-sm text-muted-foreground">vagos</span>
        </div>
        <div className="text-[11px] text-muted-foreground">
          Potencial:{' '}
          <span className="font-medium text-foreground">
            {formatCurrency(stats.vacant_kitnets_value)}
          </span>
          /mês
        </div>
      </div>
    </div>
  );
}
