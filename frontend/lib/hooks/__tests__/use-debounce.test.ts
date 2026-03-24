import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useDebounce } from '../use-debounce';

describe('useDebounce', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('returns the initial value immediately', () => {
    const { result } = renderHook(() => useDebounce('initial', 500));
    expect(result.current).toBe('initial');
  });

  it('does not update before the delay elapses', () => {
    const { result, rerender } = renderHook(
      ({ value }: { value: string }) => useDebounce(value, 500),
      { initialProps: { value: 'initial' } }
    );

    rerender({ value: 'updated' });

    // Advance time partially — not enough to trigger
    act(() => {
      vi.advanceTimersByTime(300);
    });

    expect(result.current).toBe('initial');
  });

  it('updates after the full delay elapses', () => {
    const { result, rerender } = renderHook(
      ({ value }: { value: string }) => useDebounce(value, 500),
      { initialProps: { value: 'initial' } }
    );

    rerender({ value: 'updated' });

    act(() => {
      vi.advanceTimersByTime(500);
    });

    expect(result.current).toBe('updated');
  });

  it('resets the timer when value changes before delay elapses', () => {
    const { result, rerender } = renderHook(
      ({ value }: { value: string }) => useDebounce(value, 500),
      { initialProps: { value: 'initial' } }
    );

    rerender({ value: 'first' });

    act(() => {
      vi.advanceTimersByTime(300);
    });

    // Change value again before first delay fires
    rerender({ value: 'second' });

    act(() => {
      vi.advanceTimersByTime(300);
    });

    // Still at initial — the second change has 200ms remaining
    expect(result.current).toBe('initial');

    act(() => {
      vi.advanceTimersByTime(200);
    });

    // Now the second value should be set
    expect(result.current).toBe('second');
  });

  it('uses 500ms as default delay', () => {
    const { result, rerender } = renderHook(
      ({ value }: { value: string }) => useDebounce(value),
      { initialProps: { value: 'a' } }
    );

    rerender({ value: 'b' });

    act(() => {
      vi.advanceTimersByTime(499);
    });
    expect(result.current).toBe('a');

    act(() => {
      vi.advanceTimersByTime(1);
    });
    expect(result.current).toBe('b');
  });

  it('works with numeric values', () => {
    const { result, rerender } = renderHook(
      ({ value }: { value: number }) => useDebounce(value, 300),
      { initialProps: { value: 0 } }
    );

    rerender({ value: 42 });

    act(() => {
      vi.advanceTimersByTime(300);
    });

    expect(result.current).toBe(42);
  });

  it('respects a custom delay', () => {
    const { result, rerender } = renderHook(
      ({ value }: { value: string }) => useDebounce(value, 1000),
      { initialProps: { value: 'a' } }
    );

    rerender({ value: 'b' });

    act(() => {
      vi.advanceTimersByTime(999);
    });
    expect(result.current).toBe('a');

    act(() => {
      vi.advanceTimersByTime(1);
    });
    expect(result.current).toBe('b');
  });
});
