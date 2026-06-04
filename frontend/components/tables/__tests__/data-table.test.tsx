import { describe, it, expect } from 'vitest';
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
});
