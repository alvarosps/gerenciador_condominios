'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Input } from '@/components/ui/input';
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
  Home,
  Download,
  FileSpreadsheet,
  FileText,
} from 'lucide-react';
import { toast } from 'sonner';
import { DataTable, Column } from '@/components/tables/data-table';
import { ApartmentFormModal } from './_components/apartment-form-modal';
import {
  useApartments,
  useDeleteApartment,
  useUpdateApartment,
} from '@/lib/api/hooks/use-apartments';
import { useBuildings } from '@/lib/api/hooks/use-buildings';
import { Apartment } from '@/lib/schemas/apartment.schema';
import { formatCurrency } from '@/lib/utils/formatters';
import { apartmentExportColumns } from '@/lib/hooks/use-export';
import { useCrudPage } from '@/lib/hooks/use-crud-page';

export default function ApartmentsPage() {
  // Page-specific filters state
  const [filters, setFilters] = useState({
    building_id: undefined as number | undefined,
    is_rented: undefined as boolean | undefined,
    min_price: undefined as number | undefined,
    max_price: undefined as number | undefined,
  });

  const { data: apartments, isLoading, error } = useApartments(filters);
  const { data: buildings } = useBuildings();
  const deleteMutation = useDeleteApartment();
  const updateMutation = useUpdateApartment();

  // Use the consolidated CRUD hook for all state management
  const crud = useCrudPage<Apartment>({
    entityName: 'apartamento',
    entityNamePlural: 'apartamentos',
    deleteMutation,
    exportColumns: apartmentExportColumns,
    exportFilename: 'apartamentos',
    exportSheetName: 'Apartamentos',
    deleteErrorMessage: 'Erro ao excluir apartamento. Verifique se não há locações vinculadas.',
  });

  const clearFilters = () => {
    setFilters({
      building_id: undefined,
      is_rented: undefined,
      min_price: undefined,
      max_price: undefined,
    });
  };

  const handleBulkStatusChange = (isRented: boolean) => {
    if (!apartments) return;
    crud.bulkOps.handleBulkStatusChange(
      apartments,
      async (data) => {
        await updateMutation.mutateAsync(data);
      },
      'is_rented',
      isRented
    );
  };

  const columns: Column<Apartment>[] = [
    {
      title: 'Prédio',
      key: 'building',
      width: 200,
      render: (_, record) => (
        <div>
          <div className="font-medium">{record.building?.name}</div>
          <div className="text-xs text-gray-500">Nº {record.building?.street_number}</div>
        </div>
      ),
      sorter: (a: Apartment, b: Apartment) => (a.building?.name || '').localeCompare(b.building?.name || ''),
    },
    {
      title: 'Apto',
      dataIndex: 'number',
      key: 'number',
      width: 80,
      sorter: (a: Apartment, b: Apartment) => a.number - b.number,
    },
    {
      title: 'Valor',
      dataIndex: 'rental_value',
      key: 'rental_value',
      width: 130,
      render: (value) => formatCurrency(value as number),
      sorter: (a: Apartment, b: Apartment) => a.rental_value - b.rental_value,
    },
    {
      title: 'Taxa Limpeza',
      dataIndex: 'cleaning_fee',
      key: 'cleaning_fee',
      width: 130,
      render: (value) => formatCurrency(value as number),
    },
    {
      title: 'Status',
      dataIndex: 'is_rented',
      key: 'is_rented',
      width: 120,
      render: (value) => (
        <Badge variant={value ? 'destructive' : 'default'} className={value ? '' : 'bg-green-600'}>
          {value ? 'Alugado' : 'Disponível'}
        </Badge>
      ),
      filters: [
        { text: 'Disponível', value: false },
        { text: 'Alugado', value: true },
      ],
      onFilter: (value, record) => record.is_rented === value,
    },
    {
      title: 'Inquilinos',
      dataIndex: 'max_tenants',
      key: 'max_tenants',
      width: 100,
      render: (value) => `Máx ${value}`,
    },
    {
      title: 'Móveis',
      key: 'furnitures',
      width: 100,
      render: (_, record) => (
        <div className="flex items-center gap-1">
          <Home className="h-4 w-4" />
          <span>{record.furnitures?.length || 0}</span>
        </div>
      ),
    },
    {
      title: 'Ações',
      key: 'actions',
      width: 150,
      fixed: 'right',
      render: (_, record: Apartment) => (
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
    toast.error('Erro ao carregar apartamentos');
  }

  const hasActiveFilters = Object.values(filters).some((value) => value !== undefined);

  return (
    <div>
      <div className="mb-4 flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold">Apartamentos</h1>
          <p className="text-gray-600 mt-1">
            Gerencie os apartamentos disponíveis para locação
          </p>
        </div>
        <div className="flex gap-2">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="outline"
                disabled={crud.isExporting || !apartments || apartments.length === 0}
              >
                <Download className="h-4 w-4 mr-2" />
                Exportar
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent>
              <DropdownMenuItem onClick={() => crud.handleExport('excel', apartments || [])}>
                <FileSpreadsheet className="h-4 w-4 mr-2" />
                Exportar para Excel
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => crud.handleExport('csv', apartments || [])}>
                <FileText className="h-4 w-4 mr-2" />
                Exportar para CSV
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
          <Button onClick={crud.openCreateModal}>
            <Plus className="h-4 w-4 mr-2" />
            Novo Apartamento
          </Button>
        </div>
      </div>

      {crud.bulkOps.hasSelection && (
        <div className="mb-4 p-4 bg-blue-50 border border-blue-200 rounded flex justify-between items-center">
          <span className="text-blue-700 font-medium">
            {crud.bulkOps.selectionCount} {crud.bulkOps.selectionCount === 1 ? 'apartamento selecionado' : 'apartamentos selecionados'}
          </span>
          <div className="flex gap-2">
            <Button variant="outline" onClick={crud.bulkOps.clearSelection}>
              Cancelar Seleção
            </Button>
            <Button
              variant="outline"
              onClick={() => handleBulkStatusChange(false)}
              disabled={updateMutation.isPending}
            >
              Marcar como Disponível
            </Button>
            <Button
              variant="outline"
              onClick={() => handleBulkStatusChange(true)}
              disabled={updateMutation.isPending}
            >
              Marcar como Alugado
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

      {/* Filters */}
      <Card className="mb-4 p-4">
        <div className="flex gap-4 flex-wrap items-end">
          <div className="flex-1 min-w-[200px]">
            <label className="block text-sm font-medium mb-2">Prédio</label>
            <Select
              value={filters.building_id ? String(filters.building_id) : undefined}
              onValueChange={(value) =>
                setFilters({ ...filters, building_id: value ? Number(value) : undefined })
              }
            >
              <SelectTrigger>
                <SelectValue placeholder="Todos os prédios" />
              </SelectTrigger>
              <SelectContent>
                {buildings?.map((b) => (
                  <SelectItem key={b.id} value={String(b.id)}>
                    {b.name} - {b.street_number}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="flex-1 min-w-[150px]">
            <label className="block text-sm font-medium mb-2">Status</label>
            <Select
              value={filters.is_rented !== undefined ? String(filters.is_rented) : undefined}
              onValueChange={(value) =>
                setFilters({
                  ...filters,
                  is_rented: value ? value === 'true' : undefined,
                })
              }
            >
              <SelectTrigger>
                <SelectValue placeholder="Todos" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="false">Disponível</SelectItem>
                <SelectItem value="true">Alugado</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="flex-1 min-w-[150px]">
            <label className="block text-sm font-medium mb-2">Valor Mínimo</label>
            <Input
              type="number"
              placeholder="R$ 0"
              value={filters.min_price || ''}
              onChange={(e) =>
                setFilters({
                  ...filters,
                  min_price: e.target.value ? Number(e.target.value) : undefined,
                })
              }
              min={0}
            />
          </div>

          <div className="flex-1 min-w-[150px]">
            <label className="block text-sm font-medium mb-2">Valor Máximo</label>
            <Input
              type="number"
              placeholder="R$ 99999"
              value={filters.max_price || ''}
              onChange={(e) =>
                setFilters({
                  ...filters,
                  max_price: e.target.value ? Number(e.target.value) : undefined,
                })
              }
              min={0}
            />
          </div>

          {hasActiveFilters && (
            <Button variant="outline" onClick={clearFilters}>
              Limpar Filtros
            </Button>
          )}
        </div>
      </Card>

      <DataTable<Apartment>
        columns={columns}
        dataSource={apartments}
        loading={isLoading}
        rowKey="id"
        rowSelection={crud.bulkOps.rowSelection}
      />

      <ApartmentFormModal
        open={crud.isModalOpen}
        apartment={crud.editingItem}
        onClose={crud.closeModal}
      />

      <AlertDialog open={crud.deleteDialogOpen} onOpenChange={crud.setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Excluir apartamento</AlertDialogTitle>
            <AlertDialogDescription>
              Tem certeza que deseja excluir o apartamento {crud.itemToDelete?.number ? `nº ${crud.itemToDelete.number}` : ''}? Esta ação não pode ser desfeita.
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
            <AlertDialogTitle>Excluir apartamentos selecionados</AlertDialogTitle>
            <AlertDialogDescription>
              Tem certeza que deseja excluir {crud.bulkOps.selectionCount}{' '}
              {crud.bulkOps.selectionCount === 1 ? 'apartamento' : 'apartamentos'}? Esta ação não pode
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
