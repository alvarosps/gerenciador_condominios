'use client';

import { useState, useEffect } from 'react';
import { Plus, Trash2 } from 'lucide-react';
import { toast } from 'sonner';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { MonthNavigator } from './month-navigator';
import { usePersons } from '@/lib/api/hooks/use-persons';
import {
  usePersonMonthTotal,
  usePersonPaymentSchedules,
  useBulkConfigureSchedule,
} from '@/lib/api/hooks/use-person-payment-schedules';
import { formatCurrency } from '@/lib/utils/formatters';
import { getErrorMessage } from '@/lib/utils/error-handler';

interface PaymentScheduleConfigProps {
  isAdmin: boolean;
}

interface ScheduleEntry {
  due_day: number | '';
  amount: number | '';
}

function SummaryCard({ label, value, variant }: { label: string; value: number; variant?: 'destructive' | 'success' | 'warning' }) {
  const valueClass =
    variant === 'destructive'
      ? 'text-destructive'
      : variant === 'success'
        ? 'text-green-600'
        : variant === 'warning'
          ? 'text-yellow-600'
          : 'text-foreground';

  return (
    <Card>
      <CardContent className="pt-4 pb-4">
        <p className="text-xs text-muted-foreground mb-1">{label}</p>
        <p className={`text-lg font-bold ${valueClass}`}>{formatCurrency(value)}</p>
      </CardContent>
    </Card>
  );
}

export function PaymentScheduleConfig({ isAdmin }: PaymentScheduleConfigProps) {
  const now = new Date();
  const [year, setYear] = useState(now.getFullYear());
  const [month, setMonth] = useState(now.getMonth() + 1);
  const [selectedPersonId, setSelectedPersonId] = useState<number | undefined>(undefined);
  const [entries, setEntries] = useState<ScheduleEntry[]>([]);
  const [showConfirmDialog, setShowConfirmDialog] = useState(false);

  const referenceMonth = `${year}-${String(month).padStart(2, '0')}-01`;

  const { data: persons, isLoading: personsLoading } = usePersons();
  const { data: monthTotal } = usePersonMonthTotal(selectedPersonId, referenceMonth);
  const { data: schedules } = usePersonPaymentSchedules(
    selectedPersonId !== undefined
      ? { person_id: selectedPersonId, reference_month: referenceMonth }
      : undefined,
  );
  const bulkConfigure = useBulkConfigureSchedule();

  useEffect(() => {
    if (schedules) {
      setEntries(
        schedules.map((s) => ({ due_day: s.due_day, amount: s.amount })),
      );
    } else {
      setEntries([]);
    }
  }, [schedules, selectedPersonId, referenceMonth]);

  function handleAddEntry() {
    setEntries((prev) => [...prev, { due_day: '', amount: '' }]);
  }

  function handleRemoveEntry(index: number) {
    setEntries((prev) => prev.filter((_, i) => i !== index));
  }

  function handleEntryChange(index: number, field: keyof ScheduleEntry, value: string) {
    setEntries((prev) =>
      prev.map((entry, i) => {
        if (i !== index) return entry;
        const parsed = value === '' ? '' : Number(value);
        return { ...entry, [field]: parsed };
      }),
    );
  }

  function totalConfigured(): number {
    return entries.reduce((sum, e) => sum + (typeof e.amount === 'number' ? e.amount : 0), 0);
  }

  function validateEntries(): boolean {
    for (const entry of entries) {
      if (entry.due_day === '' || entry.amount === '') {
        toast.error('Preencha todos os campos de dia e valor');
        return false;
      }
      if (typeof entry.due_day === 'number' && (entry.due_day < 1 || entry.due_day > 31)) {
        toast.error('O dia deve estar entre 1 e 31');
        return false;
      }
      if (typeof entry.amount === 'number' && entry.amount <= 0) {
        toast.error('O valor deve ser maior que zero');
        return false;
      }
    }
    return true;
  }

  function handleSaveClick() {
    if (!validateEntries()) return;
    const netTotal = monthTotal?.net_total ?? 0;
    if (totalConfigured() > netTotal) {
      setShowConfirmDialog(true);
    } else {
      void executeSave();
    }
  }

  async function executeSave() {
    if (selectedPersonId === undefined) return;
    try {
      await bulkConfigure.mutateAsync({
        person_id: selectedPersonId,
        reference_month: referenceMonth,
        entries: entries.map((e) => ({
          due_day: e.due_day as number,
          amount: e.amount as number,
        })),
      });
      toast.success('Agenda de pagamentos configurada com sucesso');
    } catch (error) {
      toast.error(getErrorMessage(error, 'Erro ao salvar agenda de pagamentos'));
    }
  }

  const payablePersons = persons?.filter((p) => !p.is_owner && !p.is_employee) ?? [];

  return (
    <div className="space-y-6">
      {/* Selectors row */}
      <div className="flex flex-wrap items-center gap-4">
        <div className="w-64">
          <Select
            value={selectedPersonId !== undefined ? String(selectedPersonId) : ''}
            onValueChange={(val) => setSelectedPersonId(val ? Number(val) : undefined)}
            disabled={personsLoading}
          >
            <SelectTrigger>
              <SelectValue placeholder="Selecione uma pessoa..." />
            </SelectTrigger>
            <SelectContent>
              {payablePersons.map((person) => (
                <SelectItem key={person.id} value={String(person.id)}>
                  {person.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <MonthNavigator
          year={year}
          month={month}
          onMonthChange={(y, m) => { setYear(y); setMonth(m); }}
        />
      </div>

      {selectedPersonId === undefined ? (
        <p className="text-muted-foreground py-8 text-center">
          Selecione uma pessoa para configurar a agenda de pagamentos
        </p>
      ) : (
        <>
          {/* Summary cards */}
          {monthTotal && (
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
              <SummaryCard label="Total Devido" value={monthTotal.net_total} variant="destructive" />
              <SummaryCard label="Total Configurado" value={totalConfigured()} />
              <SummaryCard label="Total Pago" value={monthTotal.total_paid} variant="success" />
              <SummaryCard label="Pendente" value={monthTotal.pending} variant="warning" />
            </div>
          )}

          {/* Schedule entries table */}
          <Card>
            <CardContent className="pt-4">
              {entries.length > 0 ? (
                <table className="w-full text-sm mb-4">
                  <thead>
                    <tr className="border-b text-left text-muted-foreground">
                      <th className="pb-2 font-medium w-32">Dia</th>
                      <th className="pb-2 font-medium">Valor</th>
                      {isAdmin && <th className="pb-2 font-medium w-16 text-right">Ações</th>}
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {entries.map((entry, index) => (
                      <tr key={index}>
                        <td className="py-2 pr-4">
                          <Input
                            type="number"
                            min={1}
                            max={31}
                            value={entry.due_day}
                            onChange={(e) => handleEntryChange(index, 'due_day', e.target.value)}
                            placeholder="Dia"
                            className="w-24"
                            disabled={!isAdmin}
                          />
                        </td>
                        <td className="py-2 pr-4">
                          <Input
                            type="number"
                            min={0}
                            step={0.01}
                            value={entry.amount}
                            onChange={(e) => handleEntryChange(index, 'amount', e.target.value)}
                            placeholder="0,00"
                            className="w-40"
                            disabled={!isAdmin}
                          />
                        </td>
                        {isAdmin && (
                          <td className="py-2 text-right">
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => handleRemoveEntry(index)}
                              aria-label="Remover linha"
                            >
                              <Trash2 className="h-4 w-4 text-destructive" />
                            </Button>
                          </td>
                        )}
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <p className="text-muted-foreground text-center py-6">
                  Nenhuma data configurada para este mês
                </p>
              )}

              {isAdmin && (
                <div className="flex items-center justify-between mt-2">
                  <Button variant="outline" size="sm" onClick={handleAddEntry}>
                    <Plus className="h-4 w-4 mr-1" />
                    Adicionar data
                  </Button>
                  <Button
                    onClick={handleSaveClick}
                    disabled={bulkConfigure.isPending || entries.length === 0}
                  >
                    {bulkConfigure.isPending ? 'Salvando...' : 'Salvar agenda'}
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        </>
      )}

      <AlertDialog open={showConfirmDialog} onOpenChange={setShowConfirmDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Total excede o valor devido</AlertDialogTitle>
            <AlertDialogDescription>
              O total configurado ({formatCurrency(totalConfigured())}) excede o valor devido (
              {formatCurrency(monthTotal?.net_total ?? 0)}). Deseja continuar?
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => {
                setShowConfirmDialog(false);
                void executeSave();
              }}
            >
              Confirmar
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
