/**
 * Chart color helpers — resolve to the `--chart-1..5` design tokens (app/globals.css)
 * instead of hardcoded hex, so charts respect dark mode automatically.
 */

const CHART_TOKEN_COUNT = 5;

/** CSS var() reference for a chart token, cycling through 1..5 by index. */
export function chartColor(index: number): string {
  const tokenNumber = (index % CHART_TOKEN_COUNT) + 1;
  return `var(--chart-${tokenNumber})`;
}

/**
 * Mixes any CSS color token (`var(--chart-1)`, `var(--warning)`, ...) with transparent
 * at the given opacity (0-100), for consumers that need a computed value (e.g.
 * alpha-blended fills, gradients) rather than a plain `fill="var(--token)"`.
 */
export function colorMixWithTransparent(colorToken: string, opacityPercent: number): string {
  return `color-mix(in oklch, ${colorToken} ${opacityPercent}%, transparent)`;
}
