"""
Script para importar dados financeiros a partir do JSON template.

Uso:
    python scripts/import_financial_data.py                              # usa scripts/data/financial_data.json
    python scripts/import_financial_data.py scripts/data/meu_arquivo.json  # arquivo customizado
    python scripts/import_financial_data.py --dry-run                    # simula sem gravar
    python scripts/import_financial_data.py --clear-first                # limpa dados financeiros antes de importar

Requer:
    - Todos os models do módulo financeiro implementados (sessões 01-05 do roadmap)
    - Banco de dados acessível com migrations aplicadas
    - Buildings e Apartments já cadastrados
"""

import json
import os
import sys
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

# Django setup
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "condominios_manager.settings")

import django

django.setup()

from django.db import transaction

from core.models import Apartment, Building, Lease

# Financial models — importados após django.setup()
from core.models import (
    CreditCard,
    EmployeePayment,
    Expense,
    ExpenseCategory,
    ExpenseInstallment,
    FinancialSettings,
    Income,
    Person,
    PersonIncome,
    PersonPayment,
    RentPayment,
)


class FinancialDataImporter:
    def __init__(self, data: dict, dry_run: bool = False):
        self.data = data
        self.dry_run = dry_run
        self.persons = {}  # nome -> Person
        self.cards = {}  # "pessoa|apelido" -> CreditCard
        self.categories = {}  # nome -> ExpenseCategory
        self.buildings = {}  # street_number -> Building
        self.stats = {
            "categories": 0,
            "persons": 0,
            "credit_cards": 0,
            "person_incomes": 0,
            "apartment_owners": 0,
            "lease_updates": 0,
            "expenses": 0,
            "installments": 0,
            "incomes": 0,
            "rent_payments": 0,
            "employee_payments": 0,
        }

    def run(self):
        prefix = "[DRY RUN] " if self.dry_run else ""
        print(f"\n{prefix}Iniciando importação de dados financeiros...")
        print("=" * 60)

        self._cache_buildings()
        self._import_settings()
        self._import_categories()
        self._import_persons()
        self._import_credit_cards()
        self._import_person_incomes()
        self._import_apartment_owners()
        self._import_vacant_apartments()
        self._import_lease_specials()
        self._import_card_purchases()
        self._import_bank_loans()
        self._import_personal_loans()
        self._import_offsets()
        self._import_utility_bills()
        self._import_debt_installments()
        self._import_iptu()
        self._import_fixed_expenses()
        self._import_one_time_expenses()
        self._import_extra_incomes()
        self._import_rent_payments()
        self._import_employee_payments()
        self._import_person_payments()

        print("\n" + "=" * 60)
        print(f"{prefix}Importação concluída!")
        print("\nResumo:")
        for key, count in self.stats.items():
            if count > 0:
                print(f"  {key}: {count}")

    def _cache_buildings(self):
        for b in Building.objects.all():
            self.buildings[b.street_number] = b
        print(f"  Prédios encontrados: {list(self.buildings.keys())}")

    def _get_building(self, street_number: int) -> Building:
        if street_number not in self.buildings:
            raise ValueError(f"Prédio com street_number={street_number} não encontrado no banco.")
        return self.buildings[street_number]

    def _get_apartment(self, street_number: int, apt_number: int) -> Apartment:
        building = self._get_building(street_number)
        try:
            return Apartment.objects.get(building=building, number=apt_number)
        except Apartment.DoesNotExist:
            raise ValueError(f"Apartamento {apt_number} do prédio {street_number} não encontrado.")

    def _get_lease(self, street_number: int, apt_number: int) -> Lease:
        apt = self._get_apartment(street_number, apt_number)
        try:
            return Lease.objects.get(apartment=apt)
        except Lease.DoesNotExist:
            raise ValueError(f"Lease não encontrado para apartamento {apt_number} do prédio {street_number}.")

    def _get_person(self, nome: str) -> Person:
        if nome not in self.persons:
            raise ValueError(f"Pessoa '{nome}' não encontrada. Verifique se está definida em 'pessoas'.")
        return self.persons[nome]

    def _get_card(self, pessoa: str, apelido: str) -> CreditCard:
        key = f"{pessoa}|{apelido}"
        if key not in self.cards:
            raise ValueError(f"Cartão '{apelido}' da pessoa '{pessoa}' não encontrado.")
        return self.cards[key]

    def _get_category(self, nome: str | None) -> ExpenseCategory | None:
        if not nome:
            return None
        if nome not in self.categories:
            raise ValueError(f"Categoria '{nome}' não encontrada. Verifique se está definida em 'categorias'.")
        return self.categories[nome]

    def _parse_date(self, date_str: str | None) -> date | None:
        if not date_str:
            return None
        return date.fromisoformat(date_str)

    def _require_date(self, date_str: str | None, field_name: str, context: str) -> date:
        result = self._parse_date(date_str)
        if result is None:
            raise ValueError(f"Campo '{field_name}' é obrigatório para {context}.")
        return result

    # =========================================================================
    # IMPORTAÇÃO POR SEÇÃO
    # =========================================================================

    def _import_settings(self):
        cfg = self.data.get("configuracoes")
        if not cfg:
            return

        print("\n[1/15] Configurações financeiras...")
        if not self.dry_run:
            FinancialSettings.objects.update_or_create(
                pk=1,
                defaults={
                    "initial_balance": Decimal(str(cfg["saldo_inicial"])),
                    "initial_balance_date": self._parse_date(cfg["data_saldo_inicial"]),
                    "notes": cfg.get("notas", ""),
                },
            )
        print(f"  Saldo inicial: R$ {cfg['saldo_inicial']} em {cfg['data_saldo_inicial']}")

    def _import_categories(self):
        section = self.data.get("categorias", {})
        # Suporta formato antigo (lista) e novo (dict com items)
        if isinstance(section, list):
            items = section
        else:
            items = section.get("items", [])
        if not items:
            return

        # Filtrar comentários
        items = [i for i in items if "_instrucoes" not in i and "_comentario" not in i]

        # Primeiro passo: criar categorias principais (parent=null)
        parents = [i for i in items if not i.get("parent")]
        children = [i for i in items if i.get("parent")]

        print(f"\n[2/15] Categorias de despesa ({len(items)})...")
        for item in parents:
            if not self.dry_run:
                cat, _ = ExpenseCategory.objects.update_or_create(
                    name=item["nome"],
                    defaults={
                        "description": item.get("descricao", ""),
                        "color": item.get("cor", "#6B7280"),
                        "parent": None,
                    },
                )
                self.categories[item["nome"]] = cat
            else:
                self.categories[item["nome"]] = None
            self.stats["categories"] += 1
            print(f"  + {item['nome']}")

        # Segundo passo: criar subcategorias (parent != null)
        for item in children:
            parent = self._get_category(item["parent"])
            if not self.dry_run:
                cat, _ = ExpenseCategory.objects.update_or_create(
                    name=item["nome"],
                    defaults={
                        "description": item.get("descricao", ""),
                        "color": item.get("cor", "#6B7280"),
                        "parent": parent,
                    },
                )
                self.categories[item["nome"]] = cat
            else:
                self.categories[item["nome"]] = None
            self.stats["categories"] += 1
            print(f"  + {item['parent']} > {item['nome']}")

    def _import_persons(self):
        items = self.data.get("pessoas", [])
        if not items:
            return

        print(f"\n[3/15] Pessoas ({len(items)})...")
        for item in items:
            if not self.dry_run:
                person, _ = Person.objects.update_or_create(
                    name=item["nome"],
                    defaults={
                        "relationship": item.get("relacao", ""),
                        "phone": item.get("telefone", ""),
                        "email": item.get("email", ""),
                        "is_owner": item.get("is_owner", False),
                        "is_employee": item.get("is_employee", False),
                        "notes": item.get("notas", ""),
                    },
                )
                self.persons[item["nome"]] = person
            else:
                self.persons[item["nome"]] = None
            self.stats["persons"] += 1
            flags = []
            if item.get("is_owner"):
                flags.append("owner")
            if item.get("is_employee"):
                flags.append("employee")
            flag_str = f" ({', '.join(flags)})" if flags else ""
            print(f"  + {item['nome']} - {item.get('relacao', '')}{flag_str}")

    def _import_credit_cards(self):
        items = self.data.get("cartoes", [])
        if not items:
            return

        print(f"\n[4/15] Cartões de crédito ({len(items)})...")
        for item in items:
            person = self._get_person(item["pessoa"])
            key = f"{item['pessoa']}|{item['apelido']}"
            if not self.dry_run:
                card, _ = CreditCard.objects.update_or_create(
                    person=person,
                    nickname=item["apelido"],
                    defaults={
                        "last_four_digits": item.get("ultimos_4_digitos", ""),
                        "closing_day": item["dia_fechamento"],
                        "due_day": item["dia_vencimento"],
                        "is_active": item.get("ativo", True),
                    },
                )
                self.cards[key] = card
            else:
                self.cards[key] = None
            self.stats["credit_cards"] += 1
            print(f"  + {item['apelido']} ({item['pessoa']}) - vence dia {item['dia_vencimento']}")

    def _import_person_incomes(self):
        section = self.data.get("recebimentos_pessoas", {})

        apt_items = section.get("por_apartamento", [])
        stipend_items = section.get("estipendio_fixo", [])
        total = len(apt_items) + len(stipend_items)
        if total == 0:
            return

        print(f"\n[5/15] Recebimentos de pessoas ({total})...")

        for item in apt_items:
            person = self._get_person(item["pessoa"])
            apt = self._get_apartment(item["predio_street_number"], item["apartamento_number"])
            if not self.dry_run:
                PersonIncome.objects.update_or_create(
                    person=person,
                    income_type="apartment_rent",
                    apartment=apt,
                    defaults={
                        "start_date": self._require_date(item["data_inicio"], "data_inicio", f"recebimento {item['pessoa']}"),
                        "end_date": self._parse_date(item.get("data_fim")),
                        "is_active": True,
                        "notes": item.get("notas", ""),
                    },
                )
            self.stats["person_incomes"] += 1
            print(f"  + {item['pessoa']} <- apto {item['apartamento_number']}/{item['predio_street_number']}")

        for item in stipend_items:
            person = self._get_person(item["pessoa"])
            if not self.dry_run:
                PersonIncome.objects.update_or_create(
                    person=person,
                    income_type="fixed_stipend",
                    defaults={
                        "fixed_amount": Decimal(str(item["valor"])),
                        "start_date": self._require_date(item["data_inicio"], "data_inicio", f"estipêndio {item['pessoa']}"),
                        "end_date": self._parse_date(item.get("data_fim")),
                        "is_active": True,
                        "notes": item.get("notas", ""),
                    },
                )
            self.stats["person_incomes"] += 1
            print(f"  + {item['pessoa']} <- R$ {item['valor']}/mês (estipêndio)")

    def _import_apartment_owners(self):
        section = self.data.get("proprietarios_apartamentos", {})
        items = section.get("vinculos", [])
        if not items:
            return

        print(f"\n[6/15] Proprietários de apartamentos ({len(items)})...")
        for item in items:
            person = self._get_person(item["pessoa"])
            apt = self._get_apartment(item["predio_street_number"], item["apartamento_number"])
            if not self.dry_run:
                apt.owner = person
                apt.save(update_fields=["owner"])
            self.stats["apartment_owners"] += 1
            print(f"  + Apto {item['apartamento_number']}/{item['predio_street_number']} -> {item['pessoa']}")

    def _import_vacant_apartments(self):
        section = self.data.get("kitnets_desalugados", {})
        items = section.get("items", [])
        if not items:
            return

        print(f"\n[6b/15] Kitnets desalugados ({len(items)})...")
        for item in items:
            apt = self._get_apartment(item["predio_street_number"], item["apartamento_number"])
            if not self.dry_run:
                apt.is_rented = False
                apt.save(update_fields=["is_rented"])
                # Desativar lease se existir
                try:
                    lease = Lease.objects.get(apartment=apt)
                    lease.delete()
                    print(f"  - Apto {item['apartamento_number']}/{item['predio_street_number']}: is_rented=False, lease removido")
                except Lease.DoesNotExist:
                    print(f"  - Apto {item['apartamento_number']}/{item['predio_street_number']}: is_rented=False (sem lease)")
            else:
                print(f"  - Apto {item['apartamento_number']}/{item['predio_street_number']}: is_rented=False")

    def _import_lease_specials(self):
        section = self.data.get("leases_especiais", {})
        prepaid = section.get("prepaid", [])
        salary = section.get("salary_offset", [])
        total = len(prepaid) + len(salary)
        if total == 0:
            return

        print(f"\n[7/15] Leases especiais ({total})...")

        for item in prepaid:
            lease = self._get_lease(item["predio_street_number"], item["apartamento_number"])
            if not self.dry_run:
                lease.prepaid_until = self._parse_date(item["prepaid_until"])
                lease.save(update_fields=["prepaid_until"])
            self.stats["lease_updates"] += 1
            print(f"  + Apto {item['apartamento_number']}/{item['predio_street_number']} prepaid até {item['prepaid_until']}")

        for item in salary:
            lease = self._get_lease(item["predio_street_number"], item["apartamento_number"])
            if not self.dry_run:
                lease.is_salary_offset = True
                lease.save(update_fields=["is_salary_offset"])
            self.stats["lease_updates"] += 1
            print(f"  + Apto {item['apartamento_number']}/{item['predio_street_number']} salary_offset=True")

    def _create_expense_with_installments(
        self,
        description: str,
        expense_type: str,
        total_amount: Decimal,
        installment_amount: Decimal,
        current_installment: int,
        total_installments: int,
        expense_date: date,
        due_day: int,
        next_installment_date: date | None = None,
        person=None,
        credit_card=None,
        building=None,
        category=None,
        is_debt_installment: bool = False,
        bank_name: str = "",
        interest_rate=None,
        notes: str = "",
    ) -> tuple[int, int]:
        """Cria uma Expense e gera todas as ExpenseInstallments.

        Parcelas antes da parcela_atual são marcadas como pagas.
        Parcelas a partir da parcela_atual são pendentes.

        Para datas das parcelas:
        - Se next_installment_date é fornecido: usa como âncora da parcela_atual
          e calcula as demais a partir dela (para trás e para frente)
        - Senão: calcula a partir de expense_date + due_day (data de compra)

        Returns:
            tuple(expenses_created, installments_created)
        """
        if total_installments <= 1:
            # Despesa única (sem parcelas)
            is_paid = current_installment > total_installments
            if not self.dry_run:
                Expense.objects.create(
                    description=description,
                    expense_type=expense_type,
                    total_amount=total_amount,
                    expense_date=expense_date,
                    person=person,
                    credit_card=credit_card,
                    building=building,
                    category=category,
                    is_installment=False,
                    is_debt_installment=is_debt_installment,
                    is_paid=is_paid,
                    paid_date=expense_date if is_paid else None,
                    bank_name=bank_name,
                    interest_rate=interest_rate,
                    notes=notes,
                )
            return 1, 0

        # Despesa parcelada
        expense = None
        if not self.dry_run:
            expense = Expense.objects.create(
                description=description,
                expense_type=expense_type,
                total_amount=total_amount,
                expense_date=expense_date,
                person=person,
                credit_card=credit_card,
                building=building,
                category=category,
                is_installment=True,
                total_installments=total_installments,
                is_debt_installment=is_debt_installment,
                is_paid=False,
                bank_name=bank_name,
                interest_rate=interest_rate,
                notes=notes,
            )

        installment_count = 0

        if next_installment_date:
            if current_installment <= 0:
                # Parcelas ainda não começaram.
                # data_proxima_parcela = data da 1ª parcela.
                # parcela_atual negativa indica meses extras de carência:
                #   0 = 1ª parcela no próximo vencimento
                #  -1 = 1ª parcela em 2 vencimentos (60 dias)
                #  -2 = 1ª parcela em 3 vencimentos (90 dias)
                months_offset = abs(current_installment)
                first_due = self._add_months(next_installment_date, months_offset)
            else:
                # Âncora: data_proxima_parcela é a data de vencimento da parcela_atual
                # Calcular data da parcela 1 retroativamente
                months_back = current_installment - 1
                first_due = self._add_months(next_installment_date, -months_back)
        else:
            # Calcular a partir da data de compra
            first_due = self._calculate_first_due_date(expense_date, due_day)

        for i in range(1, total_installments + 1):
            # Data de vencimento: first_due + (i-1) meses
            due_date = self._add_months(first_due, i - 1)
            is_paid = i < current_installment
            paid_date = due_date if is_paid else None

            if not self.dry_run and expense is not None:
                ExpenseInstallment.objects.create(
                    expense=expense,
                    installment_number=i,
                    total_installments=total_installments,
                    amount=installment_amount,
                    due_date=due_date,
                    is_paid=is_paid,
                    paid_date=paid_date,
                )
            installment_count += 1

        return 1, installment_count

    def _calculate_first_due_date(self, expense_date: date, due_day: int) -> date:
        """Calcula a data da primeira parcela."""
        # Se a compra foi antes do dia de vencimento no mesmo mês,
        # a primeira parcela é no mês seguinte.
        # Se foi depois, a primeira parcela é em 2 meses.
        next_month = self._add_months(date(expense_date.year, expense_date.month, 1), 1)
        try:
            return next_month.replace(day=due_day)
        except ValueError:
            # Mês não tem esse dia (ex: 31 em fevereiro)
            last_day = (self._add_months(next_month, 1) - timedelta(days=1)).day
            return next_month.replace(day=min(due_day, last_day))

    @staticmethod
    def _add_months(source_date: date, months: int) -> date:
        """Adiciona N meses a uma data."""
        month = source_date.month - 1 + months
        year = source_date.year + month // 12
        month = month % 12 + 1
        day = min(source_date.day, [31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28,
                                     31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1])
        return date(year, month, day)

    def _import_card_purchases(self):
        section = self.data.get("compras_cartao", {})
        items = section.get("items", [])
        if not items:
            return

        # Filtrar comentários (entradas com _comentario são marcadores visuais)
        items = [i for i in items if "_comentario" not in i]
        print(f"\n[8/15] Compras no cartão ({len(items)})...")
        for item in items:
            person = self._get_person(item["pessoa"])
            card = self._get_card(item["pessoa"], item["cartao"])
            category = self._get_category(item.get("categoria"))
            total_amount = Decimal(str(item["valor_parcela"])) * item["total_parcelas"]
            next_date = self._parse_date(item.get("data_proxima_parcela"))
            due_day = card.due_day if not self.dry_run else item.get("dia_vencimento", 10)

            # expense_date: usa data_compra se disponível, senão retroderiva da data_proxima_parcela
            expense_date = self._parse_date(item.get("data_compra"))
            if not expense_date and next_date:
                expense_date = self._add_months(next_date, -(item["parcela_atual"]))
            elif not expense_date:
                raise ValueError(f"Compra '{item['descricao']}': informe data_compra ou data_proxima_parcela.")

            expenses, installments = self._create_expense_with_installments(
                description=item["descricao"],
                expense_type="card_purchase",
                total_amount=total_amount,
                installment_amount=Decimal(str(item["valor_parcela"])),
                current_installment=item["parcela_atual"],
                total_installments=item["total_parcelas"],
                expense_date=expense_date,
                due_day=due_day,
                next_installment_date=next_date,
                person=person,
                credit_card=card,
                category=category,
                notes=item.get("notas", ""),
            )
            self.stats["expenses"] += expenses
            self.stats["installments"] += installments

            parcela_info = f"{item['parcela_atual']}/{item['total_parcelas']}" if item["total_parcelas"] > 1 else "à vista"
            print(f"  + {item['descricao']} ({item['cartao']}) R$ {item['valor_parcela']} x {parcela_info}")

    def _import_bank_loans(self):
        section = self.data.get("emprestimos_bancarios", {})
        items = section.get("items", [])
        if not items:
            return

        print(f"\n[9/15] Empréstimos bancários ({len(items)})...")
        for item in items:
            person = self._get_person(item["pessoa"])
            category = self._get_category(item.get("categoria"))
            next_date = self._parse_date(item.get("data_proxima_parcela"))
            total_amount = Decimal(str(item["valor_parcela"])) * item["total_parcelas"]

            expense_date = self._parse_date(item.get("data_inicio"))
            if not expense_date and next_date:
                expense_date = self._add_months(next_date, -(item["parcela_atual"]))
            elif not expense_date:
                raise ValueError(f"Empréstimo '{item['descricao']}': informe data_inicio ou data_proxima_parcela.")

            expenses, installments = self._create_expense_with_installments(
                description=item["descricao"],
                expense_type="bank_loan",
                total_amount=total_amount,
                installment_amount=Decimal(str(item["valor_parcela"])),
                current_installment=item["parcela_atual"],
                total_installments=item["total_parcelas"],
                expense_date=expense_date,
                due_day=item["dia_vencimento"],
                next_installment_date=next_date,
                person=person,
                category=category,
                bank_name=item.get("banco", ""),
                interest_rate=Decimal(str(item["taxa_juros"])) if item.get("taxa_juros") else None,
                notes=item.get("notas", ""),
            )
            self.stats["expenses"] += expenses
            self.stats["installments"] += installments

            parcela_info = f"{item['parcela_atual']}/{item['total_parcelas']}"
            print(f"  + {item['descricao']} ({item['pessoa']}) R$ {item['valor_parcela']} x {parcela_info}")

    def _import_personal_loans(self):
        section = self.data.get("emprestimos_pessoais", {})
        items = section.get("items", [])
        if not items:
            return

        print(f"\n[10/15] Empréstimos pessoais ({len(items)})...")
        for item in items:
            person = self._get_person(item["pessoa"])
            category = self._get_category(item.get("categoria"))
            next_date = self._parse_date(item.get("data_proxima_parcela"))
            total_amount = Decimal(str(item["valor_parcela"])) * item["total_parcelas"]

            expense_date = self._parse_date(item.get("data_inicio"))
            if not expense_date and next_date:
                expense_date = self._add_months(next_date, -(item["parcela_atual"]))
            elif not expense_date:
                raise ValueError(f"Empréstimo '{item['descricao']}': informe data_inicio ou data_proxima_parcela.")

            expenses, installments = self._create_expense_with_installments(
                description=item["descricao"],
                expense_type="personal_loan",
                total_amount=total_amount,
                installment_amount=Decimal(str(item["valor_parcela"])),
                current_installment=item["parcela_atual"],
                total_installments=item["total_parcelas"],
                expense_date=expense_date,
                due_day=item["dia_vencimento"],
                next_installment_date=next_date,
                person=person,
                category=category,
                notes=item.get("notas", ""),
            )
            self.stats["expenses"] += expenses
            self.stats["installments"] += installments

            parcela_info = f"{item['parcela_atual']}/{item['total_parcelas']}" if item["total_parcelas"] > 1 else "único"
            print(f"  + {item['descricao']} ({item['pessoa']}) R$ {item['valor_parcela']} x {parcela_info}")

    def _import_offsets(self):
        section = self.data.get("descontos", {})
        items = section.get("items", [])
        if not items:
            return

        print(f"\n[10b/15] Descontos/offsets ({len(items)})...")
        for item in items:
            person = self._get_person(item["pessoa"])
            category = self._get_category(item.get("categoria"))
            next_date = self._parse_date(item.get("data_proxima_parcela"))
            total_amount = Decimal(str(item["valor_parcela"])) * item["total_parcelas"]

            expense_date = self._parse_date(item.get("data_inicio"))
            if not expense_date and next_date:
                expense_date = self._add_months(next_date, -(item["parcela_atual"]))
            elif not expense_date:
                raise ValueError(f"Desconto '{item['descricao']}': informe data_inicio ou data_proxima_parcela.")

            if not self.dry_run:
                expense = Expense.objects.create(
                    description=f"[DESCONTO] {item['descricao']}",
                    expense_type="personal_loan",
                    total_amount=total_amount,
                    expense_date=expense_date,
                    person=person,
                    category=category,
                    is_installment=item["total_parcelas"] > 1,
                    total_installments=item["total_parcelas"] if item["total_parcelas"] > 1 else None,
                    is_offset=True,
                    is_paid=False,
                    notes=item.get("notas", ""),
                )

                if item["total_parcelas"] > 1:
                    if next_date and item["parcela_atual"] <= 0:
                        months_offset = abs(item["parcela_atual"])
                        first_due = self._add_months(next_date, months_offset)
                    elif next_date:
                        months_back = item["parcela_atual"] - 1
                        first_due = self._add_months(next_date, -months_back)
                    else:
                        first_due = self._calculate_first_due_date(expense_date, item["dia_vencimento"])

                    for i in range(1, item["total_parcelas"] + 1):
                        due_date = self._add_months(first_due, i - 1)
                        is_paid = i < item["parcela_atual"]
                        ExpenseInstallment.objects.create(
                            expense=expense,
                            installment_number=i,
                            total_installments=item["total_parcelas"],
                            amount=Decimal(str(item["valor_parcela"])),
                            due_date=due_date,
                            is_paid=is_paid,
                            paid_date=due_date if is_paid else None,
                        )
                        self.stats["installments"] += 1

            self.stats["expenses"] += 1
            parcela_info = f"{item['parcela_atual']}/{item['total_parcelas']}" if item["total_parcelas"] > 1 else "único"
            print(f"  - [DESCONTO] {item['descricao']} ({item['pessoa']}) R$ {item['valor_parcela']} x {parcela_info}")

    def _import_utility_bills(self):
        section = self.data.get("contas_consumo", {})
        agua = section.get("agua", [])
        luz = section.get("luz", [])
        total = len(agua) + len(luz)
        if total == 0:
            return

        print(f"\n[11/15] Contas de consumo ({total} prédios)...")

        for bill_type, items, type_name in [("water_bill", agua, "Água"), ("electricity_bill", luz, "Luz")]:
            for item in items:
                if item.get("suspensa"):
                    print(f"  ~ {type_name} - Prédio {item['predio_street_number']}: SUSPENSA (ignorada)")
                    continue

                building = self._get_building(item["predio_street_number"])
                historico = item.get("historico_mensal", [])
                parcelamento_ref = item.get("parcelamento")
                notes = item.get("notas", "")
                if parcelamento_ref:
                    notes = f"[PARCELAMENTO_INCLUSO:{parcelamento_ref}] {notes}".strip()

                identificador = item.get("identificador", "")
                label = f"{type_name} - Prédio {item['predio_street_number']}"
                if identificador:
                    label = f"{type_name} - {identificador}"

                for entry in historico:
                    if not self.dry_run:
                        Expense.objects.create(
                            description=f"{label} - {entry['mes'][:7]}",
                            expense_type=bill_type,
                            total_amount=Decimal(str(entry["valor"])),
                            expense_date=self._require_date(entry["mes"], "mes", f"{type_name} prédio {item['predio_street_number']}"),
                            building=building,
                            is_installment=False,
                            is_paid=entry.get("pago", False),
                            paid_date=self._parse_date(entry.get("data_pagamento")),
                            notes=notes,
                        )
                    self.stats["expenses"] += 1

                parcelamento_info = f" (inclui parcelamento: {parcelamento_ref})" if parcelamento_ref else ""
                print(f"  + {type_name} - Prédio {item['predio_street_number']}: {len(historico)} meses{parcelamento_info}")

    def _import_debt_installments(self):
        section = self.data.get("parcelamentos_divida", {})
        items = section.get("items", [])
        if not items:
            return

        print(f"\n[12/15] Parcelamentos de dívida ({len(items)})...")
        for item in items:
            building = self._get_building(item["predio_street_number"])
            category = self._get_category(item.get("categoria"))
            parcelas_det = item.get("parcelas_detalhadas")

            if parcelas_det:
                total_amount = Decimal(str(item.get("saldo") or item.get("valor_total_divida") or sum(p["valor"] for p in parcelas_det)))
                expense_date = self._parse_date(item.get("data_inicio")) or date.fromisoformat(parcelas_det[0]["vencimento"])
                real_total = max(p["numero"] for p in parcelas_det)

                if not self.dry_run:
                    expense = Expense.objects.create(
                        description=item["descricao"],
                        expense_type=item["tipo"],
                        total_amount=total_amount,
                        expense_date=expense_date,
                        building=building,
                        category=category,
                        is_installment=True,
                        total_installments=real_total,
                        is_debt_installment=True,
                        is_paid=False,
                        notes=item.get("notas", ""),
                    )

                    for p in parcelas_det:
                        ExpenseInstallment.objects.create(
                            expense=expense,
                            installment_number=p["numero"],
                            total_installments=real_total,
                            amount=Decimal(str(p["valor"])),
                            due_date=date.fromisoformat(p["vencimento"]),
                            is_paid=p.get("pago", False),
                            paid_date=date.fromisoformat(p["data_pagamento"]) if p.get("data_pagamento") else None,
                        )
                        self.stats["installments"] += 1

                self.stats["expenses"] += 1
                pagas = sum(1 for p in parcelas_det if p.get("pago"))
                print(f"  + {item['descricao']} {len(parcelas_det)} parcelas variáveis ({pagas} pagas)")
            else:
                next_date = self._parse_date(item.get("data_proxima_parcela"))
                expense_date = self._parse_date(item.get("data_inicio"))
                if not expense_date and next_date:
                    expense_date = self._add_months(next_date, -(item["parcela_atual"]))
                elif not expense_date:
                    raise ValueError(f"Parcelamento '{item['descricao']}': informe data_inicio ou data_proxima_parcela.")

                expenses, installments = self._create_expense_with_installments(
                    description=item["descricao"],
                    expense_type=item["tipo"],
                    total_amount=Decimal(str(item.get("saldo") or item.get("valor_total_divida") or item["valor_parcela"] * item["total_parcelas"])),
                    installment_amount=Decimal(str(item["valor_parcela"])),
                    current_installment=item["parcela_atual"],
                    total_installments=item["total_parcelas"],
                    expense_date=expense_date,
                    due_day=item["dia_vencimento"],
                    next_installment_date=next_date,
                    building=building,
                    category=category,
                    is_debt_installment=True,
                    notes=item.get("notas", ""),
                )
                self.stats["expenses"] += expenses
                self.stats["installments"] += installments

                parcela_info = f"{item['parcela_atual']}/{item['total_parcelas']}"
                print(f"  + {item['descricao']} R$ {item['valor_parcela']} x {parcela_info}")

    def _import_iptu(self):
        section = self.data.get("iptu", {})
        anual = section.get("anual", [])
        divida = section.get("divida", [])
        total = len(anual) + len(divida)
        if total == 0:
            return

        print(f"\n[13/15] IPTU ({total})...")

        for item in anual:
            building = self._get_building(item["predio_street_number"])

            expenses, installments = self._create_expense_with_installments(
                description=item["descricao"],
                expense_type="property_tax",
                total_amount=Decimal(str(item.get("valor_total") or item["valor_parcela"] * item["total_parcelas"])),
                installment_amount=Decimal(str(item["valor_parcela"])),
                current_installment=item["parcela_atual"],
                total_installments=item["total_parcelas"],
                expense_date=self._require_date(
                    item["data_primeira_parcela"], "data_primeira_parcela", item["descricao"]
                ),
                due_day=item["dia_vencimento"],
                building=building,
                notes=item.get("notas", ""),
            )
            self.stats["expenses"] += expenses
            self.stats["installments"] += installments

            parcela_info = f"{item['parcela_atual']}/{item['total_parcelas']}"
            print(f"  + {item['descricao']} R$ {item['valor_parcela']} x {parcela_info}")

        for item in divida:
            if item.get("suspensa"):
                print(f"  ~ {item['descricao']}: SUSPENSA (ignorada)")
                continue

            building = self._get_building(item["predio_street_number"])
            category = self._get_category(item.get("categoria"))
            parcelas_det = item.get("parcelas_detalhadas")

            if parcelas_det:
                # Parcelas com valores variáveis — criar manualmente
                total_amount = Decimal(str(item.get("saldo") or item.get("valor_total_divida") or sum(p["valor"] for p in parcelas_det)))
                expense_date = self._require_date(item["data_inicio"], "data_inicio", item["descricao"])
                real_total = max(p["numero"] for p in parcelas_det)

                if not self.dry_run:
                    expense = Expense.objects.create(
                        description=item["descricao"],
                        expense_type="property_tax",
                        total_amount=total_amount,
                        expense_date=expense_date,
                        building=building,
                        category=category,
                        is_installment=True,
                        total_installments=real_total,
                        is_debt_installment=True,
                        is_paid=False,
                        notes=item.get("notas", ""),
                    )

                    for p in parcelas_det:
                        ExpenseInstallment.objects.create(
                            expense=expense,
                            installment_number=p["numero"],
                            total_installments=real_total,
                            amount=Decimal(str(p["valor"])),
                            due_date=date.fromisoformat(p["vencimento"]),
                            is_paid=p.get("pago", False),
                            paid_date=date.fromisoformat(p["data_pagamento"]) if p.get("data_pagamento") else None,
                        )
                        self.stats["installments"] += 1

                self.stats["expenses"] += 1
                pagas = sum(1 for p in parcelas_det if p.get("pago"))
                print(f"  + {item['descricao']} (dívida) {len(parcelas_det)} parcelas variáveis ({pagas} pagas)")
            else:
                # Parcelas com valor fixo — usar método padrão
                expenses, installments = self._create_expense_with_installments(
                    description=item["descricao"],
                    expense_type="property_tax",
                    total_amount=Decimal(str(item.get("saldo") or item.get("valor_total_divida") or item["valor_parcela"] * item["total_parcelas"])),
                    installment_amount=Decimal(str(item["valor_parcela"])),
                    current_installment=item["parcela_atual"],
                    total_installments=item["total_parcelas"],
                    expense_date=self._require_date(item["data_inicio"], "data_inicio", item["descricao"]),
                    due_day=item["dia_vencimento"],
                    building=building,
                    category=category,
                    is_debt_installment=True,
                    notes=item.get("notas", ""),
                )
                self.stats["expenses"] += expenses
                self.stats["installments"] += installments

                parcela_info = f"{item['parcela_atual']}/{item['total_parcelas']}"
                print(f"  + {item['descricao']} (dívida) R$ {item['valor_parcela']} x {parcela_info}")

    def _import_fixed_expenses(self):
        section = self.data.get("gastos_fixos", {})
        items = section.get("items", [])
        if not items:
            return

        print(f"\n[14/15] Gastos fixos recorrentes ({len(items)})...")
        for item in items:
            building = self._get_building(item["predio_street_number"]) if item.get("predio_street_number") else None
            category = self._get_category(item.get("categoria"))
            person = self._get_person(item["pessoa"]) if item.get("pessoa") else None

            if not self.dry_run:
                Expense.objects.create(
                    description=item["descricao"],
                    expense_type="fixed_expense",
                    total_amount=Decimal(str(item["valor_mensal"])),
                    expense_date=self._require_date(item["data_inicio"], "data_inicio", item["descricao"]),
                    person=person,
                    building=building,
                    category=category,
                    is_installment=False,
                    is_recurring=True,
                    expected_monthly_amount=Decimal(str(item["valor_mensal"])),
                    recurrence_day=item.get("dia_vencimento"),
                    is_paid=False,
                    notes=item.get("notas", ""),
                )
            self.stats["expenses"] += 1

            local = f" - Prédio {item['predio_street_number']}" if item.get("predio_street_number") else ""
            print(f"  + {item['descricao']}{local} R$ {item['valor_mensal']}/mês")

    def _import_one_time_expenses(self):
        section = self.data.get("gastos_unicos", {})
        items = section.get("items", [])
        if not items:
            return

        print(f"\n[15a/15] Gastos únicos ({len(items)})...")
        for item in items:
            person = self._get_person(item["pessoa"]) if item.get("pessoa") else None
            card = self._get_card(item["pessoa"], item["cartao"]) if item.get("pessoa") and item.get("cartao") else None
            building = self._get_building(item["predio_street_number"]) if item.get("predio_street_number") else None
            category = self._get_category(item.get("categoria"))

            if not self.dry_run:
                Expense.objects.create(
                    description=item["descricao"],
                    expense_type="one_time_expense",
                    total_amount=Decimal(str(item["valor"])),
                    expense_date=self._require_date(item["data"], "data", item["descricao"]),
                    person=person,
                    credit_card=card,
                    building=building,
                    category=category,
                    is_installment=False,
                    is_paid=item.get("pago", False),
                    paid_date=self._parse_date(item.get("data_pagamento")),
                    notes=item.get("notas", ""),
                )
            self.stats["expenses"] += 1
            print(f"  + {item['descricao']} R$ {item['valor']} em {item['data']}")

    def _import_extra_incomes(self):
        section = self.data.get("receitas_extras", {})
        recorrentes = section.get("recorrentes", [])
        avulsas = section.get("avulsas", [])
        total = len(recorrentes) + len(avulsas)
        if total == 0:
            return

        print(f"\n[15b/15] Receitas extras ({total})...")

        for item in recorrentes:
            person = self._get_person(item["pessoa"]) if item.get("pessoa") else None
            if not self.dry_run:
                Income.objects.create(
                    description=item["descricao"],
                    amount=Decimal(str(item["valor_mensal"])),
                    income_date=self._require_date(item["data_inicio"], "data_inicio", item["descricao"]),
                    person=person,
                    is_recurring=True,
                    expected_monthly_amount=Decimal(str(item["valor_mensal"])),
                    is_received=False,
                    notes=item.get("notas", ""),
                )
            self.stats["incomes"] += 1
            print(f"  + {item['descricao']} R$ {item['valor_mensal']}/mês (recorrente)")

        for item in avulsas:
            person = self._get_person(item["pessoa"]) if item.get("pessoa") else None
            building = self._get_building(item["predio_street_number"]) if item.get("predio_street_number") else None
            if not self.dry_run:
                Income.objects.create(
                    description=item["descricao"],
                    amount=Decimal(str(item["valor"])),
                    income_date=self._require_date(item["data"], "data", item["descricao"]),
                    person=person,
                    building=building,
                    is_recurring=False,
                    is_received=item.get("recebido", False),
                    received_date=self._parse_date(item.get("data_recebimento")),
                    notes=item.get("notas", ""),
                )
            self.stats["incomes"] += 1
            print(f"  + {item['descricao']} R$ {item['valor']} em {item['data']}")

    def _import_rent_payments(self):
        section = self.data.get("pagamentos_aluguel", {})
        items = section.get("items", [])
        if not items:
            return

        print(f"\n[15c/15] Pagamentos de aluguel ({len(items)})...")
        for item in items:
            lease = self._get_lease(item["predio_street_number"], item["apartamento_number"])
            if not self.dry_run:
                RentPayment.objects.update_or_create(
                    lease=lease,
                    reference_month=self._require_date(item["mes_referencia"], "mes_referencia", f"aluguel apto {item['apartamento_number']}"),
                    defaults={
                        "amount_paid": Decimal(str(item["valor_pago"])),
                        "payment_date": self._require_date(item["data_pagamento"], "data_pagamento", f"aluguel apto {item['apartamento_number']}"),
                        "notes": item.get("notas", ""),
                    },
                )
            self.stats["rent_payments"] += 1
            print(f"  + Apto {item['apartamento_number']}/{item['predio_street_number']} - {item['mes_referencia'][:7]} R$ {item['valor_pago']}")

    def _import_employee_payments(self):
        section = self.data.get("pagamentos_funcionaria", {})
        items = section.get("items", [])
        if not items:
            return

        print(f"\n[15d/15] Pagamentos funcionária ({len(items)})...")
        for item in items:
            person = self._get_person(item["pessoa"])
            if not self.dry_run:
                EmployeePayment.objects.update_or_create(
                    person=person,
                    reference_month=self._require_date(item["mes_referencia"], "mes_referencia", f"pagamento {item['pessoa']}"),
                    defaults={
                        "base_salary": Decimal(str(item["salario_base"])),
                        "variable_amount": Decimal(str(item.get("valor_variavel", 0))),
                        "rent_offset": Decimal(str(item.get("rent_offset", 0))),
                        "cleaning_count": item.get("qtd_faxinas", 0),
                        "is_paid": item.get("pago", False),
                        "payment_date": self._parse_date(item.get("data_pagamento")),
                        "notes": item.get("notas", ""),
                    },
                )
            self.stats["employee_payments"] += 1

            total = Decimal(str(item["salario_base"])) + Decimal(str(item.get("valor_variavel", 0)))
            print(f"  + {item['pessoa']} - {item['mes_referencia'][:7]} R$ {total}")

    def _import_person_payments(self):
        section = self.data.get("pagamentos_pessoas", {})
        items = section.get("items", [])
        if not items:
            return

        print(f"\n[15e/15] Pagamentos a pessoas ({len(items)})...")
        for item in items:
            person = self._get_person(item["pessoa"])
            if not self.dry_run:
                PersonPayment.objects.create(
                    person=person,
                    reference_month=self._require_date(
                        item["mes_referencia"], "mes_referencia", f"pagamento {item['pessoa']}"
                    ),
                    amount=Decimal(str(item["valor"])),
                    payment_date=self._require_date(
                        item["data_pagamento"], "data_pagamento", f"pagamento {item['pessoa']}"
                    ),
                    notes=item.get("notas", ""),
                )
            self.stats["person_payments"] = self.stats.get("person_payments", 0) + 1
            print(f"  + R$ {item['valor']} a {item['pessoa']} - {item['mes_referencia'][:7]}")


def clear_financial_data():
    """Remove todos os dados financeiros (não afeta Buildings/Apartments/Leases/Tenants)."""
    print("\nLimpando dados financeiros existentes...")
    models_to_clear = [
        ExpenseInstallment,
        Expense,
        EmployeePayment,
        PersonPayment,
        RentPayment,
        Income,
        PersonIncome,
        CreditCard,
        Person,
        ExpenseCategory,
    ]
    for model in models_to_clear:
        count = model.objects.with_deleted().count()
        if count > 0:
            model.objects.with_deleted().delete()
            print(f"  Removidos {count} {model.__name__}")

    # FinancialSettings não tem SoftDelete
    FinancialSettings.objects.all().delete()

    # Limpa owner dos apartamentos
    Apartment.objects.filter(owner__isnull=False).update(owner=None)

    # Limpa campos especiais dos leases
    Lease.objects.filter(prepaid_until__isnull=False).update(prepaid_until=None)
    Lease.objects.filter(is_salary_offset=True).update(is_salary_offset=False)

    print("  Dados financeiros removidos com sucesso.")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Importa dados financeiros a partir de JSON.")
    parser.add_argument("file", nargs="?", default="scripts/data/financial_data.json", help="Arquivo JSON de dados")
    parser.add_argument("--dry-run", action="store_true", help="Simula sem gravar no banco")
    parser.add_argument("--clear-first", action="store_true", help="Limpa dados financeiros antes de importar")
    args = parser.parse_args()

    # Resolve path relativo ao projeto
    project_root = Path(__file__).resolve().parent.parent
    json_path = project_root / args.file

    if not json_path.exists():
        print(f"Arquivo não encontrado: {json_path}")
        print(f"\nCopie o template e preencha com seus dados:")
        print(f"  cp scripts/data/financial_data_template.json scripts/data/financial_data.json")
        sys.exit(1)

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if args.clear_first:
        if args.dry_run:
            print("[DRY RUN] Pulando limpeza de dados.")
        else:
            confirm = input("Tem certeza que deseja limpar TODOS os dados financeiros? (s/N): ")
            if confirm.lower() != "s":
                print("Cancelado.")
                sys.exit(0)
            clear_financial_data()

    importer = FinancialDataImporter(data, dry_run=args.dry_run)

    if args.dry_run:
        importer.run()
    else:
        with transaction.atomic():
            importer.run()


if __name__ == "__main__":
    main()
