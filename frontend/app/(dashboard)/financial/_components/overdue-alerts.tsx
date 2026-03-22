'use client';

import { AlertTriangle, CheckCircle2 } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { useOverdueInstallments } from '@/lib/api/hooks/use-financial-dashboard';
import { formatCurrency } from '@/lib/utils/formatters';

function OverdueSkeleton() {
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

export function OverdueAlerts() {
  const { data, isLoading, error } = useOverdueInstallments();

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Parcelas Vencidas</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          <OverdueSkeleton />
          <OverdueSkeleton />
        </CardContent>
      </Card>
    );
  }

  if (error || !data) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Parcelas Vencidas</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-center text-muted-foreground py-4">Erro ao carregar alertas</p>
        </CardContent>
      </Card>
    );
  }

  if (data.length === 0) {
    return (
      <Card className="hover:shadow-md transition-shadow">
        <CardHeader className="flex flex-row items-center justify-between space-y-0">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="h-5 w-5 text-green-600" />
            <CardTitle className="text-base">Parcelas Vencidas</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <Alert className="border-green-200 bg-green-50">
            <CheckCircle2 className="h-4 w-4 text-green-600" />
            <AlertDescription className="text-green-800">
              Nenhuma parcela vencida. Tudo em dia!
            </AlertDescription>
          </Alert>
        </CardContent>
      </Card>
    );
  }

  const sorted = [...data].sort((a, b) => (b.days_overdue ?? 0) - (a.days_overdue ?? 0));

  return (
    <Card className="hover:shadow-md transition-shadow border-red-200">
      <CardHeader className="flex flex-row items-center justify-between space-y-0">
        <div className="flex items-center gap-2">
          <AlertTriangle className="h-5 w-5 text-red-500" />
          <CardTitle className="text-base">Parcelas Vencidas</CardTitle>
        </div>
        <Badge variant="destructive">{data.length}</Badge>
      </CardHeader>
      <CardContent>
        <div className="space-y-2 max-h-80 overflow-y-auto">
          {sorted.map((item) => (
            <div
              key={item.id}
              className="flex items-center justify-between p-3 rounded-lg border border-red-200 bg-red-50 transition-colors"
            >
              <div className="flex-1 space-y-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="font-medium text-sm truncate">{item.expense_description}</span>
                  <Badge variant="destructive" className="text-xs shrink-0">
                    {item.days_overdue} {item.days_overdue === 1 ? 'dia' : 'dias'} de atraso
                  </Badge>
                </div>
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  {item.person_name && <span>{item.person_name}</span>}
                  {item.credit_card_nickname && <span>· {item.credit_card_nickname}</span>}
                </div>
              </div>
              <span className="font-bold text-sm text-red-600 shrink-0 ml-2">
                {formatCurrency(item.amount)}
              </span>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
