import { type z } from 'zod';
import type {
  CombinedCalendar,
  CombinedCalendarBillExit,
} from '@/lib/api/hooks/use-combined-calendar';
import { type billingAccountSchema } from '@/lib/schemas/finances/billing-account.schema';
import { type billLineItemSchema, type billSchema } from '@/lib/schemas/finances/bill.schema';
import type { ParsedInvoice } from '@/lib/schemas/finances/invoice-parse.schema';
import type { IptuAlertRow } from '@/lib/api/hooks/use-iptu-alerts';
import type { BillSkip } from '@/lib/schemas/finances/bill-skip.schema';
import { type financeCategorySchema } from '@/lib/schemas/finances/category.schema';
import { type employeeSchema } from '@/lib/schemas/finances/employee.schema';
import {
  type installmentPlanSchema,
  type installmentSchema,
} from '@/lib/schemas/finances/installment-plan.schema';
import {
  type paymentAllocationSchema,
  type paymentSchema,
} from '@/lib/schemas/finances/payment.schema';
import { type reserveSchema } from '@/lib/schemas/finances/reserve.schema';
import { type reserveMovementSchema } from '@/lib/schemas/finances/reserve-movement.schema';
import { type incomeEntrySchema } from '@/lib/schemas/finances/income-entry.schema';
import { type condoMonthCloseSchema } from '@/lib/schemas/finances/condo-month-close.schema';
import type {
  CondoProjectionMonth,
  CondoSimulationResult,
} from '@/lib/api/hooks/use-condo-projection';
import type { OwnerDistribution } from '@/lib/api/hooks/use-owner-distribution';

// These generators emit the RAW DRF read shape the hooks actually receive: monetary fields as
// STRINGS ("350.00", not 350) and NO write-only *_id fields (PrimaryKeyRelatedField(write_only)
// never appears in a read). Typed via z.input<schema> so the raw shape is type-checked. The hook's
// Zod schema coerces strings→numbers, so this is exactly what hits the schema in production.
type FinanceCategoryRaw = z.input<typeof financeCategorySchema>;
type BillingAccountRaw = z.input<typeof billingAccountSchema>;
type BillLineItemRaw = z.input<typeof billLineItemSchema>;
type BillRaw = z.input<typeof billSchema>;
type PaymentAllocationRaw = z.input<typeof paymentAllocationSchema>;
type PaymentRaw = z.input<typeof paymentSchema>;
type InstallmentRaw = z.input<typeof installmentSchema>;
type InstallmentPlanRaw = z.input<typeof installmentPlanSchema>;
type EmployeeRaw = z.input<typeof employeeSchema>;
type ReserveRaw = z.input<typeof reserveSchema>;
type ReserveMovementRaw = z.input<typeof reserveMovementSchema>;
type IncomeEntryRaw = z.input<typeof incomeEntrySchema>;
type CondoMonthCloseRaw = z.input<typeof condoMonthCloseSchema>;

export function createMockFinanceCategory(
  overrides: Partial<FinanceCategoryRaw> = {}
): FinanceCategoryRaw {
  return {
    id: 1,
    condominium: { id: 1, name: 'Condomínio' },
    parent: null,
    name: 'Energia',
    color: '#f59e0b',
    sort_order: 0,
    created_at: '2026-06-01T00:00:00Z',
    updated_at: '2026-06-01T00:00:00Z',
    ...overrides,
  };
}

export function createMockBillingAccount(
  overrides: Partial<BillingAccountRaw> = {}
): BillingAccountRaw {
  return {
    id: 1,
    condominium: { id: 1, name: 'Condomínio' },
    building: null,
    category: null,
    name: 'Conta de Luz - Prédio 836',
    external_identifier: '',
    account_type: 'generic',
    holder_name: '',
    registered_address: '',
    secondary_identifier: '',
    supply_status: 'active',
    description: '',
    default_due_day: 10,
    expected_amount: '350.00',
    lifecycle_state: 'active',
    tracking_start_month: '2026-06-01',
    end_date: null,
    notes: '',
    created_at: '2026-06-01T00:00:00Z',
    updated_at: '2026-06-01T00:00:00Z',
    ...overrides,
  };
}

export function createMockBillLineItem(overrides: Partial<BillLineItemRaw> = {}): BillLineItemRaw {
  return {
    id: 1,
    category: null,
    description: 'Consumo de energia',
    amount: '350.00',
    is_offset: false,
    ...overrides,
  };
}

export function createMockBill(overrides: Partial<BillRaw> = {}): BillRaw {
  return {
    id: 1,
    condominium: { id: 1, name: 'Condomínio' },
    building: null,
    category: null,
    competence_month: '2026-06-01',
    due_date: '2026-06-10',
    issue_date: null,
    description: 'Conta de Luz',
    external_identifier: '',
    behavior: 'recurring',
    billing_account: null,
    lifecycle_state: 'active',
    notes: '',
    line_items: [createMockBillLineItem()],
    amount_total: '350.00',
    amount_paid: '0.00',
    amount_remaining: '350.00',
    payment_status: 'open',
    is_overdue: false,
    created_at: '2026-06-01T00:00:00Z',
    updated_at: '2026-06-01T00:00:00Z',
    ...overrides,
  };
}

export function createMockParsedInvoice(overrides: Partial<ParsedInvoice> = {}): ParsedInvoice {
  return {
    bill: {
      competence_month: '2026-06-01',
      due_date: '2026-06-10',
      external_identifier: '1.273.798.010-05',
      behavior: 'recurring',
      account_type: 'electricity',
      building_id: null,
      category_id: null,
      description: 'Conta de Luz - Prédio 836',
    },
    line_items: [
      {
        description: 'Consumo de energia',
        amount: 350,
        is_offset: false,
        category_id: null,
        installment_id: null,
      },
    ],
    statement: null,
    matched_account: null,
    existing_bill_id: null,
    warnings: [],
    ...overrides,
  };
}

export function createMockIptuAlertRow(overrides: Partial<IptuAlertRow> = {}): IptuAlertRow {
  return {
    plan_id: 1,
    external_identifier: '1.273.798.010-05',
    building_label: '836',
    level: 'warning',
    overdue_count: 1,
    deadline: '2026-07-10',
    overdue_due_dates: ['2026-05-10'],
    message: 'IPTU 1.273.798.010-05 (836): 1 parcela atrasada (venc. 10/05).',
    ...overrides,
  };
}

export function createMockPaymentAllocation(
  overrides: Partial<PaymentAllocationRaw> = {}
): PaymentAllocationRaw {
  return { id: 1, bill: 1, amount: '350.00', ...overrides };
}

export function createMockPayment(overrides: Partial<PaymentRaw> = {}): PaymentRaw {
  return {
    id: 1,
    condominium: { id: 1, name: 'Condomínio' },
    payment_date: '2026-06-10',
    amount: '350.00',
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
  overrides: Partial<CombinedCalendarBillExit> = {}
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
  overrides: Partial<CombinedCalendar> = {}
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
  bills: BillRaw[];
  overdue_bills_total: string;
  overdue_bills_count: number;
  rent_overdue: { count: number; total_fee: string };
}

export function createMockOverdueResponse(
  overrides: Partial<MockOverdueResponse> = {}
): MockOverdueResponse {
  return {
    bills: [createMockBill({ is_overdue: true, payment_status: 'open' })],
    overdue_bills_total: '350.00',
    overdue_bills_count: 1,
    rent_overdue: { count: 0, total_fee: '0.00' },
    ...overrides,
  };
}

export function createMockInstallment(overrides: Partial<InstallmentRaw> = {}): InstallmentRaw {
  return {
    id: 1,
    plan: 1,
    number: 1,
    due_date: '2026-07-10',
    amount: '500.00',
    is_overdue: false,
    ...overrides,
  };
}

export function createMockInstallmentPlan(
  overrides: Partial<InstallmentPlanRaw> = {}
): InstallmentPlanRaw {
  return {
    id: 1,
    condominium: { id: 1, name: 'Condomínio' },
    description: 'IPTU 2026 - Prédio 836',
    total_amount: '1500.00',
    installment_count: 3,
    start_due_date: '2026-07-10',
    default_due_day: 10,
    lifecycle_state: 'active',
    embedded: false,
    category: null,
    building: null,
    billing_account: null,
    installments: [
      createMockInstallment({ id: 1, number: 1, amount: '500.00', due_date: '2026-07-10' }),
      createMockInstallment({ id: 2, number: 2, amount: '500.00', due_date: '2026-08-10' }),
      createMockInstallment({ id: 3, number: 3, amount: '500.00', due_date: '2026-09-10' }),
    ],
    notes: '',
    created_at: '2026-06-01T00:00:00Z',
    updated_at: '2026-06-01T00:00:00Z',
    ...overrides,
  };
}

export function createMockEmployee(overrides: Partial<EmployeeRaw> = {}): EmployeeRaw {
  return {
    id: 1,
    condominium: { id: 1, name: 'Condomínio' },
    name: 'Adriana',
    role: 'Faxineira',
    payment_type: 'fixed',
    base_salary: '1320.00',
    default_due_day: 5,
    is_active: true,
    notes: '',
    person: null,
    lease: null,
    created_at: '2026-06-01T00:00:00Z',
    updated_at: '2026-06-01T00:00:00Z',
    ...overrides,
  };
}

// --- Phase 4: reserve / income / month-close / balance dashboard (Session 46) ---

const MOCK_CONDO = { id: 1, name: 'Condomínio Central' };

export function createMockReserve(overrides: Partial<ReserveRaw> = {}): ReserveRaw {
  return {
    id: 1,
    condominium: MOCK_CONDO,
    name: 'Reserva de Emergência',
    notes: '',
    balance: '5000.00',
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ...overrides,
  };
}

export function createMockReserveMovement(
  overrides: Partial<ReserveMovementRaw> = {}
): ReserveMovementRaw {
  return {
    id: 1,
    reserve: { id: 1, name: 'Reserva de Emergência' },
    kind: 'deposit',
    amount: '1000.00',
    movement_date: '2026-06-01',
    bill: null,
    reference: null,
    notes: null,
    created_at: '2026-06-01T00:00:00Z',
    updated_at: '2026-06-01T00:00:00Z',
    ...overrides,
  };
}

export function createMockIncomeEntry(overrides: Partial<IncomeEntryRaw> = {}): IncomeEntryRaw {
  return {
    id: 1,
    condominium: MOCK_CONDO,
    building: null,
    category: null,
    description: 'Receita extra',
    amount: '500.00',
    income_date: '2026-06-05',
    is_received: false,
    received_date: null,
    notes: '',
    created_at: '2026-06-05T00:00:00Z',
    updated_at: '2026-06-05T00:00:00Z',
    ...overrides,
  };
}

export function createMockCondoMonthClose(
  overrides: Partial<CondoMonthCloseRaw> = {}
): CondoMonthCloseRaw {
  return {
    id: 1,
    condominium: MOCK_CONDO,
    reference_month: '2026-05-01',
    status: 'closed',
    closed_at: '2026-06-01T00:00:00Z',
    net_result: '2000.00',
    cash_balance_end: '15000.00',
    reserve_balance_end: '5000.00',
    carry_forward_out: '0.00',
    breakdown: {},
    created_at: '2026-06-01T00:00:00Z',
    updated_at: '2026-06-01T00:00:00Z',
    ...overrides,
  };
}

export function createMockFinanceOverview(overrides: Record<string, unknown> = {}) {
  return {
    year: 2026,
    month: 6,
    result_of_month: '2000.00',
    cash_change_of_month: '1500.00',
    cash_balance: '15000.00',
    reserve_balance: '5000.00',
    total_balance: '20000.00',
    overdue_bills_total: '300.00',
    overdue_bills_count: 2,
    rent_overdue: { count: 1, total_fee: '75.00' },
    wedge_ok: true,
    ...overrides,
  };
}

export function createMockMonthlyBalance(overrides: Record<string, unknown> = {}) {
  return {
    year: 2026,
    months: Array.from({ length: 12 }, (_, i) => ({
      month: i + 1,
      result_of_month: '2000.00',
      cash_change_of_month: '1500.00',
      cash_balance_end: String(10000 + i * 500),
      reserve_balance_end: '5000.00',
      total_balance: String(15000 + i * 500),
      is_closed: i < 5,
    })),
    ...overrides,
  };
}

export function createMockByCategory(overrides: Record<string, unknown> = {}) {
  return {
    year: 2026,
    month: 6,
    categories: [
      { category_id: 1, name: 'Manutenção', color: '#3b82f6', total: '1200.00' },
      { category_id: null, name: 'Sem categoria', color: '', total: '300.00' },
    ],
    ...overrides,
  };
}

// --- Phase 5: 12-month projection + what-if simulation (Session 48) ---

export function createMockCondoProjection(months = 12): CondoProjectionMonth[] {
  let cumulative = 5000;
  return Array.from({ length: months }, (_, i) => {
    const month = ((6 + i) % 12) + 1; // first item is the current month (July 2026)
    const year = 2026 + Math.floor((6 + i) / 12);
    const income = 4000;
    const expenses = 3200;
    const net = income - expenses;
    cumulative += net;
    return {
      year,
      month,
      income_total: income.toFixed(2),
      expenses_total: expenses.toFixed(2),
      net: net.toFixed(2),
      cumulative_cash: cumulative.toFixed(2),
      is_actual: i === 0, // current month is Real; the rest are Projetado
      is_closed: false,
    };
  });
}

export function createMockOwnerDistribution(
  overrides: Partial<OwnerDistribution> = {}
): OwnerDistribution {
  return {
    year: 2026,
    month: 7,
    household: {
      name: 'Raul & Célia',
      result_of_month: '600.00',
      carried_in: '-50.00',
      available: '550.00',
      carried_out: '0.00',
    },
    external_owners: [
      { owner_id: 2, owner_name: 'Tiago', leases_count: 2, rent_total: '1600.00' },
      { owner_id: 3, owner_name: 'Alvaro', leases_count: 2, rent_total: '1500.00' },
    ],
    external_total: '3100.00',
    ...overrides,
  };
}

export function createMockCondoSimulation(months = 12): CondoSimulationResult {
  const base = createMockCondoProjection(months);
  const simulated = base.map((m) => ({ ...m }));
  const comparison = {
    months: base.map((b, i) => {
      const sim = simulated[i] ?? b;
      return {
        year: b.year,
        month: b.month,
        base_net: b.net,
        simulated_net: sim.net,
        net_delta: '0.00',
        base_cumulative_cash: b.cumulative_cash,
        simulated_cumulative_cash: sim.cumulative_cash,
        cumulative_delta: '0.00',
      };
    }),
    final_cumulative_delta: '0.00',
    total_net_delta: '0.00',
  };
  return { base, simulated, comparison };
}
