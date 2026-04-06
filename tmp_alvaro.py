import django,os,sys
os.environ['DJANGO_SETTINGS_MODULE']='condominios_manager.settings'
sys.path.insert(0,'.')
django.setup()
from core.models import *
from django.db.models import Sum

# Alvaro - despesas recorrentes e parcelas grandes
alvaro = Person.objects.get(name='Alvaro')
print("=== ALVARO - RECORRENTES ===")
for e in Expense.objects.filter(person=alvaro, is_recurring=True):
    print(f"  {e.description} | R${e.expected_monthly_amount}/mes | type={e.expense_type} | cat={e.category}")

print("\n=== ALVARO - PARCELAS ATIVAS (nao-offset) ===")
for e in Expense.objects.filter(person=alvaro, is_installment=True, is_offset=False, installments__is_paid=False).distinct():
    unpaid = e.installments.filter(is_paid=False)
    print(f"  {e.description} | total R${e.total_amount} | {e.total_installments}x | restam {unpaid.count()} parcelas de R${unpaid.first().amount} | cat={e.category} | card={e.credit_card}")

print("\n=== ALVARO - OFFSETS ===")
for e in Expense.objects.filter(person=alvaro, is_offset=True):
    print(f"  {e.description} | R${e.total_amount} | {e.total_installments or 1}x | cat={e.category}")

print("\n=== ALVARO - ONE-TIME (nao parcela, nao recorrente, nao offset) ===")
for e in Expense.objects.filter(person=alvaro, is_installment=False, is_recurring=False, is_offset=False).order_by('-expense_date'):
    print(f"  {e.description} | R${e.total_amount} | {e.expense_date} | type={e.expense_type} | cat={e.category}")

# Junior income check
print("\n=== JUNIOR - PersonIncome ===")
junior = Person.objects.get(name='Junior')
for pi in PersonIncome.objects.filter(person=junior):
    print(f"  type={pi.income_type} | R${pi.fixed_amount} | {pi.start_date} | active={pi.is_active} | notes={pi.notes}")

# Camila income/salary check  
print("\n=== CAMILA - PersonIncome ===")
camila = Person.objects.get(name='Camila')
for pi in PersonIncome.objects.filter(person=camila):
    print(f"  type={pi.income_type} | apto={pi.apartment} | R${pi.fixed_amount} | {pi.start_date} | active={pi.is_active} | notes={pi.notes}")
