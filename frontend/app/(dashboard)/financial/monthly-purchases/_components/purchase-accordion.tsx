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

function CardPurchasesTable({ items }: { items: MonthlyPurchaseItem[] }) {
  if (items.length === 0) {
    return <p className="text-center text-muted-foreground py-4 text-sm">Nenhum item</p>;
  }
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Descrição</TableHead>
          <TableHead>Pessoa</TableHead>
          <TableHead>Cartão</TableHead>
          <TableHead className="text-right">Valor Parcela</TableHead>
          <TableHead className="text-right">Total</TableHead>
          <TableHead className="text-right">Parcelas</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {items.map((item, idx) => (
          <TableRow key={idx}>
            <TableCell>{item.description}</TableCell>
            <TableCell className="text-muted-foreground">{item.person_name ?? '—'}</TableCell>
            <TableCell className="text-muted-foreground">{item.card_name ?? '—'}</TableCell>
            <TableCell className="text-right">{formatCurrency(item.amount)}</TableCell>
            <TableCell className="text-right">{item.total_amount !== null ? formatCurrency(item.total_amount) : '—'}</TableCell>
            <TableCell className="text-right">{item.total_installments !== null ? String(item.total_installments) : '—'}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

function LoansTable({ items }: { items: MonthlyPurchaseItem[] }) {
  if (items.length === 0) {
    return <p className="text-center text-muted-foreground py-4 text-sm">Nenhum item</p>;
  }
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Descrição</TableHead>
          <TableHead>Pessoa</TableHead>
          <TableHead className="text-right">Valor Parcela</TableHead>
          <TableHead className="text-right">Total</TableHead>
          <TableHead className="text-right">Parcelas</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {items.map((item, idx) => (
          <TableRow key={idx}>
            <TableCell>{item.description}</TableCell>
            <TableCell className="text-muted-foreground">{item.person_name ?? '—'}</TableCell>
            <TableCell className="text-right">{formatCurrency(item.amount)}</TableCell>
            <TableCell className="text-right">{item.total_amount !== null ? formatCurrency(item.total_amount) : '—'}</TableCell>
            <TableCell className="text-right">{item.total_installments !== null ? String(item.total_installments) : '—'}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

function UtilityBillsTable({ items }: { items: MonthlyPurchaseItem[] }) {
  if (items.length === 0) {
    return <p className="text-center text-muted-foreground py-4 text-sm">Nenhum item</p>;
  }
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Descrição</TableHead>
          <TableHead className="text-right">Valor</TableHead>
          <TableHead>Data</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {items.map((item, idx) => (
          <TableRow key={idx}>
            <TableCell>{item.description}</TableCell>
            <TableCell className="text-right">{formatCurrency(item.amount)}</TableCell>
            <TableCell className="text-muted-foreground">{item.date ? formatDate(item.date) : '—'}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

function OneTimeExpensesTable({ items }: { items: MonthlyPurchaseItem[] }) {
  if (items.length === 0) {
    return <p className="text-center text-muted-foreground py-4 text-sm">Nenhum item</p>;
  }
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Descrição</TableHead>
          <TableHead>Pessoa</TableHead>
          <TableHead className="text-right">Valor</TableHead>
          <TableHead>Data</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {items.map((item, idx) => (
          <TableRow key={idx}>
            <TableCell>{item.description}</TableCell>
            <TableCell className="text-muted-foreground">{item.person_name ?? '—'}</TableCell>
            <TableCell className="text-right">{formatCurrency(item.amount)}</TableCell>
            <TableCell className="text-muted-foreground">{item.date ? formatDate(item.date) : '—'}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

function FixedExpensesTable({ items }: { items: MonthlyPurchaseItem[] }) {
  if (items.length === 0) {
    return <p className="text-center text-muted-foreground py-4 text-sm">Nenhum item</p>;
  }
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Descrição</TableHead>
          <TableHead>Pessoa</TableHead>
          <TableHead className="text-right">Valor Mensal</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {items.map((item, idx) => (
          <TableRow key={idx}>
            <TableCell>{item.description}</TableCell>
            <TableCell className="text-muted-foreground">{item.person_name ?? '—'}</TableCell>
            <TableCell className="text-right">{formatCurrency(item.amount)}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

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
          <CardPurchasesTable items={cardPurchases.items} />
        </AccordionContent>
      </AccordionItem>

      <AccordionItem value="utility_bills">
        <AccordionTrigger>
          {accordionTitle('Contas de Consumo', utilityBills.count, utilityBills.total)}
        </AccordionTrigger>
        <AccordionContent className="px-4">
          <UtilityBillsTable items={utilityBills.items} />
        </AccordionContent>
      </AccordionItem>

      <AccordionItem value="loans">
        <AccordionTrigger>
          {accordionTitle('Empréstimos', loans.count, loans.total)}
        </AccordionTrigger>
        <AccordionContent className="px-4">
          <LoansTable items={loans.items} />
        </AccordionContent>
      </AccordionItem>

      <AccordionItem value="one_time_expenses">
        <AccordionTrigger>
          {accordionTitle('Gastos Únicos', oneTimeExpenses.count, oneTimeExpenses.total)}
        </AccordionTrigger>
        <AccordionContent className="px-4">
          <OneTimeExpensesTable items={oneTimeExpenses.items} />
        </AccordionContent>
      </AccordionItem>

      <AccordionItem value="fixed_expenses">
        <AccordionTrigger>
          {accordionTitle('Gastos Fixos', fixedExpenses.count, fixedExpenses.total)}
        </AccordionTrigger>
        <AccordionContent className="px-4">
          <FixedExpensesTable items={fixedExpenses.items} />
        </AccordionContent>
      </AccordionItem>
    </Accordion>
  );
}
