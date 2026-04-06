'use client';

import { useEffect, useMemo } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { usePersons } from '@/lib/api/hooks/use-persons';
import { useCreditCards } from '@/lib/api/hooks/use-credit-cards';
import { useBuildings } from '@/lib/api/hooks/use-buildings';
import { useExpenseCategories } from '@/lib/api/hooks/use-expense-categories';
import { type ExpenseFilters } from '@/lib/api/hooks/use-expenses';

interface ExtendedExpenseFilters extends ExpenseFilters {
  date_from?: string;
  date_to?: string;
}

interface Props {
  filters: ExtendedExpenseFilters;
  onFiltersChange: (filters: ExtendedExpenseFilters) => void;
}

const EXPENSE_TYPE_OPTIONS = [
  { value: 'all', label: 'Todos os tipos' },
  { value: 'card_purchase', label: 'Compra no Cart\u00e3o' },
  { value: 'bank_loan', label: 'Empr\u00e9stimo Banc\u00e1rio' },
  { value: 'personal_loan', label: 'Empr\u00e9stimo Pessoal' },
  { value: 'water_bill', label: 'Conta de \u00c1gua' },
  { value: 'electricity_bill', label: 'Conta de Luz' },
  { value: 'property_tax', label: 'IPTU' },
  { value: 'fixed_expense', label: 'Gasto Fixo' },
  { value: 'one_time_expense', label: 'Gasto \u00danico' },
  { value: 'employee_salary', label: 'Sal\u00e1rio' },
];

export type { ExtendedExpenseFilters };

export function ExpenseFiltersCard({ filters, onFiltersChange }: Props) {
  const { data: persons } = usePersons();
  const { data: allCreditCards } = useCreditCards();
  const { data: buildings } = useBuildings();
  const { data: categories } = useExpenseCategories();

  const filteredCreditCards = useMemo(() => {
    if (!allCreditCards || !filters.person_id) return allCreditCards;
    return allCreditCards.filter((card) => card.person_id === filters.person_id);
  }, [allCreditCards, filters.person_id]);

  // Clear credit card when person changes
  useEffect(() => {
    if (!filters.person_id && filters.credit_card_id) {
      onFiltersChange({ ...filters, credit_card_id: undefined });
    }
  }, [filters, onFiltersChange]);

  const hasActiveFilters = Object.entries(filters).some(
    ([, v]) => v !== undefined && v !== '',
  );

  const clearFilters = () => {
    onFiltersChange({
      expense_type: undefined,
      person_id: undefined,
      credit_card_id: undefined,
      building_id: undefined,
      category_id: undefined,
      is_paid: undefined,
      is_recurring: undefined,
      is_offset: undefined,
      date_from: undefined,
      date_to: undefined,
    });
  };

  return (
    <Card className="mb-4">
      <CardContent className="pt-6">
        <div className="flex gap-4 flex-wrap items-end">
          {/* Tipo */}
          <div className="flex-1 min-w-[150px]">
            <label className="block text-sm font-medium mb-2">Tipo</label>
            <Select
              value={filters.expense_type ?? 'all'}
              onValueChange={(value) =>
                onFiltersChange({ ...filters, expense_type: value === 'all' ? undefined : value })
              }
            >
              <SelectTrigger>
                <SelectValue placeholder="Todos os tipos" />
              </SelectTrigger>
              <SelectContent>
                {EXPENSE_TYPE_OPTIONS.map((opt) => (
                  <SelectItem key={opt.value} value={opt.value}>
                    {opt.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Pessoa */}
          <div className="flex-1 min-w-[150px]">
            <label className="block text-sm font-medium mb-2">Pessoa</label>
            <Select
              value={filters.person_id ? String(filters.person_id) : 'all'}
              onValueChange={(value) =>
                onFiltersChange({
                  ...filters,
                  person_id: value === 'all' ? undefined : Number(value),
                  credit_card_id: value === 'all' ? undefined : filters.credit_card_id,
                })
              }
            >
              <SelectTrigger>
                <SelectValue placeholder="Todas as pessoas" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todas as pessoas</SelectItem>
                {persons?.map((p) => (
                  <SelectItem key={p.id} value={String(p.id)}>
                    {p.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Cart\u00e3o */}
          <div className="flex-1 min-w-[150px]">
            <label className="block text-sm font-medium mb-2">Cart\u00e3o</label>
            <Select
              value={filters.credit_card_id ? String(filters.credit_card_id) : 'all'}
              onValueChange={(value) =>
                onFiltersChange({
                  ...filters,
                  credit_card_id: value === 'all' ? undefined : Number(value),
                })
              }
              disabled={!filters.person_id}
            >
              <SelectTrigger>
                <SelectValue placeholder="Todos os cart\u00f5es" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todos os cart\u00f5es</SelectItem>
                {filteredCreditCards?.map((card) => (
                  <SelectItem key={card.id} value={String(card.id)}>
                    {card.nickname} (****{card.last_four_digits})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Pr\u00e9dio */}
          <div className="flex-1 min-w-[150px]">
            <label className="block text-sm font-medium mb-2">Pr\u00e9dio</label>
            <Select
              value={filters.building_id ? String(filters.building_id) : 'all'}
              onValueChange={(value) =>
                onFiltersChange({
                  ...filters,
                  building_id: value === 'all' ? undefined : Number(value),
                })
              }
            >
              <SelectTrigger>
                <SelectValue placeholder="Todos os pr\u00e9dios" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todos os pr\u00e9dios</SelectItem>
                {buildings?.map((b) => (
                  <SelectItem key={b.id} value={String(b.id)}>
                    {b.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Categoria */}
          <div className="flex-1 min-w-[150px]">
            <label className="block text-sm font-medium mb-2">Categoria</label>
            <Select
              value={filters.category_id ? String(filters.category_id) : 'all'}
              onValueChange={(value) =>
                onFiltersChange({
                  ...filters,
                  category_id: value === 'all' ? undefined : Number(value),
                })
              }
            >
              <SelectTrigger>
                <SelectValue placeholder="Todas" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todas as categorias</SelectItem>
                {categories?.map((cat) => (
                  <SelectItem key={cat.id} value={String(cat.id)}>
                    {cat.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Status */}
          <div className="flex-1 min-w-[130px]">
            <label className="block text-sm font-medium mb-2">Status</label>
            <Select
              value={filters.is_paid === undefined ? 'all' : filters.is_paid ? 'paid' : 'pending'}
              onValueChange={(value) =>
                onFiltersChange({
                  ...filters,
                  is_paid: value === 'all' ? undefined : value === 'paid',
                })
              }
            >
              <SelectTrigger>
                <SelectValue placeholder="Todos" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todos</SelectItem>
                <SelectItem value="paid">Pago</SelectItem>
                <SelectItem value="pending">Pendente</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Recorrente */}
          <div className="flex-1 min-w-[130px]">
            <label className="block text-sm font-medium mb-2">Recorrente</label>
            <Select
              value={filters.is_recurring === undefined ? 'all' : filters.is_recurring ? 'yes' : 'no'}
              onValueChange={(value) =>
                onFiltersChange({
                  ...filters,
                  is_recurring: value === 'all' ? undefined : value === 'yes',
                })
              }
            >
              <SelectTrigger>
                <SelectValue placeholder="Todos" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todos</SelectItem>
                <SelectItem value="yes">Sim</SelectItem>
                <SelectItem value="no">Não</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Desconto */}
          <div className="flex-1 min-w-[130px]">
            <label className="block text-sm font-medium mb-2">Desconto</label>
            <Select
              value={filters.is_offset === undefined ? 'all' : filters.is_offset ? 'yes' : 'no'}
              onValueChange={(value) =>
                onFiltersChange({
                  ...filters,
                  is_offset: value === 'all' ? undefined : value === 'yes',
                })
              }
            >
              <SelectTrigger>
                <SelectValue placeholder="Todos" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todos</SelectItem>
                <SelectItem value="yes">Sim</SelectItem>
                <SelectItem value="no">Não</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Per\u00edodo */}
          <div className="flex-1 min-w-[140px]">
            <label className="block text-sm font-medium mb-2">Data in\u00edcio</label>
            <Input
              type="date"
              value={filters.date_from ?? ''}
              onChange={(e) =>
                onFiltersChange({
                  ...filters,
                  date_from: e.target.value || undefined,
                })
              }
            />
          </div>

          <div className="flex-1 min-w-[140px]">
            <label className="block text-sm font-medium mb-2">Data fim</label>
            <Input
              type="date"
              value={filters.date_to ?? ''}
              onChange={(e) =>
                onFiltersChange({
                  ...filters,
                  date_to: e.target.value || undefined,
                })
              }
            />
          </div>

          {hasActiveFilters && (
            <Button variant="outline" onClick={clearFilters}>
              Limpar Filtros
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
