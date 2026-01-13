'use client';

import { DollarSign, Home, AlertTriangle } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Loading } from '@/components/shared/loading';
import { useDashboardFinancialSummary } from '@/lib/api/hooks/use-dashboard';
import { cn } from '@/lib/utils';

interface StatisticCardProps {
  title: string;
  value: number | string;
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
  // Handle both number and string values (backend returns Decimal as string)
  const numValue = typeof value === 'string' ? parseFloat(value) : value;
  const displayValue = isNaN(numValue) ? '0.00' : numValue.toFixed(2);

  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        {icon && <div className="h-5 w-5 text-muted-foreground">{icon}</div>}
      </CardHeader>
      <CardContent>
        <div className={cn('text-3xl font-bold', valueColor)}>
          {prefix}
          {displayValue}
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
        value={data.total_income}
        prefix="R$ "
        icon={<DollarSign />}
        valueColor="text-green-600"
        description="Soma de aluguéis + taxas"
      />

      <StatisticCard
        title="Receita por Apartamento"
        value={data.revenue_per_apartment}
        prefix="R$ "
        description="Média por apartamento alugado"
      />

      <StatisticCard
        title="Taxa de Ocupação"
        value={data.occupancy_rate}
        suffix="%"
        icon={<Home />}
        valueColor={getOccupancyColor(data.occupancy_rate)}
        description={`${data.rented_apartments} de ${data.total_apartments} apartamentos`}
      />

      <StatisticCard
        title="Apartamentos Vagos"
        value={data.vacant_apartments}
        icon={<AlertTriangle />}
        valueColor={data.vacant_apartments > 0 ? 'text-orange-500' : 'text-green-600'}
        description="Disponíveis para locação"
      />
    </div>
  );
}
