# Mock Data para Desenvolvimento

Este diretório contém dados mock completos para o desenvolvimento da aplicação de gerenciamento de condomínios.

## Estrutura dos Dados

### 📁 Arquivos Disponíveis

- **`buildings.ts`** - 5 edifícios com endereços realistas
- **`furnitures.ts`** - 12 móveis/eletrodomésticos diferentes
- **`dependents.ts`** - 8 dependentes distribuídos entre os inquilinos
- **`tenants.ts`** - 15 inquilinos (pessoas físicas e jurídicas)
- **`apartments.ts`** - 20 apartamentos distribuídos pelos edifícios
- **`leases.ts`** - 15 contratos de locação
- **`index.ts`** - Exportações centralizadas + utilitários
- **`examples.ts`** - Exemplos de uso nos componentes

## 📊 Estatísticas dos Dados Mock

| Tipo | Quantidade | Detalhes |
|------|------------|----------|
| Edifícios | 5 | Números: 836, 850, 920, 1024, 1150 |
| Apartamentos | 20 | 13 ocupados (65%), 7 vagos (35%) |
| Inquilinos | 15 | 12 pessoas físicas, 3 empresas |
| Contratos | 15 | 13 ativos, 2 pendentes de assinatura |
| Receita Mensal | ~R$ 27.450 | Soma dos contratos ativos |

## 🚀 Como Usar

### 1. Importação Básica

```typescript
import { 
  mockBuildings, 
  mockApartments, 
  mockTenants,
  mockLeases,
  mockDataUtils 
} from '../mocks';
```

### 2. Utilizando Estatísticas Prontas

```typescript
import { mockDataUtils } from '../mocks';

// Estatísticas básicas
const totalBuildings = mockDataUtils.getTotalBuildings(); // 5
const occupancyRate = mockDataUtils.getOccupancyRate(); // 65%
const monthlyRevenue = mockDataUtils.getMonthlyRevenue(); // R$ 27.450

// Filtros
const apartmentsInBuilding836 = mockDataUtils.getApartmentsByBuilding(1);
```

### 3. Usando em Componentes React

```typescript
import { getDashboardStats } from '../mocks/examples';

const Dashboard = () => {
  const stats = getDashboardStats();
  
  return (
    <div className="grid grid-cols-4 gap-4">
      <div className="bg-white p-4 rounded-lg shadow">
        <h3>Edifícios</h3>
        <p className="text-2xl font-bold">{stats.totalBuildings}</p>
      </div>
      <div className="bg-white p-4 rounded-lg shadow">
        <h3>Taxa de Ocupação</h3>
        <p className="text-2xl font-bold">{stats.occupancyRate.toFixed(1)}%</p>
      </div>
    </div>
  );
};
```

## 📋 Dados de Exemplo

### Edifícios
- **Residencial Vila Nova** (836) - 10 apartamentos
- **Condomínio Jardim Paulista** (850) - 5 apartamentos  
- **Edifício Central Plaza** (920) - 2 apartamentos
- **Residencial São Jorge** (1024) - 1 apartamento
- **Condomínio Bella Vista** (1150) - 2 apartamentos

### Inquilinos Exemplo
- **Carlos Santos Silva** - Engenheiro, casado, 2 dependentes
- **Ana Beatriz Mendes** - Médica, solteira
- **TechSolutions Ltda** - Empresa de tecnologia
- **Consultoria Empresarial S/A** - Consultoria

### Situações Simuladas
- ✅ Contratos assinados e ativos
- ⏳ Contratos gerados mas não assinados
- ⚠️ 1 inquilino com advertência
- 💰 Diferentes valores de aluguel (R$ 1.750 - R$ 3.200)
- 🏠 Apartamentos mobiliados e não mobiliados

## 🛠️ Utilitários Disponíveis

### Estatísticas de Dashboard
```typescript
mockDataUtils.getTotalBuildings()
mockDataUtils.getTotalApartments()
mockDataUtils.getOccupiedApartments()
mockDataUtils.getVacantApartments()
mockDataUtils.getOccupancyRate()
mockDataUtils.getTotalTenants()
mockDataUtils.getMonthlyRevenue()
```

### Filtros e Consultas
```typescript
mockDataUtils.getApartmentsByBuilding(buildingId)
mockDataUtils.getActiveLeases()
mockDataUtils.getPendingLeases()
mockDataUtils.getContractsToSign()
mockDataUtils.getContractsWithWarnings()
mockDataUtils.getRecentActivities()
```

## 🎯 Casos de Uso para Cada Página

### Dashboard
- Cartões de estatísticas gerais
- Gráfico de ocupação por edifício
- Timeline de atividades recentes
- Alertas de contratos pendentes

### Edifícios
- Lista de edifícios com estatísticas
- Ocupação por edifício
- Receita mensal por edifício

### Apartamentos
- Lista com filtros (edifício, status, valor)
- Status de ocupação
- Móveis inclusos

### Inquilinos
- Lista de pessoas físicas/jurídicas
- Dependentes
- Móveis próprios
- Status de pagamento

### Contratos
- Lista de contratos ativos/pendentes
- Datas de vencimento
- Valores e taxas
- Advertências

### Móveis
- Catálogo de móveis disponíveis
- Associação com apartamentos/inquilinos

## 🔄 Atualizando os Dados

Para adicionar novos dados ou modificar existentes:

1. Edite os arquivos específicos (`buildings.ts`, `apartments.ts`, etc.)
2. Mantenha a consistência dos IDs entre entidades relacionadas
3. Atualize as estatísticas em `mockDataUtils` se necessário
4. Teste as relações entre entidades

## 📝 Tipos TypeScript

Todos os dados seguem as interfaces definidas em `src/types/index.ts`:
- `Building`
- `Apartment` 
- `Tenant`
- `Dependent`
- `Lease`
- `Furniture`

## 🧪 Testando

Para verificar se os dados estão corretos:

```typescript
import { mockDataUtils } from '../mocks';

console.log('Estatísticas:', {
  buildings: mockDataUtils.getTotalBuildings(),
  apartments: mockDataUtils.getTotalApartments(),
  occupancy: mockDataUtils.getOccupancyRate(),
  revenue: mockDataUtils.getMonthlyRevenue()
});
```

---

💡 **Dica**: Use o arquivo `examples.ts` como referência para implementar funcionalidades nas páginas da aplicação. 