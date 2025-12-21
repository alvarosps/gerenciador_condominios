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
import { useExport, buildingExportColumns } from '@/lib/hooks/use-export';
import { useBulkOperations } from '@/lib/hooks/use-bulk-operations';

export default function BuildingsPage() {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingBuilding, setEditingBuilding] = useState<Building | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleteId, setDeleteId] = useState<number | null>(null);
  const [bulkDeleteDialogOpen, setBulkDeleteDialogOpen] = useState(false);

  const { data: buildings, isLoading, error } = useBuildings();
  const deleteMutation = useDeleteBuilding();
  const { exportToExcel, exportToCSV, isExporting } = useExport();
  const bulkOps = useBulkOperations({
    entityName: 'prédio',
    entityNamePlural: 'prédios',
  });

  const handleEdit = (building: Building) => {
    setEditingBuilding(building);
    setIsModalOpen(true);
  };

  const handleDeleteClick = (id: number) => {
    setDeleteId(id);
    setDeleteDialogOpen(true);
  };

  const handleDelete = async () => {
    if (!deleteId) return;
    try {
      await deleteMutation.mutateAsync(deleteId);
      toast.success('Prédio excluído com sucesso');
      setDeleteDialogOpen(false);
      setDeleteId(null);
    } catch (error) {
      toast.error('Erro ao excluir prédio. Verifique se não há apartamentos vinculados.');
      console.error('Delete error:', error);
    }
  };

  const handleModalClose = () => {
    setIsModalOpen(false);
    setEditingBuilding(null);
  };

  const handleExport = async (format: 'excel' | 'csv') => {
    if (!buildings || buildings.length === 0) {
      toast.warning('Não há dados para exportar');
      return;
    }

    try {
      if (format === 'excel') {
        await exportToExcel(buildings, buildingExportColumns, {
          filename: 'predios',
          sheetName: 'Prédios',
        });
        toast.success('Arquivo Excel exportado com sucesso!');
      } else {
        await exportToCSV(buildings, buildingExportColumns, {
          filename: 'predios',
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
      render: (_, record: Building, _index) => (
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => handleEdit(record)}
          >
            <Pencil className="h-4 w-4 mr-1" />
            Editar
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => handleDeleteClick(record.id!)}
            disabled={deleteMutation.isPending}
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
                disabled={isExporting || !buildings || buildings.length === 0}
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
          <Button onClick={() => setIsModalOpen(true)}>
            <Plus className="h-4 w-4 mr-2" />
            Novo Prédio
          </Button>
        </div>
      </div>

      {bulkOps.hasSelection && (
        <div className="mb-4 p-4 bg-blue-50 border border-blue-200 rounded flex justify-between items-center">
          <span className="text-blue-700 font-medium">
            {bulkOps.selectionCount} {bulkOps.selectionCount === 1 ? 'prédio selecionado' : 'prédios selecionados'}
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
        rowSelection={bulkOps.rowSelection}
      />

      <BuildingFormModal
        open={isModalOpen}
        building={editingBuilding}
        onClose={handleModalClose}
      />

      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Excluir prédio</AlertDialogTitle>
            <AlertDialogDescription>
              Tem certeza que deseja excluir este prédio? Esta ação não pode ser desfeita.
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
            <AlertDialogTitle>Excluir prédios selecionados</AlertDialogTitle>
            <AlertDialogDescription>
              Tem certeza que deseja excluir {bulkOps.selectionCount}{' '}
              {bulkOps.selectionCount === 1 ? 'prédio' : 'prédios'}? Esta ação não pode
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
