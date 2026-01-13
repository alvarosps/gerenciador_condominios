'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Loading } from '@/components/shared/loading';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import { useDashboardBuildingStatistics } from '@/lib/api/hooks/use-dashboard';
import { formatCurrency } from '@/lib/utils/formatters';

interface ChartDataItem {
  name: string;
  'Ocupação (%)': number;
  'Receita (R$ mil)': number;
  apartamentos: number;
  alugados: number;
}

export function BuildingStatisticsChart() {
  const { data, isLoading, error } = useDashboardBuildingStatistics();

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Estatísticas por Prédio</CardTitle>
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
          <CardTitle>Estatísticas por Prédio</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-center text-muted-foreground py-8">
            Erro ao carregar estatísticas
          </p>
        </CardContent>
      </Card>
    );
  }

  if (data.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Estatísticas por Prédio</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-center text-muted-foreground py-8">
            Nenhum prédio cadastrado
          </p>
        </CardContent>
      </Card>
    );
  }

  const chartData: ChartDataItem[] = data.map((stat) => {
    const revenue = typeof stat.total_revenue === 'string'
      ? parseFloat(stat.total_revenue)
      : stat.total_revenue;
    return {
      name: `Prédio ${stat.building_number}`,
      'Ocupação (%)': Number(stat.occupancy_rate.toFixed(1)),
      'Receita (R$ mil)': Number((revenue / 1000).toFixed(2)),
      apartamentos: stat.total_apartments,
      alugados: stat.rented_apartments,
    };
  });

  const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'];

  const CustomTooltip = ({
    active,
    payload,
    label,
  }: {
    active?: boolean;
    payload?: Array<{ payload: ChartDataItem }>;
    label?: string;
  }) => {
    if (active && payload && payload.length) {
      const dataItem = payload[0].payload;
      return (
        <div className="bg-card border rounded-lg shadow-lg p-4">
          <p className="font-bold mb-2">{label}</p>
          <p className="text-sm">
            <span className="text-muted-foreground">Apartamentos: </span>
            <span className="font-medium">
              {dataItem.alugados}/{dataItem.apartamentos}
            </span>
          </p>
          <p className="text-sm">
            <span className="text-muted-foreground">Ocupação: </span>
            <span className="font-medium text-blue-500">
              {dataItem['Ocupação (%)']}%
            </span>
          </p>
          <p className="text-sm">
            <span className="text-muted-foreground">Receita: </span>
            <span className="font-medium text-green-500">
              {formatCurrency(dataItem['Receita (R$ mil)'] * 1000)}
            </span>
          </p>
        </div>
      );
    }
    return null;
  };

  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardHeader>
        <CardTitle>Estatísticas por Prédio</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={350}>
          <BarChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
            <XAxis
              dataKey="name"
              angle={-45}
              textAnchor="end"
              height={100}
              interval={0}
              className="text-xs"
            />
            <YAxis
              yAxisId="left"
              orientation="left"
              label={{ value: 'Ocupação (%)', angle: -90, position: 'insideLeft' }}
              className="text-xs"
            />
            <YAxis
              yAxisId="right"
              orientation="right"
              label={{ value: 'Receita (R$ mil)', angle: 90, position: 'insideRight' }}
              className="text-xs"
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend />
            <Bar yAxisId="left" dataKey="Ocupação (%)" fill="#3b82f6" radius={[8, 8, 0, 0]}>
              {chartData.map((_entry, index) => (
                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
              ))}
            </Bar>
            <Bar
              yAxisId="right"
              dataKey="Receita (R$ mil)"
              fill="#10b981"
              radius={[8, 8, 0, 0]}
            />
          </BarChart>
        </ResponsiveContainer>

        <div className="mt-6 pt-4 border-t">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
            <div>
              <div className="text-2xl font-bold text-blue-500">{data.length}</div>
              <div className="text-xs text-muted-foreground">Prédios</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-green-500">
                {data.reduce((sum, b) => sum + b.total_apartments, 0)}
              </div>
              <div className="text-xs text-muted-foreground">Total Aptos</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-orange-500">
                {data.reduce((sum, b) => sum + b.rented_apartments, 0)}
              </div>
              <div className="text-xs text-muted-foreground">Aptos Alugados</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-purple-500">
                {formatCurrency(
                  data.reduce((sum, b) => {
                    const revenue = typeof b.total_revenue === 'string'
                      ? parseFloat(b.total_revenue)
                      : b.total_revenue;
                    return sum + revenue;
                  }, 0)
                )}
              </div>
              <div className="text-xs text-muted-foreground">Receita Total</div>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
