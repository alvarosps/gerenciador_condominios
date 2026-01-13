'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useFurniture } from '@/lib/api/hooks/use-furniture';
import { formatCPFOrCNPJ, formatBrazilianPhone } from '@/lib/utils/formatters';
import { StepProps } from './types';

export function ReviewStep({ formMethods }: StepProps) {
  const { data: furniture } = useFurniture();
  const values = formMethods.getValues();

  return (
    <div>
      <div className="mb-6">
        <h3 className="text-lg font-medium">Revise os Dados</h3>
        <p className="text-sm text-muted-foreground">
          Confira todas as informações antes de salvar
        </p>
      </div>

      <Card className="mb-4">
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Dados Básicos</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2 text-sm">
            <div>
              <strong>Nome:</strong> {values.name}
            </div>
            <div>
              <strong>Tipo:</strong>{' '}
              {values.is_company ? 'Pessoa Jurídica' : 'Pessoa Física'}
            </div>
            <div>
              <strong>CPF/CNPJ:</strong> {formatCPFOrCNPJ(values.cpf_cnpj || '')}
            </div>
          </div>
        </CardContent>
      </Card>

      <Card className="mb-4">
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Contato</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2 text-sm">
            <div>
              <strong>Telefone:</strong> {formatBrazilianPhone(values.phone || '')}
            </div>
            {values.phone_alternate && (
              <div>
                <strong>Tel. Alternativo:</strong>{' '}
                {formatBrazilianPhone(values.phone_alternate)}
              </div>
            )}
            {values.email && (
              <div>
                <strong>Email:</strong> {values.email}
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      <Card className="mb-4">
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Informações Profissionais</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2 text-sm">
            <div>
              <strong>Profissão:</strong> {values.profession}
            </div>
            <div>
              <strong>Estado Civil:</strong> {values.marital_status}
            </div>
          </div>
        </CardContent>
      </Card>

      {values.dependents && values.dependents.length > 0 && (
        <Card className="mb-4">
          <CardHeader className="pb-3">
            <CardTitle className="text-base">
              Dependentes ({values.dependents.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {values.dependents.map(
                (dep: { name: string; phone: string }, index: number) => (
                  <div key={index} className="text-sm pl-4 border-l-2 border-primary">
                    <div>
                      <strong>{dep.name}</strong>
                    </div>
                    <div className="text-muted-foreground">
                      {formatBrazilianPhone(dep.phone)}
                    </div>
                  </div>
                )
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {values.furniture_ids && values.furniture_ids.length > 0 && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">
              Móveis ({values.furniture_ids.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-sm">
              {furniture
                ?.filter((f) => values.furniture_ids?.includes(f.id!))
                .map((f) => f.name)
                .join(', ')}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
