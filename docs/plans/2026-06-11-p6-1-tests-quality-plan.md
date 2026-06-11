# Plano P6.1 — Qualidade de testes: warnings, mock policy, factories, gaps de fronteira

> **Estado:** PLANEJADO — não executado
> **Prioridade:** FASE P6 (Testes/Docs/CI/Higiene) · **Branch sugerida:** `test/quality-hardening` · **Depende de:** nenhum bloqueante. Idealmente roda DEPOIS dos planos de fix funcionais (cada fix carrega seus próprios testes); este plano consolida os gaps transversais de qualidade de teste que sobram entre eles. Não deve reverter nem competir com testes adicionados por outros planos.

## Objetivo

Endurecer a malha de testes para que ela passe a pegar bugs reais em vez de mascará-los. Hoje três políticas do projeto estão sendo violadas pela própria suite: (1) `pytest.ini` e `vitest.config.mts` suprimem warnings em bloco — o oposto da regra "zero warnings"; (2) 26 arquivos de teste de componente mockam hooks internos (`vi.mock('@/lib/api/hooks/...')`), violando a mock policy — foi exatamente esse padrão que deixou o bug do `condominium_id` passar; (3) as factories compartilham um `itertools.cycle` global de CPFs hardcoded, criando flakiness de ordem latente sob a suite cheia. Este plano remove as supressões em bloco (trocando-as por ignores cirúrgicos por mensagem/módulo de terceiro), migra os testes de componente do módulo NOVO (`finances/`) para `QueryClientProvider` real + MSW na fronteira HTTP com shape BRUTO da API, troca o gerador de CPFs por um contador de CPFs válidos com constantes nomeadas, e fecha os gaps de teste de fronteira (403 em ações de dinheiro, fixture de invoice só em memória, remoção de testes vazios).

## Achados endereçados

| Sev | Achado | Arquivo:linha | Correção em uma linha |
| --- | --- | --- | --- |
| MÉDIO | `pytest.ini` ignora `DeprecationWarning`/`UserWarning`/`RuntimeWarning` em bloco (contradiz zero-warnings) | `pytest.ini:79-83` | Trocar `ignore::*Warning` global por `filterwarnings = error` + ignores cirúrgicos por `:mensagem:Categoria:módulo` |
| MÉDIO | `vitest` com `dangerouslyIgnoreUnhandledErrors: true` mascara erros não tratados | `frontend/vitest.config.mts:18` | Remover a flag; tratar a causa raiz dos erros que aparecerem |
| MÉDIO | MSW `onUnhandledRequest` em `warn` (silencioso) — requests sem handler não falham | `frontend/tests/setup.ts` (server.listen) | Mudar para `onUnhandledRequest: 'error'` |
| MÉDIO | 26 arquivos de teste de componente mockam hooks internos `@/lib/api/hooks/*` (viola mock policy; deixou passar bug do `condominium_id`) | `frontend/app/(dashboard)/finances/**/__tests__/*.tsx` (ex.: `bills/__tests__/bills-page.test.tsx:10-15`) | Migrar para `renderWithProviders` + MSW (fronteira HTTP), começando pelo módulo novo `finances/` |
| MÉDIO | Mocks MSW do módulo legado usam shape pós-parse (com `_id` no read, decimais como number) | `frontend/tests/mocks/handlers.ts` + `data/finances` | Mocks devem usar shape BRUTO da API (sem write-only `_id` nos reads; decimais como string) |
| MÉDIO→BAIXO | Factories com `itertools.cycle` GLOBAL de CPFs + mesmos CPFs hardcoded em ~39 arquivos (flakiness de ordem latente) | `tests/factories.py:12-34` | Gerador de CPFs válidos por contador (sem estado global compartilhado entre testes) + constantes nomeadas |
| MÉDIO→BAIXO | Patch de `send_verification_code` (service interno) em vez da fronteira Twilio `Client` | `tests/integration/test_tenant_auth_api.py:79,104,123,147,210,237,246` | Mover o mock para a fronteira Twilio (`twilio.rest.Client`) |
| BAIXO | Fixture de invoice escreve `.pdf` no working tree a cada run | `tests/unit/test_finances/conftest.py:36-45` | Renderizar o PDF só em memória (não escrever o `.pdf` ao lado do `.txt`) |
| BAIXO | Testes que não testam nada (assert de import / `assert True`) | varrer `tests/` e `frontend/` | Remover ou substituir por asserção de comportamento real |
| BAIXO | Gaps de teste 403 em ações de dinheiro: `condo-month-closes/close`, `/reopen`, `bills/{id}/unpay` (DELETE payment) | `tests/integration/test_finances/test_finance_permissions.py:8-19` | Adicionar essas rotas à matriz `WRITE_ENDPOINTS` |
| BAIXO | Confirmar testes cross-month/fevereiro de `calculate_late_fee` (coberto em P2.1) | `core/services/fee_calculator.py:82-99` | Verificar presença; se ausente, registrar dependência em P2.1, NÃO duplicar |

## Abordagem técnica

Ordem de execução (cada bloco fecha com seu próprio gate antes de seguir):

### 1. Remover supressões de warning em bloco (backend)

Em `pytest.ini:79-83`, o estado atual é:

```ini
filterwarnings =
    error
    ignore::UserWarning
    ignore::DeprecationWarning
    ignore:.*timezone.*:RuntimeWarning
```

As três linhas `ignore::UserWarning` e `ignore::DeprecationWarning` apagam categorias inteiras, escondendo warnings do nosso próprio código. Substituir por `error` global + ignores cirúrgicos no formato `action:message_regex:category:module:lineno`, restritos a libs de terceiros. Procedimento:

1. Rodar a suite UMA vez com apenas `filterwarnings = error` (sem ignores) num branch de exploração para capturar a lista real de warnings que estouram. Registrar cada um: mensagem, categoria, módulo emissor.
2. Para cada warning de TERCEIRO (ex.: pacotes em `site-packages` — django-stubs, model_bakery, reportlab, pdfplumber, etc.), adicionar um ignore cirúrgico ancorado no módulo: `ignore:<regex da mensagem>:<Categoria>:<módulo de terceiro>`. NUNCA ancorar no nosso código (`core.*`, `finances.*`, `tests.*`).
3. Para cada warning emitido pelo NOSSO código, corrigir o código-fonte (essa é a política zero-warnings). Se o warning vier de um fix pendente de outro plano (ex.: o `RuntimeWarning` de naive datetime do timezone), manter o ignore `ignore:.*received a naive datetime.*:RuntimeWarning:django.db.models.fields` ancorado no módulo do Django, e anotar no Handoff que ele sai quando o plano de timezone aterrissar.
4. O `ignore:.*timezone.*:RuntimeWarning` atual é amplo demais (casa qualquer mensagem com "timezone"); estreitar para a mensagem e módulo reais do Django.

Resultado: `filterwarnings` começa em `error` e só lista ignores ancorados em módulos de `site-packages`, com comentário explicando cada um.

### 2. Remover supressões de erro no vitest (frontend)

1. Em `frontend/vitest.config.mts:18`, remover a linha `dangerouslyIgnoreUnhandledErrors: true,`.
2. Em `frontend/tests/setup.ts`, localizar `server.listen({ onUnhandledRequest: 'warn' })` e trocar para `onUnhandledRequest: 'error'` — qualquer request sem handler MSW passa a falhar o teste (força declarar a fronteira HTTP explicitamente).
3. Rodar `npm run test:unit`. Para cada erro/rejeição não tratada que aparecer, corrigir a causa raiz (handler MSW ausente, promise não aguardada, cleanup faltando). NÃO reintroduzir supressão.

### 3. Migrar testes de componente do módulo NOVO para MSW (fronteira HTTP)

O padrão proibido está em arquivos como `frontend/app/(dashboard)/finances/bills/__tests__/bills-page.test.tsx:10-15`:

```ts
import * as billHooks from '@/lib/api/hooks/use-bills';
vi.mock('@/lib/api/hooks/use-bills', async (importOriginal) => {
  const actual = await importOriginal<typeof billHooks>();
  return { ...actual, useGenerateMonthBills: vi.fn() };
});
```

Isso mocka o hook interno (`useGenerateMonthBills`) — o componente nunca exercita o caminho real query→client→API. A migração troca o mock de hook por um handler MSW que intercepta o POST real de `bills/generate_month/`:

1. Para cada teste de `finances/**/__tests__/*.tsx` que tem `vi.mock('@/lib/api/hooks/...')`, remover o `vi.mock` do hook e o `vi.mocked(...).mockReturnValue(...)`.
2. Renderizar com `renderWithProviders(<Page />, { queryClient: createTestQueryClient() })` (já usado nesses testes — ver `bills-page.test.tsx:5,69`), que injeta `QueryClientProvider` real com cache curto.
3. Substituir a asserção "mutate foi chamado com X" por asserção de COMPORTAMENTO: spy no handler MSW (capturar o body do request via `server.use(http.post(...))`) e/ou asserir o efeito visível na UI (toast de sucesso, linha nova na tabela, modal fechando). O endpoint correto vem de `lib/api/hooks/use-bills.ts` (a URL real que o axios chama).
4. Manter o mock SÓ na fronteira HTTP (MSW) e no estado de auth client-only (`useAuthStore.setState`, já usado — `bills-page.test.tsx:36-41`), que é estado de cliente, não internal lib.
5. Ordem de migração (módulo novo primeiro): `bills/`, `installment-plans/`, `income-entries/`, `reserve/`, `month-close/`, `employees/`, `categories/`, e os `_components/finance-*` do dashboard. Os 5 arquivos do módulo legado/admin (`apartments`, `buildings`, `furniture`, `leases`, `tenants`, `contract-template`, `financial/daily`) ficam para um plano posterior — este plano os deixa intocados (constraint abaixo).

### 4. Mocks MSW com shape BRUTO da API

A API DRF retorna, no read, FK aninhada (`building: {...}`) e NUNCA o campo write-only `building_id`; decimais saem como STRING (`"1500.00"`), não number. Vários geradores em `frontend/tests/mocks/data/finances` e os literais em `handlers.ts` usam decimais como number (ex.: `amount: 500`) e às vezes incluem `_id` no objeto de read. Procedimento:

1. Auditar `frontend/tests/mocks/data/finances` e `handlers.ts` campo a campo contra os serializers reais de `finances/serializers.py` (read shape) — confirmar: decimais como string, FKs aninhadas no read, ausência de `*_id` nos payloads de resposta.
2. Corrigir os geradores `createMock*` para emitir o shape bruto. Os componentes/hooks que hoje só passam porque consomem o shape pós-parse devem ser ajustados (ou já estão corretos e o mock é que mente — nesse caso o mock corrigido pode expor um bug real, que então é corrigido).
3. Esse alinhamento é o que teria pego o bug do `condominium_id`: com shape bruto, o teste do form de bill exercitaria a serialização real do `_id` de escrita.

### 5. Gerador de CPFs válidos por contador (factories)

Em `tests/factories.py:12-34`, `TEST_CPFS` é uma lista finita + `_cpf_cycle = itertools.cycle(TEST_CPFS)` GLOBAL de módulo. Sob a suite cheia (paralela), a posição do cycle depende da ordem de import/execução, o que já causou falhas intermitentes de `full_clean` (documentado no próprio comentário das linhas 16-19). Substituir por um gerador determinístico de CPFs com dígitos verificadores válidos:

1. Adicionar uma função `_generate_valid_cpf(seed: int) -> str` que constrói os 9 dígitos base a partir de `seed` e calcula os 2 dígitos verificadores com o algoritmo oficial (mesma matemática de `core/validators/brazilian.py`). Isso garante CPF SEMPRE válido, sem depender de uma lista hardcoded.
2. Substituir `_cpf_cycle`/`_next_cpf` por um contador `itertools.count()` encapsulado, e `make_tenant` passa a chamar `_generate_valid_cpf(next(_counter))`. O contador ainda é de módulo, mas como cada valor é único e válido, não há colisão nem dependência de ordem (o problema antigo era a lista finita reciclando valores já usados).
3. Extrair os poucos CPFs canônicos que testes específicos PRECISAM fixos (ex.: `529.982.247-25` usado em `test_tenant_auth_api.py:25`) para constantes nomeadas em `tests/factories.py` (ex.: `CPF_VALID_PRIMARY = "52998224725"`), e importá-las nesses testes em vez de re-hardcodar a string em ~39 arquivos. NÃO reescrever todos os 39 de uma vez — substituir só onde o literal é load-bearing (auth, unicidade, lookup por CPF); os demais que apenas precisam de "um CPF válido qualquer" passam a usar `make_tenant()` sem argumento.

### 6. Mock na fronteira Twilio (não no service interno)

`tests/integration/test_tenant_auth_api.py` faz `patch("core.viewsets.auth_views.send_verification_code")` (linhas 79, 104, 123, 147, 210, 237, 246). `send_verification_code` é código NOSSO (`core/services/whatsapp_service.py:72`) — mockar ele esconde o bug do `content_variables` (dict vs JSON string) reportado na auditoria de services. A fronteira externa real é `twilio.rest.Client` instanciado em `send_whatsapp_message` (`whatsapp_service.py:62-68`). Procedimento:

1. Trocar todos os `patch("core.viewsets.auth_views.send_verification_code")` por `patch("core.services.whatsapp_service.Client")` (a classe importada no topo do módulo), retornando um `MagicMock` cujo `.messages.create(...)` devolve um objeto com `.sid`.
2. Onde o teste só precisa que "não exploda" (rate-limit, lockout), o mock do `Client` basta. Onde valida o conteúdo (não há hoje), pode-se asserir `mock_client.return_value.messages.create.assert_called_once_with(...)` para travar o contrato Twilio.
3. Garantir que `settings.TWILIO_ACCOUNT_SID` esteja setado no ambiente de teste (senão `send_whatsapp_message` levanta `RuntimeError` antes de chamar o Client). Se não estiver, adicionar override via `settings` fixture nos testes de auth — sem isso o caminho real não roda.

### 7. Fixture de invoice só em memória

`tests/unit/test_finances/conftest.py:36-45` (`invoice_pdf_bytes`) escreve `(FIXTURES_DIR / f"{fixture_name}.pdf").write_bytes(pdf_bytes)` a cada chamada — polui o working tree com `.pdf` não versionados (e o design diz que o `.pdf` real nunca deve ser versionado). Remover a linha de `write_bytes`: a função renderiza e retorna os bytes só em memória; o parser (`pdfplumber`) consome bytes/BytesIO direto, sem precisar do arquivo em disco. Ajustar o docstring (linhas 38-41) para refletir "só em memória, nada escrito em disco".

### 8. Remover testes vazios

Varrer `tests/` e `frontend/` por testes que só asseguram import ou `assert True`/`expect(true).toBe(true)`. Para cada um: se houver comportamento testável adjacente, substituir por asserção real; se for puramente redundante, remover. Não inventar cobertura — remover é preferível a um teste que mente.

### 9. Testes 403 das ações de dinheiro

`tests/integration/test_finances/test_finance_permissions.py:8-19` já cobre `pay`, `bulk_pay`, `generate_month`, `create_with_lines`, `suspend` e os POST de CRUD. Faltam as ações de fechamento e o unpay (DELETE de payment). Adicionar à lista `WRITE_ENDPOINTS`:

- `("post", "/api/finances/condo-month-closes/close/")` (action em `crud_views.py:709-710`)
- `("post", "/api/finances/condo-month-closes/reopen/")` (action em `crud_views.py:713-714`)
- `("delete", "/api/finances/payments/1/")` (destroy delega a unpay — `PaymentViewSet`, `crud_views.py:153`)

Os testes parametrizados `test_non_admin_cannot_write` (espera 403) e `test_admin_write_passes_permission` (espera ≠403) cobrem automaticamente as novas linhas. Para o DELETE, o admin pode receber 404 (id inexistente) — o assert `!= 403` continua válido. Confirmar que o método `delete` é aceito pelo `getattr(client, method)` (DRF `APIClient` tem `.delete`).

### 10. Confirmar cross-month / fevereiro do late fee (não duplicar)

`core/services/fee_calculator.py:82-99` (`calculate_late_fee`) é alvo do plano P2.1. Apenas VERIFICAR se P2.1 já adicionou os cenários cross-month e due_day=31 em fevereiro. Se sim, este plano não toca; se não, registrar no Handoff que P2.1 deve cobri-los. NÃO escrever testes que dependam da assinatura nova de `calculate_late_fee` se P2.1 ainda não a entregou (evita conflito de merge).

## Arquivos a criar / modificar

- `pytest.ini` — reescrever bloco `filterwarnings` (linhas 79-83): `error` + ignores cirúrgicos ancorados em módulos de terceiros, com comentário por linha.
- `frontend/vitest.config.mts` — remover `dangerouslyIgnoreUnhandledErrors: true` (linha 18).
- `frontend/tests/setup.ts` — `onUnhandledRequest: 'error'` no `server.listen`; corrigir handlers/cleanup que estouram.
- `frontend/tests/mocks/data/finances/*.ts` (geradores `createMock*`) — shape bruto da API (decimais string, FK aninhada read, sem `*_id` no read).
- `frontend/tests/mocks/handlers.ts` — ajustar literais de resposta para shape bruto onde divergem.
- `frontend/app/(dashboard)/finances/bills/__tests__/bills-page.test.tsx` e os demais 25 arquivos de `finances/**/__tests__/*.tsx` com `vi.mock('@/lib/api/hooks/...')` — remover mock de hook interno; migrar para MSW + `renderWithProviders`; asserir comportamento.
- `tests/factories.py` — adicionar `_generate_valid_cpf` + contador; constantes nomeadas (`CPF_VALID_PRIMARY`, etc.); `make_tenant` usa o gerador.
- `tests/integration/test_tenant_auth_api.py` — trocar `patch(...send_verification_code)` por `patch("core.services.whatsapp_service.Client")`; usar `CPF_VALID_PRIMARY` da factory; garantir `TWILIO_ACCOUNT_SID` no settings de teste.
- `tests/unit/test_finances/conftest.py` — remover `write_bytes` do `.pdf` (linha 44); ajustar docstring.
- `tests/integration/test_finances/test_finance_permissions.py` — 3 novas entradas em `WRITE_ENDPOINTS`.
- Arquivos de teste vazios identificados na varredura (backend e frontend) — remover ou substituir por asserção real.

## TDD — cenários de teste

Como este é um plano de QUALIDADE de teste, o "teste" é em parte a própria suite rodando sob regras mais estritas. Cenários concretos:

- **Backend warnings (regressão de política):** rodar `python -m pytest <escopo>` com o novo `filterwarnings = error` e confirmar 0 warnings emitidos pelo nosso código. Qualquer warning de `core.*`/`finances.*`/`tests.*` falha a suite (comportamento desejado).
- **Frontend MSW estrito:** com `onUnhandledRequest: 'error'`, um teste que dispara um request sem handler DEVE falhar. Adicionar/confirmar um caso de fumaça que prova isso (request a endpoint não mockado → erro).
- **Migração de componente (bills) — prova do bug do condominium_id:** `test_bills_page_create_sends_raw_id_payload` — renderiza `BillsPage` com MSW, preenche o form, submete, e o spy do handler POST captura o body; asserir que o body carrega o `*_id` de escrita correto (não a FK aninhada). Esse teste teria pego o bug original.
- **Migração de componente — comportamento de sucesso:** `test_bills_page_generate_month_shows_success` — clica em gerar mês, MSW responde 201, asserir toast/efeito na UI (não "mutate chamado").
- **Migração — não-admin esconde escrita:** preservar o `renders the table but hides all write buttons for non-admin users` (já existe, `bills-page.test.tsx:65`) sem o `vi.mock` do hook.
- **Factory CPF válido e único:** `test_generate_valid_cpf_passes_validator` — `_generate_valid_cpf(n)` para vários `n` passa `validate_cpf`; `test_make_tenant_cpfs_are_unique` — N tenants consecutivos têm CPFs distintos; `test_make_tenant_no_global_order_dependency` — criar tenants em ordem embaralhada não colide.
- **Twilio na fronteira:** `test_request_code_calls_twilio_client_not_internal` — com `Client` mockado, o request de código chama `messages.create` uma vez; o service interno `send_verification_code` roda de verdade (não mockado).
- **Fixture invoice em memória:** `test_invoice_fixture_writes_nothing_to_disk` — chamar `invoice_pdf_bytes(...)` e asserir que nenhum `.pdf` novo aparece em `FIXTURES_DIR` (`os.listdir` antes/depois).
- **403 ações de dinheiro:** os parametrizados de `test_finance_permissions.py` cobrem as 3 novas rotas (close/reopen/unpay) automaticamente — confirmar 403 para não-admin e ≠403 para admin.
- **Testes vazios removidos:** após a varredura, `pytest --collect-only` e a contagem de testes não devem incluir asserts triviais; nenhum teste removido era a única cobertura de um caminho (verificar coverage não cair em código de produção).

## Migrations / dados

N/A — este plano não cria/altera tabelas nem mexe em dados de produção. Apenas configuração de teste, factories e arquivos de teste. Sem backup necessário.

## Constraints (o que NÃO fazer)

- NÃO migrar neste plano os testes de componente do módulo LEGADO/admin (`apartments`, `buildings`, `furniture`, `leases`, `tenants`, `contract-template`, `financial/daily`) — só o módulo NOVO `finances/`. Os legados ficam para plano posterior.
- NÃO reescrever os ~39 arquivos que hardcodam CPF de uma vez — só trocar onde o literal é load-bearing (auth, unicidade, lookup); os demais passam a usar `make_tenant()` sem argumento.
- NÃO usar nenhuma supressão (`# noqa`, `# type: ignore`, `eslint-disable`, `@ts-ignore`) para silenciar warnings que aparecerem — corrigir a causa raiz. Os ignores de `filterwarnings` são permitidos APENAS para módulos de terceiros, ancorados por módulo.
- NÃO mockar internals (hooks, services, serializers, ORM) — mock só na fronteira HTTP (MSW), Twilio `Client`, Chrome/PDF, filesystem e tempo.
- NÃO duplicar os testes de `calculate_late_fee` cobertos por P2.1 — apenas verificar e registrar dependência.
- NÃO alterar a lógica de produção exceto quando um warning/erro recém-exposto for um bug real do nosso código (aí corrige-se a causa, com teste).
- NÃO mexer no módulo financeiro pessoal legado do core além de adicionar/ajustar mocks de teste; sem refatoração profunda.

## Critérios de aceite (binários)

- [ ] `pytest.ini` `filterwarnings` começa com `error` e contém apenas ignores ancorados em módulos de `site-packages` (zero ignores de `core.*`/`finances.*`/`tests.*`).
- [ ] `dangerouslyIgnoreUnhandledErrors` removido de `frontend/vitest.config.mts`.
- [ ] MSW roda com `onUnhandledRequest: 'error'` e a suite frontend passa.
- [ ] Nenhum arquivo em `frontend/app/(dashboard)/finances/**/__tests__/*.tsx` contém `vi.mock('@/lib/api/hooks/...')`.
- [ ] Geradores `createMock*` de finances emitem shape bruto (decimais string, FK aninhada read, sem `*_id` no read).
- [ ] `tests/factories.py` não tem mais `itertools.cycle(TEST_CPFS)`; usa gerador de CPF válido por contador + constantes nomeadas.
- [ ] `test_tenant_auth_api.py` mocka `twilio.rest.Client` (não `send_verification_code`) e usa constante de CPF da factory.
- [ ] `tests/unit/test_finances/conftest.py` não escreve `.pdf` em disco.
- [ ] `WRITE_ENDPOINTS` em `test_finance_permissions.py` inclui `condo-month-closes/close`, `condo-month-closes/reopen` e DELETE de `payments/1/`.
- [ ] Zero testes vazios (import-only / `assert True`) remanescentes.
- [ ] Gate de verificação passa escopado, sem erros e sem warnings.

## Gate de verificação

Backend (escopado nos arquivos tocados + regressão dirigida):

```bash
ruff check && ruff format --check
mypy core/ finances/
pyright
python -m pytest tests/factories.py tests/integration/test_tenant_auth_api.py \
  tests/unit/test_finances/ tests/integration/test_finances/test_finance_permissions.py -p no:randomly
# Regressão dirigida (a malha de CPF e warnings afeta a suite toda — rodar um subconjunto representativo):
python -m pytest tests/integration/ tests/unit/test_models.py tests/unit/test_serializers.py
```

Frontend:

```bash
cd frontend && npm run lint && npm run type-check && npm run test:unit
```

Zero erros E zero warnings em Ruff, mypy, Pyright, ESLint, TypeScript e pytest. A suite cheia tem flakiness pré-existente de xdist/Redis — NÃO é bloqueio; usar o escopo acima como gate canônico.

## Handoff

Commit sugerido:

```
test(quality): enforce zero-warnings, mock policy and CPF factory hardening

- pytest.ini: filterwarnings=error + surgical 3rd-party ignores (no blanket suppression)
- vitest: drop dangerouslyIgnoreUnhandledErrors; MSW onUnhandledRequest=error
- finances component tests: real QueryClientProvider + MSW (raw API shape), no internal-hook mocks
- factories: valid-CPF generator by counter + named constants (kills cross-test order flakiness)
- tenant auth tests: mock Twilio Client boundary, not internal send_verification_code
- invoice fixture: in-memory only (no .pdf written to working tree)
- finance permissions: add close/reopen/unpay 403 coverage; remove empty tests

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
```

Atualizar `MEMORY.md` (índice de projeto) com uma entrada apontando para este plano e para o fato de que (a) os testes de componente do módulo legado/admin ainda usam `vi.mock` de hooks internos (dívida remanescente para plano futuro), e (b) o ignore de `RuntimeWarning` naive-datetime no `pytest.ini` deve ser removido quando o plano de timezone aterrissar.

O próximo plano (migração dos testes de componente legados/admin para MSW) assume: a fronteira MSW já está estrita (`onUnhandledRequest: 'error'`), os mocks usam shape bruto, e a factory de CPF é determinística — basta replicar o padrão já aplicado em `finances/` para os módulos restantes.
