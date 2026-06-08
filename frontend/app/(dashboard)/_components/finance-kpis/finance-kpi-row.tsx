'use client';

import { DollarSign, PiggyBank, TrendingUp, AlertTriangle, Scale } from 'lucide-react';
import { Skeleton } from '@/components/ui/skeleton';
import { Card, CardContent } from '@/components/ui/card';
import { StatCard } from '@/components/ui/stat-card';
import { AmountDisplay } from '@/components/ui/amount-display';
import { useFinanceOverview } from '@/lib/api/hooks/use-finance-balance';
import { formatCurrency, formatMonthYear } from '@/lib/utils/formatters';

function KpiSkeleton() {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
      {Array.from({ length: 5 }).map((_, i) => (
        <div key={i} className="rounded-xl border bg-card shadow p-6 space-y-2">
          <Skeleton className="h-3 w-20" />
          <Skeleton className="h-8 w-32" />
        </div>
      ))}
    </div>
  );
}

function KpiError() {
  return (
    <Card>
      <CardContent className="py-6">
        <p className="text-sm text-destructive">Erro ao carregar os indicadores financeiros.</p>
      </CardContent>
    </Card>
  );
}

interface Props {
  year: number;
  month: number;
  buildingId?: number;
}

export function FinanceKpiRow({ year, month, buildingId }: Props) {
  const { data, isLoading, isError } = useFinanceOverview(year, month, buildingId);
  const monthLabel = formatMonthYear(year, month);

  if (isLoading) return <KpiSkeleton />;
  if (isError) return <KpiError />;
  if (!data) return null;

  const overdueBillsNum = parseFloat(data.overdue_bills_total);
  const rentOverdueNum = parseFloat(data.rent_overdue.total_fee);
  // Caixa can be negative (design §4.3) — show it destructive when below zero, neutral otherwise.
  const cashTone = parseFloat(data.cash_balance) < 0 ? 'destructive' : 'foreground';
  // Atrasados shows BOTH figures (design §4.4 — bills and rent are separate, non-additive).
  const overdueBillsLabel =
    data.overdue_bills_count > 0
      ? `${data.overdue_bills_count} conta${data.overdue_bills_count > 1 ? 's' : ''} em atraso`
      : 'Sem contas atrasadas';
  const overdueSubLabel =
    rentOverdueNum > 0
      ? `${overdueBillsLabel} · Aluguel: ${formatCurrency(rentOverdueNum)}`
      : overdueBillsLabel;

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
      <StatCard
        label="Caixa"
        value={<AmountDisplay amount={data.cash_balance} tone={cashTone} />}
        icon={<DollarSign className="h-4 w-4" />}
        tone={cashTone}
        subLabel={monthLabel}
      />
      <StatCard
        label="Reserva"
        value={<AmountDisplay amount={data.reserve_balance} tone="info" />}
        icon={<PiggyBank className="h-4 w-4" />}
        tone="info"
      />
      <StatCard
        label="Resultado do Mês"
        value={<AmountDisplay amount={data.result_of_month} autoTone />}
        icon={<TrendingUp className="h-4 w-4" />}
        tone={parseFloat(data.result_of_month) >= 0 ? 'success' : 'destructive'}
        subLabel={monthLabel}
      />
      <StatCard
        label="Atrasados"
        value={<AmountDisplay amount={data.overdue_bills_total} tone={overdueBillsNum > 0 ? 'destructive' : 'muted'} />}
        icon={<AlertTriangle className="h-4 w-4" />}
        tone={overdueBillsNum > 0 ? 'destructive' : 'muted'}
        subLabel={overdueSubLabel}
      />
      <StatCard
        label="Saldo Total"
        value={<AmountDisplay amount={data.total_balance} autoTone />}
        icon={<Scale className="h-4 w-4" />}
        tone={parseFloat(data.total_balance) >= 0 ? 'success' : 'destructive'}
        subLabel="Caixa + Reserva"
      />
    </div>
  );
}
