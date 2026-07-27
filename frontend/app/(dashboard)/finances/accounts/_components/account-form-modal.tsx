'use client';

import { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { toast } from 'sonner';
import {
  Dialog,
  DialogBody,
  DialogContent,
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
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  useCreateBillingAccount,
  useUpdateBillingAccount,
} from '@/lib/api/hooks/use-billing-accounts';
import { useBuildings } from '@/lib/api/hooks/use-buildings';
import { useFinanceCategories } from '@/lib/api/hooks/use-finance-categories';
import { handleError } from '@/lib/utils/error-handler';
import {
  ACCOUNT_TYPE_LABELS,
  billingAccountTypeValues,
  supplyStatusEnum,
  type BillingAccount,
} from '@/lib/schemas/finances/billing-account.schema';
import { billingAccountStateEnum } from '@/lib/schemas/finances/category.schema';
import { ACCOUNT_STATE_LABELS } from './account-columns';

const NONE = 'none';

const _TYPED_IDENTITY_ACCOUNT_TYPES = ['water', 'electricity', 'iptu'] as const;
const _ERR_IDENTIFIER_REQUIRED = 'Inscrição/UC é obrigatória para contas de água, luz e IPTU';

const accountFormSchema = z
  .object({
    name: z.string().min(1, 'Nome é obrigatório'),
    building_id: z.number().nullable(),
    category_id: z.number().nullable(),
    account_type: z.enum(billingAccountTypeValues),
    external_identifier: z.string(),
    secondary_identifier: z.string(),
    holder_name: z.string(),
    registered_address: z.string(),
    default_due_day: z.number().min(1).max(31),
    expected_amount: z.number().min(0, 'O valor não pode ser negativo'),
    lifecycle_state: billingAccountStateEnum,
    supply_status: supplyStatusEnum,
    tracking_start_month: z.string().nullable(),
    end_date: z.string().nullable(),
    description: z.string(),
    notes: z.string(),
  })
  .superRefine((values, ctx) => {
    if (
      (_TYPED_IDENTITY_ACCOUNT_TYPES as readonly string[]).includes(values.account_type) &&
      values.external_identifier.trim() === ''
    ) {
      ctx.addIssue({
        code: 'custom',
        path: ['external_identifier'],
        message: _ERR_IDENTIFIER_REQUIRED,
      });
    }
  });

type AccountFormValues = z.infer<typeof accountFormSchema>;

const DEFAULTS: AccountFormValues = {
  name: '',
  building_id: null,
  category_id: null,
  account_type: 'generic',
  external_identifier: '',
  secondary_identifier: '',
  holder_name: '',
  registered_address: '',
  default_due_day: 10,
  expected_amount: 0,
  lifecycle_state: 'active',
  supply_status: 'active',
  tracking_start_month: null,
  end_date: null,
  description: '',
  notes: '',
};

function accountToDefaults(account: BillingAccount): AccountFormValues {
  return {
    name: account.name,
    building_id: account.building_id ?? account.building?.id ?? null,
    category_id: account.category_id ?? account.category?.id ?? null,
    account_type: account.account_type,
    external_identifier: account.external_identifier ?? '',
    secondary_identifier: account.secondary_identifier ?? '',
    holder_name: account.holder_name ?? '',
    registered_address: account.registered_address ?? '',
    default_due_day: account.default_due_day,
    expected_amount: account.expected_amount,
    lifecycle_state: account.lifecycle_state,
    supply_status: account.supply_status,
    tracking_start_month: account.tracking_start_month ?? null,
    end_date: account.end_date ?? null,
    description: account.description ?? '',
    notes: account.notes ?? '',
  };
}

interface AccountFormModalProps {
  open: boolean;
  account?: BillingAccount | null;
  onClose: () => void;
}

export function AccountFormModal({ open, account, onClose }: AccountFormModalProps) {
  const createMutation = useCreateBillingAccount();
  const updateMutation = useUpdateBillingAccount();
  const { data: buildings } = useBuildings();
  const { data: categories } = useFinanceCategories();

  const isEditing = Boolean(account?.id);
  const isLoading = createMutation.isPending || updateMutation.isPending;

  const form = useForm<AccountFormValues>({
    resolver: zodResolver(accountFormSchema),
    defaultValues: DEFAULTS,
  });

  useEffect(() => {
    if (open) {
      form.reset(account ? accountToDefaults(account) : DEFAULTS);
    }
  }, [open, account, form]);

  async function onSubmit(values: AccountFormValues) {
    try {
      // Dual pattern write: building_id/category_id plain; open_balance is a read-only
      // annotation (S67) and is never part of the payload.
      const payload = {
        name: values.name,
        building_id: values.building_id,
        category_id: values.category_id,
        account_type: values.account_type,
        external_identifier: values.external_identifier,
        secondary_identifier: values.secondary_identifier,
        holder_name: values.holder_name,
        registered_address: values.registered_address,
        default_due_day: values.default_due_day,
        expected_amount: values.expected_amount,
        lifecycle_state: values.lifecycle_state,
        supply_status: values.supply_status,
        tracking_start_month: values.tracking_start_month,
        end_date: values.end_date,
        description: values.description,
        notes: values.notes,
      };
      if (isEditing && account?.id) {
        await updateMutation.mutateAsync({ ...payload, id: account.id });
        toast.success('Conta atualizada com sucesso');
      } else {
        await createMutation.mutateAsync(payload);
        toast.success('Conta cadastrada com sucesso');
      }
      onClose();
      form.reset(DEFAULTS);
    } catch (error) {
      toast.error('Erro ao salvar conta');
      handleError(error, 'AccountFormModal.onSubmit');
    }
  }

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-h-[90vh] max-w-2xl flex flex-col">
        <DialogHeader>
          <DialogTitle>
            {isEditing ? 'Editar Conta Cadastrada' : 'Nova Conta Cadastrada'}
          </DialogTitle>
        </DialogHeader>

        <Form {...form}>
          <form
            onSubmit={form.handleSubmit(onSubmit)}
            noValidate
            className="flex flex-1 flex-col overflow-hidden"
          >
            <DialogBody className="space-y-4 pr-1">
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <FormField
                  control={form.control}
                  name="name"
                  render={({ field }) => (
                    <FormItem className="sm:col-span-2">
                      <FormLabel>Nome *</FormLabel>
                      <FormControl>
                        <Input placeholder="Ex: Água DMAE 836" {...field} disabled={isLoading} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="account_type"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Tipo de conta</FormLabel>
                      <Select
                        value={field.value}
                        onValueChange={field.onChange}
                        disabled={isLoading}
                      >
                        <FormControl>
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          {billingAccountTypeValues.map((type) => (
                            <SelectItem key={type} value={type}>
                              {ACCOUNT_TYPE_LABELS[type]}
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
                  name="building_id"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Prédio</FormLabel>
                      <Select
                        value={field.value ? String(field.value) : NONE}
                        onValueChange={(value) =>
                          field.onChange(value === NONE ? null : Number(value))
                        }
                        disabled={isLoading}
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
                            )
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
                      <FormLabel>Categoria</FormLabel>
                      <Select
                        value={field.value ? String(field.value) : NONE}
                        onValueChange={(value) =>
                          field.onChange(value === NONE ? null : Number(value))
                        }
                        disabled={isLoading}
                      >
                        <FormControl>
                          <SelectTrigger>
                            <SelectValue placeholder="Nenhuma" />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          <SelectItem value={NONE}>Nenhuma</SelectItem>
                          {categories?.map((category) =>
                            category.id === undefined ? null : (
                              <SelectItem key={category.id} value={String(category.id)}>
                                {category.name}
                              </SelectItem>
                            )
                          )}
                        </SelectContent>
                      </Select>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="external_identifier"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Inscrição / UC</FormLabel>
                      <FormControl>
                        <Input
                          placeholder="Inscrição municipal / Unidade Consumidora"
                          {...field}
                          disabled={isLoading}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="secondary_identifier"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Relógio / Imóvel</FormLabel>
                      <FormControl>
                        <Input
                          placeholder="Número do relógio / imóvel"
                          {...field}
                          disabled={isLoading}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="holder_name"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Titular</FormLabel>
                      <FormControl>
                        <Input placeholder="Nome do titular" {...field} disabled={isLoading} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="registered_address"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Endereço cadastrado</FormLabel>
                      <FormControl>
                        <Input placeholder="Endereço na conta" {...field} disabled={isLoading} />
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
                          min={1}
                          max={31}
                          value={field.value}
                          onChange={(event) => field.onChange(Number(event.target.value))}
                          onBlur={field.onBlur}
                          name={field.name}
                          ref={field.ref}
                          disabled={isLoading}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="expected_amount"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Valor esperado</FormLabel>
                      <FormControl>
                        <Input
                          type="number"
                          min={0}
                          step="0.01"
                          value={field.value}
                          onChange={(event) => field.onChange(Number(event.target.value))}
                          onBlur={field.onBlur}
                          name={field.name}
                          ref={field.ref}
                          disabled={isLoading}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="lifecycle_state"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Estado</FormLabel>
                      <Select
                        value={field.value}
                        onValueChange={field.onChange}
                        disabled={isLoading}
                      >
                        <FormControl>
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          {billingAccountStateEnum.options.map((state) => (
                            <SelectItem key={state} value={state}>
                              {ACCOUNT_STATE_LABELS[state]}
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
                  name="supply_status"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Fornecimento</FormLabel>
                      <Select
                        value={field.value}
                        onValueChange={field.onChange}
                        disabled={isLoading}
                      >
                        <FormControl>
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          <SelectItem value="active">Normal</SelectItem>
                          <SelectItem value="cut">Cortada</SelectItem>
                        </SelectContent>
                      </Select>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="tracking_start_month"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Início do acompanhamento</FormLabel>
                      <FormControl>
                        <Input
                          type="date"
                          value={field.value ?? ''}
                          onChange={(event) => {
                            const raw = event.target.value;
                            field.onChange(raw ? `${raw.slice(0, 7)}-01` : null);
                          }}
                          disabled={isLoading}
                        />
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
                      <FormLabel>Data de encerramento</FormLabel>
                      <FormControl>
                        <Input
                          type="date"
                          value={field.value ?? ''}
                          onChange={(event) => field.onChange(event.target.value || null)}
                          disabled={isLoading}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>

              <FormField
                control={form.control}
                name="description"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Descrição</FormLabel>
                    <FormControl>
                      <Textarea
                        placeholder="Descrição da conta..."
                        rows={2}
                        {...field}
                        disabled={isLoading}
                      />
                    </FormControl>
                    <FormDescription>Texto livre exibido no cadastro da conta.</FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="notes"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Observações</FormLabel>
                    <FormControl>
                      <Textarea
                        placeholder="Notas adicionais..."
                        rows={2}
                        {...field}
                        disabled={isLoading}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </DialogBody>

            <DialogFooter className="pt-4">
              <Button type="button" variant="outline" onClick={onClose} disabled={isLoading}>
                Cancelar
              </Button>
              <Button type="submit" disabled={isLoading}>
                {isEditing ? 'Atualizar' : 'Criar'}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
