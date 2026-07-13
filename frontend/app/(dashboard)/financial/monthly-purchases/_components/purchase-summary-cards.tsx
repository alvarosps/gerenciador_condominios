'use client';

import { CreditCard, Droplets, Landmark, ShoppingBag, Repeat } from 'lucide-react';
import { StatCard } from '@/components/ui/stat-card';
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
          <StatCard key={config.key} label="" value="" subLabel="" loading />
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
          <StatCard
            key={config.key}
            label={config.label}
            value={formatCurrency(group?.total ?? 0)}
            icon={<Icon className={`h-4 w-4 ${config.colorClass}`} />}
            subLabel={`${group?.count ?? 0} ${(group?.count ?? 0) === 1 ? 'item' : 'itens'}`}
          />
        );
      })}
    </div>
  );
}
