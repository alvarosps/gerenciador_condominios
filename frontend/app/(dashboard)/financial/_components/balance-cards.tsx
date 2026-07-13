'use client';

import { AlertTriangle, DollarSign, TrendingDown, TrendingUp } from 'lucide-react';
import { StatCard } from '@/components/ui/stat-card';
import type { DashboardSummary } from '@/lib/api/hooks/use-financial-dashboard';
import { formatCurrency, formatMonthYear } from '@/lib/utils/formatters';

const BALANCE_CARD_COUNT = 4;

export function BalanceCardsSkeleton() {
  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      {Array.from({ length: BALANCE_CARD_COUNT }, (_, i) => (
        <StatCard key={i} label="" value="" subLabel="" loading />
      ))}
    </div>
  );
}

export function BalanceCards({ data, monthLabel }: { data: DashboardSummary; monthLabel: string }) {
  const balance =
    typeof data.current_month_balance === 'string'
      ? parseFloat(data.current_month_balance)
      : data.current_month_balance;

  const { income_summary } = data;
  const totalEntradas = income_summary.total_monthly_income + income_summary.extra_income_total;
  const prevMonth = data.month === 1 ? 12 : data.month - 1;
  const prevYear = data.month === 1 ? data.year - 1 : data.year;
  const previousMonthLabel = formatMonthYear(prevYear, prevMonth);

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      <StatCard
        label={`Total Entradas no Mês — ${monthLabel}`}
        value={formatCurrency(totalEntradas)}
        icon={<TrendingUp className="h-5 w-5" />}
        tone="info"
        subLabel={
          <span className="space-y-0.5 block">
            <span className="block">
              {income_summary.all_apartments.length} kitnets:{' '}
              {formatCurrency(income_summary.total_monthly_income)}
            </span>
            {income_summary.extra_incomes.map((inc) => (
              <span key={inc.description} className="block">
                {inc.person_name ? `${inc.person_name} - ` : ''}
                {inc.description}: {formatCurrency(inc.amount)}
              </span>
            ))}
          </span>
        }
      />

      <StatCard
        label={`Despesas — ${monthLabel}`}
        value={formatCurrency(data.current_month_expenses)}
        icon={<TrendingDown className="h-5 w-5" />}
        tone="warning"
        subLabel={`Mês: ${formatCurrency(data.monthly_expenses)}${
          data.overdue_total > 0 ? ` + Atrasos: ${formatCurrency(data.overdue_total)}` : ''
        }`}
      />

      <StatCard
        label={`Saldo — ${monthLabel}`}
        value={formatCurrency(balance)}
        icon={<DollarSign className="h-5 w-5" />}
        tone={balance >= 0 ? 'success' : 'destructive'}
        subLabel="Receitas - Despesas"
      />

      <StatCard
        label={`Atrasados — ${previousMonthLabel}`}
        value={formatCurrency(data.overdue_total)}
        icon={<AlertTriangle className="h-5 w-5" />}
        tone={data.overdue_total > 0 ? 'destructive' : 'success'}
        subLabel={
          data.overdue_items.length > 0
            ? `${data.overdue_items.length} item${data.overdue_items.length > 1 ? 's' : ''} em atraso`
            : 'Nenhum atraso'
        }
      />
    </div>
  );
}
