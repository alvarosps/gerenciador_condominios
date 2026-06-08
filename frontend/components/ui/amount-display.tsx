import { cn } from '@/lib/utils';
import { formatCurrency } from '@/lib/utils/formatters';

export type AmountTone = 'success' | 'destructive' | 'warning' | 'info' | 'foreground' | 'muted';

export interface AmountDisplayProps {
  amount: number | string;
  showSign?: boolean;
  className?: string;
  size?: 'sm' | 'md' | 'lg';
  tone?: AmountTone;
  autoTone?: boolean;
}

const toneClasses: Record<AmountTone, string> = {
  success: 'text-success',
  destructive: 'text-destructive',
  warning: 'text-warning',
  info: 'text-info',
  foreground: 'text-foreground',
  muted: 'text-muted-foreground',
};

const sizeClasses = {
  sm: 'text-sm',
  md: 'text-base',
  lg: 'text-2xl font-bold',
};

export function AmountDisplay({
  amount,
  showSign = false,
  className,
  size = 'md',
  tone,
  autoTone = false,
}: AmountDisplayProps) {
  const num = typeof amount === 'string' ? parseFloat(amount) : amount;
  const absFormatted = formatCurrency(Math.abs(num));
  const isNegative = num < 0;

  const sign = showSign ? (isNegative ? '-' : '+') : isNegative ? '-' : '';

  let resolvedTone: AmountTone = tone ?? 'foreground';
  if (!tone && autoTone) {
    resolvedTone = num >= 0 ? 'success' : 'destructive';
  }

  return (
    <span className={cn(sizeClasses[size], 'tabular-nums', toneClasses[resolvedTone], className)}>
      {sign}
      {absFormatted}
    </span>
  );
}
