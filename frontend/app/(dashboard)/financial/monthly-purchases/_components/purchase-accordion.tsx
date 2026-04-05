'use client';

import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { formatCurrency, formatDate } from '@/lib/utils/formatters';
import type { MonthlyPurchaseGroup, MonthlyPurchaseItem } from '@/lib/api/hooks/use-monthly-purchases';

interface PurchaseAccordionProps {
  cardPurchases: MonthlyPurchaseGroup;
  loans: MonthlyPurchaseGroup;
  utilityBills: MonthlyPurchaseGroup;
  oneTimeExpenses: MonthlyPurchaseGroup;
  fixedExpenses: MonthlyPurchaseGroup;
}

interface ColumnDef {
  header: string;
  accessor: (item: MonthlyPurchaseItem) => string;
  className?: string;
}

function PurchaseTable({ items, columns }: { items: MonthlyPurchaseItem[]; columns: ColumnDef[] }) {
  if (items.length === 0) {
    return <p className="text-center text-muted-foreground py-4 text-sm">Nenhum item</p>;
  }
  return (
    <Table>
      <TableHeader>
        <TableRow>
          {columns.map((col) => (
            <TableHead key={col.header} className={col.className}>
              {col.header}
            </TableHead>
          ))}
        </TableRow>
      </TableHeader>
      <TableBody>
        {items.map((item, idx) => (
          <TableRow key={idx}>
            {columns.map((col) => (
              <TableCell key={col.header} className={col.className}>
                {col.accessor(item)}
              </TableCell>
            ))}
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

const CARD_PURCHASES_COLUMNS: ColumnDef[] = [
  { header: 'Descrição', accessor: (item) => item.description },
  { header: 'Pessoa', accessor: (item) => item.person_name ?? '—', className: 'text-muted-foreground' },
  { header: 'Cartão', accessor: (item) => item.card_name ?? '—', className: 'text-muted-foreground' },
  { header: 'Valor Parcela', accessor: (item) => formatCurrency(item.amount), className: 'text-right' },
  { header: 'Total', accessor: (item) => item.total_amount !== null ? formatCurrency(item.total_amount) : '—', className: 'text-right' },
  { header: 'Parcela Atual', accessor: () => '1', className: 'text-center' },
  { header: 'Nº Parcelas', accessor: (item) => item.total_installments !== null ? String(item.total_installments) : '—', className: 'text-center' },
];

const LOANS_COLUMNS: ColumnDef[] = [
  { header: 'Descrição', accessor: (item) => item.description },
  { header: 'Pessoa', accessor: (item) => item.person_name ?? '—', className: 'text-muted-foreground' },
  { header: 'Valor Parcela', accessor: (item) => formatCurrency(item.amount), className: 'text-right' },
  { header: 'Total', accessor: (item) => item.total_amount !== null ? formatCurrency(item.total_amount) : '—', className: 'text-right' },
  { header: 'Parcela Atual', accessor: () => '1', className: 'text-center' },
  { header: 'Nº Parcelas', accessor: (item) => item.total_installments !== null ? String(item.total_installments) : '—', className: 'text-center' },
];

const UTILITY_BILLS_COLUMNS: ColumnDef[] = [
  { header: 'Descrição', accessor: (item) => item.description },
  { header: 'Valor', accessor: (item) => formatCurrency(item.amount), className: 'text-right' },
  { header: 'Data', accessor: (item) => item.date ? formatDate(item.date) : '—', className: 'text-muted-foreground' },
];

const ONE_TIME_EXPENSES_COLUMNS: ColumnDef[] = [
  { header: 'Descrição', accessor: (item) => item.description },
  { header: 'Pessoa', accessor: (item) => item.person_name ?? '—', className: 'text-muted-foreground' },
  { header: 'Valor', accessor: (item) => formatCurrency(item.amount), className: 'text-right' },
  { header: 'Data', accessor: (item) => item.date ? formatDate(item.date) : '—', className: 'text-muted-foreground' },
];

const FIXED_EXPENSES_COLUMNS: ColumnDef[] = [
  { header: 'Descrição', accessor: (item) => item.description },
  { header: 'Pessoa', accessor: (item) => item.person_name ?? '—', className: 'text-muted-foreground' },
  { header: 'Valor Mensal', accessor: (item) => formatCurrency(item.amount), className: 'text-right' },
];

function accordionTitle(label: string, count: number, total: number) {
  return (
    <span className="flex items-center gap-3 px-4">
      <span className="font-semibold">{label}</span>
      <span className="text-muted-foreground text-sm">
        {count} {count === 1 ? 'item' : 'itens'} — {formatCurrency(total)}
      </span>
    </span>
  );
}

export function PurchaseAccordion({
  cardPurchases,
  loans,
  utilityBills,
  oneTimeExpenses,
  fixedExpenses,
}: PurchaseAccordionProps) {
  return (
    <Accordion type="multiple" className="space-y-2">
      <AccordionItem value="card_purchases">
        <AccordionTrigger>
          {accordionTitle('Compras no Cartão', cardPurchases.count, cardPurchases.total)}
        </AccordionTrigger>
        <AccordionContent className="px-4">
          <PurchaseTable items={cardPurchases.items} columns={CARD_PURCHASES_COLUMNS} />
        </AccordionContent>
      </AccordionItem>

      <AccordionItem value="utility_bills">
        <AccordionTrigger>
          {accordionTitle('Contas de Consumo', utilityBills.count, utilityBills.total)}
        </AccordionTrigger>
        <AccordionContent className="px-4">
          <PurchaseTable items={utilityBills.items} columns={UTILITY_BILLS_COLUMNS} />
        </AccordionContent>
      </AccordionItem>

      <AccordionItem value="loans">
        <AccordionTrigger>
          {accordionTitle('Empréstimos', loans.count, loans.total)}
        </AccordionTrigger>
        <AccordionContent className="px-4">
          <PurchaseTable items={loans.items} columns={LOANS_COLUMNS} />
        </AccordionContent>
      </AccordionItem>

      <AccordionItem value="one_time_expenses">
        <AccordionTrigger>
          {accordionTitle('Gastos Únicos', oneTimeExpenses.count, oneTimeExpenses.total)}
        </AccordionTrigger>
        <AccordionContent className="px-4">
          <PurchaseTable items={oneTimeExpenses.items} columns={ONE_TIME_EXPENSES_COLUMNS} />
        </AccordionContent>
      </AccordionItem>

      <AccordionItem value="fixed_expenses">
        <AccordionTrigger>
          {accordionTitle('Gastos Fixos', fixedExpenses.count, fixedExpenses.total)}
        </AccordionTrigger>
        <AccordionContent className="px-4">
          <PurchaseTable items={fixedExpenses.items} columns={FIXED_EXPENSES_COLUMNS} />
        </AccordionContent>
      </AccordionItem>
    </Accordion>
  );
}
