'use client';

import { AlertTriangle, Landmark, User } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import type { OverdueItem } from '@/lib/api/hooks/use-financial-dashboard';
import { formatCurrency, formatMonthYear } from '@/lib/utils/formatters';
import { cn } from '@/lib/utils';

interface GroupedOverdue {
  label: string;
  items: OverdueItem[];
  total: number;
}

function groupOverdueByMonth(items: OverdueItem[]): GroupedOverdue[] {
  const map = new Map<string, GroupedOverdue>();

  for (const item of items) {
    const key = `${item.reference_year}-${item.reference_month}`;
    const label = formatMonthYear(item.reference_year, item.reference_month);

    if (!map.has(key)) {
      map.set(key, { label, items: [], total: 0 });
    }
    const group = map.get(key);
    if (group) {
      group.items.push(item);
      group.total += item.amount;
    }
  }

  // Sort by date descending (most recent first)
  return [...map.values()].sort((a, b) => {
    const aItem = a.items[0];
    const bItem = b.items[0];
    if (!aItem || !bItem) return 0;
    const aKey = aItem.reference_year * 100 + aItem.reference_month;
    const bKey = bItem.reference_year * 100 + bItem.reference_month;
    return bKey - aKey;
  });
}

function OverdueCard({ group }: { group: GroupedOverdue }) {
  const personItems = group.items.filter((i) => i.type === 'person');
  const iptuItems = group.items.filter((i) => i.type === 'iptu');

  return (
    <Card className="border-warning/20 bg-warning/5">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-semibold text-warning">
            {group.label}
          </CardTitle>
          <span className="text-sm font-bold text-destructive">
            {formatCurrency(group.total)}
          </span>
        </div>
      </CardHeader>
      <CardContent className="space-y-2">
        {personItems.map((item) => (
          <div
            key={`person-${item.person_id}-${item.reference_month}`}
            className="flex items-center justify-between text-sm"
          >
            <span className="flex items-center gap-1.5 text-muted-foreground">
              <User className="h-3.5 w-3.5" />
              {item.person_name}
              {item.total_paid !== null && item.total_paid !== undefined && item.total_paid > 0 && (
                <span className="text-xs text-success">
                  (pago {formatCurrency(item.total_paid)})
                </span>
              )}
            </span>
            <span className={cn(
              'font-medium',
              (item.net_amount ?? 0) > 0 ? 'text-info' : 'text-destructive',
            )}>
              {formatCurrency(item.amount)}
            </span>
          </div>
        ))}

        {iptuItems.length > 0 && (
          <div className="space-y-1">
            {iptuItems.map((item, i) => (
              <div
                key={`iptu-${i}`}
                className="flex items-center justify-between text-sm"
              >
                <span className="flex items-center gap-1.5 text-muted-foreground truncate">
                  <Landmark className="h-3.5 w-3.5 shrink-0" />
                  <span className="truncate">
                    IPTU {item.building_name}
                    {item.installment ? ` (${item.installment})` : ''}
                  </span>
                </span>
                <span className="font-medium text-destructive whitespace-nowrap shrink-0 ml-2">
                  {formatCurrency(item.amount)}
                </span>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export function OverdueSection({ items }: { items: OverdueItem[] }) {
  if (items.length === 0) return null;

  const groups = groupOverdueByMonth(items);
  const totalOverdue = items.reduce((sum, item) => sum + item.amount, 0);

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="text-base font-semibold flex items-center gap-2">
          <AlertTriangle className="h-5 w-5 text-warning" />
          Valores em Atraso
        </h2>
        <span className="text-sm font-bold text-destructive">
          Total: {formatCurrency(totalOverdue)}
        </span>
      </div>
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {groups.map((group) => (
          <OverdueCard key={group.label} group={group} />
        ))}
      </div>
    </div>
  );
}
