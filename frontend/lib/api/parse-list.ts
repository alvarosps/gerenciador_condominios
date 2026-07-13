import { type z } from 'zod';

/**
 * Result of parsing a list response: the validated items, the backend's reported total
 * (from the DRF envelope's `count`, or `items.length` for a non-paginated array), and how
 * many raw items failed Zod validation and were skipped.
 */
export interface ParsedList<T> {
  items: T[];
  count: number;
  invalidCount: number;
}

interface DrfPaginatedEnvelope {
  count: number;
  next: string | null;
  previous: string | null;
  results: unknown[];
}

function isDrfPaginatedEnvelope(data: unknown): data is DrfPaginatedEnvelope {
  return (
    data !== null &&
    typeof data === 'object' &&
    !Array.isArray(data) &&
    'results' in data &&
    Array.isArray(data.results) &&
    'count' in data &&
    typeof data.count === 'number'
  );
}

/**
 * Parse a list API response that may be either a DRF paginated envelope
 * (`{count, next, previous, results}`) or a plain array (non-paginated endpoints).
 *
 * Each item is validated against `schema` independently — an invalid item is skipped rather
 * than failing the whole list, so a single malformed record does not empty the UI. The number
 * of skipped items is reported via `invalidCount`.
 */
export function parseList<T>(data: unknown, schema: z.ZodType<T>): ParsedList<T> {
  const rawItems = Array.isArray(data) ? data : isDrfPaginatedEnvelope(data) ? data.results : [];

  const items: T[] = [];
  let invalidCount = 0;
  for (const rawItem of rawItems) {
    const result = schema.safeParse(rawItem);
    if (result.success) {
      items.push(result.data);
    } else {
      invalidCount += 1;
    }
  }

  const count = isDrfPaginatedEnvelope(data) ? data.count : items.length;

  return { items, count, invalidCount };
}
