'use client';

import { CheckCircle2, MoreHorizontal, Pencil, Trash2, XCircle } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { type Column } from '@/components/tables/data-table';
import { formatCurrency } from '@/lib/utils/formatters';
import type { Employee } from '@/lib/schemas/finances/employee.schema';
import { PAYMENT_TYPE_LABELS } from './employee-labels';

function linkLabel(employee: Employee): string {
  if (employee.person?.name) return employee.person.name;
  if (employee.lease?.id !== undefined) return `Locação #${String(employee.lease.id)}`;
  return '—';
}

interface BuildEmployeeColumnsOptions {
  isAdmin: boolean;
  onEdit: (employee: Employee) => void;
  onDelete: (employee: Employee) => void;
}

export function buildEmployeeColumns({
  isAdmin,
  onEdit,
  onDelete,
}: BuildEmployeeColumnsOptions): Column<Employee>[] {
  const columns: Column<Employee>[] = [
    {
      title: 'Nome',
      dataIndex: 'name',
      key: 'name',
      primary: true,
      sorter: (a, b) => a.name.localeCompare(b.name),
    },
    {
      title: 'Cargo',
      key: 'role',
      render: (_, record) => (record.role ? record.role : '—'),
    },
    {
      title: 'Tipo',
      key: 'payment_type',
      render: (_, record) => PAYMENT_TYPE_LABELS[record.payment_type],
    },
    {
      title: 'Salário base',
      key: 'base_salary',
      render: (_, record) =>
        record.base_salary === null || record.base_salary === undefined
          ? '—'
          : formatCurrency(record.base_salary),
    },
    {
      title: 'Vínculo',
      key: 'link',
      render: (_, record) => linkLabel(record),
    },
    {
      title: 'Ativo',
      key: 'is_active',
      render: (_, record) => (
        <Badge variant={record.is_active ? 'default' : 'secondary'} className="gap-1">
          {record.is_active ? (
            <CheckCircle2 className="h-3 w-3" />
          ) : (
            <XCircle className="h-3 w-3" />
          )}
          {record.is_active ? 'Ativo' : 'Inativo'}
        </Badge>
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
            <Button variant="ghost" size="sm" aria-label="Ações do funcionário">
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={() => onEdit(record)}>
              <Pencil className="mr-2 h-4 w-4" />
              Editar
            </DropdownMenuItem>
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
