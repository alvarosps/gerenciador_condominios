'use client';

import { CalendarClock, ListOrdered, MoreHorizontal, Pencil, Trash2 } from 'lucide-react';
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
import type { InstallmentPlan } from '@/lib/schemas/finances/installment-plan.schema';
import { InstallmentPlanStatusChip } from './installment-plan-status-chip';

interface BuildInstallmentPlanColumnsOptions {
  isAdmin: boolean;
  onViewSchedule: (plan: InstallmentPlan) => void;
  onEdit: (plan: InstallmentPlan) => void;
  onConvert: (plan: InstallmentPlan) => void;
  onDelete: (plan: InstallmentPlan) => void;
}

export function buildInstallmentPlanColumns({
  isAdmin,
  onViewSchedule,
  onEdit,
  onConvert,
  onDelete,
}: BuildInstallmentPlanColumnsOptions): Column<InstallmentPlan>[] {
  const columns: Column<InstallmentPlan>[] = [
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
      title: 'Categoria',
      key: 'category',
      render: (_, record) => record.category?.name ?? '—',
    },
    {
      title: 'Total',
      key: 'total_amount',
      render: (_, record) => formatCurrency(record.total_amount),
    },
    {
      title: 'Parcelas',
      key: 'installment_count',
      render: (_, record) => `${String(record.installment_count)}x`,
    },
    {
      title: 'Embutido',
      key: 'embedded',
      render: (_, record) => (
        <Badge variant={record.embedded ? 'default' : 'secondary'}>
          {record.embedded ? 'Sim' : 'Não'}
        </Badge>
      ),
    },
    {
      title: 'Estado',
      key: 'lifecycle_state',
      render: (_, record) => <InstallmentPlanStatusChip state={record.lifecycle_state} />,
    },
  ];

  columns.push({
    title: 'Ações',
    key: 'actions',
    isActions: true,
    width: 80,
    fixed: 'right',
    render: (_, record) => (
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" size="sm" aria-label="Ações do plano">
            <MoreHorizontal className="h-4 w-4" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuItem onClick={() => onViewSchedule(record)}>
            <ListOrdered className="mr-2 h-4 w-4" />
            Cronograma
          </DropdownMenuItem>
          {isAdmin && (
            <>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={() => onEdit(record)}>
                <Pencil className="mr-2 h-4 w-4" />
                Editar
              </DropdownMenuItem>
              {record.lifecycle_state === 'deferred' && (
                <DropdownMenuItem onClick={() => onConvert(record)}>
                  <CalendarClock className="mr-2 h-4 w-4" />
                  Converter adiado
                </DropdownMenuItem>
              )}
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={() => onDelete(record)} className="text-destructive">
                <Trash2 className="mr-2 h-4 w-4" />
                Excluir
              </DropdownMenuItem>
            </>
          )}
        </DropdownMenuContent>
      </DropdownMenu>
    ),
  });

  return columns;
}
