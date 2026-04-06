'use client';

import { AlertTriangle, DollarSign, TrendingDown, TrendingUp } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import type { DashboardSummary } from '@/lib/api/hooks/use-financial-dashboard';
import { formatCurrency, formatMonthYear } from '@/lib/utils/formatters';
import { cn } from '@/lib/utils';

function BalanceCardSkeleton() {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <Skeleton className="h-4 w-24" />
        <Skeleton className="h-5 w-5 rounded" />
      </CardHeader>
      <CardContent>
        <Skeleton className="h-8 w-32 mb-2" />
        <Skeleton className="h-3 w-20" />
      </CardContent>
    </Card>
  );
}

export function BalanceCardsSkeleton() {
  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      <BalanceCardSkeleton />
      <BalanceCardSkeleton />
      <BalanceCardSkeleton />
      <BalanceCardSkeleton />
    </div>
  );
}

export function BalanceCards({ data, monthLabel }: { data: DashboardSummary; monthLabel: string }) {
  const balance = typeof data.current_month_balance === 'string'
    ? parseFloat(data.current_month_balance)
    : data.current_month_balance;

  const { income_summary } = data;
  const totalEntradas = income_summary.total_monthly_income + income_summary.extra_income_total;
  const prevMonth = data.month === 1 ? 12 : data.month - 1;
  const prevYear = data.month === 1 ? data.year - 1 : data.year;
  const previousMonthLabel = formatMonthYear(prevYear, prevMonth);

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      <Card className="hover:shadow-md transition-shadow">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Total Entradas no Mês — {monthLabel}</CardTitle>
          <TrendingUp className="h-5 w-5 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-3xl font-bold text-info">
            {formatCurrency(totalEntradas)}
          </div>
          <div className="mt-2 space-y-0.5">
            <p className="text-xs text-muted-foreground">
              {income_summary.all_apartments.length} kitnets: {formatCurrency(income_summary.total_monthly_income)}
            </p>
            {income_summary.extra_incomes.map((inc) => (
              <p key={inc.description} className="text-xs text-muted-foreground">
                {inc.person_name ? `${inc.person_name} - ` : ''}
                {inc.description}: {formatCurrency(inc.amount)}
              </p>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card className="hover:shadow-md transition-shadow">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Despesas — {monthLabel}</CardTitle>
          <TrendingDown className="h-5 w-5 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-3xl font-bold text-warning">
            {formatCurrency(data.current_month_expenses)}
          </div>
          <p className="text-xs text-muted-foreground mt-2">
            Mês: {formatCurrency(data.monthly_expenses)}
            {data.overdue_total > 0 && ` + Atrasos: ${formatCurrency(data.overdue_total)}`}
          </p>
        </CardContent>
      </Card>

      <Card className="hover:shadow-md transition-shadow">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Saldo — {monthLabel}</CardTitle>
          <DollarSign className="h-5 w-5 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className={cn('text-3xl font-bold', balance >= 0 ? 'text-success' : 'text-destructive')}>
            {formatCurrency(balance)}
          </div>
          <p className="text-xs text-muted-foreground mt-2">Receitas - Despesas</p>
        </CardContent>
      </Card>

      <Card className="hover:shadow-md transition-shadow">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Atrasados — {previousMonthLabel}</CardTitle>
          <AlertTriangle className={cn('h-5 w-5', data.overdue_total > 0 ? 'text-destructive' : 'text-muted-foreground')} />
        </CardHeader>
        <CardContent>
          <div className={cn('text-3xl font-bold', data.overdue_total > 0 ? 'text-destructive' : 'text-success')}>
            {formatCurrency(data.overdue_total)}
          </div>
          <p className="text-xs text-muted-foreground mt-2">
            {data.overdue_items.length > 0
              ? `${data.overdue_items.length} item${data.overdue_items.length > 1 ? 's' : ''} em atraso`
              : 'Nenhum atraso'}
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
