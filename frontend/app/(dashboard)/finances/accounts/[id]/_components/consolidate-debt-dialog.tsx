'use client';

import { useEffect, useMemo, useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Info } from 'lucide-react';
import { toast } from 'sonner';
import { useRouter } from 'next/navigation';
import {
  Dialog,
  DialogBody,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Alert, AlertDescription } from '@/components/ui/alert';
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
import { useConsolidateDebt } from '@/lib/api/hooks/use-billing-accounts';
import { showFinanceMutationError } from '@/lib/utils/error-handler';
import {
  formatCurrency,
  getTodayLocalISO,
  competenceMonthLabel,
  dueDateLabel,
} from '@/lib/utils/formatters';
import { ROUTES } from '@/lib/utils/constants';
import type { BillingAccountType } from '@/lib/schemas/finances/billing-account.schema';

/** Account types eligible for embedded consolidation — mirrors the backend rule (embedded ⇒ consumption). */
const CONSUMPTION_ACCOUNT_TYPES: ReadonlySet<BillingAccountType> = new Set([
  'water',
  'electricity',
  'internet',
]);

export interface ConsolidableBill {
  bill_id: number;
  description: string;
  competence_month: string; // YYYY-MM-01
  due_date: string;
  amount_remaining: number; // RESTO (parciais contam o resto — S70)
}

export interface ConsolidateDebtDialogProps {
  open: boolean;
  onClose: () => void;
  accountId: number;
  accountType: BillingAccountType; // embedded só p/ consumo (water/electricity/internet)
  bills: ConsolidableBill[]; // já filtradas: amount_remaining > 0 e lifecycle_state ≠ canceled
}

const embeddedFormSchema = z.object({
  embedded: z.enum(['embedded', 'standalone']),
  installment_count: z.number().int().min(2, 'Informe pelo menos 2 parcelas'),
  start_due_date: z.string().min(1, 'Data é obrigatória'),
  default_due_day: z.number().int().min(1).max(31),
});

type ConsolidateFormValues = z.infer<typeof embeddedFormSchema>;

function defaultDueDay(dateStr: string): number {
  const [, , day] = dateStr.split('-');
  const parsed = day ? Number(day) : NaN;
  return Number.isNaN(parsed) ? 1 : parsed;
}

function defaultFormValues(): ConsolidateFormValues {
  const today = getTodayLocalISO();
  return {
    embedded: 'standalone',
    installment_count: 2,
    start_due_date: today,
    default_due_day: defaultDueDay(today),
  };
}

export function ConsolidateDebtDialog({
  open,
  onClose,
  accountId,
  accountType,
  bills,
}: ConsolidateDebtDialogProps) {
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [selectionError, setSelectionError] = useState<string | null>(null);
  const consolidateDebt = useConsolidateDebt();
  const router = useRouter();
  const consumptionAccount = CONSUMPTION_ACCOUNT_TYPES.has(accountType);

  const form = useForm<ConsolidateFormValues>({
    resolver: zodResolver(embeddedFormSchema),
    defaultValues: defaultFormValues(),
  });

  useEffect(() => {
    if (open) {
      form.reset(defaultFormValues());
      setSelectedIds([]);
      setSelectionError(null);
    }
  }, [open, form]);

  const allSelected = bills.length > 0 && selectedIds.length === bills.length;

  const total = useMemo(
    () =>
      bills
        .filter((bill) => selectedIds.includes(bill.bill_id))
        .reduce((sum, bill) => sum + bill.amount_remaining, 0),
    [bills, selectedIds]
  );

  function toggleBill(billId: number, checked: boolean) {
    setSelectionError(null);
    setSelectedIds((prev) => (checked ? [...prev, billId] : prev.filter((id) => id !== billId)));
  }

  function toggleAll(checked: boolean) {
    setSelectionError(null);
    setSelectedIds(checked ? bills.map((bill) => bill.bill_id) : []);
  }

  function handleSubmit(values: ConsolidateFormValues) {
    if (selectedIds.length === 0) {
      setSelectionError('Selecione ao menos uma fatura');
      return;
    }

    consolidateDebt.mutate(
      {
        account_id: accountId,
        bill_ids: selectedIds,
        embedded: values.embedded === 'embedded',
        installment_count: values.installment_count,
        start_due_date: values.start_due_date,
        default_due_day: values.default_due_day,
      },
      {
        onSuccess: () => {
          toast.success('Saldo devedor parcelado — plano criado');
          onClose();
        },
        onError: (error) => {
          showFinanceMutationError(error, 'Erro ao parcelar saldo devedor', () =>
            router.push(ROUTES.FINANCES_MONTH_CLOSE)
          );
        },
      }
    );
  }

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="flex max-h-[90vh] max-w-2xl flex-col">
        <DialogHeader>
          <DialogTitle>Parcelar saldo devedor</DialogTitle>
          <DialogDescription>
            Selecione as faturas em aberto que devem entrar no plano de parcelamento.
          </DialogDescription>
        </DialogHeader>

        <Alert>
          <Info className="h-4 w-4" />
          <AlertDescription>
            As faturas selecionadas serão canceladas e a dívida passará a viver apenas no plano.
          </AlertDescription>
        </Alert>

        <Form {...form}>
          <form
            onSubmit={form.handleSubmit(handleSubmit)}
            noValidate
            className="flex flex-1 flex-col overflow-hidden"
          >
            <DialogBody className="space-y-4 pr-1">
              <div className="space-y-2">
                <div className="flex items-center gap-2 border-b pb-2">
                  <Checkbox
                    checked={allSelected}
                    onCheckedChange={(checked) => toggleAll(checked === true)}
                    aria-label="Selecionar todas"
                  />
                  <span className="text-sm font-medium">Selecionar todas</span>
                </div>

                {bills.map((bill) => (
                  <div key={bill.bill_id} className="flex items-center gap-3 rounded-md border p-2">
                    <Checkbox
                      checked={selectedIds.includes(bill.bill_id)}
                      onCheckedChange={(checked) => toggleBill(bill.bill_id, checked === true)}
                      aria-label={`Selecionar fatura ${bill.description}`}
                    />
                    <div className="flex-1 text-sm">
                      <div>{bill.description}</div>
                      <div className="text-xs text-muted-foreground">
                        Competência {competenceMonthLabel(bill.competence_month)} · Vencimento{' '}
                        {dueDateLabel(bill.due_date)}
                      </div>
                    </div>
                    <div className="text-sm font-medium tabular-nums">
                      {formatCurrency(bill.amount_remaining)}
                    </div>
                  </div>
                ))}

                {selectionError && <p className="text-sm text-destructive">{selectionError}</p>}
              </div>

              <div className="flex items-center justify-between rounded-md border bg-muted/50 p-3">
                <span className="text-sm font-medium">Total do plano</span>
                <span data-testid="consolidate-total" className="text-lg font-bold tabular-nums">
                  {formatCurrency(total)}
                </span>
              </div>

              <FormField
                control={form.control}
                name="embedded"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel htmlFor="consolidate-embedded">Parcelamento</FormLabel>
                    <Select
                      value={field.value}
                      onValueChange={field.onChange}
                      disabled={!consumptionAccount}
                    >
                      <FormControl>
                        <SelectTrigger id="consolidate-embedded" aria-label="Parcelamento">
                          <SelectValue />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        <SelectItem value="embedded">Embutido na conta</SelectItem>
                        <SelectItem value="standalone">Plano avulso</SelectItem>
                      </SelectContent>
                    </Select>
                    {!consumptionAccount && (
                      <FormDescription>
                        Parcelamento embutido só para contas de consumo
                      </FormDescription>
                    )}
                    <FormMessage />
                  </FormItem>
                )}
              />

              <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                <FormField
                  control={form.control}
                  name="installment_count"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel htmlFor="consolidate-installment-count">
                        Número de parcelas
                      </FormLabel>
                      <FormControl>
                        <Input
                          id="consolidate-installment-count"
                          type="number"
                          min={2}
                          value={Number.isNaN(field.value) ? '' : field.value}
                          onChange={(e) => field.onChange(e.target.valueAsNumber)}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="start_due_date"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel htmlFor="consolidate-start-due-date">
                        Data da primeira parcela
                      </FormLabel>
                      <FormControl>
                        <Input id="consolidate-start-due-date" type="date" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="default_due_day"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel htmlFor="consolidate-default-due-day">Dia de vencimento</FormLabel>
                      <FormControl>
                        <Input
                          id="consolidate-default-due-day"
                          type="number"
                          min={1}
                          max={31}
                          value={Number.isNaN(field.value) ? '' : field.value}
                          onChange={(e) => field.onChange(e.target.valueAsNumber)}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
            </DialogBody>

            <DialogFooter className="pt-4">
              <Button type="button" variant="outline" onClick={onClose}>
                Cancelar
              </Button>
              <Button type="submit" disabled={consolidateDebt.isPending}>
                {consolidateDebt.isPending ? 'Parcelando...' : 'Parcelar'}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
