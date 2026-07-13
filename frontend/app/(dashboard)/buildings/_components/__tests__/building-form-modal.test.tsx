import { describe, it, expect, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { renderWithProviders } from '@/tests/test-utils';
import { server } from '@/tests/mocks/server';
import { BuildingFormModal } from '../building-form-modal';

const API_BASE = 'http://localhost:8008/api';

// useCreateBuilding/useUpdateBuilding are mutation-only hooks (no GET fires on mount) — the real
// hooks hit MSW, no hook is mocked.
function spyCreateBuilding() {
  const calls: Record<string, unknown>[] = [];
  server.use(
    http.post(`${API_BASE}/buildings/`, async ({ request }) => {
      const body = (await request.json()) as Record<string, unknown>;
      calls.push(body);
      return HttpResponse.json({ id: 10, ...body }, { status: 201 });
    })
  );
  return calls;
}

describe('BuildingFormModal', () => {
  const defaultProps = { open: true, onClose: () => undefined };

  beforeEach(() => {
    spyCreateBuilding();
  });

  it('renders dialog when open', () => {
    renderWithProviders(<BuildingFormModal {...defaultProps} />);
    expect(screen.getByRole('dialog')).toBeInTheDocument();
  });

  it('does not render dialog when closed', () => {
    renderWithProviders(<BuildingFormModal {...defaultProps} open={false} />);
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('shows "Novo Prédio" title when creating', () => {
    renderWithProviders(<BuildingFormModal {...defaultProps} />);
    expect(screen.getByText('Novo Prédio')).toBeInTheDocument();
  });

  it('shows "Editar Prédio" title when editing', () => {
    const building = {
      id: 1,
      name: 'Prédio Central',
      street_number: 836,
      address: 'Rua das Flores, 836',
    };
    renderWithProviders(<BuildingFormModal {...defaultProps} building={building} />);
    expect(screen.getByText('Editar Prédio')).toBeInTheDocument();
  });

  it('renders all required form fields', () => {
    renderWithProviders(<BuildingFormModal {...defaultProps} />);
    expect(screen.getByText('Número da Rua *')).toBeInTheDocument();
    expect(screen.getByText('Nome do Prédio *')).toBeInTheDocument();
    expect(screen.getByText('Endereço Completo *')).toBeInTheDocument();
  });

  it('renders cancel and submit buttons', () => {
    renderWithProviders(<BuildingFormModal {...defaultProps} />);
    expect(screen.getByRole('button', { name: /cancelar/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /criar/i })).toBeInTheDocument();
  });

  it('shows "Atualizar" button when editing', () => {
    const building = {
      id: 1,
      name: 'Prédio Central',
      street_number: 836,
      address: 'Rua das Flores, 836',
    };
    renderWithProviders(<BuildingFormModal {...defaultProps} building={building} />);
    expect(screen.getByRole('button', { name: /atualizar/i })).toBeInTheDocument();
  });

  it('pre-fills form fields when editing', () => {
    const building = {
      id: 1,
      name: 'Prédio Central',
      street_number: 836,
      address: 'Rua das Flores, 836',
    };
    renderWithProviders(<BuildingFormModal {...defaultProps} building={building} />);
    expect(screen.getByDisplayValue('Prédio Central')).toBeInTheDocument();
    expect(screen.getByDisplayValue('836')).toBeInTheDocument();
  });

  it('calls onClose when cancel button is clicked', async () => {
    let closed = false;
    const onClose = () => {
      closed = true;
    };
    renderWithProviders(<BuildingFormModal open={true} onClose={onClose} />);
    screen.getByRole('button', { name: /cancelar/i }).click();
    await waitFor(() => expect(closed).toBe(true));
  });
});
