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
import { Textarea } from '@/components/ui/textarea';
import { toast } from 'sonner';
import { useDepositReserve } from '@/lib/api/hooks/use-reserves';
import { getErrorMessage, handleError } from '@/lib/utils/error-handler';
import type { Reserve } from '@/lib/schemas/finances/reserve.schema';

const depositFormSchema = z.object({
  amount: z.number().min(0.01, 'Valor deve ser maior que zero'),
  movement_date: z.string().optional(),
  reference: z.string().optional(),
  notes: z.string().optional(),
});

type DepositFormValues = z.infer<typeof depositFormSchema>;

interface Props {
  open: boolean;
  reserve: Reserve | null;
  onClose: () => void;
}

export function DepositDialog({ open, reserve, onClose }: Props) {
  const depositMutation = useDepositReserve();

  const form = useForm<DepositFormValues>({
    resolver: zodResolver(depositFormSchema),
    defaultValues: { amount: 0, movement_date: '', reference: '', notes: '' },
  });

  useEffect(() => {
    if (open) {
      form.reset({ amount: 0, movement_date: '', reference: '', notes: '' });
    }
  }, [open, form]);

  const onSubmit = async (values: DepositFormValues) => {
    if (!reserve?.id) return;
    try {
      await depositMutation.mutateAsync({
        reserveId: reserve.id,
        payload: {
          amount: values.amount,
          movement_date: values.movement_date ?? undefined,
          reference: values.reference ?? undefined,
          notes: values.notes ?? undefined,
        },
      });
      toast.success('Depósito realizado com sucesso');
      onClose();
    } catch (error) {
      toast.error(getErrorMessage(error, 'Erro ao realizar depósito'));
      handleError(error, 'DepositDialog.onSubmit');
    }
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Depositar em {reserve?.name ?? 'Reserva'}</DialogTitle>
          <DialogDescription>
            Informe o valor e a data para registrar o depósito na reserva.
          </DialogDescription>
        </DialogHeader>

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

            <FormField
              control={form.control}
              name="reference"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Referência (opcional)</FormLabel>
                  <FormControl>
                    <Input placeholder="Ex: Transferência bancária" {...field} value={field.value ?? ''} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="notes"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Observações (opcional)</FormLabel>
                  <FormControl>
                    <Textarea rows={2} {...field} value={field.value ?? ''} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <DialogFooter>
              <Button type="button" variant="outline" onClick={onClose}>
                Cancelar
              </Button>
              <Button type="submit" disabled={depositMutation.isPending}>
                {depositMutation.isPending ? 'Depositando...' : 'Depositar'}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
