'use client';

import { CreditCard, Landmark, User, ArrowDown, ArrowUp, Minus } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { usePersons } from '@/lib/api/hooks/use-persons';
import { usePersonSummary } from '@/lib/api/hooks/use-cash-flow';
import { formatCurrency } from '@/lib/utils/formatters';
import { cn } from '@/lib/utils';

function PersonCardSkeleton() {
  return (
    <Card>
      <CardHeader className="pb-3">
        <Skeleton className="h-5 w-32" />
      </CardHeader>
      <CardContent className="space-y-2">
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-3/4" />
        <Skeleton className="h-4 w-1/2" />
      </CardContent>
    </Card>
  );
}

function PersonSummaryCard({ personId, personName }: { personId: number; personName: string }) {
  const now = new Date();
  const { data, isLoading } = usePersonSummary(personId, now.getFullYear(), now.getMonth() + 1);

  if (isLoading) return <PersonCardSkeleton />;
  if (!data) return null;

  const deductions = data.card_total + data.loan_total + data.fixed_total;

  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3">
        <div className="flex items-center gap-2">
          <User className="h-4 w-4 text-muted-foreground" />
          <CardTitle className="text-base">{personName}</CardTitle>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex items-center justify-between text-sm">
          <span className="flex items-center gap-1.5 text-muted-foreground">
            <ArrowDown className="h-3.5 w-3.5 text-blue-500" />
            Recebe
          </span>
          <span className="font-medium">{formatCurrency(data.receives)}</span>
        </div>

        <div className="flex items-center justify-between text-sm">
          <span className="flex items-center gap-1.5 text-muted-foreground">
            <CreditCard className="h-3.5 w-3.5" />
            Cartões
          </span>
          <span className="font-medium">{formatCurrency(data.card_total)}</span>
        </div>

        <div className="flex items-center justify-between text-sm">
          <span className="flex items-center gap-1.5 text-muted-foreground">
            <Landmark className="h-3.5 w-3.5" />
            Empréstimos
          </span>
          <span className="font-medium">{formatCurrency(data.loan_total)}</span>
        </div>

        {data.fixed_total > 0 && (
          <div className="flex items-center justify-between text-sm">
            <span className="flex items-center gap-1.5 text-muted-foreground">
              <Minus className="h-3.5 w-3.5" />
              Fixos
            </span>
            <span className="font-medium">{formatCurrency(data.fixed_total)}</span>
          </div>
        )}

        {data.offset_total > 0 && (
          <div className="flex items-center justify-between text-sm">
            <span className="flex items-center gap-1.5 text-muted-foreground">
              <ArrowUp className="h-3.5 w-3.5 text-green-500" />
              Descontos
            </span>
            <span className="font-medium text-green-600">-{formatCurrency(data.offset_total)}</span>
          </div>
        )}

        <div className="border-t pt-2 flex items-center justify-between text-sm">
          <span className="text-muted-foreground">Deduções</span>
          <span className="font-medium">{formatCurrency(deductions)}</span>
        </div>

        <div className="border-t pt-2 flex items-center justify-between text-sm">
          <span className="text-muted-foreground font-semibold">Net</span>
          <span
            className={cn(
              'font-bold',
              data.net_amount > 0 ? 'text-red-600' : 'text-green-600',
            )}
          >
            {formatCurrency(data.net_amount)}
          </span>
        </div>

        {(data.total_paid > 0 || data.pending_balance !== data.net_amount) && (
          <div className="border-t pt-2 space-y-1">
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Pago</span>
              <span className="text-green-600">{formatCurrency(data.total_paid)}</span>
            </div>
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Pendente</span>
              <Badge
                variant={
                  data.pending_balance === 0
                    ? 'default'
                    : data.pending_balance > 0
                      ? 'destructive'
                      : 'secondary'
                }
              >
                {formatCurrency(data.pending_balance)}
              </Badge>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export function PersonSummaryCards() {
  const { data: persons, isLoading, error } = usePersons();

  if (isLoading) {
    return (
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <PersonCardSkeleton />
        <PersonCardSkeleton />
        <PersonCardSkeleton />
      </div>
    );
  }

  if (error || !persons) {
    return (
      <Card>
        <CardContent className="pt-6">
          <p className="text-center text-muted-foreground">Erro ao carregar resumo por pessoa</p>
        </CardContent>
      </Card>
    );
  }

  const relevantPersons = persons.filter((p) => !p.is_employee);

  if (relevantPersons.length === 0) {
    return (
      <Card>
        <CardContent className="pt-6">
          <p className="text-center text-muted-foreground">Nenhuma pessoa cadastrada</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-3">
      <h2 className="text-lg font-semibold">Resumo por Pessoa</h2>
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {relevantPersons.map((person) => (
          <PersonSummaryCard
            key={person.id}
            personId={person.id ?? 0}
            personName={person.name}
          />
        ))}
      </div>
    </div>
  );
}
