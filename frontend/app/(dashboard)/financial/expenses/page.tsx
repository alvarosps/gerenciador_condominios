'use client';

import { useState } from 'react';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { useDashboardSummary } from '@/lib/api/hooks/use-financial-dashboard';
import { formatCurrency } from '@/lib/utils/formatters';
import { MonthNavigator } from './_components/month-navigator';
import { ExpenseListTable } from './_components/expense-list-table';

export default function ExpensesPage() {
  const now = new Date();
  const [year, setYear] = useState(now.getFullYear());
  const [month, setMonth] = useState(now.getMonth() + 1);
  const { data, isLoading, error } = useDashboardSummary(year, month);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Despesas</h1>
        <p className="text-gray-600 mt-1">Gerencie despesas mensais</p>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <MonthNavigator
              year={year}
              month={month}
              onMonthChange={(y, m) => { setYear(y); setMonth(m); }}
            />
            {data && (
              <div className="text-sm text-muted-foreground">
                Total:{' '}
                <span className="font-bold text-red-600">
                  {formatCurrency(data.expense_summary.total)}
                </span>
              </div>
            )}
          </div>
        </CardHeader>
        <CardContent>
          {isLoading && (
            <div className="space-y-3">
              {Array.from({ length: 8 }).map((_, i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          )}
          {error && !data && (
            <p className="text-center text-muted-foreground py-8">Erro ao carregar despesas</p>
          )}
          {data && <ExpenseListTable data={data} year={year} month={month} />}
        </CardContent>
      </Card>
    </div>
  );
}
