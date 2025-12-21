'use client';

import { useState, useCallback, useEffect } from 'react';
import {
  Search,
  Building2,
  DoorOpen,
  Users,
  FileText,
  Package,
  Loader2,
} from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useDebounce } from '@/lib/hooks/use-debounce';
import { apiClient } from '@/lib/api/client';
import { formatCurrency } from '@/lib/utils/formatters';
import { formatCPFOrCNPJ, formatBrazilianPhone } from '@/lib/utils/validators';
import { Building } from '@/lib/schemas/building.schema';
import { Apartment } from '@/lib/schemas/apartment.schema';
import { Tenant } from '@/lib/schemas/tenant.schema';
import { Lease } from '@/lib/schemas/lease.schema';
import { Furniture } from '@/lib/schemas/furniture.schema';
import { Input } from '@/components/ui/input';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';

interface SearchResult {
  type: 'building' | 'apartment' | 'tenant' | 'lease' | 'furniture';
  id: number;
  title: string;
  subtitle?: string;
  metadata?: string;
  url: string;
}

export function GlobalSearch() {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [results, setResults] = useState<SearchResult[]>([]);
  const router = useRouter();

  const debouncedSearchTerm = useDebounce(searchTerm, 300);

  const performSearch = useCallback(async (term: string) => {
    if (!term || term.length < 2) {
      setResults([]);
      return;
    }

    setIsSearching(true);

    try {
      const [buildings, apartments, tenants, leases, furniture] = await Promise.all([
        apiClient.get('/buildings/', { params: { search: term } }),
        apiClient.get('/apartments/', { params: { search: term } }),
        apiClient.get('/tenants/', { params: { search: term } }),
        apiClient.get('/leases/', { params: { search: term } }),
        apiClient.get('/furnitures/', { params: { search: term } }),
      ]);

      const searchResults: SearchResult[] = [];

      // Buildings
      buildings.data.forEach((item: Building) => {
        if (item.id !== undefined) {
          searchResults.push({
            type: 'building',
            id: item.id,
            title: item.name,
            subtitle: `Número: ${item.street_number}`,
            metadata: item.address,
            url: '/dashboard/buildings',
          });
        }
      });

      // Apartments
      apartments.data.forEach((item: Apartment) => {
        if (item.id !== undefined) {
          searchResults.push({
            type: 'apartment',
            id: item.id,
            title: `Apartamento ${item.number}`,
            subtitle: item.building?.name || 'Sem prédio',
            metadata: `${formatCurrency(item.rental_value)} - ${item.is_rented ? 'Alugado' : 'Disponível'}`,
            url: '/dashboard/apartments',
          });
        }
      });

      // Tenants
      tenants.data.forEach((item: Tenant) => {
        if (item.id !== undefined) {
          searchResults.push({
            type: 'tenant',
            id: item.id,
            title: item.name,
            subtitle: formatCPFOrCNPJ(item.cpf_cnpj),
            metadata: `${formatBrazilianPhone(item.phone)} - ${item.profession}`,
            url: '/dashboard/tenants',
          });
        }
      });

      // Leases
      leases.data.forEach((item: Lease) => {
        if (item.id !== undefined) {
          searchResults.push({
            type: 'lease',
            id: item.id,
            title: `Locação - ${item.responsible_tenant?.name || 'Sem inquilino'}`,
            subtitle: `${item.apartment?.building?.name || ''} Apto ${item.apartment?.number || ''}`,
            metadata: `${formatCurrency(item.rental_value)} - Venc. dia ${item.due_day}`,
            url: '/dashboard/leases',
          });
        }
      });

      // Furniture
      furniture.data.forEach((item: Furniture) => {
        if (item.id !== undefined) {
          searchResults.push({
            type: 'furniture',
            id: item.id,
            title: item.name,
            subtitle: 'Móvel',
            metadata: item.description || '',
            url: '/dashboard/furniture',
          });
        }
      });

      setResults(searchResults);
    } catch (error) {
      console.error('Search error:', error);
      setResults([]);
    } finally {
      setIsSearching(false);
    }
  }, []);

  // Perform search when debounced term changes
  useEffect(() => {
    if (debouncedSearchTerm && isModalOpen) {
      performSearch(debouncedSearchTerm);
    } else if (!debouncedSearchTerm) {
      setResults([]);
    }
  }, [debouncedSearchTerm, isModalOpen, performSearch]);

  const handleResultClick = (result: SearchResult): void => {
    router.push(result.url);
    setIsModalOpen(false);
    setSearchTerm('');
    setResults([]);
  };

  const getIcon = (type: SearchResult['type']): React.ReactNode => {
    const iconClass = 'h-5 w-5';
    switch (type) {
      case 'building':
        return <Building2 className={cn(iconClass, 'text-blue-500')} />;
      case 'apartment':
        return <DoorOpen className={cn(iconClass, 'text-green-500')} />;
      case 'tenant':
        return <Users className={cn(iconClass, 'text-orange-500')} />;
      case 'lease':
        return <FileText className={cn(iconClass, 'text-purple-500')} />;
      case 'furniture':
        return <Package className={cn(iconClass, 'text-pink-500')} />;
    }
  };

  const getTypeLabel = (type: SearchResult['type']): string => {
    switch (type) {
      case 'building':
        return 'Prédio';
      case 'apartment':
        return 'Apartamento';
      case 'tenant':
        return 'Inquilino';
      case 'lease':
        return 'Locação';
      case 'furniture':
        return 'Móvel';
    }
  };

  const getBadgeVariant = (_type: SearchResult['type']): 'default' | 'secondary' | 'destructive' | 'outline' => {
    return 'secondary';
  };

  return (
    <>
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          placeholder="Buscar em todo o sistema..."
          onClick={() => setIsModalOpen(true)}
          className="pl-9 w-full md:w-80"
          readOnly
        />
      </div>

      <Dialog open={isModalOpen} onOpenChange={setIsModalOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Search className="h-5 w-5" />
              <span>Busca Global</span>
            </DialogTitle>
          </DialogHeader>

          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Digite para buscar em prédios, apartamentos, inquilinos, locações e móveis..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              autoFocus
              className="pl-9"
            />
          </div>

          <div className="mt-4 max-h-[500px] overflow-y-auto">
            {isSearching ? (
              <div className="flex flex-col items-center justify-center py-8 text-center">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
                <p className="mt-4 text-sm text-muted-foreground">Buscando...</p>
              </div>
            ) : results.length > 0 ? (
              <div className="space-y-1">
                {results.map((result) => (
                  <button
                    key={`${result.type}-${result.id}`}
                    onClick={() => handleResultClick(result)}
                    className="w-full text-left px-4 py-3 rounded-md hover:bg-muted transition-colors"
                  >
                    <div className="flex items-start gap-3">
                      <div className="mt-0.5">{getIcon(result.type)}</div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="font-medium truncate">{result.title}</span>
                          <Badge variant={getBadgeVariant(result.type)}>
                            {getTypeLabel(result.type)}
                          </Badge>
                        </div>
                        {result.subtitle && (
                          <div className="text-sm text-muted-foreground">{result.subtitle}</div>
                        )}
                        {result.metadata && (
                          <div className="text-xs text-muted-foreground mt-1">
                            {result.metadata}
                          </div>
                        )}
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            ) : searchTerm && !isSearching ? (
              <div className="flex flex-col items-center justify-center py-8 text-center">
                <Search className="h-12 w-12 text-muted-foreground/30" />
                <p className="mt-4 text-sm text-muted-foreground">
                  Nenhum resultado encontrado
                </p>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center py-8 text-center text-muted-foreground">
                <Search className="h-12 w-12 opacity-30" />
                <p className="mt-4">
                  Digite pelo menos 2 caracteres para buscar
                </p>
                <p className="text-sm mt-2">
                  Busque por nome, documento, endereço, ou qualquer informação
                </p>
              </div>
            )}
          </div>

          {results.length > 0 && (
            <div className="mt-4 pt-4 border-t text-sm text-muted-foreground">
              {results.length} resultado(s) encontrado(s)
            </div>
          )}
        </DialogContent>
      </Dialog>
    </>
  );
}
