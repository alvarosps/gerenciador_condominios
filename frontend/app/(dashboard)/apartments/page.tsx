'use client';

import { useState, useMemo, useEffect } from 'react';
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
import { DataTable, type Column } from '@/components/tables/data-table';
import { ApartmentFormModal } from './_components/apartment-form-modal';
import { useApartments, useDeleteApartment } from '@/lib/api/hooks/use-apartments';
import { useBuildings } from '@/lib/api/hooks/use-buildings';
import { type Apartment } from '@/lib/schemas/apartment.schema';
import { format, parseISO } from 'date-fns';
import { formatCurrency } from '@/lib/utils/formatters';
import { apartmentExportColumns } from '@/lib/hooks/use-export';
import { useCrudPage } from '@/lib/hooks/use-crud-page';

interface ApartmentFilters {
  is_rented?: boolean;
  min_price?: number;
  max_price?: number;
}

export default function ApartmentsPage() {
  const [filtersByBuilding, setFiltersByBuilding] = useState<Record<number, ApartmentFilters>>({});

  const { data: apartments, isLoading, error } = useApartments({});
  const { data: buildings } = useBuildings();
  const deleteMutation = useDeleteApartment();

  const crud = useCrudPage<Apartment>({
    entityName: 'apartamento',
    entityNamePlural: 'apartamentos',
    deleteMutation,
    exportColumns: apartmentExportColumns,
    exportFilename: 'apartamentos',
    exportSheetName: 'Apartamentos',
    deleteErrorMessage: 'Erro ao excluir apartamento. Verifique se não há locações vinculadas.',
  });

  const groupedApartments = useMemo(() => {
    const map = new Map<number, Apartment[]>();
    apartments?.forEach((apt) => {
      const buildingId = apt.building?.id;
      if (buildingId === undefined) return;
      const existing = map.get(buildingId) ?? [];
      existing.push(apt);
      map.set(buildingId, existing);
    });
    return map;
  }, [apartments]);

  const getFilters = (buildingId: number): ApartmentFilters =>
    filtersByBuilding[buildingId] ?? {};

  const updateFilter = (buildingId: number, updates: Partial<ApartmentFilters>): void => {
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

  const getFilteredApartments = (buildingId: number, apts: Apartment[]): Apartment[] => {
    const filters = getFilters(buildingId);
    return apts.filter((apt) => {
      if (filters.is_rented !== undefined && apt.is_rented !== filters.is_rented) return false;
      if (filters.min_price !== undefined && apt.rental_value < filters.min_price) return false;
      if (filters.max_price !== undefined && apt.rental_value > filters.max_price) return false;
      return true;
    });
  };

  const columns: Column<Apartment>[] = [
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
      width: 160,
      render: (_, record: Apartment) => {
        const pending = record.active_lease?.pending_rental_value;
        const pendingDate = record.active_lease?.pending_rental_value_date;

        if (pending && pendingDate) {
          return (
            <div className="space-y-0.5">
              <div>{formatCurrency(record.rental_value)}</div>
              <div className="text-xs text-success font-medium">
                → {formatCurrency(pending)} em {format(parseISO(pendingDate), 'dd/MM')}
              </div>
            </div>
          );
        }
        return formatCurrency(record.rental_value);
      },
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
        <Badge
          variant={value ? 'destructive' : 'default'}
          className={value ? '' : 'bg-success text-success-foreground'}
        >
          {value ? 'Alugado' : 'Disponível'}
        </Badge>
      ),
      sorter: (a: Apartment, b: Apartment) => Number(a.is_rented) - Number(b.is_rented),
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
      render: (value) => `Máx ${String(value)}`,
    },
    {
      title: 'Móveis',
      key: 'furnitures',
      width: 100,
      render: (_, record) => (
        <div className="flex items-center gap-1">
          <Home className="h-4 w-4" />
          <span>{record.furnitures?.length ?? 0}</span>
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
          <Button variant="ghost" size="sm" onClick={() => crud.openEditModal(record)}>
            <Pencil className="h-4 w-4 mr-1" />
            Editar
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              crud.setItemToDelete(record);
              if (record.id !== undefined) crud.handleDeleteClick(record.id);
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

  useEffect(() => {
    if (error) {
      toast.error('Erro ao carregar apartamentos');
    }
  }, [error]);

  return (
    <div>
      <div className="mb-4 flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold">Apartamentos</h1>
          <p className="text-muted-foreground mt-1">
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
              <DropdownMenuItem onClick={() => crud.handleExport('excel', apartments ?? [])}>
                <FileSpreadsheet className="h-4 w-4 mr-2" />
                Exportar para Excel
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => crud.handleExport('csv', apartments ?? [])}>
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
        <div className="mb-4 p-4 bg-primary/5 border border-primary/20 rounded flex justify-between items-center">
          <span className="text-primary font-medium">
            {crud.bulkOps.selectionCount}{' '}
            {crud.bulkOps.selectionCount === 1 ? 'apartamento selecionado' : 'apartamentos selecionados'}
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

      {isLoading ? (
        <div className="flex items-center justify-center p-12 border rounded-md">
          <div className="flex flex-col items-center gap-2">
            <div className="h-8 w-8 border-4 border-primary border-t-transparent rounded-full animate-spin" />
            <p className="text-sm text-muted-foreground">Carregando apartamentos...</p>
          </div>
        </div>
      ) : (
      <Accordion type="multiple" className="space-y-4">
        {buildings?.map((building) => {
          const buildingId = building.id;
          if (buildingId === undefined) return null;
          const apts = groupedApartments.get(buildingId) ?? [];
          const filteredApts = getFilteredApartments(buildingId, apts);
          const filters = getFilters(buildingId);
          const hasActiveFilters =
            filters.is_rented !== undefined ||
            filters.min_price !== undefined ||
            filters.max_price !== undefined;

          return (
            <AccordionItem key={buildingId} value={String(buildingId)}>
              <AccordionTrigger className="px-4">
                <div className="flex items-center gap-2">
                  <span>
                    {building.name} — Nº {building.street_number}
                  </span>
                  <Badge variant="secondary">{apts.length} apartamentos</Badge>
                </div>
              </AccordionTrigger>
              <AccordionContent className="px-4 pb-4">
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
                  <div>
                    <label className="block text-sm font-medium mb-2">Status</label>
                    <Select
                      value={
                        filters.is_rented !== undefined ? String(filters.is_rented) : undefined
                      }
                      onValueChange={(value) =>
                        updateFilter(buildingId, {
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

                  <div>
                    <label className="block text-sm font-medium mb-2">Valor Mínimo</label>
                    <Input
                      type="number"
                      placeholder="R$ 0"
                      value={filters.min_price ?? ''}
                      onChange={(e) =>
                        updateFilter(buildingId, {
                          min_price: e.target.value ? Number(e.target.value) : undefined,
                        })
                      }
                      min={0}
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-2">Valor Máximo</label>
                    <Input
                      type="number"
                      placeholder="R$ 99999"
                      value={filters.max_price ?? ''}
                      onChange={(e) =>
                        updateFilter(buildingId, {
                          max_price: e.target.value ? Number(e.target.value) : undefined,
                        })
                      }
                      min={0}
                    />
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

                <DataTable<Apartment>
                  columns={columns}
                  dataSource={filteredApts}
                  loading={isLoading}
                  rowKey="id"
                  rowSelection={crud.bulkOps.rowSelection}
                  defaultSortKey="number"
                  defaultSortDirection="asc"
                  pagination={{ pageSize: 40 }}
                />
              </AccordionContent>
            </AccordionItem>
          );
        })}
      </Accordion>
      )}

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
              Tem certeza que deseja excluir o apartamento{' '}
              {crud.itemToDelete?.number ? `nº ${crud.itemToDelete.number}` : ''}? Esta ação não
              pode ser desfeita.
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
              {crud.bulkOps.selectionCount === 1 ? 'apartamento' : 'apartamentos'}? Esta ação não
              pode ser desfeita.
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
