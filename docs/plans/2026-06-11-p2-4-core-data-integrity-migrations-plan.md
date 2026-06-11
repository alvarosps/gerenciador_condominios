# Plano P2.4 — Integridade de dados do core (constraints, soft-delete, CPF, auditoria)

> **Estado:** PLANEJADO — nao executado
> **Prioridade:** FASE P2 · **Branch sugerida:** `fix/core-data-integrity` · **Depende de:** nenhum

## Objetivo

Fechar os buracos de integridade de dados nos models patrimoniais do `core` que ja foram resolvidos em `Lease`, no financeiro legado (migration 0037) e em todo o app `finances`, mas ficaram para tras nos cadastros base. Entrega: unicidade ciente de soft-delete em Building/Furniture/Tenant/Apartment (registro deletado deixa de bloquear recriacao), CPF/CNPJ normalizado para digitos no ponto unico de entrada (corrige a quebra de unicidade e o login WhatsApp dos 2 registros fora do padrao), auditoria confiavel quando o caller usa `update_fields`, historico de dinheiro protegido contra hard delete em cascata, e CheckConstraints monetarias coerentes. Inclui MIGRATIONS — **backup antes** (`python scripts/backup_db.py`).

## Achados endereçados

| Sev | Achado | Arquivo:linha | Correção em uma linha |
| --- | --- | --- | --- |
| MEDIO | Unicidade incondicional vs soft-delete em Building.street_number | `core/models.py:257` | `unique=True` → `UniqueConstraint(condition=Q(is_deleted=False))` |
| MEDIO | Unicidade incondicional vs soft-delete em Furniture.name | `core/models.py:322-324` | idem, `name` condicional ao ativo |
| MEDIO | Unicidade incondicional vs soft-delete em Tenant.cpf_cnpj | `core/models.py:495-500` | idem, `cpf_cnpj` condicional + manter `db_index` |
| MEDIO | Unicidade incondicional vs soft-delete em Apartment(building,number) | `core/models.py:404-405` | `unique_together` → `UniqueConstraint(condition=Q(is_deleted=False))` |
| MEDIO | CPF/CNPJ persistido sem normalizacao (valor limpo do validador descartado) | `core/serializers.py:297-304`, `core/models.py:551-570` | normalizar no `clean()` do model + data migration com deteccao de colisao |
| MEDIO | AuditMixin.save nao acrescenta `updated_at` a `update_fields` | `core/models.py:104-108` | acrescentar `updated_at` ao set quando pk existe e `update_fields` foi passado |
| MEDIO | on_delete=CASCADE em historico de dinheiro (RentPayment) | `core/models.py:1314` | `RentPayment.lease` → `on_delete=PROTECT` |
| MEDIO→BAIXO | Expense.clean (`> 0`) contradiz CheckConstraint (`>= 0`) | `core/models.py:1168-1184` | `clean()` rejeitar so `< 0`; renomear constraint p/ `_non_negative` |
| MEDIO→BAIXO | Landlord singleton sem constraint parcial + logica no save() | `core/models.py:897-918` | `UniqueConstraint(condition=Q(is_active=True,is_deleted=False))` + mover desativacao p/ service |
| MEDIO→BAIXO | CheckConstraints monetarias ausentes (Lease.tag_fee/deposit/pending, RentAdjustment) | `core/models.py:662-715,798-799` | adicionar CheckConstraints `>= 0` |
| MEDIO→BAIXO | Apartment.delete usa bulk `.update()` — nao dispara sync_apartment_is_rented | `core/models.py:436-441` | iterar `lease.delete()` por instancia (como Building.delete) |
| MEDIO→BAIXO | Condominium.name sem unique (tenancy-root, chave de get_or_create) | `core/models.py:215`, `core/models.py:289-292` | `UniqueConstraint(condition=Q(is_deleted=False))` em `name` |

## Abordagem técnica

> Ordem importante: a normalizacao de CPF (passo 2) deve rodar **antes** de qualquer mudanca que dependa da unicidade limpa, e o backup (passo 0) antes de tudo. As migrations sao sequenciais a partir de 0049 (proxima livre: **0050**).

### 0. Backup (pre-requisito, NAO e codigo)
`python scripts/backup_db.py` antes de qualquer `migrate`. Documentar o caminho do dump no commit/handoff.

### 1. Unicidade ciente de soft-delete (4 cadastros core + Condominium)
Padrao canonico ja existente: `Lease` (`core/models.py:731-736`) e migration `0037_soft_delete_unique_constraints.py` (remove `unique_together`/`unique=True` e adiciona `UniqueConstraint(condition=Q(("is_deleted", False)), ...)`).

No `core/models.py`:
- **Building** (`:257`): remover `unique=True` de `street_number`; adicionar `Meta.constraints` com `UniqueConstraint(fields=["street_number"], condition=models.Q(is_deleted=False), name="unique_active_building_street_number")`. Building hoje nao tem `Meta` — criar a inner `class Meta` apos os managers.
- **Furniture** (`:322-324`): remover `unique=True` de `name`; criar `Meta.constraints` com `UniqueConstraint(fields=["name"], condition=models.Q(is_deleted=False), name="unique_active_furniture_name")`.
- **Tenant** (`:495-500`): remover `unique=True` (manter `db_index=True`); adicionar ao `Meta.constraints` existente (`:534`) `UniqueConstraint(fields=["cpf_cnpj"], condition=models.Q(is_deleted=False), name="unique_active_tenant_cpf_cnpj")`.
- **Apartment** (`:404-405`): remover `unique_together = ("building", "number")`; adicionar ao `Meta.constraints` existente (`:414`) `UniqueConstraint(fields=["building", "number"], condition=models.Q(is_deleted=False), name="unique_active_apartment_per_building")`. Manter o index `apt_building_number_idx` (fora de escopo remover indices redundantes — ver Constraints).
- **Condominium** (`:215`): adicionar `Meta` (hoje nao tem) com `constraints=[UniqueConstraint(fields=["name"], condition=models.Q(is_deleted=False), name="unique_active_condominium_name")]`. Isso impoe a invariante que `get_default()`/`Building.save` (`:289-292`, `get_or_create(name=...)`) ja assumem.

Migration **0050_soft_delete_unique_constraints_core**: para cada model, `AlterUniqueTogether(name="apartment", unique_together=set())` (Apartment), `AlterField` removendo `unique=True` (Building.street_number, Furniture.name, Tenant.cpf_cnpj), seguido de `AddConstraint(...)` com cada `UniqueConstraint` acima. Reverse: `RemoveConstraint` + restaurar `unique=True`/`unique_together` (gerado automaticamente por `makemigrations`).

Camada serializer (mensagem PT amigavel em vez de IntegrityError 500): garantir que os serializers de Building/Furniture/Tenant/Apartment validem unicidade contra o **queryset default** (que ja exclui deletados). Verificar `core/serializers.py`: onde houver `UniqueValidator`/`validators` herdados do `unique=True`, trocar por validacao explicita no `validate_<campo>`/`validate()` usando `Model.objects.filter(...).exclude(pk=instance.pk).exists()` e levantar `serializers.ValidationError({campo: "Ja existe ..."})`. Se nao houver validacao explicita hoje, o ModelSerializer derivava o `UniqueValidator` do `unique=True` — ao remover `unique=True`, esse validator some, entao a validacao explicita passa a ser obrigatoria para manter o 400 amigavel.

### 2. Normalizacao de CPF/CNPJ (model clean + data migration)
Causa-raiz: `CPFValidator.__call__`/`CNPJValidator.__call__` (`core/validators/brazilian.py:105-126,207-228`) retornam os digitos limpos, mas `Tenant.clean()` (`:563-570`) so chama as funcoes de conveniencia `validate_cpf`/`validate_cnpj` (`:301-324`, retorno descartado) e o `TenantSerializer.validate()` (`:297-304`) descarta o retorno do validador.

- **Model `Tenant.clean()`** (`core/models.py:563-570`): normalizar no ponto unico de entrada. Trocar o bloco para usar o instanciador do validador e reatribuir:
  ```python
  validator = CNPJValidator() if self.is_company else CPFValidator()
  self.cpf_cnpj = validator(self.cpf_cnpj)
  ```
  envolto no `try/except ValidationError` existente (re-levantar `{"cpf_cnpj": e.message}`). Isso normaliza para digitos antes de persistir. `Tenant.save` ja chama `full_clean()` quando nao ha `update_fields` (`:545-549`), entao toda criacao/edicao via API passa por aqui.
- **`Landlord`** (`:851`, sem unicidade) e **`Dependent`** (`:593-598`, sem unicidade): aplicar a mesma normalizacao para consistencia de lookups por CPF. `Landlord` nao tem `clean()` hoje — adicionar um `clean()` minimo que normalize `cpf_cnpj` (PF/PJ conforme heuristica de comprimento dos digitos, ou validar PF por default com fallback PJ — alinhar com a correcao de classe de excecao do plano P2.x de serializers; aqui escopar so a normalizacao, sem mudar a deteccao PF/PJ se ela vive no serializer). `Dependent.cpf_cnpj` e opcional (`blank=True`) — normalizar so quando preenchido.
- **Serializers**: garantir que o valor que chega ao model ja venha limpo OU confiar no `clean()` do model (preferivel — ponto unico). Como `Tenant.save→full_clean→clean` normaliza, o serializer nao precisa reatribuir; mas o `TenantSerializer.validate()` continua chamando o validador so para 400 amigavel (mantendo a correcao de classe de excecao que pertence ao plano de serializers, fora deste escopo). **Nao** duplicar a normalizacao nos dois lugares (DRY) — model e a fonte.

- **Data migration 0051_normalize_tenant_cpf_cnpj** (`RunPython` com reverse `RunPython.noop`):
  1. Iterar `Tenant.all_objects.all()` (incluir deletados — eles tambem ocupam a chave unica condicional so quando ativos, mas normalizar todos mantem o banco coerente).
  2. Para cada, computar `cleaned = re.sub(r"[^0-9]", "", cpf_cnpj)`.
  3. **Deteccao de colisao**: antes de gravar, agrupar por `cleaned` entre registros **ativos** (`is_deleted=False`). Se dois ativos colidirem apos limpar, a migration deve **abortar com `RuntimeError`** listando os ids/cpf colidentes (nao escolher um arbitrariamente) — o operador resolve manualmente e re-roda. (Colisao entre ativo e deletado e tolerada pela constraint condicional; nao aborta.)
  4. Gravar `cleaned` via `update(cpf_cnpj=cleaned)` no manager `all_objects` (bypassa save/clean — intencional na migration), so quando difere.
  5. Repetir para `Landlord` e `Dependent` (sem deteccao de colisao — nao tem unicidade).
  Usar `apps.get_model("core", "Tenant")` (migration-safe), nao o model importado.
  > Nota dos achados: ha 73 formatados vs 2 so-digitos no banco; apos a normalizacao todos ficam so-digitos, destravando o login WhatsApp dos 2 fora do padrao e a unicidade.

### 3. AuditMixin.save respeita update_fields (`core/models.py:104-108`)
Trocar o override para acrescentar `updated_at` ao `update_fields` quando o registro existe e o caller passou `update_fields` sem ele:
```python
def save(self, *args: Any, **kwargs: Any) -> None:
    if self.pk:
        self.updated_at = timezone.now()
        update_fields = kwargs.get("update_fields")
        if update_fields is not None:
            kwargs["update_fields"] = {*update_fields, "updated_at"}
    super().save(*args, **kwargs)
```
Depois, **remover as inclusoes manuais redundantes** de `"updated_at"` que viraram supervalentes (DRY): `SoftDeleteMixin.delete` (`:172`) e `.restore` (`:188-190`) ja listam `updated_at` manualmente — agora o mixin garante, mas mante-las nao quebra (set deduplica). Mante-las e aceitavel; o ganho real e nos call sites que **nao** listavam (`contract_service.py:388`, `serializers.py:528,549`, `proof_views.py:98`, etc.) — esses passam a auditar corretamente **sem alteracao no call site**. Nao alterar os call sites neste plano (a raiz no mixin basta).

### 4. RentPayment.lease → PROTECT (`core/models.py:1314`)
Trocar `on_delete=models.CASCADE` por `on_delete=models.PROTECT` em `RentPayment.lease`. Racional alinhado a `finances` (`PaymentAllocation.bill` PROTECT, docstring de Bill: nunca apagar historico real). **Avaliados e mantidos CASCADE** neste plano (escopo minimo, KISS): `RentAdjustment.lease` (`:786-791`) e `PaymentProof.lease` (`:1693-1697`) — reajuste e comprovante nao sao dinheiro recebido; trocar so o pagamento. Documentar a decisao no commit. Migration: `AlterField` em `rentpayment.lease`. **Atencao**: nenhum codigo de prod passa `hard_delete=True` (grep confirma), entao PROTECT nao quebra fluxo de soft-delete; o efeito e barrar um hard delete acidental de Lease que apagaria pagamentos.

### 5. Expense.clean alinhado a `>= 0` + rename de constraint (`core/models.py:1168-1184`)
- `clean()`: trocar `if self.total_amount is not None and self.total_amount <= 0:` por `< 0`, e mensagem `"O valor total nao pode ser negativo."`.
- Renomear a constraint `expense_total_amount_positive` para `expense_total_amount_non_negative` (nome passa a refletir `>= 0`). Migration: `RemoveConstraint(name="expense_total_amount_positive")` + `AddConstraint(CheckConstraint(condition=Q(total_amount__gte=0), name="expense_total_amount_non_negative"))`.
- Verificar `ExpenseSerializer` em `core/serializers.py`: se houver `validate_total_amount` exigindo `> 0`, alinhar para `< 0` rejeitado (negativo) — manter `0` valido. **Modulo legado**: so corrigir a contradicao, sem refatorar o serializer alem disso.

### 6. CheckConstraints monetarias ausentes
Adicionar (todas `>= 0`, condicao tolerante a `NULL` que o Postgres ja trata como `UNKNOWN`/passa):
- **Lease** (`Meta.constraints`, `:731`): `CheckConstraint(condition=Q(tag_fee__gte=0), name="lease_tag_fee_non_negative")`, `Q(deposit_amount__gte=0)` → `lease_deposit_amount_non_negative`, `Q(pending_rental_value__gte=0)` → `lease_pending_rental_value_non_negative`. `rental_value` ja tem (`:737-740`).
- **RentAdjustment** (`:798-799`, hoje sem `Meta.constraints`): `CheckConstraint(condition=Q(previous_value__gte=0), name="rent_adjustment_previous_value_non_negative")` e `Q(new_value__gte=0)` → `rent_adjustment_new_value_non_negative`. Criar `Meta` (hoje so tem managers).
Migration: `AddConstraint` para cada. Reverse automatico (`RemoveConstraint`).

### 7. Landlord: constraint parcial + desativacao em service (`core/models.py:897-918`)
- **Constraint**: `Meta.constraints` (hoje so `verbose_name`, `:889-891`) += `UniqueConstraint(fields=["is_active"], condition=models.Q(is_active=True, is_deleted=False), name="unique_active_landlord")`. Garante 1 ativo mesmo sob concorrencia.
- **Service**: criar `core/services/landlord_service.py` com `LandlordService.activate(landlord, *, updated_by=None)` que, dentro de `transaction.atomic()`, desativa os demais (`Landlord.objects.filter(is_active=True).exclude(pk=landlord.pk).update(is_active=False, updated_at=timezone.now(), updated_by=updated_by)`) e seta `landlord.is_active=True; landlord.save()`. Mover a logica para ca e **remover o override `Landlord.save()`** (`:897-902`).
- **Call site**: `LandlordViewSet.current` (`core/viewsets/landlord_views.py:79`) hoje faz `serializer.save(is_active=True)`. Refatorar para `landlord = serializer.save()` seguido de `LandlordService.activate(landlord, updated_by=request.user)` — o viewset delega ao service (camada correta). Conferir que `get_active()` (`:915-918`) continua funcionando (com a constraint, no maximo 1 ativo).
  > Sem a constraint parcial nao seria possivel ter mais de um ativo, mas a desativacao em massa precisa rodar dentro da mesma transacao da ativacao para nao violar a constraint transitoriamente — usar `transaction.atomic()` e desativar **antes** de ativar o novo.

### 8. Apartment.delete dispara sync_apartment_is_rented (`core/models.py:436-441`)
Hoje o bulk `self.leases.filter(is_deleted=False).update(is_deleted=True, ...)` nao dispara o signal `post_save`/`sync_apartment_is_rented` (`core/signals.py:193-198`), entao um apartamento **restaurado** depois fica com `is_rented` incoerente, e a auditoria (`updated_at`) dos leases nao muda. Trocar por iteracao por instancia, espelhando `Building.delete` (`:302-304`):
```python
if not hard_delete:
    for lease in self.leases.filter(is_deleted=False):
        lease.delete(hard_delete=False, deleted_by=deleted_by)
```
`Lease.delete` (herdado de `SoftDeleteMixin`) chama `save(update_fields=[...])`, que dispara `post_save` → `sync_apartment_is_rented` recalcula `is_rented` (passa a `False` quando nao ha mais lease ativo). Sem migration (mudanca de comportamento de metodo).
> Nota: `sync_apartment_is_rented` usa `Exists(Lease.objects...)` com o manager default (exclui deletados), entao apos soft-delete dos leases o `is_rented` vira `False` corretamente.

## Arquivos a criar / modificar

**Modificar:**
- `core/models.py` — Building (remover `unique=True`, +Meta+constraint), Furniture (idem), Tenant (`cpf_cnpj` sem `unique`, +constraint, `clean()` normaliza), Apartment (remover `unique_together`, +constraint, `delete()` itera leases), Condominium (+Meta+constraint name), AuditMixin.save (update_fields), Landlord (remover `save()` override, +constraint, `clean()` normaliza cpf), Dependent (`clean()` normaliza cpf opcional), Expense (`clean()` `< 0`), Lease (+CheckConstraints tag_fee/deposit/pending), RentAdjustment (+Meta+CheckConstraints), RentPayment (`lease` PROTECT).
- `core/serializers.py` — validacao de unicidade explicita (Building/Furniture/Tenant/Apartment) contra queryset default p/ 400 amigavel; remover `UniqueValidator` orfaos se existirem; alinhar `validate_total_amount` do Expense (`< 0`) se existir.
- `core/viewsets/landlord_views.py` — `current()` delega ativacao a `LandlordService.activate`.

**Criar:**
- `core/services/landlord_service.py` — `LandlordService.activate(landlord, *, updated_by=None)`.
- `core/migrations/0050_soft_delete_unique_constraints_core.py` — Alter/Remove unique + AddConstraint (Building/Furniture/Tenant/Apartment/Condominium); rename Expense constraint; RentPayment.lease PROTECT; CheckConstraints monetarias (Lease/RentAdjustment); unique_active_landlord. (Pode ser 1 migration; se `makemigrations` gerar 2+ por dependencia de campo→constraint, manter a ordem.)
- `core/migrations/0051_normalize_tenant_cpf_cnpj.py` — data migration `RunPython` (normaliza Tenant/Landlord/Dependent + deteccao de colisao em Tenant ativo).

**Testes (criar/estender):**
- `tests/integration/test_soft_delete.py` — recriacao apos delete (Building/Furniture/Tenant/Apartment).
- `tests/unit/test_models.py` — AuditMixin.save com update_fields; Apartment.delete sync is_rented; Tenant/Landlord/Dependent cpf normalizado no clean; Expense.clean `0` valido.
- `tests/unit/test_validators.py` — (ja cobre validadores; nada novo, mas confirmar retorno limpo usado).
- `tests/integration/test_landlord_rule_views.py` — ativacao via service mantem 1 ativo; constraint parcial.
- `tests/integration/test_rent_adjustment.py` ou novo — CheckConstraints monetarias barram negativo.
- `tests/unit/test_migrations_cpf_normalization.py` (novo) — colisao aborta; normalizacao idempotente.

## TDD — cenários de teste

> Red→Green→Refactor→Verify. Mockar SOMENTE fronteiras externas. Aqui nada externo — usar ORM real em transacao (pytest-django `db`).

**Soft-delete unicidade (regressao que prova o bug):**
- `test_recreate_building_after_soft_delete` — criar Building street_number=836, soft-delete, recriar mesmo street_number → sucesso (hoje IntegrityError).
- `test_recreate_furniture_name_after_soft_delete` — idem Furniture.name.
- `test_recreate_tenant_cpf_after_soft_delete` — idem Tenant.cpf_cnpj.
- `test_recreate_apartment_number_after_soft_delete` — idem Apartment(building,number).
- `test_two_active_buildings_same_street_number_rejected` — dois ativos com mesmo street_number → IntegrityError/ValidationError (constraint ainda protege ativos).
- `test_serializer_returns_400_on_duplicate_active_building` — POST duplicado ativo → 400 com mensagem PT no campo, nao 500.
- `test_two_active_condominiums_same_name_rejected` — Condominium.name unico entre ativos.

**Normalizacao CPF:**
- `test_tenant_cpf_normalized_to_digits_on_save` — salvar `"529.982.247-25"` → banco grava `"52998224725"`.
- `test_tenant_formatted_and_raw_cpf_are_same_identity` — criar com formatado, tentar criar com raw mesmo CPF → bloqueado (mesma identidade).
- `test_company_cnpj_normalized_on_save` — `is_company=True` normaliza CNPJ.
- `test_landlord_cpf_normalized` / `test_dependent_blank_cpf_stays_blank`.
- `test_data_migration_normalizes_existing` — fixture com cpf formatado, rodar migration func → vira digitos.
- `test_data_migration_aborts_on_active_collision` — dois Tenant ativos que limpam para o mesmo cpf → `RuntimeError` (nao grava arbitrariamente).
- `test_data_migration_tolerates_active_vs_deleted_collision` — ativo + deletado mesmo cpf limpo → migration completa sem abortar.

**AuditMixin / auditoria:**
- `test_save_with_update_fields_persists_updated_at` — salvar com `update_fields=["contract_generated"]`, `updated_at` no banco muda (hoje nao muda). Regressao do bug.
- `test_save_with_update_fields_does_not_touch_other_fields` — so `contract_generated` e `updated_at` mudam, demais intactos.
- `test_full_save_still_updates_updated_at` — save normal (sem update_fields) ainda atualiza.

**Apartment.delete cascade:**
- `test_apartment_delete_sets_is_rented_false_via_signal` — apto com lease ativo, soft-delete apto → leases soft-deletados e `is_rented` recalculado para `False`; leases tem `updated_at` novo.
- `test_apartment_restore_then_is_rented_consistent` — restaurar apto nao deixa `is_rented=True` orfao (sem lease ativo).

**RentPayment PROTECT:**
- `test_hard_delete_lease_with_payments_is_protected` — `lease.delete(hard_delete=True)` com RentPayment → `ProtectedError`.
- `test_soft_delete_lease_keeps_payments` — soft-delete normal nao apaga pagamentos (sanidade).

**Expense / CheckConstraints monetarias:**
- `test_expense_clean_allows_zero` — `Expense(total_amount=0).full_clean()` nao levanta (hoje levanta).
- `test_expense_clean_rejects_negative` — `total_amount=-1` levanta ValidationError.
- `test_lease_tag_fee_negative_rejected_by_db` — inserir Lease com tag_fee negativo → IntegrityError.
- `test_lease_deposit_negative_rejected` / `test_lease_pending_rental_value_negative_rejected`.
- `test_rent_adjustment_negative_values_rejected` — previous_value/new_value negativos → IntegrityError.

**Landlord:**
- `test_activate_deactivates_others` — `LandlordService.activate(l2)` desativa `l1`; so 1 ativo.
- `test_partial_unique_active_landlord_constraint` — tentar marcar 2 ativos via `update()` direto → IntegrityError.
- `test_landlord_activate_sets_updated_at_on_deactivated` — desativados tem `updated_at`/`updated_by` atualizados (nao bypassa auditoria).
- `test_landlord_viewset_current_put_activates_via_service` (integration) — PUT cria/ativa, GET retorna o ativo unico.

## Migrations / dados

- **Backup obrigatorio antes**: `python scripts/backup_db.py` (anotar caminho no handoff). Migrations alteram constraints e um FK (`PROTECT`) — operacao de schema, nao destrutiva de dados, mas backup e regra do projeto.
- **0050_soft_delete_unique_constraints_core** (schema): `AlterUniqueTogether(apartment, set())`, `AlterField` (Building.street_number/Furniture.name/Tenant.cpf_cnpj removendo `unique`), `AddConstraint` (5 unique condicionais + unique_active_landlord + CheckConstraints monetarias Lease/RentAdjustment), `RemoveConstraint`+`AddConstraint` (rename Expense p/ `_non_negative`), `AlterField(rentpayment.lease, PROTECT)`. Reverse: gerado por `makemigrations` (restaura unique/unique_together/CASCADE/nome antigo).
- **0051_normalize_tenant_cpf_cnpj** (dados): `RunPython(forward, RunPython.noop)`. `forward` normaliza Tenant/Landlord/Dependent via `apps.get_model`, abortando com `RuntimeError` em colisao entre Tenant **ativos**. Idempotente (so grava quando difere).
- **RLS**: este plano **nao cria tabelas** — todas as operacoes sao `Alter`/`AddConstraint`/`RunPython`, entao **nao** ha `ENABLE ROW LEVEL SECURITY` a adicionar (a regra so se aplica a tabelas novas). Confirmar no `makemigrations` que nenhuma `CreateModel` foi gerada.
- **Correcao de dado vivo**: os 2 CPF so-digitos + 73 formatados ficam todos so-digitos apos 0051; o login WhatsApp dos 2 fora do padrao destrava. Rodar `python manage.py migrate core` em local apos backup; em **prod (Supabase)** aplicar via deploy normal (Render roda migrate) — confirmar que 0051 nao aborta no dataset de prod fazendo um `--plan`/dry-run logico (rodar a deteccao de colisao como query antes do deploy).

## Constraints (o que NÃO fazer)

- **Modulo financeiro pessoal legado e DEPRECATED**: `Expense`/`RentPayment`/`RentAdjustment` so recebem as correcoes pontuais listadas (clean `>=0`, PROTECT, CheckConstraints monetarias). **Nao** refatorar serializers/viewsets financeiros, nao mexer em N+1, nao trocar `max_digits`, nao mexer no `Expense.restore` (janela ±2s e outro achado/plano).
- **Nao** trocar `RentAdjustment.lease`/`PaymentProof.lease` para PROTECT neste plano (decisao explicita: so RentPayment).
- **Nao** remover indices redundantes (`apt_building_number_idx`, `lease_start_date_idx`, etc.) — e outro achado LOW, fora de escopo.
- **Nao** tocar em OAuthExchangeCode, formato de erro `{"error"}` vs `{"detail"}`, TenantSerializer hard-delete de dependentes, classe de excecao do LandlordSerializer/TenantSerializer CNPJ — sao achados de **outros planos** (P2 serializers/auth). A normalizacao de CPF aqui e so no `clean()` do model; nao reescrever a deteccao PF/PJ do serializer.
- **Nao** usar `# noqa`, `# type: ignore`, `eslint-disable`, `@ts-ignore`, `from __future__ import annotations`, TODO/FIXME, re-exports nem shims. Refatoracao completa: ao mover a logica do `Landlord.save`, atualizar TODOS os call sites (`landlord_views.py`).
- **Nao** editar migrations existentes (hook bloqueia) — criar 0050/0051 via `makemigrations`.
- **Nao** rodar migrate sem backup. **Nao** rodar a suite cheia como gate (flakiness de xdist/Redis e pre-existente) — escopar.

## Critérios de aceite (binários)

- [ ] Backup criado antes de qualquer migrate (caminho registrado no handoff).
- [ ] `Building`/`Furniture`/`Tenant`/`Apartment`/`Condominium` permitem recriar registro apos soft-delete; dois ativos com mesma chave ainda sao rejeitados.
- [ ] Serializers retornam 400 PT (campo) em duplicata ativa, nunca 500/IntegrityError vazado.
- [ ] `Tenant`/`Landlord`/`Dependent` persistem `cpf_cnpj` so com digitos; formatado e raw do mesmo CPF sao a mesma identidade.
- [ ] Data migration 0051 normaliza existentes e **aborta** em colisao entre Tenant ativos (nao grava arbitrario).
- [ ] `AuditMixin.save` atualiza `updated_at` mesmo com `update_fields` (verificado em call site real, ex.: gerar contrato).
- [ ] `RentPayment.lease` e `PROTECT`; hard delete de Lease com pagamentos levanta `ProtectedError`.
- [ ] `Expense.full_clean()` aceita `total_amount=0` e rejeita negativo; constraint renomeada para `expense_total_amount_non_negative`.
- [ ] CheckConstraints monetarias barram negativo em Lease.tag_fee/deposit_amount/pending_rental_value e RentAdjustment.previous_value/new_value.
- [ ] So existe 1 Landlord ativo (constraint parcial); ativacao via `LandlordService.activate` em transacao; `Landlord.save` override removido; viewset delega ao service.
- [ ] `Apartment.delete` soft-deleta leases por instancia → `is_rented` recalculado e `updated_at` dos leases atualizado.
- [ ] `makemigrations` nao gera `CreateModel` (logo nenhuma RLS nova exigida); `--check` limpo.
- [ ] Gate de verificacao (escopado + regressao) passa com zero erros E zero warnings.

## Gate de verificação

Backend (escopado nos arquivos editados + regressao dirigida; a suite cheia tem flakiness pre-existente de xdist/Redis — NAO e bloqueio):

```bash
python scripts/backup_db.py
python manage.py makemigrations core --check --dry-run   # confirmar que 0050/0051 cobrem tudo
python manage.py migrate core                            # forward
ruff check core/ && ruff format --check core/
mypy core/
pyright
python -m pytest tests/unit/test_models.py tests/unit/test_validators.py \
  tests/integration/test_soft_delete.py tests/integration/test_landlord_rule_views.py \
  tests/integration/test_rent_adjustment.py tests/integration/test_tenant_api.py \
  tests/integration/test_tenant_crud.py tests/unit/test_signals.py tests/unit/test_lease_signal.py \
  tests/unit/test_migrations_cpf_normalization.py -p no:randomly
# regressao dirigida do que toca AuditMixin/Apartment/Lease:
python -m pytest tests/unit/test_expense_service.py tests/integration/test_expense_api.py \
  tests/integration/test_lease_crud.py -p no:randomly
# reverse das migrations (sanidade):
python manage.py migrate core 0049
python manage.py migrate core
```

Zero erros E zero warnings em Ruff, mypy, Pyright, pytest. Nao ha mudanca de frontend neste plano (so backend/models/migrations).

## Handoff

**Commit message sugerida:**
```
fix(core): soft-delete-aware uniqueness, CPF normalization, audit & money integrity

- Building/Furniture/Tenant/Apartment/Condominium: unique → UniqueConstraint(condition=is_deleted=False)
- Tenant/Landlord/Dependent.clean: normalize cpf_cnpj to digits (+ data migration 0051 with collision detection)
- AuditMixin.save: include updated_at in update_fields so partial saves audit correctly
- RentPayment.lease: CASCADE → PROTECT (never erase money history on hard delete)
- Expense.clean aligned to >= 0; constraint renamed expense_total_amount_non_negative
- CheckConstraints (>= 0) on Lease.tag_fee/deposit/pending + RentAdjustment.previous/new_value
- Landlord: unique_active_landlord partial constraint; activation moved to LandlordService.activate
- Apartment.delete iterates lease.delete() so sync_apartment_is_rented fires

Migrations 0050 (schema) + 0051 (data). Backup taken before migrate.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
```

**Estado/docs a atualizar:**
- Atualizar `MEMORY.md` (entrada de integridade do core) com o resultado.
- Em prod: confirmar (query de deteccao de colisao) que 0051 nao aborta antes do deploy do Render; rodar `get_advisors type=security` apos o deploy so para sanidade (nenhuma tabela nova, nenhum `rls_disabled` esperado).

**O proximo plano assume:** CPF ja normalizado no banco (planos de auth/WhatsApp login podem confiar em lookup por digitos); unicidade ja ciente de soft-delete (planos de cadastro nao precisam tratar recriacao); `AuditMixin.save` ja confiavel (planos que usam `update_fields` nao precisam listar `updated_at` manualmente); `LandlordService.activate` existe (planos de contrato podem chamar em vez de `serializer.save(is_active=True)`).
