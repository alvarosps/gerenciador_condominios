'use client';

import { useState, useMemo, useCallback } from 'react';
import dynamic from 'next/dynamic';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
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
import {
  Plus,
  Trash2,
  Download,
  FileText,
  FileSpreadsheet,
  Loader2,
} from 'lucide-react';
import { toast } from 'sonner';
import { DataTable } from '@/components/tables/data-table';
import { SearchableSelect, type SearchableSelectOption } from '@/components/ui/searchable-select';
import { createLeaseColumns, getLeaseStatus } from './_components/lease-table-columns';
import { LeaseDeleteDialog, LeaseBulkDeleteDialog } from './_components/lease-dialogs';
import {
  useLeases,
  useDeleteLease,
  useTerminateLease,
} from '@/lib/api/hooks/use-leases';
import { useBuildings } from '@/lib/api/hooks/use-buildings';
import { type Lease } from '@/lib/schemas/lease.schema';
import { leaseExportColumns } from '@/lib/hooks/use-export';
import { useCrudPage } from '@/lib/hooks/use-crud-page';

// Loading component for modals
function ModalLoader() {
  return (
    <div className="fixed inset-0 flex items-center justify-center bg-background/80">
      <Loader2 className="h-8 w-8 animate-spin text-primary" />
    </div>
  );
}

// Lazy load heavy modal components to improve initial page load
const LeaseFormModal = dynamic(
  () => import('./_components/lease-form-modal').then((mod) => mod.LeaseFormModal),
  { loading: () => <ModalLoader />, ssr: false }
);

const ContractGenerateModal = dynamic(
  () => import('./_components/contract-generate-modal').then((mod) => mod.ContractGenerateModal),
  { loading: () => <ModalLoader />, ssr: false }
);

const LateFeeModal = dynamic(
  () => import('./_components/late-fee-modal').then((mod) => mod.LateFeeModal),
  { loading: () => <ModalLoader />, ssr: false }
);

const DueDateModal = dynamic(
  () => import('./_components/due-date-modal').then((mod) => mod.DueDateModal),
  { loading: () => <ModalLoader />, ssr: false }
);

type StatusFilter = 'all' | 'active' | 'expired' | 'expiring';

interface BuildingLeaseFilters {
  responsible_tenant_id: number | undefined;
  status: StatusFilter;
}

export default function LeasesPage() {
  // Page-specific modals (not handled by useCrudPage)
  const [isContractModalOpen, setIsContractModalOpen] = useState(false);
  const [isLateFeeModalOpen, setIsLateFeeModalOpen] = useState(false);
  const [isDueDateModalOpen, setIsDueDateModalOpen] = useState(false);
  const [isTerminateModalOpen, setIsTerminateModalOpen] = useState(false);
  const [actionLease, setActionLease] = useState<Lease | null>(null);

  // Per-building filter state
  const [filtersByBuilding, setFiltersByBuilding] = useState<Record<number, BuildingLeaseFilters>>({});

  const { data: leases, isLoading, error } = useLeases();
  const { data: buildings } = useBuildings();
  const deleteMutation = useDeleteLease();
  const terminateMutation = useTerminateLease();

  const crud = useCrudPage<Lease>({
    entityName: 'locação',
    entityNamePlural: 'locações',
    deleteMutation,
    exportColumns: leaseExportColumns,
    exportFilename: 'locacoes',
    exportSheetName: 'Locações',
  });

  // Group leases by building id
  const groupedLeases = useMemo(() => {
    const map = new Map<number, Lease[]>();
    leases?.forEach((lease) => {
      const buildingId = lease.apartment?.building?.id;
      if (buildingId === undefined) return;
      const existing = map.get(buildingId) ?? [];
      existing.push(lease);
      map.set(buildingId, existing);
    });
    return map;
  }, [leases]);

  const getFilters = (buildingId: number): BuildingLeaseFilters =>
    filtersByBuilding[buildingId] ?? { responsible_tenant_id: undefined, status: 'all' };

  const updateFilter = (buildingId: number, updates: Partial<BuildingLeaseFilters>): void => {
    setFiltersByBuilding((prev) => ({
      ...prev,
      [buildingId]: { ...getFilters(buildingId), ...updates },
    }));
  };

  const clearFilters = (buildingId: number): void => {
    setFiltersByBuilding((prev) =>
      Object.fromEntries(Object.entries(prev).filter(([key]) => Number(key) !== buildingId)),
    );
  };

  const getFilteredLeases = (buildingId: number, leasesForBuilding: Lease[]): Lease[] => {
    const filters = getFilters(buildingId);
    return leasesForBuilding.filter((lease) => {
      if (
        filters.responsible_tenant_id !== undefined &&
        lease.responsible_tenant?.id !== filters.responsible_tenant_id
      ) {
        return false;
      }
      if (filters.status !== 'all') {
        const { color } = getLeaseStatus(lease);
        if (filters.status === 'active' && color !== 'green') return false;
        if (filters.status === 'expired' && color !== 'red') return false;
        if (filters.status === 'expiring' && color !== 'orange') return false;
      }
      return true;
    });
  };

  // Page-specific action handlers
  const handleGenerateContract = useCallback((lease: Lease) => {
    setActionLease(lease);
    setIsContractModalOpen(true);
  }, []);

  const handleCalculateLateFee = useCallback((lease: Lease) => {
    setActionLease(lease);
    setIsLateFeeModalOpen(true);
  }, []);

  const handleChangeDueDate = useCallback((lease: Lease) => {
    setActionLease(lease);
    setIsDueDateModalOpen(true);
  }, []);

  const handleTerminate = useCallback((lease: Lease) => {
    setActionLease(lease);
    setIsTerminateModalOpen(true);
  }, []);

  const handleActionModalClose = useCallback(() => {
    setIsContractModalOpen(false);
    setIsLateFeeModalOpen(false);
    setIsDueDateModalOpen(false);
    setActionLease(null);
  }, []);

  const handleConfirmTerminate = useCallback(async () => {
    if (!actionLease?.id) return;
    try {
      await terminateMutation.mutateAsync(actionLease.id);
      toast.success('Contrato encerrado com sucesso');
      setIsTerminateModalOpen(false);
      setActionLease(null);
    } catch {
      toast.error('Erro ao encerrar contrato');
    }
  }, [actionLease, terminateMutation]);

  const handleDelete = useCallback((lease: Lease) => {
    crud.setItemToDelete(lease);
    if (lease.id !== undefined) crud.handleDeleteClick(lease.id);
  }, [crud]);

  // Memoize columns to prevent unnecessary re-renders
  const columns = useMemo(
    () =>
      createLeaseColumns({
        onEdit: crud.openEditModal,
        onDelete: handleDelete,
        onGenerateContract: handleGenerateContract,
        onCalculateLateFee: handleCalculateLateFee,
        onChangeDueDate: handleChangeDueDate,
        onTerminate: handleTerminate,
        isDeleting: crud.isDeleting,
      }),
    [
      crud.openEditModal,
      crud.isDeleting,
      handleDelete,
      handleGenerateContract,
      handleCalculateLateFee,
      handleChangeDueDate,
      handleTerminate,
    ]
  );

  if (error) {
    toast.error('Erro ao carregar locações');
  }

  return (
    <div>
      {/* Header */}
      <div className="mb-4 flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold">Locações</h1>
          <p className="text-muted-foreground mt-1">
            Gerencie os contratos de locação dos apartamentos
          </p>
        </div>
        <div className="flex gap-2">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="outline"
                disabled={crud.isExporting || !leases || leases.length === 0}
              >
                <Download className="h-4 w-4 mr-2" />
                Exportar
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent>
              <DropdownMenuItem onClick={() => crud.handleExport('excel', leases ?? [])}>
                <FileSpreadsheet className="h-4 w-4 mr-2" />
                Exportar para Excel
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => crud.handleExport('csv', leases ?? [])}>
                <FileText className="h-4 w-4 mr-2" />
                Exportar para CSV
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
          <Button onClick={crud.openCreateModal}>
            <Plus className="h-4 w-4 mr-2" />
            Nova Locação
          </Button>
        </div>
      </div>

      {/* Bulk Selection Banner */}
      {crud.bulkOps.hasSelection && (
        <div className="mb-4 p-4 bg-info/10 border border-info/20 rounded flex justify-between items-center">
          <span className="text-info font-medium">
            {crud.bulkOps.selectionCount}{' '}
            {crud.bulkOps.selectionCount === 1 ? 'locação selecionada' : 'locações selecionadas'}
          </span>
          <div className="flex gap-2">
            <Button variant="outline" onClick={crud.bulkOps.clearSelection}>
              Cancelar Seleção
            </Button>
            <Button
              variant="destructive"
              onClick={() => crud.setBulkDeleteDialogOpen(true)}
              disabled={crud.isBulkDeleting}
            >
              <Trash2 className="h-4 w-4 mr-2" />
              Excluir Selecionadas
            </Button>
          </div>
        </div>
      )}

      {/* Accordions per building */}
      <Accordion type="multiple" className="space-y-4">
        {buildings?.map((building) => {
          const buildingId = building.id;
          if (buildingId === undefined) return null;
          const buildingLeases = groupedLeases.get(buildingId) ?? [];
          const filteredLeases = getFilteredLeases(buildingId, buildingLeases);
          const filters = getFilters(buildingId);
          const hasActiveFilters =
            filters.responsible_tenant_id !== undefined || filters.status !== 'all';

          // Build tenant options from leases in this building
          const tenantOptions: SearchableSelectOption[] = [
            { value: 'all', label: 'Todos os inquilinos' },
          ];
          const seenTenantIds = new Set<number>();
          buildingLeases.forEach((lease) => {
            const tenant = lease.responsible_tenant;
            if (tenant?.id !== undefined && !seenTenantIds.has(tenant.id)) {
              seenTenantIds.add(tenant.id);
              tenantOptions.push({ value: String(tenant.id), label: tenant.name });
            }
          });

          return (
            <AccordionItem key={buildingId} value={String(buildingId)}>
              <AccordionTrigger className="px-4">
                <div className="flex items-center gap-2">
                  <span>
                    {building.name} — Nº {building.street_number}
                  </span>
                  <Badge variant="secondary">{buildingLeases.length} locações</Badge>
                </div>
              </AccordionTrigger>
              <AccordionContent className="px-4 pb-4">
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
                  <div>
                    <label className="block text-sm font-medium mb-2">Inquilino Responsável</label>
                    <SearchableSelect
                      value={
                        filters.responsible_tenant_id
                          ? String(filters.responsible_tenant_id)
                          : 'all'
                      }
                      onValueChange={(value) =>
                        updateFilter(buildingId, {
                          responsible_tenant_id: value === 'all' ? undefined : Number(value),
                        })
                      }
                      options={tenantOptions}
                      placeholder="Todos os inquilinos"
                      searchPlaceholder="Buscar inquilino..."
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-2">Status</label>
                    <Select
                      value={filters.status}
                      onValueChange={(value) =>
                        updateFilter(buildingId, { status: value as StatusFilter })
                      }
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Todos" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">Todos</SelectItem>
                        <SelectItem value="active">Ativo</SelectItem>
                        <SelectItem value="expired">Expirado</SelectItem>
                        <SelectItem value="expiring">Expirando em breve</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  {hasActiveFilters && (
                    <div className="flex items-end">
                      <Button
                        variant="outline"
                        onClick={() => clearFilters(buildingId)}
                        className="w-full"
                      >
                        Limpar Filtros
                      </Button>
                    </div>
                  )}
                </div>

                <DataTable<Lease>
                  columns={columns}
                  dataSource={filteredLeases}
                  loading={isLoading}
                  rowKey="id"
                  rowSelection={crud.bulkOps.rowSelection}
                />
              </AccordionContent>
            </AccordionItem>
          );
        })}
      </Accordion>

      {/* Modals */}
      <LeaseFormModal
        open={crud.isModalOpen}
        lease={crud.editingItem}
        onClose={crud.closeModal}
      />

      <ContractGenerateModal
        open={isContractModalOpen}
        lease={actionLease}
        onClose={handleActionModalClose}
      />

      <LateFeeModal
        open={isLateFeeModalOpen}
        lease={actionLease}
        onClose={handleActionModalClose}
      />

      <DueDateModal
        open={isDueDateModalOpen}
        lease={actionLease}
        onClose={handleActionModalClose}
      />

      {/* Terminate Contract Dialog */}
      <AlertDialog open={isTerminateModalOpen} onOpenChange={setIsTerminateModalOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Encerrar Contrato</AlertDialogTitle>
            <AlertDialogDescription>
              Tem certeza que deseja encerrar o contrato do Apto{' '}
              {actionLease?.apartment?.number} — {actionLease?.apartment?.building?.name}? O
              apartamento será marcado como disponível.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => void handleConfirmTerminate()}
              disabled={terminateMutation.isPending}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {terminateMutation.isPending ? 'Encerrando...' : 'Encerrar'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Delete Dialogs */}
      <LeaseDeleteDialog
        open={crud.deleteDialogOpen}
        onOpenChange={crud.setDeleteDialogOpen}
        onConfirm={crud.handleDelete}
        isDeleting={crud.isDeleting}
      />

      <LeaseBulkDeleteDialog
        open={crud.bulkDeleteDialogOpen}
        onOpenChange={crud.setBulkDeleteDialogOpen}
        onConfirm={crud.handleBulkDelete}
        isDeleting={crud.isBulkDeleting}
        selectionCount={crud.bulkOps.selectionCount}
      />
    </div>
  );
}
