'use client';

import { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import {
  Dialog,
  DialogBody,
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
import { Switch } from '@/components/ui/switch';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { toast } from 'sonner';
import { useCreateIncomeEntry, useUpdateIncomeEntry } from '@/lib/api/hooks/use-income-entries';
import { useBuildings } from '@/lib/api/hooks/use-buildings';
import { useFinanceCategories } from '@/lib/api/hooks/use-finance-categories';
import { getErrorMessage, handleError } from '@/lib/utils/error-handler';
import type { IncomeEntry } from '@/lib/schemas/finances/income-entry.schema';

const incomeEntryFormSchema = z
  .object({
    description: z.string().min(1, 'Descrição é obrigatória'),
    amount: z.number().min(0.01, 'Valor deve ser maior que zero'),
    income_date: z.string().min(1, 'Data é obrigatória'),
    is_received: z.boolean(),
    received_date: z.string().nullable().optional(),
    building_id: z.number().nullable().optional(),
    category_id: z.number().nullable().optional(),
    notes: z.string(),
  })
  .refine(
    (data) => {
      if (data.is_received && !data.received_date) return false;
      return true;
    },
    {
      message: 'Data de recebimento é obrigatória quando marcado como recebido',
      path: ['received_date'],
    }
  );

type IncomeEntryFormValues = z.infer<typeof incomeEntryFormSchema>;

interface Props {
  open: boolean;
  entry?: IncomeEntry | null;
  onClose: () => void;
}

export function IncomeEntryFormModal({ open, entry, onClose }: Props) {
  const createMutation = useCreateIncomeEntry();
  const updateMutation = useUpdateIncomeEntry();
  const { data: buildings } = useBuildings();
  const { data: categories } = useFinanceCategories();

  const form = useForm<IncomeEntryFormValues>({
    resolver: zodResolver(incomeEntryFormSchema),
    defaultValues: {
      description: '',
      amount: 0,
      income_date: '',
      is_received: false,
      received_date: null,
      building_id: null,
      category_id: null,
      notes: '',
    },
  });

  const watchedIsReceived = form.watch('is_received');

  useEffect(() => {
    if (entry) {
      form.reset({
        description: entry.description,
        amount: entry.amount,
        income_date: entry.income_date,
        is_received: entry.is_received,
        received_date: entry.received_date ?? null,
        building_id: entry.building?.id ?? null,
        category_id: entry.category?.id ?? null,
        notes: entry.notes ?? '',
      });
    } else {
      form.reset({
        description: '',
        amount: 0,
        income_date: '',
        is_received: false,
        received_date: null,
        building_id: null,
        category_id: null,
        notes: '',
      });
    }
  }, [entry, open, form]);

  // Clear received_date when is_received toggled off
  useEffect(() => {
    if (!watchedIsReceived) {
      form.setValue('received_date', null);
    }
  }, [watchedIsReceived, form]);

  const onSubmit = async (values: IncomeEntryFormValues) => {
    try {
      if (entry?.id !== undefined) {
        await updateMutation.mutateAsync({ ...values, id: entry.id });
        toast.success('Receita atualizada com sucesso');
      } else {
        await createMutation.mutateAsync(values);
        toast.success('Receita criada com sucesso');
      }
      onClose();
      form.reset();
    } catch (error) {
      toast.error(getErrorMessage(error, 'Erro ao salvar receita'));
      handleError(error, 'IncomeEntryFormModal.onSubmit');
    }
  };

  const handleClose = () => {
    onClose();
    form.reset();
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-lg max-h-[90vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>{entry ? 'Editar Receita' : 'Nova Receita'}</DialogTitle>
          <DialogDescription>
            {entry
              ? 'Atualize os dados da receita do condomínio.'
              : 'Registre uma nova receita para o condomínio.'}
          </DialogDescription>
        </DialogHeader>

        <Form {...form}>
          <form
            onSubmit={form.handleSubmit(onSubmit)}
            className="flex flex-1 flex-col overflow-hidden"
          >
            <DialogBody className="space-y-4 pr-1">
              <FormField
                control={form.control}
                name="description"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Descrição *</FormLabel>
                    <FormControl>
                      <Input placeholder="Descrição da receita" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <div className="grid grid-cols-2 gap-4">
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
                  name="income_date"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Data *</FormLabel>
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
                name="building_id"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Prédio (opcional)</FormLabel>
                    <Select
                      value={field.value ? String(field.value) : 'none'}
                      onValueChange={(val) => field.onChange(val === 'none' ? null : Number(val))}
                    >
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue placeholder="Condomínio (geral)" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        <SelectItem value="none">Condomínio (geral)</SelectItem>
                        {buildings?.map((b) => (
                          <SelectItem key={b.id} value={String(b.id)}>
                            {b.name}
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
                name="category_id"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Categoria (opcional)</FormLabel>
                    <Select
                      value={field.value ? String(field.value) : 'none'}
                      onValueChange={(val) => field.onChange(val === 'none' ? null : Number(val))}
                    >
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue placeholder="Sem categoria" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        <SelectItem value="none">Sem categoria</SelectItem>
                        {categories?.map((c) => (
                          <SelectItem key={c.id} value={String(c.id)}>
                            {c.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <div className="rounded-md border p-4 space-y-3">
                <FormField
                  control={form.control}
                  name="is_received"
                  render={({ field }) => (
                    <FormItem className="flex items-center justify-between">
                      <FormLabel>Recebido?</FormLabel>
                      <FormControl>
                        <Switch checked={field.value} onCheckedChange={field.onChange} />
                      </FormControl>
                    </FormItem>
                  )}
                />

                {watchedIsReceived && (
                  <FormField
                    control={form.control}
                    name="received_date"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Data de recebimento *</FormLabel>
                        <FormControl>
                          <Input
                            type="date"
                            value={field.value ?? ''}
                            onChange={(e) => field.onChange(e.target.value || null)}
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                )}
              </div>

              <FormField
                control={form.control}
                name="notes"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Observações</FormLabel>
                    <FormControl>
                      <Textarea rows={2} placeholder="Notas adicionais..." {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </DialogBody>

            <DialogFooter className="pt-4">
              <Button type="button" variant="outline" onClick={handleClose}>
                Cancelar
              </Button>
              <Button type="submit" disabled={createMutation.isPending || updateMutation.isPending}>
                {entry ? 'Atualizar' : 'Criar'}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
