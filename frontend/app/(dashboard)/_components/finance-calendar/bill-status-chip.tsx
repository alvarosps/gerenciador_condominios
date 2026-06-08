'use client';

import { AlertTriangle, Ban, CalendarClock, CheckCircle2, Clock, PauseCircle } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { PaymentStatus } from '@/lib/schemas/finances/category.schema';

/**
 * Single source of truth for mapping a bill's status to label/icon/color.
 *
 * Status is ALWAYS conveyed by label + icon (never color alone) for accessibility.
 * Lifecycle states (suspended/deferred/canceled) take precedence and are excluded
 * from the "overdue" computation (design §4.4): a deferred/suspended bill shows its
 * lifecycle chip, never "Em atraso".
 *
 * Reused by the combined calendar (bill exits) and the bills table — entries (rent)
 * use the rent-calendar's own chip; this one is for bill exits only.
 */

export interface BillStatusChipProps {
  paymentStatus: PaymentStatus;
  isOverdue: boolean;
  lifecycleState: string;
  className?: string;
}

interface ChipVisual {
  label: string;
  Icon: LucideIcon;
  className: string;
}

// Keyed by string so a raw lifecycle_state (string) looks up without a cast; only the
// non-active states carry a chip (active falls through to the payment-status mapping).
const LIFECYCLE_CHIPS: Record<string, ChipVisual> = {
  suspended: { label: 'Suspensa', Icon: PauseCircle, className: 'text-muted-foreground' },
  deferred: { label: 'Adiada', Icon: CalendarClock, className: 'text-muted-foreground' },
  canceled: { label: 'Cancelada', Icon: Ban, className: 'text-muted-foreground' },
};

export function resolveBillStatusChip(
  paymentStatus: PaymentStatus,
  isOverdue: boolean,
  lifecycleState: string,
): ChipVisual {
  const lifecycleChip = LIFECYCLE_CHIPS[lifecycleState];
  if (lifecycleChip) return lifecycleChip;

  if (paymentStatus === 'paid') {
    return { label: 'Pago', Icon: CheckCircle2, className: 'text-success' };
  }
  if (isOverdue) {
    return { label: 'Em atraso', Icon: AlertTriangle, className: 'text-destructive' };
  }
  if (paymentStatus === 'partial') {
    return { label: 'Parcial', Icon: Clock, className: 'text-amber-600 dark:text-amber-400' };
  }
  return { label: 'Em aberto', Icon: Clock, className: 'text-amber-600 dark:text-amber-400' };
}

export function BillStatusChip({
  paymentStatus,
  isOverdue,
  lifecycleState,
  className,
}: BillStatusChipProps) {
  const { label, Icon, className: visualClass } = resolveBillStatusChip(
    paymentStatus,
    isOverdue,
    lifecycleState,
  );

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-full border border-border bg-card px-2 py-1 text-xs font-medium',
        visualClass,
        className,
      )}
    >
      <Icon className="h-3 w-3" />
      {label}
    </span>
  );
}
