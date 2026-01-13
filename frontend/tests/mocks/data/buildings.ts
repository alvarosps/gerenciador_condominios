import type { Building } from '@/lib/schemas/building.schema';

export const mockBuildings: Building[] = [
  {
    id: 1,
    street_number: 836,
    name: 'Edifício São Paulo',
    address: 'Rua das Flores, 836 - Centro, São Paulo - SP, 01310-100',
  },
  {
    id: 2,
    street_number: 850,
    name: 'Edifício Rio',
    address: 'Avenida Paulista, 850 - Bela Vista, São Paulo - SP, 01310-200',
  },
  {
    id: 3,
    street_number: 1200,
    name: 'Edifício Curitiba',
    address: 'Rua XV de Novembro, 1200 - Centro, Curitiba - PR, 80020-310',
  },
];

/**
 * Factory to create mock buildings with custom overrides
 */
export function createMockBuilding(overrides: Partial<Building> = {}): Building {
  return {
    id: Math.floor(Math.random() * 1000) + 100,
    street_number: Math.floor(Math.random() * 9000) + 1000,
    name: `Edifício Test ${Math.floor(Math.random() * 100)}`,
    address: 'Rua de Teste, 123 - Bairro Teste, São Paulo - SP, 01310-100',
    ...overrides,
  };
}
