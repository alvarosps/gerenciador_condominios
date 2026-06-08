import { describe, it, expect, vi } from 'vitest';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { screen, waitFor, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '@/tests/test-utils';
import { Form } from '@/components/ui/form';
import { BillLineItemsField } from '../bill-line-items-field';
import { billFormSchema, type BillFormValues, type BillLineFormValues } from '../bill-form-schema';

// Stub the category hook so the field renders without firing a real XHR (which would leak
// into teardown). The field only reads `.data`; an empty list is enough for these tests.
vi.mock('@/lib/api/hooks/use-finance-categories', () => ({
  useFinanceCategories: () => ({ data: [] }),
}));

function TestHost({ initialLines }: { initialLines: BillLineFormValues[] }) {
  const form = useForm<BillFormValues>({
    resolver: zodResolver(billFormSchema),
    defaultValues: {
      description: 'Conta',
      building_id: null,
      category_id: null,
      competence_month: '2026-06-01',
      due_date: '2026-06-10',
      behavior: 'one_time',
      billing_account_id: null,
      external_identifier: '',
      issue_date: null,
      notes: '',
      line_items: initialLines,
    },
  });

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(() => undefined)} noValidate>
        <BillLineItemsField form={form} />
        <button type="submit">Salvar</button>
      </form>
    </Form>
  );
}

function line(amount: number, is_offset = false): BillLineFormValues {
  return { category_id: null, description: 'Linha', amount, is_offset };
}

describe('BillLineItemsField', () => {
  it('renders the initial lines and appends/removes lines', async () => {
    renderWithProviders(<TestHost initialLines={[line(100)]} />);

    expect(screen.getByText('Linha 1')).toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: /adicionar linha/i }));
    expect(screen.getByText('Linha 2')).toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: /remover linha 2/i }));
    expect(screen.queryByText('Linha 2')).not.toBeInTheDocument();
  });

  it('shows the §4.1 subtotal Σ non-offset − Σ offset = 900 for [600, 400, 100-offset]', () => {
    renderWithProviders(
      <TestHost initialLines={[line(600), line(400), line(100, true)]} />,
    );
    expect(screen.getByTestId('bill-line-subtotal')).toHaveTextContent('R$ 900,00');
  });

  it('shows subtotal 0 for [100, 100-offset]', () => {
    renderWithProviders(<TestHost initialLines={[line(100), line(100, true)]} />);
    expect(screen.getByTestId('bill-line-subtotal')).toHaveTextContent('R$ 0,00');
  });

  it('blocks a negative amount with a Portuguese message', async () => {
    renderWithProviders(<TestHost initialLines={[line(100)]} />);

    const amountInput = screen.getByRole('spinbutton');
    fireEvent.change(amountInput, { target: { value: '-50' } });
    await userEvent.click(screen.getByRole('button', { name: /salvar/i }));

    await waitFor(() => {
      expect(screen.getByText('O valor não pode ser negativo')).toBeInTheDocument();
    });
  });

  it('shows the Portuguese empty state when all lines are removed', async () => {
    renderWithProviders(<TestHost initialLines={[line(100)]} />);
    await userEvent.click(screen.getByRole('button', { name: /remover linha 1/i }));
    expect(
      screen.getByText('Nenhuma linha — adicione consumo e/ou parcela'),
    ).toBeInTheDocument();
  });
});
