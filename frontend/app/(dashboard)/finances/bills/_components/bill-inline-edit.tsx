'use client';

import { useState } from 'react';
import { Pencil } from 'lucide-react';
import { toast } from 'sonner';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { useUpdateBill, useUpdateBillWithLines } from '@/lib/api/hooks/use-bills';
import { showFinanceMutationError } from '@/lib/utils/error-handler';
import { dueDateLabel, formatCurrency } from '@/lib/utils/formatters';
import { ROUTES } from '@/lib/utils/constants';
import type { Bill } from '@/lib/schemas/finances/bill.schema';

/** Consumption account types (S56) — the only ones an embedded installment plan can attach to
 *  (`embedded ⇒ billing_account` of a consumption type, `finances/models.py`). The read
 *  `BillLineItemSerializer` never exposes `BillLineItem.installment`, so this is the only sound
 *  signal that a bill's single line COULD be an embedded parcela (never editable inline as free
 *  money) rather than a plain seed/avulsa line. */
const CONSUMPTION_ACCOUNT_TYPES: ReadonlySet<string> = new Set([
  'water',
  'electricity',
  'internet',
]);

/**
 * Whether a bill's total is eligible for the inline `AmountPopover` (S75 contract): exactly one
 * line, no water/electricity statement, and not tied to a consumption billing account (which could
 * carry an embedded installment line alongside/instead of the seed line). Everything else routes
 * through the full "Editar" modal.
 */
export function canEditAmountInline(bill: Bill): boolean {
  if (bill.line_items.length !== 1) return false;
  if (bill.water_statement ?? bill.electricity_statement) return false;
  const accountType = bill.billing_account?.account_type;
  if (accountType && CONSUMPTION_ACCOUNT_TYPES.has(accountType)) return false;
  return true;
}

interface DueDatePopoverProps {
  bill: Bill;
}

/** Inline vencimento edit — PATCHes only `{ id, due_date }` via `useUpdateBill` (header, S75). */
export function DueDatePopover({ bill }: DueDatePopoverProps) {
  const [open, setOpen] = useState(false);
  const [value, setValue] = useState(bill.due_date);
  const updateBill = useUpdateBill();
  const router = useRouter();

  if (bill.id === undefined) return null;
  const billId = bill.id;

  function handleOpenChange(next: boolean) {
    setOpen(next);
    if (next) setValue(bill.due_date);
  }

  function handleSave() {
    updateBill.mutate(
      { id: billId, due_date: value },
      {
        onSuccess: () => {
          toast.success('Vencimento atualizado');
          setOpen(false);
        },
        onError: (error) => {
          showFinanceMutationError(error, 'Erro ao atualizar vencimento', () =>
            router.push(ROUTES.FINANCES_MONTH_CLOSE)
          );
        },
      }
    );
  }

  return (
    <Popover open={open} onOpenChange={handleOpenChange}>
      <PopoverTrigger asChild>
        <Button variant="ghost" size="sm" className="h-auto gap-1 p-0 font-normal">
          {dueDateLabel(bill.due_date)}
          <Pencil className="h-3 w-3 text-muted-foreground" aria-label="Editar vencimento" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-64 space-y-3">
        <div className="space-y-1">
          <Label htmlFor={`due-date-${String(billId)}`}>Novo vencimento</Label>
          <Input
            id={`due-date-${String(billId)}`}
            type="date"
            value={value}
            onChange={(e) => setValue(e.target.value)}
          />
        </div>
        <div className="flex justify-end gap-2">
          <Button
            type="button"
            size="sm"
            onClick={handleSave}
            disabled={updateBill.isPending || value === ''}
          >
            Salvar
          </Button>
        </div>
      </PopoverContent>
    </Popover>
  );
}

interface AmountPopoverProps {
  bill: Bill;
}

/** Inline total edit — routes through `useUpdateBillWithLines` (money lives in `BillLineItem`,
 *  NEVER PATCH). Only rendered by the caller when `canEditAmountInline(bill)` is true. */
export function AmountPopover({ bill }: AmountPopoverProps) {
  const [open, setOpen] = useState(false);
  const line = bill.line_items[0];
  const [value, setValue] = useState(line ? String(line.amount) : '');
  const [validationError, setValidationError] = useState<string | null>(null);
  const updateWithLines = useUpdateBillWithLines();
  const router = useRouter();

  if (bill.id === undefined || !line) return null;
  const billId = bill.id;

  function handleOpenChange(next: boolean) {
    setOpen(next);
    if (next && line) {
      setValue(String(line.amount));
      setValidationError(null);
    }
  }

  function handleSave() {
    const amount = Number(value);
    if (Number.isNaN(amount) || amount <= 0 || !line) {
      setValidationError('O valor deve ser maior que zero');
      return;
    }
    setValidationError(null);
    updateWithLines.mutate(
      {
        bill_id: billId,
        line_items: [
          {
            description: line.description,
            amount,
            is_offset: line.is_offset,
            ...(line.category?.id !== undefined ? { category_id: line.category.id } : {}),
          },
        ],
      },
      {
        onSuccess: () => {
          toast.success('Valor atualizado');
          setOpen(false);
        },
        onError: (error) => {
          showFinanceMutationError(error, 'Erro ao atualizar valor', () =>
            router.push(ROUTES.FINANCES_MONTH_CLOSE)
          );
        },
      }
    );
  }

  return (
    <Popover open={open} onOpenChange={handleOpenChange}>
      <PopoverTrigger asChild>
        <Button variant="ghost" size="sm" className="h-auto gap-1 p-0 font-normal">
          {formatCurrency(bill.amount_total ?? 0)}
          <Pencil className="h-3 w-3 text-muted-foreground" aria-label="Editar valor" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-64 space-y-3">
        <div className="space-y-1">
          <Label htmlFor={`amount-${String(billId)}`}>Novo valor</Label>
          <Input
            id={`amount-${String(billId)}`}
            type="number"
            min={0}
            step="0.01"
            value={value}
            onChange={(e) => setValue(e.target.value)}
          />
        </div>
        {validationError && <p className="text-sm text-destructive">{validationError}</p>}
        <div className="flex justify-end gap-2">
          <Button type="button" size="sm" onClick={handleSave} disabled={updateWithLines.isPending}>
            Salvar
          </Button>
        </div>
      </PopoverContent>
    </Popover>
  );
}
