import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { downloadBlob } from '../download';

describe('downloadBlob', () => {
  const createObjectURL = vi.fn(() => 'blob:mock-object-url');
  const revokeObjectURL = vi.fn();

  beforeEach(() => {
    createObjectURL.mockClear();
    revokeObjectURL.mockClear();
    URL.createObjectURL = createObjectURL;
    URL.revokeObjectURL = revokeObjectURL;
  });

  afterEach(() => {
    vi.restoreAllMocks();
    delete (URL as { createObjectURL?: unknown }).createObjectURL;
    delete (URL as { revokeObjectURL?: unknown }).revokeObjectURL;
  });

  it('creates an object URL, clicks an anchor with the filename, and revokes the URL', () => {
    const clicked: { href: string; download: string }[] = [];
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(function (
      this: HTMLAnchorElement
    ) {
      clicked.push({ href: this.href, download: this.download });
    });

    const blob = new Blob([new Uint8Array([1, 2, 3])], { type: 'application/pdf' });
    downloadBlob(blob, 'contrato_apto_101.pdf');

    expect(createObjectURL).toHaveBeenCalledWith(blob);
    expect(clicked).toHaveLength(1);
    expect(clicked[0]?.download).toBe('contrato_apto_101.pdf');
    expect(clicked[0]?.href).toContain('blob:mock-object-url');
    expect(revokeObjectURL).toHaveBeenCalledWith('blob:mock-object-url');
  });
});
