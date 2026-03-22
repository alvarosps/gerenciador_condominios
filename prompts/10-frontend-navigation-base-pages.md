# Sessão 10 — Frontend: Navegação + Páginas Base (Persons, Categories, Settings)

## Contexto

Leia estes arquivos:
- `@docs/plans/2026-03-21-financial-module-design.md` — Seção 7.2 (Navegação) e 7.3 parcial
- `@prompts/SESSION_STATE.md` — Estado atual
- `@prompts/00-prompt-standard.md` — Referência de exemplares

Leia estes exemplares:
- `@frontend/components/layouts/sidebar.tsx` — Sidebar com ROUTES constant
- `@frontend/lib/utils/constants.ts` — ROUTES e outras constantes
- `@frontend/app/(dashboard)/buildings/page.tsx` — Página CRUD canônica
- `@frontend/lib/hooks/use-crud-page.ts` — Hook useCrudPage
- `@frontend/components/tables/data-table.tsx` — DataTable component

Leia os hooks criados na sessão 09:
- `@frontend/lib/api/hooks/use-persons.ts`
- `@frontend/lib/api/hooks/use-expense-categories.ts`

---

## Escopo

### Arquivos a CRIAR
- `frontend/app/(dashboard)/financial/page.tsx` — Redirect para dashboard (placeholder)
- `frontend/app/(dashboard)/financial/persons/page.tsx` — CRUD Pessoas
- `frontend/app/(dashboard)/financial/persons/_components/person-form-modal.tsx`
- `frontend/app/(dashboard)/financial/persons/_components/credit-card-section.tsx` — Seção de cartões dentro do form
- `frontend/app/(dashboard)/financial/categories/page.tsx` — CRUD Categorias
- `frontend/app/(dashboard)/financial/categories/_components/category-form-modal.tsx`
- `frontend/app/(dashboard)/financial/settings/page.tsx` — Configurações financeiras

### Arquivos a MODIFICAR
- `frontend/lib/utils/constants.ts` — Adicionar rotas financeiras ao ROUTES
- `frontend/components/layouts/sidebar.tsx` — Adicionar seção "Financeiro" com sub-menu expansível

---

## Especificação

### Navegação

Adicionar ao ROUTES em `constants.ts`:
```typescript
// Financeiro (sub-menu)
{ label: 'Financeiro', path: '/financial', icon: 'DollarSign', children: [
  { label: 'Dashboard', path: '/financial' },
  { label: 'Despesas', path: '/financial/expenses' },
  { label: 'Receitas', path: '/financial/incomes' },
  { label: 'Pgto. Aluguel', path: '/financial/rent-payments' },
  { label: 'Pessoas', path: '/financial/persons' },
  { label: 'Funcionários', path: '/financial/employees' },
  { label: 'Categorias', path: '/financial/categories' },
  { label: 'Simulador', path: '/financial/simulator' },
  { label: 'Configurações', path: '/financial/settings' },
]}
```

Atualizar `sidebar.tsx` para suportar sub-menu expansível:
- Item com `children` mostra ícone de seta (chevron)
- Ao clicar, expande sub-itens com indentação
- Sub-itens com padding-left extra
- Seção ativa se qualquer sub-item está ativo
- Manter padrão visual existente

### Página de Pessoas (CRUD)

Seguir exatamente o padrão de `buildings/page.tsx`:
1. `usePersons()` para dados
2. `useDeletePerson()` para mutation
3. `useCrudPage<Person>()` para estado
4. Colunas: Nome, Relação, Telefone, Email, Proprietário (badge sim/não), Funcionário (badge sim/não), Cartões (count), Ações
5. `PersonFormModal` com campos: name, relationship (select: Filho, Genro, Funcionária, Outro), phone, email, is_owner (switch), is_employee (switch), notes
6. **Seção de Cartões** dentro do form de edição (NÃO no create):
   - Lista cartões existentes da pessoa
   - Botão "Adicionar Cartão" abre campos inline: nickname, last_four_digits, closing_day, due_day
   - Botão "Remover" por cartão
   - Usa `useCreateCreditCard()`, `useDeleteCreditCard()` diretamente

### Página de Categorias (CRUD simples)

Página mínima seguindo padrão:
1. `useExpenseCategories()` para dados
2. `useDeleteExpenseCategory()` para mutation
3. Colunas: Nome, Descrição, Cor (preview), Ações
4. `CategoryFormModal` com campos: name, description, color (input type="color")

### Página de Configurações Financeiras

Página simples (NÃO CRUD — singleton):
1. `useFinancialSettings()` — hook GET do singleton (criar se necessário)
2. Formulário com: initial_balance (input monetário), initial_balance_date (date picker), notes
3. Botão "Salvar" chama `useUpdateFinancialSettings()`
4. Sem tabela, sem delete — é um formulário único

---

## TDD

### Passo 1: Verificar type-check e build

Como são componentes React, o TDD aqui é:
1. Implementar os componentes
2. Rodar `npm run type-check` para garantir tipos corretos
3. Rodar `npm run build` para garantir que compila

### Passo 2: Implementar na ordem
1. Constants + Sidebar (navegação funciona)
2. Página de Categorias (mais simples)
3. Página de Configurações (singleton)
4. Página de Pessoas (mais complexa, com cartões)

### Passo 3: Verificar
```bash
cd frontend && npm run type-check && npm run build
```

---

## Constraints

- NÃO implemente o Dashboard Financeiro nesta sessão (a `/financial` page é apenas um redirect ou placeholder)
- NÃO implemente as páginas de Despesas, Receitas, Pagamentos ou Simulador
- NÃO modifique componentes existentes (DataTable, ConfirmDialog, etc.) — reutilize-os
- Siga EXATAMENTE o padrão de layout de `buildings/page.tsx`: header com título + botão, tabela, modal, dialogs
- Use React Hook Form + Zod para validação dos formulários (verificar se é o padrão usado nas modais existentes)
- Import `DollarSign` e `ChevronDown`/`ChevronRight` de `lucide-react` para ícones

---

## Critérios de Aceite

- [ ] Sidebar mostra "Financeiro" com sub-menu expansível
- [ ] Navegação para todas as rotas financeiras funciona (mesmo que algumas mostrem placeholder)
- [ ] Página de Pessoas: CRUD completo com tabela, modal, delete dialog
- [ ] Seção de Cartões: adicionar/remover cartões na edição de pessoa
- [ ] Página de Categorias: CRUD completo com preview de cor
- [ ] Página de Configurações: formulário singleton funciona
- [ ] `npm run type-check` passando
- [ ] `npm run build` passando sem erros

---

## Handoff

1. Rodar `npm run type-check && npm run build`
2. Atualizar `prompts/SESSION_STATE.md`
3. Commitar: `feat(financial): add sidebar navigation, Persons, Categories, and Settings pages`
