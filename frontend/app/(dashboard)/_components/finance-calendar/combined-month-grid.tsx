'use client';

import { getDay, getDaysInMonth, startOfMonth } from 'date-fns';
import { ArrowDownCircle, ArrowUpCircle, ChevronLeft, ChevronRight } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { formatMonthYear } from '@/lib/utils/formatters';
import type { RentCalendarItem } from '@/lib/api/hooks/use-rent-calendar';
import type {
  CombinedCalendarBillExit,
  CombinedCalendarDay,
} from '@/lib/api/hooks/use-combined-calendar';

const WEEKDAY_HEADERS = ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb'] as const;

function billChipClass(exit: CombinedCalendarBillExit): string {
  if (exit.lifecycle_state !== 'active') return 'bg-muted/60 text-muted-foreground';
  if (exit.payment_status === 'paid') return 'bg-success/10 text-success';
  if (exit.is_overdue) return 'bg-destructive/10 text-destructive';
  return 'bg-amber-500/10 text-amber-600 dark:text-amber-400';
}

interface DayCellProps {
  day: number;
  rentEntries: RentCalendarItem[];
  billExits: CombinedCalendarBillExit[];
  isToday: boolean;
  isSelected: boolean;
  onSelectDay: (day: number) => void;
}

function DayCell({ day, rentEntries, billExits, isToday, isSelected, onSelectDay }: DayCellProps) {
  const base = isToday ? `Dia ${String(day)} (hoje)` : `Dia ${String(day)}`;
  // Announce entries/exits to screen readers so the grid never relies on color alone.
  const parts: string[] = [];
  if (rentEntries.length > 0) parts.push(`${String(rentEntries.length)} entrada(s)`);
  if (billExits.length > 0) parts.push(`${String(billExits.length)} saída(s)`);
  const label = parts.length > 0 ? `${base}: ${parts.join(', ')}` : base;

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
      <div className="mt-0.5 space-y-0.5">
        {rentEntries.length > 0 && (
          <div
            title={`${String(rentEntries.length)} aluguel(éis)`}
            className="flex items-center gap-0.5 truncate rounded bg-success/10 px-1 py-0.5 text-[11px] leading-none text-success"
          >
            <ArrowUpCircle className="h-2.5 w-2.5 shrink-0" />
            {rentEntries.length} entrada{rentEntries.length > 1 ? 's' : ''}
          </div>
        )}
        {billExits.map((exit) => (
          <div
            key={exit.bill_id}
            title={`Saída: ${exit.description}`}
            className={cn(
              'flex items-center gap-0.5 truncate rounded px-1 py-0.5 text-[11px] leading-none',
              billChipClass(exit),
            )}
          >
            <ArrowDownCircle className="h-2.5 w-2.5 shrink-0" />
            {exit.description}
          </div>
        ))}
      </div>
    </button>
  );
}

function LegendItem({
  Icon,
  className,
  label,
}: {
  Icon: typeof ArrowUpCircle;
  className: string;
  label: string;
}) {
  return (
    <span className="inline-flex items-center gap-1">
      <Icon className={cn('h-3 w-3', className)} />
      {label}
    </span>
  );
}

interface CombinedMonthGridProps {
  year: number;
  month: number;
  days: CombinedCalendarDay[];
  today: string;
  selectedDay: number;
  onSelectDay: (day: number) => void;
  onPrevMonth: () => void;
  onNextMonth: () => void;
}

export function CombinedMonthGrid({
  year,
  month,
  days,
  today,
  selectedDay,
  onSelectDay,
  onPrevMonth,
  onNextMonth,
}: CombinedMonthGridProps) {
  const monthDate = new Date(year, month - 1, 1);
  const totalDays = getDaysInMonth(monthDate);
  const leadingOffset = getDay(startOfMonth(monthDate));

  const daysByNumber = new Map<number, CombinedCalendarDay>();
  for (const day of days) {
    daysByNumber.set(day.day, day);
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
          const dayData = daysByNumber.get(day);
          return (
            <DayCell
              key={day}
              day={day}
              rentEntries={dayData?.rent_entries ?? []}
              billExits={dayData?.bill_exits ?? []}
              isToday={isCurrentMonth && todayDay === day}
              isSelected={selectedDay === day}
              onSelectDay={onSelectDay}
            />
          );
        })}
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 border-t border-border pt-2 text-[11px] text-muted-foreground">
        <LegendItem Icon={ArrowUpCircle} className="text-success" label="Entradas (aluguéis)" />
        <LegendItem Icon={ArrowDownCircle} className="text-destructive" label="Saídas (contas)" />
      </div>
    </div>
  );
}
