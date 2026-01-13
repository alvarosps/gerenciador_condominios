'use client';

import { DependentFormList } from '../dependent-form-list';
import { StepProps } from './types';

export function DependentsStep({ formMethods }: StepProps) {
  return (
    <div>
      <div className="mb-6">
        <h3 className="text-lg font-medium">Dependentes</h3>
        <p className="text-sm text-muted-foreground">
          Adicione os dependentes que morarão no apartamento (opcional)
        </p>
      </div>
      <DependentFormList formMethods={formMethods} />
    </div>
  );
}
