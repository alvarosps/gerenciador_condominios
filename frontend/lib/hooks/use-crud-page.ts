import { useState, useCallback } from 'react';
import { UseMutationResult } from '@tanstack/react-query';
import { toast } from 'sonner';
import { useExport } from './use-export';
import { useBulkOperations } from './use-bulk-operations';

/**
 * Export column definition
 */
interface ExportColumn {
  key: string;
  label: string;
  format?: (value: unknown, record: Record<string, unknown>) => string | number;
}

/**
 * Configuration options for useCrudPage hook
 */
interface UseCrudPageOptions {
  /**
   * Entity name in singular (e.g., 'prédio', 'inquilino')
   */
  entityName: string;
  /**
   * Entity name in plural (e.g., 'prédios', 'inquilinos')
   */
  entityNamePlural: string;
  /**
   * Delete mutation hook result
   */
  deleteMutation: UseMutationResult<unknown, Error, number>;
  /**
   * Optional bulk delete mutation hook result
   */
  bulkDeleteMutation?: UseMutationResult<unknown, Error, number[]>;
  /**
   * Export columns configuration
   */
  exportColumns?: ExportColumn[];
  /**
   * Base filename for exports (without extension)
   */
  exportFilename?: string;
  /**
   * Sheet name for Excel exports
   */
  exportSheetName?: string;
  /**
   * Callback when item is successfully deleted
   */
  onDeleteSuccess?: () => void;
  /**
   * Callback when item deletion fails
   */
  onDeleteError?: (error: Error) => void;
  /**
   * Custom error message for delete failures
   */
  deleteErrorMessage?: string;
}

/**
 * Return type of useCrudPage hook
 */
interface UseCrudPageReturn<T> {
  // Modal state
  isModalOpen: boolean;
  setIsModalOpen: (open: boolean) => void;
  editingItem: T | null;
  setEditingItem: (item: T | null) => void;
  openCreateModal: () => void;
  openEditModal: (item: T) => void;
  closeModal: () => void;

  // Delete dialog state
  deleteDialogOpen: boolean;
  setDeleteDialogOpen: (open: boolean) => void;
  deleteId: number | null;
  setDeleteId: (id: number | null) => void;
  handleDeleteClick: (id: number) => void;
  handleDelete: () => Promise<void>;
  isDeleting: boolean;
  itemToDelete: T | null;
  setItemToDelete: (item: T | null) => void;

  // Bulk delete state
  bulkDeleteDialogOpen: boolean;
  setBulkDeleteDialogOpen: (open: boolean) => void;
  handleBulkDelete: () => Promise<void>;
  isBulkDeleting: boolean;

  // Bulk operations
  bulkOps: ReturnType<typeof useBulkOperations>;

  // Export state and handlers
  isExporting: boolean;
  handleExport: (format: 'excel' | 'csv', data: T[]) => Promise<void>;
}

/**
 * A composite hook that consolidates common CRUD page state and handlers.
 *
 * This hook reduces boilerplate in CRUD pages by providing:
 * - Modal state management (create/edit)
 * - Delete confirmation dialog state
 * - Bulk delete dialog state
 * - Export functionality
 * - Bulk operations
 *
 * @example
 * ```tsx
 * function BuildingsPage() {
 *   const { data: buildings } = useBuildings();
 *   const deleteMutation = useDeleteBuilding();
 *
 *   const crud = useCrudPage<Building>({
 *     entityName: 'prédio',
 *     entityNamePlural: 'prédios',
 *     deleteMutation,
 *     exportColumns: buildingExportColumns,
 *     exportFilename: 'predios',
 *     exportSheetName: 'Prédios',
 *   });
 *
 *   return (
 *     <>
 *       <Button onClick={crud.openCreateModal}>Novo Prédio</Button>
 *
 *       <DataTable
 *         onRowClick={(row) => crud.openEditModal(row)}
 *         onDeleteClick={(row) => {
 *           crud.setItemToDelete(row);
 *           crud.handleDeleteClick(row.id);
 *         }}
 *       />
 *
 *       <BuildingFormModal
 *         open={crud.isModalOpen}
 *         building={crud.editingItem}
 *         onClose={crud.closeModal}
 *       />
 *
 *       <DeleteConfirmDialog
 *         open={crud.deleteDialogOpen}
 *         onOpenChange={crud.setDeleteDialogOpen}
 *         itemName={crud.itemToDelete?.name}
 *         onConfirm={crud.handleDelete}
 *         isLoading={crud.isDeleting}
 *       />
 *     </>
 *   );
 * }
 * ```
 */
export function useCrudPage<T extends { id?: number }>({
  entityName,
  entityNamePlural,
  deleteMutation,
  bulkDeleteMutation,
  exportColumns,
  exportFilename,
  exportSheetName,
  onDeleteSuccess,
  onDeleteError,
  deleteErrorMessage,
}: UseCrudPageOptions): UseCrudPageReturn<T> {
  // Modal state
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingItem, setEditingItem] = useState<T | null>(null);

  // Delete dialog state
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleteId, setDeleteId] = useState<number | null>(null);
  const [itemToDelete, setItemToDelete] = useState<T | null>(null);

  // Bulk delete dialog state
  const [bulkDeleteDialogOpen, setBulkDeleteDialogOpen] = useState(false);

  // Hooks
  const { exportToExcel, exportToCSV, isExporting } = useExport();
  const bulkOps = useBulkOperations({
    entityName,
    entityNamePlural,
  });

  // Modal handlers
  const openCreateModal = useCallback(() => {
    setEditingItem(null);
    setIsModalOpen(true);
  }, []);

  const openEditModal = useCallback((item: T) => {
    setEditingItem(item);
    setIsModalOpen(true);
  }, []);

  const closeModal = useCallback(() => {
    setIsModalOpen(false);
    setEditingItem(null);
  }, []);

  // Delete handlers
  const handleDeleteClick = useCallback((id: number) => {
    setDeleteId(id);
    setDeleteDialogOpen(true);
  }, []);

  const handleDelete = useCallback(async () => {
    if (!deleteId) return;

    try {
      await deleteMutation.mutateAsync(deleteId);
      toast.success(`${entityName.charAt(0).toUpperCase() + entityName.slice(1)} excluído com sucesso`);
      setDeleteDialogOpen(false);
      setDeleteId(null);
      setItemToDelete(null);
      onDeleteSuccess?.();
    } catch (error) {
      const message = deleteErrorMessage || `Erro ao excluir ${entityName}. Verifique se não há dependências vinculadas.`;
      toast.error(message);
      onDeleteError?.(error as Error);
      console.error('Delete error:', error);
    }
  }, [deleteId, deleteMutation, entityName, deleteErrorMessage, onDeleteSuccess, onDeleteError]);

  // Bulk delete handler
  const handleBulkDelete = useCallback(async () => {
    if (!bulkDeleteMutation || bulkOps.selectedRowKeys.length === 0) return;

    try {
      const ids = bulkOps.selectedRowKeys.map(key => Number(key));
      await bulkDeleteMutation.mutateAsync(ids);
      toast.success(`${ids.length} ${entityNamePlural} excluídos com sucesso`);
      setBulkDeleteDialogOpen(false);
      bulkOps.clearSelection();
    } catch (error) {
      toast.error(`Erro ao excluir ${entityNamePlural}`);
      console.error('Bulk delete error:', error);
    }
  }, [bulkDeleteMutation, bulkOps, entityNamePlural]);

  // Export handler
  const handleExport = useCallback(
    async (format: 'excel' | 'csv', data: T[]) => {
      if (!exportColumns || !exportFilename) {
        toast.warning('Exportação não configurada');
        return;
      }

      if (!data || data.length === 0) {
        toast.warning('Não há dados para exportar');
        return;
      }

      try {
        if (format === 'excel') {
          await exportToExcel(data, exportColumns, {
            filename: exportFilename,
            sheetName: exportSheetName || entityNamePlural,
          });
          toast.success('Arquivo Excel exportado com sucesso!');
        } else {
          await exportToCSV(data, exportColumns, {
            filename: exportFilename,
          });
          toast.success('Arquivo CSV exportado com sucesso!');
        }
      } catch (error) {
        toast.error('Erro ao exportar arquivo');
        console.error('Export error:', error);
      }
    },
    [exportColumns, exportFilename, exportSheetName, entityNamePlural, exportToExcel, exportToCSV]
  );

  return {
    // Modal state
    isModalOpen,
    setIsModalOpen,
    editingItem,
    setEditingItem,
    openCreateModal,
    openEditModal,
    closeModal,

    // Delete dialog state
    deleteDialogOpen,
    setDeleteDialogOpen,
    deleteId,
    setDeleteId,
    handleDeleteClick,
    handleDelete,
    isDeleting: deleteMutation.isPending,
    itemToDelete,
    setItemToDelete,

    // Bulk delete state
    bulkDeleteDialogOpen,
    setBulkDeleteDialogOpen,
    handleBulkDelete,
    isBulkDeleting: bulkDeleteMutation?.isPending ?? false,

    // Bulk operations
    bulkOps,

    // Export state and handlers
    isExporting,
    handleExport,
  };
}
