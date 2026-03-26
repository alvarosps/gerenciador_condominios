'use client';

import { TrendingUp, CheckCircle2 } from 'lucide-react';
import { format } from 'date-fns';
import { ptBR } from 'date-fns/locale';
import Link from 'next/link';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { useRentAdjustmentAlerts } from '@/lib/api/hooks/use-rent-adjustments';
import { formatCurrency } from '@/lib/utils/formatters';
import type { RentAdjustmentAlert } from '@/lib/schemas/rent-adjustment.schema';

function StatusBadge({ alert }: { alert: RentAdjustmentAlert }) {
  if (alert.status === 'overdue') {
    return (
      <Badge variant="destructive">
        Atrasado {Math.abs(alert.days_until)} dias
      </Badge>
    );
  }
  return (
    <Badge className="bg-yellow-100 text-yellow-800 hover:bg-yellow-100">
      Em {alert.days_until} dias
    </Badge>
  );
}

function LastAdjustmentText({ alert }: { alert: RentAdjustmentAlert }) {
  if (!alert.last_adjustment) {
    return <span className="text-muted-foreground text-sm">Nunca reajustado</span>;
  }
  const date = format(new Date(alert.last_adjustment.adjustment_date), 'dd/MM/yyyy', {
    locale: ptBR,
  });
  return (
    <span className="text-muted-foreground text-sm">Último reajuste: {date}</span>
  );
}

export function RentAdjustmentAlerts() {
  const { data, isLoading } = useRentAdjustmentAlerts();

  if (isLoading) return null;

  if (!data || data.length === 0) {
    return (
      <Alert className="border-success/20 bg-success/10">
        <CheckCircle2 className="h-4 w-4 text-success" />
        <AlertDescription className="text-success-foreground">
          Nenhum reajuste pendente. Todos os contratos estão em dia.
        </AlertDescription>
      </Alert>
    );
  }

  return (
    <Accordion type="single" collapsible>
      <AccordionItem value="rent-adjustments" className="border-yellow-400/30 rounded-lg border">
        <AccordionTrigger className="px-6 py-4 hover:no-underline">
          <div className="flex items-center gap-2 w-full mr-4">
            <TrendingUp className="h-5 w-5 text-yellow-600" />
            <span className="text-lg font-semibold">Reajustes Pendentes</span>
            <Badge className="bg-yellow-100 text-yellow-800 hover:bg-yellow-100">
              {data.length}
            </Badge>
          </div>
        </AccordionTrigger>
        <AccordionContent className="px-6 pb-4">
          <div className="space-y-3">
            {data.map((alert) => (
              <div
                key={alert.lease_id}
                className="flex items-center justify-between p-3 rounded-lg border bg-card hover:bg-muted/50 transition-colors"
              >
                <div className="flex-1 space-y-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-medium">{alert.apartment}</span>
                    <span className="text-muted-foreground text-sm">— {alert.tenant}</span>
                    <StatusBadge alert={alert} />
                    {alert.prepaid_warning && (
                      <Badge variant="outline">Pré-pago</Badge>
                    )}
                  </div>
                  <div className="text-sm">
                    <span className="text-muted-foreground">Aluguel atual: </span>
                    <span className="font-medium">{formatCurrency(alert.rental_value)}</span>
                  </div>
                  <LastAdjustmentText alert={alert} />
                </div>
                <Link href="/leases">
                  <Button variant="ghost" size="sm">
                    <TrendingUp className="h-4 w-4 mr-2" />
                    Reajustar
                  </Button>
                </Link>
              </div>
            ))}
          </div>
        </AccordionContent>
      </AccordionItem>
    </Accordion>
  );
}
