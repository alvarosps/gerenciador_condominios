'use client';

import { useCallback, useEffect } from 'react';
import { useRouter } from 'next/navigation';
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
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { usePersons } from '@/lib/api/hooks/use-persons';
import { useCreateThirdPartySettlement } from '@/lib/api/hooks/use-third-party';
import { handleError, showFinanceMutationError } from '@/lib/utils/error-handler';
import { getTodayLocalISO } from '@/lib/utils/formatters';
import { ROUTES } from '@/lib/utils/constants';

interface SettlementFormModalProps {
  open: boolean;
  onClose: () => void;
  /** Pre-selects the person when the acerto is opened from her own row/statement. */
  defaultPersonId?: number | null;
}

/** Sentinel for "no person chosen yet" — Radix Select forbids an empty-string item value. */
const NO_PERSON = 'none';

/**
 * `amount` stays a STRING all the way to the API — the backend field is a Decimal and the money
 * discipline forbids arithmetic on the frontend. The positivity rule mirrors
 * `ThirdPartySettlement.clean()`; the backend remains the real barrier.
 */
const settlementFormSchema = z.object({
  person_id: z.number({ message: 'Pessoa é obrigatória' }).int().positive('Pessoa é obrigatória'),
  settlement_date: z.string().min(1, 'Data é obrigatória'),
  amount: z
    .string()
    .min(1, 'Valor é obrigatório')
    .refine((value) => Number(value) > 0, 'O valor do acerto deve ser positivo'),
  method: z.string(),
  notes: z.string(),
});

type SettlementFormValues = z.infer<typeof settlementFormSchema>;

export function SettlementFormModal({
  open,
  onClose,
  defaultPersonId = null,
}: SettlementFormModalProps) {
  const router = useRouter();
  const createMutation = useCreateThirdPartySettlement();
  const { data: persons } = usePersons();

  // `getTodayLocalISO` (never `toISOString`) so the default date does not roll back a day in
  // Brazil's negative offset during the early hours.
  const buildDefaults = useCallback(
    (): SettlementFormValues => ({
      person_id: defaultPersonId ?? 0,
      settlement_date: getTodayLocalISO(),
      amount: '',
      method: '',
      notes: '',
    }),
    [defaultPersonId]
  );

  const formMethods = useForm<SettlementFormValues>({
    resolver: zodResolver(settlementFormSchema),
    defaultValues: buildDefaults(),
  });

  useEffect(() => {
    if (!open) return;
    formMethods.reset(buildDefaults());
  }, [open, buildDefaults, formMethods]);

  const onSubmit = async (values: SettlementFormValues) => {
    try {
      await createMutation.mutateAsync({
        person_id: values.person_id,
        settlement_date: values.settlement_date,
        amount: values.amount,
        method: values.method,
        notes: values.notes,
      });
      toast.success('Acerto registrado com sucesso');
      onClose();
    } catch (error) {
      // showFinanceMutationError, not a bare toast: a settlement IS closed-month guarded
      // (ThirdPartySettlementService asserts the month on create/update/delete), so that 400 is
      // reachable here and the user needs the "Abrir fechamento" action instead of a dead end.
      showFinanceMutationError(error, 'Erro ao registrar acerto', () =>
        router.push(ROUTES.FINANCES_MONTH_CLOSE)
      );
      handleError(error, 'SettlementFormModal.onSubmit');
    }
  };

  const isLoading = createMutation.isPending;

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Registrar acerto</DialogTitle>
          <DialogDescription>
            Pagamento dos donos a um terceiro, abatendo a dívida acumulada com ele.
          </DialogDescription>
        </DialogHeader>

        <Form {...formMethods}>
          {/* `noValidate`: Zod owns validation (with PT messages). Without it the browser's
              native constraint check runs first and silently swallows the submit. */}
          <form onSubmit={formMethods.handleSubmit(onSubmit)} noValidate className="space-y-4">
            <FormField
              control={formMethods.control}
              name="person_id"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Pessoa *</FormLabel>
                  <Select
                    onValueChange={(value) =>
                      field.onChange(value === NO_PERSON ? 0 : Number(value))
                    }
                    // Always a DEFINED value: handing Radix `undefined` first and a string later
                    // flips the Select from uncontrolled to controlled and silently breaks the
                    // enclosing form's submit. Sentinel pattern from `employee-form-modal.tsx`.
                    value={field.value > 0 ? String(field.value) : NO_PERSON}
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
              control={formMethods.control}
              name="settlement_date"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Data do acerto *</FormLabel>
                  <FormControl>
                    <Input type="date" {...field} disabled={isLoading} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={formMethods.control}
              name="amount"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Valor *</FormLabel>
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
              control={formMethods.control}
              name="method"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Método</FormLabel>
                  <FormControl>
                    <Input placeholder="Ex: PIX" maxLength={50} {...field} disabled={isLoading} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={formMethods.control}
              name="notes"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Observação</FormLabel>
                  <FormControl>
                    <Textarea rows={2} {...field} disabled={isLoading} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <DialogFooter>
              <Button type="button" variant="outline" onClick={onClose} disabled={isLoading}>
                Cancelar
              </Button>
              <Button type="submit" disabled={isLoading}>
                Registrar
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
