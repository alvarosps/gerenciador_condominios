import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, fireEvent, waitFor } from '@testing-library/react';
import { renderWithProviders } from '@/tests/test-utils';
import { IncomeEntryFormModal } from '../_components/income-entry-form-modal';
import { createMockIncomeEntry } from '@/tests/mocks/data/finances';

const { createSpy, updateSpy } = vi.hoisted(() => ({
  createSpy: vi.fn(),
  updateSpy: vi.fn(),
}));

vi.mock('@/lib/api/hooks/use-income-entries', () => ({
  useCreateIncomeEntry: () => ({ mutateAsync: createSpy, isPending: false }),
  useUpdateIncomeEntry: () => ({ mutateAsync: updateSpy, isPending: false }),
}));
vi.mock('@/lib/api/hooks/use-buildings', () => ({
  useBuildings: () => ({ data: [], isLoading: false }),
}));
vi.mock('@/lib/api/hooks/use-finance-categories', () => ({
  useFinanceCategories: () => ({ data: [], isLoading: false }),
}));
vi.mock('sonner', () => ({ toast: { success: vi.fn(), error: vi.fn() } }));

// Radix Dialog forms must be submitted via the form element (happy-dom does not translate a
// submit-button click into a form submit) — the project's established pattern.
function submitDialogForm() {
  const formEl = screen.getByRole('dialog').querySelector('form');
  if (!formEl) throw new Error('dialog form not found');
  fireEvent.submit(formEl);
}

describe('IncomeEntryFormModal', () => {
  beforeEach(() => {
    createSpy.mockReset().mockResolvedValue({});
    updateSpy.mockReset().mockResolvedValue({});
  });

  it('creates an income entry WITHOUT sending condominium_id (backend defaults the singleton)', async () => {
    renderWithProviders(<IncomeEntryFormModal open entry={null} onClose={vi.fn()} />);
    fireEvent.change(screen.getByLabelText('Descrição *'), { target: { value: 'Doação' } });
    fireEvent.change(screen.getByRole('spinbutton'), { target: { value: '100' } });
    fireEvent.change(screen.getByLabelText('Data *'), { target: { value: '2026-06-10' } });
    submitDialogForm();
    await waitFor(() => expect(createSpy).toHaveBeenCalled());
    const payload = createSpy.mock.calls[0]?.[0] as Record<string, unknown>;
    expect(payload).toMatchObject({ description: 'Doação', amount: 100, income_date: '2026-06-10' });
    expect(payload).not.toHaveProperty('condominium_id');
  });

  it('reveals the received_date field only when is_received is toggled on (watch)', async () => {
    renderWithProviders(<IncomeEntryFormModal open entry={null} onClose={vi.fn()} />);
    expect(screen.queryByLabelText('Data de recebimento *')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('switch'));
    expect(await screen.findByLabelText('Data de recebimento *')).toBeInTheDocument();
  });

  it('blocks submission without a description / with amount <= 0 (Zod, PT)', async () => {
    renderWithProviders(<IncomeEntryFormModal open entry={null} onClose={vi.fn()} />);
    submitDialogForm();
    expect(await screen.findByText(/Descrição é obrigatória/)).toBeInTheDocument();
    expect(createSpy).not.toHaveBeenCalled();
  });

  it('requires received_date when is_received is on (cross-field refine, PT) — mutation not called', async () => {
    renderWithProviders(<IncomeEntryFormModal open entry={null} onClose={vi.fn()} />);
    fireEvent.change(screen.getByLabelText('Descrição *'), { target: { value: 'Doação' } });
    fireEvent.change(screen.getByRole('spinbutton'), { target: { value: '100' } });
    fireEvent.change(screen.getByLabelText('Data *'), { target: { value: '2026-06-10' } });
    fireEvent.click(screen.getByRole('switch')); // is_received on, received_date left empty
    submitDialogForm();
    expect(await screen.findByText(/Data de recebimento é obrigatória/)).toBeInTheDocument();
    expect(createSpy).not.toHaveBeenCalled();
  });

  it('prefills fields on edit and calls update with the id', async () => {
    const entry = createMockIncomeEntry({ id: 5, description: 'Original', amount: 200, income_date: '2026-04-01' });
    renderWithProviders(<IncomeEntryFormModal open entry={entry} onClose={vi.fn()} />);
    expect(screen.getByDisplayValue('Original')).toBeInTheDocument();
    submitDialogForm();
    await waitFor(() => expect(updateSpy).toHaveBeenCalled());
    expect(updateSpy.mock.calls[0]?.[0]).toMatchObject({ id: 5, description: 'Original' });
  });
});
