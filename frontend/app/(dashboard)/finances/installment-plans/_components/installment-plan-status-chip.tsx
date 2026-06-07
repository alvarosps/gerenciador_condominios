'use client';

import { Ban, CalendarClock, CheckCircle2, Clock } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { InstallmentPlanState } from '@/lib/schemas/finances/installment-plan.schema';

/**
 * Maps an installment plan's lifecycle_state to a label + icon (never color alone).
 * Single source of truth, reused by the columns and the page.
 */
interface ChipVisual {
  label: string;
  Icon: LucideIcon;
  className: string;
}

const PLAN_STATE_CHIPS: Record<InstallmentPlanState, ChipVisual> = {
  active: { label: 'Ativo', Icon: Clock, className: 'text-amber-600 dark:text-amber-400' },
  paid: { label: 'Quitado', Icon: CheckCircle2, className: 'text-success' },
  deferred: { label: 'Adiado', Icon: CalendarClock, className: 'text-muted-foreground' },
  canceled: { label: 'Cancelado', Icon: Ban, className: 'text-muted-foreground' },
};

interface InstallmentPlanStatusChipProps {
  state: InstallmentPlanState;
  className?: string;
}

export function InstallmentPlanStatusChip({ state, className }: InstallmentPlanStatusChipProps) {
  const { label, Icon, className: visualClass } = PLAN_STATE_CHIPS[state];
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
