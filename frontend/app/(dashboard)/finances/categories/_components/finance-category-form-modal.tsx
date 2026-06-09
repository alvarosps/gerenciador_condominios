'use client';

import { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import {
  Dialog,
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { toast } from 'sonner';
import {
  useCreateFinanceCategory,
  useFinanceCategories,
  useUpdateFinanceCategory,
} from '@/lib/api/hooks/use-finance-categories';
import { type FinanceCategory } from '@/lib/schemas/finances/category.schema';
import { handleError } from '@/lib/utils/error-handler';

interface FinanceCategoryFormModalProps {
  open: boolean;
  category?: FinanceCategory | null;
  onClose: () => void;
}

const financeCategoryFormSchema = z.object({
  name: z.string().min(1, 'Nome é obrigatório'),
  color: z.string(),
  sort_order: z.number().int().min(0),
  parent_id: z.number().nullable(),
});

type FinanceCategoryFormValues = z.infer<typeof financeCategoryFormSchema>;

const DEFAULTS: FinanceCategoryFormValues = {
  name: '',
  color: '#6B7280',
  sort_order: 0,
  parent_id: null,
};

export function FinanceCategoryFormModal({
  open,
  category,
  onClose,
}: FinanceCategoryFormModalProps) {
  const createMutation = useCreateFinanceCategory();
  const updateMutation = useUpdateFinanceCategory();
  const { data: allCategories } = useFinanceCategories();

  const isEditing = Boolean(category?.id);
  const isLoading = createMutation.isPending || updateMutation.isPending;

  // Only root categories can be a parent (one level), and never the category being edited itself.
  const parentOptions = (allCategories ?? []).filter(
    (cat) => !cat.parent && cat.id !== category?.id,
  );

  const formMethods = useForm<FinanceCategoryFormValues>({
    resolver: zodResolver(financeCategoryFormSchema),
    defaultValues: DEFAULTS,
  });

  useEffect(() => {
    formMethods.reset(
      category
        ? {
            name: category.name,
            color: category.color ?? '#6B7280',
            sort_order: category.sort_order ?? 0,
            parent_id: category.parent_id ?? category.parent?.id ?? null,
          }
        : DEFAULTS,
    );
  }, [category, formMethods]);

  const onSubmit = async (values: FinanceCategoryFormValues) => {
    try {
      const payload = {
        name: values.name,
        color: values.color,
        sort_order: values.sort_order,
        parent_id: values.parent_id,
      };
      if (isEditing && category?.id) {
        await updateMutation.mutateAsync({ ...payload, id: category.id });
        toast.success('Categoria atualizada com sucesso');
      } else {
        await createMutation.mutateAsync(payload);
        toast.success('Categoria criada com sucesso');
      }
      onClose();
      formMethods.reset(DEFAULTS);
    } catch (error) {
      toast.error('Erro ao salvar categoria');
      handleError(error, 'FinanceCategoryFormModal.onSubmit');
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
                    <Input
                      placeholder="Ex: Serviços/Utilidades"
                      maxLength={100}
                      {...field}
                      disabled={isLoading}
                    />
                  </FormControl>
                  <FormDescription>
                    Classificação opcional das contas (distinta do &quot;Tipo de conta&quot;
                    Água/Luz/IPTU).
                  </FormDescription>
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
                      <Input
                        type="color"
                        className="h-10 w-16 cursor-pointer p-1"
                        {...field}
                        disabled={isLoading}
                      />
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
              name="sort_order"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Ordem</FormLabel>
                  <FormControl>
                    <Input
                      type="number"
                      min={0}
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
                      {parentOptions.map((cat) =>
                        cat.id === undefined ? null : (
                          <SelectItem key={cat.id} value={String(cat.id)}>
                            {cat.name}
                          </SelectItem>
                        ),
                      )}
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
