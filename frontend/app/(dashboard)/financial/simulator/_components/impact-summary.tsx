'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { formatCurrency } from '@/lib/utils/formatters';
import type { SimulationComparison } from '@/lib/api/hooks/use-simulation';
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

function toNumber(val: number | string): number {
  return typeof val === 'string' ? parseFloat(val) : val;
}

function formatBreakEven(breakEvenMonth: string | null): string {
  if (!breakEvenMonth) return 'Não previsto nos próximos 12 meses';
  const parts = breakEvenMonth.split('-');
  const year = parts[0] ?? '';
  const monthIdx = parseInt(parts[1] ?? '0', 10) - 1;
  const monthName = MONTH_NAMES[monthIdx] ?? '';
  return `${monthName}/${year.slice(2)}`;
}

interface ImpactSummaryProps {
  comparison: SimulationComparison;
  base: CashFlowProjectionMonth[];
  simulated: CashFlowProjectionMonth[];
}

export function ImpactSummary({ comparison, base, simulated }: ImpactSummaryProps) {
  const totalImpact = toNumber(comparison.total_impact_12m);
  const lastBase = base[base.length - 1];
  const lastSimulated = simulated[simulated.length - 1];
  const baseFinal = lastBase ? toNumber(lastBase.cumulative_balance) : 0;
  const simulatedFinal = lastSimulated ? toNumber(lastSimulated.cumulative_balance) : 0;

  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardHeader>
        <CardTitle>Resumo do Impacto</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div>
          <p className="text-sm text-muted-foreground">Impacto Total 12 meses</p>
          <p
            className={`text-2xl font-bold ${totalImpact >= 0 ? 'text-green-600' : 'text-red-600'}`}
          >
            {totalImpact >= 0 ? '+' : ''}
            {formatCurrency(totalImpact)}
          </p>
        </div>

        <div>
          <p className="text-sm text-muted-foreground">Mês de Equilíbrio</p>
          <p className="text-lg font-semibold">
            {formatBreakEven(comparison.break_even_month)}
          </p>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-sm text-muted-foreground">Saldo Final Base</p>
            <p className="text-lg font-semibold">{formatCurrency(baseFinal)}</p>
          </div>
          <div>
            <p className="text-sm text-muted-foreground">Saldo Final Simulado</p>
            <p
              className={`text-lg font-semibold ${simulatedFinal >= baseFinal ? 'text-green-600' : 'text-red-600'}`}
            >
              {formatCurrency(simulatedFinal)}
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
