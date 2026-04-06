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

# Print model fields first
for m in [Person, CreditCard, Expense, ExpenseCategory, Income, RentPayment, PersonIncome, PersonPayment, EmployeePayment, ExpenseInstallment, Apartment, Building]:
    fields = [f.name for f in m._meta.get_fields() if hasattr(f, 'column')]
    print(f"### {m.__name__}: {', '.join(fields)}")
