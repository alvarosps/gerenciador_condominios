'use client';

import { useState, useEffect, useRef, useMemo } from 'react';
import {
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Loading } from '@/components/shared/loading';
import { useCashFlowProjection } from '@/lib/api/hooks/use-cash-flow';
import type { CashFlowProjectionMonth } from '@/lib/api/hooks/use-cash-flow';
import { formatCurrency } from '@/lib/utils/formatters';

const MONTH_NAMES = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'];

interface ChartDataItem {
  label: string;
  income: number;
  expenses: number;
  cumulative: number;
  is_projected: boolean;
}

function formatMonthLabel(year: number, month: number): string {
  const monthName = MONTH_NAMES[month - 1] ?? '';
  const shortYear = String(year).slice(2);
  return `${monthName}/${shortYear}`;
}

function toChartData(data: CashFlowProjectionMonth[]): ChartDataItem[] {
  return data.map((m) => ({
    label: formatMonthLabel(m.year, m.month),
    income: typeof m.income_total === 'string' ? parseFloat(m.income_total) : m.income_total,
    expenses: typeof m.expenses_total === 'string' ? parseFloat(m.expenses_total) : m.expenses_total,
    cumulative: typeof m.cumulative_balance === 'string' ? parseFloat(m.cumulative_balance) : m.cumulative_balance,
    is_projected: m.is_projected,
  }));
}

function CustomTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: { dataKey: string; value: number; color: string; payload: ChartDataItem }[];
  label?: string;
}) {
  if (!active || !payload?.length) return null;

  const first = payload[0];
  if (!first) return null;
  const item = first.payload;

  return (
    <div className="bg-card border rounded-lg shadow-lg p-4">
      <p className="font-bold mb-2">
        {label} {item.is_projected ? '(projetado)' : ''}
      </p>
      <p className="text-sm">
        <span className="text-muted-foreground">Receitas: </span>
        <span className="font-medium text-success">{formatCurrency(item.income)}</span>
      </p>
      <p className="text-sm">
        <span className="text-muted-foreground">Despesas: </span>
        <span className="font-medium text-destructive">{formatCurrency(item.expenses)}</span>
      </p>
      <p className="text-sm">
        <span className="text-muted-foreground">Saldo Mês: </span>
        <span className="font-medium">{formatCurrency(item.income - item.expenses)}</span>
      </p>
      <p className="text-sm border-t mt-1 pt-1">
        <span className="text-muted-foreground">Saldo Acumulado: </span>
        <span className="font-medium text-info">{formatCurrency(item.cumulative)}</span>
      </p>
    </div>
  );
}

function useDebouncedValue<T>(value: T, delay: number): T {
  const [debounced, setDebounced] = useState(value);
  const timerRef = useRef<ReturnType<typeof setTimeout>>();

  useEffect(() => {
    timerRef.current = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(timerRef.current);
  }, [value, delay]);

  return debounced;
}

export function CashFlowChart({
  currentMonthOverride,
}: {
  currentMonthOverride?: { year: number; month: number; income: number; expenses: number };
}) {
  const [fullOccupancyFuture, setFullOccupancyFuture] = useState(false);
  const [fullOccupancyCurrent, setFullOccupancyCurrent] = useState(false);
  const [extraMonthlyInput, setExtraMonthlyInput] = useState('');
  const [monthlyInstallmentInput, setMonthlyInstallmentInput] = useState('');

  const debouncedExtra = useDebouncedValue(extraMonthlyInput, 800);
  const debouncedInstallment = useDebouncedValue(monthlyInstallmentInput, 800);

  const extraMonthlyExpenses = debouncedExtra ? Math.round(Number(debouncedExtra) * 100) / 100 : 0;
  const monthlyInstallmentAmount = debouncedInstallment ? Math.round(Number(debouncedInstallment) * 100) / 100 : 0;

  const { data, isLoading, error } = useCashFlowProjection({
    months: 12,
    fullOccupancyFuture,
    fullOccupancyCurrent,
    extraMonthlyExpenses,
  });

  // All hooks must be above early returns — compute chartData via useMemo
  const chartData = useMemo(() => {
    if (!data || data.length === 0) return null;

    // Override current month with dashboard values for consistency
    let projectionData = data;
    if (currentMonthOverride) {
      const { year, month, income, expenses } = currentMonthOverride;
      let cumulativeDelta = 0;
      projectionData = data.map((m) => {
        if (m.year === year && m.month === month) {
          const newBalance = income - expenses;
          const oldBalance = m.income_total - m.expenses_total;
          cumulativeDelta = newBalance - oldBalance;
          return {
            ...m,
            income_total: income,
            expenses_total: expenses,
            balance: newBalance,
            cumulative_balance: m.cumulative_balance + cumulativeDelta,
          };
        }
        if (cumulativeDelta !== 0) {
          return { ...m, cumulative_balance: m.cumulative_balance + cumulativeDelta };
        }
        return m;
      });
    }

    // Apply cumulative installment simulation
    if (monthlyInstallmentAmount > 0) {
      const firstProjectedIdx = projectionData.findIndex((m) => m.is_projected);
      if (firstProjectedIdx !== -1) {
        let cumulativeInstallmentDelta = 0;
        projectionData = projectionData.map((m, idx) => {
          if (idx < firstProjectedIdx) return m;
          const monthsAhead = idx - firstProjectedIdx + 1;
          const installmentExpense = monthlyInstallmentAmount * monthsAhead;
          cumulativeInstallmentDelta += monthlyInstallmentAmount;
          return {
            ...m,
            expenses_total: m.expenses_total + installmentExpense,
            balance: m.income_total - (m.expenses_total + installmentExpense),
            cumulative_balance: m.cumulative_balance - cumulativeInstallmentDelta,
          };
        });
      }
    }

    return toChartData(projectionData);
  }, [data, currentMonthOverride, monthlyInstallmentAmount]);

  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardHeader>
        <CardTitle>Fluxo de Caixa — 12 Meses</CardTitle>
        <div className="flex flex-wrap items-center gap-6 pt-2">
          <div className="flex items-center gap-2">
            <Checkbox
              id="full-occupancy-future"
              checked={fullOccupancyFuture}
              onCheckedChange={(v) => setFullOccupancyFuture(v === true)}
            />
            <Label htmlFor="full-occupancy-future" className="text-sm cursor-pointer">
              Todos kitnets alugados (meses futuros)
            </Label>
          </div>
          <div className="flex items-center gap-2">
            <Checkbox
              id="full-occupancy-current"
              checked={fullOccupancyCurrent}
              onCheckedChange={(v) => setFullOccupancyCurrent(v === true)}
            />
            <Label htmlFor="full-occupancy-current" className="text-sm cursor-pointer">
              Incluir mês atual
            </Label>
          </div>
          <div className="flex items-center gap-2">
            <Label htmlFor="extra-expenses" className="text-sm whitespace-nowrap">
              Gastos extras/mês:
            </Label>
            <div className="relative w-32">
              <span className="absolute left-2 top-1/2 -translate-y-1/2 text-xs text-muted-foreground">
                R$
              </span>
              <Input
                id="extra-expenses"
                type="number"
                min={0}
                step={100}
                className="h-8 pl-8 text-sm"
                value={extraMonthlyInput}
                onChange={(e) => setExtraMonthlyInput(e.target.value)}
              />
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Label htmlFor="monthly-installments" className="text-sm whitespace-nowrap">
              Parcelas novas/mês:
            </Label>
            <div className="relative w-32">
              <span className="absolute left-2 top-1/2 -translate-y-1/2 text-xs text-muted-foreground">
                R$
              </span>
              <Input
                id="monthly-installments"
                type="number"
                min={0}
                step={100}
                className="h-8 pl-8 text-sm"
                value={monthlyInstallmentInput}
                onChange={(e) => setMonthlyInstallmentInput(e.target.value)}
              />
            </div>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {isLoading && <Loading />}
        {!isLoading && (error !== null && error !== undefined) && (
          <p className="text-center text-muted-foreground py-8">Erro ao carregar fluxo de caixa</p>
        )}
        {!isLoading && chartData === null && (
          <p className="text-center text-muted-foreground py-8">Erro ao carregar fluxo de caixa</p>
        )}
        {!isLoading && (chartData?.length === 0) && (
          <p className="text-center text-muted-foreground py-8">Nenhum dado disponível</p>
        )}
        {!isLoading && chartData && chartData.length > 0 && (
          <ResponsiveContainer width="100%" height={400}>
            <ComposedChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
              <XAxis dataKey="label" className="text-xs" />
              <YAxis
                yAxisId="left"
                orientation="left"
                tickFormatter={(v: number) => `${(v / 1000).toFixed(0)}k`}
                className="text-xs"
              />
              <YAxis
                yAxisId="right"
                orientation="right"
                tickFormatter={(v: number) => `${(v / 1000).toFixed(0)}k`}
                className="text-xs"
              />
              <Tooltip content={<CustomTooltip />} />
              <Legend />
              <Bar
                yAxisId="left"
                dataKey="income"
                name="Receitas"
                fill="var(--success)"
                radius={[4, 4, 0, 0]}
                opacity={0.9}
              />
              <Bar
                yAxisId="left"
                dataKey="expenses"
                name="Despesas"
                fill="var(--destructive)"
                radius={[4, 4, 0, 0]}
                opacity={0.9}
              />
              <Line
                yAxisId="right"
                type="monotone"
                dataKey="cumulative"
                name="Saldo Acumulado"
                stroke="var(--info)"
                strokeWidth={2}
                dot={{ r: 4 }}
              />
            </ComposedChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  );
}
