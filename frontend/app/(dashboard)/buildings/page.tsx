'use client';

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
import {
  Plus,
  Pencil,
  Trash2,
  Download,
  FileSpreadsheet,
  FileText,
} from 'lucide-react';
import { toast } from 'sonner';
import { DataTable, Column } from '@/components/tables/data-table';
import { BuildingFormModal } from './_components/building-form-modal';
import {
  useBuildings,
  useDeleteBuilding,
} from '@/lib/api/hooks/use-buildings';
import { Building } from '@/lib/schemas/building.schema';
import { buildingExportColumns } from '@/lib/hooks/use-export';
import { useCrudPage } from '@/lib/hooks/use-crud-page';

export default function BuildingsPage() {
  const { data: buildings, isLoading, error } = useBuildings();
  const deleteMutation = useDeleteBuilding();

  // Use the consolidated CRUD hook for all state management
  const crud = useCrudPage<Building>({
    entityName: 'prédio',
    entityNamePlural: 'prédios',
    deleteMutation,
    exportColumns: buildingExportColumns,
    exportFilename: 'predios',
    exportSheetName: 'Prédios',
    deleteErrorMessage: 'Erro ao excluir prédio. Verifique se não há apartamentos vinculados.',
  });

  const columns: Column<Building>[] = [
    {
      title: 'Número',
      dataIndex: 'street_number',
      key: 'street_number',
      sorter: (a: Building, b: Building) => a.street_number - b.street_number,
      width: 120,
    },
    {
      title: 'Nome',
      dataIndex: 'name',
      key: 'name',
      sorter: (a: Building, b: Building) => a.name.localeCompare(b.name),
    },
    {
      title: 'Endereço',
      dataIndex: 'address',
      key: 'address',
    },
    {
      title: 'Ações',
      key: 'actions',
      width: 150,
      fixed: 'right',
      render: (_, record: Building) => (
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => crud.openEditModal(record)}
          >
            <Pencil className="h-4 w-4 mr-1" />
            Editar
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              crud.setItemToDelete(record);
              crud.handleDeleteClick(record.id!);
            }}
            disabled={crud.isDeleting}
          >
            <Trash2 className="h-4 w-4 mr-1" />
            Excluir
          </Button>
        </div>
      ),
    },
  ];

  if (error) {
    toast.error('Erro ao carregar prédios');
  }

  return (
    <div>
      <div className="mb-4 flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold">Prédios</h1>
          <p className="text-gray-600 mt-1">
            Gerencie os prédios do condomínio
          </p>
        </div>
        <div className="flex gap-2">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="outline"
                disabled={crud.isExporting || !buildings || buildings.length === 0}
              >
                <Download className="h-4 w-4 mr-2" />
                Exportar
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent>
              <DropdownMenuItem onClick={() => crud.handleExport('excel', buildings || [])}>
                <FileSpreadsheet className="h-4 w-4 mr-2" />
                Exportar para Excel
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => crud.handleExport('csv', buildings || [])}>
                <FileText className="h-4 w-4 mr-2" />
                Exportar para CSV
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
          <Button onClick={crud.openCreateModal}>
            <Plus className="h-4 w-4 mr-2" />
            Novo Prédio
          </Button>
        </div>
      </div>

      {crud.bulkOps.hasSelection && (
        <div className="mb-4 p-4 bg-blue-50 border border-blue-200 rounded flex justify-between items-center">
          <span className="text-blue-700 font-medium">
            {crud.bulkOps.selectionCount} {crud.bulkOps.selectionCount === 1 ? 'prédio selecionado' : 'prédios selecionados'}
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
              Excluir Selecionados
            </Button>
          </div>
        </div>
      )}

      <DataTable<Building>
        columns={columns}
        dataSource={buildings}
        loading={isLoading}
        rowKey="id"
        rowSelection={crud.bulkOps.rowSelection}
      />

      <BuildingFormModal
        open={crud.isModalOpen}
        building={crud.editingItem}
        onClose={crud.closeModal}
      />

      <AlertDialog open={crud.deleteDialogOpen} onOpenChange={crud.setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Excluir prédio</AlertDialogTitle>
            <AlertDialogDescription>
              Tem certeza que deseja excluir {crud.itemToDelete?.name ? `"${crud.itemToDelete.name}"` : 'este prédio'}? Esta ação não pode ser desfeita.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction
              onClick={crud.handleDelete}
              disabled={crud.isDeleting}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {crud.isDeleting ? 'Excluindo...' : 'Excluir'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <AlertDialog open={crud.bulkDeleteDialogOpen} onOpenChange={crud.setBulkDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Excluir prédios selecionados</AlertDialogTitle>
            <AlertDialogDescription>
              Tem certeza que deseja excluir {crud.bulkOps.selectionCount}{' '}
              {crud.bulkOps.selectionCount === 1 ? 'prédio' : 'prédios'}? Esta ação não pode
              ser desfeita.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction
              onClick={crud.handleBulkDelete}
              disabled={crud.isBulkDeleting}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {crud.isBulkDeleting ? 'Excluindo...' : 'Excluir'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
