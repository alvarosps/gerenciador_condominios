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
import { toast } from 'sonner';
import {
  useCreateExpenseCategory,
  useUpdateExpenseCategory,
  useExpenseCategories,
} from '@/lib/api/hooks/use-expense-categories';
import { type ExpenseCategory } from '@/lib/schemas/expense-category.schema';
import { handleError } from '@/lib/utils/error-handler';

interface CategoryFormModalProps {
  open: boolean;
  category?: ExpenseCategory | null;
  onClose: () => void;
}

const categoryFormSchema = z.object({
  name: z.string().min(1, 'Nome é obrigatório'),
  description: z.string(),
  color: z.string().min(1, 'Cor é obrigatória'),
  parent_id: z.number().nullable(),
});

type CategoryFormValues = z.infer<typeof categoryFormSchema>;

export function CategoryFormModal({ open, category, onClose }: CategoryFormModalProps) {
  const createMutation = useCreateExpenseCategory();
  const updateMutation = useUpdateExpenseCategory();
  const { data: allCategories } = useExpenseCategories();

  const isEditing = Boolean(category?.id);
  const isLoading = createMutation.isPending || updateMutation.isPending;

  const topLevelCategories = (allCategories ?? []).filter(
    (cat) => !cat.parent && cat.id !== category?.id,
  );

  const formMethods = useForm<CategoryFormValues>({
    resolver: zodResolver(categoryFormSchema),
    defaultValues: {
      name: '',
      description: '',
      color: '#6B7280',
      parent_id: null,
    },
  });

  useEffect(() => {
    if (category) {
      formMethods.reset({
        name: category.name,
        description: category.description ?? '',
        color: category.color ?? '#6B7280',
        parent_id: category.parent_id ?? null,
      });
    } else {
      formMethods.reset({
        name: '',
        description: '',
        color: '#6B7280',
        parent_id: null,
      });
    }
  }, [category, formMethods]);

  const parentId = formMethods.watch('parent_id');

  useEffect(() => {
    if (parentId && !isEditing) {
      const parentCategory = topLevelCategories.find((cat) => cat.id === parentId);
      if (parentCategory?.color) {
        formMethods.setValue('color', parentCategory.color);
      }
    }
  }, [parentId, topLevelCategories, isEditing, formMethods]);

  const onSubmit = async (values: CategoryFormValues) => {
    try {
      const payload = {
        name: values.name,
        description: values.description ?? '',
        color: values.color,
        parent_id: values.parent_id ?? null,
      };

      if (isEditing && category?.id) {
        await updateMutation.mutateAsync({ ...payload, id: category.id });
        toast.success('Categoria atualizada com sucesso');
      } else {
        await createMutation.mutateAsync(payload);
        toast.success('Categoria criada com sucesso');
      }

      onClose();
      formMethods.reset();
    } catch (error) {
      toast.error('Erro ao salvar categoria');
      handleError(error, 'CategoryFormModal.onSubmit');
    }
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>{isEditing ? 'Editar Categoria' : 'Nova Categoria'}</DialogTitle>
        </DialogHeader>

        <Form {...formMethods}>
          <form onSubmit={formMethods.handleSubmit(onSubmit)} className="space-y-4">
            <FormField
              control={formMethods.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Nome *</FormLabel>
                  <FormControl>
                    <Input placeholder="Ex: Manutenção" maxLength={100} {...field} disabled={isLoading} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={formMethods.control}
              name="description"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Descrição</FormLabel>
                  <FormControl>
                    <Textarea
                      rows={2}
                      placeholder="Descrição da categoria..."
                      {...field}
                      disabled={isLoading}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={formMethods.control}
              name="color"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Cor</FormLabel>
                  <FormControl>
                    <div className="flex items-center gap-3">
                      <Input type="color" className="w-16 h-10 p-1 cursor-pointer" {...field} disabled={isLoading} />
                      <Input
                        placeholder="#6B7280"
                        maxLength={7}
                        {...field}
                        disabled={isLoading}
                        className="flex-1"
                      />
                    </div>
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={formMethods.control}
              name="parent_id"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Categoria Pai</FormLabel>
                  <Select
                    onValueChange={(val) => field.onChange(val === 'none' ? null : Number(val))}
                    value={field.value ? String(field.value) : 'none'}
                    disabled={isLoading}
                  >
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue placeholder="Nenhuma (categoria principal)" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      <SelectItem value="none">Nenhuma (categoria principal)</SelectItem>
                      {topLevelCategories.map((cat) => (
                        <SelectItem key={cat.id} value={String(cat.id)}>
                          {cat.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
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
