# Reajuste Anual de Aluguel

**Data**: 2026-03-26
**Status**: Aprovado
**Escopo**: Reajuste anual de aluguel com percentual manual, histórico completo, alertas no dashboard, e atualização opcional do preço de tabela do apartamento.

## Contexto

Contratos de aluguel são reajustados anualmente com base no IGP-M/FGV. Atualmente não há mecanismo no sistema para registrar, aplicar ou acompanhar reajustes. Com a implementação do Spec 1 (Preço por Ocupação), `lease.rental_value` é agora a fonte da verdade do valor pago — este spec usa esse campo como base para os reajustes.

## Decisões de Design

1. **Percentual manual** — o usuário digita o percentual. Sem integração com API do Banco Central (YAGNI).
2. **Histórico completo** — tabela dedicada `RentAdjustment` com todos os reajustes, não apenas o último.
3. **Aniversário do contrato** — alertas baseados na `start_date` do lease. A cada 12 meses do início, o contrato é elegível para reajuste. Alerta 2 meses antes.
4. **Atualização do apartamento é opcional** — checkbox na modal. Quando marcado, atualiza `rental_value`, `rental_value_double` (proporcionalmente) e `last_rent_increase_date`.
5. **Ação no lease + dashboard** — botão na tabela de leases e ação direta nos alertas do dashboard.

## Spec Relacionado

- **Spec 1 — Preço por Ocupação** (implementado): criou `lease.rental_value` como fonte da verdade. Este spec atualiza esse campo ao aplicar reajuste.

---

## Mudanças no Backend

### 1. Novo Modelo: RentAdjustment

```
RentAdjustment (AuditMixin, SoftDeleteMixin):
  lease          FK(Lease, CASCADE, related_name="rent_adjustments")
  adjustment_date DateField
  percentage      DecimalField(max_digits=5, decimal_places=2)  # ex: 5.23
  previous_value  DecimalField(max_digits=10, decimal_places=2)
  new_value       DecimalField(max_digits=10, decimal_places=2)
  apartment_updated BooleanField(default=False)
```

- Herda AuditMixin (created_at, created_by, etc.) e SoftDeleteMixin
- Managers: `objects` (SoftDeleteManager) e `all_objects` (Manager)
- Ordering: `["-adjustment_date"]`
- Histórico é imutável — sem update/delete via API

### 2. Service: RentAdjustmentService

Arquivo: `core/services/rent_adjustment_service.py`

**`apply_adjustment(lease, percentage, update_apartment_prices) -> RentAdjustment`**:
1. Validação:
   - `percentage > 0` (reajuste é sempre aumento)
   - Lease deve estar ativo (não deletado, não expirado)
2. Cálculo: `new_value = lease.rental_value * (1 + percentage / 100)`, arredondado para 2 casas decimais
3. Cria `RentAdjustment` com `previous_value=lease.rental_value`, `new_value`, `percentage`, `adjustment_date=date.today()`
4. Atualiza `lease.rental_value = new_value`
5. Se `update_apartment_prices=True`:
   - Calcula fator: `factor = new_value / previous_value`
   - `apartment.rental_value = apartment.rental_value * factor` (arredondado)
   - Se `apartment.rental_value_double is not None`: `apartment.rental_value_double = apartment.rental_value_double * factor` (arredondado)
   - `apartment.last_rent_increase_date = date.today()`
   - Salva apartment
6. Retorna o `RentAdjustment` criado

**`get_eligible_leases(alert_months=2) -> list[dict]`** — para o dashboard:
1. Busca leases ativos (não deletados): `Lease.objects.filter(is_deleted=False)`
2. Filtra leases não expirados: `start_date + validity_months > today`
3. Para cada lease, calcula a próxima data de aniversário:
   - Pega `start_date`, calcula aniversários a cada 12 meses
   - Encontra o próximo aniversário (futuro ou passado recente)
4. Retorna leases onde: aniversário está dentro de `alert_months` meses no futuro OU já passou (atrasado)
5. Cada item retorna: `lease_id`, `apartment` (número + building), `tenant` (nome), `rental_value`, `anniversary_date`, `days_until` (negativo se atrasado), `status` ("upcoming" | "overdue"), `last_adjustment` (último RentAdjustment ou null)

**Validação adicional (warning, não bloqueio)**:
- Se já existe um reajuste nos últimos 10 meses para este lease, retornar warning no response (mas permitir aplicar)

### 3. Serializer: RentAdjustmentSerializer

```python
class RentAdjustmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = RentAdjustment
        fields = ["id", "lease", "adjustment_date", "percentage", "previous_value",
                  "new_value", "apartment_updated", "created_at", "created_by"]
        read_only_fields = fields  # Histórico é imutável
```

### 4. API Endpoints

**No LeaseViewSet** (actions no lease):

`POST /api/leases/{id}/adjust_rent/`
- Body: `{ "percentage": "5.23", "update_apartment_prices": true }`
- Validação: percentage > 0, lease ativo
- Response 200: `{ "id": 1, "previous_value": "1400.00", "new_value": "1473.22", "percentage": "5.23", "adjustment_date": "2026-03-26", "apartment_updated": true, "warning": null }`
- Response com warning: `{ ..., "warning": "Já existe um reajuste recente (15/01/2026) para este contrato." }`
- Permissão: `IsAdminUser`

`GET /api/leases/{id}/rent_adjustments/`
- Response: lista de `RentAdjustmentSerializer`, ordenada por `adjustment_date` desc
- Permissão: autenticado

**Novo endpoint no DashboardViewSet** (ou views.py):

`GET /api/dashboard/rent_adjustment_alerts/`
- Response: `{ "alerts": [...] }` — lista de leases elegíveis com info de aniversário
- Permissão: autenticado

### 5. Migration

- Nova tabela `core_rentadjustment`
- Sem data migration (tabela começa vazia)
- Sem alteração em tabelas existentes

### 6. Cache

- Invalidar cache de dashboard ao aplicar reajuste
- Invalidar cache de lease ao aplicar reajuste
- Adicionar signal handler para `RentAdjustment` se necessário

---

## Mudanças no Frontend

### 1. Modal de Reajuste (`rent-adjustment-modal.tsx`)

Nova componente em `frontend/app/(dashboard)/leases/_components/`:

- Props: `open`, `lease` (Lease), `onClose`
- Campos:
  - **Percentual** (input numérico, step 0.01, editável) — default vazio
  - **Checkbox** "Atualizar preço de tabela do apartamento" — default true
- Exibe em tempo real (calculado no frontend):
  - Valor atual: `lease.rental_value`
  - Valor novo: `lease.rental_value * (1 + percentage / 100)`
- Botão "Aplicar Reajuste"
- Toast de sucesso/erro

### 2. Tabela de Leases — Nova Ação

Em `lease-table-columns.tsx`:
- Adicionar botão "Reajustar" no dropdown de ações
- Visível apenas para leases ativos (não expirados)
- Abre `RentAdjustmentModal`

### 3. Histórico de Reajustes

Em `lease-table-columns.tsx` ou novo componente:
- Botão "Histórico de Reajustes" no dropdown de ações
- Abre Sheet/Drawer com tabela:
  - Colunas: Data, Percentual, Valor Anterior, Valor Novo, Apt. Atualizado, Aplicado por
  - Ordenado por data desc
- Usa `useRentAdjustments(leaseId)` hook

### 4. Dashboard — Widget de Alertas

Novo componente `rent-adjustment-alerts.tsx` no dashboard:
- Card "Reajustes Pendentes" com contador no título
- Lista de contratos elegíveis:
  - Cada item: "Apto 203 - 850 | Danielle | R$ 1.400,00 | Aniversário: 15/04/2026"
  - Badge: "Em 45 dias" (amarelo/warning), "Atrasado 15 dias" (vermelho/destructive)
- Botão "Reajustar" em cada item → abre `RentAdjustmentModal`
- Se nenhum alerta: mostra "Nenhum reajuste pendente"

### 5. Schemas (Zod)

Novo schema `rent-adjustment.schema.ts`:
```typescript
rentAdjustmentSchema = z.object({
  id: z.number(),
  lease: z.number(),
  adjustment_date: z.string(),
  percentage: z.string().or(z.number()).transform(Number),
  previous_value: z.string().or(z.number()).transform(Number),
  new_value: z.string().or(z.number()).transform(Number),
  apartment_updated: z.boolean(),
  created_at: z.string().optional(),
  created_by: z.number().nullable().optional(),
})
```

### 6. Hooks

`frontend/lib/api/hooks/use-rent-adjustments.ts`:

- `useApplyRentAdjustment()` — mutation POST `/leases/{id}/adjust_rent/`
  - Invalida: `['leases']`, `['apartments']`, `['dashboard']`, `['rent-adjustment-alerts']`
- `useRentAdjustments(leaseId)` — query GET `/leases/{id}/rent_adjustments/`
  - Key: `['rent-adjustments', leaseId]`
- `useRentAdjustmentAlerts()` — query GET `/dashboard/rent_adjustment_alerts/`
  - Key: `['rent-adjustment-alerts']`

---

## Testes

### Backend
- **Unit**: cálculo correto do novo valor (ex: 1400 * 5.23% = 1473.22)
- **Unit**: atualização proporcional de apartment.rental_value e rental_value_double
- **Unit**: `get_eligible_leases` retorna leases corretos (próximos de aniversário, exclui expirados)
- **Unit**: `get_eligible_leases` não retorna leases fora da janela de alerta
- **Integration**: `POST adjust_rent/` — cria RentAdjustment, atualiza lease.rental_value
- **Integration**: `POST adjust_rent/` com `update_apartment_prices=true` — atualiza apartment
- **Integration**: `POST adjust_rent/` com percentual <= 0 — retorna 400
- **Integration**: `POST adjust_rent/` em lease expirado — retorna 400
- **Integration**: `POST adjust_rent/` com reajuste recente — retorna warning mas aplica
- **Integration**: `GET rent_adjustments/` — retorna histórico ordenado
- **Integration**: `GET rent_adjustment_alerts/` — retorna alertas corretos

### Frontend
- **Hook tests**: `useApplyRentAdjustment` envia payload e invalida caches
- **Hook tests**: `useRentAdjustmentAlerts` parseia resposta
