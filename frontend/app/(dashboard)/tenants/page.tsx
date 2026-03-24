'use client';

import { useState, useMemo } from 'react';
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
  ArrowRightLeft,
  FilePlus,
} from 'lucide-react';
import { toast } from 'sonner';
import { DataTable, type Column } from '@/components/tables/data-table';
import { TenantFormWizard } from './_components/tenant-form-wizard';
import { TenantLeaseModal } from './_components/tenant-lease-modal';
import { ContractViewModal } from './_components/contract-view-modal';
import {
  useTenants,
  useDeleteTenant,
} from '@/lib/api/hooks/use-tenants';
import { useLeases, usePatchLease } from '@/lib/api/hooks/use-leases';
import { type Tenant } from '@/lib/schemas/tenant.schema';
import { type Lease } from '@/lib/schemas/lease.schema';
import { formatCPFOrCNPJ, formatBrazilianPhone } from '@/lib/utils/formatters';
import { tenantExportColumns } from '@/lib/hooks/use-export';
import { useCrudPage } from '@/lib/hooks/use-crud-page';

export default function TenantsPage() {
  // Page-specific filters state
  const [filters, setFilters] = useState({
    is_company: undefined as boolean | undefined,
    search: '' as string,
  });

  const { data: tenants, isLoading, error } = useTenants(filters);
  const { data: allLeases, isLoading: leasesLoading } = useLeases();
  const deleteMutation = useDeleteTenant();

  // Tenant-lease modal state
  const [tenantLeaseMode, setTenantLeaseMode] = useState<'create' | 'transfer' | null>(null);
  const [selectedTenant, setSelectedTenant] = useState<Tenant | null>(null);
  const [selectedLease, setSelectedLease] = useState<Lease | null>(null);

  const openTransferModal = (tenant: Tenant, lease: Lease) => {
    setSelectedTenant(tenant);
    setSelectedLease(lease);
    setTenantLeaseMode('transfer');
  };

  const openCreateLeaseModal = (tenant: Tenant) => {
    setSelectedTenant(tenant);
    setSelectedLease(null);
    setTenantLeaseMode('create');
  };

  const closeTenantLeaseModal = () => {
    setTenantLeaseMode(null);
    setSelectedTenant(null);
    setSelectedLease(null);
  };

  // Contract view modal state
  const [contractViewLease, setContractViewLease] = useState<Lease | null>(null);

  // Toggle confirmation modal state
  const [toggleConfirm, setToggleConfirm] = useState<{
    lease: Lease;
    field: 'contract_signed' | 'interfone_configured';
  } | null>(null);
  const patchLease = usePatchLease();

  const handleToggleConfirm = async () => {
    if (!toggleConfirm) return;
    const { lease, field } = toggleConfirm;
    const leaseId = lease.id;
    if (leaseId === undefined) return;
    try {
      await patchLease.mutateAsync({
        id: leaseId,
        [field]: !lease[field],
      });
      toast.success(
        field === 'contract_signed'
          ? (lease.contract_signed ? 'Assinatura revertida' : 'Contrato marcado como assinado')
          : (lease.interfone_configured ? 'Interfone desconfigurado' : 'Interfone marcado como configurado')
      );
    } catch {
      toast.error('Erro ao atualizar');
    }
    setToggleConfirm(null);
  };

  // Use the consolidated CRUD hook for all state management
  const crud = useCrudPage<Tenant>({
    entityName: 'inquilino',
    entityNamePlural: 'inquilinos',
    deleteMutation,
    exportColumns: tenantExportColumns,
    exportFilename: 'inquilinos',
    exportSheetName: 'Inquilinos',
    deleteErrorMessage: 'Erro ao excluir inquilino. Verifique se não há locações vinculadas.',
  });

  // Build tenant → lease map from all non-deleted leases
  const leaseByTenantId = useMemo(() => {
    const map = new Map<number, Lease>();
    allLeases?.forEach((lease) => {
      if (lease.responsible_tenant?.id !== undefined) {
        map.set(lease.responsible_tenant.id, lease);
      }
      lease.tenants?.forEach((tenant) => {
        if (tenant.id !== undefined && !map.has(tenant.id)) {
          map.set(tenant.id, lease);
        }
      });
    });
    return map;
  }, [allLeases]);

  const clearFilters = () => {
    setFilters({
      is_company: undefined,
      search: '',
    });
  };

  const columns: Column<Tenant>[] = [
    {
      title: 'Nome / Razão Social',
      dataIndex: 'name',
      key: 'name',
      width: 250,
      sorter: (a: Tenant, b: Tenant) => a.name.localeCompare(b.name),
      render: (value, record: Tenant) => (
        <div>
          <div className="font-medium">{value as string}</div>
          <div className="text-xs text-muted-foreground">
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
      title: 'Contrato Ativo',
      key: 'has_lease',
      width: 130,
      align: 'center' as const,
      sorter: (a: Tenant, b: Tenant) => {
        const aHas = a.id !== undefined && leaseByTenantId.has(a.id) ? 1 : 0;
        const bHas = b.id !== undefined && leaseByTenantId.has(b.id) ? 1 : 0;
        return aHas - bHas;
      },
      render: (_: unknown, record: Tenant) => {
        const lease = record.id !== undefined ? leaseByTenantId.get(record.id) : undefined;
        if (!lease) {
          return <Badge variant="secondary">Não</Badge>;
        }
        const aptNumber = lease.apartment?.number;
        const buildingNumber = lease.apartment?.building?.street_number;
        const location = aptNumber && buildingNumber ? ` ${String(aptNumber)}/${String(buildingNumber)}` : '';
        return (
          <Badge className="bg-success text-success-foreground">
            Sim{location}
          </Badge>
        );
      },
    },
    {
      title: 'Contrato Assinado',
      key: 'contract_signed',
      width: 140,
      align: 'center' as const,
      render: (_: unknown, record: Tenant) => {
        const lease = record.id !== undefined ? leaseByTenantId.get(record.id) : undefined;
        if (!lease) return <span className="text-muted-foreground">—</span>;
        return (
          <Badge
            className={`cursor-pointer ${
              lease.contract_signed
                ? 'bg-info/10 text-info hover:bg-info/20'
                : 'bg-warning/10 text-warning hover:bg-warning/20'
            }`}
            onClick={() => setToggleConfirm({ lease, field: 'contract_signed' })}
          >
            {lease.contract_signed ? 'Sim' : 'Não'}
          </Badge>
        );
      },
    },
    {
      title: 'Interfone',
      key: 'interfone',
      width: 130,
      align: 'center' as const,
      render: (_: unknown, record: Tenant) => {
        const lease = record.id !== undefined ? leaseByTenantId.get(record.id) : undefined;
        if (!lease) return <span className="text-muted-foreground">—</span>;
        return (
          <Badge
            className={`cursor-pointer ${
              lease.interfone_configured
                ? 'bg-success/10 text-success hover:bg-success/20'
                : 'bg-warning/10 text-warning hover:bg-warning/20'
            }`}
            onClick={() => setToggleConfirm({ lease, field: 'interfone_configured' })}
          >
            {lease.interfone_configured ? 'Configurado' : 'Pendente'}
          </Badge>
        );
      },
    },
    {
      title: 'Contrato',
      key: 'contract_action',
      width: 100,
      align: 'center' as const,
      render: (_: unknown, record: Tenant) => {
        const lease = record.id !== undefined ? leaseByTenantId.get(record.id) : undefined;
        if (!lease) return <span className="text-muted-foreground">—</span>;
        return (
          <Button
            variant="outline"
            size="sm"
            onClick={() => setContractViewLease(lease)}
          >
            Ver
          </Button>
        );
      },
    },
    {
      title: 'Ações',
      key: 'actions',
      width: 220,
      fixed: 'right',
      render: (_, record: Tenant) => {
        const lease = record.id !== undefined ? leaseByTenantId.get(record.id) : undefined;
        return (
          <div className="flex items-center gap-1">
            {lease ? (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => openTransferModal(record, lease)}
              >
                <ArrowRightLeft className="h-4 w-4 mr-1" />
                Trocar
              </Button>
            ) : (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => openCreateLeaseModal(record)}
              >
                <FilePlus className="h-4 w-4 mr-1" />
                Contrato
              </Button>
            )}
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
                if (record.id !== undefined) crud.handleDeleteClick(record.id);
              }}
              disabled={crud.isDeleting}
            >
              <Trash2 className="h-4 w-4 mr-1" />
              Excluir
            </Button>
          </div>
        );
      },
    },
  ];

  if (error) {
    toast.error('Erro ao carregar inquilinos');
  }

  const hasActiveFilters = filters.is_company !== undefined || filters.search !== '';

  return (
    <div>
      <div className="mb-4 flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold">Inquilinos</h1>
          <p className="text-muted-foreground mt-1">
            Gerencie os inquilinos dos apartamentos
          </p>
        </div>
        <div className="flex gap-2">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="outline"
                disabled={crud.isExporting || !tenants || tenants.length === 0}
              >
                <Download className="h-4 w-4 mr-2" />
                Exportar
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent>
              <DropdownMenuItem onClick={() => crud.handleExport('excel', tenants ?? [])}>
                <FileSpreadsheet className="h-4 w-4 mr-2" />
                Exportar para Excel
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => crud.handleExport('csv', tenants ?? [])}>
                <FileText className="h-4 w-4 mr-2" />
                Exportar para CSV
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
          <Button onClick={crud.openCreateModal}>
            <Plus className="h-4 w-4 mr-2" />
            Novo Inquilino
          </Button>
        </div>
      </div>

      {crud.bulkOps.hasSelection && (
        <div className="mb-4 p-4 bg-primary/5 border border-primary/20 rounded flex justify-between items-center">
          <span className="text-primary font-medium">
            {crud.bulkOps.selectionCount}{' '}
            {crud.bulkOps.selectionCount === 1 ? 'inquilino selecionado' : 'inquilinos selecionados'}
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

      {/* Filters */}
      <Card className="mb-4">
        <CardContent className="pt-6">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            <div>
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

            <div>
              <label className="block text-sm font-medium mb-2">Tipo</label>
              <Select
                value={filters.is_company === undefined ? 'all' : String(filters.is_company)}
                onValueChange={(value) =>
                  setFilters({
                    ...filters,
                    is_company: value === 'all' ? undefined : value === 'true',
                  })
                }
              >
                <SelectTrigger>
                  <SelectValue placeholder="Todos" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todos</SelectItem>
                  <SelectItem value="false">Pessoa Física</SelectItem>
                  <SelectItem value="true">Empresa</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {hasActiveFilters && (
              <div className="flex items-end">
                <Button variant="outline" onClick={clearFilters} className="w-full">
                  Limpar Filtros
                </Button>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      <DataTable<Tenant>
        columns={columns}
        dataSource={tenants}
        loading={isLoading || leasesLoading}
        rowKey="id"
        rowSelection={crud.bulkOps.rowSelection}
        pagination={{ pageSize: 50 }}
      />

      <TenantFormWizard
        open={crud.isModalOpen}
        tenant={crud.editingItem}
        onClose={crud.closeModal}
      />

      {tenantLeaseMode !== null && selectedTenant !== null && (
        <TenantLeaseModal
          mode={tenantLeaseMode}
          tenant={selectedTenant}
          currentLease={selectedLease}
          open={tenantLeaseMode !== null}
          onClose={closeTenantLeaseModal}
        />
      )}

      <ContractViewModal
        open={contractViewLease !== null}
        lease={contractViewLease}
        onClose={() => setContractViewLease(null)}
      />

      <AlertDialog open={toggleConfirm !== null} onOpenChange={() => setToggleConfirm(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              {toggleConfirm?.field === 'contract_signed'
                ? (toggleConfirm.lease.contract_signed ? 'Reverter assinatura' : 'Confirmar assinatura')
                : (toggleConfirm?.lease.interfone_configured ? 'Desconfigurar interfone' : 'Confirmar interfone')}
            </AlertDialogTitle>
            <AlertDialogDescription>
              {toggleConfirm?.field === 'contract_signed'
                ? (toggleConfirm.lease.contract_signed
                    ? 'Deseja reverter a assinatura do contrato?'
                    : 'O contrato foi assinado?')
                : (toggleConfirm?.lease.interfone_configured
                    ? 'Deseja desconfigurar o interfone?'
                    : 'O interfone foi cadastrado?')}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => void handleToggleConfirm()}
              disabled={patchLease.isPending}
            >
              {patchLease.isPending ? 'Salvando...' : 'Confirmar'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <AlertDialog open={crud.deleteDialogOpen} onOpenChange={crud.setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Excluir inquilino</AlertDialogTitle>
            <AlertDialogDescription>
              Tem certeza que deseja excluir{' '}
              {crud.itemToDelete?.name ? `"${crud.itemToDelete.name}"` : 'este inquilino'}? Esta
              ação não pode ser desfeita.
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
            <AlertDialogTitle>Excluir inquilinos selecionados</AlertDialogTitle>
            <AlertDialogDescription>
              Tem certeza que deseja excluir {crud.bulkOps.selectionCount}{' '}
              {crud.bulkOps.selectionCount === 1 ? 'inquilino' : 'inquilinos'}? Esta ação não pode
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
