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
import { Lease } from '@/lib/schemas/lease.schema';
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
  rental_value: z.number().min(0, 'Valor não pode ser negativo'),
  cleaning_fee: z.number().min(0, 'Valor não pode ser negativo'),
  tag_fee: z.number().min(0, 'Valor não pode ser negativo'),
  due_day: z.number().min(1, 'Dia deve ser no mínimo 1').max(31, 'Dia deve ser no máximo 31'),
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
      rental_value: 0,
      cleaning_fee: 0,
      tag_fee: 50,
      due_day: 10,
    },
  });

  const selectedApartmentId = formMethods.watch('apartment_id');
  const selectedApartment = apartments?.find(apt => apt.id === selectedApartmentId);

  useEffect(() => {
    if (lease) {
      formMethods.reset({
        apartment_id: lease.apartment?.id,
        responsible_tenant_id: lease.responsible_tenant?.id,
        tenant_ids: lease.tenants?.map((t) => t.id!) || [],
        start_date: new Date(lease.start_date),
        validity_months: lease.validity_months,
        rental_value: lease.rental_value,
        cleaning_fee: lease.cleaning_fee,
        tag_fee: lease.tag_fee,
        due_day: lease.due_day,
      });
    } else {
      formMethods.reset({
        apartment_id: undefined,
        responsible_tenant_id: undefined,
        tenant_ids: [],
        start_date: undefined,
        validity_months: 12,
        rental_value: 0,
        cleaning_fee: 0,
        tag_fee: 50,
        due_day: 10,
      });
    }
  }, [lease, formMethods]);

  // Auto-fill rental value and cleaning fee when apartment changes
  useEffect(() => {
    if (selectedApartment && !lease) {
      formMethods.setValue('rental_value', selectedApartment.rental_value);
      formMethods.setValue('cleaning_fee', selectedApartment.cleaning_fee);
    }
  }, [selectedApartment, formMethods, lease]);

  const handleSubmit = async (values: LeaseFormValues) => {
    try {
      const payload = {
        ...values,
        start_date: format(values.start_date, 'yyyy-MM-dd'),
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
                Os valores de aluguel e taxa de limpeza serão preenchidos automaticamente ao selecionar o apartamento.
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
                        <SelectItem key={t.id} value={String(t.id!)}>
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

            {/* All Tenants - Note: shadcn Select doesn't have native multiple mode, using comma-separated approach */}
            <FormField
              control={formMethods.control}
              name="tenant_ids"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Todos os Inquilinos</FormLabel>
                  <div className="space-y-2">
                    {tenants?.map((t) => (
                      <div key={t.id} className="flex items-center space-x-2">
                        <input
                          type="checkbox"
                          id={`tenant-${t.id}`}
                          checked={field.value?.includes(t.id!)}
                          onChange={(e) => {
                            const currentValue = field.value || [];
                            if (e.target.checked) {
                              field.onChange([...currentValue, t.id!]);
                            } else {
                              field.onChange(currentValue.filter((id) => id !== t.id));
                            }
                          }}
                          className="h-4 w-4 rounded border-gray-300"
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
                    Todos os inquilinos que morarão no apartamento (incluindo o responsável)
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

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
                        initialFocus
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
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* Cleaning Fee */}
            <FormField
              control={formMethods.control}
              name="cleaning_fee"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Taxa de Limpeza</FormLabel>
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

            {/* Due Day */}
            <FormField
              control={formMethods.control}
              name="due_day"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Dia de Vencimento</FormLabel>
                  <FormControl>
                    <Input
                      type="number"
                      min={1}
                      max={31}
                      placeholder="Ex: 10"
                      {...field}
                      onChange={(e) => field.onChange(Number(e.target.value))}
                    />
                  </FormControl>
                  <FormDescription>
                    Dia do mês para vencimento do aluguel
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            {selectedApartment && (
              <Card>
                <CardContent className="pt-6">
                  <div className="text-sm space-y-1">
                    <div className="font-medium mb-2">Resumo do Apartamento Selecionado:</div>
                    <div>• Prédio: {selectedApartment.building?.name}</div>
                    <div>• Apartamento: {selectedApartment.number}</div>
                    <div>• Aluguel: {formatCurrency(selectedApartment.rental_value)}</div>
                    <div>• Limpeza: {formatCurrency(selectedApartment.cleaning_fee)}</div>
                    <div>• Máx. Inquilinos: {selectedApartment.max_tenants}</div>
                    <div>• Móveis incluídos: {selectedApartment.furnitures?.length || 0}</div>
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
