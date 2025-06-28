import { Apartment } from '../types';
import { mockBuildings } from './buildings';
import { mockFurnitures } from './furnitures';

export const mockApartments: Apartment[] = [
  // Prédio 836 (id: 1)
  {
    id: 1,
    building: mockBuildings[0], // street_number: 836
    number: 100,
    interfone_configured: true,
    contract_generated: true,
    contract_signed: true,
    rental_value: 1800.00,
    cleaning_fee: 150.00,
    max_tenants: 2,
    is_rented: true,
    lease_date: '2024-01-15',
    last_rent_increase_date: '2024-01-15',
    furnitures: [mockFurnitures[0], mockFurnitures[1], mockFurnitures[2]], // Fogão, Geladeira, Máquina de Lavar
  },
  {
    id: 2,
    building: mockBuildings[0], // street_number: 836
    number: 106,
    interfone_configured: true,
    contract_generated: true,
    contract_signed: true,
    rental_value: 1900.00,
    cleaning_fee: 150.00,
    max_tenants: 3,
    is_rented: true,
    lease_date: '2024-02-01',
    last_rent_increase_date: '2024-02-01',
    furnitures: [mockFurnitures[0], mockFurnitures[1], mockFurnitures[3], mockFurnitures[4]], // Fogão, Geladeira, Micro-ondas, Sofá
  },
  {
    id: 3,
    building: mockBuildings[0], // street_number: 836
    number: 108,
    interfone_configured: true,
    contract_generated: true,
    contract_signed: true,
    rental_value: 2000.00,
    cleaning_fee: 150.00,
    max_tenants: 2,
    is_rented: true,
    lease_date: '2024-03-10',
    last_rent_increase_date: '2024-03-10',
    furnitures: [mockFurnitures[0], mockFurnitures[1], mockFurnitures[8]], // Fogão, Geladeira, TV
  },
  {
    id: 4,
    building: mockBuildings[0], // street_number: 836
    number: 112,
    interfone_configured: false,
    contract_generated: false,
    contract_signed: false,
    rental_value: 1850.00,
    cleaning_fee: 150.00,
    max_tenants: 2,
    is_rented: false,
    furnitures: [mockFurnitures[0], mockFurnitures[1]], // Fogão, Geladeira
  },
  {
    id: 5,
    building: mockBuildings[0], // street_number: 836
    number: 113,
    interfone_configured: true,
    contract_generated: true,
    contract_signed: false,
    rental_value: 1750.00,
    cleaning_fee: 150.00,
    max_tenants: 3,
    is_rented: false,
    furnitures: [mockFurnitures[0], mockFurnitures[1], mockFurnitures[4]], // Fogão, Geladeira, Sofá
  },
  {
    id: 6,
    building: mockBuildings[0], // street_number: 836
    number: 115,
    interfone_configured: true,
    contract_generated: true,
    contract_signed: true,
    rental_value: 2100.00,
    cleaning_fee: 150.00,
    max_tenants: 4,
    is_rented: true,
    lease_date: '2024-04-20',
    last_rent_increase_date: '2024-04-20',
    furnitures: [mockFurnitures[0], mockFurnitures[1], mockFurnitures[2], mockFurnitures[4], mockFurnitures[8]], // Completo
  },
  {
    id: 7,
    building: mockBuildings[0], // street_number: 836
    number: 200,
    interfone_configured: true,
    contract_generated: true,
    contract_signed: true,
    rental_value: 1950.00,
    cleaning_fee: 150.00,
    max_tenants: 2,
    is_rented: true,
    lease_date: '2024-05-01',
    last_rent_increase_date: '2024-05-01',
    furnitures: [mockFurnitures[0], mockFurnitures[1], mockFurnitures[3]], // Fogão, Geladeira, Micro-ondas
  },
  {
    id: 8,
    building: mockBuildings[0], // street_number: 836
    number: 204,
    interfone_configured: true,
    contract_generated: true,
    contract_signed: true,
    rental_value: 1800.00,
    cleaning_fee: 150.00,
    max_tenants: 2,
    is_rented: true,
    lease_date: '2024-06-15',
    last_rent_increase_date: '2024-06-15',
    furnitures: [mockFurnitures[0], mockFurnitures[1]], // Fogão, Geladeira
  },
  {
    id: 9,
    building: mockBuildings[0], // street_number: 836
    number: 208,
    interfone_configured: false,
    contract_generated: false,
    contract_signed: false,
    rental_value: 1850.00,
    cleaning_fee: 150.00,
    max_tenants: 3,
    is_rented: false,
    furnitures: [mockFurnitures[0], mockFurnitures[1], mockFurnitures[4]], // Fogão, Geladeira, Sofá
  },
  {
    id: 10,
    building: mockBuildings[0], // street_number: 836
    number: 213,
    interfone_configured: true,
    contract_generated: true,
    contract_signed: true,
    rental_value: 2000.00,
    cleaning_fee: 150.00,
    max_tenants: 2,
    is_rented: true,
    lease_date: '2024-02-28',
    last_rent_increase_date: '2024-02-28',
    furnitures: [mockFurnitures[0], mockFurnitures[1], mockFurnitures[8], mockFurnitures[9]], // Fogão, Geladeira, TV, Ar Condicionado
  },

  // Prédio 850 (id: 2)
  {
    id: 11,
    building: mockBuildings[1], // street_number: 850
    number: 100,
    interfone_configured: true,
    contract_generated: true,
    contract_signed: true,
    rental_value: 2200.00,
    cleaning_fee: 180.00,
    max_tenants: 3,
    is_rented: true,
    lease_date: '2024-01-10',
    last_rent_increase_date: '2024-01-10',
    furnitures: [mockFurnitures[0], mockFurnitures[1], mockFurnitures[2], mockFurnitures[4]], // Fogão, Geladeira, Máquina, Sofá
  },
  {
    id: 12,
    building: mockBuildings[1], // street_number: 850
    number: 202,
    interfone_configured: true,
    contract_generated: true,
    contract_signed: true,
    rental_value: 2100.00,
    cleaning_fee: 180.00,
    max_tenants: 2,
    is_rented: true,
    lease_date: '2024-03-05',
    last_rent_increase_date: '2024-03-05',
    furnitures: [mockFurnitures[0], mockFurnitures[1], mockFurnitures[3], mockFurnitures[8]], // Fogão, Geladeira, Micro-ondas, TV
  },
  {
    id: 13,
    building: mockBuildings[1], // street_number: 850
    number: 203,
    interfone_configured: false,
    contract_generated: false,
    contract_signed: false,
    rental_value: 2000.00,
    cleaning_fee: 180.00,
    max_tenants: 3,
    is_rented: false,
    furnitures: [mockFurnitures[0], mockFurnitures[1]], // Fogão, Geladeira
  },
  {
    id: 14,
    building: mockBuildings[1], // street_number: 850
    number: 204,
    interfone_configured: true,
    contract_generated: true,
    contract_signed: true,
    rental_value: 2250.00,
    cleaning_fee: 180.00,
    max_tenants: 4,
    is_rented: true,
    lease_date: '2024-04-12',
    last_rent_increase_date: '2024-04-12',
    furnitures: [mockFurnitures[0], mockFurnitures[1], mockFurnitures[2], mockFurnitures[4], mockFurnitures[8], mockFurnitures[9]], // Completo
  },
  {
    id: 15,
    building: mockBuildings[1], // street_number: 850
    number: 206,
    interfone_configured: true,
    contract_generated: true,
    contract_signed: false,
    rental_value: 1950.00,
    cleaning_fee: 180.00,
    max_tenants: 2,
    is_rented: false,
    furnitures: [mockFurnitures[0], mockFurnitures[1], mockFurnitures[4]], // Fogão, Geladeira, Sofá
  },

  // Prédio 920 (id: 3)
  {
    id: 16,
    building: mockBuildings[2], // street_number: 920
    number: 101,
    interfone_configured: true,
    contract_generated: true,
    contract_signed: true,
    rental_value: 2500.00,
    cleaning_fee: 200.00,
    max_tenants: 3,
    is_rented: true,
    lease_date: '2024-05-20',
    last_rent_increase_date: '2024-05-20',
    furnitures: [mockFurnitures[0], mockFurnitures[1], mockFurnitures[2], mockFurnitures[4], mockFurnitures[8]], // Mobiliado
  },
  {
    id: 17,
    building: mockBuildings[2], // street_number: 920
    number: 102,
    interfone_configured: false,
    contract_generated: false,
    contract_signed: false,
    rental_value: 2400.00,
    cleaning_fee: 200.00,
    max_tenants: 2,
    is_rented: false,
    furnitures: [mockFurnitures[0], mockFurnitures[1]], // Básico
  },

  // Prédio 1024 (id: 4)
  {
    id: 18,
    building: mockBuildings[3], // street_number: 1024
    number: 301,
    interfone_configured: true,
    contract_generated: true,
    contract_signed: true,
    rental_value: 2800.00,
    cleaning_fee: 250.00,
    max_tenants: 4,
    is_rented: true,
    lease_date: '2024-03-25',
    last_rent_increase_date: '2024-03-25',
    furnitures: [mockFurnitures[0], mockFurnitures[1], mockFurnitures[2], mockFurnitures[4], mockFurnitures[8], mockFurnitures[9], mockFurnitures[11]], // Completo
  },

  // Prédio 1150 (id: 5)
  {
    id: 19,
    building: mockBuildings[4], // street_number: 1150
    number: 401,
    interfone_configured: true,
    contract_generated: false,
    contract_signed: false,
    rental_value: 3000.00,
    cleaning_fee: 300.00,
    max_tenants: 5,
    is_rented: false,
    furnitures: [mockFurnitures[0], mockFurnitures[1], mockFurnitures[4]], // Básico
  },
  {
    id: 20,
    building: mockBuildings[4], // street_number: 1150
    number: 402,
    interfone_configured: true,
    contract_generated: true,
    contract_signed: true,
    rental_value: 3200.00,
    cleaning_fee: 300.00,
    max_tenants: 6,
    is_rented: true,
    lease_date: '2024-06-01',
    last_rent_increase_date: '2024-06-01',
    furnitures: mockFurnitures.slice(0, 8), // Bem mobiliado
  },
]; 