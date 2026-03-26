import type { Apartment } from '@/lib/schemas/apartment.schema';
import { mockBuildings } from './buildings';
import { mockFurniture } from './furniture';

export const mockApartments: Apartment[] = [
  {
    id: 1,
    number: 101,
    building_id: 1,
    building: mockBuildings[0]!,
    rental_value: 1500,
    rental_value_double: null,
    cleaning_fee: 200,
    max_tenants: 3,
    is_rented: false,
    last_rent_increase_date: null,
    furnitures: [mockFurniture[0]!, mockFurniture[1]!],
  },
  {
    id: 2,
    number: 102,
    building_id: 1,
    building: mockBuildings[0]!,
    rental_value: 1800,
    rental_value_double: null,
    cleaning_fee: 250,
    max_tenants: 4,
    is_rented: true,
    last_rent_increase_date: '2024-07-15',
    active_lease: {
      id: 1,
      contract_generated: true,
      contract_signed: true,
      interfone_configured: true,
      start_date: '2024-01-15',
      validity_months: 12,
      responsible_tenant: { id: 1, name: 'João Silva' },
    },
    furnitures: [mockFurniture[2]!, mockFurniture[3]!, mockFurniture[4]!],
  },
  {
    id: 3,
    number: 201,
    building_id: 2,
    building: mockBuildings[1]!,
    rental_value: 1200,
    rental_value_double: null,
    cleaning_fee: 150,
    max_tenants: 2,
    is_rented: false,
    last_rent_increase_date: null,
    furnitures: [],
  },
  {
    id: 4,
    number: 202,
    building_id: 2,
    building: mockBuildings[1]!,
    rental_value: 2500,
    rental_value_double: null,
    cleaning_fee: 300,
    max_tenants: 5,
    is_rented: true,
    last_rent_increase_date: null,
    active_lease: {
      id: 2,
      contract_generated: true,
      contract_signed: false,
      interfone_configured: true,
      start_date: '2024-03-01',
      validity_months: 12,
      responsible_tenant: { id: 2, name: 'Maria Santos' },
    },
    furnitures: mockFurniture,
  },
];

/**
 * Factory to create mock apartment with custom overrides
 */
export function createMockApartment(overrides: Partial<Apartment> = {}): Apartment {
  const building = mockBuildings[0]!;
  return {
    id: Math.floor(Math.random() * 1000) + 100,
    number: Math.floor(Math.random() * 900) + 100,
    building_id: building.id!,
    building,
    rental_value: 1500,
    rental_value_double: null,
    cleaning_fee: 200,
    max_tenants: 3,
    is_rented: false,
    last_rent_increase_date: null,
    furnitures: [],
    ...overrides,
  };
}
