import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api/client";
import type { Apartment, Building, LeaseSimple, TenantSearchResult } from "@/lib/schemas/admin";

interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export function useBuildings() {
  return useQuery<Building[]>({
    queryKey: ["admin", "buildings"],
    queryFn: async () => {
      const response = await apiClient.get<PaginatedResponse<Building>>("/buildings/");
      return response.data.results;
    },
  });
}

export function useApartments(buildingId?: number) {
  return useQuery<Apartment[]>({
    queryKey: ["admin", "apartments", buildingId],
    queryFn: async () => {
      const params = buildingId !== undefined ? { building_id: buildingId } : {};
      const response = await apiClient.get<PaginatedResponse<Apartment>>("/apartments/", {
        params,
      });
      return response.data.results;
    },
  });
}

interface LeaseFilters {
  building_id?: number;
  is_active?: boolean;
}

export function useLeases(filters?: LeaseFilters) {
  return useQuery<LeaseSimple[]>({
    queryKey: ["admin", "leases", filters],
    queryFn: async () => {
      const response = await apiClient.get<PaginatedResponse<LeaseSimple>>("/leases/", {
        params: filters,
      });
      return response.data.results;
    },
  });
}

export function useTenantSearch(query: string) {
  return useQuery<TenantSearchResult[]>({
    queryKey: ["admin", "tenants", "search", query],
    queryFn: async () => {
      const response = await apiClient.get<PaginatedResponse<TenantSearchResult>>("/tenants/", {
        params: { search: query },
      });
      return response.data.results;
    },
    enabled: query.length >= 2,
  });
}

interface CreateLeaseInput {
  apartment: number;
  responsible_tenant_id: number;
  start_date: string;
  validity_months: number;
  rental_value: string;
  number_of_tenants: number;
}

export function useCreateLease() {
  const qc = useQueryClient();
  return useMutation<LeaseSimple, Error, CreateLeaseInput>({
    mutationFn: async (input) => {
      const response = await apiClient.post<LeaseSimple>("/leases/", input);
      return response.data;
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["admin", "leases"] });
      void qc.invalidateQueries({ queryKey: ["admin", "apartments"] });
    },
  });
}

interface GenerateContractResponse {
  contract_url: string;
}

export function useGenerateContract() {
  const qc = useQueryClient();
  return useMutation<GenerateContractResponse, Error, number>({
    mutationFn: async (leaseId) => {
      const response = await apiClient.post<GenerateContractResponse>(
        `/leases/${leaseId}/generate_contract/`,
      );
      return response.data;
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["admin", "leases"] });
    },
  });
}
