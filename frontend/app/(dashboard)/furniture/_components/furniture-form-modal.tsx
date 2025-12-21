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
import { toast } from 'sonner';
import {
  useCreateFurniture,
  useUpdateFurniture,
} from '@/lib/api/hooks/use-furniture';
import { Furniture } from '@/lib/schemas/furniture.schema';

interface FurnitureFormModalProps {
  open: boolean;
  furniture?: Furniture | null;
  onClose: () => void;
}

const furnitureFormSchema = z.object({
  name: z.string().min(1, 'O nome deve ter pelo menos 1 caractere').max(200, 'O nome deve ter no máximo 200 caracteres'),
});

type FurnitureFormValues = z.infer<typeof furnitureFormSchema>;

export function FurnitureFormModal({
  open,
  furniture,
  onClose,
}: FurnitureFormModalProps) {
  const createMutation = useCreateFurniture();
  const updateMutation = useUpdateFurniture();

  const isEditing = !!furniture?.id;
  const isLoading = createMutation.isPending || updateMutation.isPending;

  const formMethods = useForm<FurnitureFormValues>({
    resolver: zodResolver(furnitureFormSchema),
    defaultValues: {
      name: '',
    },
  });

  useEffect(() => {
    if (furniture) {
      formMethods.reset({
        name: furniture.name,
      });
    } else {
      formMethods.reset();
    }
  }, [furniture, formMethods]);

  const onSubmit = async (values: FurnitureFormValues) => {
    try {
      if (isEditing && furniture?.id) {
        await updateMutation.mutateAsync({ ...values, id: furniture.id });
        toast.success('Móvel atualizado com sucesso');
      } else {
        await createMutation.mutateAsync(values);
        toast.success('Móvel criado com sucesso');
      }

      onClose();
      formMethods.reset();
    } catch (error) {
      toast.error('Erro ao salvar móvel');
      console.error('Save error:', error);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>
            {isEditing ? 'Editar Móvel' : 'Novo Móvel'}
          </DialogTitle>
        </DialogHeader>

        <Form {...formMethods}>
          <form onSubmit={formMethods.handleSubmit(onSubmit)} className="space-y-4">
            <FormField
              control={formMethods.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Nome do Móvel *</FormLabel>
                  <FormControl>
                    <Input
                      placeholder="Ex: Sofá, Cama, Mesa"
                      maxLength={200}
                      {...field}
                      disabled={isLoading}
                    />
                  </FormControl>
                  <FormDescription>Nome ou descrição do móvel</FormDescription>
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
