import { describe, it, expect, vi, beforeAll, beforeEach } from 'vitest';
import { http, HttpResponse } from 'msw';
import { screen, waitFor, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { toast } from 'sonner';
import { renderWithProviders, waitForQueriesToSettle } from '@/tests/test-utils';
import { server } from '@/tests/mocks/server';
import { createMockBill } from '@/tests/mocks/data/finances';
import { QuickBillDialog } from '../quick-bill-dialog';

const API_BASE = 'http://localhost:8008/api';

interface CreateBody {
  bill: Record<string, unknown>;
  line_items: { description: string; amount: number; is_offset?: boolean }[];
}

function spyCreateWithLines() {
  const bodies: CreateBody[] = [];
  server.use(
    http.post(`${API_BASE}/finances/bills/create_with_lines/`, async ({ request }) => {
      bodies.push((await request.json()) as CreateBody);
      return HttpResponse.json(createMockBill({ id: 99 }), { status: 201 });
    })
  );
  return bodies;
}

function setBuildingsEmpty() {
  server.use(http.get(`${API_BASE}/buildings/`, () => HttpResponse.json([])));
}

function setCategoriesEmpty() {
  server.use(http.get(`${API_BASE}/finances/finance-categories/`, () => HttpResponse.json([])));
}

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

describe('QuickBillDialog', () => {
  beforeEach(() => {
    vi.mocked(toast.success).mockReset();
    vi.mocked(toast.error).mockReset();
    setBuildingsEmpty();
    setCategoriesEmpty();
  });

  it('creates a one_time bill with exactly one line via create_with_lines', async () => {
    const bodies = spyCreateWithLines();

    const { queryClient } = renderWithProviders(
      <QuickBillDialog open onClose={vi.fn()} year={2026} month={6} />
    );

    fireEvent.change(await screen.findByLabelText(/descrição/i), {
      target: { value: 'Reparo emergencial' },
    });
    fireEvent.change(screen.getByLabelText(/valor/i), { target: { value: '150' } });
    fireEvent.change(screen.getByLabelText(/vencimento/i), { target: { value: '2026-06-15' } });

    await userEvent.click(screen.getByRole('button', { name: /^criar$/i }));

    await waitFor(() => expect(bodies).toHaveLength(1));
    expect(bodies[0]?.bill).toMatchObject({
      description: 'Reparo emergencial',
      due_date: '2026-06-15',
      competence_month: '2026-06-01',
      behavior: 'one_time',
    });
    expect(bodies[0]?.line_items).toEqual([
      { description: 'Reparo emergencial', amount: 150, is_offset: false },
    ]);

    await waitForQueriesToSettle(queryClient);
  });

  it('validates required fields (descrição, valor > 0, vencimento) in PT', async () => {
    const bodies = spyCreateWithLines();

    renderWithProviders(<QuickBillDialog open onClose={vi.fn()} year={2026} month={6} />);

    await screen.findByLabelText(/descrição/i);
    await userEvent.click(screen.getByRole('button', { name: /^criar$/i }));

    expect(await screen.findByText(/descrição é obrigatória/i)).toBeInTheDocument();
    expect(screen.getByText(/o valor deve ser maior que zero/i)).toBeInTheDocument();
    expect(bodies).toHaveLength(0);
  });

  it('defaults competence_month to the month currently shown on the board', async () => {
    const bodies = spyCreateWithLines();

    const { queryClient } = renderWithProviders(
      <QuickBillDialog open onClose={vi.fn()} year={2026} month={11} />
    );

    fireEvent.change(await screen.findByLabelText(/descrição/i), {
      target: { value: 'Extintor' },
    });
    fireEvent.change(screen.getByLabelText(/valor/i), { target: { value: '80' } });
    fireEvent.change(screen.getByLabelText(/vencimento/i), { target: { value: '2026-11-05' } });

    await userEvent.click(screen.getByRole('button', { name: /^criar$/i }));

    await waitFor(() => expect(bodies).toHaveLength(1));
    expect(bodies[0]?.bill.competence_month).toBe('2026-11-01');

    await waitForQueriesToSettle(queryClient);
  });
});
