'use client';

import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Wallet } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { usePayBill } from '@/lib/api/hooks/use-bills';
import { getErrorMessage, handleError } from '@/lib/utils/error-handler';
import { fundedFromValues } from '@/lib/schemas/finances/category.schema';
import type { Bill } from '@/lib/schemas/finances/bill.schema';
import {
  FUNDED_FROM_LABELS,
  type PaymentFormValues,
  paymentFormSchema,
  todayISO,
} from './bill-payment-form';

const EXCEEDS_REMAINDER_MESSAGE =
  'O valor excede o restante. Marque a opção de juros/multa ou reduza o valor.';

/**
 * Decimal-string `new_total` for the `pay` request (contract S68 verbatim, ALWAYS 2 decimals via
 * `toFixed(2)` — never a number): the estimated-bill path adjusts the seed line to the paid value;
 * the confirmed-bill juros/multa path adds the excess as a "Juros/multa" line on top of the total.
 * Returns `undefined` when no adjustment is needed (paid at/under the remainder).
 */
export function computeNewTotal(
  bill: Bill,
  valor: number,
  addJurosMulta: boolean
): string | undefined {
  const resto = bill.amount_remaining ?? 0;
  if (bill.amount_is_estimated) {
    return valor === resto ? undefined : valor.toFixed(2);
  }
  if (valor > resto && addJurosMulta) {
    const total = bill.amount_total ?? 0;
    return (total + (valor - resto)).toFixed(2);
  }
  return undefined;
}

interface BillPayPopoverProps {
  bill: Bill;
}

/** "Pagar" popover on the row (S75) — data default today, amount empty = remainder. */
export function BillPayPopover({ bill }: BillPayPopoverProps) {
  const [open, setOpen] = useState(false);
  const [addJurosMulta, setAddJurosMulta] = useState(false);
  const [blockedMessage, setBlockedMessage] = useState<string | null>(null);
  const payBill = usePayBill();

  const form = useForm<PaymentFormValues>({
    resolver: zodResolver(paymentFormSchema),
    defaultValues: { amount: '', funded_from: 'caixa', payment_date: todayISO() },
  });

  if (bill.id === undefined) return null;
  const billId = bill.id;
  const resto = bill.amount_remaining ?? 0;
  const amountField = form.watch('amount');
  const valor = amountField && amountField !== '' ? Number(amountField) : undefined;
  const showJurosMultaOption = !bill.amount_is_estimated && valor !== undefined && valor > resto;

  function handleOpenChange(next: boolean) {
    setOpen(next);
    if (next) {
      form.reset({ amount: '', funded_from: 'caixa', payment_date: todayISO() });
      setAddJurosMulta(false);
      setBlockedMessage(null);
    }
  }

  function handleSubmit(values: PaymentFormValues) {
    setBlockedMessage(null);
    const amount = values.amount && values.amount !== '' ? Number(values.amount) : undefined;

    if (amount !== undefined && !bill.amount_is_estimated && amount > resto && !addJurosMulta) {
      setBlockedMessage(EXCEEDS_REMAINDER_MESSAGE);
      return;
    }

    const newTotal =
      amount !== undefined ? computeNewTotal(bill, amount, addJurosMulta) : undefined;

    payBill.mutate(
      {
        bill_id: billId,
        payment_date: values.payment_date,
        ...(amount !== undefined ? { amount } : {}),
        funded_from: values.funded_from,
        ...(newTotal !== undefined ? { new_total: newTotal } : {}),
      },
      {
        onSuccess: () => {
          toast.success('Pagamento registrado com sucesso');
          setOpen(false);
        },
        onError: (error) => {
          toast.error(getErrorMessage(error, 'Erro ao pagar conta'));
          handleError(error, 'Erro ao pagar conta');
        },
      }
    );
  }

  return (
    <Popover open={open} onOpenChange={handleOpenChange}>
      <PopoverTrigger asChild>
        <Button variant="outline" size="sm">
          <Wallet className="mr-2 h-4 w-4" />
          Pagar
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-80">
        <Form {...form}>
          <form onSubmit={form.handleSubmit(handleSubmit)} noValidate className="space-y-3">
            <FormField
              control={form.control}
              name="amount"
              render={({ field }) => (
                <FormItem>
                  <FormLabel htmlFor={`pay-amount-${String(billId)}`}>Valor (opcional)</FormLabel>
                  <FormControl>
                    <Input
                      id={`pay-amount-${String(billId)}`}
                      type="number"
                      min={0}
                      step="0.01"
                      placeholder="0,00"
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            {showJurosMultaOption && (
              <div className="flex items-start gap-2">
                <Checkbox
                  id={`pay-juros-multa-${String(billId)}`}
                  checked={addJurosMulta}
                  onCheckedChange={(checked) => {
                    setAddJurosMulta(checked === true);
                    setBlockedMessage(null);
                  }}
                />
                <Label
                  htmlFor={`pay-juros-multa-${String(billId)}`}
                  className="text-sm font-normal"
                >
                  Adicionar diferença como Juros/multa
                </Label>
              </div>
            )}

            {blockedMessage && <p className="text-sm text-destructive">{blockedMessage}</p>}

            <FormField
              control={form.control}
              name="funded_from"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Origem</FormLabel>
                  <Select value={field.value} onValueChange={field.onChange}>
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {fundedFromValues.map((value) => (
                        <SelectItem key={value} value={value}>
                          {FUNDED_FROM_LABELS[value]}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="payment_date"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Data</FormLabel>
                  <FormControl>
                    <Input type="date" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <div className="flex justify-end">
              <Button type="submit" size="sm" disabled={payBill.isPending}>
                {payBill.isPending ? 'Pagando...' : 'Confirmar pagamento'}
              </Button>
            </div>
          </form>
        </Form>
      </PopoverContent>
    </Popover>
  );
}
