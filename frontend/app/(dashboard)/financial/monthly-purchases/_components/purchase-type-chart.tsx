'use client';

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { formatCurrency } from '@/lib/utils/formatters';
import type { MonthlyPurchasesResponse } from '@/lib/api/hooks/use-monthly-purchases';

interface PurchaseTypeChartProps {
  data: MonthlyPurchasesResponse['by_type'] | undefined;
}

const TYPE_BARS = [
  { key: 'card_purchases' as const, label: 'Cartão', color: '#3B82F6' },
  { key: 'utility_bills' as const, label: 'Contas', color: '#06B6D4' },
  { key: 'loans' as const, label: 'Empréstimos', color: '#F97316' },
  { key: 'one_time_expenses' as const, label: 'Únicos', color: '#A855F7' },
  { key: 'fixed_expenses' as const, label: 'Fixos', color: '#22C55E' },
] as const;

function CustomTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: { value: number; payload: { color: string } }[];
  label?: string;
}) {
  if (!active || !payload?.length) return null;
  const first = payload[0];
  if (!first) return null;

  return (
    <div className="bg-card border rounded-lg shadow-lg p-3">
      <p className="font-medium" style={{ color: first.payload.color }}>{label}</p>
      <p className="text-sm">
        <span className="text-muted-foreground">Total: </span>
        <span className="font-bold">{formatCurrency(first.value)}</span>
      </p>
    </div>
  );
}

export function PurchaseTypeChart({ data }: PurchaseTypeChartProps) {
  const chartData = TYPE_BARS.map((bar) => ({
    name: bar.label,
    value: data?.[bar.key].total ?? 0,
    color: bar.color,
  }));

  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardHeader>
        <CardTitle>Por Tipo</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={chartData} margin={{ top: 5, right: 10, left: 10, bottom: 5 }}>
            <XAxis dataKey="name" tick={{ fontSize: 12 }} />
            <YAxis tickFormatter={(v: number) => formatCurrency(v)} tick={{ fontSize: 11 }} width={90} />
            <Tooltip content={<CustomTooltip />} />
            <Bar dataKey="value" radius={[4, 4, 0, 0]}>
              {chartData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
