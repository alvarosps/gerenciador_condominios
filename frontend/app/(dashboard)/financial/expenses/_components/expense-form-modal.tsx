'use client';

import { useEffect, useMemo, useRef } from 'react';
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
import { Switch } from '@/components/ui/switch';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Separator } from '@/components/ui/separator';
import { Info } from 'lucide-react';
import { toast } from 'sonner';
import Link from 'next/link';
import {
  useCreateExpense,
  useUpdateExpense,
  useGenerateInstallments,
} from '@/lib/api/hooks/use-expenses';
import { usePersons } from '@/lib/api/hooks/use-persons';
import { useCreditCards } from '@/lib/api/hooks/use-credit-cards';
import { useBuildings } from '@/lib/api/hooks/use-buildings';
import { useExpenseCategories } from '@/lib/api/hooks/use-expense-categories';
import { type Expense, validateExpenseRules } from '@/lib/schemas/expense.schema';
import { ROUTES } from '@/lib/utils/constants';

interface Props {
  open: boolean;
  expense?: Expense | null;
  defaultExpenseDate?: string;
  onClose: () => void;
  onSuccess?: () => void;
}

const EXPENSE_TYPES = [
  { value: 'card_purchase', label: 'Compra no Cart\u00e3o' },
  { value: 'bank_loan', label: 'Empr\u00e9stimo Banc\u00e1rio' },
  { value: 'personal_loan', label: 'Empr\u00e9stimo Pessoal' },
  { value: 'water_bill', label: 'Conta de \u00c1gua' },
  { value: 'electricity_bill', label: 'Conta de Luz' },
  { value: 'property_tax', label: 'IPTU' },
  { value: 'fixed_expense', label: 'Gasto Fixo Mensal' },
  { value: 'one_time_expense', label: 'Gasto \u00danico' },
  { value: 'employee_salary', label: 'Sal\u00e1rio Funcion\u00e1rio' },
];

const expenseFormSchema = z
  .object({
    description: z.string().min(1, 'Descri\u00e7\u00e3o \u00e9 obrigat\u00f3ria'),
    expense_type: z.string().min(1, 'Tipo \u00e9 obrigat\u00f3rio'),
    total_amount: z.number().min(0.01, 'Valor deve ser maior que zero'),
    expense_date: z.string().min(1, 'Data \u00e9 obrigat\u00f3ria'),
    person_id: z.number().nullable(),
    credit_card_id: z.number().nullable(),
    building_id: z.number().nullable(),
    category_id: z.number().nullable(),
    is_installment: z.boolean(),
    total_installments: z.number().nullable(),
    is_debt_installment: z.boolean(),
    is_offset: z.boolean(),
    is_recurring: z.boolean(),
    expected_monthly_amount: z.number().nullable(),
    recurrence_day: z.number().nullable(),
    bank_name: z.string(),
    interest_rate: z.number().nullable(),
    end_date: z.string().nullable(),
    notes: z.string(),
  })
  .superRefine(validateExpenseRules);

type ExpenseFormValues = z.infer<typeof expenseFormSchema>;

// Types that require person
const PERSON_REQUIRED_TYPES = ['card_purchase', 'bank_loan', 'personal_loan'];
// Types that show person as optional
const PERSON_OPTIONAL_TYPES = ['one_time_expense', 'fixed_expense'];
// Types that require building
const BUILDING_REQUIRED_TYPES = ['water_bill', 'electricity_bill', 'property_tax'];
// Types that show building as optional
const BUILDING_OPTIONAL_TYPES = ['fixed_expense', 'one_time_expense'];
// Types that show is_offset toggle (desconto)
const OFFSET_TYPES = ['card_purchase', 'bank_loan', 'personal_loan'];
// Types that show installment fields
const INSTALLMENT_TYPES = ['card_purchase', 'bank_loan', 'personal_loan'];
// Types that show debt_installment toggle (utility bills)
const DEBT_INSTALLMENT_TYPES = ['water_bill', 'electricity_bill', 'property_tax'];

export function ExpenseFormModal({ open, expense, defaultExpenseDate, onClose, onSuccess }: Props) {
  const createMutation = useCreateExpense();
  const updateMutation = useUpdateExpense();
  const generateInstallmentsMutation = useGenerateInstallments();

  const { data: persons } = usePersons();
  const { data: allCreditCards } = useCreditCards();
  const { data: buildings } = useBuildings();
  const { data: categories } = useExpenseCategories();

  const form = useForm<ExpenseFormValues>({
    resolver: zodResolver(expenseFormSchema),
    defaultValues: {
      description: '',
      expense_type: '',
      total_amount: 0,
      expense_date: defaultExpenseDate ?? '',
      person_id: null,
      credit_card_id: null,
      building_id: null,
      category_id: null,
      is_installment: false,
      total_installments: null,
      is_debt_installment: false,
      is_offset: false,
      is_recurring: false,
      expected_monthly_amount: null,
      recurrence_day: null,
      bank_name: '',
      interest_rate: null,
      end_date: null,
      notes: '',
    },
  });

  const watchedType = form.watch('expense_type');
  const watchedPersonId = form.watch('person_id');
  const watchedIsInstallment = form.watch('is_installment');
  const watchedIsDebtInstallment = form.watch('is_debt_installment');

  const filteredCreditCards = useMemo(() => {
    if (!allCreditCards || !watchedPersonId) return [];
    return allCreditCards.filter((card) => card.person?.id === watchedPersonId);
  }, [allCreditCards, watchedPersonId]);

  // Reset conditional fields when type changes
  useEffect(() => {
    if (watchedType === 'fixed_expense') {
      form.setValue('is_recurring', true);
    } else {
      form.setValue('is_recurring', false);
    }
  }, [watchedType, form]);

  // Clear credit card when person changes
  useEffect(() => {
    if (!watchedPersonId) {
      form.setValue('credit_card_id', null);
    }
  }, [watchedPersonId, form]);

  // Reset form when expense changes (edit mode) or modal opens for create
  useEffect(() => {
    if (expense) {
      form.reset({
        description: expense.description,
        expense_type: expense.expense_type,
        total_amount: expense.total_amount,
        expense_date: expense.expense_date,
        person_id: expense.person_id ?? expense.person?.id ?? null,
        credit_card_id: expense.credit_card_id ?? expense.credit_card?.id ?? null,
        building_id: expense.building_id ?? expense.building?.id ?? null,
        category_id: expense.category_id ?? expense.category?.id ?? null,
        is_installment: expense.is_installment,
        total_installments: expense.total_installments ?? null,
        is_debt_installment: expense.is_debt_installment,
        is_offset: expense.is_offset,
        is_recurring: expense.is_recurring,
        expected_monthly_amount: expense.expected_monthly_amount ?? null,
        recurrence_day: expense.recurrence_day ?? null,
        bank_name: expense.bank_name ?? '',
        interest_rate: expense.interest_rate ?? null,
        end_date: expense.end_date ?? null,
        notes: expense.notes ?? '',
      });
    } else {
      form.reset({
        description: '',
        expense_type: '',
        total_amount: 0,
        expense_date: defaultExpenseDate ?? '',
        person_id: null,
        credit_card_id: null,
        building_id: null,
        category_id: null,
        is_installment: false,
        total_installments: null,
        is_debt_installment: false,
        is_offset: false,
        is_recurring: false,
        expected_monthly_amount: null,
        recurrence_day: null,
        bank_name: '',
        interest_rate: null,
        end_date: null,
        notes: '',
      });
    }
  }, [expense, form, defaultExpenseDate]);

  const showPersonField = PERSON_REQUIRED_TYPES.includes(watchedType) || PERSON_OPTIONAL_TYPES.includes(watchedType);
  const showCreditCardField = watchedType === 'card_purchase';
  const showBuildingField = BUILDING_REQUIRED_TYPES.includes(watchedType) || BUILDING_OPTIONAL_TYPES.includes(watchedType);
  const showInstallmentFields = INSTALLMENT_TYPES.includes(watchedType);
  const showDebtInstallmentToggle = DEBT_INSTALLMENT_TYPES.includes(watchedType);
  const showOffsetToggle = OFFSET_TYPES.includes(watchedType);
  const showBankFields = watchedType === 'bank_loan';
  const showFixedExpenseFields = watchedType === 'fixed_expense';
  const isEmployeeSalary = watchedType === 'employee_salary';

  const isSubmittingRef = useRef(false);

  const handleSubmit = async (values: ExpenseFormValues) => {
    if (isSubmittingRef.current) return;
    isSubmittingRef.current = true;

    try {
      if (expense?.id) {
        await updateMutation.mutateAsync({ ...values, id: expense.id });
        toast.success('Despesa atualizada com sucesso');
      } else {
        const created = await createMutation.mutateAsync({ ...values, is_paid: false });
        toast.success('Despesa criada com sucesso');

        // Auto-generate installments if applicable
        if (values.is_installment && created.id) {
          const result = await generateInstallmentsMutation.mutateAsync(created.id);
          toast.success(`${result.installments_created} parcelas geradas`);
        }
      }

      onSuccess?.();
      onClose();
      form.reset();
    } catch {
      toast.error('Erro ao salvar despesa');
    } finally {
      isSubmittingRef.current = false;
    }
  };

  const handleClose = () => {
    onClose();
    form.reset();
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{expense ? 'Editar Despesa' : 'Nova Despesa'}</DialogTitle>
        </DialogHeader>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-4">
            {/* Always visible fields */}
            <div className="grid grid-cols-2 gap-4">
              <FormField
                control={form.control}
                name="description"
                render={({ field }) => (
                  <FormItem className="col-span-2">
                    <FormLabel>Descri\u00e7\u00e3o</FormLabel>
                    <FormControl>
                      <Input placeholder="Descri\u00e7\u00e3o da despesa" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="expense_type"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Tipo</FormLabel>
                    <Select value={field.value} onValueChange={field.onChange}>
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue placeholder="Selecione o tipo" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        {EXPENSE_TYPES.map((t) => (
                          <SelectItem key={t.value} value={t.value}>
                            {t.label}
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
                name="total_amount"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Valor Total</FormLabel>
                    <FormControl>
                      <div className="relative">
                        <span className="absolute left-3 top-1/2 -translate-y-1/2 text-sm text-muted-foreground">
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

              <FormField
                control={form.control}
                name="category_id"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Categoria (opcional)</FormLabel>
                    <Select
                      value={field.value ? String(field.value) : 'none'}
                      onValueChange={(value) => field.onChange(value === 'none' ? null : Number(value))}
                    >
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue placeholder="Selecione" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        <SelectItem value="none">Nenhuma</SelectItem>
                        {categories?.map((cat) => (
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
            </div>

            {/* Employee Salary redirect */}
            {isEmployeeSalary && (
              <Alert>
                <Info className="h-4 w-4" />
                <AlertDescription className="flex items-center justify-between">
                  <span>Use a p\u00e1gina de Funcion\u00e1rios para registrar pagamentos de sal\u00e1rio.</span>
                  <Button variant="link" asChild>
                    <Link href={ROUTES.FINANCIAL_EMPLOYEES}>Ir para Funcion\u00e1rios</Link>
                  </Button>
                </AlertDescription>
              </Alert>
            )}

            {/* Conditional fields based on type */}
            {!isEmployeeSalary && watchedType && (
              <>
                <Separator />

                {/* Person field */}
                {showPersonField && (
                  <FormField
                    control={form.control}
                    name="person_id"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>
                          Pessoa{PERSON_REQUIRED_TYPES.includes(watchedType) ? '' : ' (opcional)'}
                        </FormLabel>
                        <Select
                          value={field.value ? String(field.value) : 'none'}
                          onValueChange={(value) => field.onChange(value === 'none' ? null : Number(value))}
                        >
                          <FormControl>
                            <SelectTrigger>
                              <SelectValue placeholder="Selecione a pessoa" />
                            </SelectTrigger>
                          </FormControl>
                          <SelectContent>
                            <SelectItem value="none">Nenhuma</SelectItem>
                            {persons?.map((p) => (
                              <SelectItem key={p.id} value={String(p.id)}>
                                {p.name}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                )}

                {/* Credit Card field */}
                {showCreditCardField && (
                  <FormField
                    control={form.control}
                    name="credit_card_id"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Cart\u00e3o de Cr\u00e9dito</FormLabel>
                        <Select
                          value={field.value ? String(field.value) : 'none'}
                          onValueChange={(value) => field.onChange(value === 'none' ? null : Number(value))}
                          disabled={!watchedPersonId}
                        >
                          <FormControl>
                            <SelectTrigger>
                              <SelectValue placeholder={watchedPersonId ? 'Selecione o cart\u00e3o' : 'Selecione uma pessoa primeiro'} />
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
                        {!watchedPersonId && (
                          <FormDescription>Selecione uma pessoa para ver os cart\u00f5es</FormDescription>
                        )}
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                )}

                {/* Offset toggle */}
                {showOffsetToggle && (
                  <div className="space-y-2 rounded-md border p-4">
                    <FormField
                      control={form.control}
                      name="is_offset"
                      render={({ field }) => (
                        <FormItem className="flex items-center justify-between">
                          <div>
                            <FormLabel>Desconto (compra para os sogros/Camila)</FormLabel>
                            {field.value && (
                              <FormDescription>
                                Este valor será subtraído do total da pessoa
                              </FormDescription>
                            )}
                          </div>
                          <FormControl>
                            <Switch checked={field.value} onCheckedChange={field.onChange} />
                          </FormControl>
                        </FormItem>
                      )}
                    />
                  </div>
                )}

                {/* Building field */}
                {showBuildingField && (
                  <FormField
                    control={form.control}
                    name="building_id"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>
                          Pr\u00e9dio{BUILDING_REQUIRED_TYPES.includes(watchedType) ? '' : ' (opcional)'}
                        </FormLabel>
                        <Select
                          value={field.value ? String(field.value) : 'none'}
                          onValueChange={(value) => field.onChange(value === 'none' ? null : Number(value))}
                        >
                          <FormControl>
                            <SelectTrigger>
                              <SelectValue placeholder="Selecione o pr\u00e9dio" />
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

                {/* Bank fields */}
                {showBankFields && (
                  <div className="grid grid-cols-2 gap-4">
                    <FormField
                      control={form.control}
                      name="bank_name"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Nome do Banco</FormLabel>
                          <FormControl>
                            <Input placeholder="Ex: Ita\u00fa, Bradesco" {...field} />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                    <FormField
                      control={form.control}
                      name="interest_rate"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Taxa de Juros (%)</FormLabel>
                          <FormControl>
                            <Input
                              type="number"
                              min={0}
                              step="0.01"
                              placeholder="0.00"
                              value={field.value ?? ''}
                              onChange={(e) =>
                                field.onChange(e.target.value ? Number(e.target.value) : null)
                              }
                            />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                  </div>
                )}

                {/* Installment fields for card/loan types */}
                {showInstallmentFields && (
                  <div className="space-y-4 rounded-md border p-4">
                    <FormField
                      control={form.control}
                      name="is_installment"
                      render={({ field }) => (
                        <FormItem className="flex items-center justify-between">
                          <FormLabel>Parcelado?</FormLabel>
                          <FormControl>
                            <Switch checked={field.value} onCheckedChange={field.onChange} />
                          </FormControl>
                        </FormItem>
                      )}
                    />
                    {watchedIsInstallment && (
                      <FormField
                        control={form.control}
                        name="total_installments"
                        render={({ field }) => (
                          <FormItem>
                            <FormLabel>N\u00famero de Parcelas</FormLabel>
                            <FormControl>
                              <Input
                                type="number"
                                min={2}
                                placeholder="Ex: 12"
                                value={field.value ?? ''}
                                onChange={(e) =>
                                  field.onChange(e.target.value ? Number(e.target.value) : null)
                                }
                              />
                            </FormControl>
                            <FormMessage />
                          </FormItem>
                        )}
                      />
                    )}
                  </div>
                )}

                {/* Debt installment toggle for utility bills */}
                {showDebtInstallmentToggle && (
                  <div className="space-y-4 rounded-md border p-4">
                    <FormField
                      control={form.control}
                      name="is_debt_installment"
                      render={({ field }) => (
                        <FormItem className="flex items-center justify-between">
                          <div>
                            <FormLabel>Parcelamento de d\u00edvida?</FormLabel>
                            <FormDescription>Marque se esta conta est\u00e1 sendo parcelada</FormDescription>
                          </div>
                          <FormControl>
                            <Switch checked={field.value} onCheckedChange={field.onChange} />
                          </FormControl>
                        </FormItem>
                      )}
                    />
                    {watchedIsDebtInstallment && (
                      <>
                        <FormField
                          control={form.control}
                          name="is_installment"
                          render={({ field }) => (
                            <FormItem className="flex items-center justify-between">
                              <FormLabel>Gerar parcelas?</FormLabel>
                              <FormControl>
                                <Switch checked={field.value} onCheckedChange={field.onChange} />
                              </FormControl>
                            </FormItem>
                          )}
                        />
                        {watchedIsInstallment && (
                          <FormField
                            control={form.control}
                            name="total_installments"
                            render={({ field }) => (
                              <FormItem>
                                <FormLabel>N\u00famero de Parcelas</FormLabel>
                                <FormControl>
                                  <Input
                                    type="number"
                                    min={2}
                                    placeholder="Ex: 12"
                                    value={field.value ?? ''}
                                    onChange={(e) =>
                                      field.onChange(e.target.value ? Number(e.target.value) : null)
                                    }
                                  />
                                </FormControl>
                                <FormMessage />
                              </FormItem>
                            )}
                          />
                        )}
                      </>
                    )}
                  </div>
                )}

                {/* Fixed expense fields */}
                {showFixedExpenseFields && (
                  <div className="grid grid-cols-2 gap-4">
                    <FormField
                      control={form.control}
                      name="expected_monthly_amount"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Valor Mensal Esperado</FormLabel>
                          <FormControl>
                            <div className="relative">
                              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-sm text-muted-foreground">
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
                                  field.onChange(e.target.value ? Number(e.target.value) : null)
                                }
                              />
                            </div>
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                    <FormField
                      control={form.control}
                      name="recurrence_day"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Dia de Recorr\u00eancia</FormLabel>
                          <FormControl>
                            <Input
                              type="number"
                              min={1}
                              max={31}
                              placeholder="Ex: 10"
                              value={field.value ?? ''}
                              onChange={(e) =>
                                field.onChange(e.target.value ? Number(e.target.value) : null)
                              }
                            />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                    <FormField
                      control={form.control}
                      name="end_date"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Data de T\u00e9rmino (opcional)</FormLabel>
                          <FormControl>
                            <Input
                              type="date"
                              value={field.value ?? ''}
                              onChange={(e) => field.onChange(e.target.value || null)}
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

            {/* Notes */}
            <FormField
              control={form.control}
              name="notes"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Observa\u00e7\u00f5es (opcional)</FormLabel>
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
              {!isEmployeeSalary && (
                <Button
                  type="submit"
                  disabled={createMutation.isPending || updateMutation.isPending || generateInstallmentsMutation.isPending}
                >
                  {expense ? 'Atualizar' : 'Criar'}
                </Button>
              )}
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
