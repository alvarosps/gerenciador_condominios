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
import {
  useCreatePersonPayment,
  useUpdatePersonPayment,
} from '@/lib/api/hooks/use-person-payments';
import { usePersons } from '@/lib/api/hooks/use-persons';
import type { PersonPayment } from '@/lib/schemas/person-payment.schema';
import { handleError } from '@/lib/utils/error-handler';

interface Props {
  open: boolean;
  personPayment?: PersonPayment | null;
  onClose: () => void;
  defaultPersonId?: number;
  defaultReferenceMonth?: string;
}

const personPaymentFormSchema = z.object({
  person_id: z.number().min(1, 'Selecione uma pessoa'),
  reference_month: z.string().min(1, 'Mês de referência é obrigatório'),
  amount: z.number().min(0.01, 'Valor deve ser maior que zero'),
  payment_date: z.string().min(1, 'Data de pagamento é obrigatória'),
  notes: z.string(),
});

type PersonPaymentFormValues = z.infer<typeof personPaymentFormSchema>;

function getTodayISO(): string {
  return new Date().toISOString().split('T')[0] ?? '';
}

function getCurrentMonth(): string {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  return `${year}-${month}`;
}

export function PersonPaymentFormModal({
  open,
  personPayment,
  onClose,
  defaultPersonId,
  defaultReferenceMonth,
}: Props) {
  const createMutation = useCreatePersonPayment();
  const updateMutation = useUpdatePersonPayment();
  const { data: persons, isLoading: personsLoading } = usePersons();

  const form = useForm<PersonPaymentFormValues>({
    resolver: zodResolver(personPaymentFormSchema),
    defaultValues: {
      person_id: defaultPersonId ?? 0,
      reference_month: defaultReferenceMonth ?? getCurrentMonth(),
      amount: 0,
      payment_date: getTodayISO(),
      notes: '',
    },
  });

  useEffect(() => {
    if (personPayment) {
      const monthValue = personPayment.reference_month
        ? personPayment.reference_month.substring(0, 7)
        : '';
      form.reset({
        person_id: personPayment.person_id ?? personPayment.person?.id ?? 0,
        reference_month: monthValue,
        amount: personPayment.amount,
        payment_date: personPayment.payment_date,
        notes: personPayment.notes ?? '',
      });
    } else {
      form.reset({
        person_id: defaultPersonId ?? 0,
        reference_month: defaultReferenceMonth ?? getCurrentMonth(),
        amount: 0,
        payment_date: getTodayISO(),
        notes: '',
      });
    }
  }, [personPayment, form, defaultPersonId, defaultReferenceMonth]);

  const handleSubmit = async (values: PersonPaymentFormValues) => {
    const payload = {
      ...values,
      reference_month: values.reference_month + '-01',
    };

    try {
      if (personPayment?.id) {
        await updateMutation.mutateAsync({ ...payload, id: personPayment.id });
        toast.success('Pagamento atualizado com sucesso');
      } else {
        await createMutation.mutateAsync(payload);
        toast.success('Pagamento registrado com sucesso');
      }

      onClose();
      form.reset();
    } catch (error) {
      toast.error('Erro ao salvar pagamento');
      handleError(error, 'PersonPaymentFormModal.onSubmit');
    }
  };

  const handleClose = () => {
    onClose();
    form.reset();
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>
            {personPayment ? 'Editar Pagamento' : 'Registrar Pagamento'}
          </DialogTitle>
        </DialogHeader>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-4">
            <FormField
              control={form.control}
              name="person_id"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Pessoa *</FormLabel>
                  <Select
                    disabled={personsLoading}
                    onValueChange={(value) => field.onChange(Number(value))}
                    value={field.value ? String(field.value) : undefined}
                  >
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue placeholder="Selecione a pessoa" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {persons
                        ?.filter((p) => !p.is_employee)
                        .map((person) => (
                          <SelectItem key={person.id} value={String(person.id)}>
                            {person.name} ({person.relationship})
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
                    <Input type="month" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="amount"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Valor *</FormLabel>
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
              name="payment_date"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Data de Pagamento *</FormLabel>
                  <FormControl>
                    <Input type="date" {...field} />
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
                    <Textarea placeholder="Notas adicionais..." rows={3} {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <DialogFooter>
              <Button type="button" variant="outline" onClick={handleClose}>
                Cancelar
              </Button>
              <Button
                type="submit"
                disabled={createMutation.isPending || updateMutation.isPending}
              >
                {personPayment ? 'Atualizar' : 'Registrar'}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
