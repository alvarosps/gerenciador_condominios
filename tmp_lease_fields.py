import django,os,sys
os.environ['DJANGO_SETTINGS_MODULE']='condominios_manager.settings'
sys.path.insert(0,'.')
django.setup()
from core.models import Lease
fields = [f.name for f in Lease._meta.get_fields() if hasattr(f, 'column')]
print(f"Lease: {', '.join(fields)}")
