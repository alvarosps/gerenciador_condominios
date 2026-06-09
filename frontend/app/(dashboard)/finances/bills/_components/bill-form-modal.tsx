'use client';

import { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Info } from 'lucide-react';
import Link from 'next/link';
import { toast } from 'sonner';
import {
  Dialog,
  DialogBody,
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
import { Textarea } from '@/components/ui/textarea';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  type BillLineInput,
  type BillStatementInput,
  type CreateBillWithLines,
  type UpdateBillWithLines,
  useCreateBillWithLines,
  useUpdateBill,
  useUpdateBillWithLines,
} from '@/lib/api/hooks/use-bills';
import { useBuildings } from '@/lib/api/hooks/use-buildings';
import { useFinanceCategories } from '@/lib/api/hooks/use-finance-categories';
import { useBillingAccounts } from '@/lib/api/hooks/use-billing-accounts';
import { handleError } from '@/lib/utils/error-handler';
import { ROUTES } from '@/lib/utils/constants';
import type { Bill } from '@/lib/schemas/finances/bill.schema';
import { ACCOUNT_TYPE_LABELS, accountLabel } from '@/lib/schemas/finances/billing-account.schema';
import type { BillBehavior } from '@/lib/schemas/finances/category.schema';
import type { ParsedInvoice } from '@/lib/schemas/finances/invoice-parse.schema';
import { BillLineItemsField } from './bill-line-items-field';
import { BillStatementFields } from './bill-statement-fields';
import {
  type BillAccountType,
  type BillFormValues,
  billAccountTypeValues,
  billFormSchema,
} from './bill-form-schema';

const NONE = 'none';

const BEHAVIOR_LABELS: Record<BillBehavior, string> = {
  one_time: 'Avulsa',
  recurring: 'Recorrente',
  installment: 'Parcelada',
};

function toAccountType(value: string | undefined): BillAccountType {
  return billAccountTypeValues.find((type) => type === value) ?? 'generic';
}

function numberToString(value: number | null | undefined): string {
  return value === null || value === undefined ? '' : String(value);
}

function emptyWaterStatement(): BillFormValues['water_statement'] {
  return {
    consumo_m3: '',
    leitura_anterior: '',
    leitura_atual: '',
    leitura_dias: '',
    data_leitura: null,
    agua_status: 'active',
    esgoto_status: 'active',
  };
}

function emptyElectricityStatement(): BillFormValues['electricity_statement'] {
  return {
    consumo_kwh: '',
    energia_injetada_kwh: '',
    leitura_anterior: '',
    leitura_atual: '',
    leitura_dias: '',
    classe: '',
    bandeira: '',
  };
}

function emptyDefaults(): BillFormValues {
  return {
    description: '',
    building_id: null,
    category_id: null,
    competence_month: '',
    due_date: '',
    behavior: 'one_time',
    account_type: 'generic',
    billing_account_id: null,
    external_identifier: '',
    issue_date: null,
    notes: '',
    water_statement: emptyWaterStatement(),
    electricity_statement: emptyElectricityStatement(),
    line_items: [
      { category_id: null, description: '', amount: 0, is_offset: false, installment_id: null },
    ],
  };
}

function billToDefaults(bill: Bill): BillFormValues {
  return {
    description: bill.description,
    building_id: bill.building_id ?? bill.building?.id ?? null,
    category_id: bill.category_id ?? bill.category?.id ?? null,
    competence_month: bill.competence_month,
    due_date: bill.due_date,
    behavior: bill.behavior,
    account_type: 'generic',
    billing_account_id: bill.billing_account_id ?? bill.billing_account?.id ?? null,
    external_identifier: bill.external_identifier ?? '',
    issue_date: bill.issue_date ?? null,
    notes: bill.notes ?? '',
    water_statement: emptyWaterStatement(),
    electricity_statement: emptyElectricityStatement(),
    line_items: bill.line_items.map((line) => ({
      category_id: line.category?.id ?? null,
      description: line.description,
      amount: line.amount,
      is_offset: line.is_offset,
      installment_id: null,
    })),
  };
}

function draftWaterStatement(
  statement: ParsedInvoice['statement'],
): BillFormValues['water_statement'] {
  if (statement === null || !('consumo_m3' in statement)) {
    return emptyWaterStatement();
  }
  return {
    consumo_m3: numberToString(statement.consumo_m3),
    leitura_anterior: numberToString(statement.leitura_anterior),
    leitura_atual: numberToString(statement.leitura_atual),
    leitura_dias: numberToString(statement.leitura_dias),
    data_leitura: statement.data_leitura ?? null,
    agua_status: statement.agua_status,
    esgoto_status: statement.esgoto_status,
  };
}

function draftElectricityStatement(
  statement: ParsedInvoice['statement'],
): BillFormValues['electricity_statement'] {
  if (statement === null || !('consumo_kwh' in statement)) {
    return emptyElectricityStatement();
  }
  return {
    consumo_kwh: numberToString(statement.consumo_kwh),
    energia_injetada_kwh: numberToString(statement.energia_injetada_kwh),
    leitura_anterior: numberToString(statement.leitura_anterior),
    leitura_atual: numberToString(statement.leitura_atual),
    leitura_dias: numberToString(statement.leitura_dias),
    classe: statement.classe ?? '',
    bandeira: statement.bandeira ?? '',
  };
}

/** Map the serialized parser draft (S60) onto the form, reusing the billToDefaults shape. */
function draftToDefaults(draft: ParsedInvoice): BillFormValues {
  const accountType = toAccountType(draft.bill.account_type);
  return {
    description: draft.bill.description,
    building_id: draft.bill.building_id ?? null,
    category_id: draft.bill.category_id ?? null,
    competence_month: draft.bill.competence_month,
    due_date: draft.bill.due_date,
    behavior: 'recurring',
    account_type: accountType,
    billing_account_id: draft.matched_account?.id ?? null,
    external_identifier: draft.bill.external_identifier,
    issue_date: null,
    notes: '',
    water_statement: draftWaterStatement(draft.statement),
    electricity_statement: draftElectricityStatement(draft.statement),
    line_items: draft.line_items.map((line) => ({
      category_id: line.category_id ?? null,
      description: line.description,
      amount: line.amount, // moneyField already transformed the string Decimal to number
      is_offset: line.is_offset,
      installment_id: line.installment_id ?? null,
    })),
  };
}

function buildStatementInput(
  accountType: BillAccountType,
  values: BillFormValues,
): BillStatementInput | null {
  if (accountType === 'water') {
    const consumo = Number(values.water_statement.consumo_m3);
    return {
      kind: 'water',
      consumo_m3: Number.isNaN(consumo) ? 0 : consumo,
      leitura_anterior: emptyToNull(values.water_statement.leitura_anterior),
      leitura_atual: emptyToNull(values.water_statement.leitura_atual),
      leitura_dias: emptyToNull(values.water_statement.leitura_dias),
      data_leitura: values.water_statement.data_leitura,
      agua_status: values.water_statement.agua_status,
      esgoto_status: values.water_statement.esgoto_status,
    };
  }
  if (accountType === 'electricity') {
    const consumo = Number(values.electricity_statement.consumo_kwh);
    return {
      kind: 'electricity',
      consumo_kwh: Number.isNaN(consumo) ? 0 : consumo,
      energia_injetada_kwh: emptyToNull(values.electricity_statement.energia_injetada_kwh),
      leitura_anterior: emptyToNull(values.electricity_statement.leitura_anterior),
      leitura_atual: emptyToNull(values.electricity_statement.leitura_atual),
      leitura_dias: emptyToNull(values.electricity_statement.leitura_dias),
      classe: values.electricity_statement.classe,
      bandeira: values.electricity_statement.bandeira,
    };
  }
  return null;
}

function emptyToNull(value: string): number | null {
  if (value.trim() === '') return null;
  const parsed = Number(value);
  return Number.isNaN(parsed) ? null : parsed;
}

function toLineInput(line: BillFormValues['line_items'][number]): BillLineInput {
  return {
    description: line.description,
    amount: line.amount,
    is_offset: line.is_offset,
    ...(line.category_id !== null ? { category_id: line.category_id } : {}),
    ...(line.installment_id !== null ? { installment_id: line.installment_id } : {}),
  };
}

interface BillFormModalProps {
  open: boolean;
  bill?: Bill | null;
  draft?: ParsedInvoice | null;
  onClose: () => void;
}

export function BillFormModal({ open, bill, draft, onClose }: BillFormModalProps) {
  const createWithLines = useCreateBillWithLines();
  const updateWithLines = useUpdateBillWithLines();
  const updateBill = useUpdateBill();
  const { data: buildings } = useBuildings();
  const { data: categories } = useFinanceCategories();
  const { data: billingAccounts } = useBillingAccounts();

  const isDraft = Boolean(draft);
  const isReplacement = Boolean(draft?.existing_bill_id);
  const isEdit = Boolean(bill?.id);

  const form = useForm<BillFormValues>({
    resolver: zodResolver(billFormSchema),
    defaultValues: emptyDefaults(),
  });

  useEffect(() => {
    if (open) {
      if (draft) {
        form.reset(draftToDefaults(draft));
      } else {
        form.reset(bill ? billToDefaults(bill) : emptyDefaults());
      }
    }
  }, [open, bill, draft, form]);

  const behavior = form.watch('behavior');
  const accountType = form.watch('account_type');
  const isInstallment = behavior === 'installment';

  function submitDraft(values: BillFormValues) {
    const statement = buildStatementInput(values.account_type, values);
    const billPayload: Record<string, unknown> = {
      description: values.description,
      building_id: values.building_id,
      category_id: values.category_id,
      competence_month: values.competence_month,
      due_date: values.due_date,
      behavior: values.behavior,
      billing_account_id: values.billing_account_id,
      external_identifier: values.external_identifier,
      issue_date: values.issue_date,
      notes: values.notes,
    };
    const lineItems = values.line_items.map(toLineInput);

    // Route ENTIRELY on existing_bill_id (idempotency resolved by the backend, §5.5) —
    // never on matched_account.
    if (draft?.existing_bill_id) {
      const payload: UpdateBillWithLines = {
        bill_id: draft.existing_bill_id,
        bill: billPayload,
        line_items: lineItems,
        statement,
      };
      updateWithLines.mutate(payload, {
        onSuccess: () => {
          toast.success('Conta atualizada com sucesso');
          onClose();
        },
        onError: (error) => {
          handleError(error, 'Erro ao salvar conta');
        },
      });
      return;
    }

    const payload: CreateBillWithLines = {
      bill: billPayload,
      line_items: lineItems,
      statement,
    };
    createWithLines.mutate(payload, {
      onSuccess: () => {
        toast.success('Conta criada com sucesso');
        onClose();
      },
      onError: (error) => {
        handleError(error, 'Erro ao salvar conta');
      },
    });
  }

  function handleSubmit(values: BillFormValues) {
    if (isDraft) {
      submitDraft(values);
      return;
    }

    if (isInstallment) {
      // Installment bills belong to Phase 3 — block submission here.
      return;
    }

    if (isEdit && bill?.id) {
      // Lines are created only via `create_with_lines` (S38 exposes no bills/{id}/lines
      // endpoint), so editing an existing bill updates its own fields only.
      updateBill.mutate(
        {
          id: bill.id,
          description: values.description,
          building_id: values.building_id,
          category_id: values.category_id,
          competence_month: values.competence_month,
          due_date: values.due_date,
          behavior: values.behavior,
          billing_account_id: values.billing_account_id,
          external_identifier: values.external_identifier,
          issue_date: values.issue_date,
          notes: values.notes,
        },
        {
          onSuccess: () => {
            toast.success('Conta atualizada com sucesso');
            onClose();
          },
          onError: (error) => {
            handleError(error, 'Erro ao salvar conta');
          },
        }
      );
      return;
    }

    createWithLines.mutate(
      {
        bill: {
          description: values.description,
          building_id: values.building_id,
          category_id: values.category_id,
          competence_month: values.competence_month,
          due_date: values.due_date,
          behavior: values.behavior,
          billing_account_id: values.behavior === 'recurring' ? values.billing_account_id : null,
          external_identifier: values.external_identifier,
          issue_date: values.issue_date,
          notes: values.notes,
        },
        line_items: values.line_items.map(toLineInput),
      },
      {
        onSuccess: () => {
          toast.success('Conta criada com sucesso');
          onClose();
        },
        onError: (error) => {
          handleError(error, 'Erro ao salvar conta');
        },
      }
    );
  }

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-h-[90vh] max-w-3xl flex flex-col">
        <DialogHeader>
          <DialogTitle>
            {isDraft ? 'Importar fatura' : isEdit ? 'Editar Conta' : 'Nova Conta'}
          </DialogTitle>
        </DialogHeader>

        <Form {...form}>
          <form
            onSubmit={form.handleSubmit(handleSubmit)}
            noValidate
            className="flex flex-1 flex-col overflow-hidden"
          >
            <DialogBody className="space-y-4 pr-1">
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <FormField
                  control={form.control}
                  name="description"
                  render={({ field }) => (
                    <FormItem className="sm:col-span-2">
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
                  name="behavior"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Tipo</FormLabel>
                      <Select value={field.value} onValueChange={field.onChange}>
                        <FormControl>
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          <SelectItem value="one_time">{BEHAVIOR_LABELS.one_time}</SelectItem>
                          <SelectItem value="recurring">{BEHAVIOR_LABELS.recurring}</SelectItem>
                          <SelectItem value="installment">{BEHAVIOR_LABELS.installment}</SelectItem>
                        </SelectContent>
                      </Select>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="account_type"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Tipo de conta</FormLabel>
                      <Select value={field.value} onValueChange={field.onChange}>
                        <FormControl>
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          <SelectItem value="generic">{ACCOUNT_TYPE_LABELS.generic}</SelectItem>
                          <SelectItem value="water">{ACCOUNT_TYPE_LABELS.water}</SelectItem>
                          <SelectItem value="electricity">
                            {ACCOUNT_TYPE_LABELS.electricity}
                          </SelectItem>
                          <SelectItem value="iptu">{ACCOUNT_TYPE_LABELS.iptu}</SelectItem>
                          <SelectItem value="internet">{ACCOUNT_TYPE_LABELS.internet}</SelectItem>
                        </SelectContent>
                      </Select>
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
                        onValueChange={(value) =>
                          field.onChange(value === NONE ? null : Number(value))
                        }
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
                        onValueChange={(value) =>
                          field.onChange(value === NONE ? null : Number(value))
                        }
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
                  name="competence_month"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Competência</FormLabel>
                      <FormControl>
                        <Input type="date" {...field} />
                      </FormControl>
                      <FormDescription>Mês de competência (use o dia 1).</FormDescription>
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

                <FormField
                  control={form.control}
                  name="external_identifier"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Inscrição / UC (opcional)</FormLabel>
                      <FormControl>
                        <Input placeholder="Inscrição municipal / Unidade Consumidora" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="issue_date"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Emissão (opcional)</FormLabel>
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

                {behavior === 'recurring' && (
                  <FormField
                    control={form.control}
                    name="billing_account_id"
                    render={({ field }) => (
                      <FormItem className="sm:col-span-2">
                        <FormLabel>Conta recorrente</FormLabel>
                        <Select
                          value={field.value ? String(field.value) : NONE}
                          onValueChange={(value) =>
                            field.onChange(value === NONE ? null : Number(value))
                          }
                        >
                          <FormControl>
                            <SelectTrigger>
                              <SelectValue placeholder="Selecione a conta recorrente" />
                            </SelectTrigger>
                          </FormControl>
                          <SelectContent>
                            <SelectItem value={NONE}>Nenhuma</SelectItem>
                            {billingAccounts?.map((account) =>
                              account.id === undefined ? null : (
                                <SelectItem key={account.id} value={String(account.id)}>
                                  {accountLabel(account)}
                                </SelectItem>
                              )
                            )}
                          </SelectContent>
                        </Select>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                )}
              </div>

              <BillStatementFields form={form} accountType={accountType} />

              {isDraft && draft && draft.warnings.length > 0 && (
                <Alert>
                  <Info className="h-4 w-4" />
                  <AlertDescription>
                    <ul className="list-disc space-y-1 pl-4">
                      {draft.warnings.map((warning, index) => (
                        <li key={`${String(index)}-${warning}`}>{warning}</li>
                      ))}
                    </ul>
                  </AlertDescription>
                </Alert>
              )}

              {isInstallment && (
                <Alert>
                  <Info className="h-4 w-4" />
                  <AlertDescription>
                    Contas parceladas são geridas em{' '}
                    <Link
                      href={ROUTES.FINANCES_INSTALLMENT_PLANS}
                      className="font-medium underline underline-offset-4"
                    >
                      Planos de Parcelamento
                    </Link>
                    . Selecione outro tipo para salvar aqui.
                  </AlertDescription>
                </Alert>
              )}

              {isEdit ? (
                <Alert>
                  <Info className="h-4 w-4" />
                  <AlertDescription>
                    As linhas só podem ser definidas na criação da conta. Para alterar as linhas,
                    crie uma nova conta.
                  </AlertDescription>
                </Alert>
              ) : (
                !isInstallment && <BillLineItemsField form={form} />
              )}

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
            </DialogBody>

            <DialogFooter className="pt-4">
              <Button type="button" variant="outline" onClick={onClose}>
                Cancelar
              </Button>
              <Button
                type="submit"
                disabled={
                  (!isDraft && isInstallment) ||
                  createWithLines.isPending ||
                  updateWithLines.isPending ||
                  updateBill.isPending
                }
              >
                {isReplacement || (isEdit && !isDraft) ? 'Atualizar' : 'Criar'}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
