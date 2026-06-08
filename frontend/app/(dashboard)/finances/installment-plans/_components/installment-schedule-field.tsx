'use client';

import { useState } from 'react';
import { AlertTriangle, Check, Pencil, X } from 'lucide-react';
import { toast } from 'sonner';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useUpdateInstallment } from '@/lib/api/hooks/use-installment-plans';
import { handleError } from '@/lib/utils/error-handler';
import { formatCurrency } from '@/lib/utils/formatters';
import type { Installment } from '@/lib/schemas/finances/installment-plan.schema';

/** Format a YYYY-MM-DD date as DD/MM/YYYY using split (never new Date(iso)). */
function dueDateLabel(dueDate: string): string {
  const [year, month, day] = dueDate.split('-');
  if (!year || !month || !day) return dueDate;
  return `${day}/${month}/${year}`;
}

interface ScheduleRowProps {
  installment: Installment;
  isAdmin: boolean;
}

function ScheduleRow({ installment, isAdmin }: ScheduleRowProps) {
  const updateInstallment = useUpdateInstallment();
  const [editing, setEditing] = useState(false);
  const [amount, setAmount] = useState<number>(installment.amount);
  const [dueDate, setDueDate] = useState<string>(installment.due_date);

  function startEditing() {
    setAmount(installment.amount);
    setDueDate(installment.due_date);
    setEditing(true);
  }

  function cancelEditing() {
    setEditing(false);
  }

  function save() {
    if (installment.id === undefined) return;
    if (amount < 0) {
      toast.error('O valor da parcela não pode ser negativo');
      return;
    }
    updateInstallment.mutate(
      { id: installment.id, amount, due_date: dueDate },
      {
        onSuccess: () => {
          toast.success('Parcela atualizada com sucesso');
          setEditing(false);
        },
        onError: (error) => {
          handleError(error, 'Erro ao atualizar parcela');
        },
      },
    );
  }

  return (
    <div className="flex flex-wrap items-center gap-3 rounded-md border p-3">
      <span className="w-16 text-sm font-medium">Parcela {installment.number ?? '—'}</span>

      {editing ? (
        <>
          <Input
            type="date"
            value={dueDate}
            onChange={(e) => setDueDate(e.target.value)}
            className="w-40"
            aria-label="Vencimento da parcela"
          />
          <Input
            type="number"
            step="0.01"
            min="0"
            value={Number.isNaN(amount) ? '' : amount}
            onChange={(e) => setAmount(e.target.valueAsNumber)}
            className="w-32"
            aria-label="Valor da parcela"
          />
          <Button
            type="button"
            size="sm"
            onClick={save}
            disabled={updateInstallment.isPending}
            aria-label="Salvar parcela"
          >
            <Check className="h-4 w-4" />
          </Button>
          <Button
            type="button"
            size="sm"
            variant="outline"
            onClick={cancelEditing}
            aria-label="Cancelar edição"
          >
            <X className="h-4 w-4" />
          </Button>
        </>
      ) : (
        <>
          <span className="w-32 text-sm text-muted-foreground">{dueDateLabel(installment.due_date)}</span>
          <span className="w-32 text-sm font-medium">{formatCurrency(installment.amount)}</span>
          {installment.is_overdue ? (
            <Badge variant="destructive" className="gap-1">
              <AlertTriangle className="h-3 w-3" />
              Vencida
            </Badge>
          ) : null}
          {isAdmin && (
            <Button
              type="button"
              size="sm"
              variant="ghost"
              onClick={startEditing}
              aria-label="Editar parcela"
            >
              <Pencil className="h-4 w-4" />
            </Button>
          )}
        </>
      )}
    </div>
  );
}

interface InstallmentScheduleFieldProps {
  installments: Installment[];
  isAdmin: boolean;
}

export function InstallmentScheduleField({
  installments,
  isAdmin,
}: InstallmentScheduleFieldProps) {
  if (installments.length === 0) {
    return (
      <p className="rounded-md border-2 border-dashed py-8 text-center text-sm text-muted-foreground">
        Nenhuma parcela materializada ainda — gere as contas do mês.
      </p>
    );
  }

  const ordered = [...installments].sort((a, b) => (a.number ?? 0) - (b.number ?? 0));

  return (
    <div className="space-y-2">
      {ordered.map((installment) => (
        <ScheduleRow
          key={installment.id ?? installment.number}
          installment={installment}
          isAdmin={isAdmin}
        />
      ))}
    </div>
  );
}
