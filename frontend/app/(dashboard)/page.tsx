'use client';

import { Card } from 'antd';

export default function DashboardPage() {
  return (
    <div>
      <h1 className="text-3xl font-bold mb-6">Dashboard</h1>
      <Card>
        <p>Bem-vindo ao Condomínios Manager!</p>
        <p className="mt-2">Use o menu lateral para navegar entre os módulos.</p>
      </Card>
    </div>
  );
}
