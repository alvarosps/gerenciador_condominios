'use client';

import { useState, useEffect } from 'react';
import { ArrowDownCircle, ArrowUpCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import { DataTable, type Column } from '@/components/tables/data-table';
import { StatCard } from '@/components/ui/stat-card';
import { AmountDisplay } from '@/components/ui/amount-display';
import { useReserves } from '@/lib/api/hooks/use-reserves';
import { useReserveMovements } from '@/lib/api/hooks/use-reserve-movements';
import { useAuthStore } from '@/store/auth-store';
import { formatDate, formatCurrency } from '@/lib/utils/formatters';
import type { Reserve } from '@/lib/schemas/finances/reserve.schema';
import type { ReserveMovement } from '@/lib/schemas/finances/reserve-movement.schema';
import { DepositDialog } from './_components/deposit-dialog';
import { WithdrawDialog } from './_components/withdraw-dialog';

const kindLabel: Record<ReserveMovement['kind'], string> = {
  deposit: 'Depósito',
  withdrawal: 'Saque',
};

function movementColumns(): Column<ReserveMovement>[] {
  return [
    {
      title: 'Data',
      key: 'movement_date',
      dataIndex: 'movement_date',
      width: 110,
      render: (val) => formatDate(val as string),
      sorter: (a, b) => a.movement_date.localeCompare(b.movement_date),
    },
    {
      title: 'Reserva',
      key: 'reserve',
      render: (_, rec) => rec.reserve?.name ?? '-',
    },
    {
      title: 'Tipo',
      key: 'kind',
      width: 110,
      render: (_, rec) => (
        <Badge className={rec.kind === 'deposit' ? 'bg-success/10 text-success' : 'bg-destructive/10 text-destructive'}>
          {kindLabel[rec.kind]}
        </Badge>
      ),
    },
    {
      title: 'Valor',
      key: 'amount',
      dataIndex: 'amount',
      width: 130,
      render: (_, rec) => (
        <AmountDisplay
          amount={rec.amount}
          tone={rec.kind === 'deposit' ? 'success' : 'destructive'}
        />
      ),
    },
    {
      title: 'Vínculo',
      key: 'bill',
      render: (_, rec) =>
        rec.bill !== null ? `Pagamento de conta #${rec.bill}` : 'Transferência (caixa)',
    },
    {
      title: 'Referência',
      key: 'reference',
      render: (_, rec) => rec.reference ?? '-',
    },
    {
      title: 'Obs.',
      key: 'notes',
      render: (_, rec) => rec.notes ?? '-',
    },
  ];
}

export default function ReservePage() {
  const { user } = useAuthStore();
  const isStaff = user?.is_staff ?? false;

  const { data: reserves, isLoading: reservesLoading, error: reservesError } = useReserves();
  const { data: movements, isLoading: movementsLoading } = useReserveMovements();

  const [depositTarget, setDepositTarget] = useState<Reserve | null>(null);
  const [withdrawTarget, setWithdrawTarget] = useState<Reserve | null>(null);

  useEffect(() => {
    if (reservesError) {
      toast.error('Erro ao carregar reservas');
    }
  }, [reservesError]);

  const totalBalance = reserves?.reduce((sum, r) => sum + r.balance, 0) ?? 0;

  return (
    <div>
      <div className="mb-4 flex justify-between items-center flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold">Reservas do Condomínio</h1>
          <p className="text-muted-foreground mt-1">Gerencie os fundos de reserva</p>
        </div>
      </div>

      {/* Reserve balance cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 mb-6">
        <StatCard
          label="Saldo Total das Reservas"
          value={<AmountDisplay amount={totalBalance} tone="info" size="lg" />}
          tone="info"
        />
        {reserves?.map((reserve) => (
          <Card key={reserve.id} className="transition-shadow hover:shadow-md">
            <CardContent className="pt-6">
              <div className="flex items-start justify-between mb-2">
                <div>
                  <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                    {reserve.name}
                  </p>
                  <p className="text-2xl font-bold tabular-nums text-info mt-1">
                    {formatCurrency(reserve.balance)}
                  </p>
                </div>
              </div>
              {reserve.notes && (
                <p className="text-xs text-muted-foreground mb-3">{reserve.notes}</p>
              )}
              {isStaff && (
                <div className="flex gap-2 mt-3">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => setDepositTarget(reserve)}
                  >
                    <ArrowDownCircle className="h-3 w-3 mr-1" />
                    Depositar
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => setWithdrawTarget(reserve)}
                  >
                    <ArrowUpCircle className="h-3 w-3 mr-1" />
                    Sacar
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Movements ledger */}
      <h2 className="text-lg font-semibold mb-3">Movimentações</h2>
      <DataTable<ReserveMovement>
        columns={movementColumns()}
        dataSource={movements}
        loading={reservesLoading || movementsLoading}
        rowKey="id"
      />

      {isStaff && (
        <>
          <DepositDialog
            open={depositTarget !== null}
            reserve={depositTarget}
            onClose={() => setDepositTarget(null)}
          />
          <WithdrawDialog
            open={withdrawTarget !== null}
            reserve={withdrawTarget}
            onClose={() => setWithdrawTarget(null)}
          />
        </>
      )}
    </div>
  );
}
