import type { Furniture } from '@/lib/schemas/furniture.schema';

export const mockFurniture: Furniture[] = [
  {
    id: 1,
    name: 'Sofá 3 lugares',
    description: 'Sofá de couro marrom',
  },
  {
    id: 2,
    name: 'Mesa de jantar',
    description: 'Mesa de madeira para 6 pessoas',
  },
  {
    id: 3,
    name: 'Cama de casal',
    description: 'Cama box com colchão',
  },
  {
    id: 4,
    name: 'Geladeira',
    description: 'Geladeira frost-free duplex',
  },
  {
    id: 5,
    name: 'Fogão',
    description: 'Fogão 4 bocas com forno',
  },
  {
    id: 6,
    name: 'Máquina de lavar',
    description: 'Máquina de lavar 11kg',
  },
];

/**
 * Factory to create mock furniture with custom overrides
 */
export function createMockFurniture(overrides: Partial<Furniture> = {}): Furniture {
  return {
    id: Math.floor(Math.random() * 1000) + 100,
    name: `Móvel Test ${Math.floor(Math.random() * 100)}`,
    description: 'Descrição do móvel de teste',
    ...overrides,
  };
}
