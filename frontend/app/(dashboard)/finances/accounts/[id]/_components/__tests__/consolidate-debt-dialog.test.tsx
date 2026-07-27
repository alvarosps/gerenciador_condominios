import { describe, it, expect, vi, beforeAll, beforeEach } from 'vitest';
import { http, HttpResponse } from 'msw';
import { screen, waitFor, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { toast } from 'sonner';
import { renderWithProviders, waitForQueriesToSettle } from '@/tests/test-utils';
import { server } from '@/tests/mocks/server';
import { createMockInstallmentPlan } from '@/tests/mocks/data/finances';
import { ConsolidateDebtDialog, type ConsolidableBill } from '../consolidate-debt-dialog';

const API_BASE = 'http://localhost:8008/api';

const bills: ConsolidableBill[] = [
  {
    bill_id: 1,
    description: 'Conta de Água — Maio',
    competence_month: '2026-05-01',
    due_date: '2026-05-10',
    amount_remaining: 200,
  },
  {
    bill_id: 2,
    description: 'Conta de Água — Junho',
    competence_month: '2026-06-01',
    due_date: '2026-06-10',
    amount_remaining: 150,
  },
];

// happy-dom is missing the pointer-capture / scroll APIs Radix Select relies on.
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

function spyConsolidate(accountId = 7) {
  const bodies: Record<string, unknown>[] = [];
  server.use(
    http.post(
      `${API_BASE}/finances/billing-accounts/${String(accountId)}/consolidate_debt/`,
      async ({ request }) => {
        const body = (await request.json()) as Record<string, unknown>;
        bodies.push(body);
        return HttpResponse.json(createMockInstallmentPlan(), { status: 201 });
      }
    )
  );
  return bodies;
}

describe('ConsolidateDebtDialog', () => {
  beforeEach(() => {
    vi.mocked(toast.success).mockReset();
    vi.mocked(toast.error).mockReset();
  });

  it('lista as bills com resto formatado e atualiza o total do plano conforme a seleção', async () => {
    const { queryClient } = renderWithProviders(
      <ConsolidateDebtDialog
        open
        onClose={vi.fn()}
        accountId={7}
        accountType="water"
        bills={bills}
      />
    );

    expect(screen.getByText('R$ 200,00')).toBeInTheDocument();
    expect(screen.getByText('R$ 150,00')).toBeInTheDocument();

    // Nothing selected yet -> total starts at zero.
    expect(screen.getByText('R$ 0,00')).toBeInTheDocument();

    fireEvent.click(
      screen.getByRole('checkbox', { name: /selecionar fatura conta de água — maio/i })
    );

    await waitFor(() => {
      expect(
        screen.getByText('R$ 200,00', { selector: '[data-testid="consolidate-total"]' })
      ).toBeInTheDocument();
    });

    await waitForQueriesToSettle(queryClient);
  });

  it('posta o body do contrato S70 (bill_ids selecionadas, embedded, installment_count, start_due_date, default_due_day)', async () => {
    const bodies = spyConsolidate(7);
    const user = userEvent.setup({ pointerEventsCheck: 0 });

    const { queryClient } = renderWithProviders(
      <ConsolidateDebtDialog
        open
        onClose={vi.fn()}
        accountId={7}
        accountType="water"
        bills={bills}
      />
    );

    // Selecting "select all" alone checks every bill row.
    fireEvent.click(screen.getByRole('checkbox', { name: /selecionar todas/i }));

    const installmentCountInput = screen.getByLabelText(/número de parcelas/i);
    await user.clear(installmentCountInput);
    await user.type(installmentCountInput, '3');

    const startDueDateInput = screen.getByLabelText(/data da primeira parcela/i);
    fireEvent.change(startDueDateInput, { target: { value: '2026-08-10' } });

    const defaultDueDayInput = screen.getByLabelText(/dia de vencimento/i);
    await user.clear(defaultDueDayInput);
    await user.type(defaultDueDayInput, '10');

    await user.click(screen.getByRole('button', { name: /parcelar/i }));

    await waitFor(() => expect(bodies).toHaveLength(1));
    expect(bodies[0]).toEqual({
      bill_ids: [1, 2],
      embedded: false,
      installment_count: 3,
      start_due_date: '2026-08-10',
      default_due_day: 10,
    });

    await waitForQueriesToSettle(queryClient);
  });

  it('bloqueia submit sem seleção com mensagem PT', async () => {
    const bodies = spyConsolidate(7);

    const { queryClient } = renderWithProviders(
      <ConsolidateDebtDialog
        open
        onClose={vi.fn()}
        accountId={7}
        accountType="water"
        bills={bills}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: /parcelar/i }));

    expect(await screen.findByText(/selecione ao menos uma fatura/i)).toBeInTheDocument();
    expect(bodies).toHaveLength(0);

    await waitForQueriesToSettle(queryClient);
  });

  it('trava embedded em "Plano avulso" quando accountType é iptu/generic (hint PT visível)', async () => {
    const user = userEvent.setup({ pointerEventsCheck: 0 });
    const { queryClient } = renderWithProviders(
      <ConsolidateDebtDialog
        open
        onClose={vi.fn()}
        accountId={7}
        accountType="iptu"
        bills={bills}
      />
    );

    const embeddedSelect = screen.getByRole('combobox', { name: /parcelamento/i });
    expect(embeddedSelect).toHaveAttribute('data-disabled');

    expect(
      screen.getByText(/parcelamento embutido só para contas de consumo/i)
    ).toBeInTheDocument();

    await user.click(screen.getByRole('checkbox', { name: /selecionar todas/i }));
    await waitForQueriesToSettle(queryClient);
  });

  it('permite escolher Embutido para conta de consumo (water)', async () => {
    const user = userEvent.setup({ pointerEventsCheck: 0 });
    const bodies = spyConsolidate(7);

    const { queryClient } = renderWithProviders(
      <ConsolidateDebtDialog
        open
        onClose={vi.fn()}
        accountId={7}
        accountType="water"
        bills={bills}
      />
    );

    const embeddedSelect = screen.getByRole('combobox', { name: /parcelamento/i });
    expect(embeddedSelect).not.toHaveAttribute('data-disabled');

    await user.click(embeddedSelect);
    await user.click(await screen.findByRole('option', { name: /embutido na conta/i }));

    // Selecting "select all" alone checks every bill row.
    fireEvent.click(screen.getByRole('checkbox', { name: /selecionar todas/i }));
    fireEvent.click(screen.getByRole('button', { name: /parcelar/i }));

    await waitFor(() => expect(bodies).toHaveLength(1));
    expect(bodies[0]).toMatchObject({ embedded: true });

    await waitForQueriesToSettle(queryClient);
  });

  it('erro 400 do backend mantém o dialog aberto e exibe um toast acionável "Abrir fechamento"', async () => {
    // S76: closed-month failures route through showFinanceMutationError(error, fallback, …),
    // which shows the server's PT message via toast.error with the "Abrir fechamento" action.
    server.use(
      http.post(`${API_BASE}/finances/billing-accounts/7/consolidate_debt/`, () =>
        HttpResponse.json({ detail: 'Competência fechada.' }, { status: 400 })
      )
    );
    const onClose = vi.fn();

    const { queryClient } = renderWithProviders(
      <ConsolidateDebtDialog
        open
        onClose={onClose}
        accountId={7}
        accountType="water"
        bills={bills}
      />
    );

    // Selecting "select all" alone checks every bill row.
    fireEvent.click(screen.getByRole('checkbox', { name: /selecionar todas/i }));
    fireEvent.click(screen.getByRole('button', { name: /parcelar/i }));

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith(
        'Competência fechada.',
        expect.objectContaining({
          action: expect.objectContaining({ label: 'Abrir fechamento' }) as unknown,
        })
      );
    });
    expect(onClose).not.toHaveBeenCalled();

    await waitForQueriesToSettle(queryClient);
  });

  it('sucesso fecha o dialog e dispara toast de plano criado', async () => {
    spyConsolidate(7);
    const onClose = vi.fn();

    const { queryClient } = renderWithProviders(
      <ConsolidateDebtDialog
        open
        onClose={onClose}
        accountId={7}
        accountType="water"
        bills={bills}
      />
    );

    // Selecting "select all" alone checks every bill row.
    fireEvent.click(screen.getByRole('checkbox', { name: /selecionar todas/i }));
    fireEvent.click(screen.getByRole('button', { name: /parcelar/i }));

    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith('Saldo devedor parcelado — plano criado');
    });
    expect(onClose).toHaveBeenCalled();

    await waitForQueriesToSettle(queryClient);
  });
});
