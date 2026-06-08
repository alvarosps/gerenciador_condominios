'use client';

import { useRef, useState } from 'react';
import { toast } from 'sonner';
import { Card, CardContent } from '@/components/ui/card';
import { Loading } from '@/components/shared/loading';
import { useAuthStore } from '@/store/auth-store';
import {
  useCondoProjection,
  useCondoSimulation,
  type CondoSimulationResult,
  type CondoSimulationScenario,
} from '@/lib/api/hooks/use-condo-projection';
import { ProjectionTable } from './_components/projection-table';
import { ProjectionChart } from './_components/projection-chart';
import { SimulationPanel } from './_components/simulation-panel';
import { SimulationComparison } from './_components/simulation-comparison';

const PROJECTION_MONTHS = 12;

export default function ProjectionPage() {
  const { user } = useAuthStore();
  const isAdmin = user?.is_staff ?? false;
  const { data: projection, isLoading, isError } = useCondoProjection(PROJECTION_MONTHS);
  const simulation = useCondoSimulation();
  // Stabilize the mutate callback without an eslint-disable (decision #13).
  const mutateRef = useRef(simulation.mutate);
  mutateRef.current = simulation.mutate;
  const [simulationResult, setSimulationResult] = useState<CondoSimulationResult | null>(null);

  function runSimulation(scenarios: CondoSimulationScenario[]) {
    if (scenarios.length === 0) {
      setSimulationResult(null);
      return;
    }
    mutateRef.current(
      { scenarios, months: PROJECTION_MONTHS },
      {
        onSuccess: (data) => setSimulationResult(data),
        onError: () => toast.error('Erro ao executar a simulação. Tente novamente.'),
      },
    );
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <h1 className="text-3xl font-bold">Projeção do condomínio</h1>
        <Loading />
      </div>
    );
  }

  if (isError || !projection) {
    return (
      <div className="space-y-6">
        <h1 className="text-3xl font-bold">Projeção do condomínio</h1>
        <p className="py-8 text-center text-muted-foreground">
          Erro ao carregar a projeção. Verifique se há dados financeiros cadastrados.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">Projeção do condomínio</h1>

      <ProjectionTable months={projection} />
      <ProjectionChart months={projection} />

      {isAdmin ? (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          <div className="lg:col-span-1">
            <SimulationPanel onSimulate={runSimulation} isPending={simulation.isPending} />
          </div>
          <div className="lg:col-span-2">
            {simulationResult ? (
              <SimulationComparison result={simulationResult} />
            ) : (
              <Card>
                <CardContent className="py-8 text-center text-muted-foreground">
                  Adicione um cenário para simular o impacto no caixa projetado.
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      ) : (
        <p className="text-sm text-muted-foreground">
          O simulador está disponível apenas para administradores.
        </p>
      )}
    </div>
  );
}
