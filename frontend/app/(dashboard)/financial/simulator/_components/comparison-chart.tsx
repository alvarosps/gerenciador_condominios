'use client';

import {
  ComposedChart,
  Line,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { formatCurrency } from '@/lib/utils/formatters';
import type { CashFlowProjectionMonth } from '@/lib/api/hooks/use-cash-flow';

const MONTH_NAMES = [
  'Jan',
  'Fev',
  'Mar',
  'Abr',
  'Mai',
  'Jun',
  'Jul',
  'Ago',
  'Set',
  'Out',
  'Nov',
  'Dez',
];

interface ChartDataItem {
  label: string;
  baseCumulative: number;
  simulatedCumulative?: number;
  delta?: number;
}

function toNumber(val: number | string): number {
  return typeof val === 'string' ? parseFloat(val) : val;
}

function buildChartData(
  base: CashFlowProjectionMonth[],
  simulated?: CashFlowProjectionMonth[],
): ChartDataItem[] {
  return base.map((b, i) => {
    const monthName = MONTH_NAMES[b.month - 1] ?? '';
    const shortYear = String(b.year).slice(2);
    const baseCum = toNumber(b.cumulative_balance);
    const simMonth = simulated?.[i];
    const simCum = simMonth ? toNumber(simMonth.cumulative_balance) : undefined;

    return {
      label: `${monthName}/${shortYear}`,
      baseCumulative: baseCum,
      simulatedCumulative: simCum,
      delta: simCum !== undefined ? simCum - baseCum : undefined,
    };
  });
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
      <p className="font-bold mb-2">{label}</p>
      <p className="text-sm">
        <span className="text-muted-foreground">Cenário Atual: </span>
        <span className="font-medium text-blue-600">{formatCurrency(item.baseCumulative)}</span>
      </p>
      {item.simulatedCumulative !== undefined && (
        <>
          <p className="text-sm">
            <span className="text-muted-foreground">Cenário Simulado: </span>
            <span className="font-medium text-green-600">
              {formatCurrency(item.simulatedCumulative)}
            </span>
          </p>
          <p className="text-sm border-t mt-1 pt-1">
            <span className="text-muted-foreground">Delta: </span>
            <span
              className={`font-medium ${(item.delta ?? 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}
            >
              {(item.delta ?? 0) >= 0 ? '+' : ''}
              {formatCurrency(item.delta ?? 0)}
            </span>
          </p>
        </>
      )}
    </div>
  );
}

interface ComparisonChartProps {
  base: CashFlowProjectionMonth[];
  simulated?: CashFlowProjectionMonth[];
}

export function ComparisonChart({ base, simulated }: ComparisonChartProps) {
  const hasSimulation = simulated && simulated.length > 0;
  const chartData = buildChartData(base, hasSimulation ? simulated : undefined);

  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardHeader>
        <CardTitle>Projeção Comparativa — 12 Meses</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={400}>
          <ComposedChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
            <XAxis dataKey="label" className="text-xs" />
            <YAxis
              tickFormatter={(v: number) => `${(v / 1000).toFixed(0)}k`}
              className="text-xs"
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend />

            {hasSimulation && (
              <Area
                type="monotone"
                dataKey="delta"
                name="Delta"
                fill="#22c55e"
                fillOpacity={0.15}
                stroke="none"
              />
            )}

            <Line
              type="monotone"
              dataKey="baseCumulative"
              name="Cenário Atual"
              stroke="#3b82f6"
              strokeWidth={2}
              dot={{ r: 4 }}
            />

            {hasSimulation && (
              <Line
                type="monotone"
                dataKey="simulatedCumulative"
                name="Cenário Simulado"
                stroke="#22c55e"
                strokeWidth={2}
                dot={{ r: 4 }}
                strokeDasharray="5 5"
              />
            )}
          </ComposedChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
