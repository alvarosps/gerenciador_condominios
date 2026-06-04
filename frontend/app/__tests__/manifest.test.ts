import { describe, it, expect } from 'vitest';
import manifest from '@/app/manifest';

describe('PWA web manifest', () => {
  const result = manifest();

  it('declares the required application fields', () => {
    expect(result.name).toBe('Condomínios Manager');
    expect(result.short_name).toBe('Condomínios');
    expect(result.start_url).toBe('/');
    expect(result.display).toBe('standalone');
    expect(result.lang).toBe('pt-BR');
  });

  it('uses the documented theme HEX colors derived from the OKLCH tokens', () => {
    expect(result.theme_color).toBe('#0d847a');
    expect(result.background_color).toBe('#fbfbfc');
  });

  it('declares at least two PNG icons including 192 and a 512 maskable', () => {
    const icons = result.icons ?? [];
    expect(icons.length).toBeGreaterThanOrEqual(2);

    for (const icon of icons) {
      expect(icon.type).toBe('image/png');
      expect(icon.src.startsWith('/icons/')).toBe(true);
    }

    const hasMaskable512 = icons.some(
      (icon) => icon.sizes === '512x512' && icon.purpose === 'maskable',
    );
    expect(hasMaskable512).toBe(true);

    const has192 = icons.some((icon) => icon.sizes === '192x192');
    expect(has192).toBe(true);
  });
});
