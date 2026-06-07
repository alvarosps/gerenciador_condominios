import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { screen, fireEvent, waitFor } from '@testing-library/react';
import { renderWithProviders } from '@/tests/test-utils';
import { ApartmentFormModal } from '../apartment-form-modal';
import * as apartmentHooks from '@/lib/api/hooks/use-apartments';
import * as buildingHooks from '@/lib/api/hooks/use-buildings';
import * as furnitureHooks from '@/lib/api/hooks/use-furniture';
import * as personHooks from '@/lib/api/hooks/use-persons';
import * as authStore from '@/store/auth-store';

function submitForm() {
  // Radix Dialog portals its content to document.body, so query via the dialog.
  const form = screen.getByRole('dialog').querySelector('form');
  if (!form) throw new Error('form not found');
  fireEvent.submit(form);
}

vi.mock('@/lib/api/hooks/use-apartments', async (importOriginal) => {
  const actual = await importOriginal<typeof apartmentHooks>();
  return {
    ...actual,
    useCreateApartment: vi.fn(),
    useUpdateApartment: vi.fn(),
    useAvailableApartments: vi.fn(),
  };
});

vi.mock('@/lib/api/hooks/use-buildings', async (importOriginal) => {
  const actual = await importOriginal<typeof buildingHooks>();
  return { ...actual, useBuildings: vi.fn() };
});

vi.mock('@/lib/api/hooks/use-furniture', async (importOriginal) => {
  const actual = await importOriginal<typeof furnitureHooks>();
  return { ...actual, useFurniture: vi.fn() };
});

vi.mock('@/lib/api/hooks/use-persons', async (importOriginal) => {
  const actual = await importOriginal<typeof personHooks>();
  return { ...actual, usePersons: vi.fn() };
});

vi.mock('@/store/auth-store', () => ({ useAuthStore: vi.fn() }));

const createMutateAsync = vi.fn();
const updateMutateAsync = vi.fn();

function setIsStaff(isStaff: boolean) {
  vi.mocked(authStore.useAuthStore).mockReturnValue({ user: { is_staff: isStaff } } as never);
}

function mockHooks() {
  vi.mocked(apartmentHooks.useCreateApartment).mockReturnValue({
    mutateAsync: createMutateAsync,
    isPending: false,
  } as never);
  vi.mocked(apartmentHooks.useUpdateApartment).mockReturnValue({
    mutateAsync: updateMutateAsync,
    isPending: false,
  } as never);
  vi.mocked(buildingHooks.useBuildings).mockReturnValue({
    data: [{ id: 1, name: 'Prédio Central', street_number: 836, address: 'Rua das Flores, 836' }],
    isLoading: false,
  } as never);
  vi.mocked(furnitureHooks.useFurniture).mockReturnValue({
    data: [{ id: 1, name: 'Sofá' }, { id: 2, name: 'Cama' }],
  } as never);
  vi.mocked(personHooks.usePersons).mockReturnValue({
    data: [
      { id: 2, name: 'Tiago' },
      { id: 3, name: 'Alvaro' },
    ],
  } as never);
  setIsStaff(true);
}

const editableApartment = {
  id: 1,
  number: 101,
  rental_value: 1200,
  rental_value_double: null,
  cleaning_fee: 200,
  max_tenants: 1,
  is_rented: false,
  building: { id: 1, name: 'Prédio Central', street_number: 836, address: 'Rua das Flores, 836' },
  furnitures: [],
  owner: null as { id: number; name: string } | null,
};

describe('ApartmentFormModal', () => {
  const defaultProps = { open: true, onClose: vi.fn() };

  beforeEach(() => {
    vi.clearAllMocks();
    mockHooks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders dialog when open', () => {
    renderWithProviders(<ApartmentFormModal {...defaultProps} />);
    expect(screen.getByRole('dialog')).toBeInTheDocument();
  });

  it('does not render dialog when closed', () => {
    renderWithProviders(<ApartmentFormModal {...defaultProps} open={false} />);
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('shows "Novo Apartamento" title when creating', () => {
    renderWithProviders(<ApartmentFormModal {...defaultProps} />);
    expect(screen.getByText('Novo Apartamento')).toBeInTheDocument();
  });

  it('shows "Editar Apartamento" title when editing', () => {
    renderWithProviders(
      <ApartmentFormModal {...defaultProps} apartment={editableApartment as never} />,
    );
    expect(screen.getByText('Editar Apartamento')).toBeInTheDocument();
  });

  it('renders required form fields', () => {
    renderWithProviders(<ApartmentFormModal {...defaultProps} />);
    expect(screen.getByText('Prédio *')).toBeInTheDocument();
    expect(screen.getByText('Número do Apartamento *')).toBeInTheDocument();
    expect(screen.getByText('Valor do Aluguel *')).toBeInTheDocument();
    expect(screen.getByText('Taxa de Limpeza *')).toBeInTheDocument();
    expect(screen.getByText('Máximo de Inquilinos *')).toBeInTheDocument();
  });

  it('renders furniture checkboxes when furniture data is loaded', () => {
    renderWithProviders(<ApartmentFormModal {...defaultProps} />);
    expect(screen.getByText('Sofá')).toBeInTheDocument();
    expect(screen.getByText('Cama')).toBeInTheDocument();
  });

  it('renders cancel and submit buttons', () => {
    renderWithProviders(<ApartmentFormModal {...defaultProps} />);
    expect(screen.getByRole('button', { name: /cancelar/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /criar/i })).toBeInTheDocument();
  });

  it('calls onClose when cancel button is clicked', () => {
    const onClose = vi.fn();
    const { getByRole } = renderWithProviders(
      <ApartmentFormModal open={true} onClose={onClose} />,
    );
    getByRole('button', { name: /cancelar/i }).click();
    expect(onClose).toHaveBeenCalledOnce();
  });

  // --- Session 35: owner field (is_staff gated) ---

  it('renders the owner field for admin (is_staff)', () => {
    setIsStaff(true);
    renderWithProviders(<ApartmentFormModal {...defaultProps} />);
    expect(screen.getByText('Proprietário')).toBeInTheDocument();
  });

  it('hides the owner field for non-admin', () => {
    setIsStaff(false);
    renderWithProviders(<ApartmentFormModal {...defaultProps} />);
    expect(screen.queryByText('Proprietário')).not.toBeInTheDocument();
  });

  it('submits a numeric owner_id when the apartment has an owner', async () => {
    setIsStaff(true);
    renderWithProviders(
      <ApartmentFormModal
        {...defaultProps}
        apartment={{ ...editableApartment, owner: { id: 2, name: 'Tiago' } } as never}
      />,
    );
    submitForm();
    await waitFor(() => expect(updateMutateAsync).toHaveBeenCalled());
    expect(updateMutateAsync).toHaveBeenCalledWith(expect.objectContaining({ owner_id: 2 }));
  });

  it('submits owner_id null when the apartment belongs to the condominium', async () => {
    setIsStaff(true);
    renderWithProviders(
      <ApartmentFormModal
        {...defaultProps}
        apartment={{ ...editableApartment, owner: null } as never}
      />,
    );
    submitForm();
    await waitFor(() => expect(updateMutateAsync).toHaveBeenCalled());
    expect(updateMutateAsync).toHaveBeenCalledWith(expect.objectContaining({ owner_id: null }));
  });
});
