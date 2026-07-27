'use client';

import { useMemo, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { Plus } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { DataTable } from '@/components/tables/data-table';
import { PageHeader } from '@/components/layouts/page-header';
import { StatCard } from '@/components/ui/stat-card';
import { useAccountStatement } from '@/lib/api/hooks/use-account-statement';
import { useAuthStore } from '@/store/auth-store';
import { ROUTES } from '@/lib/utils/constants';
import { formatCurrency } from '@/lib/utils/formatters';
import { ACCOUNT_TYPE_LABELS } from '@/lib/schemas/finances/billing-account.schema';
import type {
  StatementMonthRow,
  StatementPlanRow,
} from '@/lib/schemas/finances/account-statement.schema';
import { buildStatementMonthColumns } from './_components/account-statement-columns';
import {
  ConsolidateDebtDialog,
  type ConsolidableBill,
} from './_components/consolidate-debt-dialog';

/** Bills eligible for consolidation: open balance and not canceled (S73 contract, mirrors S70). */
function consolidableBills(months: StatementMonthRow[]): ConsolidableBill[] {
  return months
    .filter((month) => month.amount_remaining > 0 && month.lifecycle_state !== 'canceled')
    .map((month) => ({
      bill_id: month.bill_id,
      description: month.description,
      competence_month: month.competence_month,
      due_date: month.due_date,
      amount_remaining: month.amount_remaining,
    }));
}

/** Progress percentage for a plan (guards against division by zero). */
function planProgress(plan: StatementPlanRow): number {
  if (plan.installment_count <= 0) return 0;
  return (plan.materialized_count / plan.installment_count) * 100;
}

function NotFoundState() {
  return (
    <div className="rounded-md border-2 border-dashed py-12 text-center">
      <p className="text-sm text-muted-foreground">Conta não encontrada</p>
      <Link
        href={ROUTES.FINANCES_ACCOUNTS}
        className="mt-2 inline-block text-sm text-primary underline"
      >
        Voltar para Contas cadastradas
      </Link>
    </div>
  );
}

export default function AccountDetailPage() {
  const params = useParams<{ id: string }>();
  const accountId = Number(params.id);
  const isValidId = Number.isInteger(accountId) && accountId > 0;

  const { user } = useAuthStore();
  const isAdmin = user?.is_staff ?? false;

  const [consolidateOpen, setConsolidateOpen] = useState(false);

  const { data: statement, isLoading, error } = useAccountStatement(isValidId ? accountId : null);

  const columns = useMemo(() => buildStatementMonthColumns(), []);
  const bills = useMemo(() => consolidableBills(statement?.months ?? []), [statement]);

  if (!isValidId || error) {
    return <NotFoundState />;
  }

  if (isLoading || !statement) {
    return (
      <div>
        <div className="mb-4 grid grid-cols-1 gap-4 sm:grid-cols-3">
          <StatCard label="Saldo devedor" value="" loading />
          <StatCard label="Faturas em aberto" value="" loading />
          <StatCard label="Atraso médio" value="" loading />
        </div>
        <DataTable<StatementMonthRow> columns={columns} rowKey="bill_id" loading />
      </div>
    );
  }

  const openBalance = Number(statement.stats.open_balance);

  return (
    <div>
      <PageHeader
        title={statement.account.name}
        description="Extrato da conta — histórico mês a mês e saldo devedor"
        actions={
          isAdmin && (
            <Button onClick={() => setConsolidateOpen(true)} disabled={bills.length === 0}>
              <Plus className="mr-2 h-4 w-4" />
              Parcelar saldo devedor
            </Button>
          )
        }
      />

      <div className="mb-4 flex flex-wrap items-center gap-2">
        <Badge variant="outline">{ACCOUNT_TYPE_LABELS[statement.account.account_type]}</Badge>
        {statement.account.supply_status === 'cut' && <Badge variant="destructive">Cortada</Badge>}
        {statement.account.lifecycle_state === 'ended' && (
          <Badge variant="outline">Encerrada</Badge>
        )}
      </div>

      <div className="mb-4 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <StatCard
          label="Saldo devedor"
          value={formatCurrency(openBalance)}
          tone={openBalance > 0 ? 'destructive' : 'success'}
        />
        <StatCard label="Faturas em aberto" value={statement.stats.open_bills_count} />
        <StatCard
          label="Atraso médio"
          value={
            statement.stats.avg_delay_days === null
              ? '—'
              : `~${String(statement.stats.avg_delay_days)} dias`
          }
          subLabel="últimas 12 faturas quitadas"
        />
      </div>

      <DataTable<StatementMonthRow>
        columns={columns}
        dataSource={statement.months}
        rowKey="bill_id"
      />

      {statement.plans.length > 0 && (
        <div className="mt-6 space-y-3">
          <h2 className="text-lg font-semibold">Planos vinculados</h2>
          {statement.plans.map((plan) => (
            <Card key={plan.id}>
              <CardContent className="flex flex-col gap-2 pt-6">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="font-medium">{plan.description}</span>
                  <div className="flex items-center gap-2">
                    <Badge variant={plan.embedded ? 'default' : 'secondary'}>
                      {plan.embedded ? 'Embutido' : 'Avulso'}
                    </Badge>
                  </div>
                </div>
                <Progress value={planProgress(plan)} />
                <span className="text-sm text-muted-foreground">
                  Parcela {plan.materialized_count}/{plan.installment_count}
                </span>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <ConsolidateDebtDialog
        open={consolidateOpen}
        onClose={() => setConsolidateOpen(false)}
        accountId={accountId}
        accountType={statement.account.account_type}
        bills={bills}
      />
    </div>
  );
}
