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
  ReferenceLine,
} from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import type { DailyBreakdownDay } from '@/lib/api/hooks/use-daily-control';
import { formatCurrency } from '@/lib/utils/formatters';

interface Props {
  data: DailyBreakdownDay[];
  isLoading: boolean;
}

interface ChartDataItem {
  day: number;
  entries: number;
  exits: number;
  cumulative: number;
  isFuture: boolean;
}

interface TooltipPayloadItem {
  dataKey: string;
  value: number;
  color: string;
  payload: ChartDataItem;
}

function toChartData(days: DailyBreakdownDay[]): ChartDataItem[] {
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  return days.map((d) => {
    const dayDate = new Date(d.date);
    dayDate.setHours(0, 0, 0, 0);
    const dayNum = parseInt(d.date.split('-')[2] ?? '0', 10);
    return {
      day: dayNum,
      entries: d.total_entries,
      exits: d.total_exits,
      cumulative: d.cumulative_balance,
      isFuture: dayDate > today,
    };
  });
}

function CustomTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: TooltipPayloadItem[];
  label?: string | number;
}) {
  if (!active || !payload?.length) return null;

  const first = payload[0];
  if (!first) return null;

  const item = first.payload;

  return (
    <div className="bg-card border rounded-lg shadow-lg p-4">
      <p className="font-bold mb-2">Dia {label}{item.isFuture ? ' (futuro)' : ''}</p>
      <p className="text-sm">
        <span className="text-muted-foreground">Entradas: </span>
        <span className="font-medium text-green-600">{formatCurrency(item.entries)}</span>
      </p>
      <p className="text-sm">
        <span className="text-muted-foreground">Saídas: </span>
        <span className="font-medium text-red-600">{formatCurrency(item.exits)}</span>
      </p>
      <p className="text-sm border-t mt-1 pt-1">
        <span className="text-muted-foreground">Saldo Acumulado: </span>
        <span className="font-medium text-blue-600">{formatCurrency(item.cumulative)}</span>
      </p>
    </div>
  );
}

function ChartSkeleton() {
  return (
    <Card>
      <CardHeader>
        <Skeleton className="h-6 w-48" />
      </CardHeader>
      <CardContent>
        <Skeleton className="h-64 w-full" />
      </CardContent>
    </Card>
  );
}

export function DailyBalanceChart({ data, isLoading }: Props) {
  if (isLoading) {
    return <ChartSkeleton />;
  }

  if (data.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Fluxo Diário</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-center text-muted-foreground py-8">Nenhum dado disponível para o período</p>
        </CardContent>
      </Card>
    );
  }

  const today = new Date();
  const todayDay = today.getDate();

  const chartData = toChartData(data);

  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardHeader>
        <CardTitle>Fluxo Diário</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={350}>
          <ComposedChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
            <XAxis dataKey="day" className="text-xs" />
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
            <ReferenceLine
              yAxisId="left"
              x={todayDay}
              stroke="#6366f1"
              strokeDasharray="4 4"
              label={{ value: 'Hoje', position: 'top', fontSize: 11 }}
            />
            <Bar
              yAxisId="left"
              dataKey="entries"
              name="Entradas"
              fill="#22c55e"
              radius={[4, 4, 0, 0]}
              opacity={0.85}
            />
            <Bar
              yAxisId="left"
              dataKey="exits"
              name="Saídas"
              fill="#ef4444"
              radius={[4, 4, 0, 0]}
              opacity={0.85}
            />
            <Line
              yAxisId="right"
              type="monotone"
              dataKey="cumulative"
              name="Saldo Acumulado"
              stroke="#3b82f6"
              strokeWidth={2}
              dot={{ r: 3 }}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
