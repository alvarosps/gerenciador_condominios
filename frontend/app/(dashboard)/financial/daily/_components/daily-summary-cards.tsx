'use client';

import { DollarSign, TrendingUp, TrendingDown, AlertTriangle } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { useDailySummary } from '@/lib/api/hooks/use-daily-control';
import { formatCurrency } from '@/lib/utils/formatters';
import { cn } from '@/lib/utils';

interface Props {
  year: number;
  month: number;
}

function SummaryCardSkeleton() {
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

export function DailySummaryCards({ year, month }: Props) {
  const { data, isLoading, error } = useDailySummary(year, month);

  if (isLoading) {
    return (
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <SummaryCardSkeleton />
        <SummaryCardSkeleton />
        <SummaryCardSkeleton />
        <SummaryCardSkeleton />
      </div>
    );
  }

  if (error ?? !data) {
    return (
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardContent className="pt-6">
            <p className="text-center text-muted-foreground">Erro ao carregar resumo</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const currentBalance = typeof data.current_balance === 'string'
    ? parseFloat(data.current_balance)
    : data.current_balance;

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      <Card className="hover:shadow-md transition-shadow">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Saldo Atual</CardTitle>
          <DollarSign className="h-5 w-5 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className={cn('text-3xl font-bold', currentBalance >= 0 ? 'text-green-600' : 'text-red-600')}>
            {formatCurrency(currentBalance)}
          </div>
          <p className="text-xs text-muted-foreground mt-2">Saldo acumulado do mês</p>
        </CardContent>
      </Card>

      <Card className="hover:shadow-md transition-shadow">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Recebido</CardTitle>
          <TrendingUp className="h-5 w-5 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-3xl font-bold text-blue-600">
            {formatCurrency(data.total_received_income)}
          </div>
          <p className="text-xs text-muted-foreground mt-2">
            de {formatCurrency(data.total_expected_income)} esperado
          </p>
        </CardContent>
      </Card>

      <Card className="hover:shadow-md transition-shadow">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Pago</CardTitle>
          <TrendingDown className="h-5 w-5 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-3xl font-bold text-orange-500">
            {formatCurrency(data.total_paid_expenses)}
          </div>
          <p className="text-xs text-muted-foreground mt-2">
            de {formatCurrency(data.total_expected_expenses)} previsto
          </p>
        </CardContent>
      </Card>

      <Card className={cn('hover:shadow-md transition-shadow', data.overdue_count > 0 && 'border-red-200')}>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Vencidas</CardTitle>
          <AlertTriangle className={cn('h-5 w-5', data.overdue_count > 0 ? 'text-red-500' : 'text-muted-foreground')} />
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-2">
            <div className={cn('text-3xl font-bold', data.overdue_count > 0 ? 'text-red-600' : 'text-muted-foreground')}>
              {formatCurrency(data.overdue_total)}
            </div>
            {data.overdue_count > 0 && (
              <Badge variant="destructive" className="shrink-0">
                {data.overdue_count}
              </Badge>
            )}
          </div>
          <p className="text-xs text-muted-foreground mt-2">
            {data.overdue_count === 0 ? 'Nenhum item vencido' : `${data.overdue_count} ${data.overdue_count === 1 ? 'item' : 'itens'} vencido${data.overdue_count === 1 ? '' : 's'}`}
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
