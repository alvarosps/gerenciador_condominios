# Reajuste Anual de Aluguel

**Data**: 2026-03-26
**Status**: Aprovado
**Escopo**: Reajuste anual de aluguel com percentual manual, histórico completo, alertas no dashboard, e atualização opcional do preço de tabela do apartamento.

## Contexto

Contratos de aluguel são reajustados anualmente com base no IGP-M/FGV. Atualmente não há mecanismo no sistema para registrar, aplicar ou acompanhar reajustes. Com a implementação do Spec 1 (Preço por Ocupação), `lease.rental_value` é agora a fonte da verdade do valor pago — este spec usa esse campo como base para os reajustes.

## Decisões de Design

1. **Percentual manual** — o usuário digita o percentual (positivo ou negativo). Sem integração com API do Banco Central (YAGNI). IGP-M pode ser negativo em alguns períodos.
2. **Histórico completo** — tabela dedicada `RentAdjustment` com todos os reajustes, não apenas o último.
3. **Aniversário do contrato** — alertas baseados na data de referência: último reajuste (`RentAdjustment.adjustment_date`) ou `start_date` se nunca reajustado. A cada 12 meses da referência, o contrato é elegível. Alerta 2 meses antes.
4. **Atualização do apartamento é opcional** — checkbox na modal. Quando marcado, aplica o mesmo percentual diretamente sobre `rental_value`, `rental_value_double` e atualiza `last_rent_increase_date`.
5. **Ação no lease + dashboard** — botão na tabela de leases e ação direta nos alertas do dashboard.
6. **Leases especiais** — `is_salary_offset=True` são excluídos dos alertas (compensação salarial, não aluguel de mercado). `prepaid_until` são incluídos mas com aviso.

## Definição: Lease Ativo

Um lease é considerado "ativo" quando:
- `is_deleted = False` (SoftDeleteManager já filtra)
- Não expirado: `start_date + relativedelta(months=validity_months) > date.today()`

Nota: na legislação brasileira, leases continuam mês a mês após o término do prazo mínimo. Um lease "expirado" no sistema pode ainda estar ativo na prática. Para este spec, usamos a definição acima — leases expirados no sistema não recebem alertas. Se necessário no futuro, pode-se adicionar um campo `is_active_override`.

## Spec Relacionado

- **Spec 1 — Preço por Ocupação** (implementado): criou `lease.rental_value` como fonte da verdade. Este spec atualiza esse campo ao aplicar reajuste.

---

## Mudanças no Backend

### 1. Novo Modelo: RentAdjustment

```
RentAdjustment (AuditMixin, SoftDeleteMixin):
  lease            FK(Lease, CASCADE, related_name="rent_adjustments")
  adjustment_date  DateField
  percentage       DecimalField(max_digits=5, decimal_places=2)  # ex: 5.23 ou -0.64
  previous_value   DecimalField(max_digits=10, decimal_places=2)
  new_value        DecimalField(max_digits=10, decimal_places=2)
  apartment_updated BooleanField(default=False)
```

- Herda AuditMixin (created_at, created_by, etc.) e SoftDeleteMixin
- Managers: `objects` (SoftDeleteManager) e `all_objects` (Manager)
- Ordering: `["-adjustment_date"]`
- Histórico é imutável — sem update/delete via API
- Não precisa de ViewSet próprio — acessado via actions no LeaseViewSet

### 2. Service: RentAdjustmentService

Arquivo: `core/services/rent_adjustment_service.py`

**`apply_adjustment(lease, percentage, update_apartment_prices) -> RentAdjustment`**:

Deve ser envolvido em `@transaction.atomic` para garantir consistência (modifica até 3 registros: RentAdjustment, Lease, Apartment).

1. Validação:
   - `percentage != 0` (0% não é reajuste)
   - Lease deve estar ativo (não deletado, não expirado — ver definição acima)
2. Cálculo: `new_value = lease.rental_value * (1 + percentage / 100)`, arredondado para 2 casas decimais
3. Cria `RentAdjustment` com `previous_value=lease.rental_value`, `new_value`, `percentage`, `adjustment_date=date.today()`
4. Atualiza `lease.rental_value = new_value`, salva lease
5. Se `update_apartment_prices=True`:
   - Aplica o mesmo percentual diretamente: `apartment.rental_value = apartment.rental_value * (1 + percentage / 100)` (arredondado)
   - Se `apartment.rental_value_double is not None`: `apartment.rental_value_double = apartment.rental_value_double * (1 + percentage / 100)` (arredondado)
   - `apartment.last_rent_increase_date = date.today()`
   - Salva apartment
6. Retorna o `RentAdjustment` criado

**Warning (não bloqueio)**: se já existe um reajuste nos últimos 10 meses para este lease, retornar `warning` no response mas permitir aplicar.

**`get_eligible_leases(alert_months=2) -> list[dict]`** — para o dashboard:

Query otimizada: `.select_related("apartment", "apartment__building", "responsible_tenant").prefetch_related("rent_adjustments")`

1. Busca leases ativos (não deletados, não expirados)
2. Exclui `is_salary_offset=True`
3. Para cada lease, calcula a **data de referência** para o próximo reajuste:
   - Se tem `RentAdjustment` anterior: referência = `last_adjustment.adjustment_date`
   - Se não tem: referência = `lease.start_date`
4. Próximo reajuste elegível: `referência + 12 meses` (usando `relativedelta(months=12)` para lidar com meses de tamanhos diferentes)
5. Retorna leases onde: data elegível está dentro de `alert_months` meses no futuro OU já passou (atrasado)
6. Cada item retorna:
   - `lease_id`, `apartment` (número + building name), `tenant` (nome), `rental_value`
   - `eligible_date` (data em que o reajuste se torna elegível)
   - `days_until` (positivo = futuro, negativo = atrasado)
   - `status`: `"upcoming"` | `"overdue"`
   - `last_adjustment`: último RentAdjustment serializado ou null
   - `prepaid_warning`: `true` se `lease.prepaid_until` está no futuro (aviso de que o prepayment não muda)

### 3. Serializer: RentAdjustmentSerializer

```python
class RentAdjustmentSerializer(serializers.ModelSerializer):
    """Read-only serializer for rent adjustment history."""
    lease_summary = serializers.SerializerMethodField()

    class Meta:
        model = RentAdjustment
        fields = ["id", "lease", "lease_summary", "adjustment_date", "percentage",
                  "previous_value", "new_value", "apartment_updated",
                  "created_at", "created_by"]
        read_only_fields = fields

    def get_lease_summary(self, obj):
        return {
            "apartment_number": obj.lease.apartment.number,
            "building_name": obj.lease.apartment.building.name,
            "tenant_name": obj.lease.responsible_tenant.name,
        }
```

Não precisa de ViewSet próprio — o histórico é acessado via action no LeaseViewSet.

### 4. API Endpoints

**No LeaseViewSet** (actions no lease):

`POST /api/leases/{id}/adjust_rent/`
- Body: `{ "percentage": "5.23", "update_apartment_prices": true }`
- Validação: percentage != 0, lease ativo
- Response **201 Created**: `{ "id": 1, "previous_value": "1400.00", "new_value": "1473.22", "percentage": "5.23", "adjustment_date": "2026-03-26", "apartment_updated": true, "warning": null }`
- Response com warning: `{ ..., "warning": { "type": "recent_adjustment", "last_date": "2026-01-15" } }`
- Permissão: `IsAdminUser`

`GET /api/leases/{id}/rent_adjustments/`
- Response: lista de `RentAdjustmentSerializer`, ordenada por `adjustment_date` desc
- Permissão: autenticado

**Novo endpoint no dashboard** (views.py ou viewset existente):

`GET /api/dashboard/rent_adjustment_alerts/`
- Response: `{ "alerts": [...] }` — lista de leases elegíveis com info de reajuste
- Permissão: autenticado

### 5. Migration

- Nova tabela `core_rentadjustment`
- Sem data migration (tabela começa vazia)
- Sem alteração em tabelas existentes

### 6. Cache

- Invalidar cache de dashboard ao aplicar reajuste
- Invalidar cache de lease ao aplicar reajuste
- Adicionar signal handler para `RentAdjustment`

---

## Mudanças no Frontend

### 1. Modal de Reajuste (`rent-adjustment-modal.tsx`)

Nova componente em `frontend/app/(dashboard)/leases/_components/`:

- Props: `open`, `lease` (Lease), `onClose`
- Usa React Hook Form + Zod (form schema separado do response schema)
- Campos:
  - **Percentual** (input numérico, step 0.01, editável) — aceita positivo e negativo
  - **Checkbox** "Atualizar preço de tabela do apartamento" — default true
- Exibe em tempo real (calculado no frontend):
  - Valor atual: `lease.rental_value`
  - Valor novo: `lease.rental_value * (1 + percentage / 100)`
- Botão "Aplicar Reajuste"
- Toast de sucesso/erro
- Se response contém `warning`, exibir toast de warning

### 2. Tabela de Leases — Nova Ação

Em `lease-table-columns.tsx`:
- Adicionar botão "Reajustar" no dropdown de ações
- Adicionar botão "Histórico de Reajustes" no dropdown de ações
- "Reajustar" visível apenas para leases ativos (não expirados)
- Interface `LeaseActionHandlers`: adicionar `onAdjustRent` e `onViewAdjustmentHistory`

### 3. Histórico de Reajustes

Novo componente `rent-adjustment-history-sheet.tsx`:
- Abre Sheet/Drawer com tabela:
  - Colunas: Data, Percentual, Valor Anterior, Valor Novo, Apt. Atualizado, Aplicado por
  - Ordenado por data desc
- Usa `useRentAdjustments(leaseId)` hook
- Acessado via botão "Histórico de Reajustes" no dropdown do lease

### 4. Dashboard — Widget de Alertas

Novo componente `rent-adjustment-alerts.tsx`:
- Posição: dashboard principal (`app/(dashboard)/page.tsx`), após o widget de inadimplência (LatePaymentsAlert)
- Card "Reajustes Pendentes" com contador no título
- Lista de contratos elegíveis:
  - Cada item: "Apto 203 - 850 | Danielle | R$ 1.400,00 | Reajuste em: 15/04/2026"
  - Badge: "Em 45 dias" (amarelo/warning), "Atrasado 15 dias" (vermelho/destructive)
  - Info: "Último reajuste: 15/04/2025" ou "Nunca reajustado"
  - Se `prepaid_warning`: badge adicional "Pré-pago"
- Botão "Reajustar" em cada item → abre `RentAdjustmentModal`
- Se nenhum alerta: mostra "Nenhum reajuste pendente"

### 5. Schemas (Zod)

Novo arquivo `rent-adjustment.schema.ts`:

Response schema (para parsear dados da API):
```typescript
export const rentAdjustmentSchema = z.object({
  id: z.number(),
  lease: z.number(),
  lease_summary: z.object({
    apartment_number: z.number(),
    building_name: z.string(),
    tenant_name: z.string(),
  }).optional(),
  adjustment_date: z.string(),
  percentage: z.string().or(z.number()).transform(Number),
  previous_value: z.string().or(z.number()).transform(Number),
  new_value: z.string().or(z.number()).transform(Number),
  apartment_updated: z.boolean(),
  created_at: z.string().optional(),
  created_by: z.number().nullable().optional(),
});
```

Form schema (para o modal):
```typescript
export const rentAdjustmentFormSchema = z.object({
  percentage: z.number().refine(v => v !== 0, "Percentual não pode ser zero"),
  update_apartment_prices: z.boolean().default(true),
});
```

### 6. Hooks

`frontend/lib/api/hooks/use-rent-adjustments.ts`:

- `useApplyRentAdjustment()` — mutation POST `/leases/{id}/adjust_rent/`
  - Invalida: `['leases']`, `['apartments']`, `['dashboard']`, `['rent-adjustment-alerts']`, `['rent-adjustments', leaseId]`
- `useRentAdjustments(leaseId)` — query GET `/leases/{id}/rent_adjustments/`
  - Key: `['rent-adjustments', leaseId]`
- `useRentAdjustmentAlerts()` — query GET `/dashboard/rent_adjustment_alerts/`
  - Key: `['rent-adjustment-alerts']`

---

## Testes

### Backend
- **Unit**: cálculo correto do novo valor (ex: 1400 * 5.23% = 1473.22)
- **Unit**: cálculo com percentual negativo (ex: 1400 * -0.64% = 1391.04)
- **Unit**: atualização do apartment com mesmo percentual (não fator derivado do lease)
- **Unit**: `get_eligible_leases` retorna leases baseado em data de referência correta (último reajuste ou start_date)
- **Unit**: `get_eligible_leases` exclui `is_salary_offset=True`
- **Unit**: `get_eligible_leases` inclui `prepaid_until` com warning
- **Unit**: `get_eligible_leases` exclui leases fora da janela de alerta
- **Unit**: `get_eligible_leases` exclui leases expirados
- **Integration**: `POST adjust_rent/` — cria RentAdjustment, atualiza lease.rental_value (atomicamente)
- **Integration**: `POST adjust_rent/` com `update_apartment_prices=true` — atualiza apartment com mesmo percentual
- **Integration**: `POST adjust_rent/` com percentual = 0 — retorna 400
- **Integration**: `POST adjust_rent/` em lease expirado — retorna 400
- **Integration**: `POST adjust_rent/` com reajuste recente — retorna 201 com warning
- **Integration**: `GET rent_adjustments/` — retorna histórico ordenado
- **Integration**: `GET rent_adjustment_alerts/` — retorna alertas corretos

### Frontend
- **Hook tests**: `useApplyRentAdjustment` envia payload e invalida caches
- **Hook tests**: `useRentAdjustmentAlerts` parseia resposta
