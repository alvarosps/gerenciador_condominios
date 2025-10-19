import { Table } from 'antd';
import type { TableProps } from 'antd';
import { PAGINATION } from '@/lib/utils/constants';

interface DataTableProps<T> extends TableProps<T> {
  dataSource?: T[];
  loading?: boolean;
}

export function DataTable<T extends object>({
  dataSource = [],
  loading = false,
  pagination = {},
  ...props
}: DataTableProps<T>) {
  const defaultPagination = {
    pageSize: PAGINATION.DEFAULT_PAGE_SIZE,
    showSizeChanger: true,
    pageSizeOptions: PAGINATION.PAGE_SIZE_OPTIONS.map(String),
    showTotal: (total: number, range: [number, number]) =>
      `${range[0]}-${range[1]} de ${total} itens`,
    ...pagination,
  };

  return (
    <Table
      {...props}
      dataSource={dataSource}
      loading={loading}
      pagination={defaultPagination}
      bordered
      size="middle"
    />
  );
}
