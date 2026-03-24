'use client';

import { useEffect } from 'react';
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
import { CalendarIcon, Info } from 'lucide-react';
import { format } from 'date-fns';
import { ptBR } from 'date-fns/locale';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';
import { useCreateLease, useUpdateLease } from '@/lib/api/hooks/use-leases';
import { useAvailableApartments } from '@/lib/api/hooks/use-apartments';
import { useTenants } from '@/lib/api/hooks/use-tenants';
import { type Lease } from '@/lib/schemas/lease.schema';
import { formatCurrency } from '@/lib/utils/formatters';

interface Props {
  open: boolean;
  lease?: Lease | null;
  onClose: () => void;
}

const leaseFormSchema = z.object({
  apartment_id: z.number().min(1, 'Selecione um apartamento'),
  responsible_tenant_id: z.number().min(1, 'Selecione o inquilino responsável'),
  tenant_ids: z.array(z.number()).min(1, 'Selecione pelo menos um inquilino'),
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

export function LeaseFormModal({ open, lease, onClose }: Props) {
  const createMutation = useCreateLease();
  const updateMutation = useUpdateLease();
  const { data: apartments, isLoading: apartmentsLoading } = useAvailableApartments();
  const { data: tenants, isLoading: tenantsLoading } = useTenants();

  const formMethods = useForm<LeaseFormValues>({
    resolver: zodResolver(leaseFormSchema),
    defaultValues: {
      apartment_id: undefined,
      responsible_tenant_id: undefined,
      tenant_ids: [],
      start_date: undefined,
      validity_months: 12,
      tag_fee: 50,
      deposit_amount: null,
      cleaning_fee_paid: false,
      tag_deposit_paid: false,
    },
  });

  const selectedApartmentId = formMethods.watch('apartment_id');
  const selectedApartment = apartments?.find(apt => apt.id === selectedApartmentId);

  const selectedResponsibleTenantId = formMethods.watch('responsible_tenant_id');
  const selectedResponsibleTenant = tenants?.find(t => t.id === selectedResponsibleTenantId);

  useEffect(() => {
    if (lease) {
      formMethods.reset({
        apartment_id: lease.apartment?.id,
        responsible_tenant_id: lease.responsible_tenant?.id,
        tenant_ids: lease.tenants?.map((t) => t.id).filter((id): id is number => id !== undefined) ?? [],
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
        tenant_ids: [],
        start_date: undefined,
        validity_months: 12,
        tag_fee: 50,
        deposit_amount: null,
        cleaning_fee_paid: false,
        tag_deposit_paid: false,
      });
    }
  }, [lease, formMethods]);

  // Watch responsible_tenant_id to auto-sync with tenant_ids for single-tenant apartments
  const responsibleTenantId = formMethods.watch('responsible_tenant_id');

  // Auto-select responsible tenant in tenant_ids when apartment only supports 1 person
  useEffect(() => {
    if (selectedApartment?.max_tenants === 1 && responsibleTenantId) {
      formMethods.setValue('tenant_ids', [responsibleTenantId]);
    }
  }, [selectedApartment?.max_tenants, responsibleTenantId, formMethods]);

  const handleSubmit = async (values: LeaseFormValues) => {
    try {
      const payload = {
        apartment_id: values.apartment_id,
        responsible_tenant_id: values.responsible_tenant_id,
        tenant_ids: values.tenant_ids,
        start_date: format(values.start_date, 'yyyy-MM-dd'),
        validity_months: values.validity_months,
        tag_fee: values.tag_fee,
        deposit_amount: values.deposit_amount ?? null,
        cleaning_fee_paid: values.cleaning_fee_paid,
        tag_deposit_paid: values.tag_deposit_paid,
      };

      if (lease?.id) {
        await updateMutation.mutateAsync({
          ...payload,
          id: lease.id,
        });
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
  };

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

            {/* All Tenants - Only show when apartment supports 2+ tenants */}
            {selectedApartment && selectedApartment.max_tenants > 1 && (
              <FormField
                control={formMethods.control}
                name="tenant_ids"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Todos os Inquilinos</FormLabel>
                    <div className="space-y-2 max-h-[200px] overflow-y-auto border rounded-md p-3">
                      {tenants?.map((t) => (
                        <div key={t.id} className="flex items-center space-x-2">
                          <input
                            type="checkbox"
                            id={`tenant-${t.id}`}
                            checked={t.id !== undefined && field.value?.includes(t.id)}
                            onChange={(e) => {
                              const currentValue = field.value ?? [];
                              if (e.target.checked && t.id !== undefined) {
                                field.onChange([...currentValue, t.id]);
                              } else {
                                field.onChange(currentValue.filter((id) => id !== t.id));
                              }
                            }}
                            className="h-4 w-4 rounded border-border"
                          />
                          <label
                            htmlFor={`tenant-${t.id}`}
                            className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
                          >
                            {t.name} - {t.cpf_cnpj}
                          </label>
                        </div>
                      ))}
                    </div>
                    <FormDescription>
                      Todos os inquilinos que morarão no apartamento (incluindo o responsável). Máximo: {selectedApartment.max_tenants}
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
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
                    R$ 50,00 para 1 inquilino, R$ 80,00 para 2+ inquilinos
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
                        <div>• Aluguel: {formatCurrency(selectedApartment.rental_value)}</div>
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
