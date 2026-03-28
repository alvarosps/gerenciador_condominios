'use client';

import { useState } from 'react';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useDashboardSummary } from '@/lib/api/hooks/use-financial-dashboard';
import { useAuthStore } from '@/store/auth-store';
import { formatCurrency } from '@/lib/utils/formatters';
import { MonthNavigator } from './_components/month-navigator';
import { ExpenseListTable } from './_components/expense-list-table';
import { PaymentScheduleConfig } from './_components/payment-schedule-config';

export default function ExpensesPage() {
  const now = new Date();
  const [year, setYear] = useState(now.getFullYear());
  const [month, setMonth] = useState(now.getMonth() + 1);
  const { data, isLoading, error } = useDashboardSummary(year, month);
  const { user } = useAuthStore();
  const isAdmin = user?.is_staff ?? false;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Despesas</h1>
        <p className="text-muted-foreground mt-1">Gerencie despesas mensais</p>
      </div>

      <Tabs defaultValue="despesas">
        <TabsList>
          <TabsTrigger value="despesas">Despesas</TabsTrigger>
          <TabsTrigger value="agenda">Agenda de Pagamentos</TabsTrigger>
        </TabsList>

        <TabsContent value="despesas">
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
                    <span className="font-bold text-destructive">
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
        </TabsContent>

        <TabsContent value="agenda">
          <Card>
            <CardContent className="pt-6">
              <PaymentScheduleConfig isAdmin={isAdmin} />
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
