import { Badge } from '@/components/ui/badge';
import { type Column } from '@/components/tables/data-table';
import {
  formatCurrency,
  formatDate,
  competenceMonthLabel,
  dueDateLabel,
} from '@/lib/utils/formatters';
import type { StatementMonthRow } from '@/lib/schemas/finances/account-statement.schema';
import type { PaymentStatus, BillLifecycleState } from '@/lib/schemas/finances/category.schema';

/**
 * Single source of PT labels for the statement's own `payment_status`/`lifecycle_state` badges.
 * Deliberately distinct from `BillStatusChip` (bills page), which requires `is_overdue` — a field
 * the statement payload does not carry (S67 contract).
 */
export const STATEMENT_PAYMENT_STATUS_LABELS: Record<PaymentStatus, string> = {
  open: 'Em aberto',
  partial: 'Parcial',
  paid: 'Paga',
};

export const STATEMENT_LIFECYCLE_STATE_LABELS: Record<BillLifecycleState, string> = {
  active: 'Ativa',
  suspended: 'Suspensa',
  deferred: 'Adiada',
  canceled: 'Cancelada',
};

export function buildStatementMonthColumns(): Column<StatementMonthRow>[] {
  return [
    {
      title: 'Competência',
      key: 'competence_month',
      primary: true,
      render: (_, record) => competenceMonthLabel(record.competence_month),
    },
    {
      title: 'Vencimento',
      key: 'due_date',
      render: (_, record) => dueDateLabel(record.due_date),
    },
    {
      title: 'Descrição',
      dataIndex: 'description',
      key: 'description',
      render: (_, record) => (
        <div className="flex items-center gap-2">
          <span>{record.description}</span>
          {record.amount_is_estimated && <Badge variant="outline">valor estimado</Badge>}
        </div>
      ),
    },
    {
      title: 'Total',
      key: 'amount_total',
      render: (_, record) => formatCurrency(record.amount_total),
    },
    {
      title: 'Pago',
      key: 'amount_paid',
      render: (_, record) => formatCurrency(record.amount_paid),
    },
    {
      title: 'Resto',
      key: 'amount_remaining',
      render: (_, record) => formatCurrency(record.amount_remaining),
    },
    {
      title: 'Status',
      key: 'payment_status',
      render: (_, record) => (
        <Badge variant={record.payment_status === 'paid' ? 'default' : 'secondary'}>
          {STATEMENT_PAYMENT_STATUS_LABELS[record.payment_status as PaymentStatus]}
        </Badge>
      ),
    },
    {
      title: 'Estado',
      key: 'lifecycle_state',
      render: (_, record) =>
        record.lifecycle_state === 'active' ? (
          <span className="text-muted-foreground">—</span>
        ) : (
          <Badge variant="outline">
            {STATEMENT_LIFECYCLE_STATE_LABELS[record.lifecycle_state as BillLifecycleState]}
          </Badge>
        ),
    },
    {
      title: 'Data pgto.',
      key: 'paid_date',
      render: (_, record) => (record.paid_date ? formatDate(record.paid_date) : '—'),
    },
  ];
}
