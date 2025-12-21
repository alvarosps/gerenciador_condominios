'use client';

import { DollarSign, Home, AlertTriangle } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Loading } from '@/components/shared/loading';
import { useDashboardFinancialSummary } from '@/lib/api/hooks/use-dashboard';
import { cn } from '@/lib/utils';

interface StatisticCardProps {
  title: string;
  value: number;
  prefix?: string;
  suffix?: string;
  icon?: React.ReactNode;
  valueColor?: string;
  description?: string;
}

function StatisticCard({
  title,
  value,
  prefix = '',
  suffix = '',
  icon,
  valueColor,
  description,
}: StatisticCardProps) {
  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        {icon && <div className="h-5 w-5 text-muted-foreground">{icon}</div>}
      </CardHeader>
      <CardContent>
        <div className={cn('text-3xl font-bold', valueColor)}>
          {prefix}
          {value.toFixed(2)}
          {suffix}
        </div>
        {description && (
          <p className="text-xs text-muted-foreground mt-2">{description}</p>
        )}
      </CardContent>
    </Card>
  );
}

export function FinancialSummaryWidget() {
  const { data, isLoading, error } = useDashboardFinancialSummary();

  if (isLoading) {
    return (
      <Card>
        <CardContent className="pt-6">
          <Loading tip="Carregando resumo financeiro..." />
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Alert variant="destructive">
        <AlertTriangle className="h-4 w-4" />
        <AlertDescription>
          Erro ao carregar resumo financeiro. Não foi possível carregar os dados. Tente novamente mais tarde.
        </AlertDescription>
      </Alert>
    );
  }

  if (!data) return null;

  const getOccupancyColor = (rate: number): string => {
    if (rate >= 90) return 'text-green-600';
    if (rate >= 70) return 'text-blue-600';
    if (rate >= 50) return 'text-orange-500';
    return 'text-red-600';
  };

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      <StatisticCard
        title="Receita Total"
        value={data.total_revenue}
        prefix="R$ "
        icon={<DollarSign />}
        valueColor="text-green-600"
        description="Soma de todos os aluguéis ativos"
      />

      <StatisticCard
        title="Valor Médio de Aluguel"
        value={data.avg_rental_value}
        prefix="R$ "
        description="Média dos valores de aluguel"
      />

      <StatisticCard
        title="Taxa de Ocupação"
        value={data.occupancy_rate}
        suffix="%"
        icon={<Home />}
        valueColor={getOccupancyColor(data.occupancy_rate)}
        description="Percentual de apartamentos alugados"
      />

      <StatisticCard
        title="Multas por Atraso"
        value={data.total_late_fees}
        prefix="R$ "
        icon={<AlertTriangle />}
        valueColor="text-red-600"
        description="Total de multas calculadas"
      />
    </div>
  );
}
