'use client';

import { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
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
import { apiClient } from '@/lib/api/client';

const formSchema = z.object({
  base_salary: z.number().min(0, 'Salário base deve ser >= 0'),
  variable_amount: z.number().min(0, 'Valor variável deve ser >= 0'),
  notes: z.string(),
});

type FormValues = z.infer<typeof formSchema>;

interface EmployeePaymentData {
  employee_payment_id: number;
  person_name: string;
  base_salary: number;
  variable_amount: number;
  notes: string;
}

interface Props {
  payment: EmployeePaymentData;
  onClose: () => void;
  onSaved: () => void;
}

export function EmployeePaymentModal({ payment, onClose, onSaved }: Props) {
  const [isSaving, setIsSaving] = useState(false);

  const form = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      base_salary: payment.base_salary,
      variable_amount: payment.variable_amount,
      notes: payment.notes ?? '',
    },
  });

  useEffect(() => {
    form.reset({
      base_salary: payment.base_salary,
      variable_amount: payment.variable_amount,
      notes: payment.notes ?? '',
    });
  }, [payment, form]);

  const watchedBase = form.watch('base_salary');
  const watchedVariable = form.watch('variable_amount');
  const total = (watchedBase ?? 0) + (watchedVariable ?? 0);

  const handleSubmit = async (values: FormValues) => {
    setIsSaving(true);
    try {
      await apiClient.patch(`/employee-payments/${payment.employee_payment_id}/`, {
        base_salary: values.base_salary,
        variable_amount: values.variable_amount,
        notes: values.notes,
      });
      toast.success('Pagamento atualizado com sucesso');
      onSaved();
      onClose();
    } catch {
      toast.error('Erro ao salvar pagamento');
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <Dialog open onOpenChange={(open) => { if (!open) onClose(); }}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Editar Pagamento — {payment.person_name}</DialogTitle>
        </DialogHeader>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-4">
            <FormField
              control={form.control}
              name="base_salary"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Salário Base</FormLabel>
                  <FormControl>
                    <div className="relative">
                      <span className="absolute left-3 top-1/2 -translate-y-1/2 text-sm text-muted-foreground">
                        R$
                      </span>
                      <Input
                        type="number"
                        min={0}
                        step="0.01"
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
              name="variable_amount"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Valor Variável (extras do mês)</FormLabel>
                  <FormControl>
                    <div className="relative">
                      <span className="absolute left-3 top-1/2 -translate-y-1/2 text-sm text-muted-foreground">
                        R$
                      </span>
                      <Input
                        type="number"
                        min={0}
                        step="0.01"
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

            <div className="rounded-md bg-muted/30 p-3 text-sm">
              <span className="text-muted-foreground">Total: </span>
              <span className="font-semibold">
                R$ {total.toFixed(2).replace('.', ',')}
              </span>
            </div>

            <FormField
              control={form.control}
              name="notes"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Observações (opcional)</FormLabel>
                  <FormControl>
                    <Textarea placeholder="Extras, limpezas, etc..." rows={3} {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <DialogFooter>
              <Button type="button" variant="outline" onClick={onClose}>
                Cancelar
              </Button>
              <Button type="submit" disabled={isSaving}>
                {isSaving ? 'Salvando...' : 'Salvar'}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
