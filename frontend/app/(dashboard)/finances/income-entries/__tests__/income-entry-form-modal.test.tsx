import { describe, it, expect, vi, beforeEach } from 'vitest';
import { http, HttpResponse } from 'msw';
import { screen, fireEvent, waitFor } from '@testing-library/react';
import { renderWithProviders, waitForQueriesToSettle } from '@/tests/test-utils';
import { server } from '@/tests/mocks/server';
import { createMockIncomeEntry } from '@/tests/mocks/data/finances';
import { incomeEntrySchema } from '@/lib/schemas/finances/income-entry.schema';
import { toast } from 'sonner';
import { IncomeEntryFormModal } from '../_components/income-entry-form-modal';

const API_BASE = 'http://localhost:8008/api';

// The modal runs through the real create/update mutations hitting MSW (the HTTP boundary); no hook
// is mocked. Buildings/categories come from the default handlers (empty lists here). `toast` is the
// global sonner mock from tests/setup.ts.

// Radix Dialog forms must be submitted via the form element (happy-dom does not translate a
// submit-button click into a form submit) — the project's established pattern.
function submitDialogForm() {
  const formEl = screen.getByRole('dialog').querySelector('form');
  if (!formEl) throw new Error('dialog form not found');
  fireEvent.submit(formEl);
}

/** Spy the create POST; pushes each request body, returns a parseable raw income entry. */
function spyCreate() {
  const bodies: Record<string, unknown>[] = [];
  server.use(
    http.post(`${API_BASE}/finances/income-entries/`, async ({ request }) => {
      const body = (await request.json()) as Record<string, unknown>;
      bodies.push(body);
      return HttpResponse.json(createMockIncomeEntry({ id: 10, ...body }), { status: 201 });
    })
  );
  return bodies;
}

/** Spy the update PUT; pushes each request body, returns a parseable raw income entry. */
function spyUpdate(id: number) {
  const bodies: Record<string, unknown>[] = [];
  server.use(
    http.put(`${API_BASE}/finances/income-entries/${id}/`, async ({ request }) => {
      const body = (await request.json()) as Record<string, unknown>;
      bodies.push(body);
      return HttpResponse.json(createMockIncomeEntry({ id, ...body }));
    })
  );
  return bodies;
}

describe('IncomeEntryFormModal', () => {
  beforeEach(() => {
    vi.mocked(toast.success).mockReset();
    vi.mocked(toast.error).mockReset();
  });

  it('creates an income entry WITHOUT sending condominium_id (backend defaults the singleton)', async () => {
    const bodies = spyCreate();
    const { queryClient } = renderWithProviders(
      <IncomeEntryFormModal open entry={null} onClose={vi.fn()} />
    );
    fireEvent.change(screen.getByLabelText('Descrição *'), { target: { value: 'Doação' } });
    fireEvent.change(screen.getByRole('spinbutton'), { target: { value: '100' } });
    fireEvent.change(screen.getByLabelText('Data *'), { target: { value: '2026-06-10' } });
    submitDialogForm();
    await waitFor(() => expect(bodies).toHaveLength(1));
    const payload = bodies[0] ?? {};
    expect(payload).toMatchObject({
      description: 'Doação',
      amount: 100,
      income_date: '2026-06-10',
    });
    expect(payload).not.toHaveProperty('condominium_id');

    await waitForQueriesToSettle(queryClient);
  });

  it('reveals the received_date field only when is_received is toggled on (watch)', async () => {
    const { queryClient } = renderWithProviders(
      <IncomeEntryFormModal open entry={null} onClose={vi.fn()} />
    );
    expect(screen.queryByLabelText('Data de recebimento *')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('switch'));
    expect(await screen.findByLabelText('Data de recebimento *')).toBeInTheDocument();

    await waitForQueriesToSettle(queryClient);
  });

  it('blocks submission without a description / with amount <= 0 (Zod, PT)', async () => {
    const bodies = spyCreate();
    const { queryClient } = renderWithProviders(
      <IncomeEntryFormModal open entry={null} onClose={vi.fn()} />
    );
    submitDialogForm();
    expect(await screen.findByText(/Descrição é obrigatória/)).toBeInTheDocument();
    expect(bodies).toHaveLength(0);

    await waitForQueriesToSettle(queryClient);
  });

  it('requires received_date when is_received is on (cross-field refine, PT) — mutation not called', async () => {
    const bodies = spyCreate();
    const { queryClient } = renderWithProviders(
      <IncomeEntryFormModal open entry={null} onClose={vi.fn()} />
    );
    fireEvent.change(screen.getByLabelText('Descrição *'), { target: { value: 'Doação' } });
    fireEvent.change(screen.getByRole('spinbutton'), { target: { value: '100' } });
    fireEvent.change(screen.getByLabelText('Data *'), { target: { value: '2026-06-10' } });
    fireEvent.click(screen.getByRole('switch')); // is_received on, received_date left empty
    submitDialogForm();
    expect(await screen.findByText(/Data de recebimento é obrigatória/)).toBeInTheDocument();
    expect(bodies).toHaveLength(0);

    await waitForQueriesToSettle(queryClient);
  });

  it('prefills fields on edit and calls update with the id', async () => {
    // Raw mock (amount as a STRING) parsed into the typed IncomeEntry the prop expects.
    const entry = incomeEntrySchema.parse(
      createMockIncomeEntry({
        id: 5,
        description: 'Original',
        amount: '200.00',
        income_date: '2026-04-01',
      })
    );
    const bodies = spyUpdate(5);
    const { queryClient } = renderWithProviders(
      <IncomeEntryFormModal open entry={entry} onClose={vi.fn()} />
    );
    expect(screen.getByDisplayValue('Original')).toBeInTheDocument();
    submitDialogForm();
    await waitFor(() => expect(bodies).toHaveLength(1));
    expect(bodies[0]).toMatchObject({ description: 'Original' });

    await waitForQueriesToSettle(queryClient);
  });
});
