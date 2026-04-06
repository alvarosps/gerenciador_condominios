'use client';

import { useState, useCallback } from 'react';
import { ArrowDownCircle, ArrowUpCircle, CheckCircle2, User } from 'lucide-react';
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { useMarkItemPaid } from '@/lib/api/hooks/use-daily-control';
import type { DailyBreakdownDay, DailyEntry, DailyExit, MarkPaidRequest } from '@/lib/api/hooks/use-daily-control';
import { formatCurrency, formatDate } from '@/lib/utils/formatters';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';
import { useAuthStore } from '@/store/auth-store';
import { PersonPayModal } from './person-pay-modal';

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

interface Props {
  day: DailyBreakdownDay | null;
  open: boolean;
  onClose: () => void;
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

function EntryItem({
  entry,
  dateStr,
  isAdmin,
  isPending,
  onMarkPaid,
}: {
  entry: DailyEntry;
  dateStr: string;
  isAdmin: boolean;
  isPending: boolean;
  onMarkPaid: (req: MarkPaidRequest) => void;
}) {
  return (
    <div className="flex items-start gap-3 py-3">
      <ArrowDownCircle className="h-5 w-5 text-success shrink-0 mt-0.5" />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-sm font-medium">{entry.description}</span>
          <Badge variant="outline" className="text-xs">{entry.type}</Badge>
        </div>
        {entry.payment_date && (
          <p className="text-xs text-muted-foreground mt-0.5">
            Pago em {formatDate(entry.payment_date)}
          </p>
        )}
      </div>
      <div className="flex items-center gap-2 shrink-0">
        {entry.paid ? (
          <Badge className="bg-success/10 text-success hover:bg-success/10 text-xs">Pago</Badge>
        ) : (
          <Badge variant="secondary" className="text-xs">Pendente</Badge>
        )}
        <span className="text-sm font-bold text-success">{formatCurrency(entry.amount)}</span>
        {isAdmin && !entry.paid && entry.id !== undefined && (
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

interface PersonScheduleExitItemProps {
  exit: DailyExit;
  dateStr: string;
  isAdmin: boolean;
  isPending: boolean;
  onPayPerson: (exit: DailyExit) => void;
}

function PersonScheduleExitItem({ exit, dateStr, isAdmin, isPending, onPayPerson }: PersonScheduleExitItemProps) {
  const overdue = isOverdueExit(exit, dateStr);

  return (
    <div className={cn('flex items-start gap-3 py-3', overdue && 'bg-destructive/10 -mx-2 px-2 rounded')}>
      <User className="h-5 w-5 text-primary shrink-0 mt-0.5" />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-sm font-medium">{exit.description}</span>
          <Badge variant="outline" className="text-xs">pessoa</Badge>
        </div>
        {exit.person && (
          <div className="text-xs text-muted-foreground mt-0.5">{exit.person}</div>
        )}
        {exit.payment_date && (
          <div className="text-xs text-muted-foreground mt-0.5">
            Pago em {formatDate(exit.payment_date)}
          </div>
        )}
      </div>
      <div className="flex items-center gap-2 shrink-0">
        {exit.paid ? (
          <Badge className="bg-success/10 text-success hover:bg-success/10 text-xs">Pago</Badge>
        ) : overdue ? (
          <Badge variant="destructive" className="text-xs">Vencida</Badge>
        ) : (
          <Badge variant="secondary" className="text-xs">Pendente</Badge>
        )}
        <span className="text-sm font-bold text-destructive">{formatCurrency(exit.amount)}</span>
        {isAdmin && !exit.paid && (
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

interface ExitItemProps {
  exit: DailyExit;
  dateStr: string;
  isAdmin: boolean;
  isPending: boolean;
  onMarkPaid: (req: MarkPaidRequest) => void;
  onPayPerson: (exit: DailyExit) => void;
}

function ExitItem({ exit, dateStr, isAdmin, isPending, onMarkPaid, onPayPerson }: ExitItemProps) {
  if (exit.type === 'person_schedule') {
    return (
      <PersonScheduleExitItem
        exit={exit}
        dateStr={dateStr}
        isAdmin={isAdmin}
        isPending={isPending}
        onPayPerson={onPayPerson}
      />
    );
  }

  const overdue = isOverdueExit(exit, dateStr);

  return (
    <div className={cn('flex items-start gap-3 py-3', overdue && 'bg-destructive/10 -mx-2 px-2 rounded')}>
      <ArrowUpCircle className="h-5 w-5 text-destructive shrink-0 mt-0.5" />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-sm font-medium">{exit.description}</span>
          <Badge variant="outline" className="text-xs">{exit.type}</Badge>
        </div>
        <div className="text-xs text-muted-foreground mt-0.5 flex gap-1 flex-wrap">
          {exit.person && <span>{exit.person}</span>}
          {exit.card && <span>· {exit.card}</span>}
          {exit.building && <span>· {exit.building}</span>}
          {exit.payment_date && <span>· Pago em {formatDate(exit.payment_date)}</span>}
        </div>
      </div>
      <div className="flex items-center gap-2 shrink-0">
        {exit.paid ? (
          <Badge className="bg-success/10 text-success hover:bg-success/10 text-xs">Pago</Badge>
        ) : overdue ? (
          <Badge variant="destructive" className="text-xs">Vencida</Badge>
        ) : (
          <Badge variant="secondary" className="text-xs">Pendente</Badge>
        )}
        <span className="text-sm font-bold text-destructive">{formatCurrency(exit.amount)}</span>
        {isAdmin && !exit.paid && (
          <Button
            variant="ghost"
            size="sm"
            className="h-7 w-7 p-0"
            title="Marcar como pago"
            disabled={isPending}
            onClick={() =>
              onMarkPaid({
                item_type: exit.type === 'credit_card' ? 'credit_card' : 'installment',
                item_id: exit.id,
                payment_date: dateStr,
              })
            }
          >
            <CheckCircle2 className="h-4 w-4 text-success" />
          </Button>
        )}
      </div>
    </div>
  );
}

interface SelectedPersonExit {
  exit: DailyExit;
  referenceMonth: string;
}

export function DayDetailDrawer({ day, open, onClose }: Props) {
  const { user } = useAuthStore();
  const isAdmin = user?.is_staff ?? false;
  const markPaidMutation = useMarkItemPaid();
  const [selectedPersonExit, setSelectedPersonExit] = useState<SelectedPersonExit | null>(null);

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

  const handlePayPerson = useCallback(
    (exit: DailyExit) => {
      if (!day) return;
      const referenceMonth = exit.reference_month ?? day.date.substring(0, 7) + '-01';
      setSelectedPersonExit({ exit, referenceMonth });
    },
    [day],
  );

  if (!day) return null;

  const totalEntries = day.entries.reduce((s, e) => s + e.amount, 0);
  const totalExits = day.exits.reduce((s, e) => s + e.amount, 0);

  return (
    <>
      <Sheet open={open} onOpenChange={(isOpen) => { if (!isOpen) onClose(); }}>
        <SheetContent className="w-full sm:max-w-lg overflow-y-auto">
          <SheetHeader>
            <SheetTitle>
              {formatDate(day.date)} — {day.day_of_week}
            </SheetTitle>
          </SheetHeader>

          <div className="mt-6 space-y-6">
            {/* Summary row */}
            <div className="grid grid-cols-3 gap-3 text-center">
              <div className="bg-success/10 rounded-lg p-3">
                <p className="text-xs text-muted-foreground">Entradas</p>
                <p className="text-sm font-bold text-success">{formatCurrency(totalEntries)}</p>
              </div>
              <div className="bg-destructive/10 rounded-lg p-3">
                <p className="text-xs text-muted-foreground">Saídas</p>
                <p className="text-sm font-bold text-destructive">{formatCurrency(totalExits)}</p>
              </div>
              <div className={cn('rounded-lg p-3', day.cumulative_balance >= 0 ? 'bg-info/10' : 'bg-destructive/10')}>
                <p className="text-xs text-muted-foreground">Saldo Acumulado</p>
                <p className={cn('text-sm font-bold', day.cumulative_balance >= 0 ? 'text-info' : 'text-destructive')}>
                  {formatCurrency(day.cumulative_balance)}
                </p>
              </div>
            </div>

            {/* Entries section */}
            {day.entries.length > 0 && (
              <div>
                <h3 className="text-sm font-semibold text-success mb-2 flex items-center gap-1">
                  <ArrowDownCircle className="h-4 w-4" />
                  Entradas ({day.entries.length})
                </h3>
                <div className="divide-y">
                  {day.entries.map((entry, idx) => (
                    <EntryItem
                      key={`entry-${entry.id ?? idx}`}
                      entry={entry}
                      dateStr={day.date}
                      isAdmin={isAdmin}
                      isPending={markPaidMutation.isPending}
                      onMarkPaid={handleMarkPaidSync}
                    />
                  ))}
                </div>
                <div className="flex justify-between pt-2 mt-2 border-t text-sm">
                  <span className="text-muted-foreground">Subtotal entradas</span>
                  <span className="font-bold text-success">{formatCurrency(totalEntries)}</span>
                </div>
              </div>
            )}

            {day.entries.length > 0 && day.exits.length > 0 && <Separator />}

            {/* Exits section */}
            {day.exits.length > 0 && (
              <div>
                <h3 className="text-sm font-semibold text-destructive mb-2 flex items-center gap-1">
                  <ArrowUpCircle className="h-4 w-4" />
                  Saídas ({day.exits.length})
                </h3>
                <div className="divide-y">
                  {day.exits.map((exit, idx) => (
                    <ExitItem
                      key={`exit-${exit.id}-${idx}`}
                      exit={exit}
                      dateStr={day.date}
                      isAdmin={isAdmin}
                      isPending={markPaidMutation.isPending}
                      onMarkPaid={handleMarkPaidSync}
                      onPayPerson={handlePayPerson}
                    />
                  ))}
                </div>
                <div className="flex justify-between pt-2 mt-2 border-t text-sm">
                  <span className="text-muted-foreground">Subtotal saídas</span>
                  <span className="font-bold text-destructive">{formatCurrency(totalExits)}</span>
                </div>
              </div>
            )}

            {day.entries.length === 0 && day.exits.length === 0 && (
              <p className="text-center text-muted-foreground py-8">Nenhuma movimentação neste dia</p>
            )}
          </div>
        </SheetContent>
      </Sheet>

      {selectedPersonExit?.exit.person_id !== undefined && day !== null && (
        <PersonPayModal
          open={selectedPersonExit !== null}
          onOpenChange={(isOpen) => {
            if (!isOpen) setSelectedPersonExit(null);
          }}
          personId={selectedPersonExit.exit.person_id}
          personName={selectedPersonExit.exit.person ?? selectedPersonExit.exit.description}
          referenceMonth={selectedPersonExit.referenceMonth}
          dueDay={parseInt(day.date.split('-')[2] ?? '1')}
          scheduleAmount={selectedPersonExit.exit.amount}
          paymentDate={day.date}
        />
      )}
    </>
  );
}
