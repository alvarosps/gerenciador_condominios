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
import { Card, CardContent } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { Calendar } from '@/components/ui/calendar';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import { CalendarIcon } from 'lucide-react';
import { format } from 'date-fns';
import { ptBR } from 'date-fns/locale';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';
import { useCreateLease, useTransferLease } from '@/lib/api/hooks/use-leases';
import { useAvailableApartments } from '@/lib/api/hooks/use-apartments';
import { type Tenant } from '@/lib/schemas/tenant.schema';
import { type Lease } from '@/lib/schemas/lease.schema';
import { formatCPFOrCNPJ, formatCurrency } from '@/lib/utils/formatters';

interface TenantLeaseModalProps {
  mode: 'create' | 'transfer';
  tenant: Tenant;
  currentLease?: Lease | null;
  open: boolean;
  onClose: () => void;
}

const tenantLeaseFormSchema = z.object({
  apartment_id: z.number().min(1, 'Selecione um apartamento'),
  tenant_ids: z.array(z.number()).min(1, 'Selecione pelo menos um inquilino'),
  start_date: z.date(),
  validity_months: z
    .number()
    .min(1, 'Validade deve ser no mínimo 1 mês')
    .max(60, 'Validade deve ser no máximo 60 meses'),
  tag_fee: z.number().min(0, 'Valor não pode ser negativo'),
  deposit_amount: z.number().min(0, 'Valor não pode ser negativo').optional().nullable(),
  cleaning_fee_paid: z.boolean(),
  tag_deposit_paid: z.boolean(),
});

type TenantLeaseFormValues = z.infer<typeof tenantLeaseFormSchema>;

export function TenantLeaseModal({
  mode,
  tenant,
  currentLease,
  open,
  onClose,
}: TenantLeaseModalProps) {
  const createMutation = useCreateLease();
  const transferMutation = useTransferLease();
  const { data: apartments, isLoading: apartmentsLoading } = useAvailableApartments();

  const isPending = createMutation.isPending || transferMutation.isPending;

  const formMethods = useForm<TenantLeaseFormValues>({
    resolver: zodResolver(tenantLeaseFormSchema),
    defaultValues: {
      apartment_id: undefined,
      tenant_ids: tenant.id !== undefined ? [tenant.id] : [],
      start_date: undefined,
      validity_months: 12,
      tag_fee: 50,
      deposit_amount: null,
      cleaning_fee_paid: false,
      tag_deposit_paid: false,
    },
  });

  useEffect(() => {
    if (!open) return;

    if (mode === 'transfer' && currentLease) {
      formMethods.reset({
        apartment_id: undefined,
        tenant_ids: tenant.id !== undefined ? [tenant.id] : [],
        start_date: new Date(currentLease.start_date),
        validity_months: currentLease.validity_months,
        tag_fee: currentLease.tag_fee,
        deposit_amount: currentLease.deposit_amount ?? null,
        cleaning_fee_paid: currentLease.cleaning_fee_paid ?? false,
        tag_deposit_paid: currentLease.tag_deposit_paid ?? false,
      });
    } else {
      formMethods.reset({
        apartment_id: undefined,
        tenant_ids: tenant.id !== undefined ? [tenant.id] : [],
        start_date: new Date(),
        validity_months: 12,
        tag_fee: 50,
        deposit_amount: null,
        cleaning_fee_paid: false,
        tag_deposit_paid: false,
      });
    }
  }, [open, mode, currentLease, tenant, formMethods]);

  const selectedApartmentId = formMethods.watch('apartment_id');
  const selectedApartment = apartments?.find((apt) => apt.id === selectedApartmentId);

  const handleSubmit = async (values: TenantLeaseFormValues) => {
    const tenantId = tenant.id;
    if (tenantId === undefined) {
      toast.error('Inquilino inválido');
      return;
    }

    try {
      const payload = {
        apartment_id: values.apartment_id,
        responsible_tenant_id: tenantId,
        tenant_ids: values.tenant_ids,
        start_date: format(values.start_date, 'yyyy-MM-dd'),
        validity_months: values.validity_months,
        tag_fee: values.tag_fee,
        deposit_amount: values.deposit_amount ?? null,
        cleaning_fee_paid: values.cleaning_fee_paid,
        tag_deposit_paid: values.tag_deposit_paid,
      };

      if (mode === 'transfer' && currentLease?.id !== undefined) {
        await transferMutation.mutateAsync({ leaseId: currentLease.id, ...payload });
        toast.success('Inquilino transferido para nova kitnet com sucesso');
      } else {
        await createMutation.mutateAsync(payload);
        toast.success('Contrato criado com sucesso');
      }

      onClose();
      formMethods.reset();
    } catch {
      toast.error('Erro ao salvar contrato');
    }
  };

  const handleClose = () => {
    onClose();
    formMethods.reset();
  };

  const dialogTitle =
    mode === 'transfer'
      ? `Trocar de Kitnet — ${tenant.name}`
      : `Criar Contrato — ${tenant.name}`;

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{dialogTitle}</DialogTitle>
        </DialogHeader>

        <Card>
          <CardContent className="pt-4">
            <div className="text-sm">
              <div className="font-medium">{tenant.name}</div>
              <div className="text-muted-foreground">{formatCPFOrCNPJ(tenant.cpf_cnpj)}</div>
            </div>
          </CardContent>
        </Card>

        <Form {...formMethods}>
          <form onSubmit={formMethods.handleSubmit(handleSubmit)} className="space-y-4">
            <Separator />
            <div className="text-sm font-medium">Apartamento</div>

            <FormField
              control={formMethods.control}
              name="apartment_id"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Apartamento Disponível</FormLabel>
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
                  <FormDescription>
                    {mode === 'transfer'
                      ? 'Selecione a nova kitnet para o inquilino'
                      : 'Somente apartamentos disponíveis são exibidos'}
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <Separator />
            <div className="text-sm font-medium">Período e Valores</div>

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
                  <FormDescription>Número de meses de duração do contrato</FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

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
                  <FormDescription>R$ 50,00 para 1 inquilino, R$ 80,00 para 2+ inquilinos</FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

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
                        onChange={(e) =>
                          field.onChange(e.target.value === '' ? null : Number(e.target.value))
                        }
                      />
                    </div>
                  </FormControl>
                  <FormDescription>Valor do depósito caução (opcional)</FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <Separator />
            <div className="text-sm font-medium">Confirmações de Pagamento</div>

            <FormField
              control={formMethods.control}
              name="cleaning_fee_paid"
              render={({ field }) => (
                <FormItem className="flex flex-row items-start space-x-3 space-y-0 rounded-md border p-4">
                  <FormControl>
                    <Checkbox checked={field.value} onCheckedChange={field.onChange} />
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

            <FormField
              control={formMethods.control}
              name="tag_deposit_paid"
              render={({ field }) => (
                <FormItem className="flex flex-row items-start space-x-3 space-y-0 rounded-md border p-4">
                  <FormControl>
                    <Checkbox checked={field.value} onCheckedChange={field.onChange} />
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

            {selectedApartment && (
              <Card>
                <CardContent className="pt-4">
                  <div className="text-sm space-y-1">
                    <div className="font-medium mb-2">Resumo do Apartamento Selecionado:</div>
                    <div>• Prédio: {selectedApartment.building?.name}</div>
                    <div>• Apartamento: {selectedApartment.number}</div>
                    <div>• Aluguel: {formatCurrency(selectedApartment.rental_value)}</div>
                    <div>• Limpeza: {formatCurrency(selectedApartment.cleaning_fee)}</div>
                    <div>• Máx. Inquilinos: {selectedApartment.max_tenants}</div>
                  </div>
                </CardContent>
              </Card>
            )}

            <DialogFooter>
              <Button type="button" variant="outline" onClick={handleClose}>
                Cancelar
              </Button>
              <Button type="submit" disabled={isPending}>
                {isPending
                  ? mode === 'transfer'
                    ? 'Transferindo...'
                    : 'Criando...'
                  : mode === 'transfer'
                    ? 'Transferir'
                    : 'Criar Contrato'}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
