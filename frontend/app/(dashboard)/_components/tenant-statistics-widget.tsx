'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Loading } from '@/components/shared/loading';
import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { useDashboardTenantStatistics } from '@/lib/api/hooks/use-dashboard';
import { Users, User, Home, Building } from 'lucide-react';

export function TenantStatisticsWidget() {
  const { data, isLoading, error } = useDashboardTenantStatistics();

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Estatísticas de Inquilinos</CardTitle>
        </CardHeader>
        <CardContent>
          <Loading />
        </CardContent>
      </Card>
    );
  }

  if (error || !data) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Estatísticas de Inquilinos</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-center text-muted-foreground py-8">
            Erro ao carregar estatísticas
          </p>
        </CardContent>
      </Card>
    );
  }

  const pieData = [
    { name: 'Pessoas Físicas', value: data.person_tenants, color: '#3b82f6' },
    { name: 'Empresas', value: data.company_tenants, color: '#10b981' },
  ];

  const COLORS = ['#3b82f6', '#10b981'];

  const CustomTooltip = ({
    active,
    payload,
  }: {
    active?: boolean;
    payload?: Array<{ name: string; value: number; payload: { color: string } }>;
  }) => {
    if (active && payload && payload.length) {
      const dataItem = payload[0];
      const total = pieData[0].value + pieData[1].value;
      const percentage = total > 0 ? ((dataItem.value / total) * 100).toFixed(1) : '0';

      return (
        <div className="bg-card border rounded-lg shadow-lg p-3">
          <p className="font-medium">{dataItem.name}</p>
          <p className="text-lg font-bold" style={{ color: dataItem.payload.color }}>
            {dataItem.value} inquilinos
          </p>
          <p className="text-xs text-muted-foreground">{percentage}%</p>
        </div>
      );
    }
    return null;
  };

  const dependentsPercentage =
    data.total_tenants > 0 ? (data.tenants_with_dependents / data.total_tenants) * 100 : 0;

  const furniturePercentage =
    data.total_tenants > 0 ? (data.tenants_with_furniture / data.total_tenants) * 100 : 0;

  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardHeader>
        <CardTitle>Estatísticas de Inquilinos</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Pie Chart */}
          <div className="text-center">
            <div className="text-sm font-medium text-muted-foreground mb-4">
              Distribuição por Tipo
            </div>
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie
                  data={pieData}
                  dataKey="value"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  outerRadius={80}
                  label={(props) =>
                    `${props.value} (${(Number(props.percent || 0) * 100).toFixed(0)}%)`
                  }
                  labelLine={false}
                >
                  {pieData.map((_entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip content={<CustomTooltip />} />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </div>

          {/* Statistics */}
          <div className="space-y-4">
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm text-muted-foreground">
                <span>Total de Inquilinos</span>
                <Users className="h-4 w-4" />
              </div>
              <div className="text-3xl font-bold text-blue-500">{data.total_tenants}</div>
            </div>

            <div className="pt-4 border-t space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-sm text-muted-foreground flex items-center gap-2">
                  <User className="h-4 w-4" /> Com Dependentes
                </span>
                <span className="font-bold">
                  {data.tenants_with_dependents}
                  <span className="text-xs text-muted-foreground ml-2">
                    ({dependentsPercentage.toFixed(1)}%)
                  </span>
                </span>
              </div>

              <div className="flex justify-between items-center">
                <span className="text-sm text-muted-foreground">Média de Dependentes</span>
                <span className="font-bold text-lg">{data.avg_dependents.toFixed(1)}</span>
              </div>

              <div className="flex justify-between items-center pt-3 border-t">
                <span className="text-sm text-muted-foreground flex items-center gap-2">
                  <Home className="h-4 w-4" /> Com Móveis
                </span>
                <span className="font-bold">
                  {data.tenants_with_furniture}
                  <span className="text-xs text-muted-foreground ml-2">
                    ({furniturePercentage.toFixed(1)}%)
                  </span>
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Bottom Summary */}
        <div className="mt-6 pt-4 border-t grid grid-cols-2 gap-4">
          <div className="text-center">
            <div className="text-2xl font-bold text-blue-500">{data.person_tenants}</div>
            <div className="text-xs text-muted-foreground flex items-center justify-center gap-1 mt-1">
              <User className="h-3 w-3" /> Pessoas Físicas
            </div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-green-500">{data.company_tenants}</div>
            <div className="text-xs text-muted-foreground flex items-center justify-center gap-1 mt-1">
              <Building className="h-3 w-3" /> Empresas
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
