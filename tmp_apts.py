import django,os,sys
os.environ['DJANGO_SETTINGS_MODULE']='condominios_manager.settings'
sys.path.insert(0,'.')
django.setup()
from core.models import *
from django.db.models import Sum

apts = Apartment.objects.filter(is_rented=True).select_related('building','owner').order_by('building__street_number','number')
print("TODOS OS APARTAMENTOS ALUGADOS:")
for a in apts:
    owner = a.owner.name if a.owner else "-"
    print(f"  {a.building.street_number}-{a.number:>3}: R${a.rental_value:>8} | owner: {owner}")

total = apts.aggregate(s=Sum('rental_value'))['s'] or 0
owner_apts = apts.filter(owner__isnull=False)
owner_total = owner_apts.aggregate(s=Sum('rental_value'))['s'] or 0

print(f"\nTotal alugueis bruto: R${total}")
print(f"Kitnets com dono:")
for a in owner_apts:
    print(f"  {a.building.street_number}-{a.number}: R${a.rental_value} -> {a.owner.name}")
print(f"Subtotal owners: R${owner_total}")
print(f"Receita liquida sogros: R${total - owner_total}")
