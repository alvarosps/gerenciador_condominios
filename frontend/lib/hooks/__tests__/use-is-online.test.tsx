/**
 * Tests for useIsOnline.
 *
 * Drives the real hook and only manipulates browser boundaries:
 * navigator.onLine and the window online/offline events.
 */

import { describe, it, expect, afterEach, vi } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useIsOnline } from '../use-is-online';

function setOnLine(value: boolean): void {
  Object.defineProperty(navigator, 'onLine', { configurable: true, value });
}

afterEach(() => {
  setOnLine(true);
});

describe('useIsOnline', () => {
  it('reflects navigator.onLine at mount (offline)', () => {
    setOnLine(false);
    const { result } = renderHook(() => useIsOnline());
    expect(result.current).toBe(false);
  });

  it('reflects navigator.onLine at mount (online)', () => {
    setOnLine(true);
    const { result } = renderHook(() => useIsOnline());
    expect(result.current).toBe(true);
  });

  it('updates on offline and online events', () => {
    setOnLine(true);
    const { result } = renderHook(() => useIsOnline());
    expect(result.current).toBe(true);

    act(() => {
      setOnLine(false);
      window.dispatchEvent(new Event('offline'));
    });
    expect(result.current).toBe(false);

    act(() => {
      setOnLine(true);
      window.dispatchEvent(new Event('online'));
    });
    expect(result.current).toBe(true);
  });

  it('removes its listeners on unmount', () => {
    const removeSpy = vi.spyOn(window, 'removeEventListener');
    const { unmount } = renderHook(() => useIsOnline());
    unmount();

    expect(removeSpy).toHaveBeenCalledWith('online', expect.any(Function));
    expect(removeSpy).toHaveBeenCalledWith('offline', expect.any(Function));
    removeSpy.mockRestore();
  });
});
