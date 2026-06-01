import subprocess
import sys

def install(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

try:
    from fpdf import FPDF
except ImportError:
    install('fpdf2')
    from fpdf import FPDF

import datetime

# Create instance of FPDF class
pdf = FPDF()

# Add a page
pdf.add_page()

# Set font
pdf.set_font("Helvetica", style="B", size=14)

# Title
pdf.cell(0, 10, "COMUNICADO DE REAJUSTE DE ALUGUEL", new_x="LMARGIN", new_y="NEXT", align="C")
pdf.ln(10)

pdf.set_font("Helvetica", size=12)

# Content
text = """À(o) Locatária(o) da Kitnet 205, Prédio 836

Assunto: Notificação de Reajuste Anual de Aluguel

Prezado(a) Inquilino(a),

Servimo-nos da presente para notificar formalmente que, de acordo com as cláusulas do contrato de locação e as normas legais vigentes, o valor do seu aluguel sofrerá o reajuste anual a partir do mês atual.

1. Base do Reajuste:
O índice utilizado para a atualização monetária é o IPCA (Índice Nacional de Preços ao Consumidor Amplo), calculado pelo IBGE, que acumulou uma variação de 4,39% no período estipulado para reajuste.

2. Justificativa:
O reajuste anual pelo IPCA é um procedimento padrão, previsto na Lei do Inquilinato, cujo objetivo é a recomposição do poder de compra da moeda e a manutenção do equilíbrio econômico do contrato frente à inflação oficial do período, sem representar aumento real do custo de locação.

3. Valores Atualizados:
   - Valor do Aluguel Anterior: R$ 934,00
   - Índice Aplicado (IPCA): + 4,39%
   - Acréscimo: R$ 41,00
   - Novo Valor do Aluguel: R$ 975,00

O novo valor de R$ 975,00 (novecentos e setenta e cinco reais) já deverá ser considerado para o pagamento do aluguel com vencimento agora no mês de Junho/2026.

Caso os boletos já tenham sido emitidos ou programados com o valor antigo, enviaremos a via atualizada para o devido pagamento, ou a diferença poderá ser ajustada conforme orientação da administração.

Ficamos à inteira disposição para eventuais dúvidas ou esclarecimentos adicionais.

Atenciosamente,



___________________________________________________
A Administração / Locador
Data: 01 de Junho de 2026
"""

pdf.multi_cell(0, 7, text)

# Save the pdf
output_filename = "Notificacao_Reajuste_Kitnet_205.pdf"
pdf.output(output_filename)

print(f"PDF successfully generated at {output_filename}")
