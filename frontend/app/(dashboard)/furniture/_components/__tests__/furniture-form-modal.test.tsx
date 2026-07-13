import { describe, it, expect, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { renderWithProviders } from '@/tests/test-utils';
import { server } from '@/tests/mocks/server';
import { FurnitureFormModal } from '../furniture-form-modal';

const API_BASE = 'http://localhost:8008/api';

// useCreateFurniture/useUpdateFurniture are mutation-only hooks (no GET fires on mount) — the real
// hooks hit MSW, no hook is mocked.
function spyCreateFurniture() {
  const calls: Record<string, unknown>[] = [];
  server.use(
    http.post(`${API_BASE}/furnitures/`, async ({ request }) => {
      const body = (await request.json()) as Record<string, unknown>;
      calls.push(body);
      return HttpResponse.json({ id: 10, ...body }, { status: 201 });
    })
  );
  return calls;
}

describe('FurnitureFormModal', () => {
  const defaultProps = { open: true, onClose: () => undefined };

  beforeEach(() => {
    spyCreateFurniture();
  });

  it('renders dialog when open', () => {
    renderWithProviders(<FurnitureFormModal {...defaultProps} />);
    expect(screen.getByRole('dialog')).toBeInTheDocument();
  });

  it('does not render dialog when closed', () => {
    renderWithProviders(<FurnitureFormModal {...defaultProps} open={false} />);
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('shows "Novo Móvel" title when creating', () => {
    renderWithProviders(<FurnitureFormModal {...defaultProps} />);
    expect(screen.getByText('Novo Móvel')).toBeInTheDocument();
  });

  it('shows "Editar Móvel" title when editing', () => {
    const furniture = { id: 1, name: 'Sofá' };
    renderWithProviders(<FurnitureFormModal {...defaultProps} furniture={furniture} />);
    expect(screen.getByText('Editar Móvel')).toBeInTheDocument();
  });

  it('renders name input field', () => {
    renderWithProviders(<FurnitureFormModal {...defaultProps} />);
    expect(screen.getByText('Nome do Móvel *')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Ex: Sofá, Cama, Mesa')).toBeInTheDocument();
  });

  it('renders cancel and submit buttons', () => {
    renderWithProviders(<FurnitureFormModal {...defaultProps} />);
    expect(screen.getByRole('button', { name: /cancelar/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /criar/i })).toBeInTheDocument();
  });

  it('shows "Atualizar" button when editing', () => {
    const furniture = { id: 1, name: 'Sofá' };
    renderWithProviders(<FurnitureFormModal {...defaultProps} furniture={furniture} />);
    expect(screen.getByRole('button', { name: /atualizar/i })).toBeInTheDocument();
  });

  it('pre-fills name field when editing', () => {
    const furniture = { id: 1, name: 'Sofá de Couro' };
    renderWithProviders(<FurnitureFormModal {...defaultProps} furniture={furniture} />);
    expect(screen.getByDisplayValue('Sofá de Couro')).toBeInTheDocument();
  });

  it('calls onClose when cancel button is clicked', async () => {
    let closed = false;
    const onClose = () => {
      closed = true;
    };
    renderWithProviders(<FurnitureFormModal open={true} onClose={onClose} />);
    screen.getByRole('button', { name: /cancelar/i }).click();
    await waitFor(() => expect(closed).toBe(true));
  });
});
