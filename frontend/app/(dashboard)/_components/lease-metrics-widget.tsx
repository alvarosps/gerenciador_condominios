'use client';

import { FileText, Clock, XCircle, CheckCircle, AlertTriangle } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Loading } from '@/components/shared/loading';
import { Progress } from '@/components/ui/progress';
import { useDashboardLeaseMetrics } from '@/lib/api/hooks/use-dashboard';
import { cn } from '@/lib/utils';

interface MetricItemProps {
  title: string;
  value: number;
  suffix?: string;
  icon?: React.ReactNode;
  valueColor?: string;
  description?: string;
}

function MetricItem({
  title,
  value,
  suffix = '',
  icon,
  valueColor,
  description,
}: MetricItemProps) {
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-muted-foreground">{title}</span>
        {icon && <div className="h-4 w-4 text-muted-foreground">{icon}</div>}
      </div>
      <div className={cn('text-2xl font-bold', valueColor)}>
        {value}
        {suffix && <span className="text-lg ml-1">{suffix}</span>}
      </div>
      {description && (
        <p className="text-xs text-muted-foreground">{description}</p>
      )}
    </div>
  );
}

export function LeaseMetricsWidget() {
  const { data, isLoading, error } = useDashboardLeaseMetrics();

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Métricas de Locações</CardTitle>
        </CardHeader>
        <CardContent>
          <Loading />
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Métricas de Locações</CardTitle>
        </CardHeader>
        <CardContent>
          <Alert variant="destructive">
            <AlertTriangle className="h-4 w-4" />
            <AlertDescription>Erro ao carregar métricas</AlertDescription>
          </Alert>
        </CardContent>
      </Card>
    );
  }

  if (!data) return null;

  const activePercentage = data.total_leases > 0
    ? (data.active_leases / data.total_leases) * 100
    : 0;

  // const getProgressColor = (percentage: number): string => {
  //   if (percentage >= 80) return 'bg-green-600';
  //   if (percentage >= 50) return 'bg-blue-500';
  //   return 'bg-red-500';
  // };

  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardHeader>
        <CardTitle>Métricas de Locações</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
          <div className="space-y-3">
            <MetricItem
              title="Locações Ativas"
              value={data.active_leases}
              suffix={`/ ${data.total_leases}`}
              icon={<FileText />}
              valueColor="text-green-600"
            />
            <div className="space-y-2">
              <Progress
                value={activePercentage}
                className="h-2"
              />
              <p className="text-xs text-muted-foreground">
                Taxa de ocupação das locações
              </p>
            </div>
          </div>

          <MetricItem
            title="Expirando em Breve"
            value={data.expiring_soon}
            icon={<Clock />}
            valueColor={data.expiring_soon > 0 ? 'text-orange-500' : 'text-green-500'}
            description="Locações que expiram em até 30 dias"
          />

          <MetricItem
            title="Locações Expiradas"
            value={data.expired_leases}
            icon={<XCircle />}
            valueColor="text-red-600"
            description="Contratos que já venceram"
          />

          <MetricItem
            title="Contratos Pendentes"
            value={data.contracts_pending}
            icon={<CheckCircle />}
            valueColor={data.contracts_pending > 0 ? 'text-orange-500' : 'text-green-500'}
            description="Locações sem contrato gerado"
          />
        </div>

        <div className="mt-6 pt-4 border-t">
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">Total de Contratos:</span>
            <span className="font-bold">{data.total_leases}</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
