'use client';

import { useMemo, useState } from 'react';
import { CalendarDays } from 'lucide-react';
import { toast } from 'sonner';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import { useBuildings } from '@/lib/api/hooks/use-buildings';
import { useRentCalendar, useToggleRentPayment } from '@/lib/api/hooks/use-rent-calendar';
import { handleError } from '@/lib/utils/error-handler';
import { RentDayPanel } from './rent-day-panel';
import { RentMonthGrid } from './rent-month-grid';
import { RentStatsPanel } from './rent-stats-panel';

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

function CalendarSkeleton() {
  return (
    <div className="grid grid-cols-1 gap-4 p-4 lg:grid-cols-[1fr_1.5fr_1fr]">
      <Skeleton className="h-64 w-full" />
      <Skeleton className="h-64 w-full" />
      <Skeleton className="h-64 w-full" />
    </div>
  );
}

function defaultSelectedDay(year: number, month: number, today: string): number {
  const [todayYear, todayMonth, todayDay] = today.split('-').map(Number);
  if (todayYear === year && todayMonth === month && todayDay) return todayDay;
  return 1;
}

export function RentCalendarSection() {
  const now = new Date();
  const [period, setPeriod] = useState({ year: now.getFullYear(), month: now.getMonth() + 1 });
  const [pickedDay, setPickedDay] = useState<number | null>(null);
  const [buildingValue, setBuildingValue] = useState<string>(ALL_BUILDINGS);

  const { year, month } = period;
  const buildingId = buildingValue === ALL_BUILDINGS ? undefined : Number(buildingValue);

  const { data: buildings } = useBuildings();
  const { data, isLoading } = useRentCalendar(year, month, buildingId);
  const toggleMutation = useToggleRentPayment();

  const referenceMonth = `${String(year)}-${String(month).padStart(2, '0')}-01`;

  const selectedDay = pickedDay ?? (data ? defaultSelectedDay(year, month, data.today) : 1);

  const selectedItems = useMemo(
    () => data?.days.find((day) => day.day === selectedDay)?.items ?? [],
    [data, selectedDay],
  );

  function handleToggle(leaseId: number) {
    toggleMutation.mutate(
      { lease_id: leaseId, reference_month: referenceMonth },
      {
        onSuccess: (result) => {
          toast.success(result.message);
        },
        onError: (error) => {
          handleError(error, 'Erro ao atualizar pagamento');
        },
      },
    );
  }

  function goToPrevMonth() {
    setPeriod((prev) =>
      prev.month === 1
        ? { year: prev.year - 1, month: 12 }
        : { ...prev, month: prev.month - 1 },
    );
    setPickedDay(1);
  }

  function goToNextMonth() {
    setPeriod((prev) =>
      prev.month === 12
        ? { year: prev.year + 1, month: 1 }
        : { ...prev, month: prev.month + 1 },
    );
    setPickedDay(1);
  }

  function goToday() {
    const today = new Date();
    setPeriod({ year: today.getFullYear(), month: today.getMonth() + 1 });
    setPickedDay(null);
  }

  function goNextDue() {
    if (!data?.next_due_date) return;
    const [, , dueDay] = data.next_due_date.split('-');
    if (dueDay) setPickedDay(Number(dueDay));
  }

  return (
    <section className="rounded-xl border bg-card shadow-sm">
      <div className="flex flex-col gap-3 border-b p-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-2">
          <CalendarDays className="h-5 w-5 text-muted-foreground" />
          <h2 className="text-lg font-semibold">Controle de Aluguéis do Mês</h2>
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
          <RentDayPanel
            items={selectedItems}
            dayLabel={dayLabel(year, month, selectedDay)}
            nextDueDate={data.next_due_date}
            isPending={toggleMutation.isPending}
            onToggle={handleToggle}
            onGoToday={goToday}
            onGoNextDue={goNextDue}
          />
          <RentMonthGrid
            year={year}
            month={month}
            days={data.days}
            today={data.today}
            selectedDay={selectedDay}
            onSelectDay={setPickedDay}
            onPrevMonth={goToPrevMonth}
            onNextMonth={goToNextMonth}
          />
          <RentStatsPanel stats={data.stats} year={year} month={month} />
        </div>
      )}
    </section>
  );
}
