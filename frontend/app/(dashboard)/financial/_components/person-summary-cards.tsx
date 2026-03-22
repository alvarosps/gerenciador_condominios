'use client';

import { CreditCard, Landmark, User } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { useDebtByPerson } from '@/lib/api/hooks/use-financial-dashboard';
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

export function PersonSummaryCards() {
  const { data, isLoading, error } = useDebtByPerson();

  if (isLoading) {
    return (
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <PersonCardSkeleton />
        <PersonCardSkeleton />
        <PersonCardSkeleton />
      </div>
    );
  }

  if (error || !data) {
    return (
      <Card>
        <CardContent className="pt-6">
          <p className="text-center text-muted-foreground">Erro ao carregar resumo por pessoa</p>
        </CardContent>
      </Card>
    );
  }

  if (data.length === 0) {
    return (
      <Card>
        <CardContent className="pt-6">
          <p className="text-center text-muted-foreground">Nenhuma pessoa com despesas registradas</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-3">
      <h2 className="text-lg font-semibold">Resumo por Pessoa</h2>
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {data.map((person) => {
          const monthlyTotal = (typeof person.monthly_card === 'string' ? parseFloat(person.monthly_card) : person.monthly_card)
            + (typeof person.monthly_loan === 'string' ? parseFloat(person.monthly_loan) : person.monthly_loan);

          return (
            <Card key={person.person_id} className="hover:shadow-md transition-shadow">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3">
                <div className="flex items-center gap-2">
                  <User className="h-4 w-4 text-muted-foreground" />
                  <CardTitle className="text-base">{person.person_name}</CardTitle>
                </div>
                {person.cards_count > 0 && (
                  <Badge variant="secondary">
                    {person.cards_count} {person.cards_count === 1 ? 'cartão' : 'cartões'}
                  </Badge>
                )}
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex items-center justify-between text-sm">
                  <span className="flex items-center gap-1.5 text-muted-foreground">
                    <CreditCard className="h-3.5 w-3.5" />
                    Cartões (mês)
                  </span>
                  <span className="font-medium">{formatCurrency(person.monthly_card)}</span>
                </div>

                <div className="flex items-center justify-between text-sm">
                  <span className="flex items-center gap-1.5 text-muted-foreground">
                    <Landmark className="h-3.5 w-3.5" />
                    Empréstimos (mês)
                  </span>
                  <span className="font-medium">{formatCurrency(person.monthly_loan)}</span>
                </div>

                <div className="border-t pt-2 flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">Total do Mês</span>
                  <span className={cn('font-bold', monthlyTotal > 0 ? 'text-red-600' : 'text-green-600')}>
                    {formatCurrency(monthlyTotal)}
                  </span>
                </div>

                <div className="border-t pt-2 flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">Dívida Total</span>
                  <span className="font-bold text-red-600">{formatCurrency(person.total_debt)}</span>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
