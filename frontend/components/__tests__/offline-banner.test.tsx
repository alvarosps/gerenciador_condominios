/**
 * Tests for OfflineBanner.
 *
 * Drives the real component and only manipulates browser boundaries:
 * navigator.onLine and the window online/offline events. No internal app code
 * or component is mocked.
 */

import { describe, it, expect, afterEach, vi } from 'vitest';
import { render, screen, act, cleanup } from '@testing-library/react';
import { OfflineBanner } from '../offline-banner';

const OFFLINE_TEXT = 'Você está offline — exibindo dados salvos';

function setOnLine(value: boolean): void {
  Object.defineProperty(navigator, 'onLine', {
    configurable: true,
    value,
  });
}

afterEach(() => {
  cleanup();
  setOnLine(true);
});

describe('OfflineBanner', () => {
  it('renders nothing when online at mount', () => {
    setOnLine(true);

    render(<OfflineBanner />);

    expect(screen.queryByRole('status')).toBeNull();
    expect(screen.queryByText(OFFLINE_TEXT)).toBeNull();
  });

  it('renders the offline message when offline at mount', () => {
    setOnLine(false);

    render(<OfflineBanner />);

    const banner = screen.getByRole('status');
    expect(banner).toHaveTextContent(OFFLINE_TEXT);
  });

  it('appears on offline event and disappears on online event', () => {
    setOnLine(true);

    render(<OfflineBanner />);
    expect(screen.queryByRole('status')).toBeNull();

    act(() => {
      setOnLine(false);
      window.dispatchEvent(new Event('offline'));
    });

    expect(screen.getByRole('status')).toHaveTextContent(OFFLINE_TEXT);

    act(() => {
      setOnLine(true);
      window.dispatchEvent(new Event('online'));
    });

    expect(screen.queryByRole('status')).toBeNull();
  });

  it('removes its event listeners on unmount', () => {
    setOnLine(true);
    const removeSpy = vi.spyOn(window, 'removeEventListener');

    const { unmount } = render(<OfflineBanner />);
    unmount();

    expect(removeSpy).toHaveBeenCalledWith('online', expect.any(Function));
    expect(removeSpy).toHaveBeenCalledWith('offline', expect.any(Function));

    removeSpy.mockRestore();
  });
});
