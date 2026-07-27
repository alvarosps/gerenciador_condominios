'use client';

import {
  AlertTriangle,
  CheckCircle2,
  CircleDashed,
  Clock,
  PiggyBank,
  PieChart,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { cn } from '@/lib/utils';
import {
  THIRD_PARTY_MONTH_STATUS_LABELS,
  type ThirdPartyMonthStatus,
} from '@/lib/schemas/finances/third-party.schema';

/**
 * Maps a statement month's status to a label + icon (never color alone) — mirrors
 * `installment-plan-status-chip.tsx`.
 *
 * SIX statuses, not five. `empty` is a gap month the window materializes so the extrato has no
 * holes; it MUST read as "nothing happened", never as success. Painting it like `paid` was a real
 * backend bug (fixed in S79) whose whole point was that "Quitado" between two overdue months lies
 * to the reader — so `empty` gets the muted tone and a dashed circle, and never the success token.
 */
interface ChipVisual {
  Icon: LucideIcon;
  className: string;
}

const STATUS_CHIPS: Record<ThirdPartyMonthStatus, ChipVisual> = {
  paid: { Icon: CheckCircle2, className: 'text-success' },
  overdue: { Icon: AlertTriangle, className: 'text-destructive' },
  partially_paid: { Icon: PieChart, className: 'text-amber-600 dark:text-amber-400' },
  open: { Icon: Clock, className: 'text-amber-600 dark:text-amber-400' },
  credit: { Icon: PiggyBank, className: 'text-info' },
  empty: { Icon: CircleDashed, className: 'text-muted-foreground' },
};

interface ThirdPartyStatusChipProps {
  status: ThirdPartyMonthStatus;
  className?: string;
}

export function ThirdPartyStatusChip({ status, className }: ThirdPartyStatusChipProps) {
  const { Icon, className: visualClass } = STATUS_CHIPS[status];
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-full border border-border bg-card px-2 py-1 text-xs font-medium',
        visualClass,
        className
      )}
    >
      <Icon className="h-3 w-3" />
      {THIRD_PARTY_MONTH_STATUS_LABELS[status]}
    </span>
  );
}
