'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
  TableFooter,
} from '@/components/ui/table';
import { formatCurrency } from '@/lib/utils/formatters';
import type { ComparisonMonth } from '@/lib/api/hooks/use-simulation';

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

function toNumber(val: number | string): number {
  return typeof val === 'string' ? parseFloat(val) : val;
}

interface ComparisonTableProps {
  months: ComparisonMonth[];
}

export function ComparisonTable({ months }: ComparisonTableProps) {
  const totalBaseBal = months.reduce((sum, m) => sum + toNumber(m.base_balance), 0);
  const totalSimBal = months.reduce((sum, m) => sum + toNumber(m.simulated_balance), 0);
  const totalDelta = months.reduce((sum, m) => sum + toNumber(m.delta), 0);

  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardHeader>
        <CardTitle>Comparativo Mês a Mês</CardTitle>
      </CardHeader>
      <CardContent className="overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Mês</TableHead>
              <TableHead className="text-right">Saldo Base</TableHead>
              <TableHead className="text-right">Acum. Base</TableHead>
              <TableHead className="text-right">Saldo Sim.</TableHead>
              <TableHead className="text-right">Acum. Sim.</TableHead>
              <TableHead className="text-right">Delta</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {months.map((m) => {
              const delta = toNumber(m.delta);
              const monthName = MONTH_NAMES[m.month - 1] ?? '';
              const shortYear = String(m.year).slice(2);

              return (
                <TableRow key={`${m.year}-${m.month}`}>
                  <TableCell className="font-medium">
                    {monthName}/{shortYear}
                  </TableCell>
                  <TableCell className="text-right">
                    {formatCurrency(m.base_balance)}
                  </TableCell>
                  <TableCell className="text-right">
                    {formatCurrency(m.base_cumulative)}
                  </TableCell>
                  <TableCell className="text-right">
                    {formatCurrency(m.simulated_balance)}
                  </TableCell>
                  <TableCell className="text-right">
                    {formatCurrency(m.simulated_cumulative)}
                  </TableCell>
                  <TableCell
                    className={`text-right font-medium ${delta >= 0 ? 'text-success' : 'text-destructive'}`}
                  >
                    {delta >= 0 ? '+' : ''}
                    {formatCurrency(delta)}
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
          <TableFooter>
            <TableRow>
              <TableCell className="font-bold">Total</TableCell>
              <TableCell className="text-right font-bold">
                {formatCurrency(totalBaseBal)}
              </TableCell>
              <TableCell />
              <TableCell className="text-right font-bold">
                {formatCurrency(totalSimBal)}
              </TableCell>
              <TableCell />
              <TableCell
                className={`text-right font-bold ${totalDelta >= 0 ? 'text-success' : 'text-destructive'}`}
              >
                {totalDelta >= 0 ? '+' : ''}
                {formatCurrency(totalDelta)}
              </TableCell>
            </TableRow>
          </TableFooter>
        </Table>
      </CardContent>
    </Card>
  );
}
