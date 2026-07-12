# Status do Projeto

**Última atualização:** 2026-07-12

## Estado Atual

- **Backend:** Django REST Framework — 2600 testes passando, 92.35% coverage
- **Frontend:** Next.js 14 + React 18 — 970 testes passando
- **Módulos entregues:** cadastro (buildings/apartments/tenants/leases/furniture), financeiro pessoal legado (`financial/` — DEPRECATED, remoção planejada), condomínio (`finances/` — contas, faturas, parcelamentos, reservas, fechamento mensal, parser de faturas DMAE/CEEE), portal do inquilino, PWA (offline read-only + web push), app mobile Expo
- **Infraestrutura:** Docker, CI/CD (GitHub Actions), pre-commit hooks, Supabase (produção) + Postgres local

## Histórico e Estado Detalhado

Este arquivo é um snapshot enxuto. Para o histórico completo de sessões executadas, decisões de produto e contratos cross-sessão, ver:

- `prompts/SESSION_STATE.md` — estado sessão-a-sessão de cada feature
- `docs/plans/` — design docs e planos de execução (auditorias, roadmaps, features)

## Decisões Recentes

- Fonte canônica de princípios de design e regras de arquitetura: `.claude/rules/`
- Cache: Redis com invalidação automática via Django signals
- Soft Delete: implementado em todos os models via mixins (exceções documentadas em `CLAUDE.md`)
