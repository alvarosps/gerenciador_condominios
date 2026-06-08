'use client';

import { useMemo, useState } from 'react';
import { CalendarRange } from 'lucide-react';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import { useBuildings } from '@/lib/api/hooks/use-buildings';
import { useCombinedCalendar, useOverdueBills } from '@/lib/api/hooks/use-combined-calendar';
import { useAuthStore } from '@/store/auth-store';
import type { CombinedCalendarBillExit } from '@/lib/api/hooks/use-combined-calendar';
import { CombinedDayPanel } from './combined-day-panel';
import { CombinedMonthGrid } from './combined-month-grid';
import { CombinedStatsPanel } from './combined-stats-panel';
import { BillPaymentDialog } from '../../finances/bills/_components/bill-payment-dialog';

const ALL_BUILDINGS = 'all';

const WEEKDAYS_PT = [
  'Domingo',
  'Segunda',
  'Terça',
  'Quarta',
  'Quinta',
  'Sexta',
  'Sábado',
] as const;

function dayLabel(year: number, month: number, day: number): string {
  const date = new Date(year, month - 1, day);
  const weekday = WEEKDAYS_PT[date.getDay()] ?? '';
  return `${weekday}, ${String(day).padStart(2, '0')}/${String(month).padStart(2, '0')}`;
}

function defaultSelectedDay(year: number, month: number, today: string): number {
  const [todayYear, todayMonth, todayDay] = today.split('-').map(Number);
  if (todayYear === year && todayMonth === month && todayDay) return todayDay;
  return 1;
}

function CalendarSkeleton() {
  return (
    <div className="grid grid-cols-1 gap-4 p-4 lg:grid-cols-[1fr_1.5fr_1fr]">
      <Skeleton className="h-64 w-full" />
      <Skeleton className="h-64 w-full" />
      <Skeleton className="h-64 w-full" />
    </div>
  );
}

interface MonthSummary {
  toPayTotal: number;
  billsCount: number;
  paidCount: number;
}

function summarizeBillExits(exits: CombinedCalendarBillExit[]): MonthSummary {
  let toPayTotal = 0;
  let billsCount = 0;
  let paidCount = 0;
  for (const exit of exits) {
    if (exit.lifecycle_state !== 'active') continue;
    billsCount += 1;
    if (exit.payment_status === 'paid') {
      paidCount += 1;
    } else {
      toPayTotal += Number(exit.amount_remaining);
    }
  }
  return { toPayTotal: Math.round(toPayTotal * 100) / 100, billsCount, paidCount };
}

export function CombinedCalendarSection() {
  const { user } = useAuthStore();
  const isAdmin = user?.is_staff ?? false;

  const now = new Date();
  const [period, setPeriod] = useState({ year: now.getFullYear(), month: now.getMonth() + 1 });
  const [pickedDay, setPickedDay] = useState<number | null>(null);
  const [buildingValue, setBuildingValue] = useState<string>(ALL_BUILDINGS);
  const [payingBillId, setPayingBillId] = useState<number | null>(null);

  const { year, month } = period;
  const buildingId = buildingValue === ALL_BUILDINGS ? undefined : Number(buildingValue);

  const { data: buildings } = useBuildings();
  const { data, isLoading } = useCombinedCalendar(year, month, buildingId);
  const { data: overdue } = useOverdueBills(buildingId);

  const selectedDay = pickedDay ?? (data ? defaultSelectedDay(year, month, data.today) : 1);

  const selectedDayData = useMemo(
    () => data?.days.find((d) => d.day === selectedDay),
    [data, selectedDay],
  );

  const monthSummary = useMemo(
    () => summarizeBillExits(data?.days.flatMap((d) => d.bill_exits) ?? []),
    [data],
  );

  const payingExit = useMemo(() => {
    if (payingBillId === null || !data) return undefined;
    for (const d of data.days) {
      const found = d.bill_exits.find((exit) => exit.bill_id === payingBillId);
      if (found) return found;
    }
    return undefined;
  }, [payingBillId, data]);

  function goToPrevMonth() {
    setPeriod((prev) =>
      prev.month === 1 ? { year: prev.year - 1, month: 12 } : { ...prev, month: prev.month - 1 },
    );
    setPickedDay(1);
  }

  function goToNextMonth() {
    setPeriod((prev) =>
      prev.month === 12 ? { year: prev.year + 1, month: 1 } : { ...prev, month: prev.month + 1 },
    );
    setPickedDay(1);
  }

  return (
    <section className="rounded-xl border bg-card shadow-sm">
      <div className="flex flex-col gap-3 border-b p-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-2">
          <CalendarRange className="h-5 w-5 text-muted-foreground" />
          <h2 className="text-lg font-semibold">Calendário do Condomínio</h2>
        </div>
        <Select value={buildingValue} onValueChange={setBuildingValue}>
          <SelectTrigger className="w-48">
            <SelectValue placeholder="Prédio" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL_BUILDINGS}>Todos os prédios</SelectItem>
            {buildings?.map((building) =>
              building.id === undefined ? null : (
                <SelectItem key={building.id} value={String(building.id)}>
                  {building.name}
                </SelectItem>
              ),
            )}
          </SelectContent>
        </Select>
      </div>

      {isLoading || !data ? (
        <CalendarSkeleton />
      ) : (
        <div className="grid grid-cols-1 gap-4 p-4 lg:grid-cols-[1fr_1.5fr_1fr]">
          <CombinedDayPanel
            dayLabel={dayLabel(year, month, selectedDay)}
            rentItems={selectedDayData?.rent_entries ?? []}
            billItems={selectedDayData?.bill_exits ?? []}
            isAdmin={isAdmin}
            pendingBillId={payingBillId}
            onPayBill={setPayingBillId}
          />
          <CombinedMonthGrid
            year={year}
            month={month}
            days={data.days}
            today={data.today}
            selectedDay={selectedDay}
            onSelectDay={setPickedDay}
            onPrevMonth={goToPrevMonth}
            onNextMonth={goToNextMonth}
          />
          <CombinedStatsPanel
            year={year}
            month={month}
            toPayTotal={monthSummary.toPayTotal}
            billsCount={monthSummary.billsCount}
            paidCount={monthSummary.paidCount}
            overdueTotal={overdue?.overdue_bills_total ?? '0.00'}
            overdueCount={overdue?.overdue_bills_count ?? 0}
          />
        </div>
      )}

      <BillPaymentDialog
        open={payingBillId !== null}
        billId={payingBillId}
        amountRemaining={payingExit ? Number(payingExit.amount_remaining) : undefined}
        description={payingExit?.description}
        onClose={() => {
          setPayingBillId(null);
        }}
      />
    </section>
  );
}
