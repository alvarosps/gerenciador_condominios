'use client';

import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Table,
  TableBody,
  TableCell,
  TableFooter,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { formatCurrency, MONTH_ABBR } from '@/lib/utils/formatters';
import type { CondoProjectionMonth } from '@/lib/api/hooks/use-condo-projection';

// Decimal-string → number only at this display/reduction boundary (the fold is computed by the
// backend, §4.7 — the table never recomputes cumulative_cash).
function toNumber(value: number | string): number {
  return typeof value === 'string' ? parseFloat(value) : value;
}

function signClass(value: number): string {
  return value >= 0 ? 'text-success' : 'text-destructive';
}

interface ProjectionTableProps {
  months: CondoProjectionMonth[];
}

export function ProjectionTable({ months }: ProjectionTableProps) {
  const totalIncome = months.reduce((sum, m) => sum + toNumber(m.income_total), 0);
  const totalExpenses = months.reduce((sum, m) => sum + toNumber(m.expenses_total), 0);
  const totalNet = months.reduce((sum, m) => sum + toNumber(m.net), 0);
  // The cumulative column is already an anchored fold (§4.7): the final balance is the LAST
  // month's cumulative_cash, NOT the sum of the column (summing it would double-count the fold).
  const finalCumulative = months.at(-1)?.cumulative_cash ?? '0';

  return (
    <Card>
      <CardHeader>
        <CardTitle>Projeção acumulada (12 meses)</CardTitle>
      </CardHeader>
      <CardContent className="overflow-x-auto">
        {months.length === 0 ? (
          <p className="text-sm text-muted-foreground">Nenhum mês para exibir.</p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Mês</TableHead>
                <TableHead className="text-right">Receita</TableHead>
                <TableHead className="text-right">Despesa</TableHead>
                <TableHead className="text-right">Resultado</TableHead>
                <TableHead className="text-right">Acumulado</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {months.map((m) => {
                const net = toNumber(m.net);
                const monthLabel = `${MONTH_ABBR[m.month - 1] ?? ''}/${String(m.year).slice(2)}`;
                return (
                  <TableRow key={`${m.year}-${m.month}`}>
                    <TableCell className="font-medium">
                      <span className="flex items-center gap-2">
                        {monthLabel}
                        {m.is_actual ? (
                          <Badge variant="secondary">Real</Badge>
                        ) : (
                          <Badge variant="outline">Projetado</Badge>
                        )}
                      </span>
                    </TableCell>
                    <TableCell className="text-right">{formatCurrency(m.income_total)}</TableCell>
                    <TableCell className="text-right">{formatCurrency(m.expenses_total)}</TableCell>
                    <TableCell className={`text-right font-medium ${signClass(net)}`}>
                      {formatCurrency(m.net)}
                    </TableCell>
                    <TableCell className="text-right">{formatCurrency(m.cumulative_cash)}</TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
            <TableFooter>
              <TableRow>
                <TableCell className="font-bold">Total</TableCell>
                <TableCell className="text-right font-bold">{formatCurrency(totalIncome)}</TableCell>
                <TableCell className="text-right font-bold">
                  {formatCurrency(totalExpenses)}
                </TableCell>
                <TableCell className={`text-right font-bold ${signClass(totalNet)}`}>
                  {formatCurrency(totalNet)}
                </TableCell>
                {/* Acumulado = último cumulative_cash (saldo final), não a soma da coluna (§4.7). */}
                <TableCell className="text-right font-bold">
                  {formatCurrency(finalCumulative)}
                </TableCell>
              </TableRow>
            </TableFooter>
          </Table>
        )}
      </CardContent>
    </Card>
  );
}
