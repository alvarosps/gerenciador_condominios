# Preço Automático por Ocupação

**Data**: 2026-03-26
**Status**: Aprovado
**Escopo**: Preço de aluguel automático baseado no número de inquilinos (1 ou 2), fluxo de dependentes na criação de contrato, e migração para `lease.rental_value` como fonte da verdade.

## Contexto

Atualmente o valor do aluguel está apenas no `Apartment.rental_value` e não varia por número de ocupantes. Apartamentos com `max_tenants == 2` podem ter preços diferentes para 1 ou 2 pessoas (diferença típica de R$100, mas configurável por apartamento). O `Lease` não armazena o valor acordado — sempre referencia o apartamento.

Problemas:
- Não há como saber automaticamente o preço correto baseado no número de inquilinos
- O valor do aluguel não fica registrado no contrato (lease), dificultando reajustes futuros
- Dependentes não são rastreados por contrato — não se sabe qual dependente reside no apartamento
- Dependentes não possuem CPF cadastrado

## Decisões de Design

1. **Dois campos explícitos no Apartment** (não base + incremento) — mais simples e editável diretamente
2. **`rental_value` no Lease** — fonte da verdade do valor pago, preparado para reajuste futuro (spec 2)
3. **Dependente sempre** — segunda pessoa é sempre dependente do responsável, nunca segundo inquilino independente. O M2M `Lease.tenants` sempre contém apenas o responsável; a segunda pessoa é rastreada via `resident_dependent`.
4. **`max_tenants` é sempre 1 ou 2** — não há apartamentos com 3+ pessoas
5. **Dependente no contrato** — fica apenas no sistema, não aparece no PDF do contrato (por enquanto)
6. **`number_of_tenants` restrito a 1 ou 2** — não pode exceder `apartment.max_tenants`. Semântica muda de "contagem declarada livre" para "tier de preço vinculado ao max_tenants".

## Specs Relacionados (Fora do Escopo)

- **Spec 2 — Reajuste Anual**: reajuste com base no IGP-M, histórico, alertas no dashboard. Usa `lease.rental_value` como base.
- **Spec 3 — Gestão de Inquilinos**: promover dependente a inquilino + upload de documentos/fotos.

A integração entre specs é garantida pelo campo `lease.rental_value`:
- Este spec cria o campo e o popula na criação do contrato
- Spec 2 atualiza o campo quando há reajuste
- Não há gaps: o valor sempre reflete o que o inquilino paga

---

## Mudanças no Backend

### 1. Model: Apartment

Adicionar campo:
- `rental_value_double` (DecimalField, max_digits=10, decimal_places=2, null=True, blank=True)
  - Valor do aluguel para 2 pessoas
  - Obrigatório quando `max_tenants == 2` (validação no serializer)
  - Null para apartamentos com `max_tenants == 1`
  - Deve ser >= `rental_value` (pode ser igual — preço idêntico para 1 ou 2 é permitido)

Campo existente `rental_value` passa a significar "valor para 1 pessoa" (semanticamente já é isso).

### 2. Model: Lease

Adicionar campos:
- `rental_value` (DecimalField, max_digits=10, decimal_places=2)
  - Valor acordado no momento da criação do contrato
  - Fonte da verdade para: contrato PDF, cálculo de multa, futuro reajuste
  - Auto-preenchido a partir do apartment (single ou double) baseado em `number_of_tenants`
  - Editável manualmente para exceções
  - **Migração**: três etapas — (1) adicionar com `null=True`, (2) data migration popula, (3) alterar para `NOT NULL`
- `resident_dependent` (ForeignKey to Dependent, null=True, blank=True, on_delete=SET_NULL)
  - Qual dependente reside no apartamento neste contrato
  - Obrigatório quando `number_of_tenants == 2` (validação no serializer)
  - Null para contratos de 1 pessoa

Adicionar validação no model ou serializer:
- `number_of_tenants <= apartment.max_tenants`
- `number_of_tenants` restrito a 1 ou 2

**M2M `tenants`**: com esta mudança, o campo `tenants` (M2M) sempre contém apenas o `responsible_tenant`. A segunda pessoa é rastreada via `resident_dependent`, não via M2M. O formulário frontend para o M2M fica oculto — `tenant_ids` é auto-populado com `[responsible_tenant_id]`. Leases existentes com múltiplos tenants no M2M não são alterados na migração (dados históricos preservados).

### 3. Model: Dependent

Adicionar campo:
- `cpf_cnpj` (CharField, max_length=14, null=True, blank=True)
  - Validado com mesma lógica de CPF/CNPJ existente
  - Nullable para dependentes já cadastrados (preenchido ao longo do tempo)
  - Não precisa ser unique (mesmo CPF pode aparecer como dependente de diferentes tenants em cenários raros)

### 4. Serializers

**ApartmentSerializer**:
- Adicionar `rental_value_double` (read + write)
- Validação: se `max_tenants == 2`, `rental_value_double` é obrigatório e >= `rental_value`

**LeaseSerializer**:
- Adicionar `rental_value` (read + write)
- Adicionar `resident_dependent` (read, nested DependentSerializer) + `resident_dependent_id` (write, PrimaryKeyRelatedField) — dual pattern
- Validação:
  - Se `number_of_tenants == 2`, `resident_dependent_id` é obrigatório
  - `resident_dependent.tenant_id == responsible_tenant_id` (dependente deve pertencer ao inquilino responsável)
  - `number_of_tenants <= apartment.max_tenants`
  - `number_of_tenants` in [1, 2]

**DependentSerializer**:
- Adicionar `cpf_cnpj` (read + write, opcional)

### 5. Services — Todos os Consumidores de `apartment.rental_value`

**CRÍTICO**: Todas as referências a `lease.apartment.rental_value` e `apartment.rental_value` (quando representando valor pago pelo inquilino) devem ser substituídas por `lease.rental_value`. Lista completa:

#### 5a. Referências via lease (mudar para `lease.rental_value`)

| Arquivo | O que mudar |
|---------|------------|
| `contract_service.py` | `prepare_contract_context()`: usar `lease.rental_value`. `calculate_total_value` caller: passar `lease.rental_value`. **ATENÇÃO**: `len(lease.tenants.all())` para tag fee deve mudar para `lease.number_of_tenants` (M2M sempre terá 1 tenant agora). |
| `fee_calculator.py` | Já recebe como parâmetro — sem mudança no service. Callers que passam `apartment.rental_value` devem passar `lease.rental_value`. |
| `cash_flow_service.py` | ~6 referências via `lease.apartment.rental_value`: renda mensal de aluguel, projeções — mudar para `lease.rental_value`. ~2 referências via `apt.rental_value` no person summary (owner repayments): mudar para valor do lease ativo do apartment. |
| `financial_dashboard_service.py` | ~4 referências via lease: salary offset, daily breakdown. ~10 referências no income breakdown que itera apartments e usa `apt.rental_value`: mudar para valor do lease ativo (pegar `lease.rental_value` via `apartment.active_lease`). |
| `daily_control_service.py` | ~2 referências: breakdown diário de aluguel, cálculo total — mudar para `lease.rental_value` |
| `dashboard_service.py` | Late payment summary: mudar referência Python para `lease.rental_value`. **ORM aggregates**: `Sum("apartment__rental_value")` → `Sum("rental_value")` (agora é campo do Lease). |
| `simulation_service.py` | ~2 referências via `apartment.rental_value`: simulação de reajuste opera sobre `lease.rental_value` (valor atualmente pago, não preço de tabela). Queries que acessam Apartment diretamente precisam join via lease. |

#### 5b. Referências que permanecem como `apartment.rental_value` (preço de tabela)

| Arquivo | Por quê manter |
|---------|---------------|
| `dashboard_service.py` building statistics | `Sum("apartments__rental_value")` agrega preço de tabela por prédio — é intencionalmente o preço base, não o valor pago. Útil para comparar potencial vs realidade. |

#### 5c. Referência que precisa decisão deliberada

| Arquivo | Decisão |
|---------|---------|
| `PersonIncomeSerializer.get_current_value()` (serializers.py) | Para `apartment_rent` type: mudar para `lease.rental_value` via apartment active_lease. O owner recebe o valor real do aluguel, não o preço de tabela. |

### 6. Validators

**Substituir `validate_tenant_count`** em `core/validators/model_validators.py`:
- Validador atual: `number_of_tenants >= tenants.count()` — obsoleto (M2M sempre terá 1)
- Novo comportamento: `number_of_tenants in [1, 2]` e `number_of_tenants <= apartment.max_tenants`
- Implementar no serializer (cross-field validation) ou substituir o validator no model

### 7. Views e Querysets

**Views (callers de fee_calculator)**:
- `LeaseViewSet.calculate_late_fee`: passar `lease.rental_value`
- `LeaseViewSet.change_due_date`: passar `lease.rental_value`

**LeaseViewSet queryset**: adicionar `select_related('resident_dependent')` para evitar N+1. Outros services que fazem queries de Lease com `select_related` não precisam — `resident_dependent` só é serializado no ViewSet, não nos services.

### 8. Template e Model Docs

**Template HTML (`contract_template.html`)**: NÃO precisa mudar. O template usa `{{ rental_value | currency }}` que vem do contexto dict preparado por `prepare_contract_context()`. Apenas a função que monta o contexto muda.

**Model `number_of_tenants` help_text**: atualizar de "Can be >= actual tenant count to account for additional occupants" para refletir nova semântica: "1 ou 2, determina tier de preço. Deve ser <= apartment.max_tenants."

---

## Mudanças no Frontend

### 1. Apartment Form

- Quando `max_tenants == 2`: exibir campo **"Valor aluguel (2 pessoas)"** ao lado do campo existente
- Quando `max_tenants == 1`: campo oculto
- Validação: `rental_value_double` obrigatório quando `max_tenants == 2`, >= `rental_value`

### 2. Lease Form Modal

**Fluxo de criação:**

1. Usuário seleciona **apartamento** → carrega dados (preços single/double, max_tenants)
2. Se `max_tenants == 2`: exibe seletor **"Quantas pessoas?"** (1 ou 2)
   - Se `max_tenants == 1`: oculto, assume 1 pessoa
3. Ao selecionar quantidade:
   - **Rental value**: auto-preenchido (`rental_value` se 1 pessoa, `rental_value_double` se 2)
   - **Tag fee**: auto-preenchido (R$50 se 1, R$80 se 2)
   - Ambos editáveis manualmente
4. Se 2 pessoas — **fluxo de dependente**:
   - Verifica dependentes do inquilino responsável
   - **Tem dependentes?** → lista com radio button para selecionar + opção "Cadastrar novo"
   - **Não tem?** → formulário inline (nome, CPF, telefone)
   - Dependente selecionado/criado salvo em `lease.resident_dependent`
   - **Criação inline de dependente**: usa o endpoint existente `POST /api/dependents/` (se existir) ou `PATCH /api/tenants/{id}/` com nested dependents (padrão atual do TenantSerializer). O dependente é criado antes do lease, e o `resident_dependent_id` é enviado na criação do lease.
5. Se volta de 2 para 1 → limpa seleção de dependente, recalcula valores
6. Se troca o **inquilino responsável** → limpa seleção de dependente (lista muda)
7. Se troca o **apartamento** → limpa tudo: recalcula valores, limpa dependente

**`tenant_ids` (M2M)**: campo oculto no formulário. Auto-populado com `[responsible_tenant_id]`. O checkbox de "Todos os inquilinos" é removido.

**Fluxo de edição:**

- Ao editar um lease existente, `rental_value` exibe o valor salvo (não recalcula automaticamente)
- Se o usuário mudar `number_of_tenants` de 1→2 ou 2→1, o sistema **sugere** o novo valor (mostra o preço do apartment) mas não sobrescreve automaticamente — o usuário confirma
- Se `contract_generated == true`, exibe aviso de que alterar o valor requer gerar novo contrato

**Card de resumo do apartamento**: mostra ambos os valores quando `max_tenants == 2`, destacando o selecionado.

### 3. Lease Table

Coluna "Valor" mostra `lease.rental_value` em vez de `apartment.rental_value`.

### 4. Apartment Schema (Zod)

Adicionar `rental_value_double` (number, nullable).

### 5. Lease Schema (Zod)

Adicionar `rental_value` (number, required) e `resident_dependent` / `resident_dependent_id`.

### 6. Dependent Schema (Zod)

Adicionar `cpf_cnpj` (string, opcional).

---

## Migração de Dados

### Estratégia de migração para `Lease.rental_value` (NOT NULL)

Três etapas em uma única migration file:
1. `AddField` com `null=True` — adiciona o campo nullable
2. `RunPython` — data migration popula todos os leases
3. `AlterField` para `null=False` — torna obrigatório

### Apartment
- Apartamentos com `max_tenants == 2`: `rental_value_double = rental_value + 100` (padrão R$100 acima)
- Apartamentos com `max_tenants == 1`: `rental_value_double = NULL`

### Lease
- Todos os leases existentes: `rental_value = apartment.rental_value`
- Exceção: Prédio 850, apto 203 → `rental_value = 1500`, `number_of_tenants = 2`

### Dependent
- `cpf_cnpj = NULL` para todos os dependentes existentes

### Lease.resident_dependent
- NULL para todos os leases existentes (não há dados históricos)

### Cache invalidation
- Verificar se signals em `core/signals.py` precisam de atualização para o novo FK `resident_dependent`
- Adicionar invalidação de cache para Dependent se necessário

---

## Testes

### Backend
- **Unit**: validação do serializer — `rental_value_double` obrigatório quando `max_tenants==2`
- **Unit**: validação do serializer — `resident_dependent_id` obrigatório quando `number_of_tenants==2`
- **Unit**: validação do serializer — `resident_dependent` deve pertencer ao `responsible_tenant`
- **Unit**: validação do serializer — `number_of_tenants <= apartment.max_tenants`
- **Integration**: criação de lease com 1 pessoa → `rental_value = apartment.rental_value`
- **Integration**: criação de lease com 2 pessoas → `rental_value = apartment.rental_value_double`, `resident_dependent` preenchido
- **Integration**: edição de lease — mudar `number_of_tenants` de 1→2 e 2→1
- **Integration**: geração de contrato usa `lease.rental_value`
- **Integration**: cálculo de multa usa `lease.rental_value`
- **Integration**: cash flow service usa `lease.rental_value`
- **Integration**: financial dashboard usa `lease.rental_value`
- **Integration**: migração de dados — leases existentes com valor correto, 850/203 com R$1500

### Frontend
- **Hook tests**: useCreateLease envia `rental_value` e `resident_dependent_id`
- **Component**: lease form auto-preenche valores ao selecionar apartment + quantidade
- **Component**: fluxo de dependente aparece/desaparece corretamente
- **Component**: trocar inquilino responsável limpa seleção de dependente
- **Component**: trocar apartamento limpa tudo e recalcula
- **Component**: edição de lease mostra valor salvo, sugere (não sobrescreve) ao mudar quantidade
