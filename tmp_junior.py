import django,os,sys,json,decimal,datetime
os.environ['DJANGO_SETTINGS_MODULE']='condominios_manager.settings'
sys.path.insert(0,'.')
django.setup()
from core.models import *
from django.db.models import Sum
class E(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal): return str(o)
        if isinstance(o, (datetime.date, datetime.datetime)): return o.isoformat()
        return super().default(o)

# Junior - todas as despesas
junior = Person.objects.get(name='Junior')
expenses = Expense.objects.filter(person=junior).order_by('-expense_date')
print("=== JUNIOR - DESPESAS ===")
for e in expenses:
    print(f"  id={e.id} | {e.description} | R${e.total_amount} | {e.expense_date} | type={e.expense_type} | offset={e.is_offset} | installment={e.is_installment} {e.total_installments or ''}x | cat={e.category}")
print(f"\nTotal (sem offset): R${expenses.filter(is_offset=False).aggregate(s=Sum('total_amount'))['s']}")
print(f"Total (com offset): R${expenses.filter(is_offset=True).aggregate(s=Sum('total_amount'))['s']}")

# Junior - parcelas nao pagas
unpaid = ExpenseInstallment.objects.filter(expense__person=junior, is_paid=False).order_by('due_date')
print(f"\n=== JUNIOR - PARCELAS NAO PAGAS ({unpaid.count()}) ===")
for i in unpaid:
    print(f"  {i.expense.description} | {i.installment_number}/{i.total_installments} | R${i.amount} | vence {i.due_date}")
print(f"Total parcelas nao pagas: R${unpaid.aggregate(s=Sum('amount'))['s']}")

# Junior - person payments
pp = PersonPayment.objects.filter(person=junior).order_by('-payment_date')
print(f"\n=== JUNIOR - PAGAMENTOS RECEBIDOS ({pp.count()}) ===")
for p in pp:
    print(f"  {p.reference_month} | R${p.amount} | {p.payment_date} | {p.notes}")

# Junior - person incomes
pi = PersonIncome.objects.filter(person=junior)
print(f"\n=== JUNIOR - RENDAS ({pi.count()}) ===")
for p in pi:
    print(f"  {p.income_type} | apto {p.apartment.number if p.apartment else '-'}/{p.apartment.building.street_number if p.apartment else '-'} | R${p.fixed_amount} | {p.start_date}-{p.end_date} | ativo={p.is_active}")
