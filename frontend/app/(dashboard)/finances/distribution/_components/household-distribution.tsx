'use client';

import { StatCard, type StatTone } from '@/components/ui/stat-card';
import { formatCurrency, formatMonthYear } from '@/lib/utils/formatters';
import type { OwnerHousehold } from '@/lib/api/hooks/use-owner-distribution';

// The fold (available/carried_out) is computed by the backend (§4.7) — these cards only DISPLAY the
// strings; the front never re-applies max/min/sum.
function toNumber(value: string): number {
  return parseFloat(value);
}

function signTone(value: string): StatTone {
  return toNumber(value) < 0 ? 'destructive' : 'success';
}

interface HouseholdDistributionProps {
  household: OwnerHousehold;
  year: number;
  month: number;
}

export function HouseholdDistribution({ household, year, month }: HouseholdDistributionProps) {
  return (
    <section className="space-y-3">
      <h2 className="text-lg font-semibold">{household.name} — resultado do condomínio</h2>
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label={`Resultado do mês — ${formatMonthYear(year, month)}`}
          value={formatCurrency(household.result_of_month)}
          tone={signTone(household.result_of_month)}
        />
        <StatCard
          label="Carregado do mês anterior"
          value={formatCurrency(household.carried_in)}
          tone={toNumber(household.carried_in) < 0 ? 'destructive' : 'foreground'}
        />
        <StatCard
          label="Disponível para distribuição"
          value={formatCurrency(household.available)}
          tone="success"
        />
        <StatCard
          label="A carregar para o próximo mês"
          value={formatCurrency(household.carried_out)}
          tone={toNumber(household.carried_out) < 0 ? 'warning' : 'foreground'}
        />
      </div>
    </section>
  );
}
