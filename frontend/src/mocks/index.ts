// Export all mock data
export { mockApartments } from './apartments';
export { mockBuildings } from './buildings';
export { mockDependents } from './dependents';
export { mockFurnitures } from './furnitures';
export { mockLeases } from './leases';
export { mockTenants } from './tenants';

// Re-export types for convenience
export type {
    Apartment, Building, Dependent, Furniture, Lease, Tenant
} from '../types';

import { mockApartments } from './apartments';
import { mockBuildings } from './buildings';
import { mockLeases } from './leases';
import { mockTenants } from './tenants';

// Helper functions for data analysis
export const mockDataUtils = {
  // Building statistics
  getTotalBuildings: () => mockBuildings.length,
  
  // Apartment statistics
  getTotalApartments: () => mockApartments.length,
  getOccupiedApartments: () => mockApartments.filter(apt => apt.is_rented).length,
  getVacantApartments: () => mockApartments.filter(apt => !apt.is_rented).length,
  getOccupancyRate: () => {
    const total = mockApartments.length;
    const occupied = mockApartments.filter(apt => apt.is_rented).length;
    return total > 0 ? (occupied / total) * 100 : 0;
  },
  getApartmentsByBuilding: (buildingId: number) => 
    mockApartments.filter(apt => apt.building.id === buildingId),
  
  // Tenant statistics
  getTotalTenants: () => mockTenants.length,
  getIndividualTenants: () => mockTenants.filter(tenant => !tenant.is_company).length,
  getCompanyTenants: () => mockTenants.filter(tenant => tenant.is_company).length,
  
  // Lease statistics
  getTotalLeases: () => mockLeases.length,
  getActiveLeases: () => mockLeases.filter(lease => lease.contract_signed).length,
  getPendingLeases: () => mockLeases.filter(lease => !lease.contract_signed).length,
  getMonthlyRevenue: () => 
    mockLeases
      .filter(lease => lease.contract_signed)
      .reduce((total, lease) => total + lease.rental_value, 0),
  
  // Contract statistics
  getContractsToSign: () => mockLeases.filter(lease => !lease.contract_signed).length,
  getContractsWithWarnings: () => mockLeases.filter(lease => lease.warning_count > 0).length,
  
  // Recent activities (mock data for timeline)
  getRecentActivities: () => [
    {
      id: 1,
      type: 'contract_signed' as const,
      description: 'Contrato assinado - Apto 402',
      date: '2024-06-01',
      tenant: 'Investimentos Imobiliários Ltda',
    },
    {
      id: 2,
      type: 'payment_received' as const,
      description: 'Pagamento recebido - Apto 204',
      date: '2024-06-15',
      tenant: 'Larissa Gomes Nunes',
    },
    {
      id: 3,
      type: 'maintenance_request' as const,
      description: 'Solicitação de manutenção - Apto 108',
      date: '2024-06-10',
      tenant: 'Roberto Oliveira Costa',
    },
    {
      id: 4,
      type: 'contract_renewal' as const,
      description: 'Renovação de contrato - Apto 115',
      date: '2024-05-20',
      tenant: 'Mariana Silva Campos',
    },
    {
      id: 5,
      type: 'new_tenant' as const,
      description: 'Novo inquilino cadastrado',
      date: '2024-05-15',
      tenant: 'Rafael Costa Barbosa',
    },
  ],
}; 