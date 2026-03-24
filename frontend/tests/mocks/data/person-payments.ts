import type { PersonPayment } from '@/lib/schemas/person-payment.schema';

export const mockPersonPayments: PersonPayment[] = [
  {
    id: 1,
    person: { id: 1, name: 'Rodrigo Souza', relationship: 'Filho', phone: '', email: '', is_owner: false, is_employee: false, notes: '' },
    person_id: 1,
    reference_month: '2026-03-01',
    amount: 500,
    payment_date: '2026-03-01',
    notes: 'Pagamento parcial',
    created_at: '2026-03-01T10:00:00Z',
    updated_at: '2026-03-01T10:00:00Z',
  },
  {
    id: 2,
    person: { id: 3, name: 'Alvaro Souza', relationship: 'Proprietário', phone: '', email: '', is_owner: true, is_employee: false, notes: '' },
    person_id: 3,
    reference_month: '2026-03-01',
    amount: 1200,
    payment_date: '2026-03-05',
    notes: '',
    created_at: '2026-03-05T14:00:00Z',
    updated_at: '2026-03-05T14:00:00Z',
  },
];

export function createMockPersonPayment(overrides: Partial<PersonPayment> = {}): PersonPayment {
  return {
    id: Math.floor(Math.random() * 1000) + 100,
    person: { id: 1, name: 'Rodrigo Souza', relationship: 'Filho', phone: '', email: '', is_owner: false, is_employee: false, notes: '' },
    person_id: 1,
    reference_month: '2026-03-01',
    amount: 500,
    payment_date: '2026-03-01',
    notes: '',
    created_at: '2026-03-01T10:00:00Z',
    updated_at: '2026-03-01T10:00:00Z',
    ...overrides,
  };
}
