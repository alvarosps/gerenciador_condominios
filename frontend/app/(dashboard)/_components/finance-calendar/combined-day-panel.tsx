'use client';

import { ArrowDownCircle, ArrowUpCircle, CalendarClock } from 'lucide-react';
import { TooltipProvider } from '@/components/ui/tooltip';
import { formatCurrency } from '@/lib/utils/formatters';
import { cn } from '@/lib/utils';
import type { RentCalendarItem } from '@/lib/api/hooks/use-rent-calendar';
import type { CombinedCalendarBillExit } from '@/lib/api/hooks/use-combined-calendar';
import { BillPaymentToggle } from './bill-payment-toggle';
import { BillStatusChip } from './bill-status-chip';

const SUSPENDED_REASON = 'Conta suspensa — reative para pagar';
const DEFERRED_REASON = 'Conta adiada — reative para pagar';
const CANCELED_REASON = 'Conta cancelada — reative para pagar';
const PAID_REASON = 'Conta já paga';

function rentStatusLabel(item: RentCalendarItem): string {
  if (!item.is_collectible) return 'Não-cobrável';
  if (item.is_paid) return 'Pago';
  if (item.is_overdue) return 'Em atraso';
  return 'A vencer';
}

function RentRow({ item }: { item: RentCalendarItem }) {
  return (
    <div className="rounded-lg border bg-card p-3">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="truncate font-medium">{item.tenant_name}</div>
          <div className="text-xs text-muted-foreground">
            Apto {item.apartment_number} · Préd. {item.building_number}
          </div>
        </div>
        <span className="text-xs font-medium text-muted-foreground">{rentStatusLabel(item)}</span>
      </div>
      <div className="mt-2 text-base font-semibold text-success">
        + {formatCurrency(item.rental_value)}
      </div>
    </div>
  );
}

function payDisabledReason(exit: CombinedCalendarBillExit): string | undefined {
  if (exit.payment_status === 'paid') return PAID_REASON;
  switch (exit.lifecycle_state) {
    case 'suspended':
      return SUSPENDED_REASON;
    case 'deferred':
      return DEFERRED_REASON;
    case 'canceled':
      return CANCELED_REASON;
    default:
      return undefined;
  }
}

interface BillRowProps {
  exit: CombinedCalendarBillExit;
  isAdmin: boolean;
  isPending: boolean;
  onPayBill: (billId: number) => void;
}

function BillRow({ exit, isAdmin, isPending, onPayBill }: BillRowProps) {
  const canPay = exit.lifecycle_state === 'active' && exit.payment_status !== 'paid';
  const buildingLabel = exit.building_number === null ? 'Condomínio' : `Préd. ${exit.building_number}`;

  return (
    <div
      className={cn(
        'rounded-lg border bg-card p-3',
        exit.payment_status === 'paid' && 'border-success/20 bg-success/10',
        exit.payment_status !== 'paid' && exit.is_overdue && 'border-destructive/20 bg-destructive/10',
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="truncate font-medium">{exit.description}</div>
          <div className="text-xs text-muted-foreground">
            {buildingLabel}
            {exit.category ? ` · ${exit.category}` : ''}
          </div>
        </div>
        {isAdmin ? (
          <BillPaymentToggle
            paymentStatus={exit.payment_status}
            isOverdue={exit.is_overdue}
            lifecycleState={exit.lifecycle_state}
            canPay={canPay}
            isPending={isPending}
            onPay={() => {
              onPayBill(exit.bill_id);
            }}
            disabledReason={payDisabledReason(exit)}
          />
        ) : (
          <BillStatusChip
            paymentStatus={exit.payment_status}
            isOverdue={exit.is_overdue}
            lifecycleState={exit.lifecycle_state}
          />
        )}
      </div>
      <div className="mt-2 text-base font-semibold text-destructive">
        − {formatCurrency(exit.amount_remaining)}
      </div>
    </div>
  );
}

interface CombinedDayPanelProps {
  dayLabel: string;
  rentItems: RentCalendarItem[];
  billItems: CombinedCalendarBillExit[];
  isAdmin: boolean;
  pendingBillId: number | null;
  onPayBill: (billId: number) => void;
}

export function CombinedDayPanel({
  dayLabel,
  rentItems,
  billItems,
  isAdmin,
  pendingBillId,
  onPayBill,
}: CombinedDayPanelProps) {
  return (
    <TooltipProvider>
      <div className="flex flex-col gap-4">
        <div className="flex items-center gap-2">
          <CalendarClock className="h-4 w-4 text-muted-foreground" />
          <span className="text-base font-semibold">{dayLabel}</span>
        </div>

        <section className="space-y-2">
          <div className="flex items-center gap-1.5 text-xs font-medium uppercase tracking-wide text-success">
            <ArrowUpCircle className="h-3.5 w-3.5" />
            Aluguéis (entradas)
          </div>
          {rentItems.length === 0 ? (
            <p className="py-2 text-sm text-muted-foreground">Nenhum aluguel neste dia</p>
          ) : (
            <div className="space-y-2">
              {rentItems.map((item) => (
                <RentRow key={item.lease_id} item={item} />
              ))}
            </div>
          )}
        </section>

        <section className="space-y-2">
          <div className="flex items-center gap-1.5 text-xs font-medium uppercase tracking-wide text-destructive">
            <ArrowDownCircle className="h-3.5 w-3.5" />
            Contas a pagar (saídas)
          </div>
          {billItems.length === 0 ? (
            <p className="py-2 text-sm text-muted-foreground">Nenhuma conta a pagar neste dia</p>
          ) : (
            <div className="space-y-2">
              {billItems.map((exit) => (
                <BillRow
                  key={exit.bill_id}
                  exit={exit}
                  isAdmin={isAdmin}
                  isPending={pendingBillId === exit.bill_id}
                  onPayBill={onPayBill}
                />
              ))}
            </div>
          )}
        </section>
      </div>
    </TooltipProvider>
  );
}
