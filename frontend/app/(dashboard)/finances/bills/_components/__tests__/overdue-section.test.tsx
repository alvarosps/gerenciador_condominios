import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { createMockBill, createMockMonthBoard } from '@/tests/mocks/data/finances';
import { billSchema, type Bill } from '@/lib/schemas/finances/bill.schema';
import { monthBoardSchema } from '@/lib/schemas/finances/month-board.schema';
import { buildBillColumns } from '../bill-columns';
import { daysLate, OverdueSection, toConsolidableBills } from '../overdue-section';

// Reuses the same column builder as the accordion body (DRY — S74 constraint). Actions are
// irrelevant here; only Descrição/Total/etc. matter for these assertions.
const columns = buildBillColumns({
  isAdmin: false,
  onEdit: () => undefined,
  onPay: () => undefined,
  onDelete: () => undefined,
  onImportInvoice: () => undefined,
});

// createMockBill returns the raw (z.input) shape used by MSW factories — components consume the
// parsed Bill (mirrors the established billSchema.parse(createMockBill(...)) pattern).
function bill(overrides: Parameters<typeof createMockBill>[0] = {}): Bill {
  return billSchema.parse(createMockBill(overrides));
}

describe('daysLate', () => {
  it('computes the day difference from a YYYY-MM-DD due_date via split (timezone-safe)', () => {
    expect(daysLate('2026-07-01', '2026-07-05')).toBe(4);
  });

  it('returns 0 for a due_date equal to today', () => {
    expect(daysLate('2026-07-05', '2026-07-05')).toBe(0);
  });
});

describe('OverdueSection', () => {
  it('returns null when both lists are empty', () => {
    const { container } = render(
      <OverdueSection
        overdue={[]}
        deferredSuspended={[]}
        columns={columns}
        overdueTotal="0.00"
        onConsolidate={() => undefined}
      />
    );
    expect(container).toBeEmptyDOMElement();
  });

  it('shows count badge and formatted overdue total in the card header', () => {
    render(
      <OverdueSection
        overdue={[bill({ id: 1 }), bill({ id: 2 })]}
        deferredSuspended={[]}
        columns={columns}
        overdueTotal="700.00"
        onConsolidate={() => undefined}
      />
    );

    expect(screen.getByText('Atrasadas')).toBeInTheDocument();
    expect(screen.getByText('2')).toBeInTheDocument();
    expect(screen.getByText('R$ 700,00')).toBeInTheDocument();
  });

  it('formats days late from due_date without new Date(iso) (timezone-safe)', () => {
    render(
      <OverdueSection
        overdue={[bill({ id: 1, due_date: '2026-07-01' })]}
        deferredSuspended={[]}
        columns={columns}
        overdueTotal="350.00"
        today="2026-07-11"
        onConsolidate={() => undefined}
      />
    );

    expect(screen.getAllByText('10 dias').length).toBeGreaterThan(0);
  });

  it('renders "N mês(es)" when the delay is 60 days or more', () => {
    render(
      <OverdueSection
        overdue={[bill({ id: 1, due_date: '2026-01-01' })]}
        deferredSuspended={[]}
        columns={columns}
        overdueTotal="350.00"
        today="2026-07-11"
        onConsolidate={() => undefined}
      />
    );

    expect(screen.getAllByText(/6 meses/).length).toBeGreaterThan(0);
  });

  it('labels suspended and deferred rows with their state badge', () => {
    render(
      <OverdueSection
        overdue={[]}
        deferredSuspended={[
          bill({ id: 1, description: 'Conta suspensa', lifecycle_state: 'suspended' }),
          bill({ id: 2, description: 'Conta adiada', lifecycle_state: 'deferred' }),
        ]}
        columns={columns}
        overdueTotal="0.00"
        onConsolidate={() => undefined}
      />
    );

    expect(screen.getByText('Dívida adiada/suspensa')).toBeInTheDocument();
    // DataTable renders both the desktop table and a CSS-hidden mobile card view for the same
    // rows (data-table-cards.tsx) — the state badge is legitimately duplicated in the DOM.
    expect(screen.getAllByText('Suspensa').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Adiada').length).toBeGreaterThan(0);
    // Explanatory text making clear these values are outside the month totals.
    expect(screen.getByText(/não entram nos totais do mês/)).toBeInTheDocument();
  });
});

describe('toConsolidableBills', () => {
  const account = {
    id: 3,
    name: 'Água 836',
    account_type: 'water' as const,
    external_identifier: 'UC-1',
    default_due_day: 10,
    expected_amount: '0.00',
    lifecycle_state: 'active' as const,
  };

  it('excludes bills that are already settled (amount_remaining <= 0) or canceled, keeping only open debt of the account (review round 1)', () => {
    const board = monthBoardSchema.parse(
      createMockMonthBoard({
        deferred_suspended: [
          createMockBill({
            id: 1,
            description: 'Já quitada',
            lifecycle_state: 'suspended',
            amount_total: '200.00',
            amount_paid: '200.00',
            amount_remaining: '0.00',
            billing_account: account,
          }),
          createMockBill({
            id: 2,
            description: 'Em aberto',
            lifecycle_state: 'suspended',
            amount_total: '300.00',
            amount_paid: '0.00',
            amount_remaining: '300.00',
            billing_account: account,
          }),
          createMockBill({
            id: 3,
            description: 'Cancelada',
            lifecycle_state: 'canceled',
            amount_total: '150.00',
            amount_paid: '0.00',
            amount_remaining: '150.00',
            billing_account: account,
          }),
        ],
        groups: [],
      })
    );

    const result = toConsolidableBills(board, 3);

    expect(result).toHaveLength(1);
    expect(result[0]?.bill_id).toBe(2);
    expect(result[0]?.description).toBe('Em aberto');
  });
});
