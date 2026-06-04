'use client';

import { getDay, getDaysInMonth, startOfMonth } from 'date-fns';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { formatMonthYear } from '@/lib/utils/formatters';
import type { RentCalendarDay, RentCalendarItem } from '@/lib/api/hooks/use-rent-calendar';

const WEEKDAY_HEADERS = ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb'] as const;

function chipClass(item: RentCalendarItem): string {
  if (!item.is_collectible) return 'bg-muted/60 text-muted-foreground';
  if (item.is_paid) return 'bg-success/10 text-success';
  if (item.is_overdue) return 'bg-destructive/10 text-destructive';
  return 'bg-amber-500/10 text-amber-600 dark:text-amber-400';
}

interface DayCellProps {
  day: number;
  items: RentCalendarItem[];
  isToday: boolean;
  isSelected: boolean;
  onSelectDay: (day: number) => void;
}

function statusLabel(item: RentCalendarItem): string {
  if (!item.is_collectible) return 'não-cobrável';
  if (item.is_paid) return 'pago';
  if (item.is_overdue) return 'em atraso';
  return 'a vencer';
}

function DayCell({ day, items, isToday, isSelected, onSelectDay }: DayCellProps) {
  const base = isToday ? `Dia ${String(day)} (hoje)` : `Dia ${String(day)}`;
  // Announce tenant + status to screen readers so the grid does not rely on color alone.
  const label =
    items.length > 0
      ? `${base}: ${items.map((i) => `${i.tenant_name} (${statusLabel(i)})`).join(', ')}`
      : base;

  return (
    <button
      type="button"
      role="gridcell"
      aria-label={label}
      aria-selected={isSelected}
      onClick={() => {
        onSelectDay(day);
      }}
      className={cn(
        'min-h-[64px] rounded-md border border-border p-1 text-left transition-colors hover:bg-muted/50',
        isSelected && 'border-primary bg-primary/10',
      )}
    >
      {isToday ? (
        <span className="inline-flex h-4 w-4 items-center justify-center rounded-full bg-primary text-[10px] font-bold text-primary-foreground">
          {day}
        </span>
      ) : (
        <span className="text-xs text-muted-foreground">{day}</span>
      )}
      {items.length > 0 && (
        <div className="mt-0.5 space-y-0.5">
          {items.map((item) => (
            <div
              key={item.lease_id}
              title={`${item.tenant_name} — ${statusLabel(item)}`}
              className={cn('truncate rounded px-1 py-0.5 text-[11px] leading-none', chipClass(item))}
            >
              {item.tenant_name}
            </div>
          ))}
        </div>
      )}
    </button>
  );
}

function LegendItem({ className, label }: { className: string; label: string }) {
  return (
    <span className="inline-flex items-center gap-1">
      <span className={cn('h-2.5 w-2.5 rounded-sm', className)} />
      {label}
    </span>
  );
}

interface RentMonthGridProps {
  year: number;
  month: number;
  days: RentCalendarDay[];
  today: string;
  selectedDay: number;
  onSelectDay: (day: number) => void;
  onPrevMonth: () => void;
  onNextMonth: () => void;
}

export function RentMonthGrid({
  year,
  month,
  days,
  today,
  selectedDay,
  onSelectDay,
  onPrevMonth,
  onNextMonth,
}: RentMonthGridProps) {
  const monthDate = new Date(year, month - 1, 1);
  const totalDays = getDaysInMonth(monthDate);
  const leadingOffset = getDay(startOfMonth(monthDate));

  const itemsByDay = new Map<number, RentCalendarItem[]>();
  for (const day of days) {
    itemsByDay.set(day.day, day.items);
  }

  const [todayYear, todayMonth, todayDay] = today.split('-').map(Number);
  const isCurrentMonth = todayYear === year && todayMonth === month;

  return (
    <div className="rounded-lg border border-border p-3">
      <div className="mb-2 flex items-center justify-between">
        <Button variant="ghost" size="icon" onClick={onPrevMonth} aria-label="Mês anterior">
          <ChevronLeft className="h-4 w-4" />
        </Button>
        <span className="text-sm font-semibold">{formatMonthYear(year, month)}</span>
        <Button variant="ghost" size="icon" onClick={onNextMonth} aria-label="Próximo mês">
          <ChevronRight className="h-4 w-4" />
        </Button>
      </div>

      <div className="mb-2 grid grid-cols-7 text-center text-[11px] font-medium uppercase text-muted-foreground">
        {WEEKDAY_HEADERS.map((label) => (
          <div key={label}>{label}</div>
        ))}
      </div>

      <div role="grid" className="grid grid-cols-7 gap-1">
        {Array.from({ length: leadingOffset }, (_, index) => (
          <div key={`offset-${String(index)}`} className="min-h-[64px] rounded-md bg-muted/40" />
        ))}
        {Array.from({ length: totalDays }, (_, index) => {
          const day = index + 1;
          return (
            <DayCell
              key={day}
              day={day}
              items={itemsByDay.get(day) ?? []}
              isToday={isCurrentMonth && todayDay === day}
              isSelected={selectedDay === day}
              onSelectDay={onSelectDay}
            />
          );
        })}
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 border-t border-border pt-2 text-[11px] text-muted-foreground">
        <LegendItem className="bg-success" label="Pago" />
        <LegendItem className="bg-amber-500" label="A vencer" />
        <LegendItem className="bg-destructive" label="Em atraso" />
        <LegendItem className="bg-muted" label="Não-cobrável" />
        <span className="inline-flex items-center gap-1">
          <span className="inline-flex h-3 w-3 items-center justify-center rounded-full bg-primary text-[8px] text-primary-foreground" />
          Hoje
        </span>
      </div>
    </div>
  );
}
