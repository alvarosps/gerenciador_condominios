'use client';

import { useState } from 'react';
import { Plus, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { formatCurrency } from '@/lib/utils/formatters';
import type {
  CondoScenarioType,
  CondoSimulationScenario,
} from '@/lib/api/hooks/use-condo-projection';

interface ScenarioOption {
  value: CondoScenarioType;
  label: string;
  field: 'amount' | 'delta';
}

const DEFAULT_SCENARIO_OPTION: ScenarioOption = {
  value: 'add_expense',
  label: 'Gasto extra (mensal)',
  field: 'amount',
};

const SCENARIO_OPTIONS: ScenarioOption[] = [
  DEFAULT_SCENARIO_OPTION,
  { value: 'remove_expense', label: 'Reduzir gasto (mensal)', field: 'amount' },
  { value: 'add_income', label: 'Receita extra (mensal)', field: 'amount' },
  { value: 'change_rent', label: 'Ajustar aluguel (delta)', field: 'delta' },
];

function optionFor(type: CondoScenarioType): ScenarioOption {
  return SCENARIO_OPTIONS.find((o) => o.value === type) ?? DEFAULT_SCENARIO_OPTION;
}

function isScenarioType(value: string): value is CondoScenarioType {
  return SCENARIO_OPTIONS.some((o) => o.value === value);
}

interface SimulationPanelProps {
  onSimulate: (scenarios: CondoSimulationScenario[]) => void;
  isPending: boolean;
}

export function SimulationPanel({ onSimulate, isPending }: SimulationPanelProps) {
  const [scenarios, setScenarios] = useState<CondoSimulationScenario[]>([]);
  const [type, setType] = useState<CondoScenarioType>('add_expense');
  const [value, setValue] = useState('');
  const [monthsWindow, setMonthsWindow] = useState('');

  function commit(next: CondoSimulationScenario[]) {
    setScenarios(next);
    onSimulate(next);
  }

  function handleAdd() {
    const magnitude = Number(value);
    // Reject empty/non-numeric, a zero (no-op for every type), and a negative for the
    // amount-based types (only change_rent's delta may be negative).
    if (!value.trim() || Number.isNaN(magnitude) || magnitude === 0) return;
    if (type !== 'change_rent' && magnitude < 0) return;
    const windowField = monthsWindow.trim() ? { months: Number(monthsWindow) } : {};
    const scenario: CondoSimulationScenario =
      type === 'change_rent'
        ? { type, delta: value, ...windowField }
        : { type, amount: value, ...windowField };
    commit([...scenarios, scenario]);
    setValue('');
    setMonthsWindow('');
  }

  function handleRemove(index: number) {
    commit(scenarios.filter((_, i) => i !== index));
  }

  function scenarioValue(scenario: CondoSimulationScenario): string {
    return scenario.delta ?? scenario.amount ?? '0';
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Simulador (what-if)</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <Label>Tipo de cenário</Label>
          <Select
            value={type}
            onValueChange={(v) => {
              if (isScenarioType(v)) setType(v);
            }}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {SCENARIO_OPTIONS.map((option) => (
                <SelectItem key={option.value} value={option.value}>
                  {option.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <Label>{optionFor(type).field === 'delta' ? 'Delta (R$)' : 'Valor (R$)'}</Label>
          <Input
            type="number"
            step="0.01"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder="0,00"
          />
        </div>
        <div className="space-y-2">
          <Label>Meses afetados (opcional)</Label>
          <Input
            type="number"
            min={0}
            value={monthsWindow}
            onChange={(e) => setMonthsWindow(e.target.value)}
            placeholder="todos os meses futuros"
          />
        </div>
        <Button type="button" onClick={handleAdd} disabled={isPending} className="w-full">
          <Plus className="mr-2 h-4 w-4" /> Adicionar cenário
        </Button>

        {scenarios.length > 0 && (
          <ul className="space-y-2">
            {scenarios.map((scenario, index) => (
              <li
                key={`${scenario.type}-${index}`}
                className="flex items-center justify-between rounded-md border px-3 py-2 text-sm"
              >
                <span>
                  {optionFor(scenario.type).label}: {formatCurrency(scenarioValue(scenario))}
                  {scenario.months !== undefined ? ` (${String(scenario.months)} m)` : ''}
                </span>
                <button
                  type="button"
                  onClick={() => handleRemove(index)}
                  aria-label="Remover cenário"
                  className="text-muted-foreground hover:text-destructive"
                >
                  <X className="h-4 w-4" />
                </button>
              </li>
            ))}
          </ul>
        )}
        {isPending && <p className="text-sm text-muted-foreground">Simulando...</p>}
      </CardContent>
    </Card>
  );
}
