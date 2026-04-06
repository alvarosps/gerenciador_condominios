# Person Payment Scheduling & Daily Control Enhancements

**Date:** 2026-03-28
**Status:** Approved
**Approach:** A — Normalized models (PersonPaymentSchedule + ExpenseMonthSkip)

## Problem

The daily financial control currently shows individual person expenses (card installments, loans, fixed expenses) as separate entries. In practice, the admin pays each person a consolidated amount on specific dates throughout the month. There is no way to:

1. Configure payment dates and amounts per person per month
2. See aggregated person payments in the daily control
3. Track partial/early payments with automatic sync
4. Skip expenses that won't be charged in a specific month
5. Properly handle utility bill due dates in the daily control

## Design Decisions

- **Manual monthly configuration** — payment schedules are configured per person per month (not percentages or recurring rules)
- **Fallback behavior** — if a person has no schedule for a month, their expenses appear individually (current behavior)
- **Utility bills (water/electricity/IPTU)** — remain separate entries tied to buildings, not grouped into person payments. If paid by a person, they are added manually as person expenses
- **Offsets (is_offset=True)** — used only to calculate the net total due, do not appear in daily control
- **Skip applies to any expense type** — persisted in the database per expense per month
- **Schedule amounts can exceed total due** — with user confirmation

## New Models

### PersonPaymentSchedule

```python
class PersonPaymentSchedule(AuditMixin, SoftDeleteMixin, models.Model):
    person = models.ForeignKey(Person, on_delete=models.CASCADE, related_name="payment_schedules")
    reference_month = models.DateField()       # first day of month: date(2026, 3, 1)
    due_day = models.PositiveSmallIntegerField()  # payment due day (1-31, capped to last day of month)
    amount = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        ordering = ["reference_month", "due_day"]
        constraints = [
            models.UniqueConstraint(
                fields=["person", "reference_month", "due_day"],
                condition=models.Q(is_deleted=False),
                name="unique_person_schedule_per_day",
            )
        ]
```

- One record per payment date per person per month
- `due_day` capped to last day of month (same pattern as `recurrence_day`)
- Sum of amounts may exceed total due (with frontend confirmation)
- Inherits AuditMixin + SoftDeleteMixin (consistent with all project models)

### ExpenseMonthSkip

```python
class ExpenseMonthSkip(AuditMixin, models.Model):
    expense = models.ForeignKey(Expense, on_delete=models.CASCADE, related_name="month_skips")
    reference_month = models.DateField()       # first day of month

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["expense", "reference_month"],
                name="unique_expense_skip_per_month",
            )
        ]
```

- No SoftDeleteMixin — simple create/delete toggle
- Any expense type can be skipped
- Daily control and person total calculations exclude skipped expenses

## Person Total Calculation

```
total_due = sum of all person expenses in the month
          - sum of offsets (is_offset=True)
          - excluding expenses with ExpenseMonthSkip for the month
```

Expenses considered:
- `ExpenseInstallment` with `due_date` in month, where `expense.person = person` and `expense.is_offset=False`
- `Expense` with `is_recurring=True` and `recurrence_day`, where `person = person` and `is_offset=False`
- `Expense` one-time with `expense_date` in month, where `person = person` and `is_offset=False`
- Offsets: summed separately and subtracted

## Daily Control Behavior

### Person WITH schedule in the month

- Individual person expenses are **replaced** by aggregated entries
- Each `PersonPaymentSchedule` becomes one entry in the daily control:
  - Description: person name
  - Amount: scheduled amount
  - Type: `"person_schedule"`
  - Status calculated dynamically:

```
total_paid_until_date = sum(PersonPayment.amount)
    where person=person, reference_month=month, payment_date <= schedule_date

total_expected_until_date = sum(PersonPaymentSchedule.amount)
    where person=person, reference_month=month, due_day <= schedule_day

paid = total_paid_until_date >= total_expected_until_date
```

### Person WITHOUT schedule in the month

- Current behavior maintained — individual expenses appear as separate entries

### Skipped expenses

- Excluded from daily control entirely
- Excluded from person total calculations

## Mark as Paid Flow (Person Schedule)

1. Admin clicks "Pay" on aggregated person entry
2. Frontend fetches current totals via `person_month_total` endpoint
3. Modal opens with:
   - Suggested amount: `max(0, expected_until_date - already_paid)`
   - Editable field
   - Context: "Expected until this date: R$X | Already paid: R$Y | Suggested: R$Z"
4. Admin confirms (or edits amount)
5. Creates `PersonPayment` with confirmed amount and `payment_date`
6. Invalidates queries: daily-control, cash-flow, financial-dashboard

### Example: Rodrigo, R$10.000, March 2026

Schedule: Day 5 = R$4.000, Day 27 = R$5.000, Day 31 = R$1.000

**Normal flow:**
- Day 5: pay R$4.000 → PersonPayment(4000). Total paid: 4.000. Day 5 ✅
- Day 27: pay R$5.000 → PersonPayment(5000). Total paid: 9.000. Day 27 ✅
- Day 31: pay R$1.000 → PersonPayment(1000). Total paid: 10.000. All ✅

**Early payment:**
- Day 1: pay R$1.000 → Total paid: 1.000
- Day 5: click pay → suggested: max(0, 4.000 - 1.000) = R$3.000. Pay R$3.000. Total: 4.000. Day 5 ✅
- Day 20: pay R$6.000 → Total paid: 10.000. Day 27 ✅ (10.000 ≥ 9.000), Day 31 ✅ (10.000 ≥ 10.000)

## API Endpoints

### New Endpoints

**PersonPaymentSchedule CRUD:**
- `GET /api/person-payment-schedules/?person_id=X&reference_month=2026-03-01`
- `POST /api/person-payment-schedules/`
- `PUT /api/person-payment-schedules/{id}/`
- `DELETE /api/person-payment-schedules/{id}/`

**Bulk configuration (replace entire month):**
- `POST /api/person-payment-schedules/bulk_configure/`
  - Body: `{ person_id, reference_month, entries: [{due_day, amount}] }`
  - Soft-deletes existing schedules for person/month, creates new ones
  - Returns: `{ total_configured, total_due, schedules: [...] }`

**Person month total (for frontend configuration UI):**
- `GET /api/person-payment-schedules/person_month_total/?person_id=X&reference_month=2026-03-01`
  - Returns: `{ total_due, total_offsets, net_total, total_scheduled, total_paid, pending }`

**ExpenseMonthSkip:**
- `POST /api/expense-month-skips/` — create skip `{ expense_id, reference_month }`
- `DELETE /api/expense-month-skips/{id}/` — remove skip
- `GET /api/expense-month-skips/?reference_month=2026-03-01` — list skips for month

### Modified Endpoints

**Daily Control:**
- `GET /api/daily-control/breakdown/` — persons with schedule show aggregated entries; skipped expenses excluded
- `POST /api/daily-control/mark_paid/` — new `item_type: "person_schedule"` with `{ person_id, reference_month, amount, payment_date }`

## Frontend Changes

### Expense with Persons Page — New "Payment Schedule" Section

Located in `/financial/expenses/` (or dedicated tab):

1. **Selectors**: Person (dropdown) + Month (navigator)
2. **Summary card**: Total due, offsets, net total, total configured, total paid
3. **Editable table**: `day | amount | actions (edit/remove)`
4. **"Add date" button**: Inserts new row
5. **Validation**: If sum > net total, show confirmation dialog before saving
6. **"Save configuration" button**: Calls `bulk_configure`

### Daily Control — Changes

**Aggregated person entries:**
- Distinct icon (User icon) to differentiate from regular expenses
- Shows: person name, scheduled amount, status (paid/pending)
- Progress badge: "R$4.000 / R$10.000 paid this month"
- "Pay" button opens modal with suggested value, editable, context info

**Expense skip:**
- Skip button (SkipForward icon) on eligible expenses in timeline
- Confirmation dialog: "Don't charge [expense] in [month]?"
- Skipped expenses disappear from timeline

### Individual Expense Page — Changes

- "Don't charge this month" toggle with month selector
- List of skipped months (if any), with option to remove skip

## Impact on Existing Features

### Cash Flow / Person Summary
- `get_person_summary()` must respect `ExpenseMonthSkip`
- `get_monthly_expenses()` must exclude skipped expenses

### Financial Dashboard
- `get_overview()` must exclude skipped expenses from current month
- `get_dashboard_summary()` must exclude skipped expenses

### Daily Control Summary
- `get_month_summary()` for persons with schedule:
  - `total_expected_expenses` uses sum of schedules (not individual expenses)
  - `total_paid_expenses` uses sum of PersonPayments
  - Avoids double-counting: individual person expenses with schedule excluded from totals

### Cache Invalidation
- New signals for `PersonPaymentSchedule` and `ExpenseMonthSkip`
- Invalidate: `daily-control`, `cash-flow`, `financial-dashboard`
- Verify `PersonPayment` signal invalidates `daily-control`

### Serializers
- New serializers following dual pattern (nested read, `_id` write):
  - `PersonPaymentScheduleSerializer`
  - `ExpenseMonthSkipSerializer`
- `ExpenseSerializer` — add read-only `month_skips` field

### Migrations
- `0030_person_payment_schedule.py`
- `0031_expense_month_skip.py`
