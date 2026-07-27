import { describe, it, expect, vi, beforeAll, beforeEach } from 'vitest';
import { http, HttpResponse } from 'msw';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { toast } from 'sonner';
import { renderWithProviders, waitForQueriesToSettle } from '@/tests/test-utils';
import { server } from '@/tests/mocks/server';
import { useAuthStore } from '@/store/auth-store';
import {
  createMockThirdPartyPerson,
  createMockThirdPartySettlement,
} from '@/tests/mocks/data/finances';
import ThirdPartyPage from '../page';

// Real hooks hit MSW — no internal hook is ever vi.mock'ed (house rule, P6.1). The real auth
// store drives admin gating; `toast` is the global sonner mock from tests/setup.ts.
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

function setPeopleResponse(people: unknown[]) {
  server.use(http.get(`${API_BASE}/finances/third-party/people/`, () => HttpResponse.json(people)));
}

function setAdmin(isStaff: boolean) {
  useAuthStore.setState({
    user: { id: 1, email: 'a@b.c', first_name: 'A', last_name: 'B', is_staff: isStaff },
    isAuthenticated: true,
  });
}

const PERSON_OPTIONS = [
  {
    id: 1,
    name: 'Alvaro',
    relationship: 'Filho',
    phone: '',
    email: '',
    is_owner: false,
    is_employee: false,
    notes: '',
    credit_cards: [],
  },
];

/** Spy the settlement POST; pushes each request body and returns a parseable settlement. */
function spyCreateSettlement() {
  const bodies: Record<string, unknown>[] = [];
  server.use(
    http.post(`${API_BASE}/finances/third-party-settlements/`, async ({ request }) => {
      bodies.push((await request.json()) as Record<string, unknown>);
      return HttpResponse.json(createMockThirdPartySettlement({ id: 99 }), { status: 201 });
    })
  );
  return bodies;
}

beforeEach(() => {
  vi.mocked(toast.success).mockReset();
  vi.mocked(toast.error).mockReset();
  setAdmin(false);
  server.use(http.get(`${API_BASE}/persons/`, () => HttpResponse.json(PERSON_OPTIONS)));
});

describe('ThirdPartyPage (índice de terceiros)', () => {
  it('lista uma linha por pessoa com devido em aberto, atrasado e último acerto formatados', async () => {
    setPeopleResponse([
      createMockThirdPartyPerson({
        person_id: 1,
        person_name: 'Alvaro',
        total_em_aberto: '450.00',
        total_atrasado: '450.00',
        last_settlement_date: '2026-07-05',
      }),
    ]);

    const { queryClient } = renderWithProviders(<ThirdPartyPage />);

    // DataTable renders a desktop table AND a mobile card view of the same row — every
    // assertion uses the AllBy* variant.
    expect((await screen.findAllByText('Alvaro')).length).toBeGreaterThan(0);
    expect(screen.getAllByText('R$ 450,00').length).toBeGreaterThan(0);
    expect(screen.getAllByText('05/07/2026').length).toBeGreaterThan(0);

    await waitForQueriesToSettle(queryClient);
  });

  it('mostra "—" quando a pessoa nunca teve acerto', async () => {
    setPeopleResponse([
      createMockThirdPartyPerson({
        person_id: 2,
        person_name: 'Tiago',
        last_settlement_date: null,
      }),
    ]);

    const { queryClient } = renderWithProviders(<ThirdPartyPage />);

    await screen.findAllByText('Tiago');
    expect(screen.getAllByText('—').length).toBeGreaterThan(0);

    await waitForQueriesToSettle(queryClient);
  });

  it('a célula do nome é um link para /finances/third-party/{id}', async () => {
    setPeopleResponse([createMockThirdPartyPerson({ person_id: 7, person_name: 'Alvaro' })]);

    const { queryClient } = renderWithProviders(<ThirdPartyPage />);

    const links = await screen.findAllByRole('link', { name: 'Alvaro' });
    expect(links.length).toBeGreaterThan(0);
    links.forEach((link) => expect(link).toHaveAttribute('href', '/finances/third-party/7'));

    await waitForQueriesToSettle(queryClient);
  });

  it('mostra empty state PT quando ninguém deve nada', async () => {
    setPeopleResponse([]);

    const { queryClient } = renderWithProviders(<ThirdPartyPage />);

    expect(await screen.findByText('Nenhuma dívida com terceiros')).toBeInTheDocument();

    await waitForQueriesToSettle(queryClient);
  });

  it('esconde "Registrar acerto" para non-admin', async () => {
    setAdmin(false);
    setPeopleResponse([createMockThirdPartyPerson()]);

    const { queryClient } = renderWithProviders(<ThirdPartyPage />);

    await screen.findAllByText('Alvaro');
    expect(screen.queryByRole('button', { name: /registrar acerto/i })).not.toBeInTheDocument();

    await waitForQueriesToSettle(queryClient);
  });

  it('admin registra acerto pelo modal enviando person_id, data, valor e método', async () => {
    setAdmin(true);
    setPeopleResponse([createMockThirdPartyPerson({ person_id: 1, person_name: 'Alvaro' })]);
    const user = userEvent.setup({ pointerEventsCheck: 0 });
    const bodies = spyCreateSettlement();

    const { queryClient } = renderWithProviders(<ThirdPartyPage />);
    await waitForQueriesToSettle(queryClient);

    await user.click(screen.getByRole('button', { name: /registrar acerto/i }));

    await user.click(await screen.findByLabelText('Pessoa *'));
    await user.click(await screen.findByRole('option', { name: 'Alvaro' }));

    await user.clear(screen.getByLabelText('Valor *'));
    await user.type(screen.getByLabelText('Valor *'), '120');
    await user.type(screen.getByLabelText('Método'), 'PIX');

    await user.click(screen.getByRole('button', { name: 'Registrar' }));

    await waitFor(() => expect(bodies).toHaveLength(1));
    expect(bodies[0]).toMatchObject({ person_id: 1, amount: '120', method: 'PIX' });
    // The date defaults to today (local ISO) — asserted by shape, not by a frozen value.
    expect(bodies[0]?.settlement_date).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    expect(toast.success).toHaveBeenCalledWith('Acerto registrado com sucesso');
  });

  it('erro da API vira toast em PT com a mensagem do backend', async () => {
    setAdmin(true);
    setPeopleResponse([createMockThirdPartyPerson({ person_id: 1, person_name: 'Alvaro' })]);
    const user = userEvent.setup({ pointerEventsCheck: 0 });
    server.use(
      http.post(`${API_BASE}/finances/third-party-settlements/`, () =>
        HttpResponse.json(
          { detail: 'Este mês está fechado e não aceita lançamentos.' },
          { status: 400 }
        )
      )
    );

    const { queryClient } = renderWithProviders(<ThirdPartyPage />);
    await waitForQueriesToSettle(queryClient);

    await user.click(screen.getByRole('button', { name: /registrar acerto/i }));
    await user.click(await screen.findByLabelText('Pessoa *'));
    await user.click(await screen.findByRole('option', { name: 'Alvaro' }));
    await user.clear(screen.getByLabelText('Valor *'));
    await user.type(screen.getByLabelText('Valor *'), '120');
    await user.click(screen.getByRole('button', { name: 'Registrar' }));

    await waitFor(() =>
      expect(toast.error).toHaveBeenCalledWith('Este mês está fechado e não aceita lançamentos.')
    );
  });

  it('rejeita valor não positivo em PT sem chamar a API', async () => {
    setAdmin(true);
    setPeopleResponse([createMockThirdPartyPerson({ person_id: 1, person_name: 'Alvaro' })]);
    const user = userEvent.setup({ pointerEventsCheck: 0 });
    const bodies = spyCreateSettlement();

    const { queryClient } = renderWithProviders(<ThirdPartyPage />);
    await waitForQueriesToSettle(queryClient);

    await user.click(screen.getByRole('button', { name: /registrar acerto/i }));
    await user.click(await screen.findByLabelText('Pessoa *'));
    await user.click(await screen.findByRole('option', { name: 'Alvaro' }));
    await user.clear(screen.getByLabelText('Valor *'));
    await user.type(screen.getByLabelText('Valor *'), '0');
    await user.click(screen.getByRole('button', { name: 'Registrar' }));

    expect(await screen.findByText('O valor do acerto deve ser positivo')).toBeInTheDocument();
    expect(bodies).toHaveLength(0);
  });

  it('exige a pessoa: submeter sem escolher ninguém não chama a API', async () => {
    setAdmin(true);
    setPeopleResponse([createMockThirdPartyPerson({ person_id: 1, person_name: 'Alvaro' })]);
    const user = userEvent.setup({ pointerEventsCheck: 0 });
    const bodies = spyCreateSettlement();

    const { queryClient } = renderWithProviders(<ThirdPartyPage />);
    await waitForQueriesToSettle(queryClient);

    await user.click(screen.getByRole('button', { name: /registrar acerto/i }));
    await user.clear(await screen.findByLabelText('Valor *'));
    await user.type(screen.getByLabelText('Valor *'), '120');
    await user.click(screen.getByRole('button', { name: 'Registrar' }));

    expect(await screen.findByText('Pessoa é obrigatória')).toBeInTheDocument();
    expect(bodies).toHaveLength(0);
  });
});
