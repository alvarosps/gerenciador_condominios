'use client';

import { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { type z } from 'zod';
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
import { Checkbox } from '@/components/ui/checkbox';
import { Card, CardContent } from '@/components/ui/card';
import { TrendingUp } from 'lucide-react';
import { toast } from 'sonner';
import { useApplyRentAdjustment } from '@/lib/api/hooks/use-rent-adjustments';
import { type Lease } from '@/lib/schemas/lease.schema';
import { rentAdjustmentFormSchema } from '@/lib/schemas/rent-adjustment.schema';
import { formatCurrency } from '@/lib/utils/formatters';

interface Props {
  open: boolean;
  lease: Lease | null;
  onClose: () => void;
}

type FormValues = z.input<typeof rentAdjustmentFormSchema>;

export function RentAdjustmentModal({ open, lease, onClose }: Props) {
  const applyMutation = useApplyRentAdjustment();

  const formMethods = useForm<FormValues>({
    resolver: zodResolver(rentAdjustmentFormSchema),
    defaultValues: {
      percentage: 0,
      update_apartment_prices: true,
    },
  });

  const percentage = formMethods.watch('percentage') ?? 0;
  const currentValue = lease?.rental_value ?? 0;
  const newValue = percentage !== 0 ? currentValue * (1 + percentage / 100) : currentValue;

  useEffect(() => {
    if (open) {
      formMethods.reset({ percentage: 0, update_apartment_prices: true });
    }
  }, [open, formMethods]);

  const handleClose = () => {
    formMethods.reset();
    onClose();
  };

  const onSubmit = async (values: FormValues) => {
    if (!lease?.id) return;

    try {
      const result = await applyMutation.mutateAsync({
        leaseId: lease.id,
        percentage: values.percentage,
        update_apartment_prices: values.update_apartment_prices ?? true,
      });

      toast.success('Reajuste aplicado com sucesso!');

      if (result.warning) {
        toast.warning(`Atenção: aluguel pré-pago registrado até ${result.warning.last_date}`);
      }

      handleClose();
    } catch {
      toast.error('Erro ao aplicar reajuste');
    }
  };

  if (!lease) return null;

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Reajustar Aluguel</DialogTitle>
        </DialogHeader>

        <Form {...formMethods}>
          <form onSubmit={formMethods.handleSubmit(onSubmit)} className="space-y-4">
            <Card>
              <CardContent className="pt-4">
                <dl className="space-y-2">
                  <div className="flex justify-between py-1 border-b">
                    <dt className="text-sm text-muted-foreground">Apartamento</dt>
                    <dd className="text-sm font-medium">
                      {lease.apartment?.building?.name} — Apto {lease.apartment?.number}
                    </dd>
                  </div>
                  <div className="flex justify-between py-1">
                    <dt className="text-sm text-muted-foreground">Inquilino</dt>
                    <dd className="text-sm font-medium">{lease.responsible_tenant?.name}</dd>
                  </div>
                </dl>
              </CardContent>
            </Card>

            <FormField
              control={formMethods.control}
              name="percentage"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Percentual (%)</FormLabel>
                  <FormControl>
                    <Input
                      type="number"
                      step="0.01"
                      placeholder="Ex: 5.00"
                      {...field}
                      value={field.value === 0 ? '' : field.value}
                      onChange={(e) => field.onChange(e.target.value ? Number(e.target.value) : 0)}
                      disabled={applyMutation.isPending}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <Card className="border-muted bg-muted/30">
              <CardContent className="pt-4 pb-3">
                <div className="space-y-1">
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Valor atual:</span>
                    <span>{formatCurrency(currentValue)}</span>
                  </div>
                  <div className="flex justify-between text-sm font-medium">
                    <span className="text-muted-foreground">Valor novo:</span>
                    <span
                      className={
                        newValue > currentValue
                          ? 'text-success'
                          : newValue < currentValue
                            ? 'text-destructive'
                            : ''
                      }
                    >
                      {formatCurrency(newValue)}
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>

            <FormField
              control={formMethods.control}
              name="update_apartment_prices"
              render={({ field }) => (
                <FormItem className="flex items-center gap-2 space-y-0">
                  <FormControl>
                    <Checkbox
                      checked={field.value ?? true}
                      onCheckedChange={field.onChange}
                      disabled={applyMutation.isPending}
                    />
                  </FormControl>
                  <FormLabel className="font-normal cursor-pointer">
                    Atualizar preço de tabela do apartamento
                  </FormLabel>
                </FormItem>
              )}
            />

            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={handleClose}
                disabled={applyMutation.isPending}
              >
                Cancelar
              </Button>
              <Button type="submit" disabled={applyMutation.isPending}>
                <TrendingUp className="h-4 w-4 mr-2" />
                {applyMutation.isPending ? 'Aplicando...' : 'Aplicar Reajuste'}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
