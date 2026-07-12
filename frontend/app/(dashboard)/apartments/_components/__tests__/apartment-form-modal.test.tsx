import { describe, it, expect, beforeEach } from 'vitest';
import { http, HttpResponse } from 'msw';
import { screen, fireEvent, waitFor } from '@testing-library/react';
import { renderWithProviders, waitForQueriesToSettle } from '@/tests/test-utils';
import { server } from '@/tests/mocks/server';
import { useAuthStore } from '@/store/auth-store';
import { ApartmentFormModal } from '../apartment-form-modal';
import type { Apartment } from '@/lib/schemas/apartment.schema';

const API_BASE = 'http://localhost:8008/api';

function submitForm() {
  // Radix Dialog portals its content to document.body, so query via the dialog.
  const form = screen.getByRole('dialog').querySelector('form');
  if (!form) throw new Error('form not found');
  fireEvent.submit(form);
}

function setIsStaff(isStaff: boolean) {
  useAuthStore.setState({
    user: { id: 1, email: 'a@b.c', first_name: 'A', last_name: 'B', is_staff: isStaff },
    isAuthenticated: true,
  });
}

// useBuildings / useFurniture / usePersons fire real GETs on mount; overridden per-test so the
// modal sees the exact fixture data the original spy-based test relied on.
function seedLookups() {
  server.use(
    http.get(`${API_BASE}/buildings/`, () =>
      HttpResponse.json([
        { id: 1, name: 'Prédio Central', street_number: 836, address: 'Rua das Flores, 836' },
      ])
    ),
    http.get(`${API_BASE}/furnitures/`, () =>
      HttpResponse.json([
        { id: 1, name: 'Sofá' },
        { id: 2, name: 'Cama' },
      ])
    ),
    http.get(`${API_BASE}/persons/`, () =>
      HttpResponse.json([
        { id: 2, name: 'Tiago', relationship: 'Filho', is_owner: false, is_employee: false },
        { id: 3, name: 'Alvaro', relationship: 'Proprietário', is_owner: true, is_employee: false },
      ])
    )
  );
}

function spyUpdateApartment() {
  const calls: Record<string, unknown>[] = [];
  server.use(
    http.put(`${API_BASE}/apartments/:id/`, async ({ params, request }) => {
      const body = (await request.json()) as Record<string, unknown>;
      calls.push(body);
      return HttpResponse.json({ id: Number(params.id), ...body });
    })
  );
  return calls;
}

const editableApartment: Apartment = {
  id: 1,
  number: 101,
  rental_value: 1200,
  rental_value_double: null,
  cleaning_fee: 200,
  max_tenants: 1,
  is_rented: false,
  building: { id: 1, name: 'Prédio Central', street_number: 836, address: 'Rua das Flores, 836' },
  furnitures: [],
  owner: null,
};

describe('ApartmentFormModal', () => {
  const defaultProps = { open: true, onClose: () => undefined };

  beforeEach(() => {
    seedLookups();
    setIsStaff(true);
  });

  it('renders dialog when open', async () => {
    const { queryClient } = renderWithProviders(<ApartmentFormModal {...defaultProps} />);
    expect(await screen.findByRole('dialog')).toBeInTheDocument();
    await waitForQueriesToSettle(queryClient);
  });

  it('does not render dialog when closed', async () => {
    const { queryClient } = renderWithProviders(
      <ApartmentFormModal {...defaultProps} open={false} />
    );
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    await waitForQueriesToSettle(queryClient);
  });

  it('shows "Novo Apartamento" title when creating', async () => {
    const { queryClient } = renderWithProviders(<ApartmentFormModal {...defaultProps} />);
    expect(await screen.findByText('Novo Apartamento')).toBeInTheDocument();
    await waitForQueriesToSettle(queryClient);
  });

  it('shows "Editar Apartamento" title when editing', async () => {
    const { queryClient } = renderWithProviders(
      <ApartmentFormModal {...defaultProps} apartment={editableApartment} />
    );
    expect(await screen.findByText('Editar Apartamento')).toBeInTheDocument();
    await waitForQueriesToSettle(queryClient);
  });

  it('renders required form fields', async () => {
    const { queryClient } = renderWithProviders(<ApartmentFormModal {...defaultProps} />);
    expect(await screen.findByText('Prédio *')).toBeInTheDocument();
    expect(screen.getByText('Número do Apartamento *')).toBeInTheDocument();
    expect(screen.getByText('Valor do Aluguel *')).toBeInTheDocument();
    expect(screen.getByText('Taxa de Limpeza *')).toBeInTheDocument();
    expect(screen.getByText('Máximo de Inquilinos *')).toBeInTheDocument();
    await waitForQueriesToSettle(queryClient);
  });

  it('renders furniture checkboxes when furniture data is loaded', async () => {
    const { queryClient } = renderWithProviders(<ApartmentFormModal {...defaultProps} />);
    expect(await screen.findByText('Sofá')).toBeInTheDocument();
    expect(screen.getByText('Cama')).toBeInTheDocument();
    await waitForQueriesToSettle(queryClient);
  });

  it('renders cancel and submit buttons', async () => {
    const { queryClient } = renderWithProviders(<ApartmentFormModal {...defaultProps} />);
    expect(await screen.findByRole('button', { name: /cancelar/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /criar/i })).toBeInTheDocument();
    await waitForQueriesToSettle(queryClient);
  });

  it('calls onClose when cancel button is clicked', async () => {
    let closed = false;
    const onClose = () => {
      closed = true;
    };
    const { queryClient } = renderWithProviders(
      <ApartmentFormModal open={true} onClose={onClose} />
    );
    fireEvent.click(await screen.findByRole('button', { name: /cancelar/i }));
    await waitFor(() => expect(closed).toBe(true));
    await waitForQueriesToSettle(queryClient);
  });

  // --- Session 35: owner field (is_staff gated) ---

  it('renders the owner field for admin (is_staff)', async () => {
    setIsStaff(true);
    const { queryClient } = renderWithProviders(<ApartmentFormModal {...defaultProps} />);
    expect(await screen.findByText('Proprietário')).toBeInTheDocument();
    await waitForQueriesToSettle(queryClient);
  });

  it('hides the owner field for non-admin', async () => {
    setIsStaff(false);
    const { queryClient } = renderWithProviders(<ApartmentFormModal {...defaultProps} />);
    await screen.findByRole('dialog');
    expect(screen.queryByText('Proprietário')).not.toBeInTheDocument();
    await waitForQueriesToSettle(queryClient);
  });

  it('submits a numeric owner_id when the apartment has an owner', async () => {
    setIsStaff(true);
    const calls = spyUpdateApartment();
    const { queryClient } = renderWithProviders(
      <ApartmentFormModal
        {...defaultProps}
        apartment={{ ...editableApartment, owner: { id: 2, name: 'Tiago' } }}
      />
    );
    await screen.findByText('Editar Apartamento');
    submitForm();
    await waitFor(() => expect(calls).toHaveLength(1));
    expect(calls[0]).toMatchObject({ owner_id: 2 });
    await waitForQueriesToSettle(queryClient);
  });

  it('submits owner_id null when the apartment belongs to the condominium', async () => {
    setIsStaff(true);
    const calls = spyUpdateApartment();
    const { queryClient } = renderWithProviders(
      <ApartmentFormModal {...defaultProps} apartment={{ ...editableApartment, owner: null }} />
    );
    await screen.findByText('Editar Apartamento');
    submitForm();
    await waitFor(() => expect(calls).toHaveLength(1));
    expect(calls[0]).toMatchObject({ owner_id: null });
    await waitForQueriesToSettle(queryClient);
  });
});
