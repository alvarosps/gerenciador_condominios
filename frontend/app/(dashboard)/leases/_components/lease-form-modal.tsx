'use client';

import { useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
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
  FormDescription,
} from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { Checkbox } from '@/components/ui/checkbox';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Card, CardContent } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { Calendar } from '@/components/ui/calendar';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Label } from '@/components/ui/label';
import { CalendarIcon, Info } from 'lucide-react';
import { format } from 'date-fns';
import { ptBR } from 'date-fns/locale';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';
import { useCreateLease, useUpdateLease } from '@/lib/api/hooks/use-leases';
import { useAvailableApartments } from '@/lib/api/hooks/use-apartments';
import { useTenants } from '@/lib/api/hooks/use-tenants';
import { type Lease } from '@/lib/schemas/lease.schema';
import { type Dependent } from '@/lib/schemas/tenant.schema';
import { formatCurrency } from '@/lib/utils/formatters';
import { apiClient } from '@/lib/api/client';

const TAG_FEE_SINGLE = 50;
const TAG_FEE_DOUBLE = 80;

interface Props {
  open: boolean;
  lease?: Lease | null;
  onClose: () => void;
}

const leaseFormSchema = z.object({
  apartment_id: z.number().min(1, 'Selecione um apartamento'),
  responsible_tenant_id: z.number().min(1, 'Selecione o inquilino responsável'),
  number_of_tenants: z.number().min(1).max(2),
  rental_value: z.number().min(0),
  resident_dependent_id: z.number().optional().nullable(),
  start_date: z.date(),
  validity_months: z.number()
    .min(1, 'Validade deve ser no mínimo 1 mês')
    .max(60, 'Validade deve ser no máximo 60 meses'),
  tag_fee: z.number().min(0, 'Valor não pode ser negativo'),
  deposit_amount: z.number().min(0, 'Valor não pode ser negativo').optional().nullable(),
  cleaning_fee_paid: z.boolean(),
  tag_deposit_paid: z.boolean(),
});

type LeaseFormValues = z.infer<typeof leaseFormSchema>;

interface NewDependentForm {
  name: string;
  cpf_cnpj: string;
  phone: string;
}

export function LeaseFormModal({ open, lease, onClose }: Props) {
  const createMutation = useCreateLease();
  const updateMutation = useUpdateLease();
  const { data: apartments, isLoading: apartmentsLoading } = useAvailableApartments();
  const { data: tenants, isLoading: tenantsLoading } = useTenants();

  const [newDependentForm, setNewDependentForm] = useState<NewDependentForm>({
    name: '',
    cpf_cnpj: '',
    phone: '',
  });
  const [showNewDependentForm, setShowNewDependentForm] = useState(false);

  const formMethods = useForm<LeaseFormValues>({
    resolver: zodResolver(leaseFormSchema),
    defaultValues: {
      apartment_id: undefined,
      responsible_tenant_id: undefined,
      number_of_tenants: 1,
      rental_value: 0,
      resident_dependent_id: null,
      start_date: undefined,
      validity_months: 12,
      tag_fee: TAG_FEE_SINGLE,
      deposit_amount: null,
      cleaning_fee_paid: false,
      tag_deposit_paid: false,
    },
  });

  const selectedApartmentId = formMethods.watch('apartment_id');
  const selectedApartment = apartments?.find(apt => apt.id === selectedApartmentId);

  const selectedResponsibleTenantId = formMethods.watch('responsible_tenant_id');
  const selectedResponsibleTenant = tenants?.find(t => t.id === selectedResponsibleTenantId);

  const numberOfTenants = formMethods.watch('number_of_tenants');

  const isEditMode = Boolean(lease);

  useEffect(() => {
    if (lease) {
      formMethods.reset({
        apartment_id: lease.apartment?.id,
        responsible_tenant_id: lease.responsible_tenant?.id,
        number_of_tenants: lease.number_of_tenants ?? 1,
        rental_value: lease.rental_value ?? 0,
        resident_dependent_id: lease.resident_dependent_id ?? null,
        start_date: new Date(lease.start_date),
        validity_months: lease.validity_months,
        tag_fee: lease.tag_fee,
        deposit_amount: lease.deposit_amount ?? null,
        cleaning_fee_paid: lease.cleaning_fee_paid ?? false,
        tag_deposit_paid: lease.tag_deposit_paid ?? false,
      });
    } else {
      formMethods.reset({
        apartment_id: undefined,
        responsible_tenant_id: undefined,
        number_of_tenants: 1,
        rental_value: 0,
        resident_dependent_id: null,
        start_date: undefined,
        validity_months: 12,
        tag_fee: TAG_FEE_SINGLE,
        deposit_amount: null,
        cleaning_fee_paid: false,
        tag_deposit_paid: false,
      });
    }
    setShowNewDependentForm(false);
    setNewDependentForm({ name: '', cpf_cnpj: '', phone: '' });
  }, [lease, formMethods]);

  // Auto-set number_of_tenants=1 and derive values when apartment changes (create mode only)
  useEffect(() => {
    if (isEditMode || !selectedApartment) return;
    formMethods.setValue('number_of_tenants', 1);
    formMethods.setValue('rental_value', selectedApartment.rental_value);
    formMethods.setValue('tag_fee', TAG_FEE_SINGLE);
    formMethods.setValue('resident_dependent_id', null);
    setShowNewDependentForm(false);
    setNewDependentForm({ name: '', cpf_cnpj: '', phone: '' });
  }, [selectedApartmentId, isEditMode, formMethods, selectedApartment]);

  // Clear dependent when responsible tenant changes
  useEffect(() => {
    formMethods.setValue('resident_dependent_id', null);
    setShowNewDependentForm(false);
    setNewDependentForm({ name: '', cpf_cnpj: '', phone: '' });
  }, [selectedResponsibleTenantId, formMethods]);

  const handleNumberOfTenantsChange = (value: number) => {
    formMethods.setValue('number_of_tenants', value);
    formMethods.setValue('resident_dependent_id', null);
    setShowNewDependentForm(false);
    setNewDependentForm({ name: '', cpf_cnpj: '', phone: '' });

    if (selectedApartment) {
      if (value === 2) {
        formMethods.setValue(
          'rental_value',
          selectedApartment.rental_value_double ?? selectedApartment.rental_value
        );
        formMethods.setValue('tag_fee', TAG_FEE_DOUBLE);
      } else {
        formMethods.setValue('rental_value', selectedApartment.rental_value);
        formMethods.setValue('tag_fee', TAG_FEE_SINGLE);
      }
    }
  };

  const handleDependentSelection = (value: string) => {
    if (value === 'new') {
      setShowNewDependentForm(true);
      formMethods.setValue('resident_dependent_id', null);
    } else {
      setShowNewDependentForm(false);
      formMethods.setValue('resident_dependent_id', Number(value));
    }
  };

  const createDependentAndGetId = async (tenantId: number): Promise<number> => {
    const existingTenant = tenants?.find(t => t.id === tenantId);
    const existingDependents: Dependent[] = existingTenant?.dependents ?? [];

    const updatedDependents = [
      ...existingDependents.map(d => ({
        id: d.id,
        name: d.name,
        phone: d.phone,
        cpf_cnpj: d.cpf_cnpj ?? '',
      })),
      {
        name: newDependentForm.name,
        phone: newDependentForm.phone,
        cpf_cnpj: newDependentForm.cpf_cnpj,
      },
    ];

    const response = await apiClient.patch<{ id: number; dependents: Dependent[] }>(
      `/tenants/${String(tenantId)}/`,
      { dependents: updatedDependents }
    );

    const createdDependents = response.data.dependents;
    const newDependent = createdDependents.find(
      d => d.name === newDependentForm.name && d.cpf_cnpj === newDependentForm.cpf_cnpj
    );

    if (!newDependent?.id) {
      throw new Error('Falha ao criar dependente');
    }

    return newDependent.id;
  };

  const handleSubmit = async (values: LeaseFormValues) => {
    try {
      let residentDependentId = values.resident_dependent_id ?? null;

      if (values.number_of_tenants === 2 && showNewDependentForm) {
        if (!newDependentForm.name || !newDependentForm.phone) {
          toast.error('Preencha nome e telefone do dependente');
          return;
        }
        residentDependentId = await createDependentAndGetId(values.responsible_tenant_id);
      }

      const payload = {
        apartment_id: values.apartment_id,
        responsible_tenant_id: values.responsible_tenant_id,
        tenant_ids: [values.responsible_tenant_id],
        number_of_tenants: values.number_of_tenants,
        rental_value: values.rental_value,
        resident_dependent_id: values.number_of_tenants === 2 ? residentDependentId : null,
        start_date: format(values.start_date, 'yyyy-MM-dd'),
        validity_months: values.validity_months,
        tag_fee: values.tag_fee,
        deposit_amount: values.deposit_amount ?? null,
        cleaning_fee_paid: values.cleaning_fee_paid,
        tag_deposit_paid: values.tag_deposit_paid,
      };

      if (lease?.id) {
        await updateMutation.mutateAsync({ ...payload, id: lease.id });
        toast.success('Locação atualizada com sucesso');
      } else {
        await createMutation.mutateAsync(payload);
        toast.success('Locação criada com sucesso');
      }

      onClose();
      formMethods.reset();
    } catch (error) {
      toast.error('Erro ao salvar locação');
      console.error('Save error:', error);
    }
  };

  const handleClose = () => {
    onClose();
    formMethods.reset();
    setShowNewDependentForm(false);
    setNewDependentForm({ name: '', cpf_cnpj: '', phone: '' });
  };

  const dependents = selectedResponsibleTenant?.dependents ?? [];

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{lease ? 'Editar Locação' : 'Nova Locação'}</DialogTitle>
        </DialogHeader>

        <Form {...formMethods}>
          <form onSubmit={formMethods.handleSubmit(handleSubmit)} className="space-y-4">
            <Alert>
              <Info className="h-4 w-4" />
              <AlertDescription>
                Os valores de aluguel e taxa de limpeza são definidos no cadastro do apartamento. O dia de vencimento é definido no cadastro do inquilino.
              </AlertDescription>
            </Alert>

            {isEditMode && lease?.contract_generated && (
              <Alert>
                <Info className="h-4 w-4" />
                <AlertDescription>
                  Este contrato já foi gerado. Após editar, será necessário regenerar o contrato.
                </AlertDescription>
              </Alert>
            )}

            <Separator />
            <div className="text-sm font-medium">Apartamento e Inquilinos</div>

            {/* Apartment Selection */}
            <FormField
              control={formMethods.control}
              name="apartment_id"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Apartamento</FormLabel>
                  <Select
                    value={field.value ? String(field.value) : ''}
                    onValueChange={(value) => field.onChange(Number(value))}
                    disabled={apartmentsLoading}
                  >
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue placeholder="Selecione o apartamento" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {apartments?.map((apt) => (
                        <SelectItem key={apt.id} value={String(apt.id)}>
                          {apt.building?.name} - Apto {apt.number} ({formatCurrency(apt.rental_value)})
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* Responsible Tenant */}
            <FormField
              control={formMethods.control}
              name="responsible_tenant_id"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Inquilino Responsável</FormLabel>
                  <Select
                    value={field.value ? String(field.value) : ''}
                    onValueChange={(value) => field.onChange(Number(value))}
                    disabled={tenantsLoading}
                  >
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue placeholder="Selecione o inquilino responsável" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {tenants?.map((t) => (
                        <SelectItem key={t.id} value={String(t.id ?? '')}>
                          {t.name} - {t.cpf_cnpj}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <FormDescription>
                    O inquilino responsável é o titular do contrato
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* Number of Tenants — only for apartments that support 2 */}
            {selectedApartment?.max_tenants === 2 && (
              <FormField
                control={formMethods.control}
                name="number_of_tenants"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Quantas pessoas?</FormLabel>
                    <FormControl>
                      <RadioGroup
                        value={String(field.value)}
                        onValueChange={(value) => handleNumberOfTenantsChange(Number(value))}
                        className="flex gap-6"
                      >
                        <div className="flex items-center space-x-2">
                          <RadioGroupItem value="1" id="tenants-1" />
                          <Label htmlFor="tenants-1">1 pessoa</Label>
                        </div>
                        <div className="flex items-center space-x-2">
                          <RadioGroupItem value="2" id="tenants-2" />
                          <Label htmlFor="tenants-2">2 pessoas</Label>
                        </div>
                      </RadioGroup>
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            )}

            {/* Dependent selection — only when 2 tenants selected */}
            {numberOfTenants === 2 && selectedApartment?.max_tenants === 2 && (
              <div className="space-y-3 rounded-md border p-4">
                <div className="text-sm font-medium">Segundo morador</div>

                {dependents.length > 0 && (
                  <RadioGroup
                    value={showNewDependentForm ? 'new' : String(formMethods.watch('resident_dependent_id') ?? '')}
                    onValueChange={handleDependentSelection}
                    className="space-y-2"
                  >
                    {dependents.map((dep) => (
                      <div key={dep.id} className="flex items-center space-x-2">
                        <RadioGroupItem value={String(dep.id)} id={`dep-${String(dep.id)}`} />
                        <Label htmlFor={`dep-${String(dep.id)}`}>
                          {dep.name}
                          {dep.cpf_cnpj ? ` — ${dep.cpf_cnpj}` : ''}
                          {dep.phone ? ` — ${dep.phone}` : ''}
                        </Label>
                      </div>
                    ))}
                    <div className="flex items-center space-x-2">
                      <RadioGroupItem value="new" id="dep-new" />
                      <Label htmlFor="dep-new">Cadastrar novo dependente</Label>
                    </div>
                  </RadioGroup>
                )}

                {(dependents.length === 0 || showNewDependentForm) && (
                  <div className="space-y-3 pt-2">
                    {dependents.length > 0 && (
                      <div className="text-sm text-muted-foreground">Novo dependente:</div>
                    )}
                    <div className="grid grid-cols-1 gap-3">
                      <div>
                        <Label htmlFor="dep-name-new">Nome</Label>
                        <Input
                          id="dep-name-new"
                          placeholder="Nome completo"
                          value={newDependentForm.name}
                          onChange={(e) =>
                            setNewDependentForm((prev) => ({ ...prev, name: e.target.value }))
                          }
                        />
                      </div>
                      <div>
                        <Label htmlFor="dep-cpf-new">CPF</Label>
                        <Input
                          id="dep-cpf-new"
                          placeholder="000.000.000-00"
                          value={newDependentForm.cpf_cnpj}
                          onChange={(e) =>
                            setNewDependentForm((prev) => ({ ...prev, cpf_cnpj: e.target.value }))
                          }
                        />
                      </div>
                      <div>
                        <Label htmlFor="dep-phone-new">Telefone</Label>
                        <Input
                          id="dep-phone-new"
                          placeholder="(00) 00000-0000"
                          value={newDependentForm.phone}
                          onChange={(e) =>
                            setNewDependentForm((prev) => ({ ...prev, phone: e.target.value }))
                          }
                        />
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}

            <Separator />
            <div className="text-sm font-medium">Período e Valores</div>

            {/* Start Date */}
            <FormField
              control={formMethods.control}
              name="start_date"
              render={({ field }) => (
                <FormItem className="flex flex-col">
                  <FormLabel>Data de Início</FormLabel>
                  <Popover>
                    <PopoverTrigger asChild>
                      <FormControl>
                        <Button
                          variant="outline"
                          className={cn(
                            'w-full pl-3 text-left font-normal',
                            !field.value && 'text-muted-foreground'
                          )}
                        >
                          {field.value ? (
                            format(field.value, 'dd/MM/yyyy', { locale: ptBR })
                          ) : (
                            <span>Selecione a data</span>
                          )}
                          <CalendarIcon className="ml-auto h-4 w-4 opacity-50" />
                        </Button>
                      </FormControl>
                    </PopoverTrigger>
                    <PopoverContent className="w-auto p-0" align="start">
                      <Calendar
                        mode="single"
                        selected={field.value}
                        onSelect={field.onChange}
                        locale={ptBR}
                        autoFocus
                      />
                    </PopoverContent>
                  </Popover>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* Validity Months */}
            <FormField
              control={formMethods.control}
              name="validity_months"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Validade (meses)</FormLabel>
                  <FormControl>
                    <Input
                      type="number"
                      min={1}
                      max={60}
                      placeholder="Ex: 12"
                      {...field}
                      onChange={(e) => field.onChange(Number(e.target.value))}
                    />
                  </FormControl>
                  <FormDescription>
                    Número de meses de duração do contrato
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* Tag Fee */}
            <FormField
              control={formMethods.control}
              name="tag_fee"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Taxa de Tag</FormLabel>
                  <FormControl>
                    <div className="relative">
                      <span className="absolute left-3 top-1/2 transform -translate-y-1/2 text-sm text-muted-foreground">
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
                  <FormDescription>
                    R$ 50,00 para 1 pessoa, R$ 80,00 para 2 pessoas
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* Rental Value */}
            <FormField
              control={formMethods.control}
              name="rental_value"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Valor do Aluguel</FormLabel>
                  <FormControl>
                    <div className="relative">
                      <span className="absolute left-3 top-1/2 transform -translate-y-1/2 text-sm text-muted-foreground">
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
                  <FormDescription>
                    Preenchido automaticamente com base no número de moradores. Pode ser editado manualmente.
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* Deposit Amount */}
            <FormField
              control={formMethods.control}
              name="deposit_amount"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Valor do Depósito</FormLabel>
                  <FormControl>
                    <div className="relative">
                      <span className="absolute left-3 top-1/2 transform -translate-y-1/2 text-sm text-muted-foreground">
                        R$
                      </span>
                      <Input
                        type="number"
                        min={0}
                        step="0.01"
                        placeholder="0.00"
                        className="pl-10"
                        value={field.value ?? ''}
                        onChange={(e) => field.onChange(e.target.value === '' ? null : Number(e.target.value))}
                      />
                    </div>
                  </FormControl>
                  <FormDescription>
                    Valor do depósito caução (opcional)
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <Separator />
            <div className="text-sm font-medium">Confirmações de Pagamento</div>

            {/* Cleaning Fee Paid */}
            <FormField
              control={formMethods.control}
              name="cleaning_fee_paid"
              render={({ field }) => (
                <FormItem className="flex flex-row items-start space-x-3 space-y-0 rounded-md border p-4">
                  <FormControl>
                    <Checkbox
                      checked={field.value}
                      onCheckedChange={field.onChange}
                    />
                  </FormControl>
                  <div className="space-y-1 leading-none">
                    <FormLabel>Taxa de Limpeza Paga</FormLabel>
                    <FormDescription>
                      Marque se a taxa de limpeza inicial foi paga pelo inquilino
                    </FormDescription>
                  </div>
                </FormItem>
              )}
            />

            {/* Tag Deposit Paid */}
            <FormField
              control={formMethods.control}
              name="tag_deposit_paid"
              render={({ field }) => (
                <FormItem className="flex flex-row items-start space-x-3 space-y-0 rounded-md border p-4">
                  <FormControl>
                    <Checkbox
                      checked={field.value}
                      onCheckedChange={field.onChange}
                    />
                  </FormControl>
                  <div className="space-y-1 leading-none">
                    <FormLabel>Depósito de Tag Pago</FormLabel>
                    <FormDescription>
                      Marque se o depósito da tag de acesso foi pago pelo inquilino
                    </FormDescription>
                  </div>
                </FormItem>
              )}
            />

            {(selectedApartment ?? selectedResponsibleTenant) && (
              <Card>
                <CardContent className="pt-6">
                  <div className="text-sm space-y-1">
                    <div className="font-medium mb-2">Resumo do Apartamento e Inquilino Selecionados:</div>
                    {selectedApartment && (
                      <>
                        <div>• Prédio: {selectedApartment.building?.name}</div>
                        <div>• Apartamento: {selectedApartment.number}</div>
                        {selectedApartment.max_tenants === 2 ? (
                          <>
                            <div>• Aluguel (1 pessoa): {formatCurrency(selectedApartment.rental_value)}</div>
                            <div>• Aluguel (2 pessoas): {formatCurrency(selectedApartment.rental_value_double ?? selectedApartment.rental_value)}</div>
                            <div className="font-medium text-primary">
                              • Valor selecionado: {formatCurrency(formMethods.watch('rental_value'))}
                            </div>
                          </>
                        ) : (
                          <div>• Aluguel: {formatCurrency(selectedApartment.rental_value)}</div>
                        )}
                        <div>• Limpeza: {formatCurrency(selectedApartment.cleaning_fee)}</div>
                        <div>• Máx. Inquilinos: {selectedApartment.max_tenants}</div>
                        <div>• Móveis incluídos: {selectedApartment.furnitures?.length ?? 0}</div>
                      </>
                    )}
                    {selectedResponsibleTenant?.due_day !== null && selectedResponsibleTenant?.due_day !== undefined && (
                      <div>• Dia de Vencimento: Dia {selectedResponsibleTenant.due_day}</div>
                    )}
                  </div>
                </CardContent>
              </Card>
            )}

            <DialogFooter>
              <Button type="button" variant="outline" onClick={handleClose}>
                Cancelar
              </Button>
              <Button
                type="submit"
                disabled={createMutation.isPending || updateMutation.isPending}
              >
                {lease ? 'Atualizar' : 'Criar'}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
