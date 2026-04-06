'use client';

import { useState, useEffect } from 'react';
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Skeleton } from '@/components/ui/skeleton';
import { useMarkItemPaid } from '@/lib/api/hooks/use-daily-control';
import {
  usePersonMonthTotal,
  usePersonPaymentSchedules,
} from '@/lib/api/hooks/use-person-payment-schedules';
import { formatCurrency } from '@/lib/utils/formatters';
import { toast } from 'sonner';

export interface PersonPayModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  personId: number;
  personName: string;
  referenceMonth: string;
  dueDay: number;
  scheduleAmount: number;
  paymentDate: string;
}

export function PersonPayModal({
  open,
  onOpenChange,
  personId,
  personName,
  referenceMonth,
  dueDay,
  scheduleAmount,
  paymentDate,
}: PersonPayModalProps) {
  const { data: monthTotal, isLoading: isLoadingTotal } = usePersonMonthTotal(
    personId,
    referenceMonth,
  );
  const { data: schedules, isLoading: isLoadingSchedules } = usePersonPaymentSchedules({
    person_id: personId,
    reference_month: referenceMonth,
  });

  const markPaidMutation = useMarkItemPaid();

  const expectedUntilDay =
    schedules?.reduce(
      (sum, s) => (s.due_day <= dueDay ? sum + s.amount : sum),
      0,
    ) ?? scheduleAmount;

  const totalPaid = monthTotal?.total_paid ?? 0;
  const suggestedAmount = Math.max(0, expectedUntilDay - totalPaid);

  const [amount, setAmount] = useState('');

  useEffect(() => {
    if (open) {
      setAmount(suggestedAmount.toFixed(2));
    }
  }, [open, suggestedAmount]);

  const handleConfirm = async () => {
    const numericAmount = parseFloat(amount);
    if (isNaN(numericAmount) || numericAmount < 0) {
      toast.error('Informe um valor válido');
      return;
    }

    const [yearStr, monthStr] = referenceMonth.split('-');
    const year = parseInt(yearStr ?? '0');
    const month = parseInt(monthStr ?? '0');

    try {
      await markPaidMutation.mutateAsync({
        item_type: 'person_schedule',
        item_id: personId,
        payment_date: paymentDate,
        person_id: personId,
        amount: numericAmount,
        year,
        month,
      });
      toast.success(`Pagamento de ${formatCurrency(numericAmount)} registrado para ${personName}`);
      onOpenChange(false);
    } catch {
      toast.error('Erro ao registrar pagamento');
    }
  };

  const handleConfirmSync = () => {
    void handleConfirm();
  };

  const isLoading = isLoadingTotal || isLoadingSchedules;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Pagamento — {personName}</DialogTitle>
        </DialogHeader>

        <div className="space-y-4 py-2">
          {isLoading ? (
            <div className="space-y-2">
              <Skeleton className="h-5 w-full" />
              <Skeleton className="h-5 w-full" />
              <Skeleton className="h-5 w-3/4" />
            </div>
          ) : (
            <div className="space-y-2 rounded-lg border p-3 bg-muted/30 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Esperado até dia {dueDay}:</span>
                <span className="font-medium">{formatCurrency(expectedUntilDay)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Já pago no mês:</span>
                <span className="font-medium text-success">{formatCurrency(totalPaid)}</span>
              </div>
              <div className="flex justify-between border-t pt-2">
                <span className="text-muted-foreground">Valor sugerido:</span>
                <span className="font-bold">{formatCurrency(suggestedAmount)}</span>
              </div>
            </div>
          )}

          <div className="space-y-1.5">
            <Label htmlFor="pay-amount">Valor a registrar (R$)</Label>
            <Input
              id="pay-amount"
              type="number"
              min="0"
              step="0.01"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              placeholder="0,00"
              disabled={markPaidMutation.isPending}
            />
          </div>
        </div>

        <DialogFooter className="gap-2">
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={markPaidMutation.isPending}
          >
            Cancelar
          </Button>
          <Button
            onClick={handleConfirmSync}
            disabled={markPaidMutation.isPending || isLoading}
          >
            {markPaidMutation.isPending ? 'Registrando...' : 'Confirmar Pagamento'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
