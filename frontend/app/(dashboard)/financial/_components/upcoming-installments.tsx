'use client';

import { Clock, CheckCircle2 } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { useUpcomingInstallments } from '@/lib/api/hooks/use-financial-dashboard';
import { useMarkInstallmentPaid } from '@/lib/api/hooks/use-expense-installments';
import { formatCurrency, formatDate } from '@/lib/utils/formatters';
import { cn } from '@/lib/utils';

function InstallmentSkeleton() {
  return (
    <div className="flex items-center justify-between p-3 border rounded-lg">
      <div className="space-y-1.5">
        <Skeleton className="h-4 w-40" />
        <Skeleton className="h-3 w-24" />
      </div>
      <Skeleton className="h-6 w-20" />
    </div>
  );
}

export function UpcomingInstallments() {
  const { data, isLoading, error } = useUpcomingInstallments(30);
  const markPaid = useMarkInstallmentPaid();

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Parcelas Próximas (30 dias)</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          <InstallmentSkeleton />
          <InstallmentSkeleton />
          <InstallmentSkeleton />
        </CardContent>
      </Card>
    );
  }

  if (error || !data) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Parcelas Próximas (30 dias)</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-center text-muted-foreground py-4">Erro ao carregar parcelas</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardHeader className="flex flex-row items-center justify-between space-y-0">
        <div className="flex items-center gap-2">
          <Clock className="h-5 w-5 text-muted-foreground" />
          <CardTitle className="text-base">Parcelas Próximas (30 dias)</CardTitle>
        </div>
        <Badge variant="secondary">{data.length}</Badge>
      </CardHeader>
      <CardContent>
        {data.length === 0 ? (
          <p className="text-center text-muted-foreground py-4">Nenhuma parcela nos próximos 30 dias</p>
        ) : (
          <div className="space-y-2 max-h-80 overflow-y-auto">
            {data.map((item) => {
              const daysUntilDue = item.days_until_due ?? 0;
              const isUrgent = daysUntilDue <= 7 && daysUntilDue >= 0;
              const isOverdue = daysUntilDue < 0;

              return (
                <div
                  key={item.id}
                  className={cn(
                    'flex items-center justify-between p-3 rounded-lg border transition-colors',
                    isOverdue && 'border-red-200 bg-red-50',
                    isUrgent && !isOverdue && 'border-yellow-200 bg-yellow-50',
                  )}
                >
                  <div className="flex-1 space-y-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-medium text-sm truncate">{item.expense_description}</span>
                      <Badge variant="outline" className="text-xs shrink-0">
                        {item.installment_number}/{item.total_installments}
                      </Badge>
                    </div>
                    <div className="flex items-center gap-2 text-xs text-muted-foreground flex-wrap">
                      <span>{formatDate(item.due_date)}</span>
                      {item.person_name && <span>· {item.person_name}</span>}
                      {item.credit_card_nickname && <span>· {item.credit_card_nickname}</span>}
                    </div>
                  </div>
                  <div className="flex items-center gap-2 shrink-0 ml-2">
                    <span className="font-bold text-sm">{formatCurrency(item.amount)}</span>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-7 w-7 p-0"
                      title="Marcar como pago"
                      onClick={() => markPaid.mutate(item.id)}
                      disabled={markPaid.isPending}
                    >
                      <CheckCircle2 className="h-4 w-4 text-green-600" />
                    </Button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
