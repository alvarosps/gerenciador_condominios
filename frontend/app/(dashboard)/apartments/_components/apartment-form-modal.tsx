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
  FormDescription,
} from '@/components/ui/form';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Checkbox } from '@/components/ui/checkbox';
import { Separator } from '@/components/ui/separator';
import { toast } from 'sonner';
import { useCreateApartment, useUpdateApartment } from '@/lib/api/hooks/use-apartments';
import { useBuildings } from '@/lib/api/hooks/use-buildings';
import { useFurniture } from '@/lib/api/hooks/use-furniture';
import { type Apartment } from '@/lib/schemas/apartment.schema';

interface Props {
  open: boolean;
  apartment?: Apartment | null;
  onClose: () => void;
}

const apartmentFormSchema = z.object({
  building_id: z.number().min(1, 'Selecione um prédio'),
  number: z.number().min(1, 'Número deve ser positivo'),
  rental_value: z.number().min(0, 'Valor não pode ser negativo'),
  cleaning_fee: z.number().min(0, 'Valor não pode ser negativo'),
  max_tenants: z.number().min(1, 'Deve ter pelo menos 1 inquilino').max(10, 'Máximo 10 inquilinos'),
  furniture_ids: z.array(z.number()).optional(),
  last_rent_increase_date: z.string().optional(),
});

type ApartmentFormValues = z.infer<typeof apartmentFormSchema>;

export function ApartmentFormModal({ open, apartment, onClose }: Props) {
  const createMutation = useCreateApartment();
  const updateMutation = useUpdateApartment();
  const { data: buildings, isLoading: buildingsLoading } = useBuildings();
  const { data: furniture } = useFurniture();

  const formMethods = useForm<ApartmentFormValues>({
    resolver: zodResolver(apartmentFormSchema),
    defaultValues: {
      building_id: undefined,
      number: undefined,
      rental_value: undefined,
      cleaning_fee: undefined,
      max_tenants: undefined,
      furniture_ids: [],
      last_rent_increase_date: '',
    },
  });

  useEffect(() => {
    if (apartment) {
      formMethods.reset({
        building_id: apartment.building_id,
        number: apartment.number,
        rental_value: apartment.rental_value,
        cleaning_fee: apartment.cleaning_fee,
        max_tenants: apartment.max_tenants,
        furniture_ids: apartment.furnitures?.map((f) => f.id).filter((id): id is number => id !== undefined) ?? [],
        last_rent_increase_date: apartment.last_rent_increase_date ?? '',
      });
    } else {
      formMethods.reset();
    }
  }, [apartment, formMethods]);

  const onSubmit = async (values: ApartmentFormValues) => {
    try {
      if (apartment?.id) {
        await updateMutation.mutateAsync({
          ...values,
          id: apartment.id,
        });
        toast.success('Apartamento atualizado com sucesso');
      } else {
        await createMutation.mutateAsync(values);
        toast.success('Apartamento criado com sucesso');
      }

      onClose();
      formMethods.reset();
    } catch (error) {
      toast.error('Erro ao salvar apartamento');
      console.error('Save error:', error);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-3">
            {apartment ? 'Editar Apartamento' : 'Novo Apartamento'}
            {apartment && (
              <Badge
                variant={apartment.is_rented ? 'destructive' : 'default'}
                className={apartment.is_rented ? '' : 'bg-success text-success-foreground'}
              >
                {apartment.is_rented ? 'Alugado' : 'Disponível'}
              </Badge>
            )}
          </DialogTitle>
        </DialogHeader>

        <Form {...formMethods}>
          <form onSubmit={formMethods.handleSubmit(onSubmit)} className="space-y-4">
            {/* Building Selection */}
            <FormField
              control={formMethods.control}
              name="building_id"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Prédio *</FormLabel>
                  <Select
                    disabled={buildingsLoading}
                    onValueChange={(value) => field.onChange(Number(value))}
                    value={field.value ? String(field.value) : undefined}
                  >
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue placeholder="Selecione o prédio" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {buildings?.map((b) => (
                        <SelectItem key={b.id} value={String(b.id)}>
                          {b.name} - Nº {b.street_number}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* Apartment Number */}
            <FormField
              control={formMethods.control}
              name="number"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Número do Apartamento *</FormLabel>
                  <FormControl>
                    <Input
                      type="number"
                      placeholder="Ex: 101"
                      {...field}
                      value={field.value || ''}
                      onChange={(e) => field.onChange(e.target.value ? Number(e.target.value) : undefined)}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <Separator className="my-4" />
            <h3 className="text-sm font-medium">Valores</h3>

            {/* Rental Value */}
            <FormField
              control={formMethods.control}
              name="rental_value"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Valor do Aluguel *</FormLabel>
                  <FormControl>
                    <Input
                      type="number"
                      step="0.01"
                      placeholder="0.00"
                      {...field}
                      value={field.value || ''}
                      onChange={(e) => field.onChange(e.target.value ? Number(e.target.value) : undefined)}
                    />
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
                  <FormLabel>Taxa de Limpeza *</FormLabel>
                  <FormControl>
                    <Input
                      type="number"
                      step="0.01"
                      placeholder="0.00"
                      {...field}
                      value={field.value || ''}
                      onChange={(e) => field.onChange(e.target.value ? Number(e.target.value) : undefined)}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* Max Tenants */}
            <FormField
              control={formMethods.control}
              name="max_tenants"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Máximo de Inquilinos *</FormLabel>
                  <FormControl>
                    <Input
                      type="number"
                      placeholder="Ex: 2"
                      {...field}
                      value={field.value || ''}
                      onChange={(e) => field.onChange(e.target.value ? Number(e.target.value) : undefined)}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <Separator className="my-4" />
            <h3 className="text-sm font-medium">Móveis do Apartamento</h3>

            {/* Furniture Selection */}
            <FormField
              control={formMethods.control}
              name="furniture_ids"
              render={() => (
                <FormItem>
                  <FormLabel>Móveis Incluídos</FormLabel>
                  <FormDescription>Selecione os móveis que já estão no apartamento</FormDescription>
                  <div className="grid grid-cols-2 gap-4 mt-2">
                    {furniture?.map((item) => (
                      <FormField
                        key={item.id}
                        control={formMethods.control}
                        name="furniture_ids"
                        render={({ field }) => (
                          <FormItem className="flex flex-row items-start space-x-3 space-y-0">
                            <FormControl>
                              <Checkbox
                                checked={item.id !== undefined && field.value?.includes(item.id)}
                                onCheckedChange={(checked) => {
                                  const current = field.value ?? [];
                                  if (checked && item.id !== undefined) {
                                    field.onChange([...current, item.id]);
                                  } else {
                                    field.onChange(current.filter((id) => id !== item.id));
                                  }
                                }}
                              />
                            </FormControl>
                            <FormLabel className="font-normal">{item.name}</FormLabel>
                          </FormItem>
                        )}
                      />
                    ))}
                  </div>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={formMethods.control}
              name="last_rent_increase_date"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Último Reajuste</FormLabel>
                  <FormControl>
                    <Input type="date" {...field} value={field.value ?? ''} />
                  </FormControl>
                  <FormDescription>Data do último reajuste de aluguel</FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <DialogFooter>
              <Button type="button" variant="outline" onClick={onClose}>
                Cancelar
              </Button>
              <Button
                type="submit"
                disabled={createMutation.isPending || updateMutation.isPending}
              >
                {apartment ? 'Atualizar' : 'Criar'}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
