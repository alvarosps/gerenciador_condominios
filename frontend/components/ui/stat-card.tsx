import type * as React from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { cn } from '@/lib/utils';

export type StatTone = 'success' | 'destructive' | 'warning' | 'info' | 'foreground' | 'muted';

export interface StatCardProps {
  label: string;
  value: React.ReactNode;
  icon?: React.ReactNode;
  tone?: StatTone;
  subLabel?: React.ReactNode;
  className?: string;
  loading?: boolean;
}

const valueToneClasses: Record<StatTone, string> = {
  success: 'text-success',
  destructive: 'text-destructive',
  warning: 'text-warning',
  info: 'text-info',
  foreground: 'text-foreground',
  muted: 'text-muted-foreground',
};

const iconToneClasses: Record<StatTone, string> = {
  success: 'bg-success/10 text-success',
  destructive: 'bg-destructive/10 text-destructive',
  warning: 'bg-warning/10 text-warning',
  info: 'bg-info/10 text-info',
  foreground: 'bg-muted text-foreground',
  muted: 'bg-muted text-muted-foreground',
};

export function StatCard({
  label,
  value,
  icon,
  tone = 'foreground',
  subLabel,
  className,
  loading = false,
}: StatCardProps) {
  if (loading) {
    return (
      <Card className={className} aria-live="polite" aria-busy={true}>
        <CardContent className="flex flex-col gap-2 pt-6">
          <div className="flex items-center justify-between">
            <Skeleton className="h-3 w-24" />
            {icon && <Skeleton className="size-8 rounded-lg" />}
          </div>
          <Skeleton className="h-8 w-32" />
          {subLabel !== undefined && <Skeleton className="h-3 w-20" />}
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={cn('transition-shadow duration-200 hover:shadow-md', className)}>
      <CardContent className="flex flex-col gap-2 pt-6">
        <div className="flex items-center justify-between">
          <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
            {label}
          </span>
          {icon && (
            <span
              className={cn('grid size-8 place-items-center rounded-lg', iconToneClasses[tone])}
            >
              {icon}
            </span>
          )}
        </div>
        <span className={cn('text-2xl font-bold tabular-nums', valueToneClasses[tone])}>
          {value}
        </span>
        {subLabel && <span className="text-xs text-muted-foreground">{subLabel}</span>}
      </CardContent>
    </Card>
  );
}
