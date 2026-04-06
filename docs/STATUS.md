# Status do Projeto

**Última atualização:** 2026-03-21

## Estado Atual

- **Backend:** 100% completo (Django REST Framework)
- **Frontend:** 100% completo (Next.js 14 + React 18)
- **Testes:** 600+ testes (523 backend + 93 frontend), 83.86% coverage backend
- **Infraestrutura:** Docker, CI/CD (GitHub Actions), pre-commit hooks

## Em Progresso

- **Módulo Financeiro:** Planejamento concluído, implementação pendente (15 sessões planejadas)
  - Plano detalhado em `prompts/` e `docs/plans/2026-03-21-financial-module-design.md`
  - Inclui: pagamentos, recibos, relatórios financeiros, simulações

## Próximos Passos

1. Implementar módulo financeiro (sessões 01-15)
2. Expandir cobertura de testes para >90%
3. Adicionar suporte a notificações (email/push)

## Decisões Recentes

- **2026-03-21:** Setup completo do Claude Code (CLAUDE.md otimizado, rules, agents, hooks, skills, MCP)
- **2026-03-21:** Design do módulo financeiro documentado
- **Arquitetura:** Service layer pattern consolidado — toda lógica de negócio em `core/services/`
- **Cache:** Redis com invalidação automática via Django signals
- **Soft Delete:** Implementado em todos os models via mixins
