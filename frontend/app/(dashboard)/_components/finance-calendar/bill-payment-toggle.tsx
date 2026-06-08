'use client';

import { Switch } from '@/components/ui/switch';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { BillStatusChip } from './bill-status-chip';
import type { PaymentStatus } from '@/lib/schemas/finances/category.schema';

interface BillPaymentToggleProps {
  paymentStatus: PaymentStatus;
  isOverdue: boolean;
  lifecycleState: string;
  /** false when the bill is not 'active' (lifecycle) or already paid — the front only knows lifecycle. */
  canPay: boolean;
  isPending: boolean;
  /** Opens the payment dialog (partial/funded_from need input) rather than paying the total directly. */
  onPay: () => void;
  disabledReason?: string;
}

export function BillPaymentToggle({
  paymentStatus,
  isOverdue,
  lifecycleState,
  canPay,
  isPending,
  onPay,
  disabledReason,
}: BillPaymentToggleProps) {
  const isPaid = paymentStatus === 'paid';
  const disabled = !canPay || isPending || isPaid;
  const ariaLabel = disabled && disabledReason ? disabledReason : 'Pagar conta';

  // KISS: the toggle OPENS the payment dialog (total/partial + funded_from) instead of
  // paying the full amount directly — partial payments and reserve funding need input.
  const toggle = (
    <Switch
      checked={isPaid}
      disabled={disabled}
      onCheckedChange={() => {
        onPay();
      }}
      aria-label={ariaLabel}
    />
  );

  return (
    <div className="flex items-center gap-2">
      <BillStatusChip
        paymentStatus={paymentStatus}
        isOverdue={isOverdue}
        lifecycleState={lifecycleState}
      />
      {disabled && disabledReason ? (
        <Tooltip>
          <TooltipTrigger asChild>
            <span tabIndex={0}>{toggle}</span>
          </TooltipTrigger>
          <TooltipContent>{disabledReason}</TooltipContent>
        </Tooltip>
      ) : (
        toggle
      )}
    </div>
  );
}
