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
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { toast } from 'sonner';
import {
  useCreateBuilding,
  useUpdateBuilding,
} from '@/lib/api/hooks/use-buildings';
import { Building } from '@/lib/schemas/building.schema';

interface BuildingFormModalProps {
  open: boolean;
  building?: Building | null;
  onClose: () => void;
}

const buildingFormSchema = z.object({
  street_number: z.number().min(1, 'O número deve ser maior que zero'),
  name: z.string().min(1, 'O nome deve ter pelo menos 1 caractere').max(200, 'O nome deve ter no máximo 200 caracteres'),
  address: z.string().min(1, 'O endereço deve ter pelo menos 1 caractere').max(500, 'O endereço deve ter no máximo 500 caracteres'),
});

type BuildingFormValues = z.infer<typeof buildingFormSchema>;

export function BuildingFormModal({
  open,
  building,
  onClose,
}: BuildingFormModalProps) {
  const createMutation = useCreateBuilding();
  const updateMutation = useUpdateBuilding();

  const isEditing = !!building?.id;
  const isLoading = createMutation.isPending || updateMutation.isPending;

  const formMethods = useForm<BuildingFormValues>({
    resolver: zodResolver(buildingFormSchema),
    defaultValues: {
      street_number: undefined,
      name: '',
      address: '',
    },
  });

  useEffect(() => {
    if (building) {
      formMethods.reset({
        street_number: building.street_number,
        name: building.name,
        address: building.address,
      });
    } else {
      formMethods.reset();
    }
  }, [building, formMethods]);

  const onSubmit = async (values: BuildingFormValues) => {
    try {
      if (isEditing && building?.id) {
        await updateMutation.mutateAsync({ ...values, id: building.id });
        toast.success('Prédio atualizado com sucesso');
      } else {
        await createMutation.mutateAsync(values);
        toast.success('Prédio criado com sucesso');
      }

      onClose();
      formMethods.reset();
    } catch (error) {
      toast.error('Erro ao salvar prédio');
      console.error('Save error:', error);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>
            {isEditing ? 'Editar Prédio' : 'Novo Prédio'}
          </DialogTitle>
        </DialogHeader>

        <Form {...formMethods}>
          <form onSubmit={formMethods.handleSubmit(onSubmit)} className="space-y-4">
            <FormField
              control={formMethods.control}
              name="street_number"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Número da Rua *</FormLabel>
                  <FormControl>
                    <Input
                      type="number"
                      placeholder="Ex: 836"
                      {...field}
                      value={field.value || ''}
                      onChange={(e) => field.onChange(e.target.value ? Number(e.target.value) : undefined)}
                      disabled={isLoading}
                    />
                  </FormControl>
                  <FormDescription>Número identificador do prédio na rua</FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={formMethods.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Nome do Prédio *</FormLabel>
                  <FormControl>
                    <Input
                      placeholder="Ex: Edifício Central"
                      maxLength={200}
                      {...field}
                      disabled={isLoading}
                    />
                  </FormControl>
                  <FormDescription>Nome ou identificação do prédio</FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={formMethods.control}
              name="address"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Endereço Completo *</FormLabel>
                  <FormControl>
                    <Textarea
                      rows={3}
                      placeholder="Ex: Rua das Flores, 836 - Centro - São Paulo/SP"
                      maxLength={500}
                      {...field}
                      disabled={isLoading}
                    />
                  </FormControl>
                  <FormDescription>Endereço completo do prédio</FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <DialogFooter>
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
