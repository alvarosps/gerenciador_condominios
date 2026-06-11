import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { screen, waitFor, fireEvent } from '@testing-library/react';
import { renderWithProviders } from '@/tests/test-utils';
import { ContractGenerateModal } from '../contract-generate-modal';
import { createMockLease } from '@/tests/mocks/data';
import type { Lease } from '@/lib/schemas/lease.schema';

const leaseNotGenerated: Lease = createMockLease({ id: 3, contract_generated: false });

describe('ContractGenerateModal', () => {
  const createObjectURL = vi.fn(() => 'blob:contract-mock');
  const revokeObjectURL = vi.fn();
  let clickedAnchors: { href: string; download: string }[] = [];

  beforeEach(() => {
    clickedAnchors = [];
    createObjectURL.mockClear();
    revokeObjectURL.mockClear();
    // JSDOM/happy-dom's URL lacks object-URL helpers; add real spies without replacing the URL
    // constructor (axios/MSW rely on `new URL(...)` internally).
    URL.createObjectURL = createObjectURL;
    URL.revokeObjectURL = revokeObjectURL;
    // Capture the synthetic download anchor's click without performing a real navigation.
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(function (
      this: HTMLAnchorElement
    ) {
      clickedAnchors.push({ href: this.href, download: this.download });
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
    delete (URL as { createObjectURL?: unknown }).createObjectURL;
    delete (URL as { revokeObjectURL?: unknown }).revokeObjectURL;
  });

  it('generates the contract then downloads via the API blob, never navigating to /download', async () => {
    const openSpy = vi.spyOn(window, 'open').mockImplementation(() => null);

    renderWithProviders(<ContractGenerateModal open lease={leaseNotGenerated} onClose={vi.fn()} />);

    fireEvent.click(screen.getByRole('button', { name: /Gerar Contrato/i }));

    // Success state appears once generate_contract resolves (MSW returns {lease_id, message}).
    const downloadButton = await screen.findByRole('button', { name: /Baixar Contrato/i });

    fireEvent.click(downloadButton);

    await waitFor(() => {
      expect(createObjectURL).toHaveBeenCalled();
    });

    // The download went through the blob path — a synthetic anchor was clicked with the blob URL.
    expect(clickedAnchors).toHaveLength(1);
    expect(clickedAnchors[0]?.href).toContain('blob:contract-mock');
    expect(clickedAnchors[0]?.download).toMatch(/^contrato_apto_/);
    expect(revokeObjectURL).toHaveBeenCalledWith('blob:contract-mock');

    // It must NOT navigate to the old insecure /download redirect.
    const navigatedToDownload = openSpy.mock.calls.some(([url]) =>
      String(url).includes('/download')
    );
    expect(navigatedToDownload).toBe(false);

    openSpy.mockRestore();
  });
});
