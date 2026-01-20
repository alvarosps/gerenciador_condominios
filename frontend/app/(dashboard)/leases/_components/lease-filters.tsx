'use client';

import { useMemo } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { SearchableSelect, SearchableSelectOption } from '@/components/ui/searchable-select';
import { Apartment } from '@/lib/schemas/apartment.schema';
import { Tenant } from '@/lib/schemas/tenant.schema';

export interface LeaseFilters {
  apartment_id: number | undefined;
  responsible_tenant_id: number | undefined;
  is_active: boolean | undefined;
  is_expired: boolean | undefined;
  expiring_soon: boolean | undefined;
}

interface Props {
  filters: LeaseFilters;
  onFiltersChange: (filters: LeaseFilters) => void;
  apartments: Apartment[] | undefined;
  tenants: Tenant[] | undefined;
}

export function LeaseFiltersCard({ filters, onFiltersChange, apartments, tenants }: Props) {
  const hasActiveFilters = Object.values(filters).some((value) => value !== undefined);

  const apartmentOptions: SearchableSelectOption[] = useMemo(() => {
    const options: SearchableSelectOption[] = [{ value: 'all', label: 'Todos os apartamentos' }];
    apartments?.forEach((apt) => {
      options.push({
        value: String(apt.id),
        label: `${apt.building?.name} - Apto ${apt.number}`,
      });
    });
    return options;
  }, [apartments]);

  const tenantOptions: SearchableSelectOption[] = useMemo(() => {
    const options: SearchableSelectOption[] = [{ value: 'all', label: 'Todos os inquilinos' }];
    tenants?.forEach((t) => {
      options.push({
        value: String(t.id!),
        label: t.name,
      });
    });
    return options;
  }, [tenants]);

  const clearFilters = () => {
    onFiltersChange({
      apartment_id: undefined,
      responsible_tenant_id: undefined,
      is_active: undefined,
      is_expired: undefined,
      expiring_soon: undefined,
    });
  };

  const handleStatusChange = (value: string) => {
    if (value === 'active') {
      onFiltersChange({
        ...filters,
        is_active: true,
        is_expired: undefined,
        expiring_soon: undefined,
      });
    } else if (value === 'expired') {
      onFiltersChange({
        ...filters,
        is_active: undefined,
        is_expired: true,
        expiring_soon: undefined,
      });
    } else if (value === 'expiring') {
      onFiltersChange({
        ...filters,
        is_active: undefined,
        is_expired: undefined,
        expiring_soon: true,
      });
    } else if (value === 'all') {
      onFiltersChange({
        ...filters,
        is_active: undefined,
        is_expired: undefined,
        expiring_soon: undefined,
      });
    }
  };

  const getStatusValue = () => {
    if (filters.is_active !== undefined) return 'active';
    if (filters.is_expired !== undefined) return 'expired';
    if (filters.expiring_soon !== undefined) return 'expiring';
    return 'all';
  };

  return (
    <Card className="mb-4">
      <CardContent className="pt-6">
        <div className="flex gap-4 flex-wrap items-end">
          <div className="flex-1 min-w-[200px]">
            <label className="block text-sm font-medium mb-2">Apartamento</label>
            <SearchableSelect
              value={filters.apartment_id ? String(filters.apartment_id) : 'all'}
              onValueChange={(value) =>
                onFiltersChange({
                  ...filters,
                  apartment_id: value === 'all' ? undefined : Number(value),
                })
              }
              options={apartmentOptions}
              placeholder="Todos os apartamentos"
              searchPlaceholder="Buscar apartamento..."
            />
          </div>

          <div className="flex-1 min-w-[200px]">
            <label className="block text-sm font-medium mb-2">Inquilino</label>
            <SearchableSelect
              value={filters.responsible_tenant_id ? String(filters.responsible_tenant_id) : 'all'}
              onValueChange={(value) =>
                onFiltersChange({
                  ...filters,
                  responsible_tenant_id: value === 'all' ? undefined : Number(value),
                })
              }
              options={tenantOptions}
              placeholder="Todos os inquilinos"
              searchPlaceholder="Buscar inquilino..."
            />
          </div>

          <div className="flex-1 min-w-[150px]">
            <label className="block text-sm font-medium mb-2">Status</label>
            <Select value={getStatusValue()} onValueChange={handleStatusChange}>
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
            <Button variant="outline" onClick={clearFilters}>
              Limpar Filtros
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
