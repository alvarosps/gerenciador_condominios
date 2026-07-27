'use client';

import { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { toast } from 'sonner';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useCreateBillWithLines } from '@/lib/api/hooks/use-bills';
import { useBuildings } from '@/lib/api/hooks/use-buildings';
import { useFinanceCategories } from '@/lib/api/hooks/use-finance-categories';
import { getErrorMessage, handleError } from '@/lib/utils/error-handler';
import { getTodayLocalISO } from '@/lib/utils/formatters';

const NONE = 'none';

const quickBillFormSchema = z.object({
  description: z.string().min(1, 'Descrição é obrigatória'),
  building_id: z.number().nullable(),
  category_id: z.number().nullable(),
  amount: z
    .string()
    .refine((v) => v !== '' && Number(v) > 0, { message: 'O valor deve ser maior que zero' }),
  due_date: z.string().min(1, 'Vencimento é obrigatório'),
});

type QuickBillFormValues = z.infer<typeof quickBillFormSchema>;

function defaultValues(): QuickBillFormValues {
  return {
    description: '',
    building_id: null,
    category_id: null,
    amount: '',
    due_date: getTodayLocalISO(),
  };
}

interface QuickBillDialogProps {
  open: boolean;
  onClose: () => void;
  /** Competence shown on the board — the created bill's `competence_month` (day 1). */
  year: number;
  month: number;
}

/** "+ Conta avulsa" (S75) — minimal form, `create_with_lines` with exactly 1 line. */
export function QuickBillDialog({ open, onClose, year, month }: QuickBillDialogProps) {
  const createWithLines = useCreateBillWithLines();
  const { data: buildings } = useBuildings();
  const { data: categories } = useFinanceCategories();

  const form = useForm<QuickBillFormValues>({
    resolver: zodResolver(quickBillFormSchema),
    defaultValues: defaultValues(),
  });

  useEffect(() => {
    if (open) {
      form.reset(defaultValues());
    }
  }, [open, form]);

  function handleSubmit(values: QuickBillFormValues) {
    const competenceMonth = `${String(year)}-${String(month).padStart(2, '0')}-01`;
    createWithLines.mutate(
      {
        bill: {
          description: values.description,
          building_id: values.building_id,
          due_date: values.due_date,
          competence_month: competenceMonth,
          behavior: 'one_time',
          ...(values.category_id !== null ? { category_id: values.category_id } : {}),
        },
        line_items: [
          {
            description: values.description,
            amount: Number(values.amount),
            is_offset: false,
            ...(values.category_id !== null ? { category_id: values.category_id } : {}),
          },
        ],
      },
      {
        onSuccess: () => {
          toast.success('Conta criada com sucesso');
          onClose();
        },
        onError: (error) => {
          toast.error(getErrorMessage(error, 'Erro ao criar conta'));
          handleError(error, 'Erro ao criar conta');
        },
      }
    );
  }

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Conta avulsa</DialogTitle>
          <DialogDescription>
            Lançamento rápido de uma conta avulsa com um único valor.
          </DialogDescription>
        </DialogHeader>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(handleSubmit)} noValidate className="space-y-4">
            <FormField
              control={form.control}
              name="description"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Descrição</FormLabel>
                  <FormControl>
                    <Input placeholder="Descrição da conta" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="building_id"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Prédio (opcional)</FormLabel>
                  <Select
                    value={field.value ? String(field.value) : NONE}
                    onValueChange={(value) => field.onChange(value === NONE ? null : Number(value))}
                  >
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue placeholder="Condomínio" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      <SelectItem value={NONE}>Condomínio (sem prédio)</SelectItem>
                      {buildings?.map((building) =>
                        building.id === undefined ? null : (
                          <SelectItem key={building.id} value={String(building.id)}>
                            {building.name}
                          </SelectItem>
                        )
                      )}
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="category_id"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Categoria (opcional)</FormLabel>
                  <Select
                    value={field.value ? String(field.value) : NONE}
                    onValueChange={(value) => field.onChange(value === NONE ? null : Number(value))}
                  >
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue placeholder="Selecione" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      <SelectItem value={NONE}>Nenhuma</SelectItem>
                      {categories?.map((category) =>
                        category.id === undefined ? null : (
                          <SelectItem key={category.id} value={String(category.id)}>
                            {category.name}
                          </SelectItem>
                        )
                      )}
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="amount"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Valor</FormLabel>
                  <FormControl>
                    <Input type="number" min={0} step="0.01" placeholder="0,00" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="due_date"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Vencimento</FormLabel>
                  <FormControl>
                    <Input type="date" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <DialogFooter>
              <Button type="button" variant="outline" onClick={onClose}>
                Cancelar
              </Button>
              <Button type="submit" disabled={createWithLines.isPending}>
                {createWithLines.isPending ? 'Criando...' : 'Criar'}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
