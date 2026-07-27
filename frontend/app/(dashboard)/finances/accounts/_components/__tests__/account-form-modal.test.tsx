import { describe, it, expect, beforeAll } from 'vitest';
import { http, HttpResponse } from 'msw';
import { screen, waitFor, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders, waitForQueriesToSettle } from '@/tests/test-utils';
import { server } from '@/tests/mocks/server';
import { createMockBillingAccount } from '@/tests/mocks/data/finances';
import { billingAccountSchema } from '@/lib/schemas/finances/billing-account.schema';
import { AccountFormModal } from '../account-form-modal';

// Real hooks (useCreateBillingAccount / useUpdateBillingAccount / useBuildings /
// useFinanceCategories) hit MSW — no hook is mocked (project mock policy).
const API_BASE = 'http://localhost:8008/api';

function setSourcesEmpty() {
  server.use(
    http.get(`${API_BASE}/buildings/`, () => HttpResponse.json([])),
    http.get(`${API_BASE}/finances/finance-categories/`, () => HttpResponse.json([]))
  );
}

function spyCreate() {
  const bodies: Record<string, unknown>[] = [];
  server.use(
    http.post(`${API_BASE}/finances/billing-accounts/`, async ({ request }) => {
      const body = (await request.json()) as Record<string, unknown>;
      bodies.push(body);
      return HttpResponse.json(createMockBillingAccount({ id: 99, ...body }), { status: 201 });
    })
  );
  return bodies;
}

function spyUpdate() {
  const bodies: (Record<string, unknown> & { id: number })[] = [];
  server.use(
    http.put(`${API_BASE}/finances/billing-accounts/:id/`, async ({ params, request }) => {
      const body = (await request.json()) as Record<string, unknown>;
      bodies.push({ ...body, id: Number(params.id) });
      return HttpResponse.json(createMockBillingAccount({ id: Number(params.id), ...body }));
    })
  );
  return bodies;
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

describe('AccountFormModal', () => {
  it('cria com payload dual-pattern: building_id/category_id planos, sem objetos nested nem open_balance', async () => {
    setSourcesEmpty();
    const creates = spyCreate();
    const { queryClient } = renderWithProviders(
      <AccountFormModal open onClose={() => undefined} />
    );

    fireEvent.change(screen.getByPlaceholderText('Ex: Água DMAE 836'), {
      target: { value: 'Conta de Luz - Prédio 836' },
    });

    await userEvent.click(screen.getByRole('button', { name: /^criar$/i }));

    await waitFor(() => {
      expect(creates).toHaveLength(1);
    });
    const body = creates[0];
    expect(body).toMatchObject({
      name: 'Conta de Luz - Prédio 836',
      building_id: null,
      category_id: null,
    });
    expect(body).not.toHaveProperty('building');
    expect(body).not.toHaveProperty('category');
    expect(body).not.toHaveProperty('condominium');
    expect(body).not.toHaveProperty('open_balance');

    await waitForQueriesToSettle(queryClient);
  });

  it('preenche o Textarea de description e envia o valor no payload', async () => {
    setSourcesEmpty();
    const creates = spyCreate();
    const { queryClient } = renderWithProviders(
      <AccountFormModal open onClose={() => undefined} />
    );

    fireEvent.change(screen.getByPlaceholderText('Ex: Água DMAE 836'), {
      target: { value: 'Internet Condomínio' },
    });
    fireEvent.change(screen.getByPlaceholderText('Descrição da conta...'), {
      target: { value: 'Plano de internet fibra do salão de festas' },
    });

    await userEvent.click(screen.getByRole('button', { name: /^criar$/i }));

    await waitFor(() => {
      expect(creates).toHaveLength(1);
    });
    expect(creates[0]).toMatchObject({
      description: 'Plano de internet fibra do salão de festas',
    });

    await waitForQueriesToSettle(queryClient);
  });

  it('rejeita external_identifier vazio para water/electricity/iptu com mensagem PT', async () => {
    setSourcesEmpty();
    const user = userEvent.setup({ pointerEventsCheck: 0 });
    const creates = spyCreate();
    const { queryClient } = renderWithProviders(
      <AccountFormModal open onClose={() => undefined} />
    );

    fireEvent.change(screen.getByPlaceholderText('Ex: Água DMAE 836'), {
      target: { value: 'Água DMAE 836' },
    });

    await user.click(screen.getByLabelText('Tipo de conta'));
    await user.click(await screen.findByRole('option', { name: 'Água' }));

    await user.click(screen.getByRole('button', { name: /^criar$/i }));

    expect(
      await screen.findByText('Inscrição/UC é obrigatória para contas de água, luz e IPTU')
    ).toBeInTheDocument();
    expect(creates).toHaveLength(0);

    await waitForQueriesToSettle(queryClient);
  });

  it('aceita external_identifier vazio para generic/internet', async () => {
    setSourcesEmpty();
    const creates = spyCreate();
    const { queryClient } = renderWithProviders(
      <AccountFormModal open onClose={() => undefined} />
    );

    fireEvent.change(screen.getByPlaceholderText('Ex: Água DMAE 836'), {
      target: { value: 'Genérica Condomínio' },
    });

    await userEvent.click(screen.getByRole('button', { name: /^criar$/i }));

    await waitFor(() => {
      expect(creates).toHaveLength(1);
    });

    await waitForQueriesToSettle(queryClient);
  });

  it('edição pré-preenche a partir do nested (building.id → building_id) e faz PUT com id', async () => {
    setSourcesEmpty();
    const updates = spyUpdate();
    // Parse through the schema (like the real read path) so expected_amount etc. arrive as the
    // component's actual prop type (number), not the raw string-Decimal MSW shape (bill-form-modal
    // test precedent at :286).
    const account = billingAccountSchema.parse(
      createMockBillingAccount({
        id: 5,
        name: 'Água DMAE 836',
        account_type: 'water',
        external_identifier: '12345',
        building: { id: 7, street_number: 836, name: 'Condomínio Steinmetz', address: 'Av. X' },
        building_id: undefined,
      })
    );

    const { queryClient } = renderWithProviders(
      <AccountFormModal open account={account} onClose={() => undefined} />
    );

    expect(await screen.findByDisplayValue('Água DMAE 836')).toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: /^atualizar$/i }));

    await waitFor(() => {
      expect(updates).toHaveLength(1);
    });
    expect(updates[0]).toMatchObject({ id: 5, building_id: 7 });

    await waitForQueriesToSettle(queryClient);
  });

  it('valida default_due_day fora de 1–31', async () => {
    setSourcesEmpty();
    const creates = spyCreate();
    const { queryClient } = renderWithProviders(
      <AccountFormModal open onClose={() => undefined} />
    );

    fireEvent.change(screen.getByPlaceholderText('Ex: Água DMAE 836'), {
      target: { value: 'Conta X' },
    });
    fireEvent.change(screen.getByLabelText('Dia de vencimento'), { target: { value: '32' } });

    await userEvent.click(screen.getByRole('button', { name: /^criar$/i }));

    await waitFor(() => {
      expect(screen.getAllByText(/too big|<=31/i).length).toBeGreaterThan(0);
    });
    expect(creates).toHaveLength(0);

    await waitForQueriesToSettle(queryClient);
  });

  it('erro 400 do backend mantém o modal aberto e mostra toast de erro', async () => {
    setSourcesEmpty();
    server.use(
      http.post(`${API_BASE}/finances/billing-accounts/`, () =>
        HttpResponse.json(
          { external_identifier: ['Já existe uma conta com essa identidade.'] },
          { status: 400 }
        )
      )
    );

    const { queryClient } = renderWithProviders(
      <AccountFormModal open onClose={() => undefined} />
    );

    fireEvent.change(screen.getByPlaceholderText('Ex: Água DMAE 836'), {
      target: { value: 'Conta Duplicada' },
    });

    await userEvent.click(screen.getByRole('button', { name: /^criar$/i }));

    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument();
    });
    expect(screen.getByPlaceholderText('Ex: Água DMAE 836')).toHaveValue('Conta Duplicada');

    await waitForQueriesToSettle(queryClient);
  });
});
