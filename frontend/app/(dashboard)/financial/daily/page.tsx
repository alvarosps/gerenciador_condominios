'use client';

import { useState, useCallback } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { ChevronLeft, ChevronRight, Plus } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useDailyBreakdown } from '@/lib/api/hooks/use-daily-control';
import { usePersons } from '@/lib/api/hooks/use-persons';
import { useBuildings } from '@/lib/api/hooks/use-buildings';
import { useAuthStore } from '@/store/auth-store';
import { getDefaultExpenseDate, MONTH_ABBR } from '@/lib/utils/formatters';
import { DailySummaryCards } from './_components/daily-summary-cards';
import { DailyBalanceChart } from './_components/daily-balance-chart';
import { DailyTimeline, type DailyFilters } from './_components/daily-timeline';
import { DayDetailDrawer } from './_components/day-detail-drawer';
import { ExpenseFormModal } from '@/app/(dashboard)/financial/expenses/_components/expense-form-modal';
import type { DailyBreakdownDay } from '@/lib/api/hooks/use-daily-control';

const MONTH_NAMES = [
  'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
  'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro',
];


export default function DailyControlPage() {
  const { user } = useAuthStore();
  const isAdmin = user?.is_staff ?? false;
  const queryClient = useQueryClient();

  const now = new Date();
  const [year, setYear] = useState(now.getFullYear());
  const [month, setMonth] = useState(now.getMonth() + 1);
  const [isCreating, setIsCreating] = useState(false);
  const [isCreatingNextMonth, setIsCreatingNextMonth] = useState(false);

  const nextMonth = month === 12 ? 1 : month + 1;
  const nextYear = month === 12 ? year + 1 : year;
  const currentMonthAbbr = MONTH_ABBR[month - 1] ?? '';
  const nextMonthAbbr = MONTH_ABBR[nextMonth - 1] ?? '';

  const handleExpenseSaved = useCallback(() => {
    void queryClient.invalidateQueries({ queryKey: ['daily-control'] });
  }, [queryClient]);

  const [filters, setFilters] = useState<DailyFilters>({
    direction: 'all',
    status: 'all',
    person: undefined,
    building: undefined,
  });

  const [selectedDay, setSelectedDay] = useState<DailyBreakdownDay | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);

  const { data: breakdownData, isLoading: isBreakdownLoading } = useDailyBreakdown(year, month);
  const { data: persons } = usePersons();
  const { data: buildings } = useBuildings();

  const goToPrevMonth = useCallback(() => {
    setMonth((prev) => {
      if (prev === 1) {
        setYear((y) => y - 1);
        return 12;
      }
      return prev - 1;
    });
  }, []);

  const goToNextMonth = useCallback(() => {
    setMonth((prev) => {
      if (prev === 12) {
        setYear((y) => y + 1);
        return 1;
      }
      return prev + 1;
    });
  }, []);

  const handleDayClick = useCallback((day: DailyBreakdownDay) => {
    setSelectedDay(day);
    setDrawerOpen(true);
  }, []);

  const handleDrawerClose = useCallback(() => {
    setDrawerOpen(false);
  }, []);

  const monthLabel = MONTH_NAMES[month - 1] ?? '';

  const safeBreakdown = breakdownData ?? [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold">Controle Diário</h1>
          <p className="text-muted-foreground mt-1">
            Acompanhe entradas e saídas dia a dia
          </p>
        </div>
        <div className="flex items-center gap-3 flex-wrap">
          <div className="flex items-center gap-2">
            <Button variant="outline" size="icon" onClick={goToPrevMonth} aria-label="Mês anterior">
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <span className="text-lg font-semibold min-w-[160px] text-center">
              {monthLabel} {year}
            </span>
            <Button variant="outline" size="icon" onClick={goToNextMonth} aria-label="Próximo mês">
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
          {isAdmin && (
            <div className="flex gap-2">
              <Button size="sm" onClick={() => setIsCreating(true)}>
                <Plus className="h-4 w-4 mr-2" />
                Nova Despesa ({currentMonthAbbr})
              </Button>
              <Button size="sm" variant="outline" onClick={() => setIsCreatingNextMonth(true)}>
                <Plus className="h-4 w-4 mr-2" />
                Nova Despesa ({nextMonthAbbr})
              </Button>
            </div>
          )}
        </div>
      </div>

      {/* Summary Cards */}
      <DailySummaryCards year={year} month={month} />

      {/* Balance Chart */}
      <div className="hidden md:block">
        <DailyBalanceChart data={safeBreakdown} isLoading={isBreakdownLoading} />
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 items-center">
        <Select
          value={filters.direction ?? 'all'}
          onValueChange={(value) =>
            setFilters((prev) => ({
              ...prev,
              direction: value as DailyFilters['direction'],
            }))
          }
        >
          <SelectTrigger className="w-40">
            <SelectValue placeholder="Tipo" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todos</SelectItem>
            <SelectItem value="entries">Entradas</SelectItem>
            <SelectItem value="exits">Saídas</SelectItem>
          </SelectContent>
        </Select>

        <Select
          value={filters.status ?? 'all'}
          onValueChange={(value) =>
            setFilters((prev) => ({
              ...prev,
              status: value as DailyFilters['status'],
            }))
          }
        >
          <SelectTrigger className="w-40">
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todos</SelectItem>
            <SelectItem value="paid">Pagos</SelectItem>
            <SelectItem value="pending">Pendentes</SelectItem>
            <SelectItem value="overdue">Vencidos</SelectItem>
          </SelectContent>
        </Select>

        <Select
          value={filters.person ?? 'all'}
          onValueChange={(value) =>
            setFilters((prev) => ({
              ...prev,
              person: value === 'all' ? undefined : value,
            }))
          }
        >
          <SelectTrigger className="w-48">
            <SelectValue placeholder="Pessoa" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todas as pessoas</SelectItem>
            {persons?.map((p) => (
              <SelectItem key={p.id} value={p.name}>
                {p.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select
          value={filters.building ?? 'all'}
          onValueChange={(value) =>
            setFilters((prev) => ({
              ...prev,
              building: value === 'all' ? undefined : value,
            }))
          }
        >
          <SelectTrigger className="w-48">
            <SelectValue placeholder="Prédio" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todos os prédios</SelectItem>
            {buildings?.map((b) => (
              <SelectItem key={b.id} value={b.name}>
                {b.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        {(filters.direction !== 'all' || filters.status !== 'all' || (filters.person ?? filters.building) !== undefined) && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() =>
              setFilters({ direction: 'all', status: 'all', person: undefined, building: undefined })
            }
          >
            Limpar filtros
          </Button>
        )}
      </div>

      {/* Timeline */}
      <DailyTimeline
        data={safeBreakdown}
        isLoading={isBreakdownLoading}
        filters={filters}
        isAdmin={isAdmin}
        onDayClick={handleDayClick}
      />

      {/* Day Detail Drawer */}
      <DayDetailDrawer
        day={selectedDay}
        open={drawerOpen}
        onClose={handleDrawerClose}
      />

      {isCreating && (
        <ExpenseFormModal
          open={isCreating}
          onClose={() => setIsCreating(false)}
          defaultExpenseDate={getDefaultExpenseDate(year, month)}
          onSuccess={handleExpenseSaved}
        />
      )}

      {isCreatingNextMonth && (
        <ExpenseFormModal
          open={isCreatingNextMonth}
          onClose={() => setIsCreatingNextMonth(false)}
          defaultExpenseDate={getDefaultExpenseDate(nextYear, nextMonth)}
          onSuccess={handleExpenseSaved}
        />
      )}
    </div>
  );
}
