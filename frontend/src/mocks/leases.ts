import { Lease } from '../types';
import { mockApartments } from './apartments';
import { mockTenants } from './tenants';

export const mockLeases: Lease[] = [
  {
    id: 1,
    apartment: mockApartments[0], // Apto 100 - Prédio 836
    responsible_tenant: mockTenants[0], // Carlos Santos Silva
    tenants: [mockTenants[0]],
    number_of_tenants: 1,
    start_date: '2024-01-15',
    validity_months: 12,
    due_day: 5,
    rental_value: 1800.00,
    cleaning_fee: 150.00,
    tag_fee: 50.00,
    contract_generated: true,
    contract_signed: true,
    interfone_configured: true,
    warning_count: 0,
  },
  {
    id: 2,
    apartment: mockApartments[1], // Apto 106 - Prédio 836
    responsible_tenant: mockTenants[1], // Ana Beatriz Mendes
    tenants: [mockTenants[1]],
    number_of_tenants: 1,
    start_date: '2024-02-01',
    validity_months: 12,
    due_day: 10,
    rental_value: 1900.00,
    cleaning_fee: 150.00,
    tag_fee: 50.00,
    contract_generated: true,
    contract_signed: true,
    interfone_configured: true,
    warning_count: 0,
  },
  {
    id: 3,
    apartment: mockApartments[2], // Apto 108 - Prédio 836
    responsible_tenant: mockTenants[2], // Roberto Oliveira Costa
    tenants: [mockTenants[2]],
    number_of_tenants: 1,
    start_date: '2024-03-10',
    validity_months: 12,
    due_day: 15,
    rental_value: 2000.00,
    cleaning_fee: 150.00,
    tag_fee: 50.00,
    contract_generated: true,
    contract_signed: true,
    interfone_configured: true,
    warning_count: 1,
  },
  {
    id: 4,
    apartment: mockApartments[5], // Apto 115 - Prédio 836
    responsible_tenant: mockTenants[5], // Mariana Silva Campos
    tenants: [mockTenants[5]],
    number_of_tenants: 1,
    start_date: '2024-04-20',
    validity_months: 18,
    due_day: 1,
    rental_value: 2100.00,
    cleaning_fee: 150.00,
    tag_fee: 50.00,
    contract_generated: true,
    contract_signed: true,
    interfone_configured: true,
    warning_count: 0,
  },
  {
    id: 5,
    apartment: mockApartments[6], // Apto 200 - Prédio 836
    responsible_tenant: mockTenants[6], // Eduardo Ferreira Alves
    tenants: [mockTenants[6]],
    number_of_tenants: 1,
    start_date: '2024-05-01',
    validity_months: 12,
    due_day: 8,
    rental_value: 1950.00,
    cleaning_fee: 150.00,
    tag_fee: 50.00,
    contract_generated: true,
    contract_signed: true,
    interfone_configured: true,
    warning_count: 0,
  },
  {
    id: 6,
    apartment: mockApartments[7], // Apto 204 - Prédio 836
    responsible_tenant: mockTenants[7], // Larissa Gomes Nunes
    tenants: [mockTenants[7]],
    number_of_tenants: 1,
    start_date: '2024-06-15',
    validity_months: 12,
    due_day: 12,
    rental_value: 1800.00,
    cleaning_fee: 150.00,
    tag_fee: 50.00,
    contract_generated: true,
    contract_signed: true,
    interfone_configured: true,
    warning_count: 0,
  },
  {
    id: 7,
    apartment: mockApartments[9], // Apto 213 - Prédio 836
    responsible_tenant: mockTenants[9], // Patricia Lima Santos
    tenants: [mockTenants[9]],
    number_of_tenants: 1,
    start_date: '2024-02-28',
    validity_months: 24,
    due_day: 22,
    rental_value: 2000.00,
    cleaning_fee: 150.00,
    tag_fee: 50.00,
    contract_generated: true,
    contract_signed: true,
    interfone_configured: true,
    warning_count: 0,
  },
  {
    id: 8,
    apartment: mockApartments[10], // Apto 100 - Prédio 850
    responsible_tenant: mockTenants[10], // TechSolutions Ltda
    tenants: [mockTenants[10]],
    number_of_tenants: 1,
    start_date: '2024-01-10',
    validity_months: 36,
    due_day: 5,
    rental_value: 2200.00,
    cleaning_fee: 180.00,
    tag_fee: 100.00,
    contract_generated: true,
    contract_signed: true,
    interfone_configured: true,
    warning_count: 0,
  },
  {
    id: 9,
    apartment: mockApartments[11], // Apto 202 - Prédio 850
    responsible_tenant: mockTenants[11], // Consultoria Empresarial S/A
    tenants: [mockTenants[11]],
    number_of_tenants: 1,
    start_date: '2024-03-05',
    validity_months: 24,
    due_day: 10,
    rental_value: 2100.00,
    cleaning_fee: 180.00,
    tag_fee: 100.00,
    contract_generated: true,
    contract_signed: true,
    interfone_configured: true,
    warning_count: 0,
  },
  {
    id: 10,
    apartment: mockApartments[13], // Apto 204 - Prédio 850
    responsible_tenant: mockTenants[3], // Julia Martins Rocha
    tenants: [mockTenants[3], mockTenants[4]], // Julia + Fernando (compartilhado)
    number_of_tenants: 2,
    start_date: '2024-04-12',
    validity_months: 12,
    due_day: 20,
    rental_value: 2250.00,
    cleaning_fee: 180.00,
    tag_fee: 100.00,
    contract_generated: true,
    contract_signed: true,
    interfone_configured: true,
    warning_count: 0,
  },
  {
    id: 11,
    apartment: mockApartments[15], // Apto 101 - Prédio 920
    responsible_tenant: mockTenants[12], // Rafael Costa Barbosa
    tenants: [mockTenants[12]],
    number_of_tenants: 1,
    start_date: '2024-05-20',
    validity_months: 12,
    due_day: 15,
    rental_value: 2500.00,
    cleaning_fee: 200.00,
    tag_fee: 150.00,
    contract_generated: true,
    contract_signed: true,
    interfone_configured: true,
    warning_count: 0,
  },
  {
    id: 12,
    apartment: mockApartments[17], // Apto 301 - Prédio 1024
    responsible_tenant: mockTenants[13], // Marina Andrade Silva
    tenants: [mockTenants[13]],
    number_of_tenants: 1,
    start_date: '2024-03-25',
    validity_months: 18,
    due_day: 20,
    rental_value: 2800.00,
    cleaning_fee: 250.00,
    tag_fee: 200.00,
    contract_generated: true,
    contract_signed: true,
    interfone_configured: true,
    warning_count: 0,
  },
  {
    id: 13,
    apartment: mockApartments[19], // Apto 402 - Prédio 1150
    responsible_tenant: mockTenants[14], // Investimentos Imobiliários Ltda
    tenants: [mockTenants[14]],
    number_of_tenants: 1,
    start_date: '2024-06-01',
    validity_months: 36,
    due_day: 1,
    rental_value: 3200.00,
    cleaning_fee: 300.00,
    tag_fee: 300.00,
    contract_generated: true,
    contract_signed: true,
    interfone_configured: true,
    warning_count: 0,
  },
  // Contratos em processo (não assinados ainda)
  {
    id: 14,
    apartment: mockApartments[4], // Apto 113 - Prédio 836
    responsible_tenant: mockTenants[8], // Gabriel Pereira Souza
    tenants: [mockTenants[8]],
    number_of_tenants: 1,
    start_date: '2024-07-01',
    validity_months: 12,
    due_day: 18,
    rental_value: 1750.00,
    cleaning_fee: 150.00,
    tag_fee: 50.00,
    contract_generated: true,
    contract_signed: false,
    interfone_configured: true,
    warning_count: 0,
  },
  {
    id: 15,
    apartment: mockApartments[14], // Apto 206 - Prédio 850
    responsible_tenant: mockTenants[4], // Fernando Rodrigues Lima
    tenants: [mockTenants[4]],
    number_of_tenants: 1,
    start_date: '2024-07-15',
    validity_months: 12,
    due_day: 25,
    rental_value: 1950.00,
    cleaning_fee: 180.00,
    tag_fee: 100.00,
    contract_generated: true,
    contract_signed: false,
    interfone_configured: true,
    warning_count: 0,
  },
]; 