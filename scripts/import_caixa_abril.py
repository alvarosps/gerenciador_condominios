"""
Import Caixa Rodrigo April 2026 fatura data into the database.

Only imports NEW items not already in DB:
- 21 à vista purchases
- 1 new parcelada (MERCADOLIVRE 2PRODUTOS 01/02)
- Anuidade already tracked (12 installments)
- All other parceladas already exist from March import
"""

import os
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "condominios_manager.settings")

import django

django.setup()

from django.db import transaction

from core.models import CreditCard, Expense, ExpenseInstallment, Person


def add_months(source_date: date, months: int) -> date:
    month = source_date.month - 1 + months
    year = source_date.year + month // 12
    month = month % 12 + 1
    day = min(
        source_date.day,
        [
            31,
            29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28,
            31,
            30,
            31,
            30,
            31,
            31,
            30,
            31,
            30,
            31,
        ][month - 1],
    )
    return date(year, month, day)


def main() -> None:
    rodrigo = Person.objects.get(name="Rodrigo")
    caixa = CreditCard.objects.get(person=rodrigo, nickname="Caixa Rodrigo")
    due_day = caixa.due_day  # 7

    # Vencimento desta fatura: 08/04/2026
    fatura_vencimento = date(2026, 4, 8)

    # === COMPRAS À VISTA ===
    avista = [
        ("BISTEK SUPERMERCADOS", 176.22, date(2026, 3, 8)),
        ("POSTO CARLAO", 128.11, date(2026, 3, 8)),
        ("DL GOOGLE YOUTUBE", 53.90, date(2026, 3, 9)),
        ("FRUTEIRAO DO FORTE", 72.22, date(2026, 3, 10)),
        ("CAPPTA FPS COMERCIO D", 342.00, date(2026, 3, 12)),
        ("SERRABEN", 65.02, date(2026, 3, 13)),
        ("PANVEL FILIAL 369", 29.43, date(2026, 3, 14)),
        ("MERCADOLIVRE 2PRODUTOS", 40.64, date(2026, 3, 14)),
        ("SUPERMERCADOS JM RAMOS", 49.63, date(2026, 3, 14)),
        ("POSTO FLEX CARLAO", 154.58, date(2026, 3, 14)),
        ("MP FRUTEIRAO DO FORTE", 43.68, date(2026, 3, 14)),
        ("CARLOS ALBERTO", 110.00, date(2026, 3, 17)),
        ("MCDONALDS", 55.80, date(2026, 3, 17)),
        ("BIGMIX", 97.73, date(2026, 3, 18)),
        ("POSTO FLEX", 165.85, date(2026, 3, 19)),
        ("MP FRUTEIRAO DO FORTE", 68.10, date(2026, 3, 19)),
        ("BISTEK SUPERMERCADOS", 351.60, date(2026, 3, 19)),
        ("MP MAURO CESAR DAS", 32.00, date(2026, 3, 19)),
        ("COM DE COMBUSTIVEIS AP", 150.00, date(2026, 3, 21)),
        ("CARLOS ALBERTO", 120.00, date(2026, 3, 23)),
        ("MP FRUTEIRAO DO FORTE", 19.27, date(2026, 3, 24)),
    ]

    # === NOVA PARCELADA (não existia no banco) ===
    nova_parcelada = {
        "descricao": "MERCADOLIVRE 2PRODUTOS",
        "valor_parcela": Decimal("35.76"),
        "parcela_atual": 1,
        "total_parcelas": 2,
        "data_compra": date(2026, 3, 24),
        "data_proxima_parcela": fatura_vencimento,
    }

    with transaction.atomic():
        # 1. Importar compras à vista
        print(f"Importando {len(avista)} compras à vista...")
        for desc, valor, data_compra in avista:
            expense = Expense.objects.create(
                description=desc,
                expense_type="card_purchase",
                total_amount=Decimal(str(valor)),
                expense_date=data_compra,
                person=rodrigo,
                credit_card=caixa,
                is_installment=False,
                is_paid=False,
            )
            print(f"  + {data_compra} {desc} R${valor}")

        # 2. Importar nova parcelada
        total_amount = nova_parcelada["valor_parcela"] * nova_parcelada["total_parcelas"]
        expense = Expense.objects.create(
            description=nova_parcelada["descricao"],
            expense_type="card_purchase",
            total_amount=total_amount,
            expense_date=nova_parcelada["data_compra"],
            person=rodrigo,
            credit_card=caixa,
            is_installment=True,
            total_installments=nova_parcelada["total_parcelas"],
            is_paid=False,
        )

        # Calculate first due date from data_proxima_parcela (which is parcela 1)
        first_due = nova_parcelada["data_proxima_parcela"]
        for i in range(1, nova_parcelada["total_parcelas"] + 1):
            due_date = add_months(first_due, i - 1)
            ExpenseInstallment.objects.create(
                expense=expense,
                installment_number=i,
                total_installments=nova_parcelada["total_parcelas"],
                amount=nova_parcelada["valor_parcela"],
                due_date=due_date,
                is_paid=False,
            )

        print(
            f"  + {nova_parcelada['data_compra']} {nova_parcelada['descricao']} R${nova_parcelada['valor_parcela']} x 1/2"
        )

    print(f"\nTotal importado: {len(avista)} à vista + 1 parcelada = {len(avista) + 1} expenses")
    total_avista = sum(v for _, v, _ in avista)
    print(f"Total à vista: R${total_avista:.2f}")
    print(f"Total parcelada (nesta fatura): R${nova_parcelada['valor_parcela']}")
    print("Total fatura (check): R$3.914,28")


if __name__ == "__main__":
    main()
