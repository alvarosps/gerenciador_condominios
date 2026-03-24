'use client';

import { DollarSign, TrendingDown, TrendingUp, Home } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import type { DashboardSummary } from '@/lib/api/hooks/use-financial-dashboard';
import { formatCurrency } from '@/lib/utils/formatters';
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

  const totalIncome = typeof data.current_month_income === 'string'
    ? parseFloat(data.current_month_income)
    : data.current_month_income;

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      <Card className="hover:shadow-md transition-shadow">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Entradas no Mês — {monthLabel}</CardTitle>
          <TrendingUp className="h-5 w-5 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-3xl font-bold text-blue-600">
            {formatCurrency(totalIncome)}
          </div>
          <div className="mt-2 space-y-0.5">
            <p className="text-xs text-muted-foreground">
              {data.income_summary.all_apartments.length} kitnets: {formatCurrency(data.income_summary.total_monthly_income)}
            </p>
            {data.income_summary.extra_incomes.map((inc) => (
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
          <CardTitle className="text-sm font-medium">Kitnets Não Alugados</CardTitle>
          <Home className="h-5 w-5 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className={cn(
            'text-3xl font-bold',
            data.income_summary.vacant_count > 0 ? 'text-amber-500' : 'text-green-600',
          )}>
            {formatCurrency(data.income_summary.vacant_lost_rent)}
          </div>
          <p className="text-xs text-muted-foreground mt-1">
            Não alugados: {data.income_summary.vacant_count}
          </p>
          {data.income_summary.vacant_by_building.map((b) => (
            <p key={b.building_name} className="text-xs text-muted-foreground">
              Prédio {b.building_name}: {b.apartments.join(', ')}
            </p>
          ))}
          {data.income_summary.vacant_count === 0 && (
            <p className="text-xs text-muted-foreground">Todos alugados</p>
          )}
        </CardContent>
      </Card>

      <Card className="hover:shadow-md transition-shadow">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Despesas — {monthLabel}</CardTitle>
          <TrendingDown className="h-5 w-5 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-3xl font-bold text-orange-500">
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
          <div className={cn('text-3xl font-bold', balance >= 0 ? 'text-green-600' : 'text-red-600')}>
            {formatCurrency(balance)}
          </div>
          <p className="text-xs text-muted-foreground mt-2">Receitas - Despesas</p>
        </CardContent>
      </Card>
    </div>
  );
}
