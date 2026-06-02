import type { RentCalendar, RentCalendarItem } from '@/lib/api/hooks/use-rent-calendar';

export function createMockRentCalendarItem(
  overrides: Partial<RentCalendarItem> = {},
): RentCalendarItem {
  return {
    lease_id: 12,
    tenant_name: 'João Silva',
    apartment_number: 101,
    building_number: '836',
    rental_value: '1500.00',
    is_paid: false,
    payment_date: null,
    is_overdue: false,
    day_passed: false,
    can_toggle: true,
    late_fee: '0.00',
    late_days: 0,
    ...overrides,
  };
}

export function createMockRentCalendar(overrides: Partial<RentCalendar> = {}): RentCalendar {
  return {
    year: 2026,
    month: 6,
    today: '2026-06-02',
    next_due_date: '2026-06-05',
    days: [
      {
        day: 5,
        date: '2026-06-05',
        weekday: 'Sexta',
        items: [createMockRentCalendarItem()],
      },
    ],
    stats: {
      received_total: '4950.00',
      to_receive_total: '9650.00',
      expected_total: '14600.00',
      paid_count: 3,
      due_count: 9,
      overdue_count: 2,
      overdue_total_fee: '37.50',
      vacant_kitnets_count: 2,
      vacant_kitnets_value: '1600.00',
    },
    ...overrides,
  };
}
