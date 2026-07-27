'use client';

import { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Info } from 'lucide-react';
import { toast } from 'sonner';
import { useRouter } from 'next/navigation';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { usePayBill } from '@/lib/api/hooks/use-bills';
import { showFinanceMutationError } from '@/lib/utils/error-handler';
import { formatCurrency } from '@/lib/utils/formatters';
import { ROUTES } from '@/lib/utils/constants';
import {
  DIALOG_FUNDED_FROM_VALUES,
  FUNDED_FROM_LABELS,
  type PaymentFormValues,
  paymentFormSchema,
  todayISO,
} from './bill-payment-form';

interface BillPaymentDialogProps {
  open: boolean;
  billId: number | null;
  /** Remaining amount of the bill, for the "pay total" hint (display only). */
  amountRemaining?: number;
  description?: string;
  onClose: () => void;
}

export function BillPaymentDialog({
  open,
  billId,
  amountRemaining,
  description,
  onClose,
}: BillPaymentDialogProps) {
  const payBill = usePayBill();
  const router = useRouter();

  const form = useForm<PaymentFormValues>({
    resolver: zodResolver(paymentFormSchema),
    defaultValues: {
      amount: '',
      funded_from: 'caixa',
      paid_by_person_id: 0,
      payment_date: todayISO(),
    },
  });

  useEffect(() => {
    if (open) {
      form.reset({
        amount: '',
        funded_from: 'caixa',
        paid_by_person_id: 0,
        payment_date: todayISO(),
      });
    }
  }, [open, billId, form]);

  const fundedFrom = form.watch('funded_from');

  function handleSubmit(values: PaymentFormValues) {
    if (billId === null) return;
    const amount = values.amount && values.amount !== '' ? Number(values.amount) : undefined;
    payBill.mutate(
      {
        bill_id: billId,
        payment_date: values.payment_date,
        ...(amount !== undefined ? { amount } : {}),
        funded_from: values.funded_from,
      },
      {
        onSuccess: () => {
          toast.success('Pagamento registrado com sucesso');
          onClose();
        },
        onError: (error) => {
          showFinanceMutationError(error, 'Erro ao pagar conta', () =>
            router.push(ROUTES.FINANCES_MONTH_CLOSE)
          );
        },
      }
    );
  }

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Pagar conta{description ? ` — ${description}` : ''}</DialogTitle>
          <DialogDescription>
            Informe o valor, a origem do pagamento e a data para registrar o pagamento desta conta.
          </DialogDescription>
        </DialogHeader>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(handleSubmit)} noValidate className="space-y-4">
            <FormField
              control={form.control}
              name="amount"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Valor (opcional)</FormLabel>
                  <FormControl>
                    <div className="relative">
                      <span className="absolute left-3 top-1/2 -translate-y-1/2 text-sm text-muted-foreground">
                        R$
                      </span>
                      <Input
                        type="number"
                        min={0}
                        step="0.01"
                        placeholder="0,00"
                        className="pl-10"
                        {...field}
                      />
                    </div>
                  </FormControl>
                  <FormDescription>
                    {amountRemaining !== undefined
                      ? `Deixe em branco para pagar o total restante (${formatCurrency(amountRemaining)}).`
                      : 'Deixe em branco para pagar o total restante.'}
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="funded_from"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Origem do pagamento</FormLabel>
                  <Select value={field.value} onValueChange={field.onChange}>
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {DIALOG_FUNDED_FROM_VALUES.map((value) => (
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

            {fundedFrom === 'reserve' && (
              <Alert>
                <Info className="h-4 w-4" />
                <AlertDescription>
                  Pagamento sairá da reserva. O saldo é validado no servidor.
                </AlertDescription>
              </Alert>
            )}

            <FormField
              control={form.control}
              name="payment_date"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Data do pagamento</FormLabel>
                  <FormControl>
                    <Input type="date" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <DialogFooter>
              <Button type="button" variant="outline" onClick={onClose}>
                Cancelar
              </Button>
              <Button type="submit" disabled={payBill.isPending}>
                {payBill.isPending ? 'Pagando...' : 'Pagar'}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
