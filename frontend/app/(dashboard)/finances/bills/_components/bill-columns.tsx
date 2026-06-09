'use client';

import { MoreHorizontal, Pencil, Trash2, Wallet } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { type Column } from '@/components/tables/data-table';
import { formatCurrency, formatMonthYear } from '@/lib/utils/formatters';
import type { Bill } from '@/lib/schemas/finances/bill.schema';
import { ACCOUNT_TYPE_LABELS } from '@/lib/schemas/finances/billing-account.schema';
import { BillStatusChip } from '../../../_components/finance-calendar/bill-status-chip';
import { BillStatusActions } from './bill-status-actions';

/** Format a YYYY-MM-01 competence month as "Junho de 2026" using split (never new Date(iso)). */
function competenceLabel(competenceMonth: string): string {
  const [year, month] = competenceMonth.split('-');
  if (!year || !month) return competenceMonth;
  return formatMonthYear(Number(year), Number(month));
}

/** Format a YYYY-MM-DD date as DD/MM/YYYY using split (never new Date(iso)). */
function dueDateLabel(dueDate: string): string {
  const [year, month, day] = dueDate.split('-');
  if (!year || !month || !day) return dueDate;
  return `${day}/${month}/${year}`;
}

interface BuildBillColumnsOptions {
  isAdmin: boolean;
  onEdit: (bill: Bill) => void;
  onPay: (bill: Bill) => void;
  onDelete: (bill: Bill) => void;
}

export function buildBillColumns({
  isAdmin,
  onEdit,
  onPay,
  onDelete,
}: BuildBillColumnsOptions): Column<Bill>[] {
  const columns: Column<Bill>[] = [
    {
      title: 'Descrição',
      dataIndex: 'description',
      key: 'description',
      primary: true,
      sorter: (a, b) => a.description.localeCompare(b.description),
    },
    {
      title: 'Prédio',
      key: 'building',
      render: (_, record) => (record.building ? record.building.name : 'Condomínio'),
    },
    {
      title: 'Tipo',
      key: 'account_type',
      render: (_, record) => ACCOUNT_TYPE_LABELS[record.account_type ?? 'generic'],
    },
    {
      title: 'Competência',
      key: 'competence_month',
      render: (_, record) => competenceLabel(record.competence_month),
    },
    {
      title: 'Vencimento',
      key: 'due_date',
      render: (_, record) => dueDateLabel(record.due_date),
    },
    {
      title: 'Total',
      key: 'amount_total',
      render: (_, record) => formatCurrency(record.amount_total ?? 0),
    },
    {
      title: 'Resta',
      key: 'amount_remaining',
      render: (_, record) => formatCurrency(record.amount_remaining ?? 0),
    },
    {
      title: 'Status',
      key: 'status',
      render: (_, record) => (
        <BillStatusChip
          paymentStatus={record.payment_status ?? 'open'}
          isOverdue={record.is_overdue ?? false}
          lifecycleState={record.lifecycle_state}
        />
      ),
    },
  ];

  if (isAdmin) {
    columns.push({
      title: 'Ações',
      key: 'actions',
      isActions: true,
      width: 80,
      fixed: 'right',
      render: (_, record) => (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="sm" aria-label="Ações da conta">
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={() => onEdit(record)}>
              <Pencil className="mr-2 h-4 w-4" />
              Editar
            </DropdownMenuItem>
            <DropdownMenuItem
              onClick={() => onPay(record)}
              disabled={record.lifecycle_state !== 'active' || record.payment_status === 'paid'}
            >
              <Wallet className="mr-2 h-4 w-4" />
              Pagar
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <BillStatusActions bill={record} />
            <DropdownMenuSeparator />
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
