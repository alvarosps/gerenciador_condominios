/**
 * Pure helpers for the condominium finance UI (Phase 2).
 *
 * These are display-only previews. The backend (`create_with_lines`) is the authority
 * for `amount_total`; the front never recalculates totals for data that already carries
 * the backend annotation (design §4.4). `computeLineTotal` exists ONLY to preview the
 * subtotal of line items while a bill is being edited in the form.
 */

import { formatMonthYear } from '@/lib/utils/formatters';

export interface LineTotalInput {
  amount: number;
  is_offset?: boolean;
}

/**
 * Format a `reference_month` (`YYYY-MM-01`) as "Junho de 2026".
 *
 * Parses by split (never `new Date(iso)` — timezone-safe) and delegates to `formatMonthYear`.
 * Shared by the month-close page and its action dialog (single source).
 */
export function formatReferenceMonth(referenceMonth: string): string {
  const [year, month] = referenceMonth.split('-');
  return formatMonthYear(Number(year), Number(month));
}

/**
 * Subtotal of a bill's line items: Σ(non-offset) − Σ(offset).
 *
 * Per design §4.1, an offset (abatimento) is stored as a POSITIVE amount with the
 * `is_offset` flag and subtracted from the total. Examples:
 * - [600, 400, 100-offset] → 900
 * - [100, 100-offset] → 0
 */
export function computeLineTotal(lines: LineTotalInput[]): number {
  const total = lines.reduce(
    (sum, line) => sum + (line.is_offset ? -line.amount : line.amount),
    0,
  );
  // Avoid floating-point dust (e.g. 0.1 + 0.2) before display.
  return Math.round(total * 100) / 100;
}
