'use client';

import { Building2, ArrowRight } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import type { ApartmentInfo, DashboardSummary } from '@/lib/api/hooks/use-financial-dashboard';
import { formatCurrency } from '@/lib/utils/formatters';

const OWNER_COLORS = ['#f59e0b', '#a855f7', '#06b6d4', '#ec4899', '#14b8a6'];
const CONDOMINIUM_COLOR = '#3b82f6';
const VACANT_COLOR = '#f59e0b';

function getOwnerColor(index: number): string {
  const color = OWNER_COLORS[index % OWNER_COLORS.length];
  return color ?? '#f59e0b';
}

function computeVacantByOwner(vacantKitnets: ApartmentInfo[]) {
  const byOwner: Record<string, { count: number; lostRent: number }> = {};
  let condoCount = 0;
  let condoLostRent = 0;

  for (const apt of vacantKitnets) {
    const ownerName = apt.owner_name;
    const rent = apt.rental_value ?? 0;
    if (ownerName) {
      const entry = byOwner[ownerName] ?? { count: 0, lostRent: 0 };
      entry.count += 1;
      entry.lostRent += rent;
      byOwner[ownerName] = entry;
    } else {
      condoCount += 1;
      condoLostRent += rent;
    }
  }

  return { byOwner, condoVacant: { count: condoCount, lostRent: condoLostRent } };
}

export function IncomeSummaryCard({ data, monthLabel }: { data: DashboardSummary; monthLabel: string }) {
  const { income_summary } = data;
  const totalIncome = income_summary.total_monthly_income;
  const hasVacant = income_summary.vacant_count > 0;
  const potentialTotal = totalIncome + income_summary.vacant_lost_rent;
  const rentedPercent = potentialTotal > 0 ? (totalIncome / potentialTotal) * 100 : 100;

  const { byOwner, condoVacant } = computeVacantByOwner(income_summary.vacant_kitnets);

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base font-semibold flex items-center gap-2">
          <Building2 className="h-5 w-5 text-info" />
          Resumo de Entradas Condomínio — {monthLabel}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Total block with potential bar */}
        <div className="rounded-lg border bg-muted/30 p-4 space-y-3">
          <div className="text-center">
            <p className="text-xs text-muted-foreground">Total Entradas Mensal</p>
            <p className="text-3xl font-bold text-success">{formatCurrency(totalIncome)}</p>
            <p className="text-xs text-muted-foreground">
              {income_summary.all_apartments.length} kitnets alugados
            </p>
          </div>

          {hasVacant && (
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <p className="text-xs" style={{ color: VACANT_COLOR }}>
                  {income_summary.vacant_count} kitnets não alugados
                </p>
                <p className="text-sm font-semibold" style={{ color: VACANT_COLOR }}>
                  + {formatCurrency(income_summary.vacant_lost_rent)}
                </p>
              </div>
              <div className="flex h-2.5 w-full overflow-hidden rounded">
                <div
                  className="rounded-l"
                  style={{
                    width: `${rentedPercent}%`,
                    background: `linear-gradient(90deg, ${CONDOMINIUM_COLOR}, ${getOwnerColor(1)})`,
                    opacity: 0.6,
                  }}
                />
                <div
                  className="rounded-r border border-dashed"
                  style={{
                    width: `${100 - rentedPercent}%`,
                    borderColor: `${VACANT_COLOR}44`,
                    background: `repeating-linear-gradient(45deg, transparent, transparent 4px, ${VACANT_COLOR}33 4px, ${VACANT_COLOR}33 8px)`,
                  }}
                />
              </div>
              <div className="flex justify-between text-[10px] text-muted-foreground">
                <span>Alugados: {formatCurrency(totalIncome)}</span>
                <span>Potencial total: {formatCurrency(potentialTotal)}</span>
              </div>
            </div>
          )}
        </div>

        {/* Arrow */}
        <p className="text-center text-sm text-muted-foreground">&#x25BC; distribui-se em</p>

        {/* Distribution cards */}
        <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
          {/* Condomínio card */}
          <DistributionCard
            label="Condomínio"
            value={income_summary.condominium_income}
            subtitle={`${income_summary.condominium_kitnet_count} kitnets`}
            footnote="vai pro caixa"
            color={CONDOMINIUM_COLOR}
            percentage={totalIncome > 0
              ? Math.round((income_summary.condominium_income / totalIncome) * 100)
              : 0}
            vacantCount={condoVacant.count}
            vacantLostRent={condoVacant.lostRent}
          />

          {/* Owner cards */}
          {income_summary.owner_incomes.map((owner, index) => {
            const ownerVacant = byOwner[owner.person_name];
            return (
              <DistributionCard
                key={owner.person_name}
                label={owner.person_name}
                value={owner.total}
                subtitle={`Aptos ${owner.apartments.join(', ')}`}
                footnote="repasse direto"
                color={getOwnerColor(index)}
                percentage={totalIncome > 0
                  ? Math.round((owner.total / totalIncome) * 100)
                  : 0}
                vacantCount={ownerVacant?.count ?? 0}
                vacantLostRent={ownerVacant?.lostRent ?? 0}
              />
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}

function DistributionCard({
  label,
  value,
  subtitle,
  footnote,
  color,
  percentage,
  vacantCount,
  vacantLostRent,
}: {
  label: string;
  value: number;
  subtitle: string;
  footnote: string;
  color: string;
  percentage: number;
  vacantCount: number;
  vacantLostRent: number;
}) {
  const potential = value + vacantLostRent;
  const filledPercent = potential > 0 ? (value / potential) * 100 : 100;

  return (
    <div
      className="relative rounded-lg border bg-muted/20 p-3 space-y-2"
      style={{ borderLeftWidth: 3, borderLeftColor: color }}
    >
      <Badge
        variant="outline"
        className="absolute top-2 right-2 text-[10px] font-semibold px-1.5 py-0"
        style={{ color, borderColor: `${color}33`, backgroundColor: `${color}20` }}
      >
        {percentage}%
      </Badge>
      <div>
        <p className="text-xs text-muted-foreground">{label}</p>
        <p className="text-xl font-bold" style={{ color }}>{formatCurrency(value)}</p>
        <p className="text-xs text-muted-foreground">{subtitle}</p>
        <p className="text-[10px] text-muted-foreground mt-1 flex items-center gap-1">
          <ArrowRight className="h-2.5 w-2.5" />
          {footnote}
        </p>
      </div>

      <div className="space-y-1 border-t border-dashed pt-2">
        {vacantCount > 0 ? (
          <div className="flex items-center justify-between">
            <p className="text-[10px]" style={{ color: VACANT_COLOR }}>
              {vacantCount} não alugado{vacantCount > 1 ? 's' : ''}
            </p>
            <p className="text-xs font-semibold" style={{ color: VACANT_COLOR }}>
              + {formatCurrency(vacantLostRent)}
            </p>
          </div>
        ) : (
          <p className="text-[10px] text-success">Todos alugados</p>
        )}
        <div className="flex h-2 w-full overflow-hidden rounded">
          <div
            className="rounded-l"
            style={{ width: `${filledPercent}%`, backgroundColor: color, opacity: 0.6 }}
          />
          {vacantCount > 0 && (
            <div
              className="rounded-r border border-dashed"
              style={{
                width: `${100 - filledPercent}%`,
                borderColor: `${VACANT_COLOR}44`,
                background: `repeating-linear-gradient(45deg, transparent, transparent 3px, ${VACANT_COLOR}33 3px, ${VACANT_COLOR}33 6px)`,
              }}
            />
          )}
        </div>
      </div>
    </div>
  );
}
