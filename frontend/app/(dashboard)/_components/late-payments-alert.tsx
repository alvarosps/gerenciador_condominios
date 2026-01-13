'use client';

import { AlertTriangle, Eye, CheckCircle2 } from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { useDashboardLatePayments } from '@/lib/api/hooks/use-dashboard';
import { formatCurrency } from '@/lib/utils/formatters';
import Link from 'next/link';

export function LatePaymentsAlert() {
  const { data, isLoading } = useDashboardLatePayments();

  if (isLoading) return null;

  if (!data || data.total_late_leases === 0) {
    return (
      <Alert className="border-green-200 bg-green-50">
        <CheckCircle2 className="h-4 w-4 text-green-600" />
        <AlertDescription className="text-green-800">
          <strong>Parabéns!</strong> Não há pagamentos em atraso. Todos os inquilinos estão em dia com os pagamentos.
        </AlertDescription>
      </Alert>
    );
  }

  const totalLateFees = parseFloat(data.total_late_fees) || 0;

  return (
    <Card className="border-red-200">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-red-500" />
            <CardTitle className="text-lg">Pagamentos em Atraso</CardTitle>
            <Badge variant="destructive">{data.total_late_leases}</Badge>
          </div>
          <div className="text-right">
            <div className="text-xs text-muted-foreground">Total em Multas</div>
            <div className="text-lg font-bold text-red-600">
              {formatCurrency(totalLateFees)}
            </div>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {data.late_leases.map((item, index) => (
            <div
              key={index}
              className="flex items-center justify-between p-3 rounded-lg border bg-card hover:bg-muted/50 transition-colors"
            >
              <div className="flex-1 space-y-1">
                <div className="flex items-center gap-2">
                  <span className="font-medium">{item.tenant_name}</span>
                  <Badge variant="destructive">
                    {item.late_days} dias de atraso
                  </Badge>
                </div>
                <div className="text-sm text-muted-foreground">
                  <span className="font-medium">
                    Prédio {item.building_number} - Apto {item.apartment_number}
                  </span>
                </div>
                <div className="text-sm">
                  <span className="text-muted-foreground">Multa: </span>
                  <span className="font-bold text-red-600">
                    {formatCurrency(parseFloat(item.late_fee) || 0)}
                  </span>
                </div>
              </div>
              <Link href="/leases">
                <Button variant="ghost" size="sm">
                  <Eye className="h-4 w-4 mr-2" />
                  Ver Locação
                </Button>
              </Link>
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
      </CardContent>
    </Card>
  );
}
