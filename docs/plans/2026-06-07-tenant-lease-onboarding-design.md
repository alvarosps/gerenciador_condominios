# Design — Fluxo guiado "Novo inquilino + contrato" (web)

> **Status**: aprovado; prompts de execução escritos (51–55).
> **Data**: 2026-06-07
> **Re-verificado em**: 2026-06-07 contra `feat/condo-finance` HEAD `a4905dc` (após S34–50 de finanças + refactors). Único impacto: `core/models.py` deslocou ~+22 linhas (classmethod `Condominium.get_default`) → refs de modelo abaixo atualizadas; serializers/views/contract_service e os componentes de `leases`/`tenants` **inalterados**; dashboard agora renderiza `FinanceKpiRow` no topo (placement do CTA ajustado na S55). **Nenhum gap estrutural novo** — sem campos obrigatórios novos em Tenant/Lease/Apartment.
> **Escopo deste doc**: APENAS o app **web**. O app **mobile** (mesmas funcionalidades + calendário) é o **Plano 2**, a ser desenhado depois. A feature de **installments/payroll** está em outra sessão e **não** é tocada aqui.

---

## 1. Objetivo

Hoje, cadastrar um novo contrato exige: (1) criar o inquilino numa tela, (2) ir até a tela de Contratos, (3) criar o contrato associando o inquilino. São três contextos distintos.

Este design entrega um **fluxo único guiado** (wizard), acessível por um botão no dashboard, que executa de ponta a ponta:

1. **Inquilino** — criar **novo** OU selecionar um **existente sem contrato ativo** (carregando os dados para edição).
2. **Contrato** — criar o contrato associando o inquilino diretamente (1 ou 2 inquilinos).
3. **PDF (opcional)** — ao final, gerar o PDF do contrato ou encerrar o fluxo.

A criação inquilino+contrato passa por **um endpoint transacional** (atômico) reaproveitável depois pelo app mobile de admin (Plano 2).

---

## 2. Escopo

### Incluído
- Endpoint backend transacional `POST /api/onboarding/tenant-lease/` (cria/atualiza inquilino + cria contrato numa transação).
- Wizard frontend `TenantLeaseOnboardingWizard` (novo vs existente, 1 ou 2 inquilinos, dados enxutos + seções opcionais, revisão, PDF).
- Botão/CTA no dashboard (gated `is_staff`).
- **Correções de raiz** identificadas na revisão (beneficiam também os endpoints atuais): disponibilidade de apartamento → 400 limpo; guard de locador ativo na geração de PDF; captura confiável de id de dependente; propagação de auditoria a dependentes; remoção dos campos fantasma `email`/`phone_alternate` do wizard de inquilino atual.

### NÃO incluído (YAGNI)
- App mobile (Plano 2).
- Installments/payroll (outra sessão).
- Criar **apartamento/prédio** dentro do fluxo (o fluxo só seleciona apartamentos disponíveis existentes).
- Regra nova "1 contrato ativo por inquilino" no backend (o front filtra; a constraint de apartamento livre protege o banco).
- Sistema de polling completo para PDF assíncrono (Celery): prod já roda efetivamente em modo *eager* — apenas tratamos defensivamente um eventual `202`.
- Assinatura/aprovação de contrato (`contract_signed`, `interfone_configured` seguem fluxos próprios fora deste wizard).

---

## 3. Decisões (confirmadas com o usuário)

| # | Decisão | Escolha |
|---|---------|---------|
| D1 | Quanto coletar do inquilino | **Enxuto + opcionais**: obrigatórios sempre + seções recolhíveis (dependentes, mobília). |
| D2 | Suporte a 2 inquilinos | **Sim, 1 ou 2** — o 2º ocupante é um **dependente** do responsável, criado na mesma transação. |
| D3 | Arquitetura backend | **Endpoint transacional novo** (`TenantOnboardingService`), reaproveitável pelo mobile. |
| D4 | `email`/`phone_alternate` | **Remover da UI** (o backend não os persiste — bug atual) e limpar do wizard de inquilino existente. |

### Premissas (derivadas, sem dúvida)
- A geração de PDF permanece em endpoint próprio (`generate_contract`) — o wizard só o invoca como passo opcional (SRP).
- Endpoint admin-only (`IsAdminUser`), consistente com escrita de inquilino/contrato.
- Sem tabelas novas ⇒ **sem migration de schema e sem RLS nova** (regra `.claude/rules/security.md`).
- Invalidação de cache é automática: os `save()` dos models disparam os signals (`core/signals.py`) independentemente de quem chama.

---

## 4. Arquitetura

Direção de dependência respeitada: **View → Service → (Serializers/Models)**. Toda a orquestração na camada de service.

### 4.1 Endpoint de onboarding (novo)

**Rota**: `POST /api/onboarding/tenant-lease/` — registrada em `core/urls.py`. Permissão `IsAdminUser`.

**View** — `TenantLeaseOnboardingView(APIView)` em `core/viewsets/onboarding_views.py` (fina):
- valida o shape via `TenantLeaseOnboardingSerializer`;
- delega a `TenantOnboardingService.onboard(...)`;
- responde `201 { "tenant": TenantSerializer(tenant).data, "lease": LeaseSerializer(lease).data }`.

**Serializer de entrada** — `TenantLeaseOnboardingSerializer` (valida só estrutura):
```jsonc
{
  "tenant": { /* campos do TenantSerializer; pode incluir "id" p/ existente */ },
  "lease":  { /* campos do LeaseSerializer SEM responsible_tenant_id e SEM tenant_ids */ },
  "resident_dependent": { "name": "...", "phone": "...", "cpf_cnpj": "" },  // opcional (2 inquilinos, residente NOVO)
  "resident_dependent_id": 123                                              // opcional (2 inquilinos, residente EXISTENTE)
}
```
> O cliente **não** envia `responsible_tenant_id` nem `tenant_ids` — o service os injeta.

**Service** — `TenantOnboardingService.onboard(*, tenant_payload, lease_payload, resident_dependent, resident_dependent_id, user)` em `core/services/tenant_onboarding_service.py`:

```python
@transaction.atomic  # o método é a fronteira atômica (os create() dos serializers NÃO são atômicos isolados)
def onboard(...):
    # 1) Pré-checagem de disponibilidade do apartamento (fail-fast + select_for_update p/ corrida)
    _assert_apartment_available(lease_payload["apartment_id"])  # lock + raise ValidationError({"apartment": ...})

    # 2) Inquilino: criar (sem id) OU atualizar parcial (com id)
    if tenant_payload.get("id"):
        tenant = Tenant.objects.get(pk=tenant_payload["id"])          # manager padrão exclui soft-deleted
        ser = TenantSerializer(tenant, data=tenant_payload, partial=True)
    else:
        ser = TenantSerializer(data=tenant_payload)
    ser.is_valid(raise_exception=True)
    tenant = ser.save(created_by=user, updated_by=user)

    # 3) Dependente residente (2 inquilinos): id existente OU criação explícita (id capturado direto)
    resolved_resident_id = resident_dependent_id
    if resident_dependent and not resident_dependent_id:
        dep = Dependent.objects.create(tenant=tenant, created_by=user, updated_by=user, **resident_dependent)
        resolved_resident_id = dep.id

    # 4) Contrato
    lease_payload |= {
        "responsible_tenant_id": tenant.id,
        "tenant_ids": [tenant.id],
        "resident_dependent_id": resolved_resident_id,
    }
    lease_ser = LeaseSerializer(data=lease_payload)
    lease_ser.is_valid(raise_exception=True)
    lease = lease_ser.save(created_by=user, updated_by=user)
    return tenant, lease
```

**Por que o dependente residente é criado explicitamente** (não por índice): ver §5, gap G1.

**Tratamento de erro/atomicidade**: qualquer `ValidationError` aborta e o `atomic()` faz rollback (sem inquilino órfão, sem edição aplicada). Um eventual `IntegrityError` da constraint de apartamento é capturado e convertido em `400 {"lease": {"apartment": [...]}}` (ver G3).

### 4.2 Correções de raiz (compartilhadas — beneficiam endpoints atuais)

Estas mudanças são **pré-requisito** do fluxo e corrigem bugs reais detectados na revisão:

1. **`LeaseSerializer.validate()`** (`core/serializers.py:402-448`) passa a checar **disponibilidade do apartamento** (apto sem contrato ativo), levantando `ValidationError({"apartment": ...})`. Hoje só a `UniqueConstraint` (`core/models.py:733-736`) protege ⇒ `IntegrityError` 500. Conserta também o `LeaseViewSet` atual. (G3)
2. **`TenantSerializer.create()`** (`core/serializers.py:298-308`) passa a **capturar os `Dependent` criados** e anexá-los (ex.: `tenant._created_dependents`) + **propagar `created_by`/`updated_by`** aos dependentes (hoje ficam nulos). (G1, G4)
3. **`contract_service.prepare_contract_context`** (`core/services/contract_service.py:191`) passa a levantar erro de domínio se `Landlord.get_active()` for `None` (em vez de renderizar contrato vazio). (G2)
4. **Wizard de inquilino atual**: remover `email`/`phone_alternate` do schema/steps (`frontend/lib/schemas/tenant.schema.ts:25-27`, `contact-info-step`) — campos descartados pelo backend hoje. (G6)

### 4.3 Frontend — `TenantLeaseOnboardingWizard`

Padrão do `TenantFormWizard` (`frontend/app/(dashboard)/tenants/_components/wizard/index.tsx`): `Dialog` + `Stepper` + RHF/Zod + TanStack. Novo folder `frontend/app/(dashboard)/_components/tenant-lease-onboarding/`.

**Passos:**
0. **Início — novo vs existente.** RadioGroup. Em "existente": select com busca de inquilinos **sem contrato ativo** (mesma fonte usada pelo accordion "Sem Contrato Ativo" da página de Inquilinos); ao escolher → prefill de todos os campos (inclusive dependentes/mobília), edição liberada. Conversão de prefill: `furnitures` (nested) → `furniture_ids`; dependentes nested → array do form (ver G7).
1. **Inquilino — obrigatórios.** `name`, `is_company` (PF/PJ), `cpf_cnpj`, `phone`, `profession`, `marital_status`, `due_day`; recolhível: `rg`.
2. **Inquilino — opcionais (recolhível).** Dependentes (`useFieldArray`) + mobília (afeta a lista do PDF). Pode pular.
3. **Contrato — imóvel & período.** `apartment` (disponíveis), `number_of_tenants` (1/2, ≤ `max_tenants`, **sempre enviado**), `start_date`, `validity_months`. Auto-deriva `rental_value` (single/double) e `tag_fee`. Se 2 inquilinos → seletor do 2º ocupante (dependente existente ou "adicionar novo"); se 2, exigir `apartment.rental_value_double`.
4. **Contrato — valores & pagamentos.** `rental_value` (pré-preenchido, **editável**), `tag_fee` (pré-preenchido), `deposit_amount`, `cleaning_fee_paid`, `tag_deposit_paid`, `due_day` (pré-preenchido do inquilino), `prepaid_until` + `is_salary_offset` (admin).
5. **Revisão.** Resumo inquilino + contrato → submit `POST /api/onboarding/tenant-lease/` (payload inclui `tenant.id` quando existente).
6. **Concluído / PDF.** Sucesso. Botões: **"Gerar contrato (PDF)"** (reusa `useGenerateContract(lease.id)` + rota `/download`; trata `{pdf_path}` e, defensivamente, `202 {task_id}`) ou **"Concluir"**.

**Hook**: `useOnboardTenantLease` → `POST` onboarding; invalida `tenants.all`, `leases.all`, `apartments.all`, `dashboard.all`.

**Reuso/DRY (extrair, não copiar do `lease-form-modal`)**: derivação de `rental_value` (single/double), `calculateTagFee` (já existe — reusar), derivação de `due_day` a partir de `start_date`, componente de seleção/criação inline de dependente, `parseLocalDate`, e o fragmento Zod de valores do contrato. (G9)

### 4.4 Ponto de entrada
- Card/CTA **"Novo inquilino + contrato"** no dashboard (`frontend/app/(dashboard)/page.tsx`), renderizado só se `user?.is_staff`.
- (Opcional/trivial, fora do escopo mínimo) atalho no header da página de Inquilinos.

---

## 5. Edge cases / gaps corrigidos (da revisão adversarial)

| ID | Gap (verificado no código) | Severidade | Correção no design |
|----|----------------------------|-----------|--------------------|
| G1 | `TenantSerializer.create()` descarta os `Dependent` e o model não tem `ordering` → `resident_dependent_index` não-confiável (pior no update smart-merge). | **Blocker** | Residente vira campo próprio (`resident_dependent` novo / `resident_dependent_id` existente); service cria o `Dependent` explicitamente e captura o id. |
| G2 | `Landlord.get_active()` pode ser `None` → PDF renderiza vazio (contrato inválido sem erro). `contract_service.py:191`. | **Blocker** | Guard que levanta erro; passo de PDF do wizard checa locador ativo / trata o 400. + teste do caso `None`. |
| G3 | Disponibilidade de apartamento só na `UniqueConstraint` → `IntegrityError` 500 e envenena o `atomic()`. Afeta `LeaseViewSet` atual. | **Major** | Check em `LeaseSerializer.validate()` + `select_for_update` + `except IntegrityError`→400 namespeado. |
| G4 | Auditoria: `serializer.save(created_by=user)` funciona, mas dependentes do nested ficam sem `created_by`. | **Major** | Service passa `created_by`/`updated_by`; `TenantSerializer.create` propaga aos dependentes. |
| G5 | `number_of_tenants` omitido cai em 1 (mispreço caso 2); `rental_value` NOT-NULL no model vs `required=False` no serializer. | **Major** | Wizard sempre envia `number_of_tenants`; `rental_value`/`tag_fee` pré-preenchidos+editáveis; se 2, exigir `rental_value_double`. |
| G6 | `email`/`phone_alternate` coletados pelo wizard atual mas descartados pelo backend (perda de dado). | **Major** | Remover da UI (D4). |
| G7 | Prefill de inquilino existente: `GET /tenants/` retorna `furnitures` nested, form precisa de `furniture_ids`; `useUpdateTenant` remove `dependents`. | **Major** | Conversão no prefill; update via endpoint de onboarding (não `useUpdateTenant`). |
| G8 | PDF: `generate_contract` retorna `{pdf_path}` (eager) ou `202 {task_id}` (broker); modal atual só trata eager. | **Major** | Tratar ambos os shapes no passo de PDF (sem polling completo; prod é eager). |
| G9 | Lógica de `rental_value`/`tag_fee`/`due_day`/dependente/data duplicada no `lease-form-modal`. | **Major** | Extrair utilitários/sub-componentes compartilhados. |
| — | Corrida: apartamento fica indisponível entre seleção e submit. | Minor | `select_for_update` + check em `validate()` cobrem. |

### Confirmado sólido (sem ação)
`IsAdminUser` correto e consistente · JWT exigido por default · sem tabelas novas → sem RLS · rollback do `atomic()` cobre tenant+lease · signals disparam no `save()` do model (cache automático) · soft-delete exclui deletados por padrão · criar contrato via onboarding também dispara a invalidação cross-app `finance-*` (receivers de finanças sobre escrita de `Lease`/`Apartment`) — comportamento automático, **sem ação**.

---

## 6. Erros (contrato com o frontend)
- Erros **namespeados**: `400 {"tenant": {...}}` ou `400 {"lease": {...}}` → o wizard pula para o passo culpado (ex.: `tenant.cpf_cnpj` → passo 1; `lease.apartment` → passo 3).
- `403` não-admin, `401` sem token.
- Mensagens ao usuário em **português** via `getErrorMessage`; logs/devs em inglês.

---

## 7. Testes (regras `tests/CLAUDE.md` — mock só de fronteira externa)

**Backend (integração view→service→model):**
- sucesso inquilino novo (tenant+lease criados e ligados; ids retornados);
- sucesso inquilino existente + edição (tenant atualizado);
- existente sem edição;
- rollback atômico (lease inválido → inquilino não persiste; edição não aplicada);
- 2 inquilinos com dependente residente **novo** (Dependent criado, `resident_dependent_id` setado, `tenant` == responsável) e **existente**;
- apartamento indisponível → 400 `lease.apartment` (sem 500);
- CPF/CNPJ duplicado → 400 `tenant.cpf_cnpj`;
- `number_of_tenants==2` sem `rental_value_double` → 400;
- não-admin → 403; sem token → 401.
- **Unit**: guard de locador `None` em `contract_service` → erro; `TenantSerializer.create` captura ids + propaga auditoria aos dependentes; `LeaseSerializer.validate` rejeita apto ocupado.

**Frontend (vitest + MSW no boundary de rede):**
- schema combinado; navegação/validação por passo; montagem do payload (novo vs existente); 2 inquilinos com residente; prefill de existente (conversão `furnitures`→`furniture_ids`); passo de PDF (trata `{pdf_path}` e `202`).
- Regressão: wizard de inquilino atual sem `email`/`phone_alternate`.

---

## 8. Sessões de implementação (sugestão — `/prompt-writing` finaliza numeração/ordem)

> Numeração à parte do range de finanças (S34–50, outra feature). Cada sessão fecha com gate (`ruff`/`mypy`/`pyright`/`pytest` backend; `lint`/`type-check`/`vitest` frontend) e TDD.

| Sessão | Camada | Conteúdo | Depende de |
|--------|--------|----------|-----------|
| O1 | BE | Correções de raiz: `LeaseSerializer.validate` (apto disponível + IntegrityError), `TenantSerializer.create` (captura ids + auditoria dependentes), guard de locador em `contract_service` + testes. | — |
| O2 | BE | `TenantOnboardingService` + `TenantLeaseOnboardingSerializer` + `TenantLeaseOnboardingView` + rota + permissão + testes de integração. | O1 |
| O3 | FE | Extração DRY (deriv. `rental_value`/`due_day`, dependente inline, `parseLocalDate`, fragmento Zod de valores) + remoção de `email`/`phone_alternate` do wizard atual + testes. | — (paralelo a O1/O2) |
| O4 | FE | `TenantLeaseOnboardingWizard` (passos 0–5) + `useOnboardTenantLease` + schema combinado + MSW + testes. | O2, O3 |
| O5 | FE | CTA no dashboard + passo 6 (PDF eager/202) + fios finais + testes + `/audit`. | O4 |

---

## 9. Exemplares (arquivo:linha)

| Para… | Veja |
|-------|------|
| Serializer dual + nested + create/update | `core/serializers.py` (TenantSerializer ~252-316, LeaseSerializer ~344-479) |
| Auditoria via `serializer.save(created_by=...)` | `core/viewsets/rule_views.py:72` |
| Service com `transaction.atomic` + ORM | `core/services/lease_service.py` |
| Geração de PDF / contexto / locador | `core/services/contract_service.py:191`; view `core/views.py:376-393`; `tasks.py` |
| Constraint de apartamento único | `core/models.py:733-736`; `Lease.clean` 753 |
| Wizard multi-step (padrão) | `frontend/app/(dashboard)/tenants/_components/wizard/index.tsx` + `types.ts` |
| Form de contrato (campos/UX/derivações) | `frontend/app/(dashboard)/leases/_components/lease-form-modal.tsx` |
| Geração de PDF no front | `frontend/.../leases/_components/contract-generate-modal.tsx`; `use-leases.ts` (useGenerateContract); `frontend/app/download/route.ts` |
| Apartamentos disponíveis | `frontend/lib/api/hooks/use-apartments.ts` (useAvailableApartments) |
| `Stepper`/`Dialog`/`Form` | `frontend/components/ui/{stepper,dialog,form}.tsx` |
| Dashboard (entrada do CTA) | `frontend/app/(dashboard)/page.tsx`; auth `frontend/store/auth-store.ts` |
