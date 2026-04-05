import django,os,sys,json,decimal,datetime
os.environ['DJANGO_SETTINGS_MODULE']='condominios_manager.settings'
sys.path.insert(0,'.')
django.setup()
from core.models import *
from django.db.models import Sum, Count, Q, F
from django.db.models.functions import TruncMonth
class E(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal): return str(o)
        if isinstance(o, (datetime.date, datetime.datetime)): return o.isoformat()
        return super().default(o)
d = {}

# 1. Parcelas nao pagas por mes (proximo 6 meses) - agrupado por pessoa e mes
from datetime import date
today = date.today()
from dateutil.relativedelta import relativedelta
six_months = today + relativedelta(months=6)
unpaid = ExpenseInstallment.objects.filter(is_paid=False, due_date__lte=six_months).select_related('expense','expense__person','expense__credit_card')
d['unpaid_by_person_month'] = list(
    unpaid.values('expense__person__name').annotate(
        total=Sum('amount'), count=Count('id')
    ).order_by('expense__person__name')
)
# 2. Parcelas por mes - proximos 6 meses detalhado
months_data = {}
for m in range(0, 7):
    d_start = today.replace(day=1) + relativedelta(months=m)
    d_end = d_start + relativedelta(months=1)
    key = f"{d_start.year}-{d_start.month:02d}"
    installments = ExpenseInstallment.objects.filter(
        is_paid=False, due_date__gte=d_start, due_date__lt=d_end
    ).select_related('expense','expense__person','expense__credit_card')
    by_person = list(installments.values('expense__person__name').annotate(
        total=Sum('amount'), count=Count('id')
    ).order_by('-total'))
    by_card = list(installments.values('expense__credit_card__nickname').annotate(
        total=Sum('amount'), count=Count('id')
    ).order_by('-total'))
    detail = list(installments.order_by('due_date').values(
        'expense__description','expense__person__name','expense__credit_card__nickname',
        'installment_number','total_installments','amount','due_date'
    ))
    months_data[key] = {'by_person': by_person, 'by_card': by_card, 'detail': detail}
d['monthly_installments'] = months_data
# 3. Despesas fixas/recorrentes ativas
d['recurring_expenses'] = list(Expense.objects.filter(
    is_recurring=True, is_offset=False
).values('id','description','expected_monthly_amount','recurrence_day','person__name',
         'credit_card__nickname','category__name','expense_type','end_date').order_by('-expected_monthly_amount'))

# 4. Despesas com parcelas ativas (is_installment=True, com parcelas nao pagas)
active_installment_expenses = Expense.objects.filter(
    is_installment=True, installments__is_paid=False
).distinct().values(
    'id','description','total_amount','expense_date','total_installments',
    'person__name','credit_card__nickname','category__name','expense_type',
    'is_offset','is_debt_installment','notes'
).order_by('person__name','description')
d['active_installment_expenses'] = list(active_installment_expenses)

# 5. Employee payments - todos
d['all_employee_payments'] = list(EmployeePayment.objects.all().order_by('-reference_month').values(
    'id','person__name','reference_month','base_salary','variable_amount',
    'rent_offset','cleaning_count','payment_date','is_paid','notes'
))

# 6. Person incomes (rendas das pessoas - como Camila)
d['all_person_incomes'] = list(PersonIncome.objects.all().values(
    'id','person__name','income_type','apartment__number','apartment__building__street_number',
    'fixed_amount','start_date','end_date','is_active','notes'
))

# 7. Person payments - todos
d['all_person_payments'] = list(PersonPayment.objects.all().order_by('-payment_date').values(
    'id','person__name','reference_month','amount','payment_date','notes'
))
# 8. Todas as incomes
d['all_incomes'] = list(Income.objects.all().order_by('-income_date').values(
    'id','description','amount','income_date','person__name','building__street_number',
    'category__name','is_recurring','expected_monthly_amount','is_received','received_date','notes'
))

# 9. Rent payments - todos
d['all_rent_payments'] = list(RentPayment.objects.all().select_related('lease','lease__apartment','lease__apartment__building').order_by('-reference_month').values(
    'id','lease__apartment__number','lease__apartment__building__street_number',
    'reference_month','amount_paid','payment_date','notes'
))

# 10. Despesas offset (descontos)
d['offset_expenses'] = list(Expense.objects.filter(is_offset=True).values(
    'id','description','total_amount','expense_date','person__name','category__name',
    'is_installment','total_installments','notes'
))

# 11. Todas as despesas nao-parcela, nao-recorrente, nao-offset (one-time)
d['onetime_expenses'] = list(Expense.objects.filter(
    is_installment=False, is_recurring=False, is_offset=False
).order_by('-expense_date').values(
    'id','description','total_amount','expense_date','expense_type',
    'person__name','credit_card__nickname','category__name','building__street_number','notes'
))

# 12. Leases with prepaid info
d['leases_prepaid'] = list(Lease.objects.filter(
    apartment__is_rented=True
).select_related('apartment','apartment__building').values(
    'id','apartment__number','apartment__building__street_number',
    'rental_value','start_date','prepaid_until','is_salary_offset'
).order_by('apartment__building__street_number','apartment__number'))

print(json.dumps(d, cls=E, indent=2, ensure_ascii=False))
