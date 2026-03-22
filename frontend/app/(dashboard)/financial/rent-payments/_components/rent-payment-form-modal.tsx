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
  useCreateRentPayment,
  useUpdateRentPayment,
} from '@/lib/api/hooks/use-rent-payments';
import { useLeases } from '@/lib/api/hooks/use-leases';
import type { RentPayment } from '@/lib/schemas/rent-payment.schema';

interface Props {
  open: boolean;
  rentPayment?: RentPayment | null;
  onClose: () => void;
}

const rentPaymentFormSchema = z.object({
  lease_id: z.number().min(1, 'Selecione um contrato'),
  reference_month: z.string().min(1, 'Mês de referência é obrigatório'),
  amount_paid: z.number().min(0.01, 'Valor deve ser maior que zero'),
  payment_date: z.string().min(1, 'Data de pagamento é obrigatória'),
  notes: z.string(),
});

type RentPaymentFormValues = z.infer<typeof rentPaymentFormSchema>;

export function RentPaymentFormModal({ open, rentPayment, onClose }: Props) {
  const createMutation = useCreateRentPayment();
  const updateMutation = useUpdateRentPayment();
  const { data: leases, isLoading: leasesLoading } = useLeases();

  const form = useForm<RentPaymentFormValues>({
    resolver: zodResolver(rentPaymentFormSchema),
    defaultValues: {
      lease_id: undefined,
      reference_month: '',
      amount_paid: 0,
      payment_date: '',
      notes: '',
    },
  });

  useEffect(() => {
    if (rentPayment) {
      // reference_month comes as "2026-03-01", convert to "2026-03" for month input
      const monthValue = rentPayment.reference_month
        ? rentPayment.reference_month.substring(0, 7)
        : '';
      form.reset({
        lease_id: rentPayment.lease_id ?? rentPayment.lease?.id,
        reference_month: monthValue,
        amount_paid: rentPayment.amount_paid,
        payment_date: rentPayment.payment_date,
        notes: rentPayment.notes ?? '',
      });
    } else {
      form.reset({
        lease_id: undefined,
        reference_month: '',
        amount_paid: 0,
        payment_date: '',
        notes: '',
      });
    }
  }, [rentPayment, form]);

  const handleSubmit = async (values: RentPaymentFormValues) => {
    // Convert "2026-03" to "2026-03-01" for API
    const payload = {
      ...values,
      reference_month: values.reference_month + '-01',
    };

    try {
      if (rentPayment?.id) {
        await updateMutation.mutateAsync({ ...payload, id: rentPayment.id });
        toast.success('Pagamento atualizado com sucesso');
      } else {
        await createMutation.mutateAsync(payload);
        toast.success('Pagamento registrado com sucesso');
      }

      onClose();
      form.reset();
    } catch (error) {
      toast.error('Erro ao salvar pagamento');
      console.error('Save error:', error);
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
            {rentPayment ? 'Editar Pagamento' : 'Registrar Pagamento'}
          </DialogTitle>
        </DialogHeader>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-4">
            <FormField
              control={form.control}
              name="lease_id"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Contrato *</FormLabel>
                  <Select
                    disabled={leasesLoading}
                    onValueChange={(value) => field.onChange(Number(value))}
                    value={field.value ? String(field.value) : undefined}
                  >
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue placeholder="Selecione o contrato" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {leases?.map((lease) => (
                        <SelectItem key={lease.id} value={String(lease.id)}>
                          {`Apt ${lease.apartment?.number ?? '?'} - ${lease.apartment?.building?.name ?? '?'} (${lease.responsible_tenant?.name ?? '?'})`}
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
              name="amount_paid"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Valor Pago *</FormLabel>
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
                {rentPayment ? 'Atualizar' : 'Registrar'}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
