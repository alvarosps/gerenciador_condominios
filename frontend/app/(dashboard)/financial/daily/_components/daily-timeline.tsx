'use client';

import { useState, useCallback } from 'react';
import { ArrowDownCircle, ArrowUpCircle, CheckCircle2, SkipForward, User } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog';
import { useMarkItemPaid } from '@/lib/api/hooks/use-daily-control';
import type { DailyBreakdownDay, DailyEntry, DailyExit, MarkPaidRequest } from '@/lib/api/hooks/use-daily-control';
import { useCreateExpenseMonthSkip } from '@/lib/api/hooks/use-expense-month-skips';
import { formatCurrency, formatDate } from '@/lib/utils/formatters';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';
import { PersonPayModal } from './person-pay-modal';

export interface DailyFilters {
  direction?: 'all' | 'entries' | 'exits';
  status?: 'all' | 'paid' | 'pending' | 'overdue';
  person?: string;
  building?: string;
}

interface Props {
  data: DailyBreakdownDay[];
  isLoading: boolean;
  filters: DailyFilters;
  isAdmin: boolean;
  onDayClick?: (day: DailyBreakdownDay) => void;
}

function isOverdueExit(exit: DailyExit, dateStr: string): boolean {
  if (exit.paid) return false;
  if (!exit.due) return false;
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const exitDate = new Date(dateStr);
  exitDate.setHours(0, 0, 0, 0);
  return exitDate < today;
}

function getItemStatus(item: DailyEntry | DailyExit, dateStr: string, isExit: boolean): 'paid' | 'overdue' | 'pending' {
  if (item.paid) return 'paid';
  if (isExit) {
    const exit = item as DailyExit;
    if (isOverdueExit(exit, dateStr)) return 'overdue';
  }
  return 'pending';
}

function StatusBadge({ status }: { status: 'paid' | 'overdue' | 'pending' }) {
  if (status === 'paid') {
    return <Badge className="bg-success/10 text-success hover:bg-success/10 text-xs">Pago</Badge>;
  }
  if (status === 'overdue') {
    return <Badge variant="destructive" className="text-xs">Vencida</Badge>;
  }
  return <Badge variant="secondary" className="text-xs">Pendente</Badge>;
}

function MarkPaidButton({
  itemType,
  itemId,
  dateStr,
  isPending,
  onMarkPaid,
}: {
  itemType: MarkPaidRequest['item_type'];
  itemId: number;
  dateStr: string;
  isPending: boolean;
  onMarkPaid: (req: MarkPaidRequest) => void;
}) {
  return (
    <Button
      variant="ghost"
      size="sm"
      className="h-7 w-7 p-0"
      title="Marcar como pago"
      disabled={isPending}
      onClick={() => onMarkPaid({ item_type: itemType, item_id: itemId, payment_date: dateStr })}
    >
      <CheckCircle2 className="h-4 w-4 text-success" />
    </Button>
  );
}

interface SkipButtonProps {
  exitId: number;
  description: string;
  referenceMonth: string;
  isPending: boolean;
}

function SkipButton({ exitId, description, referenceMonth, isPending }: SkipButtonProps) {
  const createSkipMutation = useCreateExpenseMonthSkip();

  const handleSkip = async () => {
    try {
      await createSkipMutation.mutateAsync({ expense_id: exitId, reference_month: referenceMonth });
      toast.success(`"${description}" não será cobrado neste mês`);
    } catch {
      toast.error('Erro ao pular cobrança');
    }
  };

  const handleSkipSync = () => {
    void handleSkip();
  };

  const [monthYear] = referenceMonth.split('-').slice(0, 2);
  const label = monthYear ?? referenceMonth;

  return (
    <AlertDialog>
      <AlertDialogTrigger asChild>
        <Button
          variant="ghost"
          size="sm"
          className="h-7 w-7 p-0"
          title="Pular este mês"
          disabled={isPending || createSkipMutation.isPending}
        >
          <SkipForward className="h-4 w-4 text-muted-foreground" />
        </Button>
      </AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Pular cobrança</AlertDialogTitle>
          <AlertDialogDescription>
            Não cobrar &quot;{description}&quot; em {label}? Esta ação pode ser revertida.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Cancelar</AlertDialogCancel>
          <AlertDialogAction onClick={handleSkipSync} disabled={createSkipMutation.isPending}>
            {createSkipMutation.isPending ? 'Pulando...' : 'Confirmar'}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}

interface EntryRowProps {
  entry: DailyEntry;
  dateStr: string;
  isAdmin: boolean;
  isPending: boolean;
  onMarkPaid: (req: MarkPaidRequest) => void;
}

function EntryRow({ entry, dateStr, isAdmin, isPending, onMarkPaid }: EntryRowProps) {
  const status = getItemStatus(entry, dateStr, false);

  return (
    <div className="flex items-center gap-3 py-2 px-3 rounded-lg hover:bg-muted/50 transition-colors">
      <ArrowDownCircle className="h-5 w-5 text-success shrink-0" />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-sm font-medium truncate">{entry.description}</span>
          <Badge variant="outline" className="text-xs shrink-0">{entry.type}</Badge>
        </div>
      </div>
      <div className="flex items-center gap-2 shrink-0">
        <StatusBadge status={status} />
        <span className="text-sm font-bold text-success">{formatCurrency(entry.amount)}</span>
        {isAdmin && status !== 'paid' && entry.id !== undefined && (
          <MarkPaidButton
            itemType="income"
            itemId={entry.id}
            dateStr={dateStr}
            isPending={isPending}
            onMarkPaid={onMarkPaid}
          />
        )}
      </div>
    </div>
  );
}

interface PersonScheduleExitRowProps {
  exit: DailyExit;
  dateStr: string;
  isAdmin: boolean;
  isPending: boolean;
  onPayPerson: (exit: DailyExit) => void;
}

function PersonScheduleExitRow({ exit, dateStr, isAdmin, isPending, onPayPerson }: PersonScheduleExitRowProps) {
  const status = getItemStatus(exit, dateStr, true);

  return (
    <div
      className={cn(
        'flex items-center gap-3 py-2 px-3 rounded-lg hover:bg-muted/50 transition-colors',
        status === 'overdue' && 'bg-destructive/10',
      )}
    >
      <User className="h-5 w-5 text-primary shrink-0" />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-sm font-medium truncate">{exit.description}</span>
          <Badge variant="outline" className="text-xs shrink-0">pessoa</Badge>
        </div>
        {exit.person && (
          <div className="text-xs text-muted-foreground mt-0.5">{exit.person}</div>
        )}
      </div>
      <div className="flex items-center gap-2 shrink-0">
        <StatusBadge status={status} />
        <span className="text-sm font-bold text-destructive">{formatCurrency(exit.amount)}</span>
        {isAdmin && status !== 'paid' && (
          <Button
            variant="ghost"
            size="sm"
            className="h-7 px-2"
            title="Registrar pagamento"
            disabled={isPending}
            onClick={() => onPayPerson(exit)}
          >
            <CheckCircle2 className="h-4 w-4 text-success" />
            <span className="text-xs ml-1">Pagar</span>
          </Button>
        )}
      </div>
    </div>
  );
}

interface ExitRowProps {
  exit: DailyExit;
  dateStr: string;
  referenceMonth: string;
  isAdmin: boolean;
  isPending: boolean;
  onMarkPaid: (req: MarkPaidRequest) => void;
  onPayPerson: (exit: DailyExit) => void;
}

function ExitRow({ exit, dateStr, referenceMonth, isAdmin, isPending, onMarkPaid, onPayPerson }: ExitRowProps) {
  if (exit.type === 'person_schedule') {
    return (
      <PersonScheduleExitRow
        exit={exit}
        dateStr={dateStr}
        isAdmin={isAdmin}
        isPending={isPending}
        onPayPerson={onPayPerson}
      />
    );
  }

  const status = getItemStatus(exit, dateStr, true);

  return (
    <div
      className={cn(
        'flex items-center gap-3 py-2 px-3 rounded-lg hover:bg-muted/50 transition-colors',
        status === 'overdue' && 'bg-destructive/10',
      )}
    >
      <ArrowUpCircle className="h-5 w-5 text-destructive shrink-0" />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-sm font-medium truncate">{exit.description}</span>
          <Badge variant="outline" className="text-xs shrink-0">{exit.type}</Badge>
        </div>
        {(exit.person ?? exit.card ?? exit.building) && (
          <div className="text-xs text-muted-foreground mt-0.5 flex gap-1 flex-wrap">
            {exit.person && <span>{exit.person}</span>}
            {exit.card && <span>· {exit.card}</span>}
            {exit.building && <span>· {exit.building}</span>}
          </div>
        )}
      </div>
      <div className="flex items-center gap-2 shrink-0">
        <StatusBadge status={status} />
        <span className="text-sm font-bold text-destructive">{formatCurrency(exit.amount)}</span>
        {isAdmin && status !== 'paid' && (
          <>
            <MarkPaidButton
              itemType={exit.type === 'credit_card' ? 'credit_card' : 'installment'}
              itemId={exit.id}
              dateStr={dateStr}
              isPending={isPending}
              onMarkPaid={onMarkPaid}
            />
            <SkipButton
              exitId={exit.id}
              description={exit.description}
              referenceMonth={referenceMonth}
              isPending={isPending}
            />
          </>
        )}
      </div>
    </div>
  );
}

function TimelineSkeleton() {
  return (
    <div className="space-y-4">
      {[1, 2, 3].map((i) => (
        <div key={i} className="border rounded-lg p-4 space-y-3">
          <div className="flex items-center justify-between">
            <Skeleton className="h-5 w-32" />
            <Skeleton className="h-5 w-20" />
          </div>
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
        </div>
      ))}
    </div>
  );
}

function filterDay(
  day: DailyBreakdownDay,
  filters: DailyFilters,
): { entries: DailyEntry[]; exits: DailyExit[] } {
  let entries = day.entries;
  let exits = day.exits;

  if (filters.direction === 'exits') {
    entries = [];
  } else if (filters.direction === 'entries') {
    exits = [];
  }

  if (filters.status === 'paid') {
    entries = entries.filter((e) => e.paid);
    exits = exits.filter((e) => e.paid);
  } else if (filters.status === 'pending') {
    entries = entries.filter((e) => !e.paid);
    exits = exits.filter((e) => !e.paid && !isOverdueExit(e, day.date));
  } else if (filters.status === 'overdue') {
    entries = [];
    exits = exits.filter((e) => isOverdueExit(e, day.date));
  }

  if (filters.person) {
    exits = exits.filter((e) => e.person === filters.person);
  }

  if (filters.building) {
    exits = exits.filter((e) => e.building === filters.building);
  }

  return { entries, exits };
}

interface SelectedPersonExit {
  exit: DailyExit;
  dateStr: string;
  referenceMonth: string;
}

export function DailyTimeline({ data, isLoading, filters, isAdmin, onDayClick }: Props) {
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set());
  const [selectedPersonExit, setSelectedPersonExit] = useState<SelectedPersonExit | null>(null);
  const markPaidMutation = useMarkItemPaid();

  const handleMarkPaid = useCallback(
    async (req: MarkPaidRequest) => {
      try {
        await markPaidMutation.mutateAsync(req);
        toast.success('Item marcado como pago');
      } catch {
        toast.error('Erro ao marcar item como pago');
      }
    },
    [markPaidMutation],
  );

  const handleMarkPaidSync = useCallback(
    (req: MarkPaidRequest) => {
      void handleMarkPaid(req);
    },
    [handleMarkPaid],
  );

  const toggleCollapse = useCallback((dateStr: string) => {
    setCollapsed((prev) => {
      const next = new Set(prev);
      if (next.has(dateStr)) {
        next.delete(dateStr);
      } else {
        next.add(dateStr);
      }
      return next;
    });
  }, []);

  const handlePayPerson = useCallback((exit: DailyExit, dateStr: string, referenceMonth: string) => {
    setSelectedPersonExit({ exit, dateStr, referenceMonth });
  }, []);

  if (isLoading) {
    return <TimelineSkeleton />;
  }

  if (data.length === 0) {
    return (
      <div className="text-center text-muted-foreground py-12">
        Nenhum dado disponível para o período selecionado
      </div>
    );
  }

  return (
    <>
      <div className="space-y-3">
        {data.map((day) => {
          const { entries, exits } = filterDay(day, filters);
          const hasItems = entries.length > 0 || exits.length > 0;

          if (!hasItems && (filters.direction !== 'all' || filters.status !== 'all' || filters.person || filters.building)) {
            return null;
          }

          const isCollapsed = collapsed.has(day.date) ?? (!hasItems);
          const cumulativeBalance = day.cumulative_balance;

          const dayReferenceMonth = day.date.substring(0, 7) + '-01';

          return (
            <div key={day.date} className="border rounded-lg overflow-hidden">
              <button
                className="w-full flex items-center justify-between px-4 py-3 bg-muted/30 hover:bg-muted/60 transition-colors"
                onClick={() => {
                  toggleCollapse(day.date);
                  if (onDayClick && hasItems) onDayClick(day);
                }}
              >
                <div className="flex items-center gap-3">
                  <span className="font-semibold text-sm">{formatDate(day.date)}</span>
                  <span className="text-xs text-muted-foreground capitalize">{day.day_of_week}</span>
                  {!hasItems && (
                    <Badge variant="secondary" className="text-xs">Sem movimentações</Badge>
                  )}
                </div>
                <div className="flex items-center gap-3">
                  {hasItems && (
                    <>
                      {entries.length > 0 && (
                        <span className="text-xs text-success font-medium">
                          +{formatCurrency(entries.reduce((s, e) => s + e.amount, 0))}
                        </span>
                      )}
                      {exits.length > 0 && (
                        <span className="text-xs text-destructive font-medium">
                          -{formatCurrency(exits.reduce((s, e) => s + e.amount, 0))}
                        </span>
                      )}
                    </>
                  )}
                  <span
                    className={cn(
                      'text-sm font-bold',
                      cumulativeBalance >= 0 ? 'text-success' : 'text-destructive',
                    )}
                  >
                    {formatCurrency(cumulativeBalance)}
                  </span>
                </div>
              </button>

              {!isCollapsed && hasItems && (
                <div className="divide-y">
                  {entries.map((entry, idx) => (
                    <EntryRow
                      key={`entry-${entry.id ?? idx}`}
                      entry={entry}
                      dateStr={day.date}
                      isAdmin={isAdmin}
                      isPending={markPaidMutation.isPending}
                      onMarkPaid={handleMarkPaidSync}
                    />
                  ))}
                  {exits.map((exit, idx) => (
                    <ExitRow
                      key={`exit-${exit.id}-${idx}`}
                      exit={exit}
                      dateStr={day.date}
                      referenceMonth={exit.reference_month ?? dayReferenceMonth}
                      isAdmin={isAdmin}
                      isPending={markPaidMutation.isPending}
                      onMarkPaid={handleMarkPaidSync}
                      onPayPerson={(e) => handlePayPerson(e, day.date, exit.reference_month ?? dayReferenceMonth)}
                    />
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {selectedPersonExit !== null && selectedPersonExit.exit.person_id !== undefined && (
        <PersonPayModal
          open={selectedPersonExit !== null}
          onOpenChange={(isOpen) => {
            if (!isOpen) setSelectedPersonExit(null);
          }}
          personId={selectedPersonExit.exit.person_id}
          personName={selectedPersonExit.exit.person ?? selectedPersonExit.exit.description}
          referenceMonth={selectedPersonExit.referenceMonth}
          dueDay={parseInt(selectedPersonExit.dateStr.split('-')[2] ?? '1')}
          scheduleAmount={selectedPersonExit.exit.amount}
          paymentDate={selectedPersonExit.dateStr}
        />
      )}
    </>
  );
}
