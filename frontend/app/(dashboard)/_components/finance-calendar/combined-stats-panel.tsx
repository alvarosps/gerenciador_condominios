'use client';

import { AlertTriangle, ArrowDownCircle, CheckCircle2 } from 'lucide-react';
import { formatCurrency, formatMonthYear } from '@/lib/utils/formatters';

/**
 * Lightweight month-summary panel for the combined calendar's 3rd column.
 *
 * The S39 `useCombinedCalendar` hook returns NO `stats` field, so this panel is computed
 * client-side FOR DISPLAY ONLY from the month's bill exits plus the overdue KPI from
 * `useOverdueBills`. Summing displayed remaining amounts for a month KPI is acceptable
 * display aggregation; it is NOT recomputing a single bill's `amount_total` (§4.4 forbids
 * only the latter). No saldo/caixa/reserva here — that is Phase 4.
 */

export interface CombinedStatsPanelProps {
  year: number;
  month: number;
  /** Σ amount_remaining of active, not-paid bill exits in the month (display aggregation). */
  toPayTotal: number;
  /** Count of active bill exits in the month. */
  billsCount: number;
  /** Count of paid bill exits in the month. */
  paidCount: number;
  /** Overdue KPI from useOverdueBills (string Decimal → display only). */
  overdueTotal: string;
  overdueCount: number;
}

export function CombinedStatsPanel({
  year,
  month,
  toPayTotal,
  billsCount,
  paidCount,
  overdueTotal,
  overdueCount,
}: CombinedStatsPanelProps) {
  return (
    <div className="flex flex-col gap-3">
      <div className="rounded-lg border border-border bg-card p-3">
        <div className="text-xs uppercase tracking-wide text-muted-foreground">Mês</div>
        <div className="text-lg font-semibold">{formatMonthYear(year, month)}</div>
      </div>

      <div className="rounded-lg border border-amber-500/20 bg-amber-500/10 p-3">
        <div className="flex items-center gap-1.5 text-xs font-medium text-amber-600 dark:text-amber-400">
          <ArrowDownCircle className="h-3.5 w-3.5" />
          A pagar (mês)
        </div>
        <div className="mt-1 text-2xl font-bold text-amber-600 dark:text-amber-400">
          {formatCurrency(toPayTotal)}
        </div>
        <div className="text-[11px] text-muted-foreground">
          {billsCount} {billsCount === 1 ? 'conta' : 'contas'}
        </div>
      </div>

      <div className="rounded-lg border border-success/20 bg-success/10 p-3">
        <div className="flex items-center gap-1.5 text-xs font-medium text-success">
          <CheckCircle2 className="h-3.5 w-3.5" />
          Contas pagas (mês)
        </div>
        <div className="mt-1 flex items-baseline gap-2">
          <span className="text-2xl font-bold text-success">{paidCount}</span>
          <span className="text-sm text-muted-foreground">de {billsCount}</span>
        </div>
      </div>

      <div className="rounded-lg border border-destructive/20 bg-destructive/10 p-3">
        <div className="flex items-center gap-1.5 text-xs font-medium text-destructive">
          <AlertTriangle className="h-3.5 w-3.5" />
          Em atraso (total)
        </div>
        <div className="mt-1 text-2xl font-bold text-destructive">
          {formatCurrency(overdueTotal)}
        </div>
        <div className="text-[11px] text-muted-foreground">
          {overdueCount} {overdueCount === 1 ? 'conta vencida' : 'contas vencidas'}
        </div>
      </div>
    </div>
  );
}
