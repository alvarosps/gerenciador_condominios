'use client';

import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { formatCurrency } from '@/lib/utils/formatters';
import type { MonthlyPurchaseCategoryBreakdown } from '@/lib/api/hooks/use-monthly-purchases';

interface PurchaseCategoryChartProps {
  data: MonthlyPurchaseCategoryBreakdown[];
}

const NO_CATEGORY_COLOR = '#9CA3AF';

function toPieData(data: MonthlyPurchaseCategoryBreakdown[]) {
  return data.map((item) => ({
    name: item.category_name,
    value: typeof item.total === 'string' ? parseFloat(item.total) : item.total,
    color: item.color || NO_CATEGORY_COLOR,
    percentage: item.percentage,
    count: item.count,
  }));
}

type PieDataItem = ReturnType<typeof toPieData>[number];

function CustomTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: { payload: PieDataItem }[];
}) {
  if (!active || !payload?.length) return null;

  const first = payload[0];
  if (!first) return null;
  const item = first.payload;

  return (
    <div className="bg-card border rounded-lg shadow-lg p-3">
      <p className="font-medium" style={{ color: item.color }}>{item.name}</p>
      <p className="text-sm">
        <span className="text-muted-foreground">Valor: </span>
        <span className="font-bold">{formatCurrency(item.value)}</span>
      </p>
      <p className="text-sm">
        <span className="text-muted-foreground">Percentual: </span>
        <span className="font-medium">{item.percentage.toFixed(1)}%</span>
      </p>
      <p className="text-sm">
        <span className="text-muted-foreground">Quantidade: </span>
        <span className="font-medium">{item.count}</span>
      </p>
    </div>
  );
}

export function PurchaseCategoryChart({ data }: PurchaseCategoryChartProps) {
  if (data.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Por Categoria</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-center text-muted-foreground py-8">Nenhuma compra registrada neste mês</p>
        </CardContent>
      </Card>
    );
  }

  const pieData = toPieData(data);

  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardHeader>
        <CardTitle>Por Categoria</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <PieChart>
            <Pie
              data={pieData}
              dataKey="value"
              nameKey="name"
              cx="50%"
              cy="50%"
              outerRadius={100}
              label={(props) =>
                `${String(props.name)} (${(Number(props.percent ?? 0) * 100).toFixed(0)}%)`
              }
              labelLine
            >
              {pieData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
            </Pie>
            <Tooltip content={<CustomTooltip />} />
            <Legend />
          </PieChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
