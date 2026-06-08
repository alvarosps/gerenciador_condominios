# Enable Row Level Security (RLS) on every public table.
#
# Why: this database is hosted on Supabase, which exposes the `public` schema
# through the PostgREST Data API to the `anon` / `authenticated` roles. With RLS
# disabled, anyone holding the project's anon key could read/write every row.
# This app does NOT use the Supabase Data API — all access goes through the Django
# backend, which connects as the `postgres` role (rolbypassrls = true) and is the
# owner of these tables, so it bypasses RLS entirely. Enabling RLS with no policies
# therefore denies the Data API roles while leaving the Django backend unaffected.
#
# ENABLE ROW LEVEL SECURITY on an already-enabled table is a no-op (no error), so
# this migration is idempotent and safe to re-run.

from django.db import migrations

ENABLE_RLS = """
ALTER TABLE public.account_emailaddress ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.account_emailconfirmation ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.auth_group ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.auth_group_permissions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.auth_permission ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.auth_user ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.auth_user_groups ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.auth_user_user_permissions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.core_apartment ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.core_apartment_furnitures ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.core_building ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.core_contractrule ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.core_creditcard ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.core_dependent ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.core_devicetoken ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.core_employeepayment ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.core_expense ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.core_expensecategory ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.core_expenseinstallment ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.core_expensemonthskip ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.core_financialsettings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.core_furniture ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.core_income ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.core_ipcaindex ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.core_landlord ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.core_lease ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.core_lease_tenants ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.core_monthsnapshot ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.core_notification ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.core_oauth_exchange_code ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.core_paymentproof ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.core_person ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.core_personincome ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.core_personpayment ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.core_personpaymentschedule ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.core_rentadjustment ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.core_rentpayment ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.core_tenant ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.core_tenant_furnitures ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.core_webpushsubscription ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.core_whatsappverification ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.django_admin_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.django_content_type ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.django_migrations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.django_session ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.django_site ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.socialaccount_socialaccount ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.socialaccount_socialapp ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.socialaccount_socialapp_sites ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.socialaccount_socialtoken ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.token_blacklist_blacklistedtoken ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.token_blacklist_outstandingtoken ENABLE ROW LEVEL SECURITY;
"""

DISABLE_RLS = """
ALTER TABLE public.account_emailaddress DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.account_emailconfirmation DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.auth_group DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.auth_group_permissions DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.auth_permission DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.auth_user DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.auth_user_groups DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.auth_user_user_permissions DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.core_apartment DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.core_apartment_furnitures DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.core_building DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.core_contractrule DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.core_creditcard DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.core_dependent DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.core_devicetoken DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.core_employeepayment DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.core_expense DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.core_expensecategory DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.core_expenseinstallment DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.core_expensemonthskip DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.core_financialsettings DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.core_furniture DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.core_income DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.core_ipcaindex DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.core_landlord DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.core_lease DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.core_lease_tenants DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.core_monthsnapshot DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.core_notification DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.core_oauth_exchange_code DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.core_paymentproof DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.core_person DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.core_personincome DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.core_personpayment DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.core_personpaymentschedule DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.core_rentadjustment DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.core_rentpayment DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.core_tenant DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.core_tenant_furnitures DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.core_webpushsubscription DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.core_whatsappverification DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.django_admin_log DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.django_content_type DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.django_migrations DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.django_session DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.django_site DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.socialaccount_socialaccount DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.socialaccount_socialapp DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.socialaccount_socialapp_sites DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.socialaccount_socialtoken DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.token_blacklist_blacklistedtoken DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.token_blacklist_outstandingtoken DISABLE ROW LEVEL SECURITY;
"""


class Migration(migrations.Migration):
    # This migration ALTERs tables owned by other apps (account/auth/admin/contenttypes/sessions/
    # sites/socialaccount/token_blacklist), so it must depend on them being fully migrated first.
    # Without these deps a FRESH build (manage.py migrate / pytest --create-db) can topologically
    # order this migration before those apps' initial migrations and fail with
    # `relation "public.<table>" does not exist` (e.g. django_session). Adding dependencies is safe
    # for already-applied databases (an applied migration is never re-run; deps only affect the
    # ordering of a fresh build). django_migrations needs no dep — the framework creates it first.
    dependencies = [
        ("core", "0046_add_rent_tracking_start_date_to_financial_settings"),
        ("account", "__latest__"),
        ("admin", "__latest__"),
        ("auth", "__latest__"),
        ("contenttypes", "__latest__"),
        ("sessions", "__latest__"),
        ("sites", "__latest__"),
        ("socialaccount", "__latest__"),
        ("token_blacklist", "__latest__"),
    ]

    operations = [
        migrations.RunSQL(sql=ENABLE_RLS, reverse_sql=DISABLE_RLS),
    ]
