'use client';

import { FileUp, MoreHorizontal, Pencil, Trash2, User, Wallet } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { type Column } from '@/components/tables/data-table';
import { formatCurrency, competenceMonthLabel, dueDateLabel } from '@/lib/utils/formatters';
import type { Bill } from '@/lib/schemas/finances/bill.schema';
import { ACCOUNT_TYPE_LABELS } from '@/lib/schemas/finances/billing-account.schema';
import { BillStatusChip } from '../../../_components/finance-calendar/bill-status-chip';
import { AmountPopover, DueDatePopover, canEditAmountInline } from './bill-inline-edit';
import { BillPayPopover } from './bill-pay-popover';
import { BillStatusActions } from './bill-status-actions';

/** Water/electricity account types eligible for "Importar fatura" on the row (S75). */
const INVOICE_IMPORT_ACCOUNT_TYPES: ReadonlySet<string> = new Set(['water', 'electricity']);

/** Whether the row offers "Importar fatura" in the actions dropdown (S75 contract). */
export function canImportInvoice(bill: Bill): boolean {
  const accountType = bill.account_type;
  return (
    accountType !== undefined &&
    INVOICE_IMPORT_ACCOUNT_TYPES.has(accountType) &&
    bill.amount_is_estimated &&
    bill.payment_status === 'open'
  );
}

/** Whether the row offers the "Pagar" popover (S75 contract). */
export function canPay(bill: Bill): boolean {
  return bill.lifecycle_state === 'active' && bill.payment_status !== 'paid';
}

interface BuildBillColumnsOptions {
  isAdmin: boolean;
  onEdit: (bill: Bill) => void;
  onPay: (bill: Bill) => void;
  onDelete: (bill: Bill) => void;
  onImportInvoice: (bill: Bill) => void;
}

export function buildBillColumns({
  isAdmin,
  onEdit,
  onPay,
  onDelete,
  onImportInvoice,
}: BuildBillColumnsOptions): Column<Bill>[] {
  const columns: Column<Bill>[] = [
    {
      title: 'Descrição',
      dataIndex: 'description',
      key: 'description',
      primary: true,
      sorter: (a, b) => a.description.localeCompare(b.description),
      render: (_, record) => (
        <div className="flex flex-wrap items-center gap-2">
          <span>{record.description}</span>
          {record.paid_by_person && (
            <Badge variant="secondary">
              <User className="mr-1 h-3 w-3" />
              {record.paid_by_person.name}
            </Badge>
          )}
          {record.amount_is_estimated && (record.amount_total ?? 0) > 0 && (
            <Badge variant="outline">valor estimado</Badge>
          )}
          {record.amount_is_estimated && (record.amount_total ?? 0) === 0 && (
            <Badge variant="outline">aguardando fatura</Badge>
          )}
        </div>
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
      render: (_, record) => ACCOUNT_TYPE_LABELS[record.account_type ?? 'generic'],
    },
    {
      title: 'Competência',
      key: 'competence_month',
      render: (_, record) => competenceMonthLabel(record.competence_month),
    },
    {
      title: 'Vencimento',
      key: 'due_date',
      render: (_, record) =>
        isAdmin ? <DueDatePopover bill={record} /> : dueDateLabel(record.due_date),
    },
    {
      title: 'Total',
      key: 'amount_total',
      render: (_, record) =>
        isAdmin && canEditAmountInline(record) ? (
          <AmountPopover bill={record} />
        ) : (
          formatCurrency(record.amount_total ?? 0)
        ),
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
      width: 160,
      render: (_, record) => (
        <div className="flex items-center justify-end gap-1">
          {canPay(record) && <BillPayPopover bill={record} />}
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
                Pagar (detalhado)
              </DropdownMenuItem>
              {canImportInvoice(record) && (
                <DropdownMenuItem onClick={() => onImportInvoice(record)}>
                  <FileUp className="mr-2 h-4 w-4" />
                  Importar fatura
                </DropdownMenuItem>
              )}
              <DropdownMenuSeparator />
              <BillStatusActions bill={record} />
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={() => onDelete(record)} className="text-destructive">
                <Trash2 className="mr-2 h-4 w-4" />
                Excluir
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      ),
    });
  }

  return columns;
}
