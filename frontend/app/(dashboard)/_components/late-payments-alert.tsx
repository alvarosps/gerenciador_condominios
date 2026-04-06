'use client';

import { AlertTriangle, CheckCircle2, Check, Eye } from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  useDashboardLatePayments,
  useMarkRentPaid,
} from '@/lib/api/hooks/use-dashboard';
import { formatCurrency } from '@/lib/utils/formatters';
import { handleError } from '@/lib/utils/error-handler';
import Link from 'next/link';
import { toast } from 'sonner';

function formatDate(dateStr: string | null): string {
  if (!dateStr) return 'Nenhum';
  const [year, month, day] = dateStr.split('-');
  return `${day}/${month}/${year}`;
}

export function LatePaymentsAlert() {
  const { data, isLoading } = useDashboardLatePayments();
  const markPaid = useMarkRentPaid();

  if (isLoading) return null;

  if (!data || data.total_late_leases === 0) {
    return (
      <Alert className="border-success/20 bg-success/10">
        <CheckCircle2 className="h-4 w-4 text-success" />
        <AlertDescription className="text-success-foreground">
          <strong>Parabéns!</strong> Não há pagamentos em atraso. Todos os inquilinos estão em dia
          com os pagamentos.
        </AlertDescription>
      </Alert>
    );
  }

  const totalLateFees = parseFloat(data.total_late_fees) || 0;

  function handleMarkPaid(leaseId: number) {
    markPaid.mutate(leaseId, {
      onSuccess: (result) => {
        toast.success(result.message);
      },
      onError: (error) => {
        handleError(error, 'Erro ao marcar como pago');
      },
    });
  }

  return (
    <Accordion type="single" collapsible>
      <AccordionItem value="late-payments" className="border-destructive/20 rounded-lg border">
        <AccordionTrigger className="px-6 py-4 hover:no-underline">
          <div className="mr-4 flex w-full flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-destructive" />
              <span className="text-lg font-semibold">Pagamentos em Atraso</span>
              <Badge variant="destructive">{data.total_late_leases}</Badge>
            </div>
            <div className="text-right">
              <div className="text-xs text-muted-foreground">Total em Multas</div>
              <div className="text-lg font-bold text-destructive">
                {formatCurrency(totalLateFees)}
              </div>
            </div>
          </div>
        </AccordionTrigger>
        <AccordionContent className="px-6 pb-4">
          <div className="space-y-3">
            {data.late_leases.map((item) => (
              <div
                key={item.lease_id}
                className="flex items-center justify-between gap-4 rounded-lg border bg-card p-3 transition-colors hover:bg-muted/50"
              >
                <div className="flex-1 space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="font-medium">{item.tenant_name}</span>
                    <Badge variant="destructive">{item.late_days} dias de atraso</Badge>
                  </div>
                  <div className="text-sm text-muted-foreground">
                    <span className="font-medium">
                      Prédio {item.building_number} - Apto {item.apartment_number}
                    </span>
                  </div>
                  <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm">
                    <span>
                      <span className="text-muted-foreground">Vencimento: </span>
                      <span className="font-medium">Dia {item.due_day}</span>
                    </span>
                    <span>
                      <span className="text-muted-foreground">Último pagamento: </span>
                      <span className="font-medium">
                        {formatDate(item.last_payment_date)}
                      </span>
                    </span>
                    <span>
                      <span className="text-muted-foreground">Multa: </span>
                      <span className="font-bold text-destructive">
                        {formatCurrency(parseFloat(item.late_fee) || 0)}
                      </span>
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    variant="default"
                    size="sm"
                    onClick={() => handleMarkPaid(item.lease_id)}
                    disabled={markPaid.isPending}
                  >
                    <Check className="mr-1 h-4 w-4" />
                    Pago
                  </Button>
                  <Link href="/leases">
                    <Button variant="ghost" size="sm">
                      <Eye className="mr-2 h-4 w-4" />
                      Ver Locação
                    </Button>
                  </Link>
                </div>
              </div>
            ))}
          </div>

          {data.late_leases.length > 5 && (
            <div className="mt-4 text-center">
              <Link href="/leases">
                <Button variant="link">Ver todas as locações</Button>
              </Link>
            </div>
          )}
        </AccordionContent>
      </AccordionItem>
    </Accordion>
  );
}
