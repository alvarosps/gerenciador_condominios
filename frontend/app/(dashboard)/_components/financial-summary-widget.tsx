'use client';

import { DollarSign, Home, AlertTriangle } from 'lucide-react';
import { StatCard, type StatTone } from '@/components/ui/stat-card';
import { DashboardWidgetWrapper } from './dashboard-widget-wrapper';
import { useDashboardFinancialSummary } from '@/lib/api/hooks/use-dashboard';
import { formatCurrency } from '@/lib/utils/formatters';

export function FinancialSummaryWidget() {
  const { data, isLoading, error } = useDashboardFinancialSummary();

  if (!data && !isLoading && !error) return null;

  const getOccupancyTone = (rate: number): StatTone => {
    if (rate >= 90) return 'success';
    if (rate >= 70) return 'info';
    if (rate >= 50) return 'warning';
    return 'destructive';
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
          <StatCard
            label="Receita Total"
            value={formatCurrency(data.total_income)}
            icon={<DollarSign />}
            tone="success"
            subLabel="Soma de aluguéis + taxas"
          />

          <StatCard
            label="Receita por Apartamento"
            value={formatCurrency(data.revenue_per_apartment)}
            subLabel="Média por apartamento alugado"
          />

          <StatCard
            label="Taxa de Ocupação"
            value={`${String(data.occupancy_rate)}%`}
            icon={<Home />}
            tone={getOccupancyTone(data.occupancy_rate)}
            subLabel={`${String(data.rented_apartments)} de ${String(data.total_apartments)} apartamentos`}
          />

          <StatCard
            label="Apartamentos Vagos"
            value={data.vacant_apartments}
            icon={<AlertTriangle />}
            tone={data.vacant_apartments > 0 ? 'warning' : 'success'}
            subLabel="Disponíveis para locação"
          />
        </div>
      )}
    </DashboardWidgetWrapper>
  );
}
