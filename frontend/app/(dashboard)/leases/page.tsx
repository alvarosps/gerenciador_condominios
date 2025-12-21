'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Card, CardContent } from '@/components/ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import {
  Plus,
  Pencil,
  Trash2,
  FileText,
  Download,
  FileSpreadsheet,
  Calculator,
  Calendar,
  FilePlus,
} from 'lucide-react';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';
import { DataTable, Column } from '@/components/tables/data-table';
import { LeaseFormModal } from './_components/lease-form-modal';
import { ContractGenerateModal } from './_components/contract-generate-modal';
import { LateFeeModal } from './_components/late-fee-modal';
import { DueDateModal } from './_components/due-date-modal';
import {
  useLeases,
  useDeleteLease,
} from '@/lib/api/hooks/use-leases';
import { useApartments } from '@/lib/api/hooks/use-apartments';
import { useTenants } from '@/lib/api/hooks/use-tenants';
import { Lease } from '@/lib/schemas/lease.schema';
import { formatCurrency } from '@/lib/utils/formatters';
import { format, isPast, isFuture, differenceInDays, parseISO } from 'date-fns';
import { useExport, leaseExportColumns } from '@/lib/hooks/use-export';
import { useBulkOperations } from '@/lib/hooks/use-bulk-operations';

export default function LeasesPage() {
  const [isFormModalOpen, setIsFormModalOpen] = useState(false);
  const [isContractModalOpen, setIsContractModalOpen] = useState(false);
  const [isLateFeeModalOpen, setIsLateFeeModalOpen] = useState(false);
  const [isDueDateModalOpen, setIsDueDateModalOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleteId, setDeleteId] = useState<number | null>(null);
  const [bulkDeleteDialogOpen, setBulkDeleteDialogOpen] = useState(false);
  const [selectedLease, setSelectedLease] = useState<Lease | null>(null);
  const [filters, setFilters] = useState({
    apartment_id: undefined as number | undefined,
    responsible_tenant_id: undefined as number | undefined,
    is_active: undefined as boolean | undefined,
    is_expired: undefined as boolean | undefined,
    expiring_soon: undefined as boolean | undefined,
  });

  const { data: leases, isLoading, error } = useLeases(filters);
  const { data: apartments } = useApartments();
  const { data: tenants } = useTenants();
  const deleteMutation = useDeleteLease();
  const { exportToExcel, exportToCSV, isExporting } = useExport();
  const bulkOps = useBulkOperations({
    entityName: 'locação',
    entityNamePlural: 'locações',
  });

  const handleEdit = (lease: Lease) => {
    setSelectedLease(lease);
    setIsFormModalOpen(true);
  };

  const handleDeleteClick = (id: number) => {
    setDeleteId(id);
    setDeleteDialogOpen(true);
  };

  const handleDelete = async () => {
    if (!deleteId) return;
    try {
      await deleteMutation.mutateAsync(deleteId);
      toast.success('Locação excluída com sucesso');
      setDeleteDialogOpen(false);
      setDeleteId(null);
    } catch (error) {
      toast.error('Erro ao excluir locação');
      console.error('Delete error:', error);
    }
  };

  const handleGenerateContract = (lease: Lease) => {
    setSelectedLease(lease);
    setIsContractModalOpen(true);
  };

  const handleCalculateLateFee = (lease: Lease) => {
    setSelectedLease(lease);
    setIsLateFeeModalOpen(true);
  };

  const handleChangeDueDate = (lease: Lease) => {
    setSelectedLease(lease);
    setIsDueDateModalOpen(true);
  };

  const handleModalClose = () => {
    setIsFormModalOpen(false);
    setIsContractModalOpen(false);
    setIsLateFeeModalOpen(false);
    setIsDueDateModalOpen(false);
    setSelectedLease(null);
  };

  const clearFilters = () => {
    setFilters({
      apartment_id: undefined,
      responsible_tenant_id: undefined,
      is_active: undefined,
      is_expired: undefined,
      expiring_soon: undefined,
    });
  };

  const handleExport = async (format: 'excel' | 'csv') => {
    if (!leases || leases.length === 0) {
      toast.warning('Não há dados para exportar');
      return;
    }

    try {
      if (format === 'excel') {
        await exportToExcel(leases, leaseExportColumns, {
          filename: 'locacoes',
          sheetName: 'Locações',
        });
        toast.success('Arquivo Excel exportado com sucesso!');
      } else {
        await exportToCSV(leases, leaseExportColumns, {
          filename: 'locacoes',
        });
        toast.success('Arquivo CSV exportado com sucesso!');
      }
    } catch {
      toast.error('Erro ao exportar arquivo');
    }
  };

  const handleBulkDeleteClick = () => {
    setBulkDeleteDialogOpen(true);
  };

  const handleBulkDelete = () => {
    bulkOps.handleBulkDelete(deleteMutation.mutateAsync);
    setBulkDeleteDialogOpen(false);
  };

  const getLeaseStatus = (lease: Lease) => {
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
  };

  const columns: Column<Lease>[] = [
    {
      title: 'Prédio / Apto',
      key: 'apartment',
      width: 180,
      render: (_, record: Lease, _index) => (
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
      render: (_, record: Lease, _index) => (
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
      render: (_, record: Lease, _index) => (
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
      render: (_, record: Lease, _index) => {
        const { status, color } = getLeaseStatus(record);
        const badgeVariants: Record<string, string> = {
          blue: 'bg-blue-100 text-blue-800 hover:bg-blue-200',
          red: 'bg-red-100 text-red-800 hover:bg-red-200',
          orange: 'bg-orange-100 text-orange-800 hover:bg-orange-200',
          green: 'bg-green-100 text-green-800 hover:bg-green-200',
        };
        return (
          <Badge className={cn(badgeVariants[color] || 'bg-gray-100 text-gray-800')}>
            {status}
          </Badge>
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
      render: (_, record: Lease, _index) => (
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
      render: (_, record: Lease, _index) => (
        <TooltipProvider>
          <div className="flex items-center gap-1">
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => handleEdit(record)}
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
                  onClick={() => handleGenerateContract(record)}
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
                  onClick={() => handleCalculateLateFee(record)}
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
                  onClick={() => handleChangeDueDate(record)}
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
                  onClick={() => handleDeleteClick(record.id!)}
                  disabled={deleteMutation.isPending}
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

  if (error) {
    toast.error('Erro ao carregar locações');
  }

  const hasActiveFilters = Object.values(filters).some((value) => value !== undefined);

  return (
    <div>
      <div className="mb-4 flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold">Locações</h1>
          <p className="text-gray-600 mt-1">
            Gerencie os contratos de locação dos apartamentos
          </p>
        </div>
        <div className="flex gap-2">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="outline"
                disabled={isExporting || !leases || leases.length === 0}
              >
                <Download className="h-4 w-4 mr-2" />
                Exportar
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent>
              <DropdownMenuItem onClick={() => handleExport('excel')}>
                <FileSpreadsheet className="h-4 w-4 mr-2" />
                Exportar para Excel
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => handleExport('csv')}>
                <FileText className="h-4 w-4 mr-2" />
                Exportar para CSV
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
          <Button onClick={() => setIsFormModalOpen(true)}>
            <Plus className="h-4 w-4 mr-2" />
            Nova Locação
          </Button>
        </div>
      </div>

      {bulkOps.hasSelection && (
        <div className="mb-4 p-4 bg-blue-50 border border-blue-200 rounded flex justify-between items-center">
          <span className="text-blue-700 font-medium">
            {bulkOps.selectionCount} {bulkOps.selectionCount === 1 ? 'locação selecionada' : 'locações selecionadas'}
          </span>
          <div className="flex gap-2">
            <Button variant="outline" onClick={bulkOps.clearSelection}>
              Cancelar Seleção
            </Button>
            <Button
              variant="destructive"
              onClick={handleBulkDeleteClick}
              disabled={deleteMutation.isPending}
            >
              <Trash2 className="h-4 w-4 mr-2" />
              Excluir Selecionadas
            </Button>
          </div>
        </div>
      )}

      {/* Filters */}
      <Card className="mb-4">
        <CardContent className="pt-6">
          <div className="flex gap-4 flex-wrap items-end">
            <div className="flex-1 min-w-[200px]">
              <label className="block text-sm font-medium mb-2">Apartamento</label>
              <Select
                value={filters.apartment_id ? String(filters.apartment_id) : ''}
                onValueChange={(value) =>
                  setFilters({
                    ...filters,
                    apartment_id: value === '' ? undefined : Number(value),
                  })
                }
              >
                <SelectTrigger>
                  <SelectValue placeholder="Todos os apartamentos" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">Todos os apartamentos</SelectItem>
                  {apartments?.map((apt) => (
                    <SelectItem key={apt.id} value={String(apt.id)}>
                      {apt.building?.name} - Apto {apt.number}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="flex-1 min-w-[200px]">
              <label className="block text-sm font-medium mb-2">Inquilino</label>
              <Select
                value={filters.responsible_tenant_id ? String(filters.responsible_tenant_id) : ''}
                onValueChange={(value) =>
                  setFilters({
                    ...filters,
                    responsible_tenant_id: value === '' ? undefined : Number(value),
                  })
                }
              >
                <SelectTrigger>
                  <SelectValue placeholder="Todos os inquilinos" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">Todos os inquilinos</SelectItem>
                  {tenants?.map((t) => (
                    <SelectItem key={t.id} value={String(t.id!)}>
                      {t.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="flex-1 min-w-[150px]">
              <label className="block text-sm font-medium mb-2">Status</label>
              <Select
                value={
                  filters.is_active !== undefined
                    ? 'active'
                    : filters.is_expired !== undefined
                    ? 'expired'
                    : filters.expiring_soon !== undefined
                    ? 'expiring'
                    : ''
                }
                onValueChange={(value) => {
                  if (value === 'active') {
                    setFilters({
                      ...filters,
                      is_active: true,
                      is_expired: undefined,
                      expiring_soon: undefined,
                    });
                  } else if (value === 'expired') {
                    setFilters({
                      ...filters,
                      is_active: undefined,
                      is_expired: true,
                      expiring_soon: undefined,
                    });
                  } else if (value === 'expiring') {
                    setFilters({
                      ...filters,
                      is_active: undefined,
                      is_expired: undefined,
                      expiring_soon: true,
                    });
                  } else {
                    setFilters({
                      ...filters,
                      is_active: undefined,
                      is_expired: undefined,
                      expiring_soon: undefined,
                    });
                  }
                }}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Todos" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">Todos</SelectItem>
                  <SelectItem value="active">Ativo</SelectItem>
                  <SelectItem value="expired">Expirado</SelectItem>
                  <SelectItem value="expiring">Expirando em breve</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {hasActiveFilters && (
              <Button variant="outline" onClick={clearFilters}>
                Limpar Filtros
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      <DataTable<Lease>
        columns={columns}
        dataSource={leases}
        loading={isLoading}
        rowKey="id"
        rowSelection={bulkOps.rowSelection}
      />

      <LeaseFormModal
        open={isFormModalOpen}
        lease={selectedLease}
        onClose={handleModalClose}
      />

      <ContractGenerateModal
        open={isContractModalOpen}
        lease={selectedLease}
        onClose={handleModalClose}
      />

      <LateFeeModal
        open={isLateFeeModalOpen}
        lease={selectedLease}
        onClose={handleModalClose}
      />

      <DueDateModal
        open={isDueDateModalOpen}
        lease={selectedLease}
        onClose={handleModalClose}
      />

      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Excluir locação</AlertDialogTitle>
            <AlertDialogDescription>
              Tem certeza que deseja excluir esta locação? Esta ação não pode ser desfeita.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Excluir
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <AlertDialog open={bulkDeleteDialogOpen} onOpenChange={setBulkDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Excluir locações selecionadas</AlertDialogTitle>
            <AlertDialogDescription>
              Tem certeza que deseja excluir {bulkOps.selectionCount}{' '}
              {bulkOps.selectionCount === 1 ? 'locação' : 'locações'}? Esta ação não pode
              ser desfeita.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleBulkDelete}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Excluir
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
