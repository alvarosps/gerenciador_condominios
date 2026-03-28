'use client';

import { useState } from 'react';
import { Plus } from 'lucide-react';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useDashboardSummary } from '@/lib/api/hooks/use-financial-dashboard';
import { useAuthStore } from '@/store/auth-store';
import { formatCurrency, getDefaultExpenseDate, MONTH_ABBR } from '@/lib/utils/formatters';
import { MonthNavigator } from './_components/month-navigator';
import { ExpenseListTable } from './_components/expense-list-table';
import { PaymentScheduleConfig } from './_components/payment-schedule-config';
import { ExpenseFormModal } from './_components/expense-form-modal';

export default function ExpensesPage() {
  const now = new Date();
  const [year, setYear] = useState(now.getFullYear());
  const [month, setMonth] = useState(now.getMonth() + 1);
  const [isCreating, setIsCreating] = useState(false);
  const [isCreatingNextMonth, setIsCreatingNextMonth] = useState(false);
  const { data, isLoading, error } = useDashboardSummary(year, month);
  const { user } = useAuthStore();
  const isAdmin = user?.is_staff ?? false;

  const nextMonth = month === 12 ? 1 : month + 1;
  const nextYear = month === 12 ? year + 1 : year;
  const currentMonthAbbr = MONTH_ABBR[month - 1] ?? '';
  const nextMonthAbbr = MONTH_ABBR[nextMonth - 1] ?? '';

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
              <div className="flex items-center justify-between flex-wrap gap-3">
                <MonthNavigator
                  year={year}
                  month={month}
                  onMonthChange={(y, m) => { setYear(y); setMonth(m); }}
                />
                <div className="flex items-center gap-3">
                  {data && (
                    <div className="text-sm text-muted-foreground">
                      Total:{' '}
                      <span className="font-bold text-destructive">
                        {formatCurrency(data.expense_summary.total)}
                      </span>
                    </div>
                  )}
                  {isAdmin && (
                    <div className="flex gap-2">
                      <Button size="sm" onClick={() => setIsCreating(true)}>
                        <Plus className="h-4 w-4 mr-2" />
                        Nova Despesa ({currentMonthAbbr})
                      </Button>
                      <Button size="sm" variant="outline" onClick={() => setIsCreatingNextMonth(true)}>
                        <Plus className="h-4 w-4 mr-2" />
                        Nova Despesa ({nextMonthAbbr})
                      </Button>
                    </div>
                  )}
                </div>
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

      {isCreating && (
        <ExpenseFormModal
          open={isCreating}
          onClose={() => setIsCreating(false)}
          defaultExpenseDate={getDefaultExpenseDate(year, month)}
        />
      )}

      {isCreatingNextMonth && (
        <ExpenseFormModal
          open={isCreatingNextMonth}
          onClose={() => setIsCreatingNextMonth(false)}
          defaultExpenseDate={getDefaultExpenseDate(nextYear, nextMonth)}
        />
      )}
    </div>
  );
}
