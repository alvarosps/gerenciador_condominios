'use client';

import { X, CreditCard, Home, Banknote, UserMinus, Plus, Minus } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { formatCurrency } from '@/lib/utils/formatters';
import type { SimulationScenarioType } from '@/lib/api/hooks/use-simulation';

export interface ScenarioDisplayInfo {
  id: string;
  type: SimulationScenarioType;
  title: string;
  description: string;
  impact?: number;
}

const SCENARIO_ICONS: Record<SimulationScenarioType, typeof CreditCard> = {
  pay_off_early: CreditCard,
  change_rent: Home,
  new_loan: Banknote,
  remove_tenant: UserMinus,
  add_fixed_expense: Plus,
  remove_fixed_expense: Minus,
};

const SCENARIO_COLORS: Record<SimulationScenarioType, string> = {
  pay_off_early: 'text-success',
  change_rent: 'text-info',
  new_loan: 'text-destructive',
  remove_tenant: 'text-warning',
  add_fixed_expense: 'text-destructive',
  remove_fixed_expense: 'text-success',
};

interface ScenarioCardProps {
  scenario: ScenarioDisplayInfo;
  onRemove: (id: string) => void;
}

export function ScenarioCard({ scenario, onRemove }: ScenarioCardProps) {
  const Icon = SCENARIO_ICONS[scenario.type];
  const colorClass = SCENARIO_COLORS[scenario.type];

  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardContent className="p-3">
        <div className="flex items-start gap-2">
          <div className={`mt-0.5 ${colorClass}`}>
            <Icon className="h-4 w-4" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium truncate">{scenario.title}</p>
            <p className="text-xs text-muted-foreground truncate">{scenario.description}</p>
            {scenario.impact !== undefined && (
              <p
                className={`text-xs font-medium mt-1 ${scenario.impact >= 0 ? 'text-success' : 'text-destructive'}`}
              >
                {scenario.impact >= 0 ? '+' : ''}
                {formatCurrency(scenario.impact)}
              </p>
            )}
          </div>
          <Button
            variant="ghost"
            size="icon"
            className="h-6 w-6 shrink-0"
            onClick={() => onRemove(scenario.id)}
          >
            <X className="h-3 w-3" />
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
