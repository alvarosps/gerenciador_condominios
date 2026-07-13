# Modo Demo

Dataset de demonstração exaustivo — 3 prédios, 34 kitnets, 30 inquilinos, 30 locações,
18 meses de histórico de aluguel (jan/2025–jun/2026) e o módulo financeiro condominial
completo (água/luz/internet, IPTU parcelado, folha do zelador, reserva). Fonte:
`scripts/data/demo_seed_data.json`. Comando: `core/management/commands/seed_demo.py`.

## ⚠️ Aviso de segurança (leia antes de rodar)

O banco local default (`condominio`, configurado via `.env`) **espelha produção com dados
reais**. `seed_demo` tem uma guarda que **recusa rodar** a menos que:

1. o nome do banco configurado (`DB_NAME`) contenha `"demo"` ou comece com `"test_"`, **e**
2. `DEBUG=True`.

Não existe flag de bypass. Se você não seguir o setup abaixo (banco dedicado `condominio_demo`),
o comando aborta imediatamente com `CommandError`, antes de qualquer escrita.

## Setup passo a passo (Windows / PowerShell)

### 1. Criar o banco de demo (nunca o banco real)

```powershell
$env:PGPASSWORD = "<senha do .env>"
createdb -h localhost -p 5433 -U postgres condominio_demo
```

### 2. Apontar o Django para o banco de demo

Rode os comandos seguintes com `DB_NAME=condominio_demo` no ambiente (não edite o `.env`
principal — isso evitaria trocar de banco por engano depois). Em PowerShell, por sessão:

```powershell
$env:DB_NAME = "condominio_demo"
$env:DEBUG = "True"
```

Ou prefixe cada comando (bash/git bash):

```bash
DB_NAME=condominio_demo DEBUG=True python manage.py <comando>
```

### 3. Migrar o schema

```powershell
python manage.py migrate
```

### 4. Popular o dataset de demo

```powershell
python manage.py seed_demo --reset --verify
```

- `--reset`: limpa todas as tabelas de domínio (hard delete, ordem FK-safe) e repovoa do zero.
  Sem `--reset`, o comando aborta se já existir qualquer dado (`Building`/`Tenant`) — idempotência
  segura por padrão.
- `--verify`: roda a bateria de checks de invariante (contagens vs. o JSON, CPFs válidos,
  continuidade de caixa entre meses fechados, login das 3 personas-inquilino) e imprime
  PASS/FAIL por item ao final.
- `--file <path>`: aponta para um JSON alternativo (default: `scripts/data/demo_seed_data.json`).

Saída esperada: inventário de contagens por entidade criada, seguido (com `--verify`) da lista
de checks — todos devem ser `PASS`.

## Credenciais das personas (senha única: `Demo@2026`)

| Usuário | Papel | Perfil |
| --- | --- | --- |
| `gestor.demo` | Admin (staff + superuser) | Gestor do condomínio — acesso total ao dashboard |
| `inquilino.pontual` | Inquilino (Tenant) | Juliana Ribeiro Correia — sempre paga em dia |
| `inquilino.atrasado` | Inquilino (Tenant) | Rodrigo Costa Dias — atraso crônico (5–15 dias) |
| `inquilino.onboarding` | Inquilino (Tenant) | Sem locação vinculada — fluxo de primeiro acesso |

Todos os e-mails terminam em `@demo.local`. Login via `/api/auth/token/` (username + senha) ou
pela tela de login do frontend.

## Roteiro de demonstração (ordem que melhor conta a história do produto)

1. **Login como `gestor.demo`** → Dashboard: os 5 KPIs (Caixa/Reserva/Resultado/Atrasados/Saldo),
   o **Controle de Aluguéis do Mês** (calendário colorido: pago/a vencer/em atraso/não-cobrável,
   12 atrasados com multa calculada) e o **Calendário do Condomínio** (entradas de aluguel ×
   contas a pagar, IPTU parcelado visível). História: "visão do mês em 10 segundos".
2. **Locações** → 28 contratos agrupados por prédio; abrir uma locação: ações rápidas (Editar,
   Gerar Contrato) + kebab (multa, vencimento, reajuste, histórico). Mostrar o caso **prepago**
   e o **salary-offset** (zelador) — cobrança automática correta via SSOT.
3. **Reajustes** → alertas IPCA com 23 elegíveis (índice real do IBGE no seed); aplicar um
   reajuste e mostrar o valor novo arredondado a R$5.
4. **Condomínio → Contas** → água DMAE/luz CEEE com sazonalidade de inverno, IPTU 2026 em 10×,
   folha do zelador; **Fechamento** → 17 meses fechados com continuidade de caixa provada;
   **Reserva** → depósitos/saques.
5. **Financeiro (legado)** → Controle Diário com timeline (skeleton/empty/error novos).
6. **Sair → login `inquilino.pontual`** → portal mobile-first: aluguel/vencimento, histórico de
   pagamentos, contrato, comprovante PIX (enviar um → aparece "pendente").
7. **Login `inquilino.atrasado`** → mesmo portal com atraso e multa visíveis.
8. **Login `inquilino.onboarding`** → empty state "Nenhuma locação ativa" (borda coberta).
9. De volta ao gestor: **comprovantes pendentes** (2 no seed) — aprovar registra o pagamento
   automaticamente (fluxo ponta a ponta da Fase 2; a tela web de moderação é a feature P1
   aprovada na Fase 4).

## Resetar o dataset

Rode `seed_demo --reset` novamente a qualquer momento — limpa tudo (hard delete, ordem segura
para as FKs `PROTECT`) e repopula do zero. Idempotente: pode ser repetido quantas vezes for
necessário sem acumular duplicatas ou deixar o banco em estado inconsistente.

```powershell
python manage.py seed_demo --reset --verify
```

## Como voltar ao banco real

Simplesmente pare de sobrescrever `DB_NAME`/`DEBUG` no ambiente (ou feche a sessão de terminal
onde eles foram exportados) — sem essas variáveis, o Django volta a usar o `.env` principal
(`DB_NAME=condominio`, o banco de produção espelhado). **Nunca** rode `seed_demo` nessa
configuração — a guarda descrita acima impede isso automaticamente, mas não dependa só dela:
confirme sempre qual banco está ativo (`echo $env:DB_NAME` / `echo $DB_NAME`) antes de rodar
qualquer comando de escrita.

## O que o comando NÃO faz

- Não gera arquivos de comprovante reais — `PaymentProof.file` recebe um PNG mínimo gerado em
  memória (`ContentFile`), não um upload real.
- Não roda migrations — rode `python manage.py migrate` primeiro.
- Não popula o módulo financeiro legado (`core.Person`/`core.Expense`/...) — o dataset cobre
  apenas o módulo condominial (`finances` app) e o núcleo de locação (`core`).
