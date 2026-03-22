'use client';

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
        <span className="font-medium text-green-600">{formatCurrency(item.income)}</span>
      </p>
      <p className="text-sm">
        <span className="text-muted-foreground">Despesas: </span>
        <span className="font-medium text-red-600">{formatCurrency(item.expenses)}</span>
      </p>
      <p className="text-sm">
        <span className="text-muted-foreground">Saldo Mês: </span>
        <span className="font-medium">{formatCurrency(item.income - item.expenses)}</span>
      </p>
      <p className="text-sm border-t mt-1 pt-1">
        <span className="text-muted-foreground">Saldo Acumulado: </span>
        <span className="font-medium text-blue-600">{formatCurrency(item.cumulative)}</span>
      </p>
    </div>
  );
}

export function CashFlowChart() {
  const { data, isLoading, error } = useCashFlowProjection(12);

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Fluxo de Caixa — 12 Meses</CardTitle>
        </CardHeader>
        <CardContent>
          <Loading />
        </CardContent>
      </Card>
    );
  }

  if (error || !data) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Fluxo de Caixa — 12 Meses</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-center text-muted-foreground py-8">Erro ao carregar fluxo de caixa</p>
        </CardContent>
      </Card>
    );
  }

  if (data.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Fluxo de Caixa — 12 Meses</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-center text-muted-foreground py-8">Nenhum dado disponível</p>
        </CardContent>
      </Card>
    );
  }

  const chartData = toChartData(data);

  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardHeader>
        <CardTitle>Fluxo de Caixa — 12 Meses</CardTitle>
      </CardHeader>
      <CardContent>
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
              fill="#22c55e"
              radius={[4, 4, 0, 0]}
              opacity={0.9}
            />
            <Bar
              yAxisId="left"
              dataKey="expenses"
              name="Despesas"
              fill="#ef4444"
              radius={[4, 4, 0, 0]}
              opacity={0.9}
            />
            <Line
              yAxisId="right"
              type="monotone"
              dataKey="cumulative"
              name="Saldo Acumulado"
              stroke="#3b82f6"
              strokeWidth={2}
              dot={{ r: 4 }}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
