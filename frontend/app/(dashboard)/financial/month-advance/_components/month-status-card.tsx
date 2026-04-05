'use client';

import { AlertTriangle, CheckCircle2, Clock } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import type { MonthStatus, ValidationItem } from '@/lib/api/hooks/use-month-advance';
import { formatCurrency, formatMonthYear } from '@/lib/utils/formatters';
import { cn } from '@/lib/utils';

interface ChecklistRowProps {
  label: string;
  items: ValidationItem[];
  renderItem: (item: ValidationItem, index: number) => React.ReactNode;
}

function ChecklistRow({ label, items, renderItem }: ChecklistRowProps) {
  const isOk = items.length === 0;

  return (
    <div className="space-y-1">
      <div className="flex items-center gap-2">
        {isOk ? (
          <CheckCircle2 className="h-4 w-4 text-success flex-shrink-0" />
        ) : (
          <AlertTriangle className="h-4 w-4 text-warning flex-shrink-0" />
        )}
        <span className={cn('text-sm font-medium', isOk ? 'text-success' : 'text-warning')}>
          {label}
        </span>
        {!isOk && (
          <Badge variant="secondary" className="ml-auto text-xs">
            {items.length}
          </Badge>
        )}
      </div>

      {!isOk && (
        <ul className="ml-6 space-y-0.5">
          {items.map((item, index) => (
            <li key={index} className="text-xs text-muted-foreground">
              {renderItem(item, index)}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

interface MonthStatusCardProps {
  status: MonthStatus | undefined;
  isLoading: boolean;
  year: number;
  month: number;
}

export function MonthStatusCard({ status, isLoading, year, month }: MonthStatusCardProps) {
  const monthLabel = formatMonthYear(year, month);

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <Skeleton className="h-5 w-48" />
          <Skeleton className="h-4 w-32 mt-1" />
        </CardHeader>
        <CardContent className="space-y-3">
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-3/4" />
        </CardContent>
      </Card>
    );
  }

  if (!status) {
    return (
      <Card>
        <CardContent className="pt-6">
          <p className="text-center text-muted-foreground text-sm">
            Erro ao carregar status do mês
          </p>
        </CardContent>
      </Card>
    );
  }

  const { validation } = status;

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">{monthLabel}</CardTitle>
          {status.is_finalized ? (
            <Badge className="bg-success/10 text-success border-success/20 gap-1">
              <CheckCircle2 className="h-3 w-3" />
              Finalizado
            </Badge>
          ) : (
            <Badge variant="secondary" className="gap-1">
              <Clock className="h-3 w-3" />
              Em aberto
            </Badge>
          )}
        </div>
        <CardDescription>
          {status.is_finalized
            ? 'Este mês foi finalizado e está protegido contra edições.'
            : validation.has_warnings
              ? `${String(validation.warning_count)} pendência${validation.warning_count !== 1 ? 's' : ''} encontrada${validation.warning_count !== 1 ? 's' : ''}`
              : 'Tudo verificado — pronto para finalizar'}
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-3">
        <ChecklistRow
          label="Aluguéis recebidos"
          items={validation.unpaid_rent}
          renderItem={(item) =>
            `Apto ${item.apartment ?? ''} — ${item.tenant ?? ''} (${formatCurrency(item.rental_value ?? 0)})`
          }
        />

        <ChecklistRow
          label="Parcelas pagas"
          items={validation.unpaid_installments}
          renderItem={(item) =>
            `${item.description ?? ''} ${item.installment ?? ''} — ${formatCurrency(item.amount ?? 0)}${item.person ? ` (${item.person})` : ''}`
          }
        />

        <ChecklistRow
          label="Contas de água e luz"
          items={validation.missing_utility_bills}
          renderItem={(item) => item.label ?? item.type ?? ''}
        />

        <ChecklistRow
          label="Funcionários pagos"
          items={validation.unpaid_employees}
          renderItem={(item) =>
            `${item.name ?? ''} — ${item.status === 'not_created' ? 'não criado' : 'não pago'}`
          }
        />

        <ChecklistRow
          label="Pagamentos programados"
          items={validation.unpaid_person_schedules}
          renderItem={(item) =>
            `${item.person_name ?? ''} — falta ${formatCurrency(item.remaining ?? 0)}`
          }
        />
      </CardContent>
    </Card>
  );
}
