'use client';

import { BalanceCards } from './_components/balance-cards';
import { CashFlowChart } from './_components/cash-flow-chart';
import { PersonSummaryCards } from './_components/person-summary-cards';
import { UpcomingInstallments } from './_components/upcoming-installments';
import { OverdueAlerts } from './_components/overdue-alerts';
import { CategoryBreakdownChart } from './_components/category-breakdown-chart';

export default function FinancialDashboardPage() {
  return (
    <div className="space-y-6">
      <div className="mb-2">
        <h1 className="text-3xl font-bold">Dashboard Financeiro</h1>
        <p className="text-gray-600 mt-1">Visão geral das finanças</p>
      </div>

      <BalanceCards />

      <CashFlowChart />

      <PersonSummaryCards />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <UpcomingInstallments />
        <OverdueAlerts />
      </div>

      <CategoryBreakdownChart />
    </div>
  );
}
