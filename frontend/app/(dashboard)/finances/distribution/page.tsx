'use client';

import { useState } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Loading } from '@/components/shared/loading';
import { formatMonthYear } from '@/lib/utils/formatters';
import { useOwnerDistribution } from '@/lib/api/hooks/use-owner-distribution';
import { HouseholdDistribution } from './_components/household-distribution';
import { ExternalOwnersSection } from './_components/external-owners-section';

interface YearMonth {
  year: number;
  month: number;
}

function currentYearMonth(): YearMonth {
  const now = new Date();
  return { year: now.getFullYear(), month: now.getMonth() + 1 };
}

export default function DistributionPage() {
  const [{ year, month }, setYearMonth] = useState<YearMonth>(currentYearMonth);
  const { data, isLoading, isError } = useOwnerDistribution(year, month);

  function shiftMonth(delta: number) {
    const base = new Date(year, month - 1 + delta, 1);
    setYearMonth({ year: base.getFullYear(), month: base.getMonth() + 1 });
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-3xl font-bold">Distribuição por proprietário</h1>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="icon" onClick={() => shiftMonth(-1)} aria-label="Mês anterior">
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <span className="min-w-[10rem] text-center text-sm font-medium">
            {formatMonthYear(year, month)}
          </span>
          <Button variant="outline" size="icon" onClick={() => shiftMonth(1)} aria-label="Próximo mês">
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {isLoading && <Loading />}
      {isError && (
        <p className="py-8 text-center text-muted-foreground">
          Erro ao carregar a distribuição. Verifique se há dados financeiros cadastrados.
        </p>
      )}
      {data && (
        <>
          <HouseholdDistribution household={data.household} year={data.year} month={data.month} />
          <ExternalOwnersSection
            externalOwners={data.external_owners}
            externalTotal={data.external_total}
          />
        </>
      )}
    </div>
  );
}
