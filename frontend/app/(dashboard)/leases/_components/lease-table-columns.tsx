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
  XCircle,
  TrendingUp,
  History,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { type Column } from '@/components/tables/data-table';
import { type Lease } from '@/lib/schemas/lease.schema';
import { formatCurrency } from '@/lib/utils/formatters';
import { format, isPast, isFuture, differenceInDays, differenceInMonths, parseISO } from 'date-fns';

export interface LeaseActionHandlers {
  onEdit: (lease: Lease) => void;
  onDelete: (lease: Lease) => void;
  onGenerateContract: (lease: Lease) => void;
  onCalculateLateFee: (lease: Lease) => void;
  onChangeDueDate: (lease: Lease) => void;
  onTerminate: (lease: Lease) => void;
  onAdjustRent: (lease: Lease) => void;
  onViewAdjustmentHistory: (lease: Lease) => void;
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
    blue: 'bg-info/10 text-info hover:bg-info/20',
    red: 'bg-destructive/10 text-destructive hover:bg-destructive/20',
    orange: 'bg-warning/10 text-warning hover:bg-warning/20',
    green: 'bg-success/10 text-success hover:bg-success/20',
    yellow: 'bg-warning/10 text-warning hover:bg-warning/20',
  };

  return [
    {
      title: 'Apto',
      key: 'apartment',
      width: 80,
      render: (_, record: Lease) => (
        <div className="font-medium">Apto {record.apartment?.number}</div>
      ),
      sorter: (a: Lease, b: Lease) => (a.apartment?.number ?? 0) - (b.apartment?.number ?? 0),
    },
    {
      title: 'Inquilino Responsável',
      key: 'tenant',
      width: 200,
      render: (_, record: Lease) => (
        <div>
          <div className="font-medium">{record.responsible_tenant?.name}</div>
          {record.tenants && record.tenants.length > 1 && (
            <div className="text-xs text-muted-foreground">
              +{record.tenants.length - 1} inquilino(s)
            </div>
          )}
        </div>
      ),
      sorter: (a: Lease, b: Lease) =>
        (a.responsible_tenant?.name ?? '').localeCompare(b.responsible_tenant?.name ?? ''),
    },
    {
      title: 'Período',
      key: 'period',
      width: 200,
      render: (_, record: Lease) => (
        <div className="text-sm">
          <div>{format(parseISO(record.start_date), 'dd/MM/yyyy')}</div>
          <div className="text-muted-foreground">
            até {record.final_date ? format(parseISO(record.final_date), 'dd/MM/yyyy') : 'N/A'}
          </div>
          <div className="text-xs text-muted-foreground">
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
          <Badge className={cn(badgeVariants[color] ?? 'bg-muted text-muted-foreground')}>
            {status}
          </Badge>
        );
      },
      sorter: (a: Lease, b: Lease) => {
        const priority: Record<string, number> = { red: 0, orange: 1, green: 2, blue: 3 };
        const aColor = getLeaseStatus(a).color;
        const bColor = getLeaseStatus(b).color;
        return (priority[aColor] ?? 4) - (priority[bColor] ?? 4);
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
                <Badge className={cn(badgeVariants[color] ?? 'bg-muted text-muted-foreground', 'cursor-help')}>
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
      sorter: (a: Lease, b: Lease) => {
        const aStatus = getMinimumPeriodStatus(a);
        const bStatus = getMinimumPeriodStatus(b);
        const aVal = aStatus.completed ? -1 : aStatus.monthsRemaining;
        const bVal = bStatus.completed ? -1 : bStatus.monthsRemaining;
        return aVal - bVal;
      },
    },
    {
      title: 'Valor',
      key: 'rental_value',
      width: 120,
      render: (_, record: Lease) => formatCurrency(record.rental_value ?? 0),
      sorter: (a: Lease, b: Lease) => (a.rental_value ?? 0) - (b.rental_value ?? 0),
    },
    {
      title: 'Vencimento',
      key: 'due_day',
      width: 100,
      render: (_, record: Lease) => `Dia ${String(record.responsible_tenant?.due_day ?? '-')}`,
      sorter: (a: Lease, b: Lease) => (a.responsible_tenant?.due_day ?? 0) - (b.responsible_tenant?.due_day ?? 0),
    },
    {
      title: 'Contrato',
      key: 'contract_status',
      width: 120,
      align: 'center',
      render: (_, record: Lease) => (
        <div className="flex flex-col items-center gap-1">
          {record.contract_generated && (
            <Badge className="bg-success/10 text-success">Gerado</Badge>
          )}
          {record.contract_signed && (
            <Badge className="bg-info/10 text-info">Assinado</Badge>
          )}
          {!record.contract_generated && !record.contract_signed && (
            <Badge variant="secondary">Pendente</Badge>
          )}
        </div>
      ),
      sorter: (a: Lease, b: Lease) => {
        const contractPriority = (l: Lease): number => {
          if (l.contract_signed) return 0;
          if (l.contract_generated) return 1;
          return 2;
        };
        return contractPriority(a) - contractPriority(b);
      },
    },
    {
      title: 'Ações',
      key: 'actions',
      width: 240,
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
                  onClick={() => handlers.onAdjustRent(record)}
                >
                  <TrendingUp className="h-4 w-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Reajustar Aluguel</TooltipContent>
            </Tooltip>

            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => handlers.onViewAdjustmentHistory(record)}
                >
                  <History className="h-4 w-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Histórico de Reajustes</TooltipContent>
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

            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => handlers.onTerminate(record)}
                >
                  <XCircle className="h-4 w-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Encerrar Contrato</TooltipContent>
            </Tooltip>
          </div>
        </TooltipProvider>
      ),
    },
  ];
}
