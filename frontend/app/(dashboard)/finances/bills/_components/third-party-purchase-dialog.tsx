'use client';

import { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Info } from 'lucide-react';
import { toast } from 'sonner';
import { useRouter } from 'next/navigation';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Alert, AlertDescription } from '@/components/ui/alert';
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
import { useCreateThirdPartyPurchase } from '@/lib/api/hooks/use-bills';
import { useBuildings } from '@/lib/api/hooks/use-buildings';
import { useFinanceCategories } from '@/lib/api/hooks/use-finance-categories';
import { usePersons } from '@/lib/api/hooks/use-persons';
import { showFinanceMutationError } from '@/lib/utils/error-handler';
import { getTodayLocalISO } from '@/lib/utils/formatters';
import { ROUTES } from '@/lib/utils/constants';

/** Sentinel for the optional selects — Radix Select forbids an empty-string item value. */
const NONE = 'none';

/** Mirrors `ThirdPartyPurchaseService.MAX_INSTALLMENT_COUNT`; the backend stays the real barrier. */
const MAX_INSTALLMENT_COUNT = 60;

/**
 * `amount` stays a decimal STRING end to end — the backend field is a Decimal, and splitting a
 * parcelamento is the SERVICE's job (it creates N bills + N payments in one transaction). The
 * frontend never divides money.
 */
const purchaseFormSchema = z.object({
  person_id: z.number().int().positive('Pessoa é obrigatória'),
  description: z.string().min(1, 'Descrição é obrigatória'),
  amount: z
    .string()
    .refine((v) => v !== '' && Number(v) > 0, { message: 'O valor deve ser maior que zero' }),
  competence_month: z.string().min(1, 'Competência é obrigatória'),
  due_date: z.string().min(1, 'Vencimento é obrigatório'),
  installment_count: z
    .number()
    .int()
    .min(1, 'Mínimo de 1 parcela')
    .max(MAX_INSTALLMENT_COUNT, `Máximo de ${String(MAX_INSTALLMENT_COUNT)} parcelas`),
  category_id: z.number().nullable(),
  building_id: z.number().nullable(),
});

type PurchaseFormValues = z.infer<typeof purchaseFormSchema>;

interface ThirdPartyPurchaseDialogProps {
  open: boolean;
  onClose: () => void;
  /** Competence shown on the board — seeds the purchase's `competence_month` (day 1). */
  year: number;
  month: number;
}

function competenceOf(year: number, month: number): string {
  return `${String(year)}-${String(month).padStart(2, '0')}-01`;
}

function defaultValues(year: number, month: number): PurchaseFormValues {
  return {
    person_id: 0,
    description: '',
    amount: '',
    competence_month: competenceOf(year, month),
    // `getTodayLocalISO`, never `toISOString`: the latter rolls back a day in Brazil's negative
    // offset during the early hours.
    due_date: getTodayLocalISO(),
    installment_count: 1,
    category_id: null,
    building_id: null,
  };
}

/**
 * "Nova compra de terceiro" (S82 §3) — a purchase somebody already paid for with her own money.
 * It is born PAID: the backend creates the Bill together with the Payment that settles it, so it
 * never shows up as "a pagar". Nothing leaves the caixa; the condominium simply owes that person
 * until a settlement (`/finances/third-party`) extinguishes the debt.
 */
export function ThirdPartyPurchaseDialog({
  open,
  onClose,
  year,
  month,
}: ThirdPartyPurchaseDialogProps) {
  const createPurchase = useCreateThirdPartyPurchase();
  const { data: persons } = usePersons();
  const { data: buildings } = useBuildings();
  const { data: categories } = useFinanceCategories();
  const router = useRouter();

  const form = useForm<PurchaseFormValues>({
    resolver: zodResolver(purchaseFormSchema),
    defaultValues: defaultValues(year, month),
  });

  useEffect(() => {
    if (open) {
      form.reset(defaultValues(year, month));
    }
  }, [open, year, month, form]);

  const installmentCount = form.watch('installment_count');

  function handleSubmit(values: PurchaseFormValues) {
    createPurchase.mutate(
      {
        person_id: values.person_id,
        description: values.description,
        amount: values.amount,
        competence_month: values.competence_month,
        due_date: values.due_date,
        installment_count: values.installment_count,
        ...(values.category_id !== null ? { category_id: values.category_id } : {}),
        ...(values.building_id !== null ? { building_id: values.building_id } : {}),
      },
      {
        onSuccess: (bills) => {
          toast.success(
            bills.length > 1
              ? `Compra lançada em ${String(bills.length)} parcelas`
              : 'Compra registrada com sucesso'
          );
          onClose();
        },
        onError: (error) => {
          showFinanceMutationError(error, 'Erro ao registrar compra', () =>
            router.push(ROUTES.FINANCES_MONTH_CLOSE)
          );
        },
      }
    );
  }

  const isLoading = createPurchase.isPending;

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-h-[90vh] max-w-lg overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Nova compra de terceiro</DialogTitle>
          <DialogDescription>
            Algo que um filho ou o genro comprou para o condomínio usando o dinheiro dele.
          </DialogDescription>
        </DialogHeader>

        <Alert>
          <Info className="h-4 w-4" />
          <AlertDescription>
            A compra já foi paga pela pessoa e entra como dívida com ela. Por isso ela não aparece
            em &quot;a pagar&quot; e nada sai do caixa — a dívida só é quitada com um acerto.
          </AlertDescription>
        </Alert>

        <Form {...form}>
          {/* `noValidate`: Zod owns validation (with PT messages). Without it the browser's native
              constraint check runs first and silently swallows the submit. */}
          <form onSubmit={form.handleSubmit(handleSubmit)} noValidate className="space-y-4">
            <FormField
              control={form.control}
              name="person_id"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Quem comprou *</FormLabel>
                  <Select
                    onValueChange={(value) => field.onChange(value === NONE ? 0 : Number(value))}
                    // Always a DEFINED value: handing Radix `undefined` first and a string later
                    // flips the Select from uncontrolled to controlled and breaks the submit.
                    value={field.value > 0 ? String(field.value) : NONE}
                    disabled={isLoading}
                  >
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue placeholder="Selecione a pessoa" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {(persons ?? []).map((person) =>
                        person.id === undefined ? null : (
                          <SelectItem key={person.id} value={String(person.id)}>
                            {person.name}
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
              name="description"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Descrição *</FormLabel>
                  <FormControl>
                    <Input
                      placeholder="Ex: Bomba d'água"
                      {...field}
                      disabled={isLoading}
                      value={field.value}
                    />
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
                  <FormLabel>Valor total *</FormLabel>
                  <FormControl>
                    <Input
                      type="number"
                      step="0.01"
                      min="0"
                      placeholder="0,00"
                      {...field}
                      disabled={isLoading}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="installment_count"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Parcelas</FormLabel>
                  <FormControl>
                    <Input
                      type="number"
                      min={1}
                      max={MAX_INSTALLMENT_COUNT}
                      step={1}
                      value={String(field.value)}
                      onChange={(event) => field.onChange(Number(event.target.value))}
                      disabled={isLoading}
                    />
                  </FormControl>
                  <FormDescription>
                    {installmentCount > 1
                      ? 'O valor total é dividido pelo servidor: uma conta por mês, todas já quitadas.'
                      : 'Use 1 para uma compra à vista.'}
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="competence_month"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Competência *</FormLabel>
                  <FormControl>
                    <Input type="date" {...field} disabled={isLoading} />
                  </FormControl>
                  <FormDescription>
                    Mês em que a compra entra no resultado (a primeira parcela).
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="due_date"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Vencimento *</FormLabel>
                  <FormControl>
                    <Input type="date" {...field} disabled={isLoading} />
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
                  <FormLabel>Categoria</FormLabel>
                  <Select
                    onValueChange={(value) => field.onChange(value === NONE ? null : Number(value))}
                    value={field.value === null ? NONE : String(field.value)}
                    disabled={isLoading}
                  >
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue placeholder="Sem categoria" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      <SelectItem value={NONE}>Sem categoria</SelectItem>
                      {(categories ?? []).map((category) =>
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
              name="building_id"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Prédio</FormLabel>
                  <Select
                    onValueChange={(value) => field.onChange(value === NONE ? null : Number(value))}
                    value={field.value === null ? NONE : String(field.value)}
                    disabled={isLoading}
                  >
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue placeholder="Condomínio (sem prédio)" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      <SelectItem value={NONE}>Condomínio (sem prédio)</SelectItem>
                      {(buildings ?? []).map((building) =>
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

            <DialogFooter>
              <Button type="button" variant="outline" onClick={onClose} disabled={isLoading}>
                Cancelar
              </Button>
              <Button type="submit" disabled={isLoading}>
                {isLoading ? 'Registrando...' : 'Registrar compra'}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
