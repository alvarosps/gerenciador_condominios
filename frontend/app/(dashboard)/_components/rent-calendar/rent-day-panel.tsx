'use client';

import { useMemo } from 'react';
import { CalendarClock, CheckCircle2, AlertTriangle, Ban } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { TooltipProvider } from '@/components/ui/tooltip';
import { formatCurrency } from '@/lib/utils/formatters';
import { cn } from '@/lib/utils';
import type { RentCalendarItem } from '@/lib/api/hooks/use-rent-calendar';
import { RentPaymentToggle } from './rent-payment-toggle';

const PAID_DAY_PASSED_REASON =
  'Pagamento confirmado — o dia já passou, não é possível desmarcar';
const MONTH_FINALIZED_REASON = 'Mês finalizado — não é possível alterar';

const NON_COLLECTIBLE_REASON_LABELS: Record<string, string> = {
  owner_repass: 'Repasse ao proprietário',
  salary_offset: 'Desconto salário',
};

function formatDayMonth(dateStr: string | null): string {
  if (!dateStr) return '';
  const [, month, day] = dateStr.split('-');
  return `${day ?? ''}/${month ?? ''}`;
}

function disabledReason(item: RentCalendarItem): string | undefined {
  if (item.can_toggle) return undefined;
  if (item.is_paid && item.day_passed) return PAID_DAY_PASSED_REASON;
  return MONTH_FINALIZED_REASON;
}

function StatusChip({ item }: { item: RentCalendarItem }) {
  if (item.is_paid) {
    return (
      <span className="inline-flex items-center gap-1 rounded-full border border-success/20 bg-card px-2 py-1 text-xs font-medium text-success">
        <CheckCircle2 className="h-3 w-3" />
        Pago
      </span>
    );
  }
  if (item.is_overdue) {
    return (
      <span className="inline-flex items-center gap-1 rounded-full border border-destructive/20 bg-card px-2 py-1 text-xs font-medium text-destructive">
        <AlertTriangle className="h-3 w-3" />
        Em atraso · {item.late_days} dias
      </span>
    );
  }
  return (
    <span className="rounded-full border border-amber-500/20 bg-amber-500/10 px-2 py-1 text-xs font-medium text-amber-600 dark:text-amber-400">
      A vencer
    </span>
  );
}

interface DayItemCardProps {
  item: RentCalendarItem;
  isPending: boolean;
  onToggle: (leaseId: number) => void;
}

function DayItemCard({ item, isPending, onToggle }: DayItemCardProps) {
  return (
    <div
      className={cn(
        'rounded-lg border bg-card p-3',
        item.is_paid && 'border-success/20 bg-success/10',
        !item.is_paid && item.is_overdue && 'border-destructive/20 bg-destructive/10',
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="truncate font-medium">{item.tenant_name}</div>
          <div className="text-xs text-muted-foreground">
            Apto {item.apartment_number} · Préd. {item.building_number}
          </div>
        </div>
        <StatusChip item={item} />
      </div>
      <div className="mt-3 flex items-center justify-between gap-2">
        <div>
          <span className="text-base font-semibold">{formatCurrency(item.rental_value)}</span>
          {item.is_paid && item.payment_date && (
            <div className="text-[11px] text-muted-foreground">
              Pago em {formatDayMonth(item.payment_date)}
            </div>
          )}
          {!item.is_paid && item.is_overdue && (
            <div className="text-[11px] font-medium text-destructive">
              + multa {formatCurrency(item.late_fee)}
            </div>
          )}
        </div>
        <RentPaymentToggle
          isPaid={item.is_paid}
          canToggle={item.can_toggle}
          isPending={isPending}
          onToggle={() => {
            onToggle(item.lease_id);
          }}
          disabledReason={disabledReason(item)}
        />
      </div>
    </div>
  );
}

function NonCollectibleItemCard({ item }: { item: RentCalendarItem }) {
  const label =
    item.non_collectible_reason !== null
      ? (NON_COLLECTIBLE_REASON_LABELS[item.non_collectible_reason] ?? item.non_collectible_reason)
      : '';

  return (
    <div className="rounded-lg border border-muted bg-muted/30 p-3">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="truncate font-medium text-muted-foreground">{item.tenant_name}</div>
          <div className="text-xs text-muted-foreground">
            Apto {item.apartment_number} · Préd. {item.building_number}
          </div>
        </div>
        <span className="inline-flex items-center gap-1 rounded-full border border-muted bg-muted px-2 py-1 text-xs font-medium text-muted-foreground">
          <Ban className="h-3 w-3" />
          {label}
        </span>
      </div>
      <div className="mt-3">
        <span className="text-base font-semibold text-muted-foreground">
          {formatCurrency(item.rental_value)}
        </span>
      </div>
    </div>
  );
}

interface RentDayPanelProps {
  items: RentCalendarItem[];
  dayLabel: string;
  nextDueDate: string | null;
  pendingLeaseId: number | null;
  onToggle: (leaseId: number) => void;
  onGoToday: () => void;
  onGoNextDue: () => void;
}

export function RentDayPanel({
  items,
  dayLabel,
  nextDueDate,
  pendingLeaseId,
  onToggle,
  onGoToday,
  onGoNextDue,
}: RentDayPanelProps) {
  const collectibleItems = useMemo(() => items.filter((i) => i.is_collectible), [items]);
  const nonCollectibleItems = useMemo(() => items.filter((i) => !i.is_collectible), [items]);

  return (
    <TooltipProvider>
      <div className="flex flex-col gap-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CalendarClock className="h-4 w-4 text-muted-foreground" />
            <span className="text-base font-semibold">{dayLabel}</span>
          </div>
          <div className="flex gap-1.5">
            <Button variant="outline" size="sm" onClick={onGoToday}>
              Hoje
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={onGoNextDue}
              disabled={nextDueDate === null}
            >
              Próx. vencimento
            </Button>
          </div>
        </div>

        {items.length === 0 ? (
          <p className="py-8 text-center text-sm text-muted-foreground">
            Nenhum vencimento neste dia
          </p>
        ) : (
          <div className="space-y-4">
            {collectibleItems.length > 0 && (
              <div className="space-y-3">
                {collectibleItems.map((item) => (
                  <DayItemCard
                    key={item.lease_id}
                    item={item}
                    isPending={pendingLeaseId === item.lease_id}
                    onToggle={onToggle}
                  />
                ))}
              </div>
            )}
            {nonCollectibleItems.length > 0 && (
              <div className="space-y-3">
                <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                  Não-cobrável
                </p>
                {nonCollectibleItems.map((item) => (
                  <NonCollectibleItemCard key={item.lease_id} item={item} />
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </TooltipProvider>
  );
}
