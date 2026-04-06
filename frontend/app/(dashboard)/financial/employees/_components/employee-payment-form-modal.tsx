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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { toast } from 'sonner';
import { useCreateEmployeePayment, useUpdateEmployeePayment } from '@/lib/api/hooks/use-employee-payments';
import { usePersons } from '@/lib/api/hooks/use-persons';
import { type EmployeePayment } from '@/lib/schemas/employee-payment.schema';
import { formatCurrency } from '@/lib/utils/formatters';
import { handleError } from '@/lib/utils/error-handler';

interface Props {
  open: boolean;
  payment?: EmployeePayment | null;
  onClose: () => void;
}

const employeePaymentFormSchema = z.object({
  person_id: z.number().min(1, 'Selecione um funcionário'),
  reference_month: z.string().min(1, 'Mês de referência é obrigatório'),
  base_salary: z.number().min(0, 'Salário base deve ser zero ou maior'),
  variable_amount: z.number(),
  rent_offset: z.number(),
  cleaning_count: z.number().int().min(0),
  notes: z.string(),
});

type EmployeePaymentFormValues = z.infer<typeof employeePaymentFormSchema>;

function toMonthInput(dateStr: string): string {
  // "2026-03-01" -> "2026-03"
  return dateStr.slice(0, 7);
}

export function EmployeePaymentFormModal({ open, payment, onClose }: Props) {
  const createMutation = useCreateEmployeePayment();
  const updateMutation = useUpdateEmployeePayment();
  const { data: persons } = usePersons();

  const employees = persons?.filter((p) => p.is_employee) ?? [];

  const form = useForm<EmployeePaymentFormValues>({
    resolver: zodResolver(employeePaymentFormSchema),
    defaultValues: {
      person_id: undefined,
      reference_month: '',
      base_salary: 0,
      variable_amount: 0,
      rent_offset: 0,
      cleaning_count: 0,
      notes: '',
    },
  });

  const watchedBaseSalary = form.watch('base_salary');
  const watchedVariable = form.watch('variable_amount');

  useEffect(() => {
    if (payment) {
      form.reset({
        person_id: payment.person_id ?? payment.person?.id,
        reference_month: toMonthInput(payment.reference_month),
        base_salary: payment.base_salary,
        variable_amount: payment.variable_amount,
        rent_offset: payment.rent_offset,
        cleaning_count: payment.cleaning_count,
        notes: payment.notes ?? '',
      });
    } else {
      form.reset({
        person_id: undefined,
        reference_month: '',
        base_salary: 0,
        variable_amount: 0,
        rent_offset: 0,
        cleaning_count: 0,
        notes: '',
      });
    }
  }, [payment, form]);

  const handleSubmit = async (values: EmployeePaymentFormValues) => {
    const submissionData = {
      ...values,
      reference_month: values.reference_month + '-01',
    };

    try {
      if (payment?.id) {
        await updateMutation.mutateAsync({ ...submissionData, id: payment.id });
        toast.success('Pagamento atualizado com sucesso');
      } else {
        await createMutation.mutateAsync({ ...submissionData, is_paid: false });
        toast.success('Pagamento criado com sucesso');
      }

      onClose();
      form.reset();
    } catch (error) {
      toast.error('Erro ao salvar pagamento');
      handleError(error, 'EmployeePaymentFormModal.onSubmit');
    }
  };

  const handleClose = () => {
    onClose();
    form.reset();
  };

  const isLoading = createMutation.isPending || updateMutation.isPending;
  const totalAmount = (watchedBaseSalary ?? 0) + (watchedVariable ?? 0);

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{payment ? 'Editar Pagamento' : 'Novo Pagamento de Funcionário'}</DialogTitle>
        </DialogHeader>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-4">
            <FormField
              control={form.control}
              name="person_id"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Funcionário *</FormLabel>
                  <Select
                    value={field.value ? String(field.value) : 'none'}
                    onValueChange={(value) => field.onChange(value === 'none' ? undefined : Number(value))}
                  >
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue placeholder="Selecione o funcionário" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      <SelectItem value="none">Selecione</SelectItem>
                      {employees.map((p) => (
                        <SelectItem key={p.id} value={String(p.id)}>
                          {p.name}
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
              name="reference_month"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Mês de Referência *</FormLabel>
                  <FormControl>
                    <Input type="month" {...field} disabled={isLoading} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <div className="grid grid-cols-2 gap-4">
              <FormField
                control={form.control}
                name="base_salary"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Salário Base *</FormLabel>
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
                          disabled={isLoading}
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
                    <FormLabel>Valor Variável</FormLabel>
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
                          disabled={isLoading}
                        />
                      </div>
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="rent_offset"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Compensação Aluguel</FormLabel>
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
                          disabled={isLoading}
                        />
                      </div>
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="cleaning_count"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Faxinas</FormLabel>
                    <FormControl>
                      <Input
                        type="number"
                        min={0}
                        step="1"
                        placeholder="0"
                        {...field}
                        onChange={(e) => field.onChange(Number(e.target.value))}
                        disabled={isLoading}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            <div className="rounded-md border p-3 bg-muted/50">
              <p className="text-sm font-bold">
                Total: {formatCurrency(totalAmount)}
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                Salário Base + Valor Variável (compensação de aluguel é informativa)
              </p>
            </div>

            <FormField
              control={form.control}
              name="notes"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Observações (opcional)</FormLabel>
                  <FormControl>
                    <Textarea placeholder="Notas adicionais..." rows={3} {...field} disabled={isLoading} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <DialogFooter>
              <Button type="button" variant="outline" onClick={handleClose} disabled={isLoading}>
                Cancelar
              </Button>
              <Button type="submit" disabled={isLoading}>
                {payment ? 'Atualizar' : 'Criar'}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
