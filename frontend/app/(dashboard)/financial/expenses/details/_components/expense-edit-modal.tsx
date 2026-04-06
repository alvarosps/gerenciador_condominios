'use client';

import { useState, useEffect } from 'react';
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
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
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
import { Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { useExpenseCategories } from '@/lib/api/hooks/use-expense-categories';
import { useCreditCards } from '@/lib/api/hooks/use-credit-cards';
import { useBuildings } from '@/lib/api/hooks/use-buildings';
import { getDefaultExpenseDate } from '@/lib/utils/formatters';
import { apiClient } from '@/lib/api/client';
import type { ExpenseDetailItem } from '@/lib/api/hooks/use-financial-dashboard';

const EXPENSE_TYPE_OPTIONS = [
  { value: 'card_purchase', label: 'Compra no Cartão' },
  { value: 'bank_loan', label: 'Empréstimo Bancário' },
  { value: 'personal_loan', label: 'Empréstimo Pessoal' },
  { value: 'fixed_expense', label: 'Despesa Fixa' },
  { value: 'one_time_expense', label: 'Gasto Único' },
  { value: 'water_bill', label: 'Conta de Água' },
  { value: 'electricity_bill', label: 'Conta de Luz' },
  { value: 'property_tax', label: 'IPTU' },
] as const;

const INSTALLMENT_TYPES = ['card_purchase', 'bank_loan', 'personal_loan'];

const formSchema = z.object({
  description: z.string().min(1, 'Descrição é obrigatória'),
  amount: z.number().positive('Valor deve ser positivo'),
  category_id: z.number().nullable(),
  subcategory_id: z.number().nullable(),
  notes: z.string(),
  expense_type: z.string(),
  expense_date: z.string(),
  credit_card_id: z.number().nullable(),
  building_id: z.number().nullable(),
  is_installment: z.boolean(),
  total_installments: z.number().min(1).nullable(),
  current_installment: z.number().min(1).nullable(),
  is_offset: z.boolean(),
});

type FormValues = z.infer<typeof formSchema>;

interface EditProps {
  mode: 'edit';
  item: ExpenseDetailItem;
  personId?: number | null;
  detailType?: string;
  defaultExpenseDate?: string;
  onClose: () => void;
  onSaved: () => void;
}

interface CreateProps {
  mode: 'create';
  item?: undefined;
  personId?: number | null;
  detailType?: string;
  defaultExpenseDate?: string;
  onClose: () => void;
  onSaved: () => void;
}

type Props = EditProps | CreateProps;

const DETAIL_TYPE_TO_EXPENSE_TYPE: Record<string, string> = {
  electricity: 'electricity_bill',
  water: 'water_bill',
  iptu: 'property_tax',
};

const BUILDING_REQUIRED_TYPES = ['water_bill', 'electricity_bill', 'property_tax'];

export function ExpenseEditModal({ mode, item, personId, detailType, defaultExpenseDate, onClose, onSaved }: Props) {
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [pendingValues, setPendingValues] = useState<FormValues | null>(null);

  const { data: categories, isLoading: categoriesLoading } = useExpenseCategories();
  const { data: allCreditCards } = useCreditCards();
  const { data: buildings } = useBuildings();

  const isCreate = mode === 'create';
  const presetExpenseType = detailType ? (DETAIL_TYPE_TO_EXPENSE_TYPE[detailType] ?? '') : '';

  const filteredCreditCards = allCreditCards?.filter(
    (card) => card.person?.id === personId
  ) ?? [];

  const form = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      description: '',
      amount: 0,
      category_id: null,
      subcategory_id: null,
      notes: '',
      expense_type: presetExpenseType,
      expense_date: defaultExpenseDate ?? getDefaultExpenseDate(new Date().getFullYear(), new Date().getMonth() + 1),
      credit_card_id: null,
      building_id: null,
      is_installment: false,
      total_installments: null,
      current_installment: null,
      is_offset: false,
    },
  });

  const watchedCategoryId = form.watch('category_id');
  const watchedExpenseType = form.watch('expense_type');
  const watchedIsInstallment = form.watch('is_installment');
  const hasInstallment = item?.installment_id !== null && item?.installment_id !== undefined;
  const showInstallmentFields =
    (isCreate && INSTALLMENT_TYPES.includes(watchedExpenseType)) || (!isCreate && hasInstallment);
  const showCreditCardField = isCreate && watchedExpenseType === 'card_purchase';
  const showBuildingField = isCreate && BUILDING_REQUIRED_TYPES.includes(watchedExpenseType);

  // Top-level categories have no parent (parent is null/undefined, not a number or object)
  const topLevelCategories =
    categories?.filter((cat) => !cat.parent && !cat.parent_id) ?? [];

  const subcategories =
    watchedCategoryId !== null
      ? (categories?.find((cat) => cat.id === watchedCategoryId)?.subcategories ?? [])
      : [];

  useEffect(() => {
    if (item) {
      form.reset({
        description: item.description,
        amount: item.amount,
        category_id: item.category_id ?? null,
        subcategory_id: item.subcategory_id ?? null,
        notes: item.notes ?? '',
        expense_type: presetExpenseType,
        expense_date: '',
        credit_card_id: null,
        building_id: null,
        is_installment: hasInstallment,
        total_installments: item.total_installments ?? null,
        current_installment: item.installment_number ?? null,
        is_offset: false,
      });
    } else if (isCreate) {
      form.reset({
        description: '',
        amount: 0,
        category_id: null,
        subcategory_id: null,
        notes: '',
        expense_type: presetExpenseType,
        expense_date: defaultExpenseDate ?? getDefaultExpenseDate(new Date().getFullYear(), new Date().getMonth() + 1),
        credit_card_id: null,
        building_id: null,
        is_installment: false,
        total_installments: null,
        current_installment: null,
        is_offset: false,
      });
    }
  }, [item, isCreate, form, hasInstallment, defaultExpenseDate, presetExpenseType]);

  useEffect(() => {
    form.setValue('subcategory_id', null);
  }, [watchedCategoryId, form]);

  const handleSubmit = (values: FormValues) => {
    setPendingValues(values);
    setConfirmOpen(true);
  };

  const handleConfirmSave = async () => {
    if (!pendingValues) return;

    setIsSaving(true);
    try {
      const effectiveCategoryId = pendingValues.subcategory_id ?? pendingValues.category_id;
      const totalParcelas = pendingValues.total_installments ?? 1;
      const isParcelado = pendingValues.is_installment && totalParcelas > 0;
      const parcelaAmount = pendingValues.amount;
      const totalAmount = isParcelado
        ? Math.round(parcelaAmount * totalParcelas * 100) / 100
        : parcelaAmount;

      if (isCreate) {
        // === CREATE ===
        const isFixed = pendingValues.expense_type === 'fixed_expense';

        const { data: created } = await apiClient.post<{ id: number }>('/expenses/', {
          description: pendingValues.description,
          total_amount: totalAmount,
          expense_type: pendingValues.expense_type,
          expense_date: pendingValues.expense_date,
          category_id: effectiveCategoryId,
          person_id: personId ?? null,
          credit_card_id: pendingValues.credit_card_id,
          building_id: pendingValues.building_id,
          notes: pendingValues.notes,
          is_installment: isParcelado,
          total_installments: isParcelado ? totalParcelas : null,
          is_recurring: isFixed,
          expected_monthly_amount: isFixed ? parcelaAmount : null,
          is_offset: pendingValues.is_offset,
        });

        if (isParcelado) {
          const currentInst = pendingValues.current_installment ?? 1;
          const startDate = new Date(pendingValues.expense_date);

          for (let i = 1; i <= totalParcelas; i++) {
            const dueDate = new Date(startDate);
            dueDate.setMonth(dueDate.getMonth() + (i - currentInst));
            const dueDateStr = dueDate.toISOString().split('T')[0] ?? '';

            await apiClient.post('/expense-installments/', {
              expense: created.id,
              installment_number: i,
              total_installments: totalParcelas,
              amount: parcelaAmount,
              due_date: dueDateStr,
              is_paid: i < currentInst,
              paid_date: i < currentInst ? dueDateStr : null,
            });
          }
        }

        toast.success('Despesa criada com sucesso');
      } else {
        // === EDIT: single API call to overwrite expense + rebuild installments ===
        if (!item) return;
        const expenseId = item.expense_id;
        const expenseDate = item.due_date ?? new Date().toISOString().split('T')[0] ?? '';

        // Build installments array for the rebuild endpoint
        const installments: Record<string, unknown>[] = [];
        if (isParcelado) {
          const currentInst = pendingValues.current_installment ?? 1;
          const startDate = new Date(expenseDate);

          for (let i = 1; i <= totalParcelas; i++) {
            const dueDate = new Date(startDate);
            dueDate.setMonth(dueDate.getMonth() + (i - currentInst));
            const dueDateStr = dueDate.toISOString().split('T')[0] ?? '';

            installments.push({
              installment_number: i,
              total_installments: totalParcelas,
              amount: parcelaAmount,
              due_date: dueDateStr,
              is_paid: i < currentInst,
              paid_date: i < currentInst ? dueDateStr : null,
            });
          }
        }

        await apiClient.post(`/expenses/${expenseId}/rebuild/`, {
          description: pendingValues.description,
          total_amount: totalAmount,
          category_id: effectiveCategoryId,
          notes: pendingValues.notes,
          is_installment: isParcelado,
          total_installments: isParcelado ? totalParcelas : null,
          is_offset: pendingValues.is_offset,
          installments,
        });

        toast.success('Despesa atualizada com sucesso');
      }

      setConfirmOpen(false);
      onSaved();
      onClose();
    } catch {
      toast.error(isCreate ? 'Erro ao criar despesa' : 'Erro ao salvar alterações');
    } finally {
      setIsSaving(false);
    }
  };

  const handleClose = () => {
    form.reset();
    onClose();
  };

  const isOpen = isCreate || item !== undefined;

  return (
    <>
      <Dialog open={isOpen} onOpenChange={(open) => { if (!open) handleClose(); }}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>{isCreate ? 'Nova Despesa' : 'Editar Despesa'}</DialogTitle>
          </DialogHeader>

          <Form {...form}>
            <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-4">
              {/* Expense type - only for creation, hidden when preset from detail type */}
              {isCreate && !presetExpenseType && (
                <FormField
                  control={form.control}
                  name="expense_type"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Tipo de Despesa</FormLabel>
                      <Select value={field.value} onValueChange={field.onChange}>
                        <FormControl>
                          <SelectTrigger>
                            <SelectValue placeholder="Selecione o tipo" />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          {EXPENSE_TYPE_OPTIONS.map((opt) => (
                            <SelectItem key={opt.value} value={opt.value}>
                              {opt.label}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              )}

              <FormField
                control={form.control}
                name="description"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Descrição</FormLabel>
                    <FormControl>
                      <Input placeholder="Descrição da despesa" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="amount"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>{showInstallmentFields ? 'Valor da Parcela' : 'Valor'}</FormLabel>
                    <FormControl>
                      <div className="relative">
                        <span className="absolute left-3 top-1/2 -translate-y-1/2 text-sm text-muted-foreground">
                          R$
                        </span>
                        <Input
                          type="number"
                          min={0.01}
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

              {/* Date - only for creation */}
              {isCreate && (
                <FormField
                  control={form.control}
                  name="expense_date"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Data</FormLabel>
                      <FormControl>
                        <Input type="date" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              )}

              {/* Credit card field for card_purchase */}
              {showCreditCardField && (
                <FormField
                  control={form.control}
                  name="credit_card_id"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Cartão de Crédito</FormLabel>
                      <Select
                        value={field.value ? String(field.value) : 'none'}
                        onValueChange={(value) => field.onChange(value === 'none' ? null : Number(value))}
                      >
                        <FormControl>
                          <SelectTrigger>
                            <SelectValue placeholder="Selecione o cartão" />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          <SelectItem value="none">Nenhum</SelectItem>
                          {filteredCreditCards.map((card) => (
                            <SelectItem key={card.id} value={String(card.id)}>
                              {card.nickname} (****{card.last_four_digits})
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              )}

              {/* Building field for utility types */}
              {showBuildingField && (
                <FormField
                  control={form.control}
                  name="building_id"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Prédio</FormLabel>
                      <Select
                        value={field.value ? String(field.value) : 'none'}
                        onValueChange={(value) => field.onChange(value === 'none' ? null : Number(value))}
                      >
                        <FormControl>
                          <SelectTrigger>
                            <SelectValue placeholder="Selecione o prédio" />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          <SelectItem value="none">Nenhum</SelectItem>
                          {buildings?.map((b) => (
                            <SelectItem key={b.id} value={String(b.id)}>
                              {b.name}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              )}

              {/* Offset (discount) toggle */}
              <FormField
                control={form.control}
                name="is_offset"
                render={({ field }) => (
                  <FormItem className="flex items-center gap-2 space-y-0">
                    <FormControl>
                      <input
                        type="checkbox"
                        checked={field.value}
                        onChange={field.onChange}
                        className="h-4 w-4 rounded border-border"
                      />
                    </FormControl>
                    <FormLabel className="font-normal">
                      Desconto (compra para outra pessoa)
                    </FormLabel>
                  </FormItem>
                )}
              />

              {/* Installment fields for card/loan types */}
              {showInstallmentFields && (
                <>
                  <FormField
                    control={form.control}
                    name="is_installment"
                    render={({ field }) => (
                      <FormItem className="flex items-center gap-2 space-y-0">
                        <FormControl>
                          <input
                            type="checkbox"
                            checked={field.value}
                            onChange={field.onChange}
                            className="h-4 w-4 rounded border-border"
                          />
                        </FormControl>
                        <FormLabel className="font-normal">Parcelado</FormLabel>
                      </FormItem>
                    )}
                  />

                  {watchedIsInstallment && (
                    <div className="grid grid-cols-2 gap-3">
                      <FormField
                        control={form.control}
                        name="current_installment"
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel>Parcela Atual</FormLabel>
                            <FormControl>
                              <Input
                                type="number"
                                min={1}
                                placeholder="Ex: 1"
                                {...field}
                                value={field.value ?? ''}
                                onChange={(e) => field.onChange(e.target.value ? Number(e.target.value) : null)}
                              />
                            </FormControl>
                            <FormMessage />
                          </FormItem>
                        )}
                      />
                      <FormField
                        control={form.control}
                        name="total_installments"
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel>Total de Parcelas</FormLabel>
                            <FormControl>
                              <Input
                                type="number"
                                min={1}
                                placeholder="Ex: 12"
                                {...field}
                                value={field.value ?? ''}
                                onChange={(e) => field.onChange(e.target.value ? Number(e.target.value) : null)}
                              />
                            </FormControl>
                            <FormMessage />
                          </FormItem>
                        )}
                      />
                    </div>
                  )}
                </>
              )}

              <FormField
                control={form.control}
                name="category_id"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Categoria (opcional)</FormLabel>
                    <Select
                      value={field.value !== null ? String(field.value) : 'none'}
                      disabled={categoriesLoading}
                      onValueChange={(value) =>
                        field.onChange(value === 'none' ? null : Number(value))
                      }
                    >
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue placeholder={categoriesLoading ? 'Carregando...' : 'Selecione'} />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        <SelectItem value="none">Nenhuma</SelectItem>
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

              <FormField
                control={form.control}
                name="subcategory_id"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Subcategoria (opcional)</FormLabel>
                    <Select
                      value={field.value !== null ? String(field.value) : 'none'}
                      onValueChange={(value) =>
                        field.onChange(value === 'none' ? null : Number(value))
                      }
                      disabled={watchedCategoryId === null || subcategories.length === 0}
                    >
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue
                            placeholder={
                              watchedCategoryId === null
                                ? 'Selecione uma categoria primeiro'
                                : 'Selecione'
                            }
                          />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        <SelectItem value="none">Nenhuma</SelectItem>
                        {subcategories.map((sub) => (
                          <SelectItem key={sub.id} value={String(sub.id)}>
                            {sub.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="notes"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Observações (opcional)</FormLabel>
                    <FormControl>
                      <Textarea placeholder="Notas adicionais..." rows={3} {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <DialogFooter>
                <Button type="button" variant="outline" onClick={handleClose}>
                  Cancelar
                </Button>
                <Button type="submit">{isCreate ? 'Criar' : 'Salvar'}</Button>
              </DialogFooter>
            </form>
          </Form>
        </DialogContent>
      </Dialog>

      <AlertDialog open={confirmOpen} onOpenChange={setConfirmOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              {isCreate ? 'Confirmar criação' : 'Confirmar alterações'}
            </AlertDialogTitle>
            <AlertDialogDescription>
              {isCreate
                ? 'Tem certeza que deseja criar esta despesa?'
                : 'Tem certeza que deseja salvar as alterações?'}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isSaving}>Cancelar</AlertDialogCancel>
            <AlertDialogAction
              onClick={(e) => {
                e.preventDefault();
                void handleConfirmSave();
              }}
              disabled={isSaving}
            >
              {isSaving ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  {isCreate ? 'Criando...' : 'Salvando...'}
                </>
              ) : (
                'Confirmar'
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
