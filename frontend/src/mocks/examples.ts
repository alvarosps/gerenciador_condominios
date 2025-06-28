// Exemplos de como usar os dados mock nas páginas
// Este arquivo serve apenas como referência e pode ser deletado

import type {
    ActivityItem,
    BuildingStats,
    DashboardStats
} from '../types';
import {
    mockApartments,
    mockBuildings,
    mockDataUtils,
    mockLeases
} from './index';

// Exemplo 1: Como usar no Dashboard
export const getDashboardStats = (): DashboardStats => ({
  totalBuildings: mockDataUtils.getTotalBuildings(),
  totalApartments: mockDataUtils.getTotalApartments(),
  occupiedApartments: mockDataUtils.getOccupiedApartments(),
  vacantApartments: mockDataUtils.getVacantApartments(),
  occupancyRate: mockDataUtils.getOccupancyRate(),
  totalTenants: mockDataUtils.getTotalTenants(),
  individualTenants: mockDataUtils.getIndividualTenants(),
  companyTenants: mockDataUtils.getCompanyTenants(),
  totalLeases: mockDataUtils.getTotalLeases(),
  activeLeases: mockDataUtils.getActiveLeases(),
  pendingLeases: mockDataUtils.getPendingLeases(),
  monthlyRevenue: mockDataUtils.getMonthlyRevenue(),
  contractsToSign: mockDataUtils.getContractsToSign(),
  contractsWithWarnings: mockDataUtils.getContractsWithWarnings(),
});

// Exemplo 2: Como usar na página de Edifícios
export const getBuildingStats = (): BuildingStats[] => {
  return mockBuildings.map(building => {
    const buildingApartments = mockDataUtils.getApartmentsByBuilding(building.id);
    const occupiedApartments = buildingApartments.filter(apt => apt.is_rented);
    const monthlyRevenue = mockLeases
      .filter(lease => lease.contract_signed && lease.apartment.building.id === building.id)
      .reduce((total, lease) => total + lease.rental_value, 0);

    return {
      id: building.id,
      name: building.name,
      totalApartments: buildingApartments.length,
      occupiedApartments: occupiedApartments.length,
      vacantApartments: buildingApartments.length - occupiedApartments.length,
      occupancyRate: buildingApartments.length > 0 ? (occupiedApartments.length / buildingApartments.length) * 100 : 0,
      monthlyRevenue,
    };
  });
};

// Exemplo 3: Como usar nas atividades recentes
export const getRecentActivities = (): ActivityItem[] => {
  return mockDataUtils.getRecentActivities();
};

// Exemplo 4: Como filtrar apartamentos
export const getApartmentsByBuilding = (buildingId: number) => {
  return mockApartments.filter(apt => apt.building.id === buildingId);
};

// Exemplo 5: Como obter inquilinos em atraso (mock)
export const getTenantsInDefault = () => {
  // Simula inquilinos em atraso baseado em warning_count
  return mockLeases
    .filter(lease => lease.warning_count > 0)
    .map(lease => ({
      tenant: lease.responsible_tenant,
      apartment: lease.apartment,
      warningCount: lease.warning_count,
      daysInDefault: lease.warning_count * 30, // Simula dias em atraso
    }));
};

// Exemplo 6: Como usar em componentes React
/*
// No seu componente React:

import { getDashboardStats, getBuildingStats } from '../mocks/examples';

const Dashboard = () => {
  const stats = getDashboardStats();
  
  return (
    <div>
      <div>Total de Edifícios: {stats.totalBuildings}</div>
      <div>Taxa de Ocupação: {stats.occupancyRate.toFixed(1)}%</div>
      <div>Receita Mensal: R$ {stats.monthlyRevenue.toLocaleString('pt-BR')}</div>
    </div>
  );
};

const Buildings = () => {
  const buildingStats = getBuildingStats();
  
  return (
    <div>
      {buildingStats.map(building => (
        <div key={building.id}>
          <h3>{building.name}</h3>
          <p>Apartamentos: {building.totalApartments}</p>
          <p>Ocupação: {building.occupancyRate.toFixed(1)}%</p>
        </div>
      ))}
    </div>
  );
};
*/ 