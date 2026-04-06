import django, os, sys, json, decimal, datetime
os.environ['DJANGO_SETTINGS_MODULE'] = 'condominios_manager.settings'
sys.path.insert(0, '.')
django.setup()
from core.models import *
from django.db.models import Sum, Count
class E(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal): return str(o)
        if isinstance(o, (datetime.date, datetime.datetime)): return o.isoformat()
        return super().default(o)
d = {}
d['persons'] = list(Person.objects.all().values('id','name','phone','email','pix_key','pix_key_type','relationship','is_employee','is_owner','initial_balance','initial_balance_date','notes'))
d['credit_cards'] = list(CreditCard.objects.all().values('id','nickname','last_four_digits','closing_day','due_day','is_active','person__name','person_id'))
d['categories'] = list(ExpenseCategory.objects.all().values('id','name','parent_id','description'))
d['expenses_by_person'] = list(Expense.objects.filter(is_offset=False).values('person__name').annotate(total=Sum('total_amount'), count=Count('id')).order_by('-total'))
d['offset_by_person'] = list(Expense.objects.filter(is_offset=True).values('person__name').annotate(total=Sum('total_amount'), count=Count('id')).order_by('-total'))
d['expenses_by_category'] = list(Expense.objects.filter(is_offset=False).values('category__name').annotate(total=Sum('total_amount'), count=Count('id')).order_by('-total'))
d['expenses_by_card'] = list(Expense.objects.values('credit_card__nickname','credit_card__person__name').annotate(total=Sum('total_amount'), count=Count('id')).order_by('-total'))
d['recent_expenses'] = list(Expense.objects.order_by('-expense_date').values('id','description','total_amount','expense_date','expense_type','is_recurring','is_offset','is_installment','total_installments','end_date','person__name','credit_card__nickname','category__name','building__street_number','is_debt_installment','notes')[:80])
d['buildings'] = list(Building.objects.all().values('id','street_number','name','address'))
d['apartments'] = list(Apartment.objects.all().values('id','number','building__street_number','rental_value','cleaning_fee','owner__name','is_rented'))
d['incomes'] = list(Income.objects.order_by('-income_date').values('id','description','amount','income_date','person__name','building__street_number','category__name','is_recurring','is_received','notes')[:30])
d['rent_payments'] = list(RentPayment.objects.order_by('-payment_date').values('id','amount_paid','payment_date','reference_month','lease__id','notes')[:40])
d['person_incomes'] = list(PersonIncome.objects.all().values('id','person__name','income_type','apartment__number','apartment__building__street_number','fixed_amount','start_date','end_date','is_active','notes'))
d['person_payments'] = list(PersonPayment.objects.order_by('-payment_date').values('id','person__name','reference_month','amount','payment_date','notes')[:30])
d['employee_payments'] = list(EmployeePayment.objects.order_by('-reference_month').values('id','person__name','reference_month','base_salary','variable_amount','rent_offset','cleaning_count','is_paid','notes')[:10])
d['unpaid_installments_upcoming'] = list(ExpenseInstallment.objects.filter(is_paid=False).order_by('due_date').values('expense__description','expense__person__name','expense__credit_card__nickname','installment_number','total_installments','amount','due_date')[:60])
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
