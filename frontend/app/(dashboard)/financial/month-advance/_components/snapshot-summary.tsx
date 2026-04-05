'use client';

import { ArrowDownRight, ArrowUpRight, Minus, TrendingDown, TrendingUp } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import type { MonthSnapshotDetail } from '@/lib/api/hooks/use-month-advance';
import { formatCurrency, formatDate, formatMonthYear } from '@/lib/utils/formatters';
import { cn } from '@/lib/utils';

interface SnapshotSummaryProps {
  snapshot: MonthSnapshotDetail;
}

interface SummaryRowProps {
  label: string;
  value: string | number;
  sublabel?: string;
  variant?: 'default' | 'income' | 'expense' | 'balance';
}

function SummaryRow({ label, value, sublabel, variant = 'default' }: SummaryRowProps) {
  const colorClass = {
    default: 'text-foreground',
    income: 'text-info',
    expense: 'text-warning',
    balance:
      parseFloat(String(value)) >= 0 ? 'text-success' : 'text-destructive',
  }[variant];

  return (
    <div className="flex items-center justify-between py-1">
      <div>
        <span className="text-sm">{label}</span>
        {sublabel && <p className="text-xs text-muted-foreground">{sublabel}</p>}
      </div>
      <span className={cn('text-sm font-medium', colorClass)}>
        {formatCurrency(value)}
      </span>
    </div>
  );
}

export function SnapshotSummary({ snapshot }: SnapshotSummaryProps) {
  const refMonth = snapshot.reference_month
    ? (() => {
        const d = new Date(snapshot.reference_month + 'T00:00:00');
        return formatMonthYear(d.getFullYear(), d.getMonth() + 1);
      })()
    : '';

  const netBalance = parseFloat(snapshot.net_balance);
  const isPositive = netBalance >= 0;

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">Resumo do Snapshot</CardTitle>
          {isPositive ? (
            <TrendingUp className="h-5 w-5 text-success" />
          ) : (
            <TrendingDown className="h-5 w-5 text-destructive" />
          )}
        </div>
        <CardDescription>
          {refMonth}
          {snapshot.finalized_at && ` — Fechado em ${formatDate(snapshot.finalized_at)}`}
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-1">
        {/* Receitas */}
        <p className="text-xs font-semibold uppercase text-muted-foreground pt-1">Receitas</p>

        <SummaryRow
          label="Aluguéis"
          value={snapshot.total_rent_income}
          variant="income"
        />
        <SummaryRow
          label="Outros recebimentos"
          value={snapshot.total_extra_income}
          variant="income"
        />
        <SummaryRow
          label="Pagamentos de pessoas"
          value={snapshot.total_person_payments_received}
          variant="income"
        />

        <div className="flex items-center justify-between py-1 font-semibold">
          <div className="flex items-center gap-1 text-info">
            <ArrowUpRight className="h-4 w-4" />
            <span className="text-sm">Total Receitas</span>
          </div>
          <span className="text-sm text-info">{formatCurrency(snapshot.total_income)}</span>
        </div>

        <Separator className="my-2" />

        {/* Despesas */}
        <p className="text-xs font-semibold uppercase text-muted-foreground">Despesas</p>

        {parseFloat(snapshot.total_card_installments) > 0 && (
          <SummaryRow label="Parcelas de cartão" value={snapshot.total_card_installments} variant="expense" />
        )}
        {parseFloat(snapshot.total_loan_installments) > 0 && (
          <SummaryRow label="Parcelas de empréstimo" value={snapshot.total_loan_installments} variant="expense" />
        )}
        {parseFloat(snapshot.total_debt_installments) > 0 && (
          <SummaryRow label="Parcelas de dívida" value={snapshot.total_debt_installments} variant="expense" />
        )}
        {parseFloat(snapshot.total_utility_bills) > 0 && (
          <SummaryRow label="Contas de água/luz" value={snapshot.total_utility_bills} variant="expense" />
        )}
        {parseFloat(snapshot.total_property_tax) > 0 && (
          <SummaryRow label="IPTU" value={snapshot.total_property_tax} variant="expense" />
        )}
        {parseFloat(snapshot.total_employee_salary) > 0 && (
          <SummaryRow label="Salários" value={snapshot.total_employee_salary} variant="expense" />
        )}
        {parseFloat(snapshot.total_fixed_expenses) > 0 && (
          <SummaryRow label="Despesas fixas" value={snapshot.total_fixed_expenses} variant="expense" />
        )}
        {parseFloat(snapshot.total_one_time_expenses) > 0 && (
          <SummaryRow label="Despesas avulsas" value={snapshot.total_one_time_expenses} variant="expense" />
        )}
        {parseFloat(snapshot.total_owner_repayments) > 0 && (
          <SummaryRow label="Repasses a proprietários" value={snapshot.total_owner_repayments} variant="expense" />
        )}
        {parseFloat(snapshot.total_person_stipends) > 0 && (
          <SummaryRow label="Mesadas" value={snapshot.total_person_stipends} variant="expense" />
        )}

        <div className="flex items-center justify-between py-1 font-semibold">
          <div className="flex items-center gap-1 text-warning">
            <ArrowDownRight className="h-4 w-4" />
            <span className="text-sm">Total Despesas</span>
          </div>
          <span className="text-sm text-warning">{formatCurrency(snapshot.total_expenses)}</span>
        </div>

        <Separator className="my-2" />

        {/* Saldo */}
        <div className="flex items-center justify-between py-1">
          <div className="flex items-center gap-1">
            <Minus className="h-4 w-4 text-muted-foreground" />
            <span className="text-sm font-semibold">Saldo do Mês</span>
          </div>
          <span
            className={cn(
              'text-sm font-bold',
              isPositive ? 'text-success' : 'text-destructive',
            )}
          >
            {formatCurrency(snapshot.net_balance)}
          </span>
        </div>

        {parseFloat(snapshot.cumulative_ending_balance) !== 0 && (
          <div className="flex items-center justify-between py-1">
            <span className="text-xs text-muted-foreground">Saldo acumulado final</span>
            <span className="text-xs font-medium text-muted-foreground">
              {formatCurrency(snapshot.cumulative_ending_balance)}
            </span>
          </div>
        )}

        {snapshot.notes && (
          <p className="text-xs text-muted-foreground pt-2 border-t mt-2">
            Obs.: {snapshot.notes}
          </p>
        )}
      </CardContent>
    </Card>
  );
}
