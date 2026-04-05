import django, os, sys, json, decimal, datetime
os.environ['DJANGO_SETTINGS_MODULE'] = 'condominios_manager.settings'
sys.path.insert(0, '.')
django.setup()
from core.models import *
from django.db.models import Sum, Count, Q
class E(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal): return str(o)
        if isinstance(o, (datetime.date, datetime.datetime)): return o.isoformat()
        return super().default(o)
d = {}
d['persons'] = list(Person.objects.all().values('id','name','phone','email','pix_key','pix_key_type','relationship','is_employee','is_owner','initial_balance','initial_balance_date','notes'))
d['credit_cards'] = list(CreditCard.objects.select_related('person').all().values('id','nickname','last_four_digits','closing_day','due_day','is_active','person__name','person_id'))
d['categories'] = list(ExpenseCategory.objects.all().values('id','name','parent_id'))
d['expenses_summary'] = list(Expense.objects.filter(is_offset=False).values('person__name').annotate(total=Sum('total_amount'), count=Count('id')).order_by('-total'))
d['offset_summary'] = list(Expense.objects.filter(is_offset=True).values('person__name').annotate(total=Sum('total_amount'), count=Count('id')).order_by('-total'))
d['expenses_by_category'] = list(Expense.objects.filter(is_offset=False).values('category__name').annotate(total=Sum('total_amount'), count=Count('id')).order_by('-total'))
d['expenses_by_card'] = list(Expense.objects.values('credit_card__nickname','credit_card__person__name').annotate(total=Sum('total_amount'), count=Count('id')).order_by('-total'))
d['recent_expenses'] = list(Expense.objects.select_related('person','credit_card','category','building').all().order_by('-expense_date').values('id','description','total_amount','expense_date','expense_type','is_recurring','is_offset','is_installment','total_installments','end_date','person__name','credit_card__nickname','category__name','building__street_number','is_debt_installment','notes')[:80])
d['buildings'] = list(Building.objects.all().values('id','street_number','name'))
d['apartments'] = list(Apartment.objects.select_related('building','owner').all().values('id','number','building__street_number','rental_value','cleaning_fee','owner__name','is_rented'))
d['incomes'] = list(Income.objects.all().order_by('-income_date').values('id','description','amount','income_date','source')[:30])
d['rent_payments'] = list(RentPayment.objects.select_related('apartment','apartment__building').all().order_by('-payment_date').values('id','amount','payment_date','month_reference','apartment__number','apartment__building__street_number')[:40])
d['person_incomes'] = list(PersonIncome.objects.select_related('person').all().order_by('-income_date').values('id','person__name','description','amount','income_date')[:30])
d['person_payments'] = list(PersonPayment.objects.select_related('person').all().order_by('-payment_date').values('id','person__name','description','amount','payment_date','payment_method')[:30])
d['employee_payments'] = list(EmployeePayment.objects.select_related('person').all().order_by('-reference_month').values('id','person__name','reference_month','base_salary','variable_amount','rent_offset','cleaning_count','is_paid','notes')[:10])
d['unpaid_installments'] = list(ExpenseInstallment.objects.filter(is_paid=False).select_related('expense','expense__person','expense__credit_card').order_by('due_date').values('expense__description','expense__person__name','expense__credit_card__nickname','installment_number','total_installments','amount','due_date')[:50])
d['summary'] = {
    'total_persons': Person.objects.count(),
    'total_credit_cards': CreditCard.objects.count(),
    'total_expenses': Expense.objects.count(),
    'total_expenses_amount': str(Expense.objects.filter(is_offset=False).aggregate(s=Sum('total_amount'))['s'] or 0),
    'total_offset_amount': str(Expense.objects.filter(is_offset=True).aggregate(s=Sum('total_amount'))['s'] or 0),
    'total_incomes': Income.objects.count(),
    'total_incomes_amount': str(Income.objects.aggregate(s=Sum('amount'))['s'] or 0),
    'total_rent_payments': RentPayment.objects.count(),
    'total_apartments': Apartment.objects.count(),
    'rented_apartments': Apartment.objects.filter(is_rented=True).count(),
    'total_rental_value': str(Apartment.objects.filter(is_rented=True).aggregate(s=Sum('rental_value'))['s'] or 0),
}
print(json.dumps(d, cls=E, indent=2, ensure_ascii=False))
