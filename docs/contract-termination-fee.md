# Multa por rescisão antecipada

Regra: 2,5 aluguéis vigentes no mês da devolução, com redução de 1/12 da multa integral por mês completo desde o início da locação. O prazo para zerar a multa é de 12 meses, mesmo se a locação continuar.

Frações de mês: dias transcorridos desde o último aniversário mensal divididos pelos dias entre esse aniversário e o próximo. Se o dia inicial não existir no mês, usa-se o último dia do mês. O resultado monetário é arredondado uma única vez, para centavos.

Exemplo de aluguel de R$ 840: multa integral R$ 2.100; redução mensal R$ 175; após 1 mês R$ 1.925; após 12 meses R$ 0. Para aluguel de R$ 1.200, a multa integral correta é R$ 3.000 e a redução mensal é R$ 250.

## Aplicação no sistema

- `FeeCalculatorService.calculate_termination_fee` centraliza o cálculo.
- `GET /api/leases/{id}/calculate_termination_fee/?terminated_on=AAAA-MM-DD` fornece uma estimativa para administradores, sem alterar dados.
- O encerramento devolve `termination_fee_estimate` na resposta. O fluxo publicado encerra na data atual e não possui histórico financeiro de operações; esta mudança não introduz esse módulo.
- A tela apresenta a estimativa e orienta conferir o contrato assinado e as dispensas legais. Nenhuma cobrança ou pagamento é criado automaticamente.
- O template base contém a cláusula e o contexto inclui `termination_full_fee` e `termination_monthly_reduction`, também disponíveis no editor.

## Publicação do template ativo

O HTML base em `core/templates/contract_template.html` não substitui automaticamente o `ContractTemplate` ativo no banco. Antes de publicar uma alteração no template ativo:

1. Publicar o código que fornece as variáveis `termination_full_fee` e `termination_monthly_reduction`.
2. Guardar uma cópia do HTML ativo e identificar sua versão no editor de contratos.
3. Substituir somente o bloco antigo de rescisão pelo novo bloco do HTML base, de “CLÁUSULA – DA RESCISÃO ANTECIPADA, MULTA CONTRATUAL E AVISO PRÉVIO” até o parágrafo de dispensa legal. Alinhar também o parágrafo antigo de prazo com a prorrogação prevista na nova redação. Preservar outras personalizações.
4. Conferir a prévia com uma locação e salvar pelo editor, que cria uma nova versão com histórico.
5. Conferir um novo PDF. Os documentos já gerados e os contratos já assinados conservam suas condições; a estimativa não modifica essas condições.

A publicação e a gravação do template de produção não foram executadas nesta alteração. Não há alteração de schema nem migration.

O aviso pode ser eletrônico, inclusive WhatsApp, com recebimento comprovável. A cláusula prevê a entrega das chaves e a prorrogação por prazo indeterminado. A quantia de um aluguel e encargos por falta de aviso durante o prazo indeterminado é distinta da multa por rescisão antecipada (artigo 6º); não há cálculo automático dessa quantia, pois não existe registro de aviso prévio/encargos no fluxo de encerramento. A cláusula antiga de prazo que autorizava retomada livre pelo locador em 30 dias também foi alinhada à nova redação, sem classificar a permanência regular como irregular.
