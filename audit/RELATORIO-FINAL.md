# Relatório Final — Fable Audit · Condomínios Manager

**Período**: 2026-07-12 a 2026-07-13 · **Baseline**: master `f0a1323` (após merge do perf/p5-p6) · **Estado final**: master `84e94e3` · **Escopo**: backend Django + frontend web Next.js (mobile Expo fora, por decisão do usuário)

---

## 1. Sumário executivo

A auditoria partiu de um sistema já maduro — 2.600 testes verdes e uma auditoria anterior (2026-07-10) com 142 achados parcialmente pendentes de verificação — e o levou, em seis fases com aprovação humana entre cada uma, a um estado em que **todos os achados corrigíveis foram corrigidos com evidência**, o design system passou a ser efetivamente adotado, e o produto ganhou uma demo reproduzível e um parecer realista de comercialização.

A Fase 1 consolidou ~128 achados abertos (re-verificando adversarialmente os 53 pendentes do bloco frontend/portal/infra/testes — o merge de P5/P6 só havia resolvido 3). A Fase 2 corrigiu ~114 deles em 14 lotes e 3 PRs mergeados, incluindo os 14 críticos: o portal do inquilino inteiro estava inoperante (login OTP não autenticava, upload de comprovante sempre 400), o caixa de mês fechado era mutável por pagamento retrodatado, qualquer inquilino autenticado lia o portfólio inteiro com PII de proprietários, e a troca de vencimento para o mesmo dia cobrava um mês de taxa. A Fase 3 não fez rebrand — descobriu que os tokens e componentes certos já existiam sem adoção, e os adotou (dark mode passou a funcionar nos gráficos; um único padrão de loading, de stat-card e de header). A Fase 4 priorizou 10 features ancoradas em mercado e código, com Top 3 aprovado (moderação de comprovantes → régua WhatsApp+PIX → IPCA em lote). A Fase 5 entregou o modo demo com dados fictícios estruturalmente reais, verificado navegando o app de verdade — o que ainda pegou 2 bugs do próprio seed. A Fase 6 concluiu que comercializar é viável mas de cauda longa, e recomendou validação a custo zero antes de qualquer produtização.

**Próximos passos** (em ordem): (1) OPS de deploy — conferir render.yaml no dashboard Render e deixar a migration 0009 aplicar; (2) executar o Top 3 de features da Fase 4; (3) destravar os deferidos de infra (S3 + Celery) que também são pré-requisito de comercialização; (4) se houver apetite comercial, rodar o Mês 1 de validação da Fase 6.

## 2. Métricas antes → depois

| Métrica | Antes (f0a1323) | Depois (84e94e3) |
|---|---|---|
| Testes backend | 2.600 passed | **2.721 passed** (+121 regressões novas) |
| Cobertura backend | 92,35% | **92,40%** (piso de CI: 90%) |
| Testes frontend | 943/945 (2 falhas) | **1.024/1.024** (+ testes das Fases 3/5 → 1.040+ no estado final) |
| ruff / mypy / pyright | limpos / limpos / limpos | limpos (0 erros, 0 warnings em 118 arquivos Python) |
| eslint / tsc | limpos, mas com 3 `eslint-disable` no client | **0 supressões inline no repo** (política CRITICAL cumprida) |
| Vulnerabilidades npm | 29 (5 críticas) | **6** — só famílias deferidas (next@14 breaking; xlsx sem fix upstream) |
| Vulnerabilidades pip | 0 | 0 |
| Achados abertos da auditoria | ~128 | **0 corrigíveis abertos**; 14 deferidos com justificativa registrada |
| A11y | 3 icon-buttons sem nome acessível; touch 36px no portal; contraste warning sem par | labels adicionados; portal com touch 44px; charts em tokens com dark real |
| `vi.mock` de hooks internos (política de mock) | 11 arquivos | **0** (100% MSW) |
| Deploy | start command e crons só no dashboard | **render.yaml versionado** (web + 2 crons America/Sao_Paulo) |

## 3. Design system (Fase 3)

O inventário do ui-auditor mostrou uma base boa e um problema de adoção: paleta oklch completa com paridade dark 1:1, Radix em 100% dos modais, sonner único — mas os gráficos usavam hex fixos ignorando os `--chart-1..5` (logo, sem dark), 39 stat-cards manuais coexistiam com um `StatCard` de 4 usos, dois padrões de loading disputavam o app e os títulos alternavam entre text-2xl e text-3xl sem critério. A direção escolhida foi consolidação, não rebrand: a identidade teal permanece; o orçamento de mudança foi gasto em consistência e no portal do inquilino (touch targets 44px, aria-labels). Modernizações entregues: charts nos tokens (dark funcional), skeleton rows como padrão único de loading no DataTable, `PageHeader` em 29 páginas, `StatCard` com loading embutido, estados error/empty/disabled nas telas que não os tinham, PWA theme-color corrigido para o sRGB real do token.

**Backlog restante (deliberado)**: density switcher de tabelas (YAGNI para 1-2 usuários), polish profundo do módulo `financial/` legado (DEPRECATED, remoção prevista no P7), limpeza das ~124 classes Tailwind arbitrárias (baixo impacto; corrigir quando tocar no arquivo).

## 4. Roadmap de features (Fase 4 — detalhe em `audit/fase-4-roadmap.md`)

Top 3 aprovado: **(1) Tela web de moderação de comprovantes PIX** (impacto 5, esforço 1 — backend 100% pronto após a Fase 2 fazer aprovação registrar o pagamento); **(2) Régua de cobrança WhatsApp com PIX embutido** (5×3 — o recurso definidor da categoria no BR; Twilio, payload PIX e cron já existem); **(3) Reajuste IPCA em lote com notificação ao inquilino** (4×2 — alertas de elegíveis já existem; tipos de notificação declarados e nunca emitidos). Demais 7 features na matriz: composer de avisos, relatório anual p/ IR, exports no finances, assinatura eletrônica, anexo em Bill (depende de S3), backup na UI, trilha de auditoria.

## 5. Demo (Fase 5 — guia completo em `docs/DEMO.md`)

Banco separado `condominio_demo`, populado por `python manage.py seed_demo --reset --verify` com guarda dura (só roda em DB com "demo"/"test_" no nome e DEBUG). Dataset fictício com pesquisa de domínio real: IPCA IBGE mês a mês, aluguéis de kitnet POA, tarifas DMAE/CEEE 2026, IPTU em 10×. Inventário: 3 prédios, 34 kitnets, 28 leases ativas (6 vagas), 30 inquilinos com CPFs algoritmicamente válidos, 475 pagamentos em 18 meses (atrasos crônicos, prepago, salary-offset), 10 reajustes IPCA, 240 lançamentos condominiais, 17 meses fechados com continuidade de caixa provada pelo `--verify`, 6 comprovantes PIX. Personas (senha `Demo@2026`): `gestor.demo`, `inquilino.pontual`, `inquilino.atrasado`, `inquilino.onboarding`. O roteiro de demonstração de 9 passos está no DEMO.md e foi verificado navegando o app real (dashboard, locações, contas, portal nas 3 personas).

## 6. Comercialização (Fase 6 — parecer completo em `audit/fase-6-gtm.md`)

Posicionamento possível: proprietário-PF autogestor com 5-50 unidades — nicho real (18,9 mi de domicílios alugados, recorde IBGE 2025) e mal atendido pelas 1.209 proptechs BR, que miram imobiliárias com pricing opaco e cobram como add-on o que este produto tem nativo (portal do inquilino, PIX, reajuste). Pricing sugerido transparente: Grátis ≤5 / R$49 ≤20 / R$99 ≤60 unidades. Gaps honestos antes de vender: multi-tenancy (o sistema é single-tenant por design), billing, LGPD, S3+Celery. Break-even com premissas explícitas: 4 clientes cobrem infra; ~19 remuneram a manutenção — funil de 6-12 meses via SEO. **Parecer**: viável, mas começar por validação a custo zero (vídeo da demo + landing + 10 conversas, com gates de decisão), usando multi-instância como atalho de piloto. Estimativas para planejamento, não aconselhamento financeiro.

## 7. Apêndices

- **Tabela completa de achados com status final**: `audit/findings.md` (inclui a tabela de 14 deferidos com justificativa e destino)
- **Logs de verificação por lote** (14 lotes, comandos e números reais): `audit/verification-log.md`
- **Roadmap de features com specs do Top 3**: `audit/fase-4-roadmap.md`
- **Parecer GTM com fontes**: `audit/fase-6-gtm.md`
- **PRs da auditoria**: #20 (baseline P5/P6), #21 (Fase 2), #22 (Fase 3), #23 (Fase 5)
- **Relatórios de origem**: `docs/plans/2026-07-10-full-audit-report.md` + `2026-07-10-audit-roadmap.md`
