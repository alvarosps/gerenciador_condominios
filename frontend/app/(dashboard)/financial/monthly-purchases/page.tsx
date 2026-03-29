'use client';

import { useState, useCallback } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { useMonthlyPurchases } from '@/lib/api/hooks/use-monthly-purchases';
import { formatCurrency } from '@/lib/utils/formatters';
import { PurchaseSummaryCards } from './_components/purchase-summary-cards';
import { PurchaseCategoryChart } from './_components/purchase-category-chart';
import { PurchaseTypeChart } from './_components/purchase-type-chart';
import { PurchaseAccordion } from './_components/purchase-accordion';

const MONTH_NAMES = [
  'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
  'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro',
];

export default function MonthlyPurchasesPage() {
  const now = new Date();
  const [year, setYear] = useState(now.getFullYear());
  const [month, setMonth] = useState(now.getMonth() + 1);

  const { data, isLoading, error } = useMonthlyPurchases(year, month);

  const goToPrevMonth = useCallback(() => {
    setMonth((prev) => {
      if (prev === 1) {
        setYear((y) => y - 1);
        return 12;
      }
      return prev - 1;
    });
  }, []);

  const goToNextMonth = useCallback(() => {
    setMonth((prev) => {
      if (prev === 12) {
        setYear((y) => y + 1);
        return 1;
      }
      return prev + 1;
    });
  }, []);

  const monthLabel = MONTH_NAMES[month - 1] ?? '';

  const byType = data?.by_type;
  const byCategory = data?.by_category ?? [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold">Compras do Mês</h1>
          <p className="text-muted-foreground mt-1">
            Novas compras e despesas registradas no período
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="icon" onClick={goToPrevMonth} aria-label="Mês anterior">
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <span className="text-lg font-semibold min-w-[160px] text-center">
            {monthLabel} {year}
          </span>
          <Button variant="outline" size="icon" onClick={goToNextMonth} aria-label="Próximo mês">
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Total badge */}
      {isLoading ? (
        <Skeleton className="h-6 w-48" />
      ) : error ? (
        <p className="text-destructive text-sm">Erro ao carregar dados do mês</p>
      ) : (
        <p className="text-sm text-muted-foreground">
          Total do período:{' '}
          <span className="font-semibold text-foreground">{formatCurrency(data?.total ?? 0)}</span>
        </p>
      )}

      {/* Summary cards */}
      <PurchaseSummaryCards data={byType} isLoading={isLoading} />

      {/* Charts */}
      {!error && (
        <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
          <PurchaseCategoryChart data={byCategory} />
          <PurchaseTypeChart data={byType} />
        </div>
      )}

      {/* Accordions */}
      {!isLoading && !error && byType && (
        <PurchaseAccordion
          cardPurchases={byType.card_purchases}
          loans={byType.loans}
          utilityBills={byType.utility_bills}
          oneTimeExpenses={byType.one_time_expenses}
          fixedExpenses={byType.fixed_expenses}
        />
      )}
    </div>
  );
}
