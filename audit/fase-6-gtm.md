# Fase 6 — Parecer de Viabilidade de Comercialização (versão leve, 2026-07-13)

Base: dossiê do market-analyst (fontes citadas ao final) + conhecimento direto do código (Fases 1-5).
**Aviso**: estimativas para planejamento, não aconselhamento financeiro.

## 1. Posicionamento possível

**Para quem**: proprietário-pessoa-física autogestor com 5-50 unidades (kitnets/apartamentos) — exatamente o perfil do sistema hoje. O mercado de aluguel bateu recorde (18,9 mi de domicílios alugados, 23,8% do total, IBGE/PNAD 2025) e imobiliárias cobram 8-12% do aluguel + ~1 aluguel por contrato novo — incentivo econômico forte à autogestão.

**Contra quem**: as 1.209 proptechs BR miram quase todas a IMOBILIÁRIA (pricing opaco, R$100-500/mês, features travadas por volume, portal do inquilino como add-on pago). O recorte PF-autogestor é pouco endereçado; os players internacionais (TenantCloud US$15-50, Innago grátis, MagicDoor US$2,50/lease) provam que o modelo self-serve barato funciona no segmento.

**Por que ganharia**: os diferenciais que já existem NATIVOS no produto são exatamente as dores nº 1 dos incumbentes (Reclame Aqui/Superlógica 7.5): portal do inquilino + comprovante PIX + WhatsApp OTP incluídos (add-ons pagos alhures), reajuste IPCA automatizado, contas do condomínio integradas, pricing que PODE ser transparente. Pós-auditoria, a base técnica está genuinamente sólida (2.700+ testes, cov 92%, gates zerados).

## 2. O que falta para vender (gaps honestos, em ordem de dureza)

| Gap | Tamanho | Nota |
|---|---|---|
| **Multi-tenancy** | GRANDE (semanas) | Landlord e FinancialSettings são singletons; Condominium existe como tenancy-root mas o auth não escopa por organização. SEM isso, só o modelo multi-instância (abaixo) funciona |
| Billing/assinatura + onboarding self-serve | Médio | Gateway (Stripe/Pagar.me), trial, signup de organização |
| LGPD | Médio | Dados de inquilinos = PII de terceiros: DPA, termos, base legal, exclusão |
| Storage durável (I2) + Celery real (I1) | Médio | Já deferidos da Fase 2; obrigatórios com clientes |
| Cobrança automática (P2 da Fase 4) | Médio | Régua WhatsApp+PIX é O recurso da categoria no BR |
| Suporte/observabilidade | Contínuo | A dor nº1 dos concorrentes é suporte ruim — barra baixa, mas é gente |
| Mobile | Fora | 24 achados abertos; portal web PWA cobre o essencial |

**Atalho estratégico — multi-instância**: o sistema é single-tenant por design; para 2-5 clientes, um deploy por cliente (Render+Supabase free/starter) evita o refactor de multi-tenancy inteiro. Viável como piloto; não escala além de ~5-10 clientes (custo e ops por instância).

## 3. Modelo de monetização recomendado

Planos por faixa, **preço público transparente** (ataca a opacidade do mercado BR), calibrado entre o piso internacional e o teto BR:

| Plano | Unidades | Preço sugerido | Racional |
|---|---|---|---|
| Grátis | até 5 | R$ 0 | funil (MagicDoor/Innago provam o modelo); PF com 2-3 imóveis |
| Pro | até 20 | **R$ 49/mês** | undercut do entry da Pilota (R$49 no plano de 3!) com muito mais produto |
| Carteira | até 60 | **R$ 99/mês** | ~½ do entry Kenlo (R$247); cobre o perfil "você" (37 unidades) |

Ticket médio de planejamento: **R$ 69/mês**.

## 4. Break-even simples (TODAS as premissas explícitas)

Premissas: ticket médio R$69 · infra compartilhada multi-tenant R$250/mês (Render paid + Supabase Pro + Twilio) · manutenção/suporte 10h/mês valoradas a R$100/h = R$1.000/mês · CAC ≈ R$0 em caixa (SEO/conteúdo/comunidade — paga-se em tempo) · conversão trial→pago 9-18% (benchmark global sem cartão) · churn 2-3%/mês.

- **Cobrir infra**: 4 clientes pagantes.
- **Cobrir infra + valor do seu tempo de manutenção**: ~19 clientes.
- Com conversão de 10%, ~19 pagantes exigem ~190 trials — em canal orgânico, é um funil de 6-12 meses, não 90 dias.

## 5. Parecer (a síntese em 4 frases)

Comercializar é **tecnicamente viável e o nicho existe**, mas o ticket é baixo e o retorno só compensa com dezenas de clientes — não é dinheiro rápido, é um produto de cauda longa via SEO. O caminho de MENOR risco não começa com código: começa com **validação barata** usando o que a Fase 5 já entregou (demo + roteiro). Só investir nos gaps grandes (multi-tenancy, billing, LGPD) se a validação der sinal. Enquanto isso, o sistema continua pagando-se como uso próprio — que já é o ROI real dele.

## 6. Esboço 90 dias (condicional, com gates de decisão)

- **Mês 1 — Validar (custo ~zero)**: gravar vídeo de 5min seguindo o roteiro da demo (docs/DEMO.md); landing page com pricing + lista de espera; 10 conversas com proprietários autogestores (grupos/fóruns). **Gate: ≥50 e-mails OU 5 "eu pagaria" explícitos — senão, parar aqui sem custo.**
- **Mês 2 — Piloto multi-instância**: 2 proprietários conhecidos como beta grátis (1 deploy cada); executar I1/I2 (Celery+S3) + P2 da Fase 4 (régua WhatsApp) que servem ao SEU uso de qualquer forma. **Gate: os 2 betas usando semanalmente.**
- **Mês 3 — Primeiros pagantes**: converter betas a 50% off; decisão make-or-buy do multi-tenancy só aqui, com demanda comprovada.

## Fontes principais
IBGE/PNAD via [Portas](https://portas.com.br/dados-inteligencia/aluguel-dispara-no-brasil-e-fatia-de-imoveis-quitados-encolhe/) e [Agência IBGE](https://agenciadenoticias.ibge.gov.br/agencia-noticias/2012-agencia-de-noticias/noticias/46449-domicilios-alugados-cresceram-mais-de-50-desde-2016) · [Kenlo planos](https://www.kenlo.com.br/planos-imob/) · [Pilota comparativo](https://blog.pilotaimoveis.com.br/post/plataforma-gestao-alugueis-imobiliarios-brasil-comparacao-superlogica-kenlo-imobzi) · [TenantCloud](https://www.tenantcloud.com/pricing) · [Innago](https://innago.com/pricing/) · [MagicDoor](https://magicdoor.com/pricing/) · [Reclame Aqui Superlógica](https://www.reclameaqui.com.br/empresa/superlogica/) · [custos de imobiliária](https://regenteimoveis.com.br/guia/locacao/custo-administrar-imovel-sozinho-vs-imobiliaria/) · [proptechs BR](https://cvcrm.com.br/blog/proptechs-no-brasil/) · [benchmarks trial](https://www.pulseahead.com/blog/trial-to-paid-conversion-benchmarks-in-saas)
