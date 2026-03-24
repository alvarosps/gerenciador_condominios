'use client';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
  SheetFooter,
} from '@/components/ui/sheet';
import { CheckCircle, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';
import { type Expense } from '@/lib/schemas/expense.schema';
import { type ExpenseInstallment } from '@/lib/schemas/expense-installment.schema';
import {
  useExpenseInstallments,
  useMarkInstallmentPaid,
  useBulkMarkInstallmentsPaid,
} from '@/lib/api/hooks/use-expense-installments';
import { formatCurrency, formatDate } from '@/lib/utils/formatters';

interface Props {
  open: boolean;
  expense: Expense | null;
  onClose: () => void;
}

function getInstallmentStatus(installment: ExpenseInstallment): {
  label: string;
  className: string;
} {
  if (installment.is_paid) {
    return { label: 'Pago', className: 'bg-success/10 text-success' };
  }
  if (installment.is_overdue) {
    return { label: 'Vencido', className: 'bg-destructive/10 text-destructive' };
  }
  return { label: 'Pendente', className: 'bg-warning/10 text-warning' };
}

export function InstallmentsDrawer({ open, expense, onClose }: Props) {
  const { data: installments, isLoading } = useExpenseInstallments(
    expense?.id ? { expense_id: expense.id } : undefined,
  );
  const markPaidMutation = useMarkInstallmentPaid();
  const bulkMarkPaidMutation = useBulkMarkInstallmentsPaid();

  const unpaidInstallments = installments?.filter((i) => !i.is_paid) ?? [];
  const hasUnpaid = unpaidInstallments.length > 0;

  const handleMarkPaid = async (installmentId: number) => {
    try {
      await markPaidMutation.mutateAsync(installmentId);
      toast.success('Parcela marcada como paga');
    } catch {
      toast.error('Erro ao marcar parcela como paga');
    }
  };

  const handleMarkAllPaid = async () => {
    const ids = unpaidInstallments
      .map((i) => i.id)
      .filter((id): id is number => id !== undefined);
    if (ids.length === 0) return;

    try {
      await bulkMarkPaidMutation.mutateAsync(ids);
      toast.success(`${ids.length} parcelas marcadas como pagas`);
    } catch {
      toast.error('Erro ao marcar parcelas como pagas');
    }
  };

  return (
    <Sheet open={open} onOpenChange={onClose}>
      <SheetContent side="right" className="w-full sm:max-w-lg overflow-y-auto">
        <SheetHeader>
          <SheetTitle>{expense?.description}</SheetTitle>
          <SheetDescription>
            {expense?.expense_type} &middot; {formatCurrency(expense?.total_amount)}
          </SheetDescription>
        </SheetHeader>

        <div className="mt-6 space-y-3">
          {isLoading && (
            <div className="flex justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          )}

          {installments?.map((installment) => {
            const status = getInstallmentStatus(installment);
            const installmentId = installment.id;
            return (
              <div
                key={installmentId}
                className="flex items-center justify-between rounded-md border p-3"
              >
                <div className="space-y-1">
                  <div className="font-medium">
                    {installment.installment_number}/{installment.total_installments}
                  </div>
                  <div className="text-sm text-muted-foreground">
                    {formatCurrency(installment.amount)} &middot; {formatDate(installment.due_date)}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Badge className={cn(status.className)}>{status.label}</Badge>
                  {!installment.is_paid && installmentId !== undefined && (
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => void handleMarkPaid(installmentId)}
                      disabled={markPaidMutation.isPending}
                    >
                      <CheckCircle className="h-4 w-4" />
                    </Button>
                  )}
                </div>
              </div>
            );
          })}

          {!isLoading && installments?.length === 0 && (
            <p className="text-center text-sm text-muted-foreground py-8">
              Nenhuma parcela encontrada
            </p>
          )}
        </div>

        {hasUnpaid && (
          <SheetFooter className="mt-6">
            <Button
              onClick={handleMarkAllPaid}
              disabled={bulkMarkPaidMutation.isPending}
              className="w-full"
            >
              {bulkMarkPaidMutation.isPending && (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              )}
              Marcar todas como pagas ({unpaidInstallments.length})
            </Button>
          </SheetFooter>
        )}
      </SheetContent>
    </Sheet>
  );
}
