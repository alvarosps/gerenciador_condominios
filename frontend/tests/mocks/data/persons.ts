import type { Person } from '@/lib/schemas/person.schema';

export const mockPersons: Person[] = [
  {
    id: 1,
    name: 'Rodrigo Souza',
    relationship: 'Filho',
    phone: '11999990001',
    email: 'rodrigo@example.com',
    is_owner: false,
    is_employee: false,
    user: null,
    notes: '',
    credit_cards: [
      {
        id: 1,
        nickname: 'Nubank Rodrigo',
        last_four_digits: '1234',
        closing_day: 3,
        due_day: 10,
        is_active: true,
      },
    ],
  },
  {
    id: 2,
    name: 'Rosa Silva',
    relationship: 'Funcionária',
    phone: '11999990002',
    email: '',
    is_owner: false,
    is_employee: true,
    user: null,
    notes: 'Funcionária de limpeza',
    credit_cards: [],
  },
  {
    id: 3,
    name: 'Alvaro Souza',
    relationship: 'Proprietário',
    phone: '11999990003',
    email: 'alvaro@example.com',
    is_owner: true,
    is_employee: false,
    user: 1,
    notes: '',
    credit_cards: [
      {
        id: 2,
        nickname: 'Itaú Alvaro',
        last_four_digits: '5678',
        closing_day: 8,
        due_day: 15,
        is_active: true,
      },
    ],
  },
];

export function createMockPerson(overrides: Partial<Person> = {}): Person {
  return {
    id: Math.floor(Math.random() * 1000) + 100,
    name: `Pessoa Test ${Math.floor(Math.random() * 100)}`,
    relationship: 'Outro',
    phone: '11999990000',
    email: 'test@example.com',
    is_owner: false,
    is_employee: false,
    user: null,
    notes: '',
    credit_cards: [],
    ...overrides,
  };
}
