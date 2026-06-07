'use client';

import { FinancialSummaryWidget } from './_components/financial-summary-widget';
import { LeaseMetricsWidget } from './_components/lease-metrics-widget';
import { BuildingStatisticsChart } from './_components/building-statistics-chart';
import { LatePaymentsAlert } from './_components/late-payments-alert';
import { RentAdjustmentAlerts } from './_components/rent-adjustment-alerts';
import { RentCalendarSection } from './_components/rent-calendar/rent-calendar-section';
import { CombinedCalendarSection } from './_components/finance-calendar/combined-calendar-section';
import { TenantStatisticsWidget } from './_components/tenant-statistics-widget';

export default function DashboardPage() {
  return (
    <div>
      <div className="mb-6">
        <h1 className="text-3xl font-bold">Dashboard</h1>
        <p className="text-muted-foreground mt-1">
          Visão geral do sistema de gestão de condomínios
        </p>
      </div>

      <div className="space-y-6">
        {/* Rent Calendar - Top */}
        <RentCalendarSection />

        {/* Combined Condominium Calendar (rent entries + bill exits) — below the rent calendar */}
        <CombinedCalendarSection />

        {/* Financial Summary - Top Row */}
        <FinancialSummaryWidget />

        {/* Late Payments Alert */}
        <LatePaymentsAlert />

        {/* Rent Adjustment Alerts */}
        <RentAdjustmentAlerts />

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
