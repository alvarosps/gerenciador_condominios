# Guia de Desenvolvimento

## Setup Local

### Pré-requisitos
- Python 3.12+ (com `uv` ou `pip`)
- Node.js 18+ (com `fnm` ou `nvm`)
- PostgreSQL 15+
- Chrome/Chromium (para geração de PDFs)
- Redis (para cache — opcional em dev)

### Backend
```bash
# Instalar dependências
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Configurar banco
cp .env.example .env  # Ajustar credenciais
python manage.py migrate
python manage.py createsuperuser

# Rodar servidor
python manage.py runserver  # http://localhost:8008
```

### Frontend
```bash
cd frontend
npm install
npm run dev  # http://localhost:4000
```

## Rodando Testes

```bash
# Backend — todos os testes (paralelo, reusa DB)
python -m pytest

# Backend — só unit tests
python -m pytest tests/unit/

# Backend — com coverage
python -m pytest --cov=core --cov-report=html
# Relatório em htmlcov/index.html

# Frontend
cd frontend && npm run test:unit

# Lint completo
pre-commit run --all-files                    # Backend
cd frontend && npm run lint && npm run type-check  # Frontend
```

## Debugging

1. **Backend:** Django debug toolbar disponível em dev (`django-debug-toolbar`)
2. **API:** Testar endpoints com `httpie` ou Swagger em `/api/docs/` (drf-spectacular)
3. **Frontend:** React DevTools + TanStack Query DevTools
4. **Logs:** Middleware registra requests lentos (>1s) automaticamente

## Criando uma Nova Feature

Use o skill `/new-feature` no Claude Code ou siga o workflow em `.claude/skills/new-feature/SKILL.md`.

Resumo:
1. Branch: `git checkout -b feat/<nome>`
2. Backend: Model → Migration → Serializer → Service → View → URL → Tests
3. Frontend: Schema (Zod) → Hook (TanStack Query) → Page → Components → Tests
4. Verificar: `python -m pytest && cd frontend && npm run lint && npm run type-check`
5. Commit: `feat(scope): descrição`

## Usando Claude Code Neste Projeto

### Agentes disponíveis (`.claude/agents/`)
- **implementer**: Para implementar features seguindo os padrões
- **reviewer**: Para code review antes de commits/PRs (read-only: sem Write/Edit)
- **tester**: Para criar/corrigir testes
- Modelo: `inherit` (usam o modelo da sessão atual)

### Skills disponíveis (`.claude/skills/`)
- `/new-feature`, `/admin`, `/financial`, `/audit`, `/brainstorming`, `/prompt-writing`, `/prompt-session`
- Debugging e refactoring usam os skills do plugin Superpowers (`superpowers:systematic-debugging`, fluxo de refactor + TDD)
- Workflows multi-agente (`.claude/workflows/`): `/review-diff`, `/coverage-sweep`

### Hooks ativos (`.claude/hooks/` via settings.json)
- **SessionStart:** lembretes de data-safety (backup antes de migrate destrutivo, soft-delete, cache)
- **Scope guard (PreToolUse Edit/Write):** bloqueia edição de node_modules/build, lockfiles e migrations já versionadas
- **Conventional commits (PreToolUse Bash):** valida `git commit -m` (script Node)
- **DB-safety guard (PreToolUse Bash):** bloqueia flush/reset_db/dbshell/migrate-zero e SQL destrutivo
- Lint/format NÃO roda em hook do Claude — roda no pre-commit (husky + lint-staged: Ruff/ESLint)

### MCP Servers (`.mcp.json`)
- **github:** servidor remoto oficial (`https://api.githubcopilot.com/mcp/`, OAuth via `/mcp`) — issues, PRs, code search
- Context7 (docs de libraries) está disponível como plugin global, não configurado no projeto
