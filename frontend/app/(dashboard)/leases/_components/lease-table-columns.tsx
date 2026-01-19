'use client';

import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import {
  Pencil,
  Trash2,
  Calculator,
  Calendar,
  FilePlus,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Column } from '@/components/tables/data-table';
import { Lease } from '@/lib/schemas/lease.schema';
import { formatCurrency } from '@/lib/utils/formatters';
import { format, isPast, isFuture, differenceInDays, differenceInMonths, parseISO } from 'date-fns';

export interface LeaseActionHandlers {
  onEdit: (lease: Lease) => void;
  onDelete: (lease: Lease) => void;
  onGenerateContract: (lease: Lease) => void;
  onCalculateLateFee: (lease: Lease) => void;
  onChangeDueDate: (lease: Lease) => void;
  isDeleting: boolean;
}

export function getLeaseStatus(lease: Lease) {
  const startDate = parseISO(lease.start_date);
  const finalDate = lease.final_date ? parseISO(lease.final_date) : null;
  const today = new Date();

  if (isFuture(startDate)) {
    return { status: 'Futuro', color: 'blue' };
  }

  if (finalDate && isPast(finalDate)) {
    return { status: 'Expirado', color: 'red' };
  }

  if (finalDate) {
    const daysToExpire = differenceInDays(finalDate, today);
    if (daysToExpire <= 30) {
      return { status: `Expira em ${daysToExpire} dias`, color: 'orange' };
    }
  }

  return { status: 'Ativo', color: 'green' };
}

export function getMinimumPeriodStatus(lease: Lease) {
  const startDate = parseISO(lease.start_date);
  const today = new Date();
  const minimumMonths = lease.validity_months;

  // If the lease hasn't started yet
  if (isFuture(startDate)) {
    return {
      completed: false,
      monthsElapsed: 0,
      monthsRemaining: minimumMonths,
      label: `Faltam ${minimumMonths} meses`,
      color: 'yellow',
    };
  }

  const monthsElapsed = differenceInMonths(today, startDate);
  const monthsRemaining = minimumMonths - monthsElapsed;

  if (monthsElapsed >= minimumMonths) {
    return {
      completed: true,
      monthsElapsed,
      monthsRemaining: 0,
      label: 'Período completo',
      color: 'green',
    };
  }

  return {
    completed: false,
    monthsElapsed,
    monthsRemaining,
    label: `Faltam ${monthsRemaining} ${monthsRemaining === 1 ? 'mês' : 'meses'}`,
    color: 'yellow',
  };
}

export function createLeaseColumns(handlers: LeaseActionHandlers): Column<Lease>[] {
  const badgeVariants: Record<string, string> = {
    blue: 'bg-blue-100 text-blue-800 hover:bg-blue-200',
    red: 'bg-red-100 text-red-800 hover:bg-red-200',
    orange: 'bg-orange-100 text-orange-800 hover:bg-orange-200',
    green: 'bg-green-100 text-green-800 hover:bg-green-200',
    yellow: 'bg-yellow-100 text-yellow-800 hover:bg-yellow-200',
  };

  return [
    {
      title: 'Prédio / Apto',
      key: 'apartment',
      width: 180,
      render: (_, record: Lease) => (
        <div>
          <div className="font-medium">{record.apartment?.building?.name}</div>
          <div className="text-xs text-gray-500">
            Apto {record.apartment?.number}
          </div>
        </div>
      ),
    },
    {
      title: 'Inquilino Responsável',
      key: 'tenant',
      width: 200,
      render: (_, record: Lease) => (
        <div>
          <div className="font-medium">{record.responsible_tenant?.name}</div>
          {record.tenants && record.tenants.length > 1 && (
            <div className="text-xs text-gray-500">
              +{record.tenants.length - 1} inquilino(s)
            </div>
          )}
        </div>
      ),
    },
    {
      title: 'Período',
      key: 'period',
      width: 200,
      render: (_, record: Lease) => (
        <div className="text-sm">
          <div>{format(parseISO(record.start_date), 'dd/MM/yyyy')}</div>
          <div className="text-gray-500">
            até {record.final_date ? format(parseISO(record.final_date), 'dd/MM/yyyy') : 'N/A'}
          </div>
          <div className="text-xs text-gray-400">
            {record.validity_months} meses
          </div>
        </div>
      ),
      sorter: (a: Lease, b: Lease) => new Date(a.start_date).getTime() - new Date(b.start_date).getTime(),
    },
    {
      title: 'Status',
      key: 'status',
      width: 140,
      render: (_, record: Lease) => {
        const { status, color } = getLeaseStatus(record);
        return (
          <Badge className={cn(badgeVariants[color] || 'bg-gray-100 text-gray-800')}>
            {status}
          </Badge>
        );
      },
    },
    {
      title: 'Período Mínimo',
      key: 'minimum_period',
      width: 150,
      render: (_, record: Lease) => {
        const { label, color, monthsElapsed } = getMinimumPeriodStatus(record);
        return (
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Badge className={cn(badgeVariants[color] || 'bg-gray-100 text-gray-800', 'cursor-help')}>
                  {label}
                </Badge>
              </TooltipTrigger>
              <TooltipContent>
                <div className="text-sm">
                  <div>Mínimo: {record.validity_months} meses</div>
                  <div>Decorridos: {monthsElapsed} meses</div>
                </div>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        );
      },
    },
    {
      title: 'Valor',
      dataIndex: 'rental_value',
      key: 'rental_value',
      width: 120,
      render: (value) => formatCurrency(value as number),
      sorter: (a: Lease, b: Lease) => a.rental_value - b.rental_value,
    },
    {
      title: 'Vencimento',
      dataIndex: 'due_day',
      key: 'due_day',
      width: 100,
      render: (value) => `Dia ${value}`,
      sorter: (a: Lease, b: Lease) => a.due_day - b.due_day,
    },
    {
      title: 'Contrato',
      key: 'contract_status',
      width: 120,
      align: 'center',
      render: (_, record: Lease) => (
        <div className="flex flex-col items-center gap-1">
          {record.contract_generated && (
            <Badge className="bg-green-100 text-green-800">Gerado</Badge>
          )}
          {record.contract_signed && (
            <Badge className="bg-blue-100 text-blue-800">Assinado</Badge>
          )}
          {!record.contract_generated && !record.contract_signed && (
            <Badge variant="secondary">Pendente</Badge>
          )}
        </div>
      ),
    },
    {
      title: 'Ações',
      key: 'actions',
      width: 200,
      fixed: 'right',
      render: (_, record: Lease) => (
        <TooltipProvider>
          <div className="flex items-center gap-1">
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => handlers.onEdit(record)}
                >
                  <Pencil className="h-4 w-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Editar Locação</TooltipContent>
            </Tooltip>

            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => handlers.onGenerateContract(record)}
                >
                  <FilePlus className="h-4 w-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Gerar Contrato</TooltipContent>
            </Tooltip>

            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => handlers.onCalculateLateFee(record)}
                >
                  <Calculator className="h-4 w-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Calcular Multa</TooltipContent>
            </Tooltip>

            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => handlers.onChangeDueDate(record)}
                >
                  <Calendar className="h-4 w-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Mudar Vencimento</TooltipContent>
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
          </div>
        </TooltipProvider>
      ),
    },
  ];
}
