'use client';

import { Switch } from '@/components/ui/switch';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';

interface RentPaymentToggleProps {
  isPaid: boolean;
  canToggle: boolean;
  isPending: boolean;
  onToggle: () => void;
  disabledReason?: string;
}

export function RentPaymentToggle({
  isPaid,
  canToggle,
  isPending,
  onToggle,
  disabledReason,
}: RentPaymentToggleProps) {
  const ariaLabel = !canToggle && disabledReason ? disabledReason : 'Pago?';

  const toggle = (
    <Switch
      checked={isPaid}
      disabled={!canToggle || isPending}
      onCheckedChange={() => {
        onToggle();
      }}
      aria-label={ariaLabel}
    />
  );

  return (
    <div className="flex items-center gap-2">
      <span className="text-xs text-muted-foreground">Pago?</span>
      {!canToggle && disabledReason ? (
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
