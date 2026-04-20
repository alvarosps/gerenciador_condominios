'use client';

import { DollarSign, Home, AlertTriangle } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { DashboardWidgetWrapper } from './dashboard-widget-wrapper';
import { useDashboardFinancialSummary } from '@/lib/api/hooks/use-dashboard';
import { formatCurrency } from '@/lib/utils/formatters';
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
  const displayValue = typeof value === 'string' ? value : String(value);

  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        {icon && <div className="h-5 w-5 text-muted-foreground">{icon}</div>}
      </CardHeader>
      <CardContent>
        <div className={cn('text-xl sm:text-2xl md:text-3xl font-bold', valueColor)}>
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

  if (!data && !isLoading && !error) return null;

  const getOccupancyColor = (rate: number): string => {
    if (rate >= 90) return 'text-success';
    if (rate >= 70) return 'text-info';
    if (rate >= 50) return 'text-warning';
    return 'text-destructive';
  };

  return (
    <DashboardWidgetWrapper
      title="Resumo Financeiro"
      isLoading={isLoading}
      error={error}
      skeletonLines={4}
    >
      {data && (
        <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-4">
          <StatisticCard
            title="Receita Total"
            value={formatCurrency(data.total_income)}
            icon={<DollarSign />}
            valueColor="text-success"
            description="Soma de aluguéis + taxas"
          />

          <StatisticCard
            title="Receita por Apartamento"
            value={formatCurrency(data.revenue_per_apartment)}
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
            valueColor={data.vacant_apartments > 0 ? 'text-warning' : 'text-success'}
            description="Disponíveis para locação"
          />
        </div>
      )}
    </DashboardWidgetWrapper>
  );
}
