'use client';

import { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Info } from 'lucide-react';
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
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { useConvertDeferred } from '@/lib/api/hooks/use-installment-plans';
import { handleError } from '@/lib/utils/error-handler';

const convertDeferredFormSchema = z.object({
  installment_count: z.number().int().positive('Número de parcelas inválido'),
  start_due_date: z.string().min(1, 'Data da primeira parcela é obrigatória'),
  default_due_day: z.number().int().min(1).max(31),
});

type ConvertDeferredFormValues = z.infer<typeof convertDeferredFormSchema>;

interface ConvertDeferredDialogProps {
  open: boolean;
  /** PK of the deferred Bill to reparcel (the backend action operates on a Bill). */
  billId: number | null;
  description?: string;
  onClose: () => void;
}

/** Default the first due date to the 10th of next month (split-based, never new Date(iso)). */
function nextMonthDefaultDueDate(): string {
  const now = new Date();
  const year = now.getMonth() === 11 ? now.getFullYear() + 1 : now.getFullYear();
  const month = now.getMonth() === 11 ? 1 : now.getMonth() + 2;
  return `${String(year)}-${String(month).padStart(2, '0')}-10`;
}

export function ConvertDeferredDialog({
  open,
  billId,
  description,
  onClose,
}: ConvertDeferredDialogProps) {
  const convertDeferred = useConvertDeferred();

  const form = useForm<ConvertDeferredFormValues>({
    resolver: zodResolver(convertDeferredFormSchema),
    defaultValues: {
      installment_count: 3,
      start_due_date: nextMonthDefaultDueDate(),
      default_due_day: 10,
    },
  });

  useEffect(() => {
    if (open) {
      form.reset({
        installment_count: 3,
        start_due_date: nextMonthDefaultDueDate(),
        default_due_day: 10,
      });
    }
  }, [open, form]);

  function handleSubmit(values: ConvertDeferredFormValues) {
    if (billId === null) return;
    convertDeferred.mutate(
      { bill_id: billId, ...values },
      {
        onSuccess: () => {
          toast.success('Plano de parcelas criado a partir do item adiado');
          onClose();
        },
        onError: (error) => {
          handleError(error, 'Erro ao converter item adiado');
        },
      },
    );
  }

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Converter item adiado</DialogTitle>
          <DialogDescription>
            {description
              ? `Reparcelar "${description}" em prestações.`
              : 'Reparcelar o item adiado em prestações.'}
          </DialogDescription>
        </DialogHeader>

        <Alert>
          <Info className="h-4 w-4" />
          <AlertDescription>
            O IPTU anual adiado será reparcelado; o valor total é preservado.
          </AlertDescription>
        </Alert>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(handleSubmit)} noValidate className="space-y-4">
            <FormField
              control={form.control}
              name="installment_count"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Nº de parcelas</FormLabel>
                  <FormControl>
                    <Input
                      type="number"
                      min="1"
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
                  <FormLabel>Primeira parcela</FormLabel>
                  <FormControl>
                    <Input type="date" {...field} />
                  </FormControl>
                  <FormDescription>Vencimento da primeira parcela.</FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="default_due_day"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Dia de vencimento</FormLabel>
                  <FormControl>
                    <Input
                      type="number"
                      min="1"
                      max="31"
                      value={Number.isNaN(field.value) ? '' : field.value}
                      onChange={(e) => field.onChange(e.target.valueAsNumber)}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <DialogFooter>
              <Button type="button" variant="outline" onClick={onClose}>
                Cancelar
              </Button>
              <Button type="submit" disabled={convertDeferred.isPending}>
                Converter
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
