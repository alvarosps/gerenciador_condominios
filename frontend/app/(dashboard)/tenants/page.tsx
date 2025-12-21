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
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import {
  Plus,
  Pencil,
  Trash2,
  Download,
  FileSpreadsheet,
  FileText,
  Search,
  Users,
  User,
} from 'lucide-react';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';
import { DataTable, Column } from '@/components/tables/data-table';
import { TenantFormWizard } from './_components/tenant-form-wizard';
import {
  useTenants,
  useDeleteTenant,
} from '@/lib/api/hooks/use-tenants';
import { Tenant } from '@/lib/schemas/tenant.schema';
import { formatCPFOrCNPJ, formatBrazilianPhone } from '@/lib/utils/validators';
import { useExport, tenantExportColumns } from '@/lib/hooks/use-export';
import { useBulkOperations } from '@/lib/hooks/use-bulk-operations';

export default function TenantsPage() {
  const [isWizardOpen, setIsWizardOpen] = useState(false);
  const [editingTenant, setEditingTenant] = useState<Tenant | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleteId, setDeleteId] = useState<number | null>(null);
  const [bulkDeleteDialogOpen, setBulkDeleteDialogOpen] = useState(false);
  const [filters, setFilters] = useState({
    is_company: undefined as boolean | undefined,
    has_dependents: undefined as boolean | undefined,
    has_furniture: undefined as boolean | undefined,
    search: '' as string,
  });

  const { data: tenants, isLoading, error } = useTenants(filters);
  const deleteMutation = useDeleteTenant();
  const { exportToExcel, exportToCSV, isExporting } = useExport();
  const bulkOps = useBulkOperations({
    entityName: 'inquilino',
    entityNamePlural: 'inquilinos',
  });

  const handleEdit = (tenant: Tenant) => {
    setEditingTenant(tenant);
    setIsWizardOpen(true);
  };

  const handleDeleteClick = (id: number) => {
    setDeleteId(id);
    setDeleteDialogOpen(true);
  };

  const handleDelete = async () => {
    if (!deleteId) return;
    try {
      await deleteMutation.mutateAsync(deleteId);
      toast.success('Inquilino excluído com sucesso');
      setDeleteDialogOpen(false);
      setDeleteId(null);
    } catch (error) {
      toast.error('Erro ao excluir inquilino. Verifique se não há locações vinculadas.');
      console.error('Delete error:', error);
    }
  };

  const handleWizardClose = () => {
    setIsWizardOpen(false);
    setEditingTenant(null);
  };

  const clearFilters = () => {
    setFilters({
      is_company: undefined,
      has_dependents: undefined,
      has_furniture: undefined,
      search: '',
    });
  };

  const handleExport = async (format: 'excel' | 'csv') => {
    if (!tenants || tenants.length === 0) {
      toast.warning('Não há dados para exportar');
      return;
    }

    try {
      if (format === 'excel') {
        await exportToExcel(tenants, tenantExportColumns, {
          filename: 'inquilinos',
          sheetName: 'Inquilinos',
        });
        toast.success('Arquivo Excel exportado com sucesso!');
      } else {
        await exportToCSV(tenants, tenantExportColumns, {
          filename: 'inquilinos',
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

  const columns: Column<Tenant>[] = [
    {
      title: 'Nome / Razão Social',
      dataIndex: 'name',
      key: 'name',
      width: 250,
      sorter: (a: Tenant, b: Tenant) => a.name.localeCompare(b.name),
      render: (value, record: Tenant, _index) => (
        <div>
          <div className="font-medium">{value as string}</div>
          <div className="text-xs text-gray-500">
            {record.is_company ? 'Empresa' : 'Pessoa Física'}
          </div>
        </div>
      ),
    },
    {
      title: 'CPF / CNPJ',
      dataIndex: 'cpf_cnpj',
      key: 'cpf_cnpj',
      width: 180,
      render: (value) => (
        <span className="font-mono text-sm">{formatCPFOrCNPJ(value as string)}</span>
      ),
    },
    {
      title: 'Telefone',
      dataIndex: 'phone',
      key: 'phone',
      width: 150,
      render: (value) => formatBrazilianPhone(value as string),
    },
    {
      title: 'Email',
      dataIndex: 'email',
      key: 'email',
      width: 200,
    },
    {
      title: 'Profissão',
      dataIndex: 'profession',
      key: 'profession',
      width: 150,
    },
    {
      title: 'Estado Civil',
      dataIndex: 'marital_status',
      key: 'marital_status',
      width: 120,
      render: (value) => {
        const statusVariants: Record<string, string> = {
          'Solteiro': 'bg-blue-100 text-blue-800 hover:bg-blue-200',
          'Casado': 'bg-green-100 text-green-800 hover:bg-green-200',
          'Divorciado': 'bg-orange-100 text-orange-800 hover:bg-orange-200',
          'Viúvo': 'bg-gray-100 text-gray-800 hover:bg-gray-200',
        };
        return (
          <Badge className={cn(statusVariants[value as string] || 'bg-gray-100 text-gray-800')}>
            {value as string}
          </Badge>
        );
      },
    },
    {
      title: 'Dependentes',
      key: 'dependents',
      width: 120,
      align: 'center',
      render: (_, record: Tenant, _index) => {
        const count = record.dependents?.length || 0;
        return (
          <div className="flex items-center gap-2 justify-center">
            <Users className="h-5 w-5 text-muted-foreground" />
            <Badge
              variant={count > 0 ? 'default' : 'secondary'}
              className={cn(count > 0 ? 'bg-blue-500 hover:bg-blue-600' : '')}
            >
              {count}
            </Badge>
          </div>
        );
      },
      sorter: (a: Tenant, b: Tenant) => (a.dependents?.length || 0) - (b.dependents?.length || 0),
    },
    {
      title: 'Móveis',
      key: 'furnitures',
      width: 100,
      align: 'center',
      render: (_, record: Tenant, _index) => {
        const count = record.furnitures?.length || 0;
        return (
          <div className="flex items-center gap-2 justify-center">
            <User className="h-5 w-5 text-muted-foreground" />
            <Badge
              variant={count > 0 ? 'default' : 'secondary'}
              className={cn(count > 0 ? 'bg-green-500 hover:bg-green-600' : '')}
            >
              {count}
            </Badge>
          </div>
        );
      },
    },
    {
      title: 'Ações',
      key: 'actions',
      width: 150,
      fixed: 'right',
      render: (_, record: Tenant, _index) => (
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
    toast.error('Erro ao carregar inquilinos');
  }

  const hasActiveFilters =
    filters.is_company !== undefined ||
    filters.has_dependents !== undefined ||
    filters.has_furniture !== undefined ||
    filters.search !== '';

  return (
    <div>
      <div className="mb-4 flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold">Inquilinos</h1>
          <p className="text-gray-600 mt-1">
            Gerencie os inquilinos dos apartamentos
          </p>
        </div>
        <div className="flex gap-2">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="outline"
                disabled={isExporting || !tenants || tenants.length === 0}
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
          <Button onClick={() => setIsWizardOpen(true)}>
            <Plus className="h-4 w-4 mr-2" />
            Novo Inquilino
          </Button>
        </div>
      </div>

      {bulkOps.hasSelection && (
        <div className="mb-4 p-4 bg-blue-50 border border-blue-200 rounded flex justify-between items-center">
          <span className="text-blue-700 font-medium">
            {bulkOps.selectionCount} {bulkOps.selectionCount === 1 ? 'inquilino selecionado' : 'inquilinos selecionados'}
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

      {/* Filters */}
      <Card className="mb-4">
        <CardContent className="pt-6">
          <div className="flex gap-4 flex-wrap items-end">
            <div className="flex-1 min-w-[250px]">
              <label className="block text-sm font-medium mb-2">
                Buscar por Nome ou CPF/CNPJ
              </label>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Digite o nome ou documento..."
                  value={filters.search}
                  onChange={(e) => setFilters({ ...filters, search: e.target.value })}
                  className="pl-10"
                />
              </div>
            </div>

            <div className="flex-1 min-w-[150px]">
              <label className="block text-sm font-medium mb-2">Tipo</label>
              <Select
                value={filters.is_company === undefined ? '' : String(filters.is_company)}
                onValueChange={(value) =>
                  setFilters({
                    ...filters,
                    is_company: value === '' ? undefined : value === 'true',
                  })
                }
              >
                <SelectTrigger>
                  <SelectValue placeholder="Todos" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">Todos</SelectItem>
                  <SelectItem value="false">Pessoa Física</SelectItem>
                  <SelectItem value="true">Empresa</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="flex-1 min-w-[150px]">
              <label className="block text-sm font-medium mb-2">Dependentes</label>
              <Select
                value={filters.has_dependents === undefined ? '' : String(filters.has_dependents)}
                onValueChange={(value) =>
                  setFilters({
                    ...filters,
                    has_dependents: value === '' ? undefined : value === 'true',
                  })
                }
              >
                <SelectTrigger>
                  <SelectValue placeholder="Todos" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">Todos</SelectItem>
                  <SelectItem value="true">Com Dependentes</SelectItem>
                  <SelectItem value="false">Sem Dependentes</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="flex-1 min-w-[150px]">
              <label className="block text-sm font-medium mb-2">Móveis</label>
              <Select
                value={filters.has_furniture === undefined ? '' : String(filters.has_furniture)}
                onValueChange={(value) =>
                  setFilters({
                    ...filters,
                    has_furniture: value === '' ? undefined : value === 'true',
                  })
                }
              >
                <SelectTrigger>
                  <SelectValue placeholder="Todos" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">Todos</SelectItem>
                  <SelectItem value="true">Com Móveis</SelectItem>
                  <SelectItem value="false">Sem Móveis</SelectItem>
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

      <DataTable<Tenant>
        columns={columns}
        dataSource={tenants}
        loading={isLoading}
        rowKey="id"
        rowSelection={bulkOps.rowSelection}
      />

      <TenantFormWizard
        open={isWizardOpen}
        tenant={editingTenant}
        onClose={handleWizardClose}
      />

      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Excluir inquilino</AlertDialogTitle>
            <AlertDialogDescription>
              Tem certeza que deseja excluir este inquilino? Esta ação não pode ser desfeita.
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
            <AlertDialogTitle>Excluir inquilinos selecionados</AlertDialogTitle>
            <AlertDialogDescription>
              Tem certeza que deseja excluir {bulkOps.selectionCount}{' '}
              {bulkOps.selectionCount === 1 ? 'inquilino' : 'inquilinos'}? Esta ação não pode
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
