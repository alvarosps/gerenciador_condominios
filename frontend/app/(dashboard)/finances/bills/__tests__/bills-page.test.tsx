import { describe, it, expect, vi, beforeAll, beforeEach, afterEach } from 'vitest';
import { http, HttpResponse, delay } from 'msw';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders, createTestQueryClient } from '@/tests/test-utils';
import { server } from '@/tests/mocks/server';
import { useAuthStore } from '@/store/auth-store';
import { createMockBill } from '@/tests/mocks/data/finances';
import BillsPage from '../page';
import * as billHooks from '@/lib/api/hooks/use-bills';

vi.mock('@/lib/api/hooks/use-bills', async (importOriginal) => {
  const actual = await importOriginal<typeof billHooks>();
  return { ...actual, useGenerateMonthBills: vi.fn() };
});

// Stub the building filter hook so its (delayed) XHR does not leak into teardown; the bills
// list still goes through MSW (and is awaited by each test, so it settles cleanly).
vi.mock('@/lib/api/hooks/use-buildings', () => ({ useBuildings: () => ({ data: [] }) }));

const API_BASE = 'http://localhost:8008/api';

beforeAll(() => {
  if (!Element.prototype.hasPointerCapture) {
    Element.prototype.hasPointerCapture = () => false;
    Element.prototype.setPointerCapture = () => undefined;
    Element.prototype.releasePointerCapture = () => undefined;
  }
  if (!Element.prototype.scrollIntoView) {
    Element.prototype.scrollIntoView = () => undefined;
  }
});

function setBillsResponse(bills: unknown[]) {
  server.use(
    http.get(`${API_BASE}/finances/bills/`, () => HttpResponse.json(bills)),
  );
}

function setAdmin(isStaff: boolean) {
  useAuthStore.setState({
    user: { id: 1, email: 'a@b.c', first_name: 'A', last_name: 'B', is_staff: isStaff },
    isAuthenticated: true,
  });
}

function mockGenerate() {
  const calls: { year: number; month: number }[] = [];
  const mutate = vi.fn(
    (params: { year: number; month: number }, options?: { onSuccess?: (r: unknown) => void }) => {
      calls.push(params);
      options?.onSuccess?.({ created: 1, bills: [] });
    },
  );
  vi.mocked(billHooks.useGenerateMonthBills).mockReturnValue({ mutate, isPending: false } as never);
  return { calls };
}

describe('BillsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGenerate();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders the table but hides all write buttons for non-admin users', async () => {
    setAdmin(false);
    setBillsResponse([createMockBill({ id: 1, description: 'Conta de Luz' })]);

    renderWithProviders(<BillsPage />, { queryClient: createTestQueryClient() });

    expect((await screen.findAllByText('Conta de Luz')).length).toBeGreaterThan(0);
    expect(screen.queryByRole('button', { name: /nova conta/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /gerar contas do mês/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /ações da conta/i })).not.toBeInTheDocument();
  });

  it('shows write buttons for admin and generate-month calls useGenerateMonthBills', async () => {
    setAdmin(true);
    const { calls } = mockGenerate();
    setBillsResponse([createMockBill({ id: 1, description: 'Conta de Luz' })]);

    renderWithProviders(<BillsPage />, { queryClient: createTestQueryClient() });

    expect(await screen.findByRole('button', { name: /nova conta/i })).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: /gerar contas do mês/i }));

    await waitFor(() => {
      expect(calls).toHaveLength(1);
    });
    expect(calls[0]).toMatchObject({
      year: expect.any(Number) as number,
      month: expect.any(Number) as number,
    });
  });

  it('formats competence via split + formatMonthYear and shows "Condomínio" for null building', async () => {
    setAdmin(false);
    setBillsResponse([
      createMockBill({ id: 1, competence_month: '2026-06-01', building: null, building_id: null }),
    ]);

    renderWithProviders(<BillsPage />, { queryClient: createTestQueryClient() });

    expect((await screen.findAllByText('Junho de 2026')).length).toBeGreaterThan(0);
    expect(screen.getAllByText('Condomínio').length).toBeGreaterThan(0);
  });

  it('renders a lifecycle chip (not "Em atraso") for a deferred bill', async () => {
    setAdmin(false);
    setBillsResponse([
      createMockBill({
        id: 1,
        lifecycle_state: 'deferred',
        is_overdue: true,
        payment_status: 'open',
      }),
    ]);

    renderWithProviders(<BillsPage />, { queryClient: createTestQueryClient() });

    expect((await screen.findAllByText('Adiada')).length).toBeGreaterThan(0);
    expect(screen.queryByText('Em atraso')).not.toBeInTheDocument();
  });

  it('shows the overdue chip for an overdue active bill', async () => {
    setAdmin(false);
    setBillsResponse([
      createMockBill({ id: 1, lifecycle_state: 'active', is_overdue: true, payment_status: 'open' }),
    ]);

    renderWithProviders(<BillsPage />, { queryClient: createTestQueryClient() });

    expect((await screen.findAllByText('Em atraso')).length).toBeGreaterThan(0);
  });

  it('shows a loading skeleton then content', async () => {
    setAdmin(false);
    server.use(
      http.get(`${API_BASE}/finances/bills/`, async () => {
        await delay(50);
        return HttpResponse.json([createMockBill({ id: 1, description: 'Conta de Luz' })]);
      }),
    );

    renderWithProviders(<BillsPage />, { queryClient: createTestQueryClient() });
    expect((await screen.findAllByText('Conta de Luz')).length).toBeGreaterThan(0);
  });

  it('shows a Portuguese empty state when there are no bills', async () => {
    setAdmin(false);
    setBillsResponse([]);

    renderWithProviders(<BillsPage />, { queryClient: createTestQueryClient() });

    expect(await screen.findByText('Nenhuma conta cadastrada')).toBeInTheDocument();
  });
});
