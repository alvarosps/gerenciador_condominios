import { describe, it, expect, vi } from 'vitest';
import { screen, within } from '@testing-library/react';
import { renderWithProviders } from '@/tests/test-utils';
import { DataTable, type Column } from '../data-table';

interface Row {
  id: number;
  name: string;
  phone: string;
}

const data: Row[] = [
  { id: 1, name: 'Ana', phone: '11999990000' },
  { id: 2, name: 'Bruno', phone: '11888880000' },
];

const baseColumns: Column<Row>[] = [
  {
    title: 'Nome',
    dataIndex: 'name',
    key: 'name',
    primary: true,
    render: (value) => <span data-testid="name-cell">{String(value)}</span>,
  },
  { title: 'Telefone', dataIndex: 'phone', key: 'phone' },
];

describe('DataTable responsive table/cards', () => {
  it('wraps content in an @container context', () => {
    const { container } = renderWithProviders(
      <DataTable dataSource={data} columns={baseColumns} rowKey="id" />
    );
    expect(container.querySelector('.\\@container')).not.toBeNull();
  });

  it('renders the table branch with hidden @md:block classes wrapping the table', () => {
    const { container } = renderWithProviders(
      <DataTable dataSource={data} columns={baseColumns} rowKey="id" />
    );
    const tableWrapper = container.querySelector('.hidden.\\@md\\:block');
    expect(tableWrapper).not.toBeNull();
    expect(tableWrapper?.querySelector('table')).not.toBeNull();
  });

  it('renders the cards branch with the @md:hidden class', () => {
    const { container } = renderWithProviders(
      <DataTable dataSource={data} columns={baseColumns} rowKey="id" />
    );
    expect(container.querySelector('.\\@md\\:hidden')).not.toBeNull();
  });

  it('renders the table rows with the same data using column.render', () => {
    renderWithProviders(<DataTable dataSource={data} columns={baseColumns} rowKey="id" />);
    const nameCells = screen.getAllByTestId('name-cell');
    const texts = nameCells.map((cell) => cell.textContent);
    expect(texts).toContain('Ana');
    expect(texts).toContain('Bruno');
  });

  it('renders the cards with the same data', () => {
    renderWithProviders(<DataTable dataSource={data} columns={baseColumns} rowKey="id" />);
    expect(screen.getAllByTestId('data-table-card')).toHaveLength(2);
  });

  it('works with columns lacking the new optional fields (backward compatible)', () => {
    const legacyColumns: Column<Row>[] = [
      { title: 'Nome', dataIndex: 'name', key: 'name' },
      { title: 'Telefone', dataIndex: 'phone', key: 'phone' },
    ];
    const singleRow: Row[] = [{ id: 1, name: 'Ana', phone: '11999990000' }];
    renderWithProviders(<DataTable dataSource={singleRow} columns={legacyColumns} rowKey="id" />);
    const card = screen.getByTestId('data-table-card');
    const title = within(card).getByTestId('data-table-card-title');
    expect(title).toHaveTextContent('Ana');
    expect(within(card).queryByTestId('data-table-card-footer')).toBeNull();
  });

  it('still renders pagination controls when there is data', () => {
    renderWithProviders(<DataTable dataSource={data} columns={baseColumns} rowKey="id" />);
    expect(screen.getByLabelText('Página anterior')).toBeInTheDocument();
    expect(screen.getByLabelText('Próxima página')).toBeInTheDocument();
  });

  it('applies the align prop as a text-align class on header and body cells', () => {
    const alignedColumns: Column<Row>[] = [
      { title: 'Nome', dataIndex: 'name', key: 'name', primary: true },
      { title: 'Telefone', dataIndex: 'phone', key: 'phone', align: 'right' },
    ];
    renderWithProviders(<DataTable dataSource={data} columns={alignedColumns} rowKey="id" />);

    const headerCell = screen.getByRole('columnheader', { name: 'Telefone' });
    expect(headerCell).toHaveClass('text-right');

    const bodyCell = screen.getAllByText('11999990000')[0]?.closest('td');
    expect(bodyCell).toHaveClass('text-right');
  });
});

describe('DataTable loading state', () => {
  it('renders the real header with skeleton rows instead of a spinner', () => {
    const { container } = renderWithProviders(
      <DataTable dataSource={[]} columns={baseColumns} rowKey="id" loading />
    );

    expect(screen.getByRole('columnheader', { name: 'Nome' })).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: 'Telefone' })).toBeInTheDocument();
    expect(container.querySelectorAll('.animate-pulse').length).toBeGreaterThan(0);
    expect(container.querySelector('.animate-spin')).toBeNull();
  });

  it('marks the loading container as busy for assistive tech', () => {
    const { container } = renderWithProviders(
      <DataTable dataSource={[]} columns={baseColumns} rowKey="id" loading />
    );
    const busyContainer = container.querySelector('[aria-busy="true"]');
    expect(busyContainer).not.toBeNull();
    expect(busyContainer).toHaveAttribute('aria-live', 'polite');
  });

  it('renders skeleton rows for the row-selection checkbox column when enabled', () => {
    renderWithProviders(
      <DataTable
        dataSource={[]}
        columns={baseColumns}
        rowKey="id"
        loading
        rowSelection={{ selectedRowKeys: [], onChange: vi.fn() }}
      />
    );
    // Header checkbox column has no accessible checkbox while loading (no data to select).
    expect(screen.queryByLabelText('Selecionar todos')).toBeNull();
  });
});
