'use client';

import { DollarSign, TrendingUp, TrendingDown, AlertTriangle } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { StatCard } from '@/components/ui/stat-card';
import { useDailySummary } from '@/lib/api/hooks/use-daily-control';
import { formatCurrency } from '@/lib/utils/formatters';

interface Props {
  year: number;
  month: number;
}

const SUMMARY_CARD_COUNT = 4;

export function DailySummaryCards({ year, month }: Props) {
  const { data, isLoading, error } = useDailySummary(year, month);

  if (isLoading) {
    return (
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: SUMMARY_CARD_COUNT }, (_, i) => (
          <StatCard key={i} label="" value="" subLabel="" loading />
        ))}
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

  const currentBalance =
    typeof data.current_balance === 'string'
      ? parseFloat(data.current_balance)
      : data.current_balance;

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      <StatCard
        label="Saldo Atual"
        value={formatCurrency(currentBalance)}
        icon={<DollarSign className="h-5 w-5" />}
        tone={currentBalance >= 0 ? 'success' : 'destructive'}
        subLabel="Saldo acumulado do mês"
      />

      <StatCard
        label="Recebido"
        value={formatCurrency(data.total_received_income)}
        icon={<TrendingUp className="h-5 w-5" />}
        tone="info"
        subLabel={`de ${formatCurrency(data.total_expected_income)} esperado`}
      />

      <StatCard
        label="Pago"
        value={formatCurrency(data.total_paid_expenses)}
        icon={<TrendingDown className="h-5 w-5" />}
        tone="warning"
        subLabel={`de ${formatCurrency(data.total_expected_expenses)} previsto`}
      />

      <StatCard
        label="Vencidas"
        value={
          <span className="flex items-center gap-2">
            {formatCurrency(data.overdue_total)}
            {data.overdue_count > 0 && (
              <Badge variant="destructive" className="shrink-0">
                {data.overdue_count}
              </Badge>
            )}
          </span>
        }
        icon={<AlertTriangle className="h-5 w-5" />}
        tone={data.overdue_count > 0 ? 'destructive' : 'muted'}
        subLabel={
          data.overdue_count === 0
            ? 'Nenhum item vencido'
            : `${data.overdue_count} ${data.overdue_count === 1 ? 'item' : 'itens'} vencido${data.overdue_count === 1 ? '' : 's'}`
        }
      />
    </div>
  );
}
