/**
 * Trigger a browser download for an in-memory Blob.
 *
 * Creates a temporary object URL, clicks a synthetic anchor, then revokes the URL.
 * Used for authenticated file downloads fetched via the same-origin API proxy (so the
 * request carries the HttpOnly auth cookies), instead of navigating to a backend URL.
 */
export function downloadBlob(blob: Blob, filename: string): void {
  const objectUrl = URL.createObjectURL(blob);
  try {
    const anchor = document.createElement('a');
    anchor.href = objectUrl;
    anchor.download = filename;
    anchor.rel = 'noopener';
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
  } finally {
    URL.revokeObjectURL(objectUrl);
  }
}
