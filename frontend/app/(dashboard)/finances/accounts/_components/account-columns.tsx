'use client';

import Link from 'next/link';
import { MoreHorizontal, Pencil, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { type Column } from '@/components/tables/data-table';
import { formatCurrency } from '@/lib/utils/formatters';
import { ROUTES } from '@/lib/utils/constants';
import {
  ACCOUNT_TYPE_LABELS,
  type BillingAccount,
} from '@/lib/schemas/finances/billing-account.schema';
import type { BillingAccountState } from '@/lib/schemas/finances/category.schema';

/** PT labels for BillingAccountState (active/suspended/deferred/ended) — single source (DRY),
 * reused by account-form-modal's select. */
export const ACCOUNT_STATE_LABELS: Record<BillingAccountState, string> = {
  active: 'Ativa',
  suspended: 'Suspensa',
  deferred: 'Adiada',
  ended: 'Encerrada',
};

interface BuildAccountColumnsOptions {
  isAdmin: boolean;
  onEdit: (account: BillingAccount) => void;
  onDelete: (account: BillingAccount) => void;
}

export function buildAccountColumns({
  isAdmin,
  onEdit,
  onDelete,
}: BuildAccountColumnsOptions): Column<BillingAccount>[] {
  const columns: Column<BillingAccount>[] = [
    {
      title: 'Nome',
      dataIndex: 'name',
      key: 'name',
      primary: true,
      sorter: (a, b) => a.name.localeCompare(b.name),
      render: (_, record) =>
        record.id === undefined ? (
          record.name
        ) : (
          <Link
            href={`${ROUTES.FINANCES_ACCOUNTS}/${String(record.id)}`}
            className="text-primary underline-offset-4 hover:underline"
          >
            {record.name}
          </Link>
        ),
    },
    {
      title: 'Prédio',
      key: 'building',
      render: (_, record) => (record.building ? record.building.name : 'Condomínio'),
    },
    {
      title: 'Tipo',
      key: 'account_type',
      render: (_, record) => ACCOUNT_TYPE_LABELS[record.account_type],
    },
    {
      title: 'Inscrição/UC',
      key: 'external_identifier',
      render: (_, record) => record.external_identifier || '—',
    },
    {
      title: 'Relógio/Imóvel',
      key: 'secondary_identifier',
      render: (_, record) => record.secondary_identifier || '—',
    },
    {
      title: 'Dia venc.',
      key: 'default_due_day',
      render: (_, record) => record.default_due_day,
    },
    {
      title: 'Valor esperado',
      key: 'expected_amount',
      render: (_, record) => formatCurrency(record.expected_amount),
    },
    {
      title: 'Estado',
      key: 'lifecycle_state',
      render: (_, record) => (
        <Badge variant={record.lifecycle_state === 'active' ? 'secondary' : 'outline'}>
          {ACCOUNT_STATE_LABELS[record.lifecycle_state]}
        </Badge>
      ),
    },
    {
      title: 'Fornecimento',
      key: 'supply_status',
      render: (_, record) =>
        record.supply_status === 'cut' ? <Badge variant="destructive">Cortada</Badge> : '—',
    },
    {
      title: 'Saldo devedor',
      key: 'open_balance',
      render: (_, record) =>
        record.open_balance === undefined ? (
          '—'
        ) : (
          <span className={record.open_balance > 0 ? 'text-destructive font-medium' : undefined}>
            {formatCurrency(record.open_balance)}
          </span>
        ),
    },
  ];

  if (isAdmin) {
    columns.push({
      title: 'Ações',
      key: 'actions',
      isActions: true,
      width: 80,
      render: (_, record) => (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="sm" aria-label="Ações da conta cadastrada">
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={() => onEdit(record)}>
              <Pencil className="mr-2 h-4 w-4" />
              Editar
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => onDelete(record)} className="text-destructive">
              <Trash2 className="mr-2 h-4 w-4" />
              Excluir
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      ),
    });
  }

  return columns;
}
