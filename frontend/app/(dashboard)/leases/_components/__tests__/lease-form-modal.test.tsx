import { describe, it, expect, beforeEach } from 'vitest';
import { http, HttpResponse } from 'msw';
import { screen, fireEvent, waitFor } from '@testing-library/react';
import { renderWithProviders, waitForQueriesToSettle } from '@/tests/test-utils';
import { server } from '@/tests/mocks/server';
import { useAuthStore } from '@/store/auth-store';
import { LeaseFormModal } from '../lease-form-modal';
import type { Lease } from '@/lib/schemas/lease.schema';

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

// useAvailableApartments / useTenants fire real GETs on mount; overridden per-test so the modal
// sees exactly one available apartment and one tenant, matching the original fixture data.
function seedApartmentsAndTenants() {
  server.use(
    http.get(`${API_BASE}/apartments/`, () =>
      HttpResponse.json([
        {
          id: 1,
          number: 101,
          rental_value: 1200,
          rental_value_double: null,
          cleaning_fee: 200,
          max_tenants: 1,
          is_rented: false,
          building: {
            id: 1,
            name: 'Prédio Central',
            street_number: 836,
            address: 'Rua das Flores',
          },
          furnitures: [],
        },
      ])
    ),
    http.get(`${API_BASE}/tenants/`, () =>
      HttpResponse.json([
        {
          id: 1,
          name: 'João Silva',
          cpf_cnpj: '12345678901',
          due_day: 5,
          dependents: [],
          is_company: false,
          furnitures: [],
        },
      ])
    )
  );
}

function spyUpdateLease() {
  const calls: Record<string, unknown>[] = [];
  server.use(
    http.put(`${API_BASE}/leases/:id/`, async ({ params, request }) => {
      const body = (await request.json()) as Record<string, unknown>;
      calls.push(body);
      return HttpResponse.json({ id: Number(params.id), ...body });
    })
  );
  return calls;
}

const editableLease: Lease = {
  id: 1,
  apartment: {
    id: 1,
    number: 101,
    rental_value: 1200,
    rental_value_double: null,
    cleaning_fee: 200,
    max_tenants: 1,
    is_rented: true,
    building: { id: 1, name: 'Prédio Central', street_number: 836, address: 'Rua das Flores' },
    furnitures: [],
  },
  responsible_tenant: {
    id: 1,
    name: 'João Silva',
    cpf_cnpj: '12345678901',
    due_day: 5,
    phone: '(11) 99999-0000',
    is_company: false,
    furnitures: [],
    dependents: [],
  },
  tenants: [],
  number_of_tenants: 1,
  rental_value: 1200,
  deposit_amount: null,
  start_date: '2024-01-01',
  validity_months: 12,
  tag_fee: 20,
  cleaning_fee_paid: false,
  tag_deposit_paid: false,
  contract_generated: false,
  prepaid_until: null,
  is_salary_offset: false,
};

describe('LeaseFormModal', () => {
  const defaultProps = { open: true, onClose: () => undefined };

  beforeEach(() => {
    seedApartmentsAndTenants();
    setIsStaff(true);
  });

  it('renders dialog when open', async () => {
    const { queryClient } = renderWithProviders(<LeaseFormModal {...defaultProps} />);
    expect(await screen.findByRole('dialog')).toBeInTheDocument();
    await waitForQueriesToSettle(queryClient);
  });

  it('does not render dialog when closed', async () => {
    const { queryClient } = renderWithProviders(<LeaseFormModal {...defaultProps} open={false} />);
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    await waitForQueriesToSettle(queryClient);
  });

  it('shows "Nova Locação" title when creating', async () => {
    const { queryClient } = renderWithProviders(<LeaseFormModal {...defaultProps} />);
    expect(await screen.findByText('Nova Locação')).toBeInTheDocument();
    await waitForQueriesToSettle(queryClient);
  });

  it('shows "Editar Locação" title when editing', async () => {
    const { queryClient } = renderWithProviders(
      <LeaseFormModal {...defaultProps} lease={editableLease} />
    );
    expect(await screen.findByText('Editar Locação')).toBeInTheDocument();
    await waitForQueriesToSettle(queryClient);
  });

  it('renders apartment and tenant select fields', async () => {
    const { queryClient } = renderWithProviders(<LeaseFormModal {...defaultProps} />);
    expect(await screen.findByText('Apartamento')).toBeInTheDocument();
    expect(screen.getByText('Inquilino Responsável')).toBeInTheDocument();
    await waitForQueriesToSettle(queryClient);
  });

  it('renders period and value fields', async () => {
    const { queryClient } = renderWithProviders(<LeaseFormModal {...defaultProps} />);
    expect(await screen.findByText('Data de Início')).toBeInTheDocument();
    expect(screen.getByText('Validade (meses)')).toBeInTheDocument();
    expect(screen.getByText('Taxa de Tag')).toBeInTheDocument();
    expect(screen.getByText('Valor do Aluguel')).toBeInTheDocument();
    await waitForQueriesToSettle(queryClient);
  });

  it('renders payment confirmation checkboxes', async () => {
    const { queryClient } = renderWithProviders(<LeaseFormModal {...defaultProps} />);
    expect(await screen.findByText('Taxa de Limpeza Paga')).toBeInTheDocument();
    expect(screen.getByText('Taxa de Tag Paga')).toBeInTheDocument();
    await waitForQueriesToSettle(queryClient);
  });

  it('renders cancel and submit buttons', async () => {
    const { queryClient } = renderWithProviders(<LeaseFormModal {...defaultProps} />);
    expect(await screen.findByRole('button', { name: /cancelar/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /criar/i })).toBeInTheDocument();
    await waitForQueriesToSettle(queryClient);
  });

  it('calls onClose when cancel button is clicked', async () => {
    let closed = false;
    const onClose = () => {
      closed = true;
    };
    const { queryClient } = renderWithProviders(<LeaseFormModal open={true} onClose={onClose} />);
    fireEvent.click(await screen.findByRole('button', { name: /cancelar/i }));
    await waitFor(() => expect(closed).toBe(true));
    await waitForQueriesToSettle(queryClient);
  });

  // --- Session 35: prepaid_until + is_salary_offset (is_staff gated) ---

  it('renders the prepaid/salary-offset fields for admin (is_staff)', async () => {
    setIsStaff(true);
    const { queryClient } = renderWithProviders(<LeaseFormModal {...defaultProps} />);
    expect(await screen.findByText('Aluguel compensado por salário')).toBeInTheDocument();
    expect(screen.getByText('Pré-pago até')).toBeInTheDocument();
    await waitForQueriesToSettle(queryClient);
  });

  it('hides the prepaid/salary-offset fields for non-admin', async () => {
    setIsStaff(false);
    const { queryClient } = renderWithProviders(<LeaseFormModal {...defaultProps} />);
    await screen.findByRole('dialog');
    expect(screen.queryByText('Aluguel compensado por salário')).not.toBeInTheDocument();
    expect(screen.queryByText('Pré-pago até')).not.toBeInTheDocument();
    await waitForQueriesToSettle(queryClient);
  });

  it('pre-fills prepaid_until when editing', async () => {
    setIsStaff(true);
    const { queryClient } = renderWithProviders(
      <LeaseFormModal
        {...defaultProps}
        lease={{ ...editableLease, prepaid_until: '2026-07-01', is_salary_offset: true }}
      />
    );
    expect(await screen.findByDisplayValue('2026-07-01')).toBeInTheDocument();
    await waitForQueriesToSettle(queryClient);
  });

  it('submits prepaid_until and is_salary_offset on update', async () => {
    setIsStaff(true);
    const calls = spyUpdateLease();
    const { queryClient } = renderWithProviders(
      <LeaseFormModal
        {...defaultProps}
        lease={{ ...editableLease, prepaid_until: '2026-07-01', is_salary_offset: true }}
      />
    );
    await screen.findByDisplayValue('2026-07-01');
    submitForm();
    await waitFor(() => expect(calls).toHaveLength(1));
    expect(calls[0]).toMatchObject({ prepaid_until: '2026-07-01', is_salary_offset: true });
    await waitForQueriesToSettle(queryClient);
  });

  it('clears prepaid_until to null when the date input is emptied', async () => {
    setIsStaff(true);
    const calls = spyUpdateLease();
    const { queryClient } = renderWithProviders(
      <LeaseFormModal {...defaultProps} lease={{ ...editableLease, prepaid_until: '2026-07-01' }} />
    );
    const dateInput = await screen.findByDisplayValue('2026-07-01');
    fireEvent.change(dateInput, { target: { value: '' } });
    submitForm();
    await waitFor(() => expect(calls).toHaveLength(1));
    expect(calls[0]).toMatchObject({ prepaid_until: null });
    await waitForQueriesToSettle(queryClient);
  });
});
