'use client';

import { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { toast } from 'sonner';
import { useWithdrawReserve } from '@/lib/api/hooks/use-reserves';
import { getErrorMessage, handleError } from '@/lib/utils/error-handler';
import { formatCurrency } from '@/lib/utils/formatters';
import type { Reserve } from '@/lib/schemas/finances/reserve.schema';

const withdrawFormSchema = z.object({
  amount: z.number().min(0.01, 'Valor deve ser maior que zero'),
  movement_date: z.string().optional(),
});

type WithdrawFormValues = z.infer<typeof withdrawFormSchema>;

interface Props {
  open: boolean;
  reserve: Reserve | null;
  onClose: () => void;
}

export function WithdrawDialog({ open, reserve, onClose }: Props) {
  const withdrawMutation = useWithdrawReserve();

  const form = useForm<WithdrawFormValues>({
    resolver: zodResolver(withdrawFormSchema),
    defaultValues: { amount: 0, movement_date: '' },
  });

  useEffect(() => {
    if (open) {
      form.reset({ amount: 0, movement_date: '' });
    }
  }, [open, form]);

  const onSubmit = async (values: WithdrawFormValues) => {
    if (!reserve?.id) return;
    try {
      await withdrawMutation.mutateAsync({
        reserveId: reserve.id,
        payload: {
          amount: values.amount,
          movement_date: values.movement_date ?? undefined,
        },
      });
      toast.success('Saque realizado com sucesso');
      onClose();
    } catch (error) {
      toast.error(getErrorMessage(error, 'Erro ao realizar saque'));
      handleError(error, 'WithdrawDialog.onSubmit');
    }
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Sacar de {reserve?.name ?? 'Reserva'}</DialogTitle>
          <DialogDescription>
            Informe o valor para retirar da reserva. O saldo não pode ficar negativo.
          </DialogDescription>
        </DialogHeader>

        {reserve && (
          <p className="text-sm text-muted-foreground">
            Saldo disponível: <span className="font-medium">{formatCurrency(reserve.balance)}</span>
          </p>
        )}

        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <FormField
              control={form.control}
              name="amount"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Valor (R$) *</FormLabel>
                  <FormControl>
                    <div className="relative">
                      <span className="absolute left-3 top-1/2 -translate-y-1/2 text-sm text-muted-foreground">
                        R$
                      </span>
                      <Input
                        type="number"
                        min={0}
                        step="0.01"
                        placeholder="0.00"
                        className="pl-10"
                        {...field}
                        onChange={(e) => field.onChange(Number(e.target.value))}
                      />
                    </div>
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="movement_date"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Data do movimento</FormLabel>
                  <FormControl>
                    <Input type="date" {...field} value={field.value ?? ''} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <DialogFooter>
              <Button type="button" variant="outline" onClick={onClose}>
                Cancelar
              </Button>
              <Button type="submit" variant="destructive" disabled={withdrawMutation.isPending}>
                {withdrawMutation.isPending ? 'Sacando...' : 'Sacar'}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
