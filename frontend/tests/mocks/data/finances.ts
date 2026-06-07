import type {
  CombinedCalendar,
  CombinedCalendarBillExit,
} from '@/lib/api/hooks/use-combined-calendar';
import type { BillingAccount } from '@/lib/schemas/finances/billing-account.schema';
import type { Bill, BillLineItem } from '@/lib/schemas/finances/bill.schema';
import type { BillSkip } from '@/lib/schemas/finances/bill-skip.schema';
import type { FinanceCategory } from '@/lib/schemas/finances/category.schema';
import type { Payment, PaymentAllocation } from '@/lib/schemas/finances/payment.schema';

export function createMockFinanceCategory(
  overrides: Partial<FinanceCategory> = {},
): FinanceCategory {
  return {
    id: 1,
    condominium: { id: 1, name: 'Condomínio' },
    parent: null,
    parent_id: null,
    name: 'Energia',
    color: '#f59e0b',
    sort_order: 0,
    created_at: '2026-06-01T00:00:00Z',
    updated_at: '2026-06-01T00:00:00Z',
    ...overrides,
  };
}

export function createMockBillingAccount(overrides: Partial<BillingAccount> = {}): BillingAccount {
  return {
    id: 1,
    condominium: { id: 1, name: 'Condomínio' },
    building: null,
    building_id: null,
    category: null,
    category_id: null,
    name: 'Conta de Luz - Prédio 836',
    external_identifier: '',
    description: '',
    default_due_day: 10,
    expected_amount: 350,
    lifecycle_state: 'active',
    tracking_start_month: '2026-06-01',
    end_date: null,
    notes: '',
    created_at: '2026-06-01T00:00:00Z',
    updated_at: '2026-06-01T00:00:00Z',
    ...overrides,
  };
}

export function createMockBillLineItem(overrides: Partial<BillLineItem> = {}): BillLineItem {
  return {
    id: 1,
    category: null,
    description: 'Consumo de energia',
    amount: 350,
    is_offset: false,
    ...overrides,
  };
}

export function createMockBill(overrides: Partial<Bill> = {}): Bill {
  return {
    id: 1,
    condominium: { id: 1, name: 'Condomínio' },
    building: null,
    building_id: null,
    category: null,
    category_id: null,
    competence_month: '2026-06-01',
    due_date: '2026-06-10',
    issue_date: null,
    description: 'Conta de Luz',
    external_identifier: '',
    behavior: 'recurring',
    billing_account: null,
    billing_account_id: null,
    lifecycle_state: 'active',
    notes: '',
    line_items: [createMockBillLineItem()],
    amount_total: 350,
    amount_paid: 0,
    amount_remaining: 350,
    payment_status: 'open',
    is_overdue: false,
    created_at: '2026-06-01T00:00:00Z',
    updated_at: '2026-06-01T00:00:00Z',
    ...overrides,
  };
}

export function createMockPaymentAllocation(
  overrides: Partial<PaymentAllocation> = {},
): PaymentAllocation {
  return { id: 1, bill: 1, amount: 350, ...overrides };
}

export function createMockPayment(overrides: Partial<Payment> = {}): Payment {
  return {
    id: 1,
    condominium: { id: 1, name: 'Condomínio' },
    payment_date: '2026-06-10',
    amount: 350,
    method: '',
    funded_from: 'caixa',
    reference: '',
    notes: '',
    allocations: [createMockPaymentAllocation()],
    created_at: '2026-06-10T00:00:00Z',
    updated_at: '2026-06-10T00:00:00Z',
    ...overrides,
  };
}

export function createMockBillSkip(overrides: Partial<BillSkip> = {}): BillSkip {
  return {
    id: 1,
    billing_account: 1,
    reference_month: '2026-06-01',
    ...overrides,
  };
}

export function createMockBillExit(
  overrides: Partial<CombinedCalendarBillExit> = {},
): CombinedCalendarBillExit {
  return {
    bill_id: 1,
    description: 'Conta de Luz',
    building_number: null,
    category: 'Energia',
    amount_total: '350.00',
    amount_remaining: '350.00',
    payment_status: 'open',
    due_date: '2026-06-10',
    is_overdue: false,
    lifecycle_state: 'active',
    ...overrides,
  };
}

export function createMockCombinedCalendar(
  overrides: Partial<CombinedCalendar> = {},
): CombinedCalendar {
  return {
    year: 2026,
    month: 6,
    today: '2026-06-07',
    days: [
      {
        day: 10,
        date: '2026-06-10',
        weekday: 'Quarta',
        rent_entries: [],
        bill_exits: [createMockBillExit()],
      },
    ],
    ...overrides,
  };
}

export interface MockOverdueResponse {
  bills: Bill[];
  overdue_bills_total: string;
  overdue_bills_count: number;
  rent_overdue: { count: number; total_fee: string };
}

export function createMockOverdueResponse(
  overrides: Partial<MockOverdueResponse> = {},
): MockOverdueResponse {
  return {
    bills: [createMockBill({ is_overdue: true, payment_status: 'open' })],
    overdue_bills_total: '350.00',
    overdue_bills_count: 1,
    rent_overdue: { count: 0, total_fee: '0.00' },
    ...overrides,
  };
}
