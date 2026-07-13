import { describe, it, expect } from 'vitest';
import { z } from 'zod';
import { parseList } from '../parse-list';

const itemSchema = z.object({
  id: z.number(),
  name: z.string(),
});

describe('parseList', () => {
  it('parses a plain array response', () => {
    const data = [
      { id: 1, name: 'A' },
      { id: 2, name: 'B' },
    ];

    const result = parseList(data, itemSchema);

    expect(result.items).toEqual([
      { id: 1, name: 'A' },
      { id: 2, name: 'B' },
    ]);
    expect(result.count).toBe(2);
    expect(result.invalidCount).toBe(0);
  });

  it('parses a DRF paginated envelope response', () => {
    const data = {
      count: 42,
      next: 'http://api/list/?page=2',
      previous: null,
      results: [
        { id: 1, name: 'A' },
        { id: 2, name: 'B' },
      ],
    };

    const result = parseList(data, itemSchema);

    expect(result.items).toEqual([
      { id: 1, name: 'A' },
      { id: 2, name: 'B' },
    ]);
    // count comes from the envelope's real backend total, not items.length
    expect(result.count).toBe(42);
    expect(result.invalidCount).toBe(0);
  });

  it('skips an invalid item in the middle and keeps the valid ones', () => {
    const data = [
      { id: 1, name: 'A' },
      { id: 'not-a-number', name: 'B' },
      { id: 3, name: 'C' },
    ];

    const result = parseList(data, itemSchema);

    expect(result.items).toEqual([
      { id: 1, name: 'A' },
      { id: 3, name: 'C' },
    ]);
    expect(result.invalidCount).toBe(1);
  });

  it('returns an empty items list when all items are invalid, without throwing', () => {
    const data = [
      { id: 'x', name: 1 },
      { id: 'y', name: 2 },
    ];

    const result = parseList(data, itemSchema);

    expect(result.items).toEqual([]);
    expect(result.invalidCount).toBe(2);
  });

  it('treats an unrecognized response shape as an empty list', () => {
    const result = parseList({ unexpected: true }, itemSchema);

    expect(result.items).toEqual([]);
    expect(result.count).toBe(0);
    expect(result.invalidCount).toBe(0);
  });
});
