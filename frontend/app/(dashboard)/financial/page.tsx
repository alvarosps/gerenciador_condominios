'use client';

import { Card, CardContent } from '@/components/ui/card';
import { useDashboardSummary } from '@/lib/api/hooks/use-financial-dashboard';
import { formatMonthYear } from '@/lib/utils/formatters';
import { BalanceCards, BalanceCardsSkeleton } from './_components/balance-cards';
import { IncomeSummaryCard } from './_components/income-summary-card';
import { OtherIncomeCard } from './_components/other-income-card';
import { ExpenseSummaryCard } from './_components/expense-summary-card';
import { OverdueSection } from './_components/overdue-section';
import { CashFlowChart } from './_components/cash-flow-chart';
import { CategoryBreakdownChart } from './_components/category-breakdown-chart';

export default function FinancialDashboardPage() {
  const now = new Date();
  const year = now.getFullYear();
  const month = now.getMonth() + 1;
  const { data, isLoading, error } = useDashboardSummary(year, month);
  const monthLabel = formatMonthYear(year, month);

  return (
    <div className="space-y-6">
      <div className="mb-2">
        <h1 className="text-3xl font-bold">Dashboard Financeiro</h1>
        <p className="text-muted-foreground mt-1">Visão geral das finanças — {monthLabel}</p>
      </div>

      {isLoading && <BalanceCardsSkeleton />}

      {error && !data && (
        <Card>
          <CardContent className="pt-6">
            <p className="text-center text-muted-foreground">Erro ao carregar dashboard</p>
          </CardContent>
        </Card>
      )}

      {data && (
        <>
          <BalanceCards data={data} monthLabel={monthLabel} />
          <IncomeSummaryCard data={data} monthLabel={monthLabel} />
          <OtherIncomeCard
            extraIncomes={data.income_summary.extra_incomes}
            extraIncomeTotal={data.income_summary.extra_income_total}
            monthLabel={monthLabel}
          />
          <ExpenseSummaryCard data={data} monthLabel={monthLabel} />
          <OverdueSection items={data.overdue_items} />
        </>
      )}

      <CashFlowChart
        currentMonthOverride={
          data
            ? {
                year,
                month,
                income: data.current_month_income,
                expenses: data.current_month_expenses,
              }
            : undefined
        }
      />

      <CategoryBreakdownChart />
    </div>
  );
}
