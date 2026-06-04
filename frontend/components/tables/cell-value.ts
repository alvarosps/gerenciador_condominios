import type { Column } from './data-table';

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object';
}

export function resolveCellValue<T>(record: T, column: Column<T>): unknown {
  if (!column.dataIndex) return undefined;

  const path = String(column.dataIndex).split('.');
  let value: unknown = record;

  for (const key of path) {
    if (isRecord(value) && key in value) {
      value = value[key];
    } else {
      return undefined;
    }
  }

  return value;
}

function stringifyCellValue(value: unknown): string {
  if (value === null || value === undefined) return '';
  if (typeof value === 'object') return JSON.stringify(value);
  if (typeof value === 'string') return value;
  if (typeof value === 'number' || typeof value === 'bigint') return value.toString();
  if (typeof value === 'boolean') return value ? 'true' : 'false';
  if (typeof value === 'symbol') return value.toString();
  return '';
}

export function renderCellContent<T>(
  column: Column<T>,
  record: T,
  index: number
): React.ReactNode {
  const value = resolveCellValue(record, column);
  if (column.render) {
    return column.render(value, record, index);
  }
  return stringifyCellValue(value);
}
