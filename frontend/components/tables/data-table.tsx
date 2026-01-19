import { useState } from 'react';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Checkbox } from '@/components/ui/checkbox';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { PAGINATION } from '@/lib/utils/constants';

export interface Column<T> {
  title: string;
  dataIndex?: keyof T | string;
  key: string;
  render?: (value: unknown, record: T, index: number) => React.ReactNode;
  width?: number | string;
  sorter?: (a: T, b: T) => number;
  filters?: Array<{ text: string; value: unknown }>;
  onFilter?: (value: unknown, record: T) => boolean;
  fixed?: 'left' | 'right';
  align?: 'left' | 'center' | 'right';
}

interface RowSelection<T> {
  selectedRowKeys?: React.Key[];
  onChange?: (selectedRowKeys: React.Key[], selectedRows: T[]) => void;
}

interface DataTableProps<T extends Record<string, unknown>> {
  dataSource?: T[];
  columns: Column<T>[];
  loading?: boolean;
  pagination?: boolean | {
    pageSize?: number;
    total?: number;
    current?: number;
    onChange?: (page: number, pageSize: number) => void;
  };
  rowKey?: string | ((record: T) => string);
  rowSelection?: RowSelection<T>;
}

export function DataTable<T extends Record<string, unknown>>({
  dataSource = [],
  columns,
  loading = false,
  pagination = {},
  rowKey = 'key',
  rowSelection,
}: DataTableProps<T>) {
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(
    typeof pagination === 'object' && pagination.pageSize
      ? pagination.pageSize
      : PAGINATION.DEFAULT_PAGE_SIZE
  );

  const showPagination = pagination !== false;
  const paginationConfig = typeof pagination === 'object' ? pagination : {};
  const total = paginationConfig.total || dataSource.length;
  const totalPages = Math.ceil(total / pageSize);
  const start = (currentPage - 1) * pageSize;
  const end = start + pageSize;
  const paginatedData = dataSource.slice(start, end);

  // Define getRowKey before it's used
  const getRowKey = (record: T, index: number): string => {
    if (typeof rowKey === 'function') {
      return rowKey(record);
    }
    if (typeof rowKey === 'string' && rowKey in record) {
      return String(record[rowKey as keyof T]);
    }
    return `row-${index}`;
  };

  const selectedKeys = rowSelection?.selectedRowKeys || [];
  const allCurrentPageKeys: React.Key[] = paginatedData.map((_record, index) =>
    getRowKey(_record, start + index)
  );
  const allSelected =
    paginatedData.length > 0 &&
    allCurrentPageKeys.every((key) => selectedKeys.includes(key));
  const someSelected =
    allCurrentPageKeys.some((key) => selectedKeys.includes(key)) && !allSelected;

  const handlePageChange = (page: number): void => {
    setCurrentPage(page);
    paginationConfig.onChange?.(page, pageSize);
  };

  const handlePageSizeChange = (newSize: string): void => {
    const size = parseInt(newSize, 10);
    setPageSize(size);
    setCurrentPage(1);
    paginationConfig.onChange?.(1, size);
  };

  const getCellValue = (record: T, column: Column<T>): unknown => {
    if (!column.dataIndex) return undefined;

    const path = String(column.dataIndex).split('.');
    let value: unknown = record;

    for (const key of path) {
      if (value && typeof value === 'object' && key in value) {
        value = (value as Record<string, unknown>)[key];
      } else {
        return undefined;
      }
    }

    return value;
  };

  const handleSelectAll = (checked: boolean): void => {
    if (!rowSelection?.onChange) return;

    if (checked) {
      const newSelectedKeys = [...selectedKeys];
      const newSelectedRows: T[] = [];

      allCurrentPageKeys.forEach((key, index) => {
        if (!selectedKeys.includes(key)) {
          newSelectedKeys.push(key);
          newSelectedRows.push(paginatedData[index]);
        }
      });

      rowSelection.onChange(newSelectedKeys, newSelectedRows);
    } else {
      const newSelectedKeys = selectedKeys.filter(
        (key) => !allCurrentPageKeys.includes(key)
      );
      const newSelectedRows = dataSource.filter((_record, index) => {
        const key = getRowKey(_record, index);
        return newSelectedKeys.includes(key);
      });
      rowSelection.onChange(newSelectedKeys, newSelectedRows);
    }
  };

  const handleSelectRow = (record: T, index: number, checked: boolean): void => {
    if (!rowSelection?.onChange) return;

    const key = getRowKey(record, index);
    let newSelectedKeys: React.Key[];
    let newSelectedRows: T[];

    if (checked) {
      newSelectedKeys = [...selectedKeys, key];
      newSelectedRows = dataSource.filter((_r, i) => {
        const k = getRowKey(_r, i);
        return newSelectedKeys.includes(k);
      });
    } else {
      newSelectedKeys = selectedKeys.filter((k) => k !== key);
      newSelectedRows = dataSource.filter((_r, i) => {
        const k = getRowKey(_r, i);
        return newSelectedKeys.includes(k);
      });
    }

    rowSelection.onChange(newSelectedKeys, newSelectedRows);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8 border rounded-md">
        <div className="flex flex-col items-center gap-2">
          <div className="h-8 w-8 border-4 border-primary border-t-transparent rounded-full animate-spin" />
          <p className="text-sm text-muted-foreground">Carregando...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              {rowSelection && (
                <TableHead style={{ width: 50 }}>
                  <Checkbox
                    checked={allSelected}
                    onCheckedChange={handleSelectAll}
                    aria-label="Select all"
                    className={someSelected ? 'opacity-50' : ''}
                  />
                </TableHead>
              )}
              {columns.map((column) => (
                <TableHead key={column.key} style={{ width: column.width }}>
                  {column.title}
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {paginatedData.length === 0 ? (
              <TableRow>
                <TableCell
                  colSpan={columns.length + (rowSelection ? 1 : 0)}
                  className="text-center py-8"
                >
                  <p className="text-muted-foreground">Nenhum dado disponível</p>
                </TableCell>
              </TableRow>
            ) : (
              paginatedData.map((record, index) => {
                const rowKey = getRowKey(record, start + index);
                const isSelected = selectedKeys.includes(rowKey);

                return (
                  <TableRow key={rowKey}>
                    {rowSelection && (
                      <TableCell>
                        <Checkbox
                          checked={isSelected}
                          onCheckedChange={(checked) =>
                            handleSelectRow(record, start + index, checked as boolean)
                          }
                          aria-label="Select row"
                        />
                      </TableCell>
                    )}
                    {columns.map((column) => {
                      const value = getCellValue(record, column);
                      const content = column.render
                        ? column.render(value, record, index)
                        : String(value ?? '');

                      return <TableCell key={column.key}>{content}</TableCell>;
                    })}
                  </TableRow>
                );
              })
            )}
          </TableBody>
        </Table>
      </div>

      {showPagination && dataSource.length > 0 && (
        <div className="flex items-center justify-between">
          <div className="text-sm text-muted-foreground">
            {start + 1}-{Math.min(end, total)} de {total} itens
          </div>

          <div className="flex items-center gap-2">
            <Select value={String(pageSize)} onValueChange={handlePageSizeChange}>
              <SelectTrigger className="w-[100px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {PAGINATION.PAGE_SIZE_OPTIONS.map((size) => (
                  <SelectItem key={size} value={String(size)}>
                    {size} / página
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <div className="flex items-center gap-1">
              <Button
                variant="outline"
                size="sm"
                onClick={() => handlePageChange(currentPage - 1)}
                disabled={currentPage === 1}
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>

              <span className="text-sm px-2">
                Página {currentPage} de {totalPages}
              </span>

              <Button
                variant="outline"
                size="sm"
                onClick={() => handlePageChange(currentPage + 1)}
                disabled={currentPage === totalPages}
              >
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
