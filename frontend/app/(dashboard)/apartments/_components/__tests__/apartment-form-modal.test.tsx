import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { screen } from '@testing-library/react';
import { renderWithProviders } from '@/tests/test-utils';
import { ApartmentFormModal } from '../apartment-form-modal';
import * as apartmentHooks from '@/lib/api/hooks/use-apartments';
import * as buildingHooks from '@/lib/api/hooks/use-buildings';
import * as furnitureHooks from '@/lib/api/hooks/use-furniture';

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

const idleMutation = { mutateAsync: vi.fn(), isPending: false };

function mockHooks() {
  vi.mocked(apartmentHooks.useCreateApartment).mockReturnValue(idleMutation as never);
  vi.mocked(apartmentHooks.useUpdateApartment).mockReturnValue(idleMutation as never);
  vi.mocked(buildingHooks.useBuildings).mockReturnValue({
    data: [{ id: 1, name: 'Prédio Central', street_number: 836, address: 'Rua das Flores, 836' }],
    isLoading: false,
  } as never);
  vi.mocked(furnitureHooks.useFurniture).mockReturnValue({
    data: [{ id: 1, name: 'Sofá' }, { id: 2, name: 'Cama' }],
  } as never);
}

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
    const apartment = {
      id: 1,
      number: 101,
      rental_value: 1200,
      cleaning_fee: 200,
      max_tenants: 1,
      is_rented: false,
      building: { id: 1, name: 'Prédio Central', street_number: 836, address: 'Rua das Flores, 836' },
      furnitures: [],
    };
    renderWithProviders(<ApartmentFormModal {...defaultProps} apartment={apartment as never} />);
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

  it('calls onClose when cancel button is clicked', async () => {
    const onClose = vi.fn();
    const { getByRole } = renderWithProviders(
      <ApartmentFormModal open={true} onClose={onClose} />,
    );
    getByRole('button', { name: /cancelar/i }).click();
    expect(onClose).toHaveBeenCalledOnce();
  });
});
