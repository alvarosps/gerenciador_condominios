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

### Docker (alternativa)
```bash
docker-compose up -d  # Dev: PostgreSQL + Django + Frontend
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

Use o skill `/new-feature` no Claude Code ou siga o workflow em `.claude/skills/new-feature.md`.

Resumo:
1. Branch: `git checkout -b feat/<nome>`
2. Backend: Model → Migration → Serializer → Service → View → URL → Tests
3. Frontend: Schema (Zod) → Hook (TanStack Query) → Page → Components → Tests
4. Verificar: `python -m pytest && cd frontend && npm run lint && npm run type-check`
5. Commit: `feat(scope): descrição`

## Usando Claude Code Neste Projeto

### Agentes disponíveis
- **implementer** (sonnet): Para implementar features seguindo os padrões
- **reviewer** (opus): Para code review antes de commits/PRs
- **tester** (sonnet): Para criar/corrigir testes

### Skills disponíveis
- `/new-feature`: Workflow completo de nova feature
- `/debug`: Debugging sistemático
- `/refactor`: Refactoring seguro com testes como rede de segurança

### Hooks ativos
- **Auto-lint:** Black/isort (Python) e ESLint (TypeScript) rodam automaticamente após edições
- **Conventional commits:** Commits são validados automaticamente
- **Scope guard:** Edições em node_modules, migrations existentes, e lockfiles são bloqueadas

### MCP Servers
- **context7:** Documentação atualizada de libraries (adicione "use context7" ao prompt)
- **github:** Integração com issues e PRs
- **sequential-thinking:** Raciocínio estruturado para decisões complexas
