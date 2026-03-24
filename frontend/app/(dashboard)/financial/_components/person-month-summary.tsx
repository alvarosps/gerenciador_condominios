'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Separator } from '@/components/ui/separator';
import { Button } from '@/components/ui/button';
import { Plus } from 'lucide-react';
import { usePersonSummary, type PersonSummary } from '@/lib/api/hooks/use-cash-flow';
import { formatCurrency } from '@/lib/utils/formatters';
import { cn } from '@/lib/utils';

interface PersonMonthSummaryProps {
  personId: number;
  personName: string;
  personRelationship: string;
  year: number;
  month: number;
  onRegisterPayment?: () => void;
  showPaymentButton?: boolean;
}

function SummarySkeleton() {
  return (
    <Card>
      <CardHeader className="pb-3">
        <Skeleton className="h-5 w-40" />
      </CardHeader>
      <CardContent className="space-y-3">
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-3/4" />
        <Skeleton className="h-4 w-1/2" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-2/3" />
      </CardContent>
    </Card>
  );
}

function formatMonthLabel(year: number, month: number): string {
  const date = new Date(year, month - 1);
  return date
    .toLocaleDateString('pt-BR', { month: 'long', year: 'numeric' })
    .replace(/^(\w)/, (c) => c.toUpperCase());
}

function formatPaymentDate(dateStr: string): string {
  const date = new Date(dateStr + 'T00:00:00');
  return date.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' });
}

function SummarySection({
  label,
  total,
  details,
  isNegative,
}: {
  label: string;
  total: number;
  details: { description: string; amount: number; extra?: string }[];
  isNegative?: boolean;
}) {
  if (total === 0 && details.length === 0) return null;

  return (
    <div className="space-y-1">
      <div className="flex justify-between text-sm font-medium">
        <span className="text-muted-foreground">{label}:</span>
        <span className={cn(isNegative && 'text-success')}>
          {isNegative ? '-' : ''}
          {formatCurrency(Math.abs(total))}
        </span>
      </div>
      {details.map((detail, i) => (
        <div key={i} className="flex justify-between text-xs pl-4 text-muted-foreground">
          <span className="truncate mr-2">
            {detail.description}
            {detail.extra ? ` ${detail.extra}` : ''}
          </span>
          <span className="whitespace-nowrap">
            {isNegative ? '-' : ''}
            {formatCurrency(Math.abs(detail.amount))}
          </span>
        </div>
      ))}
    </div>
  );
}

function SummaryContent({
  data,
  onRegisterPayment,
  showPaymentButton,
}: {
  data: PersonSummary;
  onRegisterPayment?: () => void;
  showPaymentButton?: boolean;
}) {
  return (
    <div className="space-y-3">
      <SummarySection
        label="Recebe"
        total={data.receives}
        details={data.receives_details.map((d) => ({
          description: d.description ?? d.source,
          amount: d.amount ?? d.rental_value ?? 0,
          extra:
            d.apartment_number && d.building_name
              ? `(Apt ${d.apartment_number} - ${d.building_name})`
              : undefined,
        }))}
      />

      <SummarySection
        label="Cartões"
        total={data.card_total}
        details={data.card_details.map((d) => ({
          description: d.description,
          amount: d.amount,
          extra: `${d.installment}${d.card_name ? ` (${d.card_name})` : ''}`,
        }))}
      />

      <SummarySection
        label="Empréstimos"
        total={data.loan_total}
        details={data.loan_details.map((d) => ({
          description: d.description,
          amount: d.amount,
          extra: d.installment,
        }))}
      />

      <SummarySection
        label="Gastos fixos"
        total={data.fixed_total}
        details={data.fixed_details.map((d) => ({
          description: d.description,
          amount: d.amount,
        }))}
      />

      {data.offset_total > 0 && (
        <SummarySection
          label="Descontos"
          total={data.offset_total}
          isNegative
          details={data.offset_details.map((d) => ({
            description: d.description,
            amount: d.amount,
            extra: d.installment ?? undefined,
          }))}
        />
      )}

      <Separator />

      <div className="space-y-1">
        <div className="flex justify-between text-sm font-semibold">
          <span>Total devido:</span>
          <span>{formatCurrency(data.net_amount)}</span>
        </div>
        <div className="flex justify-between text-sm">
          <span className="text-muted-foreground">Pago:</span>
          <span className="text-success">{formatCurrency(data.total_paid)}</span>
        </div>
        <div className="flex justify-between text-sm font-semibold">
          <span>Pendente:</span>
          <span
            className={cn(
              data.pending_balance === 0 && 'text-success',
              data.pending_balance > 0 && 'text-destructive',
              data.pending_balance < 0 && 'text-warning',
            )}
          >
            {formatCurrency(data.pending_balance)}
            {data.pending_balance === 0 && ' (quitado)'}
            {data.pending_balance < 0 && ' (pagou a mais)'}
          </span>
        </div>
      </div>

      {data.payment_details.length > 0 && (
        <>
          <Separator />
          <div className="space-y-1">
            <span className="text-sm font-medium text-muted-foreground">Pagamentos:</span>
            {data.payment_details.map((p, i) => (
              <div key={i} className="flex justify-between text-xs pl-4 text-muted-foreground">
                <span>
                  {formatPaymentDate(p.payment_date)}
                  {p.notes ? ` - ${p.notes}` : ''}
                </span>
                <span>{formatCurrency(p.amount)}</span>
              </div>
            ))}
          </div>
        </>
      )}

      {showPaymentButton && onRegisterPayment && (
        <Button variant="outline" size="sm" className="w-full mt-2" onClick={onRegisterPayment}>
          <Plus className="h-4 w-4 mr-1" />
          Registrar pagamento
        </Button>
      )}
    </div>
  );
}

export function PersonMonthSummary({
  personId,
  personName,
  personRelationship,
  year,
  month,
  onRegisterPayment,
  showPaymentButton = true,
}: PersonMonthSummaryProps) {
  const { data, isLoading, error } = usePersonSummary(personId, year, month);

  if (isLoading) return <SummarySkeleton />;

  if (error || !data) {
    return (
      <Card>
        <CardContent className="pt-6">
          <p className="text-center text-sm text-muted-foreground">
            Erro ao carregar resumo de {personName}
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3">
        <div className="flex items-center gap-2">
          <CardTitle className="text-base">
            {personName} - {formatMonthLabel(year, month)}
          </CardTitle>
        </div>
        <Badge variant="secondary">{personRelationship}</Badge>
      </CardHeader>
      <CardContent>
        <SummaryContent
          data={data}
          onRegisterPayment={onRegisterPayment}
          showPaymentButton={showPaymentButton}
        />
      </CardContent>
    </Card>
  );
}
