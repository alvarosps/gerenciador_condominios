import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { waitFor } from '@testing-library/react';
import { renderWithProviders } from '@/tests/test-utils';
import { ContractViewModal } from '../contract-view-modal';
import { createMockLease } from '@/tests/mocks/data';
import type { Lease } from '@/lib/schemas/lease.schema';

const generatedLease: Lease = createMockLease({ id: 1, contract_generated: true });

describe('ContractViewModal', () => {
  const createObjectURL = vi.fn(() => 'blob:contract-view-mock');
  const revokeObjectURL = vi.fn();

  beforeEach(() => {
    createObjectURL.mockClear();
    revokeObjectURL.mockClear();
    // happy-dom's URL lacks object-URL helpers; add real spies without replacing the URL
    // constructor (axios/MSW rely on `new URL(...)` internally).
    URL.createObjectURL = createObjectURL;
    URL.revokeObjectURL = revokeObjectURL;
  });

  afterEach(() => {
    vi.restoreAllMocks();
    delete (URL as { createObjectURL?: unknown }).createObjectURL;
    delete (URL as { revokeObjectURL?: unknown }).revokeObjectURL;
  });

  it('fetches the PDF via the API and shows it in an iframe using the object URL', async () => {
    const { container } = renderWithProviders(
      <ContractViewModal open lease={generatedLease} onClose={vi.fn()} />
    );

    await waitFor(() => {
      expect(createObjectURL).toHaveBeenCalled();
    });

    const iframe = await waitFor(() => {
      const found = document.querySelector<HTMLIFrameElement>('iframe[title="Contrato PDF"]');
      if (!found) throw new Error('contract iframe not rendered');
      return found;
    });

    // The iframe must use the blob object URL, never an anonymous backend /contracts/ URL.
    expect(iframe.getAttribute('src')).toBe('blob:contract-view-mock');
    expect(iframe.getAttribute('src')).not.toContain('/contracts/');
    expect(container.innerHTML).not.toContain('/contracts/');
  });
});
