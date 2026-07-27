'use client';

import { useCallback, useMemo, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { Plus } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { DataTable } from '@/components/tables/data-table';
import { PageHeader } from '@/components/layouts/page-header';
import { StatCard } from '@/components/ui/stat-card';
import { useThirdPartyStatement } from '@/lib/api/hooks/use-third-party';
import { useAuthStore } from '@/store/auth-store';
import { ROUTES } from '@/lib/utils/constants';
import { formatCurrency } from '@/lib/utils/formatters';
import type { ThirdPartyStatementMonth } from '@/lib/schemas/finances/third-party.schema';
import { SettlementFormModal } from '../_components/settlement-form-modal';
import { buildThirdPartyStatementColumns } from './_components/third-party-statement-columns';

function NotFoundState() {
  return (
    <div className="rounded-md border-2 border-dashed py-12 text-center">
      <p className="text-sm text-muted-foreground">Pessoa não encontrada</p>
      <Link
        href={ROUTES.FINANCES_THIRD_PARTY}
        className="mt-2 inline-block text-sm text-primary underline"
      >
        Voltar para Terceiros
      </Link>
    </div>
  );
}

export default function ThirdPartyStatementPage() {
  const params = useParams<{ id: string }>();
  const personId = Number(params.id);
  const isValidId = Number.isInteger(personId) && personId > 0;

  const { user } = useAuthStore();
  const isAdmin = user?.is_staff ?? false;

  const [settlementOpen, setSettlementOpen] = useState(false);
  const [expandedMonths, setExpandedMonths] = useState<ReadonlySet<string>>(new Set());

  const { data: statement, isLoading, error } = useThirdPartyStatement(isValidId ? personId : null);

  const toggleMonth = useCallback((month: string) => {
    setExpandedMonths((previous) => {
      const next = new Set(previous);
      if (next.has(month)) next.delete(month);
      else next.add(month);
      return next;
    });
  }, []);

  const columns = useMemo(
    () => buildThirdPartyStatementColumns({ expandedMonths, onToggleMonth: toggleMonth }),
    [expandedMonths, toggleMonth]
  );

  if (!isValidId || error) {
    return <NotFoundState />;
  }

  if (isLoading || !statement) {
    return (
      <div>
        <div className="mb-4 grid grid-cols-1 gap-4 sm:grid-cols-3">
          <StatCard label="Em aberto" value="" loading />
          <StatCard label="Atrasado" value="" loading />
          <StatCard label="Crédito" value="" loading />
        </div>
        <DataTable<ThirdPartyStatementMonth> columns={columns} rowKey="month" loading />
      </div>
    );
  }

  // Read straight from the payload — the FIFO allocation is the backend's, never recomputed here.
  const { totals } = statement;

  return (
    <div>
      <PageHeader
        title={statement.person_name}
        description="Extrato de terceiro — o que os donos devem a esta pessoa, mês a mês"
        actions={
          isAdmin && (
            <Button onClick={() => setSettlementOpen(true)}>
              <Plus className="mr-2 h-4 w-4" />
              Registrar acerto
            </Button>
          )
        }
      />

      <div className="mb-4 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <StatCard
          label="Em aberto"
          value={formatCurrency(totals.total_em_aberto)}
          tone={totals.total_em_aberto > 0 ? 'destructive' : 'success'}
        />
        <StatCard
          label="Atrasado"
          value={formatCurrency(totals.total_atrasado)}
          tone={totals.total_atrasado > 0 ? 'destructive' : 'muted'}
        />
        <StatCard
          label="Crédito"
          value={formatCurrency(totals.saldo_credor)}
          tone={totals.saldo_credor > 0 ? 'info' : 'muted'}
          subLabel="acertos ainda não consumidos"
        />
      </div>

      {statement.months.length === 0 ? (
        <p className="rounded-md border-2 border-dashed py-12 text-center text-sm text-muted-foreground">
          Nenhum movimento no período
        </p>
      ) : (
        <DataTable<ThirdPartyStatementMonth>
          columns={columns}
          dataSource={statement.months}
          rowKey="month"
        />
      )}

      <SettlementFormModal
        open={settlementOpen}
        onClose={() => setSettlementOpen(false)}
        defaultPersonId={personId}
      />
    </div>
  );
}
