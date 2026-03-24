'use client';

import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { Pencil, Trash2, List, CheckCircle } from 'lucide-react';
import { cn } from '@/lib/utils';
import { type Column } from '@/components/tables/data-table';
import { type Expense } from '@/lib/schemas/expense.schema';
import { formatCurrency, formatDate } from '@/lib/utils/formatters';

export interface ExpenseActionHandlers {
  onEdit: (expense: Expense) => void;
  onDelete: (expense: Expense) => void;
  onViewInstallments: (expense: Expense) => void;
  onMarkPaid: (expense: Expense) => void;
  isDeleting: boolean;
  isMarkingPaid: boolean;
  isAdmin: boolean;
}

const EXPENSE_TYPE_LABELS: Record<string, { label: string; color: string }> = {
  card_purchase: { label: 'Cartão', color: 'bg-primary/10 text-primary' },
  bank_loan: { label: 'Emp. Bancário', color: 'bg-destructive/10 text-destructive' },
  personal_loan: { label: 'Emp. Pessoal', color: 'bg-warning/10 text-warning' },
  water_bill: { label: 'Água', color: 'bg-info/10 text-info' },
  electricity_bill: { label: 'Luz', color: 'bg-warning/10 text-warning' },
  property_tax: { label: 'IPTU', color: 'bg-success/10 text-success' },
  fixed_expense: { label: 'Fixo', color: 'bg-muted text-muted-foreground' },
  one_time_expense: { label: 'Único', color: 'bg-info/10 text-info' },
  employee_salary: { label: 'Salário', color: 'bg-success/10 text-success' },
};

function getInstallmentLabel(expense: Expense): string | null {
  if (!expense.is_installment || !expense.total_installments) return null;
  const paid = (expense.installments ?? []).filter((i) => i.is_paid).length;
  return `${paid}/${expense.total_installments}`;
}

export function createExpenseColumns(handlers: ExpenseActionHandlers): Column<Expense>[] {
  return [
    {
      title: 'Descrição',
      dataIndex: 'description',
      key: 'description',
      sorter: (a, b) => a.description.localeCompare(b.description),
    },
    {
      title: 'Tipo',
      key: 'expense_type',
      width: 130,
      render: (_, record) => {
        const typeInfo = EXPENSE_TYPE_LABELS[record.expense_type];
        return (
          <Badge className={cn(typeInfo?.color ?? 'bg-muted text-muted-foreground')}>
            {typeInfo?.label ?? record.expense_type}
          </Badge>
        );
      },
    },
    {
      title: 'Valor',
      dataIndex: 'total_amount',
      key: 'total_amount',
      width: 130,
      render: (value) => formatCurrency(value as number),
      sorter: (a, b) => a.total_amount - b.total_amount,
    },
    {
      title: 'Pessoa',
      key: 'person',
      width: 140,
      render: (_, record) => record.person?.name ?? '-',
    },
    {
      title: 'Cartão',
      key: 'credit_card',
      width: 130,
      render: (_, record) => record.credit_card?.nickname ?? '-',
    },
    {
      title: 'Prédio',
      key: 'building',
      width: 130,
      render: (_, record) => record.building?.name ?? '-',
    },
    {
      title: 'Categoria',
      key: 'category',
      width: 130,
      render: (_, record) => {
        if (!record.category) return '-';
        return (
          <Badge
            style={{ backgroundColor: `${record.category.color}20`, color: record.category.color }}
          >
            {record.category.name}
          </Badge>
        );
      },
    },
    {
      title: 'Parcelas',
      key: 'installments',
      width: 90,
      align: 'center',
      render: (_, record) => getInstallmentLabel(record) ?? '-',
    },
    {
      title: 'Status',
      key: 'status',
      width: 100,
      align: 'center',
      render: (_, record) => (
        <Badge className={cn(record.is_paid ? 'bg-success/10 text-success' : 'bg-warning/10 text-warning')}>
          {record.is_paid ? 'Pago' : 'Pendente'}
        </Badge>
      ),
    },
    {
      title: 'Data',
      dataIndex: 'expense_date',
      key: 'expense_date',
      width: 110,
      render: (value) => formatDate(value as string),
      sorter: (a, b) => new Date(a.expense_date).getTime() - new Date(b.expense_date).getTime(),
    },
    {
      title: 'Ações',
      key: 'actions',
      width: 180,
      fixed: 'right',
      render: (_, record) => (
        <TooltipProvider>
          <div className="flex items-center gap-1">
            {handlers.isAdmin && (
              <>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button variant="ghost" size="icon" onClick={() => handlers.onEdit(record)}>
                      <Pencil className="h-4 w-4" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>Editar</TooltipContent>
                </Tooltip>

                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => handlers.onDelete(record)}
                      disabled={handlers.isDeleting}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>Excluir</TooltipContent>
                </Tooltip>
              </>
            )}

            {record.is_installment && (
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => handlers.onViewInstallments(record)}
                  >
                    <List className="h-4 w-4" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>Ver Parcelas</TooltipContent>
              </Tooltip>
            )}

            {handlers.isAdmin && !record.is_paid && !record.is_installment && (
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => handlers.onMarkPaid(record)}
                    disabled={handlers.isMarkingPaid}
                  >
                    <CheckCircle className="h-4 w-4" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>Marcar como Pago</TooltipContent>
              </Tooltip>
            )}
          </div>
        </TooltipProvider>
      ),
    },
  ];
}
