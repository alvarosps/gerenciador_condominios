# Plano P5.2 — Performance frontend: lazy xlsx + filtro de competência nas Contas

> **Estado:** PLANEJADO — nao executado
> **Prioridade:** FASE P5 · **Branch sugerida:** `perf/frontend-bundle` · **Depende de:** nenhum
>
> **Revisão 2026-06-12 (pós-merge de P4):** âncoras re-verificadas contra o `master` atual. P4.3 mexeu em `use-bills.ts` mas só adicionou `invalidateFinanceMoneyCaches` ABAIXO (linhas 118-126) das âncoras que este plano cita (15-23, 92-94, 99) — **zero drift** aqui. Correções aplicadas: (a) §A passo 6 — a razão de os consumidores compilarem não é "já usam `void`" (eles usam `onClick={() => crud.handleExport(...)}` puro), e sim `.eslintrc.json` `no-misused-promises` `checksVoidReturn.attributes:false`; (b) `use-crud-page.test.tsx` e o diretório `frontend/lib/hooks/__tests__/` **não existem** — são criação, não "estender"; (c) `bills-page.test.tsx` existe mas seu helper `setBillsResponse` não captura query params (precisa handler que capture); (d) mensagem de erro do CSV é "Erro ao exportar arquivo CSV"; (e) aria-labels acentuados; (f) cite de backend `crud_views.py` é 341-343, não 315-317.

## Objetivo

Reduzir o peso do bundle inicial de TODAS as paginas CRUD (incluindo mobile/PWA) tornando o `xlsx` (~300KB) um import dinamico (`await import`) dentro dos handlers de export, que ja sao chamados de forma assincrona. Em paralelo, conter o crescimento ilimitado de payload/DOM da pagina "Contas do Condominio" (`bills/page.tsx`) adicionando um seletor de competencia com default no mes corrente, passando `competence_month` (ja suportado pelo backend) e mantendo a opcao "todas as competencias". Nada de logica de negocio muda — e exclusivamente performance e UX de filtro.

## Achados endereçados

| Sev | Achado | Arquivo:linha | Correção em uma linha |
| --- | --- | --- | --- |
| MEDIO | `xlsx` importado estaticamente em `use-export.ts`; via `use-crud-page` cai no bundle de toda pagina CRUD (mobile/PWA) | `frontend/lib/hooks/use-export.ts:2` (`import * as XLSX from 'xlsx'`) | Trocar import estatico por `await import('xlsx')` dentro de `exportToExcel`/`exportToCSV` (tornar ambas `async`) |
| MEDIO→BAIXO | `BillsPage` busca TODAS as bills da historia (`page_size=10000`) sem filtro de competencia e renderiza tudo sem paginacao | `frontend/app/(dashboard)/finances/bills/page.tsx:76` (`useBills(filters)`) + `frontend/lib/api/hooks/use-bills.ts:99` (`page_size: 10000`) | Adicionar seletor de competencia (default mes corrente) que injeta `competence_month` em `BillFilters`; manter "Todas as competencias" como opcao |

## Abordagem técnica

### Parte A — lazy `xlsx` em `use-export.ts`

Hoje `frontend/lib/hooks/use-export.ts` faz `import * as XLSX from 'xlsx'` (linha 2). `exportToExcel` (linha 27) e `exportToCSV` (linha 95) sao funcoes **sincronas** que usam `XLSX.utils.*` / `XLSX.writeFile` / `XLSX.utils.sheet_to_csv`. Como `use-crud-page.ts` importa `useExport` (linha 4) e e usado por todas as paginas CRUD, o `xlsx` entra no chunk de cada rota.

Passos (na ordem):

1. **Remover** o `import * as XLSX from 'xlsx'` do topo de `use-export.ts`.
2. Tornar `exportToExcel` **`async`** (`async <T extends ...>(...) => { ... }`) e, no inicio do bloco `try`, adicionar `const XLSX = await import('xlsx');`. O restante do corpo (json_to_sheet, book_new, book_append_sheet, auto-size cols, writeFile) permanece identico, usando o `XLSX` local. Retorno continua `{ success: true, filename }`, agora dentro de uma `Promise`.
3. Tornar `exportToCSV` **`async`** da mesma forma: `const XLSX = await import('xlsx');` no inicio do `try`, mantendo json_to_sheet/sheet_to_csv e a logica de Blob/download intactas.
4. `setIsExporting(true)` permanece antes do `try`; o `finally { setIsExporting(false); }` continua valido (roda apos o `await`). O `catch` mantem `handleError(...)` + `throw new Error('Erro ao exportar arquivo' | '... CSV')`.
5. **Atualizar o consumidor** `use-crud-page.ts`. O `handleExport` (linha 244) hoje e `useCallback((format, data) => { ... exportToExcel(...) ... })` sincrono e usa `try/catch`. Como `exportToExcel`/`exportToCSV` passam a retornar `Promise`, tornar o callback **`async`** e dar `await` nas chamadas para que o `try/catch` continue capturando a rejeicao (sem `await`, a Promise rejeitada escaparia do `try`). Os `toast.success(...)` so disparam apos o `await` resolver. Assinatura no `UseCrudPageReturn` (linha 98) passa de `handleExport: (format, data) => void` para `handleExport: (format, data) => Promise<void>` — atualizar o tipo da interface.
6. **Consumidores de `handleExport` — nenhuma edição necessária.** Os 10 call sites sao todos `onClick={() => crud.handleExport('excel'|'csv', <data> ?? [])}` **sem** `void` — em `buildings/page.tsx:135,139`, `apartments/page.tsx:250,254`, `leases/page.tsx:300,304`, `furniture/page.tsx:130,134`, `tenants/page.tsx:379,383`. Depois da mudança o arrow passa a retornar uma `Promise`, mas **compila limpo** porque `.eslintrc.json:31-34` define `@typescript-eslint/no-misused-promises` com `checksVoidReturn: { attributes: false }` — uma função que retorna Promise passada a um atributo JSX (`onClick`) NAO é sinalizada. **NAO adicionar `void`** (desnecessário; o arrow já descarta o resultado). A razão antiga ("já usam `void`") está errada — eles nunca usaram `void`; a garantia é a config do eslint. Nenhum chamador encadeia `.then`/depende do retorno síncrono.

> Observacao DRY: o bloco `await import('xlsx')` aparece em duas funcoes irmas; **nao** extrair um wrapper so para isso (YAGNI) — duas linhas identicas e mais simples que um helper que so reexpoe o modulo. Manter inline.

### Parte B — seletor de competencia em `bills/page.tsx`

Backend ja filtra: `finances/viewsets/crud_views.py:341-343` (dentro de `_apply_filters`: `competence_month = params.get("competence_month")` / `if competence_month is not None:` / `queryset = queryset.filter(competence_month=competence_month)`) aplica **match exato** de data (1o dia do mes, formato ISO `YYYY-MM-01`). `BillFilters` (em `use-bills.ts:15-23`, `competence_month?: string` na 18) ja declara o campo. `useBills` ja remove chaves `undefined` antes de mandar como query param (linhas 92-94). Logo, **nenhuma** mudanca de backend/hook e necessaria — so a UI.

Estado atual do `BillsPage` (`bills/page.tsx`):
- linha 62-63: `const now = new Date();` + `const [period] = useState({ year: now.getFullYear(), month: now.getMonth() + 1 });` (period e so-leitura, usado em `handleGenerateMonth`).
- linha 72-74: `filters` so injeta `lifecycle_state`.
- linha 76: `const { data: bills, isLoading } = useBills(filters);`.

Passos (na ordem):

1. Reusar o padrao ja consolidado em `finances/distribution/page.tsx` (chevrons + `formatMonthYear` + `shiftMonth`). Trocar `const [period] = useState(...)` por `const [period, setPeriod] = useState({ year: now.getFullYear(), month: now.getMonth() + 1 });` (agora mutavel).
2. Adicionar estado de modo de competencia: `const [competenceMode, setCompetenceMode] = useState<'month' | 'all'>('month');` — default `'month'` (mes corrente). Quando `'all'`, nao envia `competence_month` (mantem "todas as competencias").
3. Calcular o valor ISO do filtro: derivar `const competenceMonthParam = competenceMode === 'all' ? undefined : \`${period.year}-${String(period.month).padStart(2, '0')}-01\`;`. Esse string casa com o `DateField` do backend (match exato no 1o dia do mes).
4. Injetar no `filters` (linha 72): adicionar `...(competenceMonthParam ? { competence_month: competenceMonthParam } : {})`. Como `useBills` ja limpa `undefined`, o objeto fica limpo.
5. UI do seletor: na barra de filtros existente (`div` da linha 193 — `<div className="mb-4 flex flex-wrap items-center gap-3">`, hoje so com o Select de `lifecycleFilter` em 194-206), adicionar, ANTES do Select de situacao, um grupo com:
   - Botao chevron "Mês anterior" (`ChevronLeft`, `aria-label="Mês anterior"`) chamando `shiftMonth(-1)`. **Manter os acentos** nos `aria-label` ("Mês anterior"/"Próximo mês") para casar com `distribution/page.tsx` e com seletores de teste sensíveis a acento.
   - Label central `formatMonthYear(period.year, period.month)` (`min-w-[10rem] text-center`), com `aria-hidden` quando em modo `'all'` ou desabilitado visualmente.
   - Botao chevron "Próximo mês" (`ChevronRight`, `aria-label="Próximo mês"`) chamando `shiftMonth(1)`.
   - Um `Select` (Shadcn, ja importado em 24-30) "competencia" com duas opcoes: `<SelectItem value="month">Mês selecionado</SelectItem>` e `<SelectItem value="all">Todas as competências</SelectItem>`, `value={competenceMode}` / `onValueChange={(v) => setCompetenceMode(v as 'month' | 'all')}`. Quando `'all'`, desabilitar os chevrons (`disabled`) e a label fica esmaecida (`text-muted-foreground`) — KISS, sem esconder.
6. Implementar `shiftMonth` identico ao da distribution page: `function shiftMonth(delta: number) { const base = new Date(period.year, period.month - 1 + delta, 1); setPeriod({ year: base.getFullYear(), month: base.getMonth() + 1 }); }`. Isso trata virada de ano corretamente.
7. Imports a adicionar em `bills/page.tsx`: `ChevronLeft, ChevronRight` de `lucide-react` (ja importa `CalendarPlus, FileUp, Plus`); `formatMonthYear` de `@/lib/utils/formatters`.
8. `handleGenerateMonth` (linha 120) continua usando `period.year`/`period.month` — agora o botao "Gerar contas do mes" passa a gerar para o mes **selecionado** no seletor (comportamento mais coerente, ja que period virou navegavel). Sem mudanca de codigo no handler, apenas o efeito de period ser mutavel. Confirmar no teste.
9. O agrupamento por predio (`groups`, linha 82-97) e a renderizacao em accordion permanecem — agora operam sobre o subconjunto filtrado por competencia, reduzindo DOM. Sem mudanca de logica de agrupamento.

> Nota: NAO mexer no `page_size: 10000` do `use-bills.ts` (preferencia conhecida do projeto: page_size grande e intencional). O ganho de payload vem do filtro de competencia reduzir o conjunto retornado, nao da paginacao.

## Arquivos a criar / modificar

- `frontend/lib/hooks/use-export.ts` — remover import estatico de `xlsx`; `exportToExcel` e `exportToCSV` viram `async` com `const XLSX = await import('xlsx')` no inicio do `try`.
- `frontend/lib/hooks/use-crud-page.ts` — `handleExport` vira `async` com `await` nas chamadas de export; tipo no `UseCrudPageReturn` muda para `handleExport: (format: 'excel' | 'csv', data: T[]) => Promise<void>`.
- `frontend/app/(dashboard)/finances/bills/page.tsx` — `period` mutavel + estado `competenceMode` + `shiftMonth` + `competenceMonthParam` no `filters`; seletor de competencia (chevrons + label + Select) na barra de filtros; imports `ChevronLeft/ChevronRight` e `formatMonthYear`.
- `frontend/lib/hooks/__tests__/use-export.test.ts` — **CRIAR** (confirmado inexistente). O proprio diretorio `frontend/lib/hooks/__tests__/` **nao existe ainda** — criar o diretorio junto com o arquivo. Testes para `useExport` cobrindo o caminho async + lazy import.
- `frontend/lib/hooks/__tests__/use-crud-page.test.tsx` — **CRIAR** (confirmado inexistente; a redacao antiga "estender o __tests__ existente" estava ERRADA — nao ha arquivo nem diretorio). Mockar `useExport` na fronteira do hook (unico mock sancionado aqui, ja que o export real dispara xlsx/DOM). Cobrir os 4 cenarios de `handleExport` abaixo.
- `frontend/lib/api/hooks/__tests__/use-bills.test.tsx` — estender (EXISTE): garantir que `useBills({ competence_month })` repassa o param (ja existe um teste "forwards filters as query params" na linha 74-97 cobrindo `competence_month: '2026-06-01'`; manter e usar como ancora de regressao).
- `frontend/app/(dashboard)/finances/bills/__tests__/bills-page.test.tsx` — estender (EXISTE, 187 linhas): default envia `competence_month` do mes corrente; alternar para "Todas as competencias" remove o param; chevrons navegam o mes e o param muda. **Atenção:** o helper `setBillsResponse` (linhas 30-34) NAO captura query params — para assertar `competence_month` adicionar um handler `http.get` que capture os searchParams (espelhar `use-bills.test.tsx:76-86`); reusar o helper `mockGenerate` (linhas 43-53) para o caso "gerar usa o mes selecionado". Manter o sibling `bills-page-import.test.tsx` verde.

## TDD — cenários de teste

### `use-export.test.ts` (vitest)
- `exportToExcel resolve uma Promise e dispara o download` — chamar `await exportToExcel(data, columns)` e afirmar `{ success: true, filename }` com sufixo `.xlsx`; mock de `XLSX.writeFile` na fronteira (spy sobre o modulo `xlsx` dinamico) para nao escrever arquivo real no jsdom.
- `exportToCSV resolve uma Promise e cria um Blob CSV` — `await exportToCSV(...)`; afirmar retorno `.csv` e que `document.createElement('a').click()` foi chamado (spy em `URL.createObjectURL` / `link.click`).
- `isExporting volta a false apos resolver (finally)` — apos `await`, `isExporting === false`.
- `propaga erro como "Erro ao exportar arquivo" quando o xlsx falha` (edge, Excel) — forcar rejeicao no caminho de geracao e afirmar `rejects.toThrow('Erro ao exportar arquivo')`. **Nota:** o caminho CSV lanca a mensagem ESPECIFICA `'Erro ao exportar arquivo CSV'` (use-export.ts:142-144) — o teste do CSV deve assertar essa string, nao a generica.
- **Regressao (lazy import):** `o modulo xlsx nao e avaliado ate o handler ser chamado` — afirmar que apenas apos `await exportToExcel(...)` o `import('xlsx')` resolve (ou, alternativa pragmatica em jsdom: que `exportToExcel` e uma funcao `async` cujo `.constructor.name === 'AsyncFunction'`, provando que o caminho assincrono existe). A prova canonica de "xlsx fora do chunk inicial" e o `next build` (ver gate).

### `use-crud-page` (CRIAR `lib/hooks/__tests__/use-crud-page.test.tsx` — diretorio e arquivo novos)
- `handleExport excel chama exportToExcel e mostra toast de sucesso apos await` — mockar `useExport` (fronteira do hook) com `exportToExcel` retornando Promise resolvida; afirmar `toast.success('Arquivo Excel exportado com sucesso!')` apos `await`.
- `handleExport csv com erro mostra toast de erro` (edge) — `exportToCSV` rejeita; afirmar `toast.error('Erro ao exportar arquivo')` — a mensagem do toast no `catch` de `use-crud-page.ts:269-272` é a generica, independente do path (prova que o `await` mantem o erro dentro do `try/catch`).
- `handleExport avisa quando nao ha dados` (edge) — passar `data: []` (o guard usa `data?.length === 0`, não `!data?.length`) ⇒ `toast.warning('Não há dados para exportar')`, sem chamar export.
- `handleExport avisa quando export nao configurado` (edge) — sem `exportColumns`/`exportFilename` ⇒ `toast.warning('Exportação não configurada')`.

### `use-bills.test.tsx` (vitest + MSW)
- **(ja existe — regressao)** `forwards filters as query params` cobre `competence_month: '2026-06-01'`; manter passando apos as mudancas.

### `bills-page.test.tsx` (vitest + MSW + userEvent)

> Para capturar `competence_month` é preciso um handler `http.get` que leia `new URL(request.url).searchParams` (espelhar `use-bills.test.tsx:76-86`); o helper `setBillsResponse` (30-34) ignora query params. As queries de chevron usam `getByRole('button', { name: 'Mês anterior' | 'Próximo mês' })` (aria-labels acentuados).

- `por padrao busca a competencia do mes corrente` (regressao do bug) — capturar o query param da requisicao GET `/finances/bills/` e afirmar `competence_month === <YYYY>-<MM>-01` do mes atual (derivar do `new Date()` no teste com `vi.setSystemTime` para determinismo).
- `alternar para "Todas as competências" remove o filtro de competencia` — selecionar a opcao "Todas as competências"; afirmar que a nova requisicao GET nao contem `competence_month`.
- `chevron "Mês anterior" muda o competence_month para o mes anterior` — clicar `ChevronLeft` (aria-label "Mês anterior"); afirmar param vira o mes anterior (testar virada de ano com `vi.setSystemTime(new Date('2026-01-15'))` ⇒ `2025-12-01`).
- `chevron "Próximo mês" avanca o competence_month` — clicar `ChevronRight` (aria-label "Próximo mês"); afirmar param do proximo mes.
- `chevrons ficam desabilitados em modo "Todas as competências"` (edge) — selecionar "all"; afirmar `ChevronLeft`/`ChevronRight` `disabled`.
- `"Gerar contas do mês" usa o mes selecionado` — navegar com chevron e clicar "Gerar contas do mês"; afirmar que `useGenerateMonthBills().mutate` recebeu o `{ year, month }` navegado (reusar o helper `mockGenerate` ja existente, linhas 43-53).
- **(manter)** os testes existentes de agrupamento/lifecycle/empty-state continuam verdes (a resposta MSW e mockada, independente do param).

## Migrations / dados

N/A — mudanca exclusivamente frontend; nenhuma model, migration, RLS ou correcao de dado vivo. Backend ja suporta o filtro `competence_month`.

## Constraints (o que NÃO fazer)

- NAO alterar `page_size: 10000` em `use-bills.ts` — page_size grande e intencional no projeto.
- NAO refatorar o modulo financeiro pessoal legado (`app/(dashboard)/financial/`, sidebar "Financas") — este plano so toca o modulo NOVO `finances/` e os hooks compartilhados de export/CRUD.
- NAO introduzir bundle-analyzer/webpack config novo no `next.config` so para "provar" o ganho — a prova e o `next build` e o teste async; YAGNI.
- NAO extrair helper/wrapper para o `await import('xlsx')` (duas linhas irmas, KISS/DRY balanceado — wrapper so reexportaria o modulo).
- NAO esconder a label de competencia quando em modo "all" — apenas esmaecer/desabilitar (KISS, descoberta visivel).
- NAO usar `# noqa`, `eslint-disable`, `@ts-ignore`, `// @ts-expect-error`, nem `from __future__` (irrelevante aqui). Tipar `handleExport` como `Promise<void>` de verdade.
- NAO converter `competence_month` via `new Date(iso)` na UI (timezone-unsafe) — construir o ISO por `padStart` a partir de `period.year`/`period.month`, e usar `formatMonthYear(year, month)` para o label (padrao ja usado).
- Mensagens de UI em PT-BR; mensagens de log/dev em EN (manter `handleError` como esta).

## Critérios de aceite (binários)

- [ ] `use-export.ts` nao tem mais `import ... 'xlsx'` no topo; `exportToExcel` e `exportToCSV` sao `async` e usam `await import('xlsx')`.
- [ ] `handleExport` em `use-crud-page.ts` e `async`, da `await` nos exports, e o tipo no `UseCrudPageReturn` e `(format, data) => Promise<void>`.
- [ ] Todos os consumidores de `handleExport` compilam sem warning de Promise nao tratada (lint limpo).
- [ ] `next build` conclui sem erro; o chunk inicial das rotas CRUD nao referencia `xlsx` estaticamente (xlsx aparece como chunk dinamico/lazy). Verificavel pela saida do build (chunk separado para `xlsx`).
- [ ] `BillsPage` por padrao requisita `competence_month` do mes corrente (`YYYY-MM-01`).
- [ ] Opcao "Todas as competencias" remove o param `competence_month` da requisicao.
- [ ] Chevrons navegam mes a mes (incl. virada de ano) e atualizam o param; ficam desabilitados em modo "all".
- [ ] "Gerar contas do mes" usa o mes selecionado no seletor.
- [ ] Todos os testes novos + regressao (`use-bills` "forwards filters", `bills-page` existentes) verdes.
- [ ] `npm run lint && npm run type-check && npm run test:unit` sem erros E sem warnings.

## Gate de verificação

Frontend (escopado + regressao dirigida):

```bash
cd frontend
npm run test:unit -- lib/hooks/__tests__/use-export.test.ts \
  lib/hooks/__tests__/use-crud-page.test.tsx \
  lib/api/hooks/__tests__/use-bills.test.tsx \
  "app/(dashboard)/finances/bills/__tests__/bills-page.test.tsx"
npm run lint
npm run type-check
npm run build   # confirma que xlsx vira chunk dinamico e o build passa
```

Gate completo antes de fechar:

```bash
cd frontend && npm run lint && npm run type-check && npm run test:unit
```

Zero erros E zero warnings (ESLint, TypeScript, Vitest). Backend nao e tocado — nao ha gate Python neste plano.

## Handoff

Commit sugerido:

```
perf(frontend): lazy-load xlsx + competence filter on bills page

- use-export: exportToExcel/exportToCSV agora async com await import('xlsx');
  remove xlsx do bundle inicial de todas as paginas CRUD (mobile/PWA)
- use-crud-page: handleExport async (Promise<void>) com await nos exports
- bills/page: seletor de competencia (chevrons + Select) com default no mes
  corrente injetando competence_month; opcao "Todas as competencias" mantida

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
```

- Atualizar `MEMORY.md` (projeto) com nota curta: "P5.2 frontend perf — xlsx lazy + filtro competencia em bills/ — branch perf/frontend-bundle".
- Proximo plano pode assumir: o padrao de competencia (chevrons + Select "month/all") esta consolidado em `bills/page.tsx` e pode ser reusado em outras telas do modulo `finances/` que listam por competencia; o lazy import de `xlsx` ja vale para TODA pagina que usa `useCrudPage`/`useExport`.
