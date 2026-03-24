'use client';

import { Building2, Home, PlusCircle, Users } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import type { DashboardSummary } from '@/lib/api/hooks/use-financial-dashboard';
import { formatCurrency } from '@/lib/utils/formatters';

export function IncomeSummaryCard({ data, monthLabel }: { data: DashboardSummary; monthLabel: string }) {
  const { income_summary } = data;

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base font-semibold flex items-center gap-2">
          <Building2 className="h-5 w-5 text-blue-500" />
          Resumo de Entradas — {monthLabel}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
          {/* Total entradas mensal */}
          <div className="space-y-1">
            <p className="text-xs text-muted-foreground font-medium">Total Entradas Mensal</p>
            <p className="text-xl font-bold text-blue-600">
              {formatCurrency(income_summary.total_monthly_income)}
            </p>
            <p className="text-xs text-muted-foreground">
              {income_summary.all_apartments.length} kitnets alugados
            </p>
          </div>

          {/* Owner incomes */}
          {income_summary.owner_incomes.map((owner) => (
            <div key={owner.person_name} className="space-y-1">
              <p className="text-xs text-muted-foreground font-medium flex items-center gap-1">
                <Users className="h-3 w-3" />
                Entradas {owner.person_name}
              </p>
              <p className="text-xl font-bold text-purple-600">
                {formatCurrency(owner.total)}
              </p>
              <p className="text-xs text-muted-foreground">
                Aptos {owner.apartments.join(', ')}
              </p>
            </div>
          ))}

          {/* Kitnets não alugados */}
          <div className="space-y-1">
            <p className="text-xs text-muted-foreground font-medium flex items-center gap-1">
              <Home className="h-3 w-3" />
              Kitnets Não Alugados
            </p>
            <p className="text-xl font-bold text-amber-500">
              {formatCurrency(income_summary.vacant_lost_rent)}
            </p>
            <p className="text-xs text-muted-foreground">
              Não alugados: {income_summary.vacant_count}
            </p>
            {income_summary.vacant_by_building.map((b) => (
              <p key={b.building_name} className="text-xs text-muted-foreground">
                Prédio {b.building_name}: {b.apartments.join(', ')}
              </p>
            ))}
          </div>

          {/* Entradas condomínio */}
          <div className="space-y-1">
            <p className="text-xs text-muted-foreground font-medium">Entradas Condomínio</p>
            <p className="text-xl font-bold text-green-600">
              {formatCurrency(income_summary.condominium_income)}
            </p>
            <p className="text-xs text-muted-foreground">
              {income_summary.condominium_kitnet_count} kitnets
            </p>
          </div>

          {/* Outras entradas */}
          {income_summary.extra_incomes.length > 0 && (
            <div className="space-y-1">
              <p className="text-xs text-muted-foreground font-medium flex items-center gap-1">
                <PlusCircle className="h-3 w-3" />
                Outras Entradas
              </p>
              <p className="text-xl font-bold text-teal-600">
                {formatCurrency(income_summary.extra_income_total)}
              </p>
              {income_summary.extra_incomes.map((inc) => (
                <p key={inc.description} className="text-xs text-muted-foreground">
                  {inc.description}: {formatCurrency(inc.amount)}
                  {inc.is_recurring ? ' (mensal)' : ''}
                </p>
              ))}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
