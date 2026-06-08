'use client';

import { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { toast } from 'sonner';
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
import { Switch } from '@/components/ui/switch';
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  useCreateInstallmentPlan,
  useUpdateInstallmentPlan,
} from '@/lib/api/hooks/use-installment-plans';
import { useBuildings } from '@/lib/api/hooks/use-buildings';
import { useFinanceCategories } from '@/lib/api/hooks/use-finance-categories';
import { useBillingAccounts } from '@/lib/api/hooks/use-billing-accounts';
import { handleError } from '@/lib/utils/error-handler';
import type { InstallmentPlan } from '@/lib/schemas/finances/installment-plan.schema';
import {
  installmentPlanFormSchema,
  type InstallmentPlanFormValues,
} from './installment-plan-form-schema';

const NONE = 'none';

function emptyDefaults(): InstallmentPlanFormValues {
  return {
    description: '',
    category_id: null,
    building_id: null,
    total_amount: 0,
    installment_count: 1,
    start_due_date: '',
    default_due_day: 10,
    embedded: false,
    linked_billing_account_id: null,
    notes: '',
  };
}

function planToDefaults(plan: InstallmentPlan): InstallmentPlanFormValues {
  return {
    description: plan.description,
    category_id: plan.category_id ?? plan.category?.id ?? null,
    building_id: plan.building_id ?? plan.building?.id ?? null,
    total_amount: plan.total_amount,
    installment_count: plan.installment_count,
    start_due_date: plan.start_due_date,
    default_due_day: plan.default_due_day,
    embedded: plan.embedded,
    linked_billing_account_id:
      plan.linked_billing_account_id ?? plan.linked_billing_account?.id ?? null,
    notes: plan.notes ?? '',
  };
}

interface InstallmentPlanFormModalProps {
  open: boolean;
  plan?: InstallmentPlan | null;
  onClose: () => void;
}

export function InstallmentPlanFormModal({ open, plan, onClose }: InstallmentPlanFormModalProps) {
  const createPlan = useCreateInstallmentPlan();
  const updatePlan = useUpdateInstallmentPlan();
  const { data: buildings } = useBuildings();
  const { data: categories } = useFinanceCategories();
  const { data: billingAccounts } = useBillingAccounts();

  const isEdit = Boolean(plan?.id);

  const form = useForm<InstallmentPlanFormValues>({
    resolver: zodResolver(installmentPlanFormSchema),
    defaultValues: emptyDefaults(),
  });

  useEffect(() => {
    if (open) {
      form.reset(plan ? planToDefaults(plan) : emptyDefaults());
    }
  }, [open, plan, form]);

  const embedded = form.watch('embedded');

  function handleSubmit(values: InstallmentPlanFormValues) {
    const payload = {
      description: values.description,
      category_id: values.category_id,
      building_id: values.building_id,
      total_amount: values.total_amount,
      installment_count: values.installment_count,
      start_due_date: values.start_due_date,
      default_due_day: values.default_due_day,
      embedded: values.embedded,
      linked_billing_account_id: values.embedded ? values.linked_billing_account_id : null,
      notes: values.notes,
    };

    if (isEdit && plan?.id) {
      updatePlan.mutate(
        { id: plan.id, ...payload },
        {
          onSuccess: () => {
            toast.success('Plano de parcelas atualizado com sucesso');
            onClose();
          },
          onError: (error) => {
            handleError(error, 'Erro ao salvar plano de parcelas');
          },
        },
      );
      return;
    }

    createPlan.mutate(
      { lifecycle_state: 'active', ...payload },
      {
        onSuccess: () => {
          toast.success('Plano de parcelas criado com sucesso');
          onClose();
        },
        onError: (error) => {
          handleError(error, 'Erro ao salvar plano de parcelas');
        },
      },
    );
  }

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-h-[90vh] max-w-3xl overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{isEdit ? 'Editar Plano de Parcelas' : 'Novo Plano de Parcelas'}</DialogTitle>
          <DialogDescription>
            Defina o plano de parcelas. As parcelas são geradas pela materialização do mês.
          </DialogDescription>
        </DialogHeader>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(handleSubmit)} noValidate className="space-y-4">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <FormField
                control={form.control}
                name="description"
                render={({ field }) => (
                  <FormItem className="sm:col-span-2">
                    <FormLabel>Descrição</FormLabel>
                    <FormControl>
                      <Input placeholder="Ex.: IPTU 2026 - Prédio 836" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="building_id"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Prédio (opcional)</FormLabel>
                    <Select
                      value={field.value ? String(field.value) : NONE}
                      onValueChange={(value) => field.onChange(value === NONE ? null : Number(value))}
                    >
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue placeholder="Condomínio" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        <SelectItem value={NONE}>Condomínio (sem prédio)</SelectItem>
                        {buildings?.map((building) =>
                          building.id === undefined ? null : (
                            <SelectItem key={building.id} value={String(building.id)}>
                              {building.name}
                            </SelectItem>
                          ),
                        )}
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
                      value={field.value ? String(field.value) : NONE}
                      onValueChange={(value) => field.onChange(value === NONE ? null : Number(value))}
                    >
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue placeholder="Selecione" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        <SelectItem value={NONE}>Nenhuma</SelectItem>
                        {categories?.map((category) =>
                          category.id === undefined ? null : (
                            <SelectItem key={category.id} value={String(category.id)}>
                              {category.name}
                            </SelectItem>
                          ),
                        )}
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              <FormField
                control={form.control}
                name="total_amount"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Valor total</FormLabel>
                    <FormControl>
                      <Input
                        type="number"
                        step="0.01"
                        min="0"
                        value={Number.isNaN(field.value) ? '' : field.value}
                        onChange={(e) => field.onChange(e.target.valueAsNumber)}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="installment_count"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Nº de parcelas</FormLabel>
                    <FormControl>
                      <Input
                        type="number"
                        min="1"
                        value={Number.isNaN(field.value) ? '' : field.value}
                        onChange={(e) => field.onChange(e.target.valueAsNumber)}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="default_due_day"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Dia de vencimento</FormLabel>
                    <FormControl>
                      <Input
                        type="number"
                        min="1"
                        max="31"
                        value={Number.isNaN(field.value) ? '' : field.value}
                        onChange={(e) => field.onChange(e.target.valueAsNumber)}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            <FormField
              control={form.control}
              name="start_due_date"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Primeira parcela</FormLabel>
                  <FormControl>
                    <Input type="date" {...field} />
                  </FormControl>
                  <FormDescription>Data de vencimento da primeira parcela.</FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="embedded"
              render={({ field }) => (
                <FormItem className="flex items-center justify-between rounded-md border p-3">
                  <div className="space-y-0.5">
                    <FormLabel>Parcela embutida</FormLabel>
                    <FormDescription>
                      Quando ativo, cada parcela vira uma linha na conta recorrente vinculada.
                    </FormDescription>
                  </div>
                  <FormControl>
                    <Switch
                      checked={field.value}
                      onCheckedChange={field.onChange}
                      aria-label="Parcela embutida"
                    />
                  </FormControl>
                </FormItem>
              )}
            />

            {embedded && (
              <FormField
                control={form.control}
                name="linked_billing_account_id"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Conta recorrente vinculada</FormLabel>
                    <Select
                      value={field.value ? String(field.value) : NONE}
                      onValueChange={(value) => field.onChange(value === NONE ? null : Number(value))}
                    >
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue placeholder="Selecione a conta recorrente" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        <SelectItem value={NONE}>Nenhuma</SelectItem>
                        {billingAccounts?.map((account) =>
                          account.id === undefined ? null : (
                            <SelectItem key={account.id} value={String(account.id)}>
                              {account.name}
                            </SelectItem>
                          ),
                        )}
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )}
              />
            )}

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
              <Button type="button" variant="outline" onClick={onClose}>
                Cancelar
              </Button>
              <Button type="submit" disabled={createPlan.isPending || updatePlan.isPending}>
                {isEdit ? 'Atualizar' : 'Criar'}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
