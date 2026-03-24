'use client';

import { useRef, useState } from 'react';
import { Plus } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Loading } from '@/components/shared/loading';
import { useCashFlowProjection } from '@/lib/api/hooks/use-cash-flow';
import {
  useSimulation,
  type SimulationScenario,
  type SimulationResult,
} from '@/lib/api/hooks/use-simulation';
import { ScenarioBuilder } from './_components/scenario-builder';
import { ScenarioCard, type ScenarioDisplayInfo } from './_components/scenario-card';
import { ComparisonChart } from './_components/comparison-chart';
import { ComparisonTable } from './_components/comparison-table';
import { ImpactSummary } from './_components/impact-summary';

interface StoredScenario {
  scenario: SimulationScenario;
  display: ScenarioDisplayInfo;
}

export default function SimulatorPage() {
  const [scenarios, setScenarios] = useState<StoredScenario[]>([]);
  const [isAddingScenario, setIsAddingScenario] = useState(false);
  const [simulationResult, setSimulationResult] = useState<SimulationResult | null>(null);

  const { data: baseProjection, isLoading: isLoadingBase, error: baseError } = useCashFlowProjection(12);
  const simulation = useSimulation();
  const mutateRef = useRef(simulation.mutate);
  mutateRef.current = simulation.mutate;

  function runSimulation(currentScenarios: StoredScenario[]) {
    if (currentScenarios.length === 0) {
      setSimulationResult(null);
      return;
    }

    const apiScenarios = currentScenarios.map((s) => s.scenario);
    mutateRef.current(apiScenarios, {
      onSuccess: (data) => {
        setSimulationResult(data);
      },
      onError: () => {
        toast.error('Erro ao executar simulação. Tente novamente.');
      },
    });
  }

  function handleAddScenario(scenario: SimulationScenario, display: ScenarioDisplayInfo) {
    const updated = [...scenarios, { scenario, display }];
    setScenarios(updated);
    runSimulation(updated);
  }

  function handleRemoveScenario(id: string) {
    const updated = scenarios.filter((s) => s.display.id !== id);
    setScenarios(updated);
    runSimulation(updated);
  }

  const displayScenarios = scenarios.map((s) => s.display);

  if (isLoadingBase) {
    return (
      <div className="space-y-6">
        <h1 className="text-3xl font-bold">Simulador Financeiro</h1>
        <Loading />
      </div>
    );
  }

  if (baseError || !baseProjection) {
    return (
      <div className="space-y-6">
        <h1 className="text-3xl font-bold">Simulador Financeiro</h1>
        <p className="text-center text-muted-foreground py-8">
          Erro ao carregar projeção base. Verifique se há dados financeiros cadastrados.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">Simulador Financeiro</h1>

      {/* Comparison Chart — full width */}
      <ComparisonChart
        base={baseProjection}
        simulated={simulationResult?.simulated}
      />

      {/* Bottom section: scenarios sidebar + impact/table */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Scenarios panel */}
        <div className="lg:col-span-1 space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold">Cenários</h2>
            <Button size="sm" onClick={() => setIsAddingScenario(true)}>
              <Plus className="h-4 w-4 mr-1" />
              Cenário
            </Button>
          </div>

          {displayScenarios.length === 0 ? (
            <p className="text-sm text-muted-foreground py-4 text-center">
              Nenhum cenário adicionado. Clique em &quot;+ Cenário&quot; para simular.
            </p>
          ) : (
            displayScenarios.map((display) => (
              <ScenarioCard
                key={display.id}
                scenario={display}
                onRemove={handleRemoveScenario}
              />
            ))
          )}

          {simulation.isPending && (
            <p className="text-sm text-muted-foreground text-center py-2">Simulando...</p>
          )}
        </div>

        {/* Impact + Table */}
        <div className="lg:col-span-3 space-y-6">
          {simulationResult && (
            <>
              <ImpactSummary
                comparison={simulationResult.comparison}
                base={simulationResult.base}
                simulated={simulationResult.simulated}
              />
              <ComparisonTable months={simulationResult.comparison.month_by_month} />
            </>
          )}

          {!simulationResult && scenarios.length === 0 && (
            <div className="text-center py-12 text-muted-foreground">
              <p className="text-lg">Adicione cenários para ver o impacto financeiro</p>
              <p className="text-sm mt-1">
                Compare diferentes situações como quitar dívidas, alterar aluguéis ou simular novos
                empréstimos.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Scenario Builder Sheet */}
      <ScenarioBuilder
        open={isAddingScenario}
        onClose={() => setIsAddingScenario(false)}
        onAdd={handleAddScenario}
      />
    </div>
  );
}
