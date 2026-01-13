'use client';

import { useState, useMemo, useCallback } from 'react';
import dynamic from 'next/dynamic';
import { Button } from '@/components/ui/button';
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
import { LeaseFiltersCard, LeaseFilters } from './_components/lease-filters';
import { createLeaseColumns } from './_components/lease-table-columns';
import { LeaseDeleteDialog, LeaseBulkDeleteDialog } from './_components/lease-dialogs';
import {
  useLeases,
  useDeleteLease,
} from '@/lib/api/hooks/use-leases';
import { useApartments } from '@/lib/api/hooks/use-apartments';
import { useTenants } from '@/lib/api/hooks/use-tenants';
import { Lease } from '@/lib/schemas/lease.schema';
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

export default function LeasesPage() {
  // Page-specific modals (not handled by useCrudPage)
  const [isContractModalOpen, setIsContractModalOpen] = useState(false);
  const [isLateFeeModalOpen, setIsLateFeeModalOpen] = useState(false);
  const [isDueDateModalOpen, setIsDueDateModalOpen] = useState(false);
  const [actionLease, setActionLease] = useState<Lease | null>(null);

  // Page-specific filters
  const [filters, setFilters] = useState<LeaseFilters>({
    apartment_id: undefined,
    responsible_tenant_id: undefined,
    is_active: undefined,
    is_expired: undefined,
    expiring_soon: undefined,
  });

  const { data: leases, isLoading, error } = useLeases(filters);
  const { data: apartments } = useApartments();
  const { data: tenants } = useTenants();
  const deleteMutation = useDeleteLease();

  // Use the consolidated CRUD hook for standard CRUD operations
  const crud = useCrudPage<Lease>({
    entityName: 'locação',
    entityNamePlural: 'locações',
    deleteMutation,
    exportColumns: leaseExportColumns,
    exportFilename: 'locacoes',
    exportSheetName: 'Locações',
  });

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

  const handleActionModalClose = useCallback(() => {
    setIsContractModalOpen(false);
    setIsLateFeeModalOpen(false);
    setIsDueDateModalOpen(false);
    setActionLease(null);
  }, []);

  const handleDelete = useCallback((lease: Lease) => {
    crud.setItemToDelete(lease);
    crud.handleDeleteClick(lease.id!);
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
        isDeleting: crud.isDeleting,
      }),
    [crud.openEditModal, crud.isDeleting, handleDelete, handleGenerateContract, handleCalculateLateFee, handleChangeDueDate]
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
          <p className="text-gray-600 mt-1">
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
              <DropdownMenuItem onClick={() => crud.handleExport('excel', leases || [])}>
                <FileSpreadsheet className="h-4 w-4 mr-2" />
                Exportar para Excel
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => crud.handleExport('csv', leases || [])}>
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
        <div className="mb-4 p-4 bg-blue-50 border border-blue-200 rounded flex justify-between items-center">
          <span className="text-blue-700 font-medium">
            {crud.bulkOps.selectionCount} {crud.bulkOps.selectionCount === 1 ? 'locação selecionada' : 'locações selecionadas'}
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

      {/* Filters */}
      <LeaseFiltersCard
        filters={filters}
        onFiltersChange={setFilters}
        apartments={apartments}
        tenants={tenants}
      />

      {/* Data Table */}
      <DataTable<Lease>
        columns={columns}
        dataSource={leases}
        loading={isLoading}
        rowKey="id"
        rowSelection={crud.bulkOps.rowSelection}
      />

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

      {/* Dialogs */}
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
