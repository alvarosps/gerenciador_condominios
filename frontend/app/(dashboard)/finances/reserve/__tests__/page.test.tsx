import { describe, it, expect, beforeEach } from 'vitest';
import { http, HttpResponse } from 'msw';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders, waitForQueriesToSettle } from '@/tests/test-utils';
import { server } from '@/tests/mocks/server';
import { useAuthStore } from '@/store/auth-store';
import ReservePage from '../page';
import { createMockReserve } from '@/tests/mocks/data/finances';

const API_BASE = 'http://localhost:8008/api';

// Real hooks (useReserves / useReserveMovements) hit MSW; the real auth store drives staff gating.
function setStaff(isStaff: boolean) {
  useAuthStore.setState({
    user: { id: 1, email: 'a@b.c', first_name: 'A', last_name: 'B', is_staff: isStaff },
    isAuthenticated: true,
  });
}

function setReserves(reserves: unknown[]) {
  server.use(http.get(`${API_BASE}/finances/reserves/`, () => HttpResponse.json(reserves)));
}

describe('ReservePage', () => {
  beforeEach(() => {
    setStaff(false);
  });

  it('renders reserve balance cards and deposit/withdraw buttons for staff', async () => {
    setStaff(true);
    setReserves([createMockReserve({ id: 1, name: 'Emergência', balance: '5000.00' })]);

    const { queryClient } = renderWithProviders(<ReservePage />);

    await waitFor(() => expect(screen.getByText('Emergência')).toBeInTheDocument());
    expect(screen.getByRole('button', { name: /Depositar/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Sacar/i })).toBeInTheDocument();

    await waitForQueriesToSettle(queryClient);
  });

  it('hides deposit/withdraw buttons for non-staff', async () => {
    setStaff(false);
    setReserves([createMockReserve({ id: 1, name: 'Emergência' })]);

    const { queryClient } = renderWithProviders(<ReservePage />);

    await waitFor(() => expect(screen.getByText('Emergência')).toBeInTheDocument());
    expect(screen.queryByRole('button', { name: /Depositar/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Sacar/i })).not.toBeInTheDocument();

    await waitForQueriesToSettle(queryClient);
  });

  it('opens the deposit dialog when the deposit button is clicked', async () => {
    setStaff(true);
    setReserves([createMockReserve({ id: 1, name: 'Fundo' })]);

    const { queryClient } = renderWithProviders(<ReservePage />);

    await waitFor(() =>
      expect(screen.getByRole('button', { name: /Depositar/i })).toBeInTheDocument()
    );
    await userEvent.click(screen.getByRole('button', { name: /Depositar/i }));

    await waitFor(() => expect(screen.getByText(/Depositar em Fundo/i)).toBeInTheDocument());

    await waitForQueriesToSettle(queryClient);
  });

  it('renders the movements table', async () => {
    setStaff(false);
    setReserves([]);

    const { queryClient } = renderWithProviders(<ReservePage />);

    await waitFor(() => expect(screen.getByText('Movimentações')).toBeInTheDocument());

    await waitForQueriesToSettle(queryClient);
  });
});
