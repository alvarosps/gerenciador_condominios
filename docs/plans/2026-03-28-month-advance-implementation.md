# Month Advance System — Plano de Implementação (Gerenciador de Condomínios)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implementar um sistema de avanço de mês que cria snapshots financeiros, valida obrigações, pré-cria registros mensais, protege meses finalizados, ancora o controle diário com saldo real, e usa snapshots para projeções históricas.

**Architecture:** Django service layer + novo modelo MonthSnapshot + MonthAdvanceService. Reutiliza o CashFlowService existente para cálculos. Integra com DailyControlService (saldo acumulado) e CashFlowProjection (meses históricos). Segue os padrões do projeto (AuditMixin, SoftDeleteMixin, service pattern).

**Tech Stack:** Django 5.2, Django REST Framework, PostgreSQL, pytest, Next.js 14

**Reference:** [Spec completa](./2026-03-28-month-advance-system-spec.md)

---

## Recomendações de Design

### O que o avanço de mês DEVE fazer

1. **Criar MonthSnapshot** — congelar receitas, despesas, saldo, breakdown detalhado (usando CashFlowService), **incluindo saldo acumulado final** (`cumulative_ending_balance`)
2. **Validar obrigações** — alertar sobre aluguéis não recebidos, parcelas não pagas, contas não registradas, funcionários não pagos
3. **Pré-criar registros do próximo mês:**
   - `EmployeePayment` para cada funcionário (copiando base_salary do mês anterior)
   - `PersonPaymentSchedule` para cada pessoa com schedule ativo (carry forward)
   - **NÃO** criar RentPayment (o pagamento é registrado quando efetivamente recebido)
4. **Proteger mês finalizado** — impedir edições em dados de meses já fechados (soft lock via middleware/serializer)
5. **Informar** — retornar preview do próximo mês (parcelas vencendo, aluguéis esperados, contas manuais necessárias)
6. **Ancorar controle diário** — o snapshot armazena `cumulative_ending_balance` que serve como ponto de partida para o `cumulative_balance` do controle diário do mês seguinte (resolve o problema de sempre começar em R$ 0,00)
7. **Alimentar projeções históricas** — meses finalizados usam dados do snapshot em vez de recalcular on-demand (dados congelados, imutáveis), garantindo que edições retroativas não alterem o histórico

### O que o avanço NÃO faz

- **NÃO muta parcelas** — ExpenseInstallments já têm due_dates fixas
- **NÃO muta despesas recorrentes** — projetadas on-demand via recurrence_day
- **NÃO incrementa currentInstallment** — não existe esse conceito aqui
- **NÃO cria despesas de água/luz** — devem ser adicionadas manualmente (sistema alerta)

### Rollback

Trivial: deletar MonthSnapshot + registros auto-criados do próximo mês. Nenhum dado original foi mutado.

---

## Phase Overview

| Phase | Name                                                              | Tasks                                                        |
| ----- | ----------------------------------------------------------------- | ------------------------------------------------------------ |
| 1     | [Modelo + Migration](#phase-1-modelo--migration)                  | MonthSnapshot model com cumulative_ending_balance, migration |
| 2     | [MonthAdvanceService](#phase-2-monthadvanceservice)               | Validação, snapshot, pré-criação, preview                    |
| 3     | [API Endpoints](#phase-3-api-endpoints)                           | ViewSet com advance, rollback, status, snapshots             |
| 4     | [Proteção de Mês Finalizado](#phase-4-proteção-de-mês-finalizado) | Serializer/view guards contra edição                         |
| 5     | [Integração Controle Diário](#phase-5-integração-controle-diário) | DailyControlService usa snapshot como saldo inicial          |
| 6     | [Integração Projeções](#phase-6-integração-projeções)             | CashFlowProjection usa snapshots para meses históricos       |
| 7     | [Testes](#phase-7-testes)                                         | Unit + integration tests                                     |
| 8     | [Frontend](#phase-8-frontend)                                     | Página de avanço de mês, status, histórico                   |

---

## Phase 1: Modelo + Migration

### Task 1.1: Criar modelo MonthSnapshot

**Files:**

- Modify: `core/models.py`
- Create: Migration via `python manage.py makemigrations`

- [ ] **Step 1: Adicionar o modelo ao final de core/models.py**

```python
class MonthSnapshot(AuditMixin, models.Model):
    """
    Snapshot imutável do estado financeiro de um mês finalizado.
    Criado pelo MonthAdvanceService quando o mês é "fechado".
    """

    reference_month = models.DateField(
        help_text="Primeiro dia do mês de referência (ex: 2026-03-01)"
    )

    # === Receitas ===
    total_rent_income = models.DecimalField(
        max_digits=12, decimal_places=2, default=0
    )
    total_extra_income = models.DecimalField(
        max_digits=12, decimal_places=2, default=0
    )
    total_person_payments_received = models.DecimalField(
        max_digits=12, decimal_places=2, default=0
    )
    total_income = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # === Despesas ===
    total_card_installments = models.DecimalField(
        max_digits=12, decimal_places=2, default=0
    )
    total_loan_installments = models.DecimalField(
        max_digits=12, decimal_places=2, default=0
    )
    total_utility_bills = models.DecimalField(
        max_digits=12, decimal_places=2, default=0
    )
    total_fixed_expenses = models.DecimalField(
        max_digits=12, decimal_places=2, default=0
    )
    total_one_time_expenses = models.DecimalField(
        max_digits=12, decimal_places=2, default=0
    )
    total_employee_salary = models.DecimalField(
        max_digits=12, decimal_places=2, default=0
    )
    total_owner_repayments = models.DecimalField(
        max_digits=12, decimal_places=2, default=0
    )
    total_person_stipends = models.DecimalField(
        max_digits=12, decimal_places=2, default=0
    )
    total_debt_installments = models.DecimalField(
        max_digits=12, decimal_places=2, default=0
    )
    total_property_tax = models.DecimalField(
        max_digits=12, decimal_places=2, default=0
    )
    total_expenses = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # === Saldo ===
    net_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    cumulative_ending_balance = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        help_text="Saldo acumulado ao final do mês (snapshot anterior + net_balance deste mês). "
                  "Serve como ponto de partida para o controle diário do mês seguinte.",
    )

    # === Detalhamento ===
    detailed_breakdown = models.JSONField(
        default=dict,
        help_text="Breakdown completo por categoria com itens individuais",
    )

    # === Status ===
    is_finalized = models.BooleanField(
        default=False, help_text="True quando o mês está oficialmente fechado"
    )
    finalized_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-reference_month"]
        constraints = [
            models.UniqueConstraint(
                fields=["reference_month"],
                name="unique_month_snapshot",
            )
        ]

    def __str__(self):
        status = "Finalizado" if self.is_finalized else "Aberto"
        return f"Snapshot {self.reference_month.strftime('%m/%Y')} ({status})"
```

- [ ] **Step 2: Criar migration**

```bash
python manage.py makemigrations core --name month_snapshot
```

- [ ] **Step 3: Aplicar migration**

```bash
python manage.py migrate
```

- [ ] **Step 4: Verificar**

```bash
python manage.py shell -c "from core.models import MonthSnapshot; print(MonthSnapshot._meta.db_table)"
```

- [ ] **Step 5: Commit**

```bash
git add core/models.py core/migrations/
git commit -m "feat: add MonthSnapshot model for month advance system"
```

---

## Phase 2: MonthAdvanceService

### Task 2.1: Criar o service

**Files:**

- Create: `core/services/month_advance_service.py`

- [ ] **Step 1: Criar o service**

```python
"""
Service for advancing financial months.

Handles: validation, snapshot creation, pre-creation of next month records,
and rollback of month advancement.
"""

from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from django.db import transaction
from django.utils import timezone

from core.models import (
    EmployeePayment,
    Expense,
    ExpenseInstallment,
    Lease,
    MonthSnapshot,
    PersonPayment,
    PersonPaymentSchedule,
    RentPayment,
)
from core.services.cash_flow_service import CashFlowService


class MonthAdvanceService:
    """Orchestrates month advancement: validate → snapshot → prepare next month."""

    def __init__(self):
        self.cash_flow_service = CashFlowService()

    # ──────────────────────────────────────────────
    # PUBLIC API
    # ──────────────────────────────────────────────

    def get_status(self, year: int, month: int) -> dict[str, Any]:
        """Check current status of a month: finalized? validation warnings?"""
        reference_month = date(year, month, 1)
        snapshot = MonthSnapshot.objects.filter(
            reference_month=reference_month
        ).first()

        validation = self._validate_month(year, month)

        return {
            "year": year,
            "month": month,
            "is_finalized": snapshot.is_finalized if snapshot else False,
            "snapshot_id": snapshot.pk if snapshot else None,
            "validation": validation,
        }

    def advance_month(
        self, year: int, month: int, *, force: bool = False, notes: str = ""
    ) -> dict[str, Any]:
        """
        Advance (close) a month: validate, create snapshot, prepare next month.

        Args:
            year: Year to close
            month: Month to close (1-12)
            force: If True, proceed despite validation warnings
            notes: Optional notes to attach to the snapshot

        Returns:
            Dict with snapshot data, warnings, and next month preview
        """
        reference_month = date(year, month, 1)

        # Check idempotency
        existing = MonthSnapshot.objects.filter(
            reference_month=reference_month, is_finalized=True
        ).first()
        if existing:
            raise ValueError(
                f"Mês {month:02d}/{year} já foi finalizado. "
                f"Use rollback primeiro se precisar reprocessar."
            )

        # Check chronological order
        self._validate_chronological_order(reference_month)

        # Validate
        validation = self._validate_month(year, month)
        warnings = self._extract_warnings(validation)

        if warnings and not force:
            raise ValueError(
                f"Validação falhou com {len(warnings)} aviso(s). "
                f"Use force=True para prosseguir. Avisos: {'; '.join(warnings)}"
            )

        # Execute in transaction
        with transaction.atomic():
            # Phase 1: Create snapshot
            snapshot = self._create_snapshot(year, month, warnings, notes)

            # Phase 2: Pre-create next month records
            next_month_info = self._prepare_next_month(year, month)

            # Phase 3: Finalize
            snapshot.is_finalized = True
            snapshot.finalized_at = timezone.now()
            snapshot.save()

        return {
            "success": True,
            "snapshot_id": snapshot.pk,
            "reference_month": str(reference_month),
            "warnings": warnings,
            "summary": {
                "total_income": float(snapshot.total_income),
                "total_expenses": float(snapshot.total_expenses),
                "net_balance": float(snapshot.net_balance),
            },
            "next_month_preview": next_month_info,
        }

    def rollback_month(
        self, year: int, month: int, *, confirm: bool = False
    ) -> dict[str, Any]:
        """
        Rollback a finalized month. Deletes snapshot and auto-created records.

        Args:
            year: Year to rollback
            month: Month to rollback
            confirm: Must be True to proceed (destructive operation)
        """
        if not confirm:
            raise ValueError("Rollback requer confirm=True (operação destrutiva)")

        reference_month = date(year, month, 1)

        # Verify this is the last finalized month
        latest = (
            MonthSnapshot.objects.filter(is_finalized=True)
            .order_by("-reference_month")
            .first()
        )
        if not latest or latest.reference_month != reference_month:
            raise ValueError(
                "Só é possível reverter o último mês finalizado. "
                f"Último mês: {latest.reference_month if latest else 'nenhum'}"
            )

        with transaction.atomic():
            # Calculate next month for cleanup
            next_month = self._next_month_date(reference_month)

            # Delete auto-created EmployeePayments for next month
            # (only those not yet paid — don't delete if user already edited)
            emp_deleted, _ = EmployeePayment.objects.filter(
                reference_month=next_month, is_paid=False
            ).delete()

            # Delete auto-created PersonPaymentSchedules for next month
            # Only if they match carried-forward patterns
            schedules_deleted, _ = PersonPaymentSchedule.objects.filter(
                reference_month=next_month
            ).delete()

            # Delete the snapshot
            snapshot = MonthSnapshot.objects.get(reference_month=reference_month)
            snapshot_id = snapshot.pk
            snapshot.delete(hard_delete=True)

        return {
            "success": True,
            "rolled_back_month": str(reference_month),
            "details": {
                "snapshot_deleted": True,
                "employee_payments_deleted": emp_deleted,
                "schedules_deleted": schedules_deleted,
            },
        }

    def get_next_month_preview(self, year: int, month: int) -> dict[str, Any]:
        """Preview what the next month will look like without advancing."""
        next_date = self._next_month_date(date(year, month, 1))
        return self._build_next_month_preview(next_date.year, next_date.month)

    # ──────────────────────────────────────────────
    # VALIDATION
    # ──────────────────────────────────────────────

    def _validate_month(self, year: int, month: int) -> dict[str, Any]:
        """Validate all obligations for a month."""
        month_start = date(year, month, 1)
        next_month = self._next_month_date(month_start)

        return {
            "unpaid_rent": self._check_unpaid_rent(month_start),
            "unpaid_installments": self._check_unpaid_installments(
                month_start, next_month
            ),
            "unpaid_employees": self._check_unpaid_employees(month_start),
            "missing_utility_bills": self._check_missing_utility_bills(
                month_start, next_month
            ),
            "unpaid_person_schedules": self._check_unpaid_person_schedules(
                month_start
            ),
        }

    def _check_unpaid_rent(self, month_start: date) -> list[dict]:
        """Check for active leases without RentPayment for this month."""
        active_leases = Lease.objects.filter(
            is_deleted=False,
            apartment__is_rented=True,
            apartment__owner__isnull=True,
        ).exclude(
            prepaid_until__gte=month_start
        ).exclude(
            is_salary_offset=True
        ).select_related("apartment", "apartment__building", "responsible_tenant")

        unpaid = []
        for lease in active_leases:
            has_payment = RentPayment.objects.filter(
                lease=lease, reference_month=month_start, is_deleted=False
            ).exists()
            if not has_payment:
                unpaid.append({
                    "lease_id": lease.pk,
                    "apartment": f"{lease.apartment.number}/{lease.apartment.building.street_number}",
                    "tenant": lease.responsible_tenant.name,
                    "rental_value": float(lease.rental_value),
                })
        return unpaid

    def _check_unpaid_installments(
        self, month_start: date, next_month: date
    ) -> list[dict]:
        """Check for unpaid installments due this month."""
        unpaid = ExpenseInstallment.objects.filter(
            due_date__gte=month_start,
            due_date__lt=next_month,
            is_paid=False,
            is_deleted=False,
            expense__is_deleted=False,
            expense__is_offset=False,
        ).select_related("expense", "expense__person", "expense__credit_card")

        return [
            {
                "installment_id": inst.pk,
                "description": inst.expense.description,
                "person": inst.expense.person.name if inst.expense.person else None,
                "amount": float(inst.amount),
                "due_date": str(inst.due_date),
                "installment": f"{inst.installment_number}/{inst.total_installments}",
            }
            for inst in unpaid
        ]

    def _check_unpaid_employees(self, month_start: date) -> list[dict]:
        """Check for employees without EmployeePayment for this month."""
        from core.models import Person

        employees = Person.objects.filter(
            is_employee=True, is_deleted=False
        )

        unpaid = []
        for emp in employees:
            payment = EmployeePayment.objects.filter(
                person=emp, reference_month=month_start, is_deleted=False
            ).first()
            if not payment:
                unpaid.append({
                    "person_id": emp.pk,
                    "name": emp.name,
                    "status": "not_created",
                })
            elif not payment.is_paid:
                unpaid.append({
                    "person_id": emp.pk,
                    "name": emp.name,
                    "status": "not_paid",
                    "amount": float(payment.total_paid),
                })
        return unpaid

    def _check_missing_utility_bills(
        self, month_start: date, next_month: date
    ) -> list[dict]:
        """Check if water/electricity bills exist for this month."""
        missing = []
        for bill_type, label in [
            ("water_bill", "Conta de Água"),
            ("electricity_bill", "Conta de Luz"),
        ]:
            exists = Expense.objects.filter(
                expense_type=bill_type,
                expense_date__gte=month_start,
                expense_date__lt=next_month,
                is_deleted=False,
            ).exists()
            if not exists:
                missing.append({"type": bill_type, "label": label})
        return missing

    def _check_unpaid_person_schedules(self, month_start: date) -> list[dict]:
        """Check PersonPaymentSchedule entries without corresponding PersonPayment."""
        schedules = PersonPaymentSchedule.objects.filter(
            reference_month=month_start, is_deleted=False
        ).select_related("person")

        unpaid = []
        for schedule in schedules:
            payments = PersonPayment.objects.filter(
                person=schedule.person,
                reference_month=month_start,
                is_deleted=False,
            )
            total_paid = sum(p.amount for p in payments)
            if total_paid < schedule.amount:
                unpaid.append({
                    "person_id": schedule.person.pk,
                    "person_name": schedule.person.name,
                    "expected": float(schedule.amount),
                    "paid": float(total_paid),
                    "remaining": float(schedule.amount - total_paid),
                })
        return unpaid

    def _extract_warnings(self, validation: dict) -> list[str]:
        """Convert validation results into human-readable warnings."""
        warnings = []

        for rent in validation["unpaid_rent"]:
            warnings.append(
                f"Aluguel não recebido: {rent['apartment']} ({rent['tenant']}) - R${rent['rental_value']:.2f}"
            )

        for inst in validation["unpaid_installments"]:
            warnings.append(
                f"Parcela não paga: {inst['description']} {inst['installment']} - R${inst['amount']:.2f}"
            )

        for emp in validation["unpaid_employees"]:
            status = (
                "não criado" if emp["status"] == "not_created" else "não pago"
            )
            warnings.append(f"Funcionário {status}: {emp['name']}")

        for bill in validation["missing_utility_bills"]:
            warnings.append(f"{bill['label']} não registrada para o mês")

        for schedule in validation["unpaid_person_schedules"]:
            warnings.append(
                f"Pagamento programado pendente: {schedule['person_name']} "
                f"- Falta R${schedule['remaining']:.2f}"
            )

        return warnings

    # ──────────────────────────────────────────────
    # SNAPSHOT CREATION
    # ──────────────────────────────────────────────

    def _create_snapshot(
        self, year: int, month: int, warnings: list[str], notes: str
    ) -> MonthSnapshot:
        """Create MonthSnapshot using CashFlowService data."""
        cash_flow = self.cash_flow_service.get_monthly_cash_flow(year, month)

        income = cash_flow["income"]
        expenses = cash_flow["expenses"]

        # Calculate person payments received
        month_start = date(year, month, 1)
        person_payments = PersonPayment.objects.filter(
            reference_month=month_start, is_deleted=False
        )
        total_person_payments = sum(p.amount for p in person_payments)

        # Build detailed breakdown
        breakdown = {
            "rent_details": income.get("rent_details", []),
            "extra_income_details": income.get("extra_income_details", []),
            "card_installments": expenses.get("card_installments_details", []),
            "loan_installments": expenses.get("loan_installments_details", []),
            "utility_bills": expenses.get("utility_bills_details", []),
            "debt_installments": expenses.get("debt_installments_details", []),
            "property_tax": expenses.get("property_tax_details", []),
            "employee_salaries": expenses.get("employee_salary_details", []),
            "fixed_expenses": expenses.get("fixed_expenses_details", []),
            "one_time_expenses": expenses.get("one_time_expenses_details", []),
            "owner_repayments": expenses.get("owner_repayments_details", []),
            "person_stipends": expenses.get("person_stipends_details", []),
            "person_payments": [
                {
                    "person_id": p.person_id,
                    "person_name": p.person.name,
                    "amount": float(p.amount),
                    "payment_date": str(p.payment_date),
                }
                for p in person_payments.select_related("person")
            ],
            "validation_warnings": warnings,
        }

        # Serialize Decimal values in breakdown
        breakdown = self._serialize_breakdown(breakdown)

        snapshot = MonthSnapshot.objects.create(
            reference_month=month_start,
            total_rent_income=income.get("rent_income", 0),
            total_extra_income=income.get("extra_income", 0),
            total_person_payments_received=total_person_payments,
            total_income=income.get("total", 0) + total_person_payments,
            total_card_installments=expenses.get("card_installments", 0),
            total_loan_installments=expenses.get("loan_installments", 0),
            total_utility_bills=expenses.get("utility_bills", 0),
            total_fixed_expenses=expenses.get("fixed_expenses", 0),
            total_one_time_expenses=expenses.get("one_time_expenses", 0),
            total_employee_salary=expenses.get("employee_salary", 0),
            total_owner_repayments=expenses.get("owner_repayments", 0),
            total_person_stipends=expenses.get("person_stipends", 0),
            total_debt_installments=expenses.get("debt_installments", 0),
            total_property_tax=expenses.get("property_tax", 0),
            total_expenses=expenses.get("total", 0),
            net_balance=income.get("total", 0) - expenses.get("total", 0),
            detailed_breakdown=breakdown,
            notes=notes,
        )

        return snapshot

    def _serialize_breakdown(self, data: Any) -> Any:
        """Recursively convert Decimal/date values to JSON-serializable types."""
        if isinstance(data, dict):
            return {k: self._serialize_breakdown(v) for k, v in data.items()}
        if isinstance(data, list):
            return [self._serialize_breakdown(item) for item in data]
        if isinstance(data, Decimal):
            return float(data)
        if isinstance(data, date):
            return str(data)
        return data

    # ──────────────────────────────────────────────
    # NEXT MONTH PREPARATION
    # ──────────────────────────────────────────────

    def _prepare_next_month(self, year: int, month: int) -> dict[str, Any]:
        """Pre-create records for the next month and return preview."""
        current_month = date(year, month, 1)
        next_month = self._next_month_date(current_month)

        created = {
            "employee_payments_created": self._carry_forward_employee_payments(
                current_month, next_month
            ),
            "payment_schedules_created": self._carry_forward_payment_schedules(
                current_month, next_month
            ),
        }

        preview = self._build_next_month_preview(next_month.year, next_month.month)
        preview["auto_created"] = created

        return preview

    def _carry_forward_employee_payments(
        self, current_month: date, next_month: date
    ) -> int:
        """Create EmployeePayment entries for next month based on current month."""
        current_payments = EmployeePayment.objects.filter(
            reference_month=current_month, is_deleted=False
        )

        created = 0
        for payment in current_payments:
            # Don't create if already exists
            exists = EmployeePayment.objects.filter(
                person=payment.person,
                reference_month=next_month,
                is_deleted=False,
            ).exists()
            if not exists:
                EmployeePayment.objects.create(
                    person=payment.person,
                    reference_month=next_month,
                    base_salary=payment.base_salary,
                    variable_amount=Decimal("0"),
                    rent_offset=payment.rent_offset,
                    cleaning_count=0,
                    is_paid=False,
                )
                created += 1
        return created

    def _carry_forward_payment_schedules(
        self, current_month: date, next_month: date
    ) -> int:
        """Carry forward PersonPaymentSchedule entries to next month."""
        current_schedules = PersonPaymentSchedule.objects.filter(
            reference_month=current_month, is_deleted=False
        )

        created = 0
        for schedule in current_schedules:
            exists = PersonPaymentSchedule.objects.filter(
                person=schedule.person,
                reference_month=next_month,
                due_day=schedule.due_day,
                is_deleted=False,
            ).exists()
            if not exists:
                PersonPaymentSchedule.objects.create(
                    person=schedule.person,
                    reference_month=next_month,
                    due_day=schedule.due_day,
                    amount=schedule.amount,
                )
                created += 1
        return created

    def _build_next_month_preview(
        self, year: int, month: int
    ) -> dict[str, Any]:
        """Build a preview of what the next month looks like."""
        month_start = date(year, month, 1)
        next_month = self._next_month_date(month_start)

        # Upcoming installments
        upcoming_installments = ExpenseInstallment.objects.filter(
            due_date__gte=month_start,
            due_date__lt=next_month,
            is_deleted=False,
            expense__is_deleted=False,
            expense__is_offset=False,
        ).select_related("expense").count()

        # Expected rent
        expected_rent_count = Lease.objects.filter(
            is_deleted=False,
            apartment__is_rented=True,
            apartment__owner__isnull=True,
        ).exclude(
            prepaid_until__gte=month_start
        ).exclude(
            is_salary_offset=True
        ).count()

        # Reminders
        reminders = [
            "Adicionar conta de água do mês",
            "Adicionar conta de luz do mês",
        ]

        return {
            "year": year,
            "month": month,
            "upcoming_installments_count": upcoming_installments,
            "expected_rent_count": expected_rent_count,
            "reminders": reminders,
        }

    # ──────────────────────────────────────────────
    # HELPERS
    # ──────────────────────────────────────────────

    def _next_month_date(self, current: date) -> date:
        """Get first day of next month."""
        if current.month == 12:
            return date(current.year + 1, 1, 1)
        return date(current.year, current.month + 1, 1)

    def _validate_chronological_order(self, reference_month: date) -> None:
        """Ensure no gaps: previous month must be finalized."""
        if reference_month.month == 1:
            prev_month = date(reference_month.year - 1, 12, 1)
        else:
            prev_month = date(reference_month.year, reference_month.month - 1, 1)

        # Check if there are ANY finalized months
        any_finalized = MonthSnapshot.objects.filter(is_finalized=True).exists()
        if not any_finalized:
            # First month ever — no predecessor needed
            return

        # If there are finalized months, the previous month must be finalized
        prev_finalized = MonthSnapshot.objects.filter(
            reference_month=prev_month, is_finalized=True
        ).exists()
        if not prev_finalized:
            raise ValueError(
                f"O mês anterior ({prev_month.strftime('%m/%Y')}) não foi finalizado. "
                f"Não é possível pular meses."
            )
```

- [ ] **Step 2: Verificar que não há erros de syntax**

```bash
python -c "from core.services.month_advance_service import MonthAdvanceService; print('OK')"
```

- [ ] **Step 3: Commit**

```bash
git add core/services/month_advance_service.py
git commit -m "feat: add MonthAdvanceService for month advancement pipeline"
```

---

## Phase 3: API Endpoints

### Task 3.1: Criar ViewSet e Serializer

**Files:**

- Create: `core/viewsets/month_advance_views.py`
- Modify: `core/urls.py`

- [ ] **Step 1: Criar o ViewSet**

```python
"""ViewSet for month advancement operations."""

from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response

from core.models import MonthSnapshot
from core.services.month_advance_service import MonthAdvanceService


class MonthSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = MonthSnapshot
        fields = [
            "id",
            "reference_month",
            "total_income",
            "total_expenses",
            "net_balance",
            "total_rent_income",
            "total_extra_income",
            "total_person_payments_received",
            "total_card_installments",
            "total_loan_installments",
            "total_utility_bills",
            "total_fixed_expenses",
            "total_one_time_expenses",
            "total_employee_salary",
            "total_owner_repayments",
            "total_person_stipends",
            "total_debt_installments",
            "total_property_tax",
            "is_finalized",
            "finalized_at",
            "detailed_breakdown",
            "notes",
            "created_at",
        ]
        read_only_fields = fields


class MonthAdvanceViewSet(viewsets.ViewSet):
    """
    Endpoints for month advancement pipeline.

    POST /advance/     — Advance (close) a month
    POST /rollback/    — Rollback the last finalized month
    GET  /status/      — Check month status and validation
    GET  /snapshots/   — List all snapshots
    GET  /snapshots/{year}/{month}/ — Get specific snapshot
    GET  /preview/     — Preview next month without advancing
    """

    permission_classes = [IsAdminUser]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.service = MonthAdvanceService()

    @action(detail=False, methods=["post"])
    def advance(self, request):
        """Advance (close) a month."""
        year = request.data.get("year")
        month = request.data.get("month")
        force = request.data.get("force", False)
        notes = request.data.get("notes", "")

        if not year or not month:
            return Response(
                {"error": "year and month are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = self.service.advance_month(
                int(year), int(month), force=bool(force), notes=str(notes)
            )
            return Response(result, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=["post"])
    def rollback(self, request):
        """Rollback the last finalized month."""
        year = request.data.get("year")
        month = request.data.get("month")
        confirm = request.data.get("confirm", False)

        if not year or not month:
            return Response(
                {"error": "year and month are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = self.service.rollback_month(
                int(year), int(month), confirm=bool(confirm)
            )
            return Response(result, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=["get"])
    def get_status(self, request):
        """Check month status and validation."""
        year = request.query_params.get("year")
        month = request.query_params.get("month")

        if not year or not month:
            return Response(
                {"error": "year and month query params are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = self.service.get_status(int(year), int(month))
        return Response(result)

    @action(detail=False, methods=["get"])
    def snapshots(self, request):
        """List all snapshots, optionally filtered by year."""
        year = request.query_params.get("year")
        qs = MonthSnapshot.objects.all()
        if year:
            qs = qs.filter(reference_month__year=int(year))
        serializer = MonthSnapshotSerializer(qs, many=True)
        return Response(serializer.data)

    @action(
        detail=False,
        methods=["get"],
        url_path="snapshots/(?P<year>[0-9]{4})/(?P<month>[0-9]{1,2})",
    )
    def snapshot_detail(self, request, year=None, month=None):
        """Get specific month snapshot."""
        reference_month = f"{year}-{int(month):02d}-01"
        try:
            snapshot = MonthSnapshot.objects.get(reference_month=reference_month)
        except MonthSnapshot.DoesNotExist:
            return Response(
                {"error": "Snapshot not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = MonthSnapshotSerializer(snapshot)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def preview(self, request):
        """Preview next month without advancing."""
        year = request.query_params.get("year")
        month = request.query_params.get("month")

        if not year or not month:
            return Response(
                {"error": "year and month query params are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = self.service.get_next_month_preview(int(year), int(month))
        return Response(result)
```

- [ ] **Step 2: Registrar nos URLs**

Em `core/urls.py`, adicionar:

```python
from core.viewsets.month_advance_views import MonthAdvanceViewSet

# No router registration ou manualmente:
router.register(r'month-advance', MonthAdvanceViewSet, basename='month-advance')
```

- [ ] **Step 3: Verificar endpoints**

```bash
python manage.py shell -c "from core.urls import router; [print(u.pattern) for u in router.urls if 'month' in str(u.pattern)]"
```

- [ ] **Step 4: Commit**

---

## Phase 4: Proteção de Mês Finalizado

### Task 4.1: Adicionar validação nos serializers financeiros

**Files:**

- Modify: `core/serializers.py` ou serializers relevantes

- [ ] **Step 1: Criar mixin de proteção**

```python
class FinalizedMonthProtectionMixin:
    """Prevents modification of financial data in finalized months."""

    def validate(self, attrs):
        attrs = super().validate(attrs)

        # Determine the reference month from the data
        reference_month = self._get_reference_month(attrs)
        if reference_month is None:
            return attrs

        # Check if month is finalized
        from core.models import MonthSnapshot

        is_finalized = MonthSnapshot.objects.filter(
            reference_month=reference_month, is_finalized=True
        ).exists()

        if is_finalized:
            raise serializers.ValidationError(
                f"O mês {reference_month.strftime('%m/%Y')} está finalizado. "
                f"Use rollback para reabrir antes de editar."
            )

        return attrs

    def _get_reference_month(self, attrs):
        """Override in subclasses to extract the relevant month."""
        return None
```

- [ ] **Step 2: Aplicar nos serializers de RentPayment, EmployeePayment, PersonPayment, ExpenseInstallment**

Para cada serializer que usa `reference_month` ou `due_date`:

- Herdar de `FinalizedMonthProtectionMixin`
- Implementar `_get_reference_month()` extraindo o mês do campo relevante

- [ ] **Step 3: Testes**
- [ ] **Step 4: Commit**

---

## Phase 5: Integração Controle Diário

### Task 5.1: DailyControlService usa snapshot como saldo inicial

**Problem:** O `get_daily_breakdown()` começa `cumulative_balance` em R$ 0,00 a cada mês. Deveria começar do saldo real do mês anterior.

**Files:**

- Modify: `core/services/daily_control_service.py`

- [ ] **Step 1: Modificar get_daily_breakdown para buscar saldo anterior**

No início do método `get_daily_breakdown(year, month)`, antes do loop de dias, adicionar:

```python
from core.models import MonthSnapshot, FinancialSettings

# Determine starting balance for this month
starting_balance = self._get_starting_balance(month_start)

# Use as starting cumulative balance
cumulative_balance = starting_balance  # Was: Decimal("0.00")
```

- [ ] **Step 2: Criar método \_get_starting_balance**

```python
def _get_starting_balance(self, month_start: date) -> Decimal:
    """
    Get the cumulative balance at the START of a month.

    Uses MonthSnapshot.cumulative_ending_balance from the previous month.
    If no previous snapshot exists, falls back to FinancialSettings.initial_balance.
    """
    # Find the most recent finalized snapshot before this month
    previous_snapshot = MonthSnapshot.objects.filter(
        reference_month__lt=month_start,
        is_finalized=True,
    ).order_by('-reference_month').first()

    if previous_snapshot:
        return previous_snapshot.cumulative_ending_balance

    # No previous snapshot — use initial balance from settings
    settings = FinancialSettings.objects.first()
    if settings and settings.initial_balance_date and settings.initial_balance_date <= month_start:
        return settings.initial_balance

    return Decimal("0.00")
```

- [ ] **Step 3: Atualizar get_month_summary para incluir starting_balance**

No `get_month_summary`, incluir no retorno:

```python
{
    # ... campos existentes ...
    "starting_balance": float(self._get_starting_balance(month_start)),
    "ending_balance": float(starting_balance + received_income - paid_expenses),
}
```

- [ ] **Step 4: Testes**

```python
def test_daily_breakdown_starts_from_previous_snapshot(self):
    """When previous month has a finalized snapshot, daily control starts from its ending balance."""
    # Create snapshot for February with cumulative_ending_balance = 5000
    MonthSnapshot.objects.create(
        reference_month=date(2026, 2, 1),
        cumulative_ending_balance=Decimal("5000.00"),
        is_finalized=True,
        # ... other required fields
    )

    # Get March daily breakdown
    service = DailyControlService()
    result = service.get_daily_breakdown(2026, 3)

    # Day 1 with no entries/exits should show cumulative_balance = 5000
    assert result[0]["cumulative_balance"] == 5000.0

def test_daily_breakdown_uses_initial_balance_when_no_snapshot(self):
    """When no snapshot exists, falls back to FinancialSettings.initial_balance."""
    FinancialSettings.objects.update_or_create(
        pk=1, defaults={"initial_balance": Decimal("10000.00"), "initial_balance_date": date(2026, 1, 1)}
    )

    service = DailyControlService()
    result = service.get_daily_breakdown(2026, 3)
    assert result[0]["cumulative_balance"] == 10000.0
```

- [ ] **Step 5: Commit**

---

## Phase 6: Integração Projeções

### Task 6.1: CashFlowProjection usa snapshots para meses históricos

**Problem:** `get_cash_flow_projection()` recalcula meses passados on-demand. Se dados forem editados retroativamente, o histórico muda. Meses finalizados devem usar o snapshot congelado.

**Files:**

- Modify: `core/services/cash_flow_service.py`

- [ ] **Step 1: Modificar get_cash_flow_projection para usar snapshots**

No loop de meses do `get_cash_flow_projection()`, antes de calcular on-demand, verificar se existe snapshot:

```python
from core.models import MonthSnapshot

for i in range(months):
    # ... calculate month_date ...
    month_start = date(proj_year, proj_month, 1)

    # Check if this month has a finalized snapshot
    snapshot = MonthSnapshot.objects.filter(
        reference_month=month_start,
        is_finalized=True,
    ).first()

    if snapshot:
        # Use frozen snapshot data instead of recalculating
        income_total = snapshot.total_income
        expenses_total = snapshot.total_expenses
        balance = snapshot.net_balance
        cumulative_balance = snapshot.cumulative_ending_balance

        projection.append({
            "year": proj_year,
            "month": proj_month,
            "income_total": float(income_total),
            "expenses_total": float(expenses_total),
            "balance": float(balance),
            "cumulative_balance": float(cumulative_balance),
            "is_snapshot": True,  # flag to indicate this is frozen data
            # ... include other details from snapshot.detailed_breakdown
        })
        continue

    # No snapshot — calculate on-demand (existing logic)
    # ... existing calculation code ...
```

- [ ] **Step 2: Atualizar SimulationService para usar snapshots como base**

No `simulation_service.py`, quando building the baseline projection, meses com snapshot devem ser marcados como "locked" — simulações não devem alterar meses passados congelados:

```python
def _apply_scenario(self, projection, scenario):
    for entry in projection:
        if entry.get("is_snapshot"):
            continue  # Don't modify frozen months
        # ... apply scenario changes to future months only ...
```

- [ ] **Step 3: Testes**

```python
def test_projection_uses_snapshot_for_finalized_months(self):
    """Finalized months use snapshot data, not recalculated data."""
    # Create a snapshot for March 2026
    MonthSnapshot.objects.create(
        reference_month=date(2026, 3, 1),
        total_income=Decimal("15000.00"),
        total_expenses=Decimal("12000.00"),
        net_balance=Decimal("3000.00"),
        cumulative_ending_balance=Decimal("8008.00"),
        is_finalized=True,
        detailed_breakdown={},
    )

    service = CashFlowService()
    projection = service.get_cash_flow_projection(months=6)

    # Find March in projection
    march_entry = next(e for e in projection if e["year"] == 2026 and e["month"] == 3)
    assert march_entry["is_snapshot"] is True
    assert march_entry["income_total"] == 15000.0
    assert march_entry["cumulative_balance"] == 8008.0

def test_simulation_does_not_modify_snapshot_months(self):
    """Simulations should not alter data from finalized months."""
    # ... setup snapshot + run simulation ...
    # Verify snapshot month values unchanged
```

- [ ] **Step 4: Commit**

### Task 6.2: Atualizar MonthAdvanceService para calcular cumulative_ending_balance

**Files:**

- Modify: `core/services/month_advance_service.py`

- [ ] **Step 1: Calcular cumulative_ending_balance no \_create_snapshot**

No método `_create_snapshot`, após calcular `net_balance`, buscar o saldo acumulado anterior:

```python
# Calculate cumulative ending balance
previous_snapshot = MonthSnapshot.objects.filter(
    reference_month__lt=month_start,
    is_finalized=True,
).order_by('-reference_month').first()

if previous_snapshot:
    cumulative_starting = previous_snapshot.cumulative_ending_balance
else:
    settings = FinancialSettings.objects.first()
    cumulative_starting = settings.initial_balance if settings else Decimal("0.00")

cumulative_ending = cumulative_starting + net_balance

# Pass to MonthSnapshot.objects.create:
# cumulative_ending_balance=cumulative_ending,
```

- [ ] **Step 2: Commit**

---

## Phase 7: Testes (renumerada)

### Task 5.1: Unit tests do MonthAdvanceService

**Files:**

- Create: `tests/unit/test_month_advance_service.py`

- [ ] **Step 1: Escrever testes**

```python
import pytest
from datetime import date
from decimal import Decimal
from core.models import MonthSnapshot, EmployeePayment, PersonPaymentSchedule
from core.services.month_advance_service import MonthAdvanceService


@pytest.mark.django_db
class TestMonthAdvanceService:
    def setup_method(self):
        self.service = MonthAdvanceService()

    def test_advance_creates_snapshot(self, sample_financial_data):
        result = self.service.advance_month(2026, 3, force=True)
        assert result["success"] is True
        assert MonthSnapshot.objects.filter(
            reference_month=date(2026, 3, 1)
        ).exists()

    def test_advance_idempotent(self, sample_financial_data):
        self.service.advance_month(2026, 3, force=True)
        with pytest.raises(ValueError, match="já foi finalizado"):
            self.service.advance_month(2026, 3, force=True)

    def test_advance_requires_force_with_warnings(self, unpaid_rent_data):
        with pytest.raises(ValueError, match="Validação falhou"):
            self.service.advance_month(2026, 3, force=False)

    def test_advance_with_force_includes_warnings(self, unpaid_rent_data):
        result = self.service.advance_month(2026, 3, force=True)
        assert len(result["warnings"]) > 0

    def test_advance_creates_employee_payments_for_next_month(self, employee_data):
        self.service.advance_month(2026, 3, force=True)
        next_month_payments = EmployeePayment.objects.filter(
            reference_month=date(2026, 4, 1)
        )
        assert next_month_payments.count() > 0

    def test_advance_carries_forward_payment_schedules(self, schedule_data):
        self.service.advance_month(2026, 3, force=True)
        next_schedules = PersonPaymentSchedule.objects.filter(
            reference_month=date(2026, 4, 1)
        )
        assert next_schedules.count() > 0

    def test_rollback_deletes_snapshot(self, sample_financial_data):
        self.service.advance_month(2026, 3, force=True)
        result = self.service.rollback_month(2026, 3, confirm=True)
        assert result["success"] is True
        assert not MonthSnapshot.objects.filter(
            reference_month=date(2026, 3, 1)
        ).exists()

    def test_rollback_requires_confirm(self, sample_financial_data):
        self.service.advance_month(2026, 3, force=True)
        with pytest.raises(ValueError, match="confirm=True"):
            self.service.rollback_month(2026, 3, confirm=False)

    def test_rollback_only_last_month(self, sample_financial_data):
        self.service.advance_month(2026, 3, force=True)
        self.service.advance_month(2026, 4, force=True)
        with pytest.raises(ValueError, match="último mês"):
            self.service.rollback_month(2026, 3, confirm=True)

    def test_chronological_order_enforced(self, sample_financial_data):
        self.service.advance_month(2026, 3, force=True)
        with pytest.raises(ValueError, match="não foi finalizado"):
            self.service.advance_month(2026, 5, force=True)  # Skip April

    def test_status_returns_validation(self):
        result = self.service.get_status(2026, 3)
        assert "validation" in result
        assert "is_finalized" in result

    def test_snapshot_contains_breakdown(self, sample_financial_data):
        self.service.advance_month(2026, 3, force=True)
        snapshot = MonthSnapshot.objects.get(reference_month=date(2026, 3, 1))
        assert "rent_details" in snapshot.detailed_breakdown
        assert "card_installments" in snapshot.detailed_breakdown
        assert "validation_warnings" in snapshot.detailed_breakdown
```

- [ ] **Step 2: Criar fixtures (conftest.py)**
- [ ] **Step 3: Rodar testes**

```bash
pytest tests/unit/test_month_advance_service.py -v
```

- [ ] **Step 4: Commit**

### Task 7.2: Integration tests da API

**Files:**

- Create: `tests/integration/test_month_advance_api.py`

- [ ] Testar endpoints: POST advance, POST rollback, GET status, GET snapshots
- [ ] Testar permissões (apenas admin)
- [ ] Testar proteção de mês finalizado nos serializers
- [ ] Commit

---

## Phase 8: Frontend

### Task 6.1: Página de avanço de mês

**Files:**

- Create: `frontend/app/(dashboard)/financial/month-advance/page.tsx`
- Create: `frontend/lib/api/hooks/useMonthAdvance.ts`

- [ ] **Step 1: Hook de API**

```typescript
// useMonthAdvance.ts
export function useMonthStatus(year: number, month: number) {
  return useQuery({
    queryKey: ["month-advance", "status", year, month],
    queryFn: () =>
      api.get(`/api/month-advance/get_status/?year=${year}&month=${month}`),
  });
}

export function useMonthSnapshots(year?: number) {
  return useQuery({
    queryKey: ["month-advance", "snapshots", year],
    queryFn: () =>
      api.get(`/api/month-advance/snapshots/${year ? `?year=${year}` : ""}`),
  });
}

export function useAdvanceMonth() {
  return useMutation({
    mutationFn: (data: {
      year: number;
      month: number;
      force?: boolean;
      notes?: string;
    }) => api.post("/api/month-advance/advance/", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["month-advance"] });
      toast.success("Mês avançado com sucesso!");
    },
  });
}

export function useRollbackMonth() {
  return useMutation({
    mutationFn: (data: { year: number; month: number; confirm: boolean }) =>
      api.post("/api/month-advance/rollback/", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["month-advance"] });
      toast.success("Mês revertido com sucesso!");
    },
  });
}
```

- [ ] **Step 2: Página com componentes**

A página deve ter:

1. **Status card** — mostra mês atual, se está finalizado, validação
2. **Validation checklist** — lista de itens pendentes (aluguéis, parcelas, contas)
3. **Advance button** — com confirmação e opção force
4. **Snapshot history** — timeline de meses finalizados com totais
5. **Rollback button** — apenas para o último mês, com confirmação dupla

- [ ] **Step 3: Testes frontend**
- [ ] **Step 4: Commit**

---

## Verificação Final

- [ ] `python manage.py test` — todos os testes passam
- [ ] `pytest` — 83%+ coverage mantida
- [ ] Frontend build: `cd frontend && pnpm build`
- [ ] Manual: avançar um mês via API
- [ ] Manual: verificar snapshot contém breakdown completo
- [ ] Manual: verificar EmployeePayments criados para próximo mês
- [ ] Manual: verificar proteção de edição em mês finalizado
- [ ] Manual: rollback do mês e verificar restauração
