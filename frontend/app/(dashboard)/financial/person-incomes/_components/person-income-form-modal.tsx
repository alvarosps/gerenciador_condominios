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
import { Switch } from '@/components/ui/switch';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { toast } from 'sonner';
import {
  useCreatePersonIncome,
  useUpdatePersonIncome,
} from '@/lib/api/hooks/use-person-incomes';
import { usePersons } from '@/lib/api/hooks/use-persons';
import { useApartments } from '@/lib/api/hooks/use-apartments';
import { useLeases } from '@/lib/api/hooks/use-leases';
import type { PersonIncome } from '@/lib/schemas/person-income.schema';
import { formatCurrency } from '@/lib/utils/formatters';
import { handleError } from '@/lib/utils/error-handler';

interface Props {
  open: boolean;
  personIncome?: PersonIncome | null;
  onClose: () => void;
}

const personIncomeFormSchema = z.object({
  person_id: z.number().min(1, 'Selecione uma pessoa'),
  income_type: z.string().min(1, 'Selecione o tipo'),
  apartment_id: z.number().nullable(),
  fixed_amount: z.number().nullable(),
  start_date: z.string().min(1, 'Data de início é obrigatória'),
  end_date: z.string(),
  is_active: z.boolean(),
  notes: z.string(),
});

type PersonIncomeFormValues = z.infer<typeof personIncomeFormSchema>;

function getTodayISO(): string {
  return new Date().toISOString().split('T')[0] ?? '';
}

export function PersonIncomeFormModal({ open, personIncome, onClose }: Props) {
  const createMutation = useCreatePersonIncome();
  const updateMutation = useUpdatePersonIncome();

  const { data: persons, isLoading: personsLoading } = usePersons();
  const { data: apartments, isLoading: apartmentsLoading } = useApartments();
  const { data: leases } = useLeases();

  const form = useForm<PersonIncomeFormValues>({
    resolver: zodResolver(personIncomeFormSchema),
    defaultValues: {
      person_id: 0,
      income_type: 'fixed_stipend',
      apartment_id: null,
      fixed_amount: null,
      start_date: getTodayISO(),
      end_date: '',
      is_active: true,
      notes: '',
    },
  });

  const watchedIncomeType = form.watch('income_type');
  const watchedApartmentId = form.watch('apartment_id');

  const activeLeaseForApartment = leases?.find(
    (l) => l.apartment?.id === watchedApartmentId,
  );

  useEffect(() => {
    if (personIncome) {
      form.reset({
        person_id: personIncome.person_id ?? personIncome.person?.id ?? 0,
        income_type: personIncome.income_type,
        apartment_id: personIncome.apartment_id ?? personIncome.apartment?.id ?? null,
        fixed_amount: personIncome.fixed_amount ?? null,
        start_date: personIncome.start_date,
        end_date: personIncome.end_date ?? '',
        is_active: personIncome.is_active,
        notes: personIncome.notes ?? '',
      });
    } else {
      form.reset({
        person_id: 0,
        income_type: 'fixed_stipend',
        apartment_id: null,
        fixed_amount: null,
        start_date: getTodayISO(),
        end_date: '',
        is_active: true,
        notes: '',
      });
    }
  }, [personIncome, form]);

  const handleSubmit = async (values: PersonIncomeFormValues) => {
    const payload: Record<string, unknown> = {
      person_id: values.person_id,
      income_type: values.income_type,
      start_date: values.start_date,
      end_date: values.end_date || null,
      is_active: values.is_active,
      notes: values.notes,
    };

    if (values.income_type === 'apartment_rent') {
      payload.apartment_id = values.apartment_id;
      payload.fixed_amount = null;
    } else {
      payload.apartment_id = null;
      payload.fixed_amount = values.fixed_amount;
    }

    try {
      if (personIncome?.id) {
        await updateMutation.mutateAsync({ ...payload, id: personIncome.id } as PersonIncome & { id: number });
        toast.success('Rendimento atualizado com sucesso');
      } else {
        await createMutation.mutateAsync(payload as Omit<PersonIncome, 'id' | 'person' | 'apartment' | 'current_value'>);
        toast.success('Rendimento criado com sucesso');
      }

      onClose();
      form.reset();
    } catch (error) {
      toast.error('Erro ao salvar rendimento');
      handleError(error, 'PersonIncomeFormModal.onSubmit');
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
            {personIncome ? 'Editar Rendimento' : 'Novo Rendimento'}
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
                      {persons?.map((person) => (
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
              name="income_type"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Tipo *</FormLabel>
                  <Select
                    onValueChange={field.onChange}
                    value={field.value}
                  >
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue placeholder="Selecione o tipo" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      <SelectItem value="apartment_rent">Aluguel Apartamento</SelectItem>
                      <SelectItem value="fixed_stipend">Estipêndio Fixo</SelectItem>
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />

            {watchedIncomeType === 'apartment_rent' && (
              <>
                <FormField
                  control={form.control}
                  name="apartment_id"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Apartamento *</FormLabel>
                      <Select
                        disabled={apartmentsLoading}
                        onValueChange={(value) => field.onChange(Number(value))}
                        value={field.value ? String(field.value) : undefined}
                      >
                        <FormControl>
                          <SelectTrigger>
                            <SelectValue placeholder="Selecione o apartamento" />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          {apartments?.map((apt) => (
                            <SelectItem key={apt.id} value={String(apt.id)}>
                              Apto {apt.number} - {apt.building?.name ?? apt.building?.street_number ?? ''}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                {activeLeaseForApartment && (
                  <div className="rounded-md bg-muted p-3 text-sm">
                    <span className="font-medium">Valor atual do lease:</span>{' '}
                    {formatCurrency(activeLeaseForApartment.apartment?.rental_value ?? 0)}
                  </div>
                )}
                {watchedApartmentId && !activeLeaseForApartment && (
                  <div className="rounded-md bg-warning/10 p-3 text-sm text-warning">
                    Nenhum lease ativo encontrado para este apartamento
                  </div>
                )}
              </>
            )}

            {watchedIncomeType === 'fixed_stipend' && (
              <FormField
                control={form.control}
                name="fixed_amount"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Valor Fixo *</FormLabel>
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
                          value={field.value ?? ''}
                          onChange={(e) =>
                            field.onChange(e.target.value ? Number(e.target.value) : null)
                          }
                        />
                      </div>
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            )}

            <div className="grid grid-cols-2 gap-4">
              <FormField
                control={form.control}
                name="start_date"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Data Início *</FormLabel>
                    <FormControl>
                      <Input type="date" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="end_date"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Data Fim (opcional)</FormLabel>
                    <FormControl>
                      <Input type="date" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            <FormField
              control={form.control}
              name="is_active"
              render={({ field }) => (
                <FormItem className="flex items-center justify-between rounded-md border p-3">
                  <FormLabel>Ativo</FormLabel>
                  <FormControl>
                    <Switch checked={field.value} onCheckedChange={field.onChange} />
                  </FormControl>
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
                {personIncome ? 'Atualizar' : 'Criar'}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
