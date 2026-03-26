'use client';

import { PlusCircle } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import type { ExtraIncome } from '@/lib/api/hooks/use-financial-dashboard';
import { formatCurrency } from '@/lib/utils/formatters';

export function OtherIncomeCard({
  extraIncomes,
  extraIncomeTotal,
  monthLabel,
}: {
  extraIncomes: ExtraIncome[];
  extraIncomeTotal: number;
  monthLabel: string;
}) {
  if (extraIncomes.length === 0) return null;

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base font-semibold flex items-center gap-2">
          <PlusCircle className="h-5 w-5 text-success" />
          Outras Entradas — {monthLabel}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <p className="text-2xl font-bold text-success">{formatCurrency(extraIncomeTotal)}</p>
        <div className="grid gap-3 md:grid-cols-2">
          {extraIncomes.map((inc) => (
            <div
              key={inc.description}
              className="rounded-lg border bg-muted/20 p-3"
              style={{ borderLeftWidth: 3, borderLeftColor: '#22c55e' }}
            >
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-muted-foreground">
                    {inc.person_name ? `${inc.person_name} — ` : ''}
                    {inc.description}
                  </p>
                  <p className="text-lg font-bold">{formatCurrency(inc.amount)}</p>
                </div>
                {inc.is_recurring && (
                  <Badge variant="outline" className="text-[10px] text-success border-success/30 bg-success/10">
                    mensal
                  </Badge>
                )}
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
