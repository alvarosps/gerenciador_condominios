/**
 * Tests for DeleteConfirmDialog offline gating.
 *
 * Drives the real component and only manipulates the browser boundary
 * (navigator.onLine). Offline access is read-only, so destructive actions must
 * be disabled while offline.
 */

import { describe, it, expect, afterEach, vi } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';
import { DeleteConfirmDialog } from '../delete-confirm-dialog';

function setOnLine(value: boolean): void {
  Object.defineProperty(navigator, 'onLine', { configurable: true, value });
}

afterEach(() => {
  cleanup();
  setOnLine(true);
});

describe('DeleteConfirmDialog offline gating', () => {
  it('enables the delete action and shows no warning when online', () => {
    setOnLine(true);

    render(
      <DeleteConfirmDialog open onOpenChange={() => undefined} itemName="Item X" onConfirm={vi.fn()} />
    );

    expect(screen.getByRole('button', { name: 'Excluir' })).toBeEnabled();
    expect(screen.queryByText(/Indisponível offline/i)).toBeNull();
  });

  it('disables the delete action and warns when offline', () => {
    setOnLine(false);

    render(
      <DeleteConfirmDialog open onOpenChange={() => undefined} itemName="Item X" onConfirm={vi.fn()} />
    );

    expect(screen.getByRole('button', { name: 'Excluir' })).toBeDisabled();
    expect(screen.getByText(/Indisponível offline/i)).toBeInTheDocument();
  });
});
