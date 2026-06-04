import { describe, it, expect } from 'vitest';
import { viewport } from '@/app/layout';

describe('layout viewport', () => {
  it('exports a defined viewport object', () => {
    expect(viewport).toBeDefined();
  });

  it('sets width to device-width', () => {
    expect(viewport.width).toBe('device-width');
  });

  it('sets initialScale to 1', () => {
    expect(viewport.initialScale).toBe(1);
  });

  it('sets viewportFit to cover', () => {
    expect(viewport.viewportFit).toBe('cover');
  });

  it('declares the teal themeColor (added in Session 28)', () => {
    expect(viewport.themeColor).toEqual([
      { media: '(prefers-color-scheme: light)', color: '#0d847a' },
      { media: '(prefers-color-scheme: dark)', color: '#0d847a' },
    ]);
  });
});
