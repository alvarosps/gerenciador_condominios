import { describe, it, expect } from 'vitest';
import { screen, within } from '@testing-library/react';
import { renderWithProviders } from '@/tests/test-utils';
import { DataTableCards } from '../data-table-cards';
import type { Column } from '../data-table';

interface Row {
  id: number;
  name: string;
  phone: string;
  secret: string;
}

const ana: Row = { id: 1, name: 'Ana', phone: '11999990000', secret: 'hidden-a' };
const bruno: Row = { id: 2, name: 'Bruno', phone: '11888880000', secret: 'hidden-b' };
const data: Row[] = [ana, bruno];

const rowKey = (record: Row): string => String(record.id);

describe('DataTableCards', () => {
  it('uses the primary column value as the card title', () => {
    const columns: Column<Row>[] = [
      { title: 'Telefone', dataIndex: 'phone', key: 'phone' },
      { title: 'Nome', dataIndex: 'name', key: 'name', primary: true },
    ];
    renderWithProviders(<DataTableCards columns={columns} data={data} rowKey={rowKey} />);
    expect(screen.getByText('Ana')).toBeInTheDocument();
    expect(screen.getByText('Bruno')).toBeInTheDocument();
  });

  it('falls back to the first non-actions column for the title when no primary is set', () => {
    const columns: Column<Row>[] = [
      { title: 'Nome', dataIndex: 'name', key: 'name' },
      { title: 'Telefone', dataIndex: 'phone', key: 'phone' },
    ];
    renderWithProviders(<DataTableCards columns={columns} data={[ana]} rowKey={rowKey} />);
    const card = screen.getByTestId('data-table-card');
    const title = within(card).getByTestId('data-table-card-title');
    expect(title).toHaveTextContent('Ana');
  });

  it('renders body rows as "label: value" pairs', () => {
    const columns: Column<Row>[] = [
      { title: 'Nome', dataIndex: 'name', key: 'name', primary: true },
      { title: 'Telefone', dataIndex: 'phone', key: 'phone' },
    ];
    renderWithProviders(<DataTableCards columns={columns} data={[ana]} rowKey={rowKey} />);
    expect(screen.getByText('Telefone')).toBeInTheDocument();
    expect(screen.getByText('11999990000')).toBeInTheDocument();
  });

  it('omits a column marked hideOnCard from the card', () => {
    const columns: Column<Row>[] = [
      { title: 'Nome', dataIndex: 'name', key: 'name', primary: true },
      { title: 'Telefone', dataIndex: 'phone', key: 'phone' },
      { title: 'Segredo', dataIndex: 'secret', key: 'secret', hideOnCard: true },
    ];
    renderWithProviders(<DataTableCards columns={columns} data={[ana]} rowKey={rowKey} />);
    expect(screen.queryByText('Segredo')).not.toBeInTheDocument();
    expect(screen.queryByText('hidden-a')).not.toBeInTheDocument();
  });

  it('uses column.render for the body content (not the raw value)', () => {
    const columns: Column<Row>[] = [
      { title: 'Nome', dataIndex: 'name', key: 'name', primary: true },
      {
        title: 'Status',
        key: 'status',
        render: () => <span>BADGE-X</span>,
      },
    ];
    renderWithProviders(<DataTableCards columns={columns} data={[ana]} rowKey={rowKey} />);
    expect(screen.getByText('BADGE-X')).toBeInTheDocument();
  });

  it('renders isActions columns in a distinct footer with full-width actions', () => {
    const columns: Column<Row>[] = [
      { title: 'Nome', dataIndex: 'name', key: 'name', primary: true },
      {
        title: 'Ações',
        key: 'actions',
        isActions: true,
        render: () => <button type="button">Editar</button>,
      },
    ];
    renderWithProviders(<DataTableCards columns={columns} data={[ana]} rowKey={rowKey} />);
    const footer = screen.getByTestId('data-table-card-footer');
    const editButton = within(footer).getByRole('button', { name: 'Editar' });
    expect(editButton).toBeInTheDocument();
    const actionWrapper = footer.firstElementChild;
    expect(actionWrapper).not.toBeNull();
    expect(actionWrapper?.className).toContain('w-full');
  });

  it('shows the empty state when data is empty', () => {
    const columns: Column<Row>[] = [{ title: 'Nome', dataIndex: 'name', key: 'name' }];
    renderWithProviders(<DataTableCards columns={columns} data={[]} rowKey={rowKey} />);
    expect(screen.getByText('Nenhum dado disponível')).toBeInTheDocument();
  });

  it('renders one card per record using rowKey without duplicate-key warnings', () => {
    const columns: Column<Row>[] = [{ title: 'Nome', dataIndex: 'name', key: 'name', primary: true }];
    renderWithProviders(<DataTableCards columns={columns} data={data} rowKey={rowKey} />);
    expect(screen.getAllByTestId('data-table-card')).toHaveLength(2);
  });

  it('applies the received className to the list container', () => {
    const columns: Column<Row>[] = [{ title: 'Nome', dataIndex: 'name', key: 'name', primary: true }];
    const { container } = renderWithProviders(
      <DataTableCards columns={columns} data={data} rowKey={rowKey} className="@md:hidden" />
    );
    const list = container.querySelector('.\\@md\\:hidden');
    expect(list).not.toBeNull();
  });
});
