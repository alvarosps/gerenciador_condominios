'use client';

import { CreditCard, Droplets, Landmark, ShoppingBag, Repeat } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { formatCurrency } from '@/lib/utils/formatters';
import type { MonthlyPurchasesResponse } from '@/lib/api/hooks/use-monthly-purchases';

interface PurchaseSummaryCardsProps {
  data: MonthlyPurchasesResponse['by_type'] | undefined;
  isLoading: boolean;
}

const TYPE_CONFIG = [
  {
    key: 'card_purchases' as const,
    label: 'Compras no Cartão',
    icon: CreditCard,
    colorClass: 'text-blue-500',
  },
  {
    key: 'utility_bills' as const,
    label: 'Contas de Consumo',
    icon: Droplets,
    colorClass: 'text-cyan-500',
  },
  {
    key: 'loans' as const,
    label: 'Empréstimos',
    icon: Landmark,
    colorClass: 'text-orange-500',
  },
  {
    key: 'one_time_expenses' as const,
    label: 'Gastos Únicos',
    icon: ShoppingBag,
    colorClass: 'text-purple-500',
  },
  {
    key: 'fixed_expenses' as const,
    label: 'Gastos Fixos',
    icon: Repeat,
    colorClass: 'text-green-500',
  },
] as const;

export function PurchaseSummaryCards({ data, isLoading }: PurchaseSummaryCardsProps) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
        {TYPE_CONFIG.map((config) => (
          <Card key={config.key}>
            <CardHeader className="pb-2">
              <Skeleton className="h-4 w-24" />
            </CardHeader>
            <CardContent>
              <Skeleton className="h-6 w-20 mb-1" />
              <Skeleton className="h-3 w-12" />
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
      {TYPE_CONFIG.map((config) => {
        const group = data?.[config.key];
        const Icon = config.icon;
        return (
          <Card key={config.key} className="hover:shadow-md transition-shadow">
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
                <Icon className={`h-4 w-4 ${config.colorClass}`} />
                {config.label}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-xl font-bold">{formatCurrency(group?.total ?? 0)}</p>
              <p className="text-xs text-muted-foreground mt-1">
                {group?.count ?? 0} {(group?.count ?? 0) === 1 ? 'item' : 'itens'}
              </p>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
