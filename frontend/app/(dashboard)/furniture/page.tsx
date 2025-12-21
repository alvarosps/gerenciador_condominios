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
import { FurnitureFormModal } from './_components/furniture-form-modal';
import {
  useFurniture,
  useDeleteFurniture,
} from '@/lib/api/hooks/use-furniture';
import { Furniture } from '@/lib/schemas/furniture.schema';
import { useExport, furnitureExportColumns } from '@/lib/hooks/use-export';
import { useBulkOperations } from '@/lib/hooks/use-bulk-operations';

export default function FurniturePage() {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingFurniture, setEditingFurniture] = useState<Furniture | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleteId, setDeleteId] = useState<number | null>(null);
  const [bulkDeleteDialogOpen, setBulkDeleteDialogOpen] = useState(false);

  const { data: furniture, isLoading, error } = useFurniture();
  const deleteMutation = useDeleteFurniture();
  const { exportToExcel, exportToCSV, isExporting } = useExport();
  const bulkOps = useBulkOperations({
    entityName: 'móvel',
    entityNamePlural: 'móveis',
  });

  const handleEdit = (item: Furniture) => {
    setEditingFurniture(item);
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
      toast.success('Móvel excluído com sucesso');
      setDeleteDialogOpen(false);
      setDeleteId(null);
    } catch (error) {
      toast.error('Erro ao excluir móvel. Verifique se não há apartamentos ou inquilinos vinculados.');
      console.error('Delete error:', error);
    }
  };

  const handleModalClose = () => {
    setIsModalOpen(false);
    setEditingFurniture(null);
  };

  const handleExport = async (format: 'excel' | 'csv') => {
    if (!furniture || furniture.length === 0) {
      toast.warning('Não há dados para exportar');
      return;
    }

    try {
      if (format === 'excel') {
        await exportToExcel(furniture, furnitureExportColumns, {
          filename: 'moveis',
          sheetName: 'Móveis',
        });
        toast.success('Arquivo Excel exportado com sucesso!');
      } else {
        await exportToCSV(furniture, furnitureExportColumns, {
          filename: 'moveis',
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

  const columns: Column<Furniture>[] = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 80,
      sorter: (a: Furniture, b: Furniture) => (a.id || 0) - (b.id || 0),
    },
    {
      title: 'Nome do Móvel',
      dataIndex: 'name',
      key: 'name',
      sorter: (a: Furniture, b: Furniture) => a.name.localeCompare(b.name),
    },
    {
      title: 'Ações',
      key: 'actions',
      width: 150,
      fixed: 'right',
      render: (_, record: Furniture, _index) => (
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
    toast.error('Erro ao carregar móveis');
  }

  return (
    <div>
      <div className="mb-4 flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold">Móveis</h1>
          <p className="text-gray-600 mt-1">
            Gerencie o catálogo de móveis disponíveis
          </p>
        </div>
        <div className="flex gap-2">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="outline"
                disabled={isExporting || !furniture || furniture.length === 0}
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
            Novo Móvel
          </Button>
        </div>
      </div>

      {bulkOps.hasSelection && (
        <div className="mb-4 p-4 bg-blue-50 border border-blue-200 rounded flex justify-between items-center">
          <span className="text-blue-700 font-medium">
            {bulkOps.selectionCount} {bulkOps.selectionCount === 1 ? 'móvel selecionado' : 'móveis selecionados'}
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

      <DataTable<Furniture>
        columns={columns}
        dataSource={furniture}
        loading={isLoading}
        rowKey="id"
        rowSelection={bulkOps.rowSelection}
      />

      <FurnitureFormModal
        open={isModalOpen}
        furniture={editingFurniture}
        onClose={handleModalClose}
      />

      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Excluir móvel</AlertDialogTitle>
            <AlertDialogDescription>
              Tem certeza que deseja excluir este móvel? Esta ação não pode ser desfeita.
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
            <AlertDialogTitle>Excluir móveis selecionados</AlertDialogTitle>
            <AlertDialogDescription>
              Tem certeza que deseja excluir {bulkOps.selectionCount}{' '}
              {bulkOps.selectionCount === 1 ? 'móvel' : 'móveis'}? Esta ação não pode
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
