'use client';

import {
  Area,
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
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { formatCurrency, MONTH_ABBR } from '@/lib/utils/formatters';
import type { CondoSimulationResult } from '@/lib/api/hooks/use-condo-projection';

function toNumber(value: number | string): number {
  return typeof value === 'string' ? parseFloat(value) : value;
}

function monthLabel(year: number, month: number): string {
  return `${MONTH_ABBR[month - 1] ?? ''}/${String(year).slice(2)}`;
}

function signClass(value: number): string {
  return value >= 0 ? 'text-success' : 'text-destructive';
}

interface SimulationComparisonProps {
  result: CondoSimulationResult;
}

export function SimulationComparison({ result }: SimulationComparisonProps) {
  const rows = result.comparison.months;
  const chartData = rows.map((m) => ({
    label: monthLabel(m.year, m.month),
    base: toNumber(m.base_cumulative_cash),
    simulated: toNumber(m.simulated_cumulative_cash),
    delta: toNumber(m.cumulative_delta),
  }));
  const finalDelta = toNumber(result.comparison.final_cumulative_delta);
  const totalNetDelta = toNumber(result.comparison.total_net_delta);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Comparativo: base × simulado</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex flex-wrap gap-6 text-sm">
          <div>
            <span className="text-muted-foreground">Δ Caixa final: </span>
            <span className={`font-semibold ${signClass(finalDelta)}`}>
              {formatCurrency(result.comparison.final_cumulative_delta)}
            </span>
          </div>
          <div>
            <span className="text-muted-foreground">Δ Resultado total: </span>
            <span className={`font-semibold ${signClass(totalNetDelta)}`}>
              {formatCurrency(result.comparison.total_net_delta)}
            </span>
          </div>
        </div>

        {/* Non-blocking chart (§10/§12). */}
        <ResponsiveContainer width="100%" height={320}>
          <ComposedChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
            <XAxis dataKey="label" className="text-xs" />
            <YAxis
              tickFormatter={(v: number) => `${(v / 1000).toFixed(0)}k`}
              className="text-xs"
            />
            <Tooltip formatter={(v: number) => formatCurrency(v)} />
            <Legend />
            <Area
              type="monotone"
              dataKey="delta"
              name="Δ"
              fill="var(--info)"
              stroke="var(--info)"
              opacity={0.2}
            />
            <Line
              type="monotone"
              dataKey="base"
              name="Base"
              stroke="var(--muted-foreground)"
              strokeWidth={2}
              dot={false}
            />
            <Line
              type="monotone"
              dataKey="simulated"
              name="Simulado"
              stroke="var(--info)"
              strokeWidth={2}
              strokeDasharray="5 5"
              dot={false}
            />
          </ComposedChart>
        </ResponsiveContainer>

        {/* Delta sub-table (load-bearing). */}
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Mês</TableHead>
                <TableHead className="text-right">Resultado base</TableHead>
                <TableHead className="text-right">Resultado sim.</TableHead>
                <TableHead className="text-right">Δ Resultado</TableHead>
                <TableHead className="text-right">Δ Acumulado</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.map((m) => {
                const netDelta = toNumber(m.net_delta);
                const cumulativeDelta = toNumber(m.cumulative_delta);
                return (
                  <TableRow key={`${m.year}-${m.month}`}>
                    <TableCell className="font-medium">{monthLabel(m.year, m.month)}</TableCell>
                    <TableCell className="text-right">{formatCurrency(m.base_net)}</TableCell>
                    <TableCell className="text-right">{formatCurrency(m.simulated_net)}</TableCell>
                    <TableCell className={`text-right font-medium ${signClass(netDelta)}`}>
                      {formatCurrency(m.net_delta)}
                    </TableCell>
                    <TableCell className={`text-right ${signClass(cumulativeDelta)}`}>
                      {formatCurrency(m.cumulative_delta)}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  );
}
