"""
Parser de faturas do Itaú para o formato do financial_data_template.json.

Uso:
    python scripts/parse_itau_fatura.py fatura.txt --pessoa "Rodrigo" --cartao "Itau Azul Rodrigo"

O arquivo .txt deve conter o texto extraído da fatura PDF (copiar/colar do PDF).
O script identifica:
  - Compras parceladas (formato NN/TT) → compras_cartao com parcelas
  - Compras à vista (sem NN/TT) → compras_cartao com total_parcelas=1
  - Mensalidade/anuidade → compras_cartao com total_parcelas=1
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path


@dataclass
class FaturaEntry:
    descricao: str
    valor_parcela: float
    parcela_atual: int
    total_parcelas: int
    data_compra: str
    data_vencimento_atual: str
    categoria: str | None = None
    notas: str = ""


@dataclass
class FaturaData:
    titular: str = ""
    cartao_final: str = ""
    vencimento: str = ""
    fechamento: str = ""
    proximo_fechamento: str = ""
    total_fatura: float = 0.0
    entries: list[FaturaEntry] = field(default_factory=list)
    mensalidade_liquida: float = 0.0


CATEGORY_MAP: dict[str, str | None] = {
    "saúde": "Farmácia",
    "saude": "Farmácia",
    "farmácia": "Farmácia",
    "farmacia": "Farmácia",
    "supermercado": "Mercado",
    "vestuário": "Vestuário",
    "vestuario": "Vestuário",
    "eletronicos": None,
    "transporte": None,
    "educação": None,
    "educacao": None,
    "outros": None,
    "casa": None,
    "serviços": None,
    "servicos": None,
    "retail": None,
}


def infer_year(month: int, fatura_date: date) -> int:
    """Infere o ano de uma transação com base no mês e na data da fatura."""
    # Meses iguais ou anteriores ao fechamento = mesmo ano ou ano anterior
    # Se o mês é maior que o mês do fechamento, é do ano anterior
    if month > fatura_date.month + 2:
        return fatura_date.year - 1
    return fatura_date.year


def parse_installment(text: str) -> tuple[int, int] | None:
    """Extrai NN/TT de um texto. Retorna (parcela_atual, total_parcelas) ou None."""
    match = re.search(r"\b(\d{2})/(\d{2})\b", text)
    if match:
        nn = int(match.group(1))
        tt = int(match.group(2))
        # Validar que parece ser parcelas (não data)
        if 1 <= nn <= tt <= 99 and tt >= 2:
            return nn, tt
    return None


def parse_lancamento_line(line: str) -> dict | None:
    """Tenta parsear uma linha de lançamento.

    Formato esperado: DD/MM ESTABELECIMENTO [NN/TT] VALOR
    """
    # Padrão: data no início, valor no final
    match = re.match(
        r"(\d{2}/\d{2})\s+(.+?)\s+([\d.,]+)\s*$",
        line.strip(),
    )
    if not match:
        return None

    date_str = match.group(1)
    middle = match.group(2).strip()
    valor_str = match.group(3).replace(".", "").replace(",", ".")

    try:
        valor = float(valor_str)
    except ValueError:
        return None

    # Checar se tem parcelas no middle
    installment = parse_installment(middle)
    if installment:
        # Remover o NN/TT do nome do estabelecimento
        desc = re.sub(r"\s*\d{2}/\d{2}\s*", " ", middle).strip()
        parcela_atual, total_parcelas = installment
    else:
        desc = middle
        parcela_atual = 1
        total_parcelas = 1

    day, month = int(date_str[:2]), int(date_str[3:5])

    return {
        "day": day,
        "month": month,
        "descricao": desc,
        "valor": valor,
        "parcela_atual": parcela_atual,
        "total_parcelas": total_parcelas,
    }


def parse_fatura_text(text: str) -> FaturaData:
    """Parseia o texto completo de uma fatura Itaú."""
    fatura = FaturaData()

    # Extrair vencimento
    venc_match = re.search(r"Vencimento:\s*(\d{2}/\d{2}/\d{4})", text)
    if venc_match:
        d, m, y = venc_match.group(1).split("/")
        fatura.vencimento = f"{y}-{m}-{d}"

    # Extrair fechamento
    fech_match = re.search(r"Emissão:\s*(\d{2}/\d{2}/\d{4})", text)
    if fech_match:
        d, m, y = fech_match.group(1).split("/")
        fatura.fechamento = f"{y}-{m}-{d}"

    # Extrair próximo fechamento
    prox_match = re.search(r"próx\.\s*Fechamento:\s*(\d{2}/\d{2}/\d{4})", text)
    if prox_match:
        d, m, y = prox_match.group(1).split("/")
        fatura.proximo_fechamento = f"{y}-{m}-{d}"

    # Extrair titular
    titular_match = re.search(r"Titular\s+(.+?)$", text, re.MULTILINE)
    if titular_match:
        fatura.titular = titular_match.group(1).strip()

    # Extrair cartão
    cartao_match = re.search(r"Cartão\s+(\d{4})\.XXXX\.XXXX\.(\d{4})", text)
    if cartao_match:
        fatura.cartao_final = cartao_match.group(2)

    # Extrair total
    total_match = re.search(r"Total desta fatura\s+([\d.,]+)", text)
    if total_match:
        fatura.total_fatura = float(total_match.group(1).replace(".", "").replace(",", "."))

    # Identificar a data da fatura para inferir ano
    if fatura.fechamento:
        fatura_date = date.fromisoformat(fatura.fechamento)
    elif fatura.vencimento:
        fatura_date = date.fromisoformat(fatura.vencimento)
    else:
        fatura_date = date.today()

    # Extrair lançamentos da seção "compras e saques"
    # Procurar a seção de lançamentos
    lines = text.split("\n")

    in_lancamentos = False
    in_proximas = False
    in_produtos = False
    pending_entry: dict | None = None
    mensalidade_total = 0.0

    for line in lines:
        stripped = line.strip()

        # Detectar seções
        if "compras parceladas" in stripped.lower() and "próximas" in stripped.lower():
            in_proximas = True
            in_lancamentos = False
            in_produtos = False
            continue

        if "produtos e serviços" in stripped.lower() and "lançamentos" in stripped.lower():
            in_produtos = True
            in_lancamentos = False
            in_proximas = False
            continue

        if "compras e saques" in stripped.lower() and "lançamentos" in stripped.lower():
            in_lancamentos = True
            in_proximas = False
            in_produtos = False
            continue

        # Pular seção de próximas faturas
        if in_proximas:
            continue

        # Processar produtos e serviços (mensalidade)
        if in_produtos:
            if "Mensalidade" in stripped or "Anuidade" in stripped:
                # Extrair valor
                val_match = re.search(r"([-]?[\d.,]+)\s*$", stripped)
                if val_match:
                    val = float(val_match.group(1).replace(".", "").replace(",", "."))
                    mensalidade_total += val
            elif "Redução" in stripped or "Desconto" in stripped:
                val_match = re.search(r"([-]?[\d.,]+)\s*$", stripped)
                if val_match:
                    val = float(val_match.group(1).replace(".", "").replace(",", "."))
                    mensalidade_total += val
            continue

        # Processar lançamentos de compras
        if not in_lancamentos:
            continue

        # Ignorar linhas de header
        if stripped.startswith("DATA") or stripped.startswith("RODRIGO") or not stripped:
            if pending_entry:
                _finalize_entry(fatura, pending_entry, fatura_date)
                pending_entry = None
            continue

        # Ignorar linhas de totais
        if "Lançamentos no cartão" in stripped or "Total" in stripped.lower():
            if pending_entry:
                _finalize_entry(fatura, pending_entry, fatura_date)
                pending_entry = None
            continue

        # Tentar parsear como lançamento
        parsed = parse_lancamento_line(stripped)
        if parsed:
            # Finalizar entrada pendente
            if pending_entry:
                _finalize_entry(fatura, pending_entry, fatura_date)

            pending_entry = parsed
        elif pending_entry:
            # Linha de continuação (categoria + cidade)
            category_line = stripped.lower()
            for cat_key, cat_value in CATEGORY_MAP.items():
                if category_line.startswith(cat_key):
                    pending_entry["categoria"] = cat_value
                    # Adicionar a linha à descrição
                    pending_entry["descricao"] += f" {stripped}"
                    break
            else:
                # Pode ser continuação da descrição
                pending_entry["descricao"] += f" {stripped}"

    # Finalizar última entrada pendente
    if pending_entry:
        _finalize_entry(fatura, pending_entry, fatura_date)

    fatura.mensalidade_liquida = round(mensalidade_total, 2)

    return fatura


def _finalize_entry(fatura: FaturaData, entry: dict, fatura_date: date) -> None:
    """Converte um dict de lançamento em FaturaEntry e adiciona à fatura."""
    year = infer_year(entry["month"], fatura_date)
    data_compra = f"{year}-{entry['month']:02d}-{entry['day']:02d}"

    fatura.entries.append(
        FaturaEntry(
            descricao=_clean_description(entry["descricao"]),
            valor_parcela=entry["valor"],
            parcela_atual=entry["parcela_atual"],
            total_parcelas=entry["total_parcelas"],
            data_compra=data_compra,
            data_vencimento_atual=fatura.vencimento,
            categoria=entry.get("categoria"),
        )
    )


def _clean_description(desc: str) -> str:
    """Limpa a descrição removendo espaços extras."""
    # Remover espaços duplos
    desc = re.sub(r"\s+", " ", desc).strip()
    return desc


def to_financial_json(
    fatura: FaturaData,
    pessoa: str,
    cartao: str,
) -> dict:
    """Converte FaturaData para o formato do financial_data_template.json."""
    compras: list[dict] = []

    for entry in fatura.entries:
        item: dict = {
            "pessoa": pessoa,
            "cartao": cartao,
            "descricao": entry.descricao,
            "valor_parcela": entry.valor_parcela,
            "parcela_atual": entry.parcela_atual,
            "total_parcelas": entry.total_parcelas,
            "data_compra": entry.data_compra,
            "data_proxima_parcela": entry.data_vencimento_atual
            if entry.total_parcelas > 1
            else None,
            "categoria": entry.categoria,
            "notas": "",
        }
        compras.append(item)

    # Mensalidade como gasto à vista
    if fatura.mensalidade_liquida != 0:
        compras.append(
            {
                "pessoa": pessoa,
                "cartao": cartao,
                "descricao": f"Anuidade {cartao} (líquida)",
                "valor_parcela": abs(fatura.mensalidade_liquida),
                "parcela_atual": 1,
                "total_parcelas": 1,
                "data_compra": fatura.fechamento or fatura.vencimento,
                "data_proxima_parcela": None,
                "categoria": None,
                "notas": "Mensalidade - Redução",
            }
        )

    return {
        "metadata": {
            "titular": fatura.titular,
            "cartao_final": fatura.cartao_final,
            "vencimento": fatura.vencimento,
            "fechamento": fatura.fechamento,
            "total_fatura": fatura.total_fatura,
            "total_parcelas_encontradas": len([e for e in fatura.entries if e.total_parcelas > 1]),
            "total_avista_encontradas": len([e for e in fatura.entries if e.total_parcelas == 1]),
            "mensalidade_liquida": fatura.mensalidade_liquida,
        },
        "compras_cartao": compras,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Parser de faturas Itaú")
    parser.add_argument("file", help="Arquivo .txt com texto da fatura")
    parser.add_argument("--pessoa", required=True, help="Nome da pessoa no template")
    parser.add_argument("--cartao", required=True, help="Apelido do cartão no template")
    parser.add_argument("--output", "-o", help="Arquivo de saída JSON (default: stdout)")
    args = parser.parse_args()

    file_path = Path(args.file)
    if not file_path.exists():
        print(f"Arquivo não encontrado: {file_path}")
        sys.exit(1)

    text = file_path.read_text(encoding="utf-8")
    fatura = parse_fatura_text(text)
    result = to_financial_json(fatura, args.pessoa, args.cartao)

    output = json.dumps(result, indent=2, ensure_ascii=False)

    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
        print(f"Resultado salvo em: {args.output}")
        print(f"  Parcelas: {result['metadata']['total_parcelas_encontradas']}")
        print(f"  À vista: {result['metadata']['total_avista_encontradas']}")
        print(f"  Mensalidade líquida: R$ {result['metadata']['mensalidade_liquida']}")
    else:
        print(output)


if __name__ == "__main__":
    main()
