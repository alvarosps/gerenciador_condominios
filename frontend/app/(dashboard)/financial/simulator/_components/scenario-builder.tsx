'use client';

import { useState } from 'react';
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetFooter,
} from '@/components/ui/sheet';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useExpenses } from '@/lib/api/hooks/use-expenses';
import { useApartments } from '@/lib/api/hooks/use-apartments';
import { formatCurrency } from '@/lib/utils/formatters';
import type { SimulationScenario, SimulationScenarioType } from '@/lib/api/hooks/use-simulation';
import type { ScenarioDisplayInfo } from './scenario-card';

const SCENARIO_TYPE_OPTIONS: { value: SimulationScenarioType; label: string }[] = [
  { value: 'pay_off_early', label: 'Quitar Despesa Antecipada' },
  { value: 'change_rent', label: 'Alterar Aluguel' },
  { value: 'new_loan', label: 'Novo Empréstimo' },
  { value: 'remove_tenant', label: 'Remover Inquilino' },
  { value: 'add_fixed_expense', label: 'Adicionar Gasto Fixo' },
  { value: 'remove_fixed_expense', label: 'Remover Gasto Fixo' },
];

interface ScenarioBuilderProps {
  open: boolean;
  onClose: () => void;
  onAdd: (scenario: SimulationScenario, display: ScenarioDisplayInfo) => void;
}

export function ScenarioBuilder({ open, onClose, onAdd }: ScenarioBuilderProps) {
  const [scenarioType, setScenarioType] = useState<SimulationScenarioType | ''>('');
  const [expenseId, setExpenseId] = useState('');
  const [apartmentId, setApartmentId] = useState('');
  const [amount, setAmount] = useState('');
  const [installments, setInstallments] = useState('');
  const [startMonth, setStartMonth] = useState('');
  const [description, setDescription] = useState('');
  const [newRentValue, setNewRentValue] = useState('');

  const { data: installmentExpenses } = useExpenses({ is_paid: false });
  const { data: rentedApartments } = useApartments({ is_rented: true });
  const { data: allApartments } = useApartments();
  const { data: fixedExpenses } = useExpenses({ is_recurring: true });

  const activeInstallmentExpenses =
    installmentExpenses?.filter((e) => e.is_installment && !e.is_paid) ?? [];
  const activeFixedExpenses = fixedExpenses?.filter((e) => e.is_recurring && !e.is_paid) ?? [];

  function resetForm() {
    setScenarioType('');
    setExpenseId('');
    setApartmentId('');
    setAmount('');
    setInstallments('');
    setStartMonth('');
    setDescription('');
    setNewRentValue('');
  }

  function handleClose() {
    resetForm();
    onClose();
  }

  function handleSubmit() {
    if (!scenarioType) return;

    let scenario: SimulationScenario;
    let display: ScenarioDisplayInfo;
    const id = `${scenarioType}-${Date.now()}`;

    switch (scenarioType) {
      case 'pay_off_early': {
        const expense = activeInstallmentExpenses.find((e) => e.id === Number(expenseId));
        if (!expense) return;
        scenario = { type: 'pay_off_early', expense_id: expense.id };
        display = {
          id,
          type: 'pay_off_early',
          title: 'Quitar Antecipada',
          description: `${expense.description} — ${expense.remaining_installments ?? 0} parcelas restantes`,
        };
        break;
      }
      case 'change_rent': {
        const apartment = allApartments?.find((a) => a.id === Number(apartmentId));
        if (!apartment || !newRentValue) return;
        scenario = {
          type: 'change_rent',
          apartment_id: apartment.id,
          new_value: Number(newRentValue),
        };
        display = {
          id,
          type: 'change_rent',
          title: 'Alterar Aluguel',
          description: `Apto ${apartment.number} — ${formatCurrency(apartment.rental_value)} → ${formatCurrency(Number(newRentValue))}`,
        };
        break;
      }
      case 'new_loan': {
        if (!amount || !installments || !startMonth) return;
        scenario = {
          type: 'new_loan',
          amount: Number(amount),
          installments: Number(installments),
          start_month: startMonth,
        };
        display = {
          id,
          type: 'new_loan',
          title: 'Novo Empréstimo',
          description: `${Number(installments)}x de ${formatCurrency(Number(amount))}`,
        };
        break;
      }
      case 'remove_tenant': {
        const apartment = rentedApartments?.find((a) => a.id === Number(apartmentId));
        if (!apartment) return;
        scenario = { type: 'remove_tenant', apartment_id: apartment.id };
        display = {
          id,
          type: 'remove_tenant',
          title: 'Remover Inquilino',
          description: `Apto ${apartment.number} — perda de ${formatCurrency(apartment.rental_value)}/mês`,
        };
        break;
      }
      case 'add_fixed_expense': {
        if (!amount) return;
        scenario = {
          type: 'add_fixed_expense',
          amount: Number(amount),
          description: description || 'Despesa fixa (simulação)',
        };
        display = {
          id,
          type: 'add_fixed_expense',
          title: 'Novo Gasto Fixo',
          description: `${description || 'Despesa fixa'} — ${formatCurrency(Number(amount))}/mês`,
        };
        break;
      }
      case 'remove_fixed_expense': {
        const expense = activeFixedExpenses.find((e) => e.id === Number(expenseId));
        if (!expense) return;
        scenario = { type: 'remove_fixed_expense', expense_id: expense.id };
        display = {
          id,
          type: 'remove_fixed_expense',
          title: 'Remover Gasto Fixo',
          description: `${expense.description} — ${formatCurrency(expense.expected_monthly_amount ?? 0)}/mês`,
        };
        break;
      }
    }

    onAdd(scenario, display);
    handleClose();
  }

  const selectedApartment = allApartments?.find((a) => a.id === Number(apartmentId));

  return (
    <Sheet open={open} onOpenChange={(isOpen) => !isOpen && handleClose()}>
      <SheetContent className="sm:max-w-md">
        <SheetHeader>
          <SheetTitle>Adicionar Cenário</SheetTitle>
        </SheetHeader>

        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label>Tipo de Cenário</Label>
            <Select
              value={scenarioType}
              onValueChange={(v) => {
                setScenarioType(v as SimulationScenarioType);
                setExpenseId('');
                setApartmentId('');
                setAmount('');
                setInstallments('');
                setStartMonth('');
                setDescription('');
                setNewRentValue('');
              }}
            >
              <SelectTrigger>
                <SelectValue placeholder="Selecione o tipo..." />
              </SelectTrigger>
              <SelectContent>
                {SCENARIO_TYPE_OPTIONS.map((opt) => (
                  <SelectItem key={opt.value} value={opt.value}>
                    {opt.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {scenarioType === 'pay_off_early' && (
            <div className="space-y-2">
              <Label>Despesa Parcelada</Label>
              <Select value={expenseId} onValueChange={setExpenseId}>
                <SelectTrigger>
                  <SelectValue placeholder="Selecione a despesa..." />
                </SelectTrigger>
                <SelectContent>
                  {activeInstallmentExpenses.map((e) => (
                    <SelectItem key={e.id} value={String(e.id)}>
                      {e.description} — {e.remaining_installments ?? 0} parcelas,{' '}
                      {formatCurrency(e.total_remaining ?? 0)} restante
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}

          {scenarioType === 'change_rent' && (
            <>
              <div className="space-y-2">
                <Label>Apartamento</Label>
                <Select value={apartmentId} onValueChange={setApartmentId}>
                  <SelectTrigger>
                    <SelectValue placeholder="Selecione o apartamento..." />
                  </SelectTrigger>
                  <SelectContent>
                    {(allApartments ?? [])
                      .filter((a) => a.is_rented)
                      .map((a) => (
                        <SelectItem key={a.id} value={String(a.id)}>
                          Apto {a.number} —{' '}
                          {a.building ? `Prédio ${a.building.street_number}` : ''} —{' '}
                          {formatCurrency(a.rental_value)}
                        </SelectItem>
                      ))}
                  </SelectContent>
                </Select>
              </div>
              {selectedApartment && (
                <p className="text-sm text-muted-foreground">
                  Valor atual: {formatCurrency(selectedApartment.rental_value)}
                </p>
              )}
              <div className="space-y-2">
                <Label>Novo Valor (R$)</Label>
                <Input
                  type="number"
                  step="0.01"
                  min="0"
                  value={newRentValue}
                  onChange={(e) => setNewRentValue(e.target.value)}
                  placeholder="0,00"
                />
              </div>
            </>
          )}

          {scenarioType === 'new_loan' && (
            <>
              <div className="space-y-2">
                <Label>Valor da Parcela (R$)</Label>
                <Input
                  type="number"
                  step="0.01"
                  min="0"
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                  placeholder="0,00"
                />
              </div>
              <div className="space-y-2">
                <Label>Número de Parcelas</Label>
                <Input
                  type="number"
                  min="1"
                  value={installments}
                  onChange={(e) => setInstallments(e.target.value)}
                  placeholder="12"
                />
              </div>
              <div className="space-y-2">
                <Label>Mês Inicial</Label>
                <Input
                  type="month"
                  value={startMonth}
                  onChange={(e) => setStartMonth(e.target.value)}
                />
              </div>
            </>
          )}

          {scenarioType === 'remove_tenant' && (
            <div className="space-y-2">
              <Label>Apartamento Ocupado</Label>
              <Select value={apartmentId} onValueChange={setApartmentId}>
                <SelectTrigger>
                  <SelectValue placeholder="Selecione o apartamento..." />
                </SelectTrigger>
                <SelectContent>
                  {(rentedApartments ?? []).map((a) => (
                    <SelectItem key={a.id} value={String(a.id)}>
                      Apto {a.number} — {a.building ? `Prédio ${a.building.street_number}` : ''} —{' '}
                      {formatCurrency(a.rental_value)}/mês
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}

          {scenarioType === 'add_fixed_expense' && (
            <>
              <div className="space-y-2">
                <Label>Descrição</Label>
                <Input
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Ex: Internet, Seguro..."
                />
              </div>
              <div className="space-y-2">
                <Label>Valor Mensal (R$)</Label>
                <Input
                  type="number"
                  step="0.01"
                  min="0"
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                  placeholder="0,00"
                />
              </div>
            </>
          )}

          {scenarioType === 'remove_fixed_expense' && (
            <div className="space-y-2">
              <Label>Gasto Fixo</Label>
              <Select value={expenseId} onValueChange={setExpenseId}>
                <SelectTrigger>
                  <SelectValue placeholder="Selecione o gasto fixo..." />
                </SelectTrigger>
                <SelectContent>
                  {activeFixedExpenses.map((e) => (
                    <SelectItem key={e.id} value={String(e.id)}>
                      {e.description} — {formatCurrency(e.expected_monthly_amount ?? 0)}/mês
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}
        </div>

        <SheetFooter>
          <Button variant="outline" onClick={handleClose}>
            Cancelar
          </Button>
          <Button onClick={handleSubmit} disabled={!scenarioType}>
            Adicionar
          </Button>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  );
}
