import { describe, it, expect } from 'vitest';
import { resolveCellValue } from '../cell-value';
import type { Column } from '../data-table';

interface NestedRecord {
  name: string;
  apartment: {
    building: {
      street_number: number;
    };
  };
}

describe('resolveCellValue', () => {
  it('resolves a simple dataIndex to the field value', () => {
    const record = { name: 'Ana' };
    const column: Column<{ name: string }> = { title: 'Nome', dataIndex: 'name', key: 'name' };
    expect(resolveCellValue(record, column)).toBe('Ana');
  });

  it('resolves a dotted path over a nested object to the leaf value', () => {
    const record: NestedRecord = {
      name: 'Ana',
      apartment: { building: { street_number: 836 } },
    };
    const column: Column<NestedRecord> = {
      title: 'Prédio',
      dataIndex: 'apartment.building.street_number',
      key: 'building',
    };
    expect(resolveCellValue(record, column)).toBe(836);
  });

  it('returns undefined when an intermediate hop in the path is missing', () => {
    const record = { name: 'Ana' };
    const column: Column<{ name: string }> = {
      title: 'Prédio',
      dataIndex: 'apartment.building.street_number',
      key: 'building',
    };
    expect(resolveCellValue(record, column)).toBeUndefined();
  });

  it('returns undefined for a column without dataIndex (render-only column)', () => {
    const record = { name: 'Ana' };
    const column: Column<{ name: string }> = {
      title: 'Ações',
      key: 'actions',
      render: () => 'x',
    };
    expect(resolveCellValue(record, column)).toBeUndefined();
  });

  it('matches direct property access for a dataIndex column (parity)', () => {
    const record = { name: 'Ana' };
    const column: Column<{ name: string }> = { title: 'Nome', dataIndex: 'name', key: 'name' };
    expect(resolveCellValue(record, column)).toBe(record.name);
  });
});
