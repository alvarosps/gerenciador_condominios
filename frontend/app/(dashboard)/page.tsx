'use client';

import { FinancialSummaryWidget } from './_components/financial-summary-widget';
import { LeaseMetricsWidget } from './_components/lease-metrics-widget';
import { BuildingStatisticsChart } from './_components/building-statistics-chart';
import { LatePaymentsAlert } from './_components/late-payments-alert';
import { TenantStatisticsWidget } from './_components/tenant-statistics-widget';

export default function DashboardPage() {
  return (
    <div>
      <div className="mb-6">
        <h1 className="text-3xl font-bold">Dashboard</h1>
        <p className="text-gray-600 mt-1">
          Visão geral do sistema de gestão de condomínios
        </p>
      </div>

      <div className="space-y-6">
        {/* Financial Summary - Top Row */}
        <FinancialSummaryWidget />

        {/* Late Payments Alert */}
        <LatePaymentsAlert />

        {/* Metrics Row */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <LeaseMetricsWidget />
          <TenantStatisticsWidget />
        </div>

        {/* Building Statistics Chart - Full Width */}
        <BuildingStatisticsChart />
      </div>
    </div>
  );
}
