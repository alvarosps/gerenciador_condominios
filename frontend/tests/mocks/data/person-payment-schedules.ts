import type { PersonPaymentSchedule } from '@/lib/schemas/person-payment-schedule.schema';

export const mockPersonPaymentSchedules: PersonPaymentSchedule[] = [
  {
    id: 1,
    person: { id: 1, name: 'Rodrigo', relationship: 'Sócio', phone: '', email: '', is_owner: false, is_employee: false, notes: '' },
    person_id: 1,
    reference_month: '2026-03-01',
    due_day: 5,
    amount: 4000,
    created_at: '2026-03-01T00:00:00Z',
    updated_at: '2026-03-01T00:00:00Z',
  },
  {
    id: 2,
    person: { id: 1, name: 'Rodrigo', relationship: 'Sócio', phone: '', email: '', is_owner: false, is_employee: false, notes: '' },
    person_id: 1,
    reference_month: '2026-03-01',
    due_day: 27,
    amount: 5000,
    created_at: '2026-03-01T00:00:00Z',
    updated_at: '2026-03-01T00:00:00Z',
  },
];

let nextId = 100;

export function createMockPersonPaymentSchedule(
  overrides?: Partial<PersonPaymentSchedule>,
): PersonPaymentSchedule {
  return {
    id: nextId++,
    person: { id: 1, name: 'Rodrigo', relationship: 'Sócio', phone: '', email: '', is_owner: false, is_employee: false, notes: '' },
    person_id: 1,
    reference_month: '2026-03-01',
    due_day: 10,
    amount: 3000,
    created_at: '2026-03-01T00:00:00Z',
    updated_at: '2026-03-01T00:00:00Z',
    ...overrides,
  };
}
