'use client';

import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { formatCurrency, MONTH_ABBR } from '@/lib/utils/formatters';
import type { CondoProjectionMonth } from '@/lib/api/hooks/use-condo-projection';

// Non-blocking chart (design §10/§12): the ProjectionTable carries the gate; Recharts SVG is not
// asserted in jsdom. Decimal-string → number only here, at the display boundary.
interface ChartDatum {
  label: string;
  income: number;
  expenses: number;
  cumulative: number;
  is_projected: boolean;
}

function toNumber(value: number | string): number {
  return typeof value === 'string' ? parseFloat(value) : value;
}

function toChartData(months: CondoProjectionMonth[]): ChartDatum[] {
  return months.map((m) => ({
    label: `${MONTH_ABBR[m.month - 1] ?? ''}/${String(m.year).slice(2)}`,
    income: toNumber(m.income_total),
    expenses: toNumber(m.expenses_total),
    cumulative: toNumber(m.cumulative_cash),
    is_projected: !m.is_actual,
  }));
}

function CustomTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: { payload: ChartDatum }[];
  label?: string;
}) {
  if (!active || !payload?.length) return null;
  const first = payload[0];
  if (!first) return null;
  const item = first.payload;
  return (
    <div className="rounded-lg border bg-card p-4 shadow-lg">
      <p className="mb-2 font-bold">
        {label} {item.is_projected ? '(projetado)' : '(real)'}
      </p>
      <p className="text-sm">
        <span className="text-muted-foreground">Receita: </span>
        <span className="font-medium text-success">{formatCurrency(item.income)}</span>
      </p>
      <p className="text-sm">
        <span className="text-muted-foreground">Despesa: </span>
        <span className="font-medium text-destructive">{formatCurrency(item.expenses)}</span>
      </p>
      <p className="mt-1 border-t pt-1 text-sm">
        <span className="text-muted-foreground">Caixa acumulado: </span>
        <span className="font-medium text-info">{formatCurrency(item.cumulative)}</span>
      </p>
    </div>
  );
}

interface ProjectionChartProps {
  months: CondoProjectionMonth[];
}

export function ProjectionChart({ months }: ProjectionChartProps) {
  const data = toChartData(months);
  return (
    <Card>
      <CardHeader>
        <CardTitle>Receita × Despesa × Caixa acumulado</CardTitle>
      </CardHeader>
      <CardContent>
        {data.length === 0 ? (
          <p className="py-8 text-center text-muted-foreground">Nenhum dado disponível</p>
        ) : (
          <ResponsiveContainer width="100%" height={400}>
            <ComposedChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
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
                name="Receita"
                fill="var(--success)"
                radius={[4, 4, 0, 0]}
                opacity={0.9}
              />
              <Bar
                yAxisId="left"
                dataKey="expenses"
                name="Despesa"
                fill="var(--destructive)"
                radius={[4, 4, 0, 0]}
                opacity={0.9}
              />
              <Line
                yAxisId="right"
                type="monotone"
                dataKey="cumulative"
                name="Caixa acumulado"
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
