--
-- PostgreSQL database dump
--

\restrict ORJe4op3AfVBI50oMjD6Rq7AVdfVsNqbvN3GKyehZRd3UPM4hdIpNi4MKFP743l

-- Dumped from database version 18.1
-- Dumped by pg_dump version 18.1

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

ALTER TABLE IF EXISTS ONLY "public"."token_blacklist_outstandingtoken" DROP CONSTRAINT IF EXISTS "token_blacklist_outs_user_id_83bc629a_fk_auth_user";
ALTER TABLE IF EXISTS ONLY "public"."token_blacklist_blacklistedtoken" DROP CONSTRAINT IF EXISTS "token_blacklist_blacklistedtoken_token_id_3cc7fe56_fk";
ALTER TABLE IF EXISTS ONLY "public"."socialaccount_socialaccount" DROP CONSTRAINT IF EXISTS "socialaccount_socialaccount_user_id_8146e70c_fk_auth_user_id";
ALTER TABLE IF EXISTS ONLY "public"."socialaccount_socialapp_sites" DROP CONSTRAINT IF EXISTS "socialaccount_social_socialapp_id_97fb6e7d_fk_socialacc";
ALTER TABLE IF EXISTS ONLY "public"."socialaccount_socialapp_sites" DROP CONSTRAINT IF EXISTS "socialaccount_social_site_id_2579dee5_fk_django_si";
ALTER TABLE IF EXISTS ONLY "public"."socialaccount_socialtoken" DROP CONSTRAINT IF EXISTS "socialaccount_social_app_id_636a42d7_fk_socialacc";
ALTER TABLE IF EXISTS ONLY "public"."socialaccount_socialtoken" DROP CONSTRAINT IF EXISTS "socialaccount_social_account_id_951f210e_fk_socialacc";
ALTER TABLE IF EXISTS ONLY "public"."django_admin_log" DROP CONSTRAINT IF EXISTS "django_admin_log_user_id_c564eba6_fk_auth_user_id";
ALTER TABLE IF EXISTS ONLY "public"."django_admin_log" DROP CONSTRAINT IF EXISTS "django_admin_log_content_type_id_c4bce8eb_fk_django_co";
ALTER TABLE IF EXISTS ONLY "public"."core_tenant" DROP CONSTRAINT IF EXISTS "core_tenant_user_id_6a06dd7c_fk_auth_user_id";
ALTER TABLE IF EXISTS ONLY "public"."core_tenant" DROP CONSTRAINT IF EXISTS "core_tenant_updated_by_id_a39a25ef_fk_auth_user_id";
ALTER TABLE IF EXISTS ONLY "public"."core_tenant_furnitures" DROP CONSTRAINT IF EXISTS "core_tenant_furnitures_tenant_id_a5273f50_fk_core_tenant_id";
ALTER TABLE IF EXISTS ONLY "public"."core_tenant_furnitures" DROP CONSTRAINT IF EXISTS "core_tenant_furnitur_furniture_id_b38a2b66_fk_core_furn";
ALTER TABLE IF EXISTS ONLY "public"."core_tenant" DROP CONSTRAINT IF EXISTS "core_tenant_deleted_by_id_3ff8f8bb_fk_auth_user_id";
ALTER TABLE IF EXISTS ONLY "public"."core_tenant" DROP CONSTRAINT IF EXISTS "core_tenant_created_by_id_c9f39c01_fk_auth_user_id";
ALTER TABLE IF EXISTS ONLY "public"."core_rentpayment" DROP CONSTRAINT IF EXISTS "core_rentpayment_updated_by_id_bef14fbe_fk_auth_user_id";
ALTER TABLE IF EXISTS ONLY "public"."core_rentpayment" DROP CONSTRAINT IF EXISTS "core_rentpayment_lease_id_a1c2bf37_fk_core_lease_id";
ALTER TABLE IF EXISTS ONLY "public"."core_rentpayment" DROP CONSTRAINT IF EXISTS "core_rentpayment_deleted_by_id_c6bc4999_fk_auth_user_id";
ALTER TABLE IF EXISTS ONLY "public"."core_rentpayment" DROP CONSTRAINT IF EXISTS "core_rentpayment_created_by_id_78b62bf5_fk_auth_user_id";
ALTER TABLE IF EXISTS ONLY "public"."core_rentadjustment" DROP CONSTRAINT IF EXISTS "core_rentadjustment_updated_by_id_d57f9608_fk_auth_user_id";
ALTER TABLE IF EXISTS ONLY "public"."core_rentadjustment" DROP CONSTRAINT IF EXISTS "core_rentadjustment_lease_id_49b5f5c0_fk_core_lease_id";
ALTER TABLE IF EXISTS ONLY "public"."core_rentadjustment" DROP CONSTRAINT IF EXISTS "core_rentadjustment_deleted_by_id_4b51a341_fk_auth_user_id";
ALTER TABLE IF EXISTS ONLY "public"."core_rentadjustment" DROP CONSTRAINT IF EXISTS "core_rentadjustment_created_by_id_70b404e3_fk_auth_user_id";
ALTER TABLE IF EXISTS ONLY "public"."core_personpaymentschedule" DROP CONSTRAINT IF EXISTS "core_personpaymentschedule_person_id_364d7616_fk_core_person_id";
ALTER TABLE IF EXISTS ONLY "public"."core_personpaymentschedule" DROP CONSTRAINT IF EXISTS "core_personpaymentsc_updated_by_id_a6fcae64_fk_auth_user";
ALTER TABLE IF EXISTS ONLY "public"."core_personpaymentschedule" DROP CONSTRAINT IF EXISTS "core_personpaymentsc_deleted_by_id_6b831031_fk_auth_user";
ALTER TABLE IF EXISTS ONLY "public"."core_personpaymentschedule" DROP CONSTRAINT IF EXISTS "core_personpaymentsc_created_by_id_5524466f_fk_auth_user";
ALTER TABLE IF EXISTS ONLY "public"."core_personpayment" DROP CONSTRAINT IF EXISTS "core_personpayment_updated_by_id_1d230c37_fk_auth_user_id";
ALTER TABLE IF EXISTS ONLY "public"."core_personpayment" DROP CONSTRAINT IF EXISTS "core_personpayment_person_id_510d65a7_fk_core_person_id";
ALTER TABLE IF EXISTS ONLY "public"."core_personpayment" DROP CONSTRAINT IF EXISTS "core_personpayment_deleted_by_id_99ec06ff_fk_auth_user_id";
ALTER TABLE IF EXISTS ONLY "public"."core_personpayment" DROP CONSTRAINT IF EXISTS "core_personpayment_created_by_id_719a825a_fk_auth_user_id";
ALTER TABLE IF EXISTS ONLY "public"."core_personincome" DROP CONSTRAINT IF EXISTS "core_personincome_updated_by_id_704816d7_fk_auth_user_id";
ALTER TABLE IF EXISTS ONLY "public"."core_personincome" DROP CONSTRAINT IF EXISTS "core_personincome_person_id_bff5a221_fk_core_person_id";
ALTER TABLE IF EXISTS ONLY "public"."core_personincome" DROP CONSTRAINT IF EXISTS "core_personincome_deleted_by_id_f348ffbb_fk_auth_user_id";
ALTER TABLE IF EXISTS ONLY "public"."core_personincome" DROP CONSTRAINT IF EXISTS "core_personincome_created_by_id_b232accf_fk_auth_user_id";
ALTER TABLE IF EXISTS ONLY "public"."core_personincome" DROP CONSTRAINT IF EXISTS "core_personincome_apartment_id_6d13107c_fk_core_apartment_id";
ALTER TABLE IF EXISTS ONLY "public"."core_person" DROP CONSTRAINT IF EXISTS "core_person_user_id_3dfe5fcf_fk_auth_user_id";
ALTER TABLE IF EXISTS ONLY "public"."core_person" DROP CONSTRAINT IF EXISTS "core_person_updated_by_id_2c0e591e_fk_auth_user_id";
ALTER TABLE IF EXISTS ONLY "public"."core_person" DROP CONSTRAINT IF EXISTS "core_person_deleted_by_id_cc8215b4_fk_auth_user_id";
ALTER TABLE IF EXISTS ONLY "public"."core_person" DROP CONSTRAINT IF EXISTS "core_person_created_by_id_47e54549_fk_auth_user_id";
ALTER TABLE IF EXISTS ONLY "public"."core_paymentproof" DROP CONSTRAINT IF EXISTS "core_paymentproof_updated_by_id_aa748fc5_fk_auth_user_id";
ALTER TABLE IF EXISTS ONLY "public"."core_paymentproof" DROP CONSTRAINT IF EXISTS "core_paymentproof_reviewed_by_id_1e426c23_fk_auth_user_id";
ALTER TABLE IF EXISTS ONLY "public"."core_paymentproof" DROP CONSTRAINT IF EXISTS "core_paymentproof_lease_id_b7a8844e_fk_core_lease_id";
ALTER TABLE IF EXISTS ONLY "public"."core_paymentproof" DROP CONSTRAINT IF EXISTS "core_paymentproof_deleted_by_id_6023d639_fk_auth_user_id";
ALTER TABLE IF EXISTS ONLY "public"."core_paymentproof" DROP CONSTRAINT IF EXISTS "core_paymentproof_created_by_id_1cfed265_fk_auth_user_id";
ALTER TABLE IF EXISTS ONLY "public"."core_oauth_exchange_code" DROP CONSTRAINT IF EXISTS "core_oauth_exchange_code_user_id_806380b2_fk_auth_user_id";
ALTER TABLE IF EXISTS ONLY "public"."core_notification" DROP CONSTRAINT IF EXISTS "core_notification_updated_by_id_10dfda28_fk_auth_user_id";
ALTER TABLE IF EXISTS ONLY "public"."core_notification" DROP CONSTRAINT IF EXISTS "core_notification_recipient_id_24a3d95c_fk_auth_user_id";
ALTER TABLE IF EXISTS ONLY "public"."core_notification" DROP CONSTRAINT IF EXISTS "core_notification_created_by_id_b954034c_fk_auth_user_id";
ALTER TABLE IF EXISTS ONLY "public"."core_monthsnapshot" DROP CONSTRAINT IF EXISTS "core_monthsnapshot_updated_by_id_ff44bdc4_fk_auth_user_id";
ALTER TABLE IF EXISTS ONLY "public"."core_monthsnapshot" DROP CONSTRAINT IF EXISTS "core_monthsnapshot_created_by_id_3e18926e_fk_auth_user_id";
ALTER TABLE IF EXISTS ONLY "public"."core_lease" DROP CONSTRAINT IF EXISTS "core_lease_updated_by_id_837ebc4b_fk_auth_user_id";
ALTER TABLE IF EXISTS ONLY "public"."core_lease_tenants" DROP CONSTRAINT IF EXISTS "core_lease_tenants_tenant_id_1fe477aa_fk_core_tenant_id";
ALTER TABLE IF EXISTS ONLY "public"."core_lease_tenants" DROP CONSTRAINT IF EXISTS "core_lease_tenants_lease_id_4e718198_fk_core_lease_id";
ALTER TABLE IF EXISTS ONLY "public"."core_lease" DROP CONSTRAINT IF EXISTS "core_lease_responsible_tenant_id_7048940f_fk_core_tenant_id";
ALTER TABLE IF EXISTS ONLY "public"."core_lease" DROP CONSTRAINT IF EXISTS "core_lease_resident_dependent_id_999b3373_fk_core_dependent_id";
ALTER TABLE IF EXISTS ONLY "public"."core_lease" DROP CONSTRAINT IF EXISTS "core_lease_deleted_by_id_a349bea4_fk_auth_user_id";
ALTER TABLE IF EXISTS ONLY "public"."core_lease" DROP CONSTRAINT IF EXISTS "core_lease_created_by_id_10d4e47a_fk_auth_user_id";
ALTER TABLE IF EXISTS ONLY "public"."core_lease" DROP CONSTRAINT IF EXISTS "core_lease_apartment_id_f3c48467_fk_core_apartment_id";
ALTER TABLE IF EXISTS ONLY "public"."core_landlord" DROP CONSTRAINT IF EXISTS "core_landlord_updated_by_id_a96c2f8a_fk_auth_user_id";
ALTER TABLE IF EXISTS ONLY "public"."core_landlord" DROP CONSTRAINT IF EXISTS "core_landlord_deleted_by_id_7daf3704_fk_auth_user_id";
ALTER TABLE IF EXISTS ONLY "public"."core_landlord" DROP CONSTRAINT IF EXISTS "core_landlord_created_by_id_26771936_fk_auth_user_id";
ALTER TABLE IF EXISTS ONLY "public"."core_income" DROP CONSTRAINT IF EXISTS "core_income_updated_by_id_71cc281c_fk_auth_user_id";
ALTER TABLE IF EXISTS ONLY "public"."core_income" DROP CONSTRAINT IF EXISTS "core_income_person_id_4b0c8077_fk_core_person_id";
ALTER TABLE IF EXISTS ONLY "public"."core_income" DROP CONSTRAINT IF EXISTS "core_income_deleted_by_id_eabcd72d_fk_auth_user_id";
ALTER TABLE IF EXISTS ONLY "public"."core_income" DROP CONSTRAINT IF EXISTS "core_income_created_by_id_10268b93_fk_auth_user_id";
ALTER TABLE IF EXISTS ONLY "public"."core_income" DROP CONSTRAINT IF EXISTS "core_income_category_id_03e3d7bb_fk_core_expensecategory_id";
ALTER TABLE IF EXISTS ONLY "public"."core_income" DROP CONSTRAINT IF EXISTS "core_income_building_id_76ef9a87_fk_core_building_id";
ALTER TABLE IF EXISTS ONLY "public"."core_furniture" DROP CONSTRAINT IF EXISTS "core_furniture_updated_by_id_05fc60d9_fk_auth_user_id";
ALTER TABLE IF EXISTS ONLY "public"."core_furniture" DROP CONSTRAINT IF EXISTS "core_furniture_deleted_by_id_48e626b9_fk_auth_user_id";
ALTER TABLE IF EXISTS ONLY "public"."core_furniture" DROP CONSTRAINT IF EXISTS "core_furniture_created_by_id_ac6fa2c3_fk_auth_user_id";
ALTER TABLE IF EXISTS ONLY "public"."core_financialsettings" DROP CONSTRAINT IF EXISTS "core_financialsettings_updated_by_id_d1242b26_fk_auth_user_id";
ALTER TABLE IF EXISTS ONLY "public"."core_expensemonthskip" DROP CONSTRAINT IF EXISTS "core_expensemonthskip_updated_by_id_6715bdf6_fk_auth_user_id";
ALTER TABLE IF EXISTS ONLY "public"."core_expensemonthskip" DROP CONSTRAINT IF EXISTS "core_expensemonthskip_expense_id_ac188bd0_fk_core_expense_id";
ALTER TABLE IF EXISTS ONLY "public"."core_expensemonthskip" DROP CONSTRAINT IF EXISTS "core_expensemonthskip_created_by_id_29f4e78c_fk_auth_user_id";
ALTER TABLE IF EXISTS ONLY "public"."core_expenseinstallment" DROP CONSTRAINT IF EXISTS "core_expenseinstallment_updated_by_id_b3ccb642_fk_auth_user_id";
ALTER TABLE IF EXISTS ONLY "public"."core_expenseinstallment" DROP CONSTRAINT IF EXISTS "core_expenseinstallment_expense_id_2bdeacda_fk_core_expense_id";
ALTER TABLE IF EXISTS ONLY "public"."core_expenseinstallment" DROP CONSTRAINT IF EXISTS "core_expenseinstallment_deleted_by_id_95b9cae6_fk_auth_user_id";
ALTER TABLE IF EXISTS ONLY "public"."core_expenseinstallment" DROP CONSTRAINT IF EXISTS "core_expenseinstallment_created_by_id_7fed7a7d_fk_auth_user_id";
ALTER TABLE IF EXISTS ONLY "public"."core_expensecategory" DROP CONSTRAINT IF EXISTS "core_expensecategory_updated_by_id_631d2c1b_fk_auth_user_id";
ALTER TABLE IF EXISTS ONLY "public"."core_expensecategory" DROP CONSTRAINT IF EXISTS "core_expensecategory_parent_id_823b7351_fk_core_expe";
ALTER TABLE IF EXISTS ONLY "public"."core_expensecategory" DROP CONSTRAINT IF EXISTS "core_expensecategory_deleted_by_id_bb1ba135_fk_auth_user_id";
ALTER TABLE IF EXISTS ONLY "public"."core_expensecategory" DROP CONSTRAINT IF EXISTS "core_expensecategory_created_by_id_147adbcf_fk_auth_user_id";
ALTER TABLE IF EXISTS ONLY "public"."core_expense" DROP CONSTRAINT IF EXISTS "core_expense_updated_by_id_6316c802_fk_auth_user_id";
ALTER TABLE IF EXISTS ONLY "public"."core_expense" DROP CONSTRAINT IF EXISTS "core_expense_person_id_494927aa_fk_core_person_id";
ALTER TABLE IF EXISTS ONLY "public"."core_expense" DROP CONSTRAINT IF EXISTS "core_expense_deleted_by_id_f2737b0a_fk_auth_user_id";
ALTER TABLE IF EXISTS ONLY "public"."core_expense" DROP CONSTRAINT IF EXISTS "core_expense_credit_card_id_49386120_fk_core_creditcard_id";
ALTER TABLE IF EXISTS ONLY "public"."core_expense" DROP CONSTRAINT IF EXISTS "core_expense_created_by_id_f387daf3_fk_auth_user_id";
ALTER TABLE IF EXISTS ONLY "public"."core_expense" DROP CONSTRAINT IF EXISTS "core_expense_category_id_dcdb74b3_fk_core_expensecategory_id";
ALTER TABLE IF EXISTS ONLY "public"."core_expense" DROP CONSTRAINT IF EXISTS "core_expense_building_id_bf94522e_fk_core_building_id";
ALTER TABLE IF EXISTS ONLY "public"."core_employeepayment" DROP CONSTRAINT IF EXISTS "core_employeepayment_updated_by_id_c6203d80_fk_auth_user_id";
ALTER TABLE IF EXISTS ONLY "public"."core_employeepayment" DROP CONSTRAINT IF EXISTS "core_employeepayment_person_id_6404dbbf_fk_core_person_id";
ALTER TABLE IF EXISTS ONLY "public"."core_employeepayment" DROP CONSTRAINT IF EXISTS "core_employeepayment_deleted_by_id_a07b41ff_fk_auth_user_id";
ALTER TABLE IF EXISTS ONLY "public"."core_employeepayment" DROP CONSTRAINT IF EXISTS "core_employeepayment_created_by_id_e6b42255_fk_auth_user_id";
ALTER TABLE IF EXISTS ONLY "public"."core_devicetoken" DROP CONSTRAINT IF EXISTS "core_devicetoken_user_id_479d4f09_fk_auth_user_id";
ALTER TABLE IF EXISTS ONLY "public"."core_devicetoken" DROP CONSTRAINT IF EXISTS "core_devicetoken_updated_by_id_d97de1f7_fk_auth_user_id";
ALTER TABLE IF EXISTS ONLY "public"."core_devicetoken" DROP CONSTRAINT IF EXISTS "core_devicetoken_created_by_id_ddc63831_fk_auth_user_id";
ALTER TABLE IF EXISTS ONLY "public"."core_dependent" DROP CONSTRAINT IF EXISTS "core_dependent_updated_by_id_c4c6f044_fk_auth_user_id";
ALTER TABLE IF EXISTS ONLY "public"."core_dependent" DROP CONSTRAINT IF EXISTS "core_dependent_tenant_id_ebc48edd_fk_core_tenant_id";
ALTER TABLE IF EXISTS ONLY "public"."core_dependent" DROP CONSTRAINT IF EXISTS "core_dependent_deleted_by_id_ce75a7cb_fk_auth_user_id";
ALTER TABLE IF EXISTS ONLY "public"."core_dependent" DROP CONSTRAINT IF EXISTS "core_dependent_created_by_id_1f75409f_fk_auth_user_id";
ALTER TABLE IF EXISTS ONLY "public"."core_creditcard" DROP CONSTRAINT IF EXISTS "core_creditcard_updated_by_id_64af5879_fk_auth_user_id";
ALTER TABLE IF EXISTS ONLY "public"."core_creditcard" DROP CONSTRAINT IF EXISTS "core_creditcard_person_id_ee13c25f_fk_core_person_id";
ALTER TABLE IF EXISTS ONLY "public"."core_creditcard" DROP CONSTRAINT IF EXISTS "core_creditcard_deleted_by_id_c491ac7c_fk_auth_user_id";
ALTER TABLE IF EXISTS ONLY "public"."core_creditcard" DROP CONSTRAINT IF EXISTS "core_creditcard_created_by_id_f58028fd_fk_auth_user_id";
ALTER TABLE IF EXISTS ONLY "public"."core_contractrule" DROP CONSTRAINT IF EXISTS "core_contractrule_updated_by_id_de44cbd6_fk_auth_user_id";
ALTER TABLE IF EXISTS ONLY "public"."core_contractrule" DROP CONSTRAINT IF EXISTS "core_contractrule_deleted_by_id_10cc20cc_fk_auth_user_id";
ALTER TABLE IF EXISTS ONLY "public"."core_contractrule" DROP CONSTRAINT IF EXISTS "core_contractrule_created_by_id_5fc91e81_fk_auth_user_id";
ALTER TABLE IF EXISTS ONLY "public"."core_building" DROP CONSTRAINT IF EXISTS "core_building_updated_by_id_b9061915_fk_auth_user_id";
ALTER TABLE IF EXISTS ONLY "public"."core_building" DROP CONSTRAINT IF EXISTS "core_building_deleted_by_id_46b06a95_fk_auth_user_id";
ALTER TABLE IF EXISTS ONLY "public"."core_building" DROP CONSTRAINT IF EXISTS "core_building_created_by_id_880b4e2d_fk_auth_user_id";
ALTER TABLE IF EXISTS ONLY "public"."core_apartment" DROP CONSTRAINT IF EXISTS "core_apartment_updated_by_id_951fb395_fk_auth_user_id";
ALTER TABLE IF EXISTS ONLY "public"."core_apartment" DROP CONSTRAINT IF EXISTS "core_apartment_owner_id_2eed0a5c_fk_core_person_id";
ALTER TABLE IF EXISTS ONLY "public"."core_apartment_furnitures" DROP CONSTRAINT IF EXISTS "core_apartment_furni_furniture_id_a48c384f_fk_core_furn";
ALTER TABLE IF EXISTS ONLY "public"."core_apartment_furnitures" DROP CONSTRAINT IF EXISTS "core_apartment_furni_apartment_id_fbc40478_fk_core_apar";
ALTER TABLE IF EXISTS ONLY "public"."core_apartment" DROP CONSTRAINT IF EXISTS "core_apartment_deleted_by_id_aee90fef_fk_auth_user_id";
ALTER TABLE IF EXISTS ONLY "public"."core_apartment" DROP CONSTRAINT IF EXISTS "core_apartment_created_by_id_63233eca_fk_auth_user_id";
ALTER TABLE IF EXISTS ONLY "public"."core_apartment" DROP CONSTRAINT IF EXISTS "core_apartment_building_id_016e1f62_fk_core_building_id";
ALTER TABLE IF EXISTS ONLY "public"."auth_user_user_permissions" DROP CONSTRAINT IF EXISTS "auth_user_user_permissions_user_id_a95ead1b_fk_auth_user_id";
ALTER TABLE IF EXISTS ONLY "public"."auth_user_user_permissions" DROP CONSTRAINT IF EXISTS "auth_user_user_permi_permission_id_1fbb5f2c_fk_auth_perm";
ALTER TABLE IF EXISTS ONLY "public"."auth_user_groups" DROP CONSTRAINT IF EXISTS "auth_user_groups_user_id_6a12ed8b_fk_auth_user_id";
ALTER TABLE IF EXISTS ONLY "public"."auth_user_groups" DROP CONSTRAINT IF EXISTS "auth_user_groups_group_id_97559544_fk_auth_group_id";
ALTER TABLE IF EXISTS ONLY "public"."auth_permission" DROP CONSTRAINT IF EXISTS "auth_permission_content_type_id_2f476e4b_fk_django_co";
ALTER TABLE IF EXISTS ONLY "public"."auth_group_permissions" DROP CONSTRAINT IF EXISTS "auth_group_permissions_group_id_b120cbf9_fk_auth_group_id";
ALTER TABLE IF EXISTS ONLY "public"."auth_group_permissions" DROP CONSTRAINT IF EXISTS "auth_group_permissio_permission_id_84c5c92e_fk_auth_perm";
ALTER TABLE IF EXISTS ONLY "public"."account_emailconfirmation" DROP CONSTRAINT IF EXISTS "account_emailconfirm_email_address_id_5b7f8c58_fk_account_e";
ALTER TABLE IF EXISTS ONLY "public"."account_emailaddress" DROP CONSTRAINT IF EXISTS "account_emailaddress_user_id_2c513194_fk_auth_user_id";
DROP INDEX IF EXISTS "public"."unique_verified_email";
DROP INDEX IF EXISTS "public"."unique_primary_email";
DROP INDEX IF EXISTS "public"."unique_person_schedule_per_day";
DROP INDEX IF EXISTS "public"."unique_active_rent_payment";
DROP INDEX IF EXISTS "public"."unique_active_lease_per_apartment";
DROP INDEX IF EXISTS "public"."unique_active_expense_installment";
DROP INDEX IF EXISTS "public"."unique_active_employee_payment";
DROP INDEX IF EXISTS "public"."unique_active_credit_card";
DROP INDEX IF EXISTS "public"."token_blacklist_outstandingtoken_user_id_83bc629a";
DROP INDEX IF EXISTS "public"."token_blacklist_outstandingtoken_jti_hex_d9bdf6f7_like";
DROP INDEX IF EXISTS "public"."tenant_type_name_idx";
DROP INDEX IF EXISTS "public"."tenant_status_type_idx";
DROP INDEX IF EXISTS "public"."socialaccount_socialtoken_app_id_636a42d7";
DROP INDEX IF EXISTS "public"."socialaccount_socialtoken_account_id_951f210e";
DROP INDEX IF EXISTS "public"."socialaccount_socialapp_sites_socialapp_id_97fb6e7d";
DROP INDEX IF EXISTS "public"."socialaccount_socialapp_sites_site_id_2579dee5";
DROP INDEX IF EXISTS "public"."socialaccount_socialaccount_user_id_8146e70c";
DROP INDEX IF EXISTS "public"."rule_active_order_idx";
DROP INDEX IF EXISTS "public"."rent_payment_month_idx";
DROP INDEX IF EXISTS "public"."rent_payment_lease_month_idx";
DROP INDEX IF EXISTS "public"."person_payment_month_idx";
DROP INDEX IF EXISTS "public"."lease_tenant_date_idx";
DROP INDEX IF EXISTS "public"."lease_status_date_idx";
DROP INDEX IF EXISTS "public"."lease_start_date_idx";
DROP INDEX IF EXISTS "public"."lease_contract_gen_idx";
DROP INDEX IF EXISTS "public"."lease_apt_date_idx";
DROP INDEX IF EXISTS "public"."ipca_index_month_idx";
DROP INDEX IF EXISTS "public"."installment_paid_due_idx";
DROP INDEX IF EXISTS "public"."installment_due_date_idx";
DROP INDEX IF EXISTS "public"."inst_exp_date_paid_idx";
DROP INDEX IF EXISTS "public"."idx_expense_recurring_date";
DROP INDEX IF EXISTS "public"."idx_expense_person_paid_date";
DROP INDEX IF EXISTS "public"."idx_expense_category_date";
DROP INDEX IF EXISTS "public"."expense_type_date_idx";
DROP INDEX IF EXISTS "public"."expense_paid_date_idx";
DROP INDEX IF EXISTS "public"."expense_date_idx";
DROP INDEX IF EXISTS "public"."exp_person_type_idx";
DROP INDEX IF EXISTS "public"."exp_person_date_idx";
DROP INDEX IF EXISTS "public"."django_site_domain_a2e37b91_like";
DROP INDEX IF EXISTS "public"."django_session_session_key_c0390e0f_like";
DROP INDEX IF EXISTS "public"."django_session_expire_date_a5c62663";
DROP INDEX IF EXISTS "public"."django_admin_log_user_id_c564eba6";
DROP INDEX IF EXISTS "public"."django_admin_log_content_type_id_c4bce8eb";
DROP INDEX IF EXISTS "public"."core_whatsa_cpf_cnp_c8c80e_idx";
DROP INDEX IF EXISTS "public"."core_tenant_updated_by_id_a39a25ef";
DROP INDEX IF EXISTS "public"."core_tenant_is_deleted_a0b4f60a";
DROP INDEX IF EXISTS "public"."core_tenant_furnitures_tenant_id_a5273f50";
DROP INDEX IF EXISTS "public"."core_tenant_furnitures_furniture_id_b38a2b66";
DROP INDEX IF EXISTS "public"."core_tenant_deleted_by_id_3ff8f8bb";
DROP INDEX IF EXISTS "public"."core_tenant_created_by_id_c9f39c01";
DROP INDEX IF EXISTS "public"."core_tenant_cpf_cnpj_1c2c482d_like";
DROP INDEX IF EXISTS "public"."core_rentpayment_updated_by_id_bef14fbe";
DROP INDEX IF EXISTS "public"."core_rentpayment_lease_id_a1c2bf37";
DROP INDEX IF EXISTS "public"."core_rentpayment_is_deleted_d07101fc";
DROP INDEX IF EXISTS "public"."core_rentpayment_deleted_by_id_c6bc4999";
DROP INDEX IF EXISTS "public"."core_rentpayment_created_by_id_78b62bf5";
DROP INDEX IF EXISTS "public"."core_rentadjustment_updated_by_id_d57f9608";
DROP INDEX IF EXISTS "public"."core_rentadjustment_lease_id_49b5f5c0";
DROP INDEX IF EXISTS "public"."core_rentadjustment_is_deleted_79558ba6";
DROP INDEX IF EXISTS "public"."core_rentadjustment_deleted_by_id_4b51a341";
DROP INDEX IF EXISTS "public"."core_rentadjustment_created_by_id_70b404e3";
DROP INDEX IF EXISTS "public"."core_personpaymentschedule_updated_by_id_a6fcae64";
DROP INDEX IF EXISTS "public"."core_personpaymentschedule_person_id_364d7616";
DROP INDEX IF EXISTS "public"."core_personpaymentschedule_is_deleted_48c18b58";
DROP INDEX IF EXISTS "public"."core_personpaymentschedule_deleted_by_id_6b831031";
DROP INDEX IF EXISTS "public"."core_personpaymentschedule_created_by_id_5524466f";
DROP INDEX IF EXISTS "public"."core_personpayment_updated_by_id_1d230c37";
DROP INDEX IF EXISTS "public"."core_personpayment_person_id_510d65a7";
DROP INDEX IF EXISTS "public"."core_personpayment_is_deleted_21b48c3a";
DROP INDEX IF EXISTS "public"."core_personpayment_deleted_by_id_99ec06ff";
DROP INDEX IF EXISTS "public"."core_personpayment_created_by_id_719a825a";
DROP INDEX IF EXISTS "public"."core_personincome_updated_by_id_704816d7";
DROP INDEX IF EXISTS "public"."core_personincome_person_id_bff5a221";
DROP INDEX IF EXISTS "public"."core_personincome_is_deleted_30a25355";
DROP INDEX IF EXISTS "public"."core_personincome_deleted_by_id_f348ffbb";
DROP INDEX IF EXISTS "public"."core_personincome_created_by_id_b232accf";
DROP INDEX IF EXISTS "public"."core_personincome_apartment_id_6d13107c";
DROP INDEX IF EXISTS "public"."core_person_updated_by_id_2c0e591e";
DROP INDEX IF EXISTS "public"."core_person_is_deleted_6e3a9413";
DROP INDEX IF EXISTS "public"."core_person_deleted_by_id_cc8215b4";
DROP INDEX IF EXISTS "public"."core_person_created_by_id_47e54549";
DROP INDEX IF EXISTS "public"."core_paymentproof_updated_by_id_aa748fc5";
DROP INDEX IF EXISTS "public"."core_paymentproof_reviewed_by_id_1e426c23";
DROP INDEX IF EXISTS "public"."core_paymentproof_lease_id_b7a8844e";
DROP INDEX IF EXISTS "public"."core_paymentproof_is_deleted_89873b63";
DROP INDEX IF EXISTS "public"."core_paymentproof_deleted_by_id_6023d639";
DROP INDEX IF EXISTS "public"."core_paymentproof_created_by_id_1cfed265";
DROP INDEX IF EXISTS "public"."core_paymen_status_2d7c73_idx";
DROP INDEX IF EXISTS "public"."core_paymen_lease_i_d9c27f_idx";
DROP INDEX IF EXISTS "public"."core_oauth_exchange_code_user_id_806380b2";
DROP INDEX IF EXISTS "public"."core_notification_updated_by_id_10dfda28";
DROP INDEX IF EXISTS "public"."core_notification_recipient_id_24a3d95c";
DROP INDEX IF EXISTS "public"."core_notification_created_by_id_b954034c";
DROP INDEX IF EXISTS "public"."core_notifi_type_312e1c_idx";
DROP INDEX IF EXISTS "public"."core_notifi_recipie_aeffaf_idx";
DROP INDEX IF EXISTS "public"."core_notifi_recipie_37a373_idx";
DROP INDEX IF EXISTS "public"."core_monthsnapshot_updated_by_id_ff44bdc4";
DROP INDEX IF EXISTS "public"."core_monthsnapshot_created_by_id_3e18926e";
DROP INDEX IF EXISTS "public"."core_lease_updated_by_id_837ebc4b";
DROP INDEX IF EXISTS "public"."core_lease_tenants_tenant_id_1fe477aa";
DROP INDEX IF EXISTS "public"."core_lease_tenants_lease_id_4e718198";
DROP INDEX IF EXISTS "public"."core_lease_start_date_0ca440cd";
DROP INDEX IF EXISTS "public"."core_lease_responsible_tenant_id_7048940f";
DROP INDEX IF EXISTS "public"."core_lease_resident_dependent_id_999b3373";
DROP INDEX IF EXISTS "public"."core_lease_is_deleted_3b73b647";
DROP INDEX IF EXISTS "public"."core_lease_deleted_by_id_a349bea4";
DROP INDEX IF EXISTS "public"."core_lease_created_by_id_10d4e47a";
DROP INDEX IF EXISTS "public"."core_lease_apartment_id_f3c48467";
DROP INDEX IF EXISTS "public"."core_landlord_updated_by_id_a96c2f8a";
DROP INDEX IF EXISTS "public"."core_landlord_is_deleted_9aac14d7";
DROP INDEX IF EXISTS "public"."core_landlord_deleted_by_id_7daf3704";
DROP INDEX IF EXISTS "public"."core_landlord_created_by_id_26771936";
DROP INDEX IF EXISTS "public"."core_income_updated_by_id_71cc281c";
DROP INDEX IF EXISTS "public"."core_income_person_id_4b0c8077";
DROP INDEX IF EXISTS "public"."core_income_is_deleted_f41c8420";
DROP INDEX IF EXISTS "public"."core_income_deleted_by_id_eabcd72d";
DROP INDEX IF EXISTS "public"."core_income_created_by_id_10268b93";
DROP INDEX IF EXISTS "public"."core_income_category_id_03e3d7bb";
DROP INDEX IF EXISTS "public"."core_income_building_id_76ef9a87";
DROP INDEX IF EXISTS "public"."core_furniture_updated_by_id_05fc60d9";
DROP INDEX IF EXISTS "public"."core_furniture_name_3a0fcd18_like";
DROP INDEX IF EXISTS "public"."core_furniture_is_deleted_6ea2d58b";
DROP INDEX IF EXISTS "public"."core_furniture_deleted_by_id_48e626b9";
DROP INDEX IF EXISTS "public"."core_furniture_created_by_id_ac6fa2c3";
DROP INDEX IF EXISTS "public"."core_financialsettings_updated_by_id_d1242b26";
DROP INDEX IF EXISTS "public"."core_expensemonthskip_updated_by_id_6715bdf6";
DROP INDEX IF EXISTS "public"."core_expensemonthskip_expense_id_ac188bd0";
DROP INDEX IF EXISTS "public"."core_expensemonthskip_created_by_id_29f4e78c";
DROP INDEX IF EXISTS "public"."core_expenseinstallment_updated_by_id_b3ccb642";
DROP INDEX IF EXISTS "public"."core_expenseinstallment_is_deleted_214e26e4";
DROP INDEX IF EXISTS "public"."core_expenseinstallment_expense_id_2bdeacda";
DROP INDEX IF EXISTS "public"."core_expenseinstallment_deleted_by_id_95b9cae6";
DROP INDEX IF EXISTS "public"."core_expenseinstallment_created_by_id_7fed7a7d";
DROP INDEX IF EXISTS "public"."core_expensecategory_updated_by_id_631d2c1b";
DROP INDEX IF EXISTS "public"."core_expensecategory_parent_id_823b7351";
DROP INDEX IF EXISTS "public"."core_expensecategory_name_aaa0c3d3_like";
DROP INDEX IF EXISTS "public"."core_expensecategory_is_deleted_61ebaa13";
DROP INDEX IF EXISTS "public"."core_expensecategory_deleted_by_id_bb1ba135";
DROP INDEX IF EXISTS "public"."core_expensecategory_created_by_id_147adbcf";
DROP INDEX IF EXISTS "public"."core_expense_updated_by_id_6316c802";
DROP INDEX IF EXISTS "public"."core_expense_person_id_494927aa";
DROP INDEX IF EXISTS "public"."core_expense_is_deleted_a19e6eb0";
DROP INDEX IF EXISTS "public"."core_expense_deleted_by_id_f2737b0a";
DROP INDEX IF EXISTS "public"."core_expense_credit_card_id_49386120";
DROP INDEX IF EXISTS "public"."core_expense_created_by_id_f387daf3";
DROP INDEX IF EXISTS "public"."core_expense_category_id_dcdb74b3";
DROP INDEX IF EXISTS "public"."core_expense_building_id_bf94522e";
DROP INDEX IF EXISTS "public"."core_employeepayment_updated_by_id_c6203d80";
DROP INDEX IF EXISTS "public"."core_employeepayment_person_id_6404dbbf";
DROP INDEX IF EXISTS "public"."core_employeepayment_is_deleted_d7f82bfb";
DROP INDEX IF EXISTS "public"."core_employeepayment_deleted_by_id_a07b41ff";
DROP INDEX IF EXISTS "public"."core_employeepayment_created_by_id_e6b42255";
DROP INDEX IF EXISTS "public"."core_devicetoken_user_id_479d4f09";
DROP INDEX IF EXISTS "public"."core_devicetoken_updated_by_id_d97de1f7";
DROP INDEX IF EXISTS "public"."core_devicetoken_token_d6aba46e_like";
DROP INDEX IF EXISTS "public"."core_devicetoken_created_by_id_ddc63831";
DROP INDEX IF EXISTS "public"."core_dependent_updated_by_id_c4c6f044";
DROP INDEX IF EXISTS "public"."core_dependent_tenant_id_ebc48edd";
DROP INDEX IF EXISTS "public"."core_dependent_is_deleted_d9f585ac";
DROP INDEX IF EXISTS "public"."core_dependent_deleted_by_id_ce75a7cb";
DROP INDEX IF EXISTS "public"."core_dependent_created_by_id_1f75409f";
DROP INDEX IF EXISTS "public"."core_creditcard_updated_by_id_64af5879";
DROP INDEX IF EXISTS "public"."core_creditcard_person_id_ee13c25f";
DROP INDEX IF EXISTS "public"."core_creditcard_is_deleted_676e834b";
DROP INDEX IF EXISTS "public"."core_creditcard_deleted_by_id_c491ac7c";
DROP INDEX IF EXISTS "public"."core_creditcard_created_by_id_f58028fd";
DROP INDEX IF EXISTS "public"."core_contractrule_updated_by_id_de44cbd6";
DROP INDEX IF EXISTS "public"."core_contractrule_order_2385e299";
DROP INDEX IF EXISTS "public"."core_contractrule_is_deleted_060b997a";
DROP INDEX IF EXISTS "public"."core_contractrule_is_active_53171522";
DROP INDEX IF EXISTS "public"."core_contractrule_deleted_by_id_10cc20cc";
DROP INDEX IF EXISTS "public"."core_contractrule_created_by_id_5fc91e81";
DROP INDEX IF EXISTS "public"."core_building_updated_by_id_b9061915";
DROP INDEX IF EXISTS "public"."core_building_is_deleted_c61a5410";
DROP INDEX IF EXISTS "public"."core_building_deleted_by_id_46b06a95";
DROP INDEX IF EXISTS "public"."core_building_created_by_id_880b4e2d";
DROP INDEX IF EXISTS "public"."core_apartment_updated_by_id_951fb395";
DROP INDEX IF EXISTS "public"."core_apartment_owner_id_2eed0a5c";
DROP INDEX IF EXISTS "public"."core_apartment_is_deleted_5e88d077";
DROP INDEX IF EXISTS "public"."core_apartment_furnitures_furniture_id_a48c384f";
DROP INDEX IF EXISTS "public"."core_apartment_furnitures_apartment_id_fbc40478";
DROP INDEX IF EXISTS "public"."core_apartment_deleted_by_id_aee90fef";
DROP INDEX IF EXISTS "public"."core_apartment_created_by_id_63233eca";
DROP INDEX IF EXISTS "public"."core_apartment_building_id_016e1f62";
DROP INDEX IF EXISTS "public"."auth_user_username_6821ab7c_like";
DROP INDEX IF EXISTS "public"."auth_user_user_permissions_user_id_a95ead1b";
DROP INDEX IF EXISTS "public"."auth_user_user_permissions_permission_id_1fbb5f2c";
DROP INDEX IF EXISTS "public"."auth_user_groups_user_id_6a12ed8b";
DROP INDEX IF EXISTS "public"."auth_user_groups_group_id_97559544";
DROP INDEX IF EXISTS "public"."auth_permission_content_type_id_2f476e4b";
DROP INDEX IF EXISTS "public"."auth_group_permissions_permission_id_84c5c92e";
DROP INDEX IF EXISTS "public"."auth_group_permissions_group_id_b120cbf9";
DROP INDEX IF EXISTS "public"."auth_group_name_a6ea08ec_like";
DROP INDEX IF EXISTS "public"."apt_rented_value_idx";
DROP INDEX IF EXISTS "public"."apt_is_rented_idx";
DROP INDEX IF EXISTS "public"."apt_building_rented_idx";
DROP INDEX IF EXISTS "public"."apt_building_number_idx";
DROP INDEX IF EXISTS "public"."account_emailconfirmation_key_f43612bd_like";
DROP INDEX IF EXISTS "public"."account_emailconfirmation_email_address_id_5b7f8c58";
DROP INDEX IF EXISTS "public"."account_emailaddress_user_id_2c513194";
DROP INDEX IF EXISTS "public"."account_emailaddress_email_03be32b2_like";
DROP INDEX IF EXISTS "public"."account_emailaddress_email_03be32b2";
ALTER TABLE IF EXISTS ONLY "public"."core_monthsnapshot" DROP CONSTRAINT IF EXISTS "unique_month_snapshot";
ALTER TABLE IF EXISTS ONLY "public"."core_expensemonthskip" DROP CONSTRAINT IF EXISTS "unique_expense_skip_per_month";
ALTER TABLE IF EXISTS ONLY "public"."token_blacklist_outstandingtoken" DROP CONSTRAINT IF EXISTS "token_blacklist_outstandingtoken_pkey";
ALTER TABLE IF EXISTS ONLY "public"."token_blacklist_outstandingtoken" DROP CONSTRAINT IF EXISTS "token_blacklist_outstandingtoken_jti_hex_d9bdf6f7_uniq";
ALTER TABLE IF EXISTS ONLY "public"."token_blacklist_blacklistedtoken" DROP CONSTRAINT IF EXISTS "token_blacklist_blacklistedtoken_token_id_key";
ALTER TABLE IF EXISTS ONLY "public"."token_blacklist_blacklistedtoken" DROP CONSTRAINT IF EXISTS "token_blacklist_blacklistedtoken_pkey";
ALTER TABLE IF EXISTS ONLY "public"."socialaccount_socialtoken" DROP CONSTRAINT IF EXISTS "socialaccount_socialtoken_pkey";
ALTER TABLE IF EXISTS ONLY "public"."socialaccount_socialtoken" DROP CONSTRAINT IF EXISTS "socialaccount_socialtoken_app_id_account_id_fca4e0ac_uniq";
ALTER TABLE IF EXISTS ONLY "public"."socialaccount_socialapp_sites" DROP CONSTRAINT IF EXISTS "socialaccount_socialapp_sites_pkey";
ALTER TABLE IF EXISTS ONLY "public"."socialaccount_socialapp" DROP CONSTRAINT IF EXISTS "socialaccount_socialapp_pkey";
ALTER TABLE IF EXISTS ONLY "public"."socialaccount_socialapp_sites" DROP CONSTRAINT IF EXISTS "socialaccount_socialapp__socialapp_id_site_id_71a9a768_uniq";
ALTER TABLE IF EXISTS ONLY "public"."socialaccount_socialaccount" DROP CONSTRAINT IF EXISTS "socialaccount_socialaccount_provider_uid_fc810c6e_uniq";
ALTER TABLE IF EXISTS ONLY "public"."socialaccount_socialaccount" DROP CONSTRAINT IF EXISTS "socialaccount_socialaccount_pkey";
ALTER TABLE IF EXISTS ONLY "public"."django_site" DROP CONSTRAINT IF EXISTS "django_site_pkey";
ALTER TABLE IF EXISTS ONLY "public"."django_site" DROP CONSTRAINT IF EXISTS "django_site_domain_a2e37b91_uniq";
ALTER TABLE IF EXISTS ONLY "public"."django_session" DROP CONSTRAINT IF EXISTS "django_session_pkey";
ALTER TABLE IF EXISTS ONLY "public"."django_migrations" DROP CONSTRAINT IF EXISTS "django_migrations_pkey";
ALTER TABLE IF EXISTS ONLY "public"."django_content_type" DROP CONSTRAINT IF EXISTS "django_content_type_pkey";
ALTER TABLE IF EXISTS ONLY "public"."django_content_type" DROP CONSTRAINT IF EXISTS "django_content_type_app_label_model_76bd3d3b_uniq";
ALTER TABLE IF EXISTS ONLY "public"."django_admin_log" DROP CONSTRAINT IF EXISTS "django_admin_log_pkey";
ALTER TABLE IF EXISTS ONLY "public"."core_whatsappverification" DROP CONSTRAINT IF EXISTS "core_whatsappverification_pkey";
ALTER TABLE IF EXISTS ONLY "public"."core_tenant" DROP CONSTRAINT IF EXISTS "core_tenant_user_id_key";
ALTER TABLE IF EXISTS ONLY "public"."core_tenant" DROP CONSTRAINT IF EXISTS "core_tenant_pkey";
ALTER TABLE IF EXISTS ONLY "public"."core_tenant_furnitures" DROP CONSTRAINT IF EXISTS "core_tenant_furnitures_tenant_id_furniture_id_2ca08b30_uniq";
ALTER TABLE IF EXISTS ONLY "public"."core_tenant_furnitures" DROP CONSTRAINT IF EXISTS "core_tenant_furnitures_pkey";
ALTER TABLE IF EXISTS ONLY "public"."core_tenant" DROP CONSTRAINT IF EXISTS "core_tenant_cpf_cnpj_key";
ALTER TABLE IF EXISTS ONLY "public"."core_rentpayment" DROP CONSTRAINT IF EXISTS "core_rentpayment_pkey";
ALTER TABLE IF EXISTS ONLY "public"."core_rentadjustment" DROP CONSTRAINT IF EXISTS "core_rentadjustment_pkey";
ALTER TABLE IF EXISTS ONLY "public"."core_personpaymentschedule" DROP CONSTRAINT IF EXISTS "core_personpaymentschedule_pkey";
ALTER TABLE IF EXISTS ONLY "public"."core_personpayment" DROP CONSTRAINT IF EXISTS "core_personpayment_pkey";
ALTER TABLE IF EXISTS ONLY "public"."core_personincome" DROP CONSTRAINT IF EXISTS "core_personincome_pkey";
ALTER TABLE IF EXISTS ONLY "public"."core_person" DROP CONSTRAINT IF EXISTS "core_person_user_id_key";
ALTER TABLE IF EXISTS ONLY "public"."core_person" DROP CONSTRAINT IF EXISTS "core_person_pkey";
ALTER TABLE IF EXISTS ONLY "public"."core_paymentproof" DROP CONSTRAINT IF EXISTS "core_paymentproof_pkey";
ALTER TABLE IF EXISTS ONLY "public"."core_oauth_exchange_code" DROP CONSTRAINT IF EXISTS "core_oauth_exchange_code_pkey";
ALTER TABLE IF EXISTS ONLY "public"."core_oauth_exchange_code" DROP CONSTRAINT IF EXISTS "core_oauth_exchange_code_code_key";
ALTER TABLE IF EXISTS ONLY "public"."core_notification" DROP CONSTRAINT IF EXISTS "core_notification_pkey";
ALTER TABLE IF EXISTS ONLY "public"."core_monthsnapshot" DROP CONSTRAINT IF EXISTS "core_monthsnapshot_pkey";
ALTER TABLE IF EXISTS ONLY "public"."core_lease_tenants" DROP CONSTRAINT IF EXISTS "core_lease_tenants_pkey";
ALTER TABLE IF EXISTS ONLY "public"."core_lease_tenants" DROP CONSTRAINT IF EXISTS "core_lease_tenants_lease_id_tenant_id_b6dc2ad7_uniq";
ALTER TABLE IF EXISTS ONLY "public"."core_lease" DROP CONSTRAINT IF EXISTS "core_lease_pkey";
ALTER TABLE IF EXISTS ONLY "public"."core_landlord" DROP CONSTRAINT IF EXISTS "core_landlord_pkey";
ALTER TABLE IF EXISTS ONLY "public"."core_ipcaindex" DROP CONSTRAINT IF EXISTS "core_ipcaindex_reference_month_key";
ALTER TABLE IF EXISTS ONLY "public"."core_ipcaindex" DROP CONSTRAINT IF EXISTS "core_ipcaindex_pkey";
ALTER TABLE IF EXISTS ONLY "public"."core_income" DROP CONSTRAINT IF EXISTS "core_income_pkey";
ALTER TABLE IF EXISTS ONLY "public"."core_furniture" DROP CONSTRAINT IF EXISTS "core_furniture_pkey";
ALTER TABLE IF EXISTS ONLY "public"."core_furniture" DROP CONSTRAINT IF EXISTS "core_furniture_name_key";
ALTER TABLE IF EXISTS ONLY "public"."core_financialsettings" DROP CONSTRAINT IF EXISTS "core_financialsettings_pkey";
ALTER TABLE IF EXISTS ONLY "public"."core_expensemonthskip" DROP CONSTRAINT IF EXISTS "core_expensemonthskip_pkey";
ALTER TABLE IF EXISTS ONLY "public"."core_expenseinstallment" DROP CONSTRAINT IF EXISTS "core_expenseinstallment_pkey";
ALTER TABLE IF EXISTS ONLY "public"."core_expensecategory" DROP CONSTRAINT IF EXISTS "core_expensecategory_pkey";
ALTER TABLE IF EXISTS ONLY "public"."core_expensecategory" DROP CONSTRAINT IF EXISTS "core_expensecategory_name_key";
ALTER TABLE IF EXISTS ONLY "public"."core_expense" DROP CONSTRAINT IF EXISTS "core_expense_pkey";
ALTER TABLE IF EXISTS ONLY "public"."core_employeepayment" DROP CONSTRAINT IF EXISTS "core_employeepayment_pkey";
ALTER TABLE IF EXISTS ONLY "public"."core_devicetoken" DROP CONSTRAINT IF EXISTS "core_devicetoken_token_key";
ALTER TABLE IF EXISTS ONLY "public"."core_devicetoken" DROP CONSTRAINT IF EXISTS "core_devicetoken_pkey";
ALTER TABLE IF EXISTS ONLY "public"."core_dependent" DROP CONSTRAINT IF EXISTS "core_dependent_pkey";
ALTER TABLE IF EXISTS ONLY "public"."core_creditcard" DROP CONSTRAINT IF EXISTS "core_creditcard_pkey";
ALTER TABLE IF EXISTS ONLY "public"."core_contractrule" DROP CONSTRAINT IF EXISTS "core_contractrule_pkey";
ALTER TABLE IF EXISTS ONLY "public"."core_building" DROP CONSTRAINT IF EXISTS "core_building_street_number_key";
ALTER TABLE IF EXISTS ONLY "public"."core_building" DROP CONSTRAINT IF EXISTS "core_building_pkey";
ALTER TABLE IF EXISTS ONLY "public"."core_apartment" DROP CONSTRAINT IF EXISTS "core_apartment_pkey";
ALTER TABLE IF EXISTS ONLY "public"."core_apartment_furnitures" DROP CONSTRAINT IF EXISTS "core_apartment_furnitures_pkey";
ALTER TABLE IF EXISTS ONLY "public"."core_apartment_furnitures" DROP CONSTRAINT IF EXISTS "core_apartment_furniture_apartment_id_furniture_i_89520678_uniq";
ALTER TABLE IF EXISTS ONLY "public"."core_apartment" DROP CONSTRAINT IF EXISTS "core_apartment_building_id_number_eb0e26fe_uniq";
ALTER TABLE IF EXISTS ONLY "public"."auth_user" DROP CONSTRAINT IF EXISTS "auth_user_username_key";
ALTER TABLE IF EXISTS ONLY "public"."auth_user_user_permissions" DROP CONSTRAINT IF EXISTS "auth_user_user_permissions_user_id_permission_id_14a6b632_uniq";
ALTER TABLE IF EXISTS ONLY "public"."auth_user_user_permissions" DROP CONSTRAINT IF EXISTS "auth_user_user_permissions_pkey";
ALTER TABLE IF EXISTS ONLY "public"."auth_user" DROP CONSTRAINT IF EXISTS "auth_user_pkey";
ALTER TABLE IF EXISTS ONLY "public"."auth_user_groups" DROP CONSTRAINT IF EXISTS "auth_user_groups_user_id_group_id_94350c0c_uniq";
ALTER TABLE IF EXISTS ONLY "public"."auth_user_groups" DROP CONSTRAINT IF EXISTS "auth_user_groups_pkey";
ALTER TABLE IF EXISTS ONLY "public"."auth_permission" DROP CONSTRAINT IF EXISTS "auth_permission_pkey";
ALTER TABLE IF EXISTS ONLY "public"."auth_permission" DROP CONSTRAINT IF EXISTS "auth_permission_content_type_id_codename_01ab375a_uniq";
ALTER TABLE IF EXISTS ONLY "public"."auth_group" DROP CONSTRAINT IF EXISTS "auth_group_pkey";
ALTER TABLE IF EXISTS ONLY "public"."auth_group_permissions" DROP CONSTRAINT IF EXISTS "auth_group_permissions_pkey";
ALTER TABLE IF EXISTS ONLY "public"."auth_group_permissions" DROP CONSTRAINT IF EXISTS "auth_group_permissions_group_id_permission_id_0cd325b0_uniq";
ALTER TABLE IF EXISTS ONLY "public"."auth_group" DROP CONSTRAINT IF EXISTS "auth_group_name_key";
ALTER TABLE IF EXISTS ONLY "public"."account_emailconfirmation" DROP CONSTRAINT IF EXISTS "account_emailconfirmation_pkey";
ALTER TABLE IF EXISTS ONLY "public"."account_emailconfirmation" DROP CONSTRAINT IF EXISTS "account_emailconfirmation_key_key";
ALTER TABLE IF EXISTS ONLY "public"."account_emailaddress" DROP CONSTRAINT IF EXISTS "account_emailaddress_user_id_email_987c8728_uniq";
ALTER TABLE IF EXISTS ONLY "public"."account_emailaddress" DROP CONSTRAINT IF EXISTS "account_emailaddress_pkey";
DROP TABLE IF EXISTS "public"."token_blacklist_outstandingtoken";
DROP TABLE IF EXISTS "public"."token_blacklist_blacklistedtoken";
DROP TABLE IF EXISTS "public"."socialaccount_socialtoken";
DROP TABLE IF EXISTS "public"."socialaccount_socialapp_sites";
DROP TABLE IF EXISTS "public"."socialaccount_socialapp";
DROP TABLE IF EXISTS "public"."socialaccount_socialaccount";
DROP TABLE IF EXISTS "public"."django_site";
DROP TABLE IF EXISTS "public"."django_session";
DROP TABLE IF EXISTS "public"."django_migrations";
DROP TABLE IF EXISTS "public"."django_content_type";
DROP TABLE IF EXISTS "public"."django_admin_log";
DROP TABLE IF EXISTS "public"."core_whatsappverification";
DROP TABLE IF EXISTS "public"."core_tenant_furnitures";
DROP TABLE IF EXISTS "public"."core_tenant";
DROP TABLE IF EXISTS "public"."core_rentpayment";
DROP TABLE IF EXISTS "public"."core_rentadjustment";
DROP TABLE IF EXISTS "public"."core_personpaymentschedule";
DROP TABLE IF EXISTS "public"."core_personpayment";
DROP TABLE IF EXISTS "public"."core_personincome";
DROP TABLE IF EXISTS "public"."core_person";
DROP TABLE IF EXISTS "public"."core_paymentproof";
DROP TABLE IF EXISTS "public"."core_oauth_exchange_code";
DROP TABLE IF EXISTS "public"."core_notification";
DROP TABLE IF EXISTS "public"."core_monthsnapshot";
DROP TABLE IF EXISTS "public"."core_lease_tenants";
DROP TABLE IF EXISTS "public"."core_lease";
DROP TABLE IF EXISTS "public"."core_landlord";
DROP TABLE IF EXISTS "public"."core_ipcaindex";
DROP TABLE IF EXISTS "public"."core_income";
DROP TABLE IF EXISTS "public"."core_furniture";
DROP TABLE IF EXISTS "public"."core_financialsettings";
DROP TABLE IF EXISTS "public"."core_expensemonthskip";
DROP TABLE IF EXISTS "public"."core_expenseinstallment";
DROP TABLE IF EXISTS "public"."core_expensecategory";
DROP TABLE IF EXISTS "public"."core_expense";
DROP TABLE IF EXISTS "public"."core_employeepayment";
DROP TABLE IF EXISTS "public"."core_devicetoken";
DROP TABLE IF EXISTS "public"."core_dependent";
DROP TABLE IF EXISTS "public"."core_creditcard";
DROP TABLE IF EXISTS "public"."core_contractrule";
DROP TABLE IF EXISTS "public"."core_building";
DROP TABLE IF EXISTS "public"."core_apartment_furnitures";
DROP TABLE IF EXISTS "public"."core_apartment";
DROP TABLE IF EXISTS "public"."auth_user_user_permissions";
DROP TABLE IF EXISTS "public"."auth_user_groups";
DROP TABLE IF EXISTS "public"."auth_user";
DROP TABLE IF EXISTS "public"."auth_permission";
DROP TABLE IF EXISTS "public"."auth_group_permissions";
DROP TABLE IF EXISTS "public"."auth_group";
DROP TABLE IF EXISTS "public"."account_emailconfirmation";
DROP TABLE IF EXISTS "public"."account_emailaddress";
DROP SCHEMA IF EXISTS "public";
--
-- Name: public; Type: SCHEMA; Schema: -; Owner: pg_database_owner
--

CREATE SCHEMA "public";


ALTER SCHEMA "public" OWNER TO "pg_database_owner";

--
-- Name: SCHEMA "public"; Type: COMMENT; Schema: -; Owner: pg_database_owner
--

COMMENT ON SCHEMA "public" IS 'standard public schema';


SET default_tablespace = '';

SET default_table_access_method = "heap";

--
-- Name: account_emailaddress; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE "public"."account_emailaddress" (
    "id" integer NOT NULL,
    "email" character varying(254) NOT NULL,
    "verified" boolean NOT NULL,
    "primary" boolean NOT NULL,
    "user_id" integer NOT NULL
);


ALTER TABLE "public"."account_emailaddress" OWNER TO "postgres";

--
-- Name: account_emailaddress_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE "public"."account_emailaddress" ALTER COLUMN "id" ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME "public"."account_emailaddress_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: account_emailconfirmation; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE "public"."account_emailconfirmation" (
    "id" integer NOT NULL,
    "created" timestamp with time zone NOT NULL,
    "sent" timestamp with time zone,
    "key" character varying(64) NOT NULL,
    "email_address_id" integer NOT NULL
);


ALTER TABLE "public"."account_emailconfirmation" OWNER TO "postgres";

--
-- Name: account_emailconfirmation_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE "public"."account_emailconfirmation" ALTER COLUMN "id" ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME "public"."account_emailconfirmation_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: auth_group; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE "public"."auth_group" (
    "id" integer NOT NULL,
    "name" character varying(150) NOT NULL
);


ALTER TABLE "public"."auth_group" OWNER TO "postgres";

--
-- Name: auth_group_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE "public"."auth_group" ALTER COLUMN "id" ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME "public"."auth_group_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: auth_group_permissions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE "public"."auth_group_permissions" (
    "id" bigint NOT NULL,
    "group_id" integer NOT NULL,
    "permission_id" integer NOT NULL
);


ALTER TABLE "public"."auth_group_permissions" OWNER TO "postgres";

--
-- Name: auth_group_permissions_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE "public"."auth_group_permissions" ALTER COLUMN "id" ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME "public"."auth_group_permissions_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: auth_permission; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE "public"."auth_permission" (
    "id" integer NOT NULL,
    "name" character varying(255) NOT NULL,
    "content_type_id" integer NOT NULL,
    "codename" character varying(100) NOT NULL
);


ALTER TABLE "public"."auth_permission" OWNER TO "postgres";

--
-- Name: auth_permission_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE "public"."auth_permission" ALTER COLUMN "id" ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME "public"."auth_permission_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: auth_user; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE "public"."auth_user" (
    "id" integer NOT NULL,
    "password" character varying(128) NOT NULL,
    "last_login" timestamp with time zone,
    "is_superuser" boolean NOT NULL,
    "username" character varying(150) NOT NULL,
    "first_name" character varying(150) NOT NULL,
    "last_name" character varying(150) NOT NULL,
    "email" character varying(254) NOT NULL,
    "is_staff" boolean NOT NULL,
    "is_active" boolean NOT NULL,
    "date_joined" timestamp with time zone NOT NULL
);


ALTER TABLE "public"."auth_user" OWNER TO "postgres";

--
-- Name: auth_user_groups; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE "public"."auth_user_groups" (
    "id" bigint NOT NULL,
    "user_id" integer NOT NULL,
    "group_id" integer NOT NULL
);


ALTER TABLE "public"."auth_user_groups" OWNER TO "postgres";

--
-- Name: auth_user_groups_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE "public"."auth_user_groups" ALTER COLUMN "id" ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME "public"."auth_user_groups_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: auth_user_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE "public"."auth_user" ALTER COLUMN "id" ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME "public"."auth_user_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: auth_user_user_permissions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE "public"."auth_user_user_permissions" (
    "id" bigint NOT NULL,
    "user_id" integer NOT NULL,
    "permission_id" integer NOT NULL
);


ALTER TABLE "public"."auth_user_user_permissions" OWNER TO "postgres";

--
-- Name: auth_user_user_permissions_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE "public"."auth_user_user_permissions" ALTER COLUMN "id" ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME "public"."auth_user_user_permissions_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: core_apartment; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE "public"."core_apartment" (
    "id" bigint NOT NULL,
    "number" integer NOT NULL,
    "rental_value" numeric(10,2) NOT NULL,
    "cleaning_fee" numeric(10,2) NOT NULL,
    "max_tenants" integer NOT NULL,
    "is_rented" boolean NOT NULL,
    "last_rent_increase_date" "date",
    "building_id" bigint NOT NULL,
    "created_at" timestamp with time zone NOT NULL,
    "created_by_id" integer,
    "deleted_at" timestamp with time zone,
    "deleted_by_id" integer,
    "is_deleted" boolean NOT NULL,
    "updated_at" timestamp with time zone NOT NULL,
    "updated_by_id" integer,
    "owner_id" bigint,
    "rental_value_double" numeric(10,2),
    CONSTRAINT "apt_cleaning_fee_non_negative" CHECK (("cleaning_fee" >= (0)::numeric)),
    CONSTRAINT "apt_rental_value_non_negative" CHECK (("rental_value" >= (0)::numeric)),
    CONSTRAINT "core_apartment_max_tenants_check" CHECK (("max_tenants" >= 0)),
    CONSTRAINT "core_apartment_number_check" CHECK (("number" >= 0))
);


ALTER TABLE "public"."core_apartment" OWNER TO "postgres";

--
-- Name: core_apartment_furnitures; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE "public"."core_apartment_furnitures" (
    "id" bigint NOT NULL,
    "apartment_id" bigint NOT NULL,
    "furniture_id" bigint NOT NULL
);


ALTER TABLE "public"."core_apartment_furnitures" OWNER TO "postgres";

--
-- Name: core_apartment_furnitures_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE "public"."core_apartment_furnitures" ALTER COLUMN "id" ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME "public"."core_apartment_furnitures_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: core_apartment_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE "public"."core_apartment" ALTER COLUMN "id" ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME "public"."core_apartment_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: core_building; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE "public"."core_building" (
    "id" bigint NOT NULL,
    "street_number" integer NOT NULL,
    "name" character varying(100) NOT NULL,
    "address" character varying(200) NOT NULL,
    "created_at" timestamp with time zone NOT NULL,
    "created_by_id" integer,
    "deleted_at" timestamp with time zone,
    "deleted_by_id" integer,
    "is_deleted" boolean NOT NULL,
    "updated_at" timestamp with time zone NOT NULL,
    "updated_by_id" integer,
    CONSTRAINT "core_building_street_number_check" CHECK (("street_number" >= 0))
);


ALTER TABLE "public"."core_building" OWNER TO "postgres";

--
-- Name: core_building_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE "public"."core_building" ALTER COLUMN "id" ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME "public"."core_building_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: core_contractrule; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE "public"."core_contractrule" (
    "id" bigint NOT NULL,
    "created_at" timestamp with time zone NOT NULL,
    "updated_at" timestamp with time zone NOT NULL,
    "is_deleted" boolean NOT NULL,
    "deleted_at" timestamp with time zone,
    "content" "text" NOT NULL,
    "order" integer NOT NULL,
    "is_active" boolean NOT NULL,
    "created_by_id" integer,
    "updated_by_id" integer,
    "deleted_by_id" integer,
    CONSTRAINT "core_contractrule_order_check" CHECK (("order" >= 0))
);


ALTER TABLE "public"."core_contractrule" OWNER TO "postgres";

--
-- Name: core_contractrule_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE "public"."core_contractrule" ALTER COLUMN "id" ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME "public"."core_contractrule_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: core_creditcard; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE "public"."core_creditcard" (
    "id" bigint NOT NULL,
    "created_at" timestamp with time zone NOT NULL,
    "updated_at" timestamp with time zone NOT NULL,
    "is_deleted" boolean NOT NULL,
    "deleted_at" timestamp with time zone,
    "nickname" character varying(100) NOT NULL,
    "last_four_digits" character varying(4) NOT NULL,
    "closing_day" smallint NOT NULL,
    "due_day" smallint NOT NULL,
    "is_active" boolean NOT NULL,
    "created_by_id" integer,
    "deleted_by_id" integer,
    "updated_by_id" integer,
    "person_id" bigint NOT NULL,
    CONSTRAINT "core_creditcard_closing_day_check" CHECK (("closing_day" >= 0)),
    CONSTRAINT "core_creditcard_due_day_check" CHECK (("due_day" >= 0))
);


ALTER TABLE "public"."core_creditcard" OWNER TO "postgres";

--
-- Name: core_creditcard_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE "public"."core_creditcard" ALTER COLUMN "id" ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME "public"."core_creditcard_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: core_dependent; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE "public"."core_dependent" (
    "id" bigint NOT NULL,
    "name" character varying(150) NOT NULL,
    "phone" character varying(20) NOT NULL,
    "tenant_id" bigint NOT NULL,
    "created_at" timestamp with time zone NOT NULL,
    "created_by_id" integer,
    "deleted_at" timestamp with time zone,
    "deleted_by_id" integer,
    "is_deleted" boolean NOT NULL,
    "updated_at" timestamp with time zone NOT NULL,
    "updated_by_id" integer,
    "cpf_cnpj" character varying(14)
);


ALTER TABLE "public"."core_dependent" OWNER TO "postgres";

--
-- Name: core_dependent_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE "public"."core_dependent" ALTER COLUMN "id" ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME "public"."core_dependent_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: core_devicetoken; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE "public"."core_devicetoken" (
    "id" bigint NOT NULL,
    "created_at" timestamp with time zone NOT NULL,
    "updated_at" timestamp with time zone NOT NULL,
    "token" character varying(255) NOT NULL,
    "platform" character varying(10) NOT NULL,
    "is_active" boolean NOT NULL,
    "created_by_id" integer,
    "updated_by_id" integer,
    "user_id" integer NOT NULL
);


ALTER TABLE "public"."core_devicetoken" OWNER TO "postgres";

--
-- Name: core_devicetoken_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE "public"."core_devicetoken" ALTER COLUMN "id" ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME "public"."core_devicetoken_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: core_employeepayment; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE "public"."core_employeepayment" (
    "id" bigint NOT NULL,
    "created_at" timestamp with time zone NOT NULL,
    "updated_at" timestamp with time zone NOT NULL,
    "is_deleted" boolean NOT NULL,
    "deleted_at" timestamp with time zone,
    "reference_month" "date" NOT NULL,
    "base_salary" numeric(12,2) NOT NULL,
    "variable_amount" numeric(12,2) NOT NULL,
    "rent_offset" numeric(12,2) NOT NULL,
    "cleaning_count" integer NOT NULL,
    "payment_date" "date",
    "is_paid" boolean NOT NULL,
    "notes" "text" NOT NULL,
    "created_by_id" integer,
    "deleted_by_id" integer,
    "updated_by_id" integer,
    "person_id" bigint NOT NULL,
    CONSTRAINT "core_employeepayment_cleaning_count_check" CHECK (("cleaning_count" >= 0)),
    CONSTRAINT "employee_base_salary_non_negative" CHECK (("base_salary" >= (0)::numeric))
);


ALTER TABLE "public"."core_employeepayment" OWNER TO "postgres";

--
-- Name: core_employeepayment_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE "public"."core_employeepayment" ALTER COLUMN "id" ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME "public"."core_employeepayment_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: core_expense; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE "public"."core_expense" (
    "id" bigint NOT NULL,
    "created_at" timestamp with time zone NOT NULL,
    "updated_at" timestamp with time zone NOT NULL,
    "is_deleted" boolean NOT NULL,
    "deleted_at" timestamp with time zone,
    "description" character varying(500) NOT NULL,
    "expense_type" character varying(30) NOT NULL,
    "total_amount" numeric(12,2) NOT NULL,
    "expense_date" "date" NOT NULL,
    "is_installment" boolean NOT NULL,
    "total_installments" integer,
    "is_debt_installment" boolean NOT NULL,
    "is_recurring" boolean NOT NULL,
    "expected_monthly_amount" numeric(12,2),
    "recurrence_day" smallint,
    "is_paid" boolean NOT NULL,
    "paid_date" "date",
    "bank_name" character varying(100) NOT NULL,
    "interest_rate" numeric(5,2),
    "notes" "text" NOT NULL,
    "building_id" bigint,
    "created_by_id" integer,
    "credit_card_id" bigint,
    "deleted_by_id" integer,
    "updated_by_id" integer,
    "category_id" bigint,
    "person_id" bigint,
    "is_offset" boolean NOT NULL,
    "end_date" "date",
    CONSTRAINT "core_expense_recurrence_day_check" CHECK (("recurrence_day" >= 0)),
    CONSTRAINT "core_expense_total_installments_check" CHECK (("total_installments" >= 0)),
    CONSTRAINT "expense_total_amount_positive" CHECK (("total_amount" > (0)::numeric))
);


ALTER TABLE "public"."core_expense" OWNER TO "postgres";

--
-- Name: core_expense_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE "public"."core_expense" ALTER COLUMN "id" ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME "public"."core_expense_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: core_expensecategory; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE "public"."core_expensecategory" (
    "id" bigint NOT NULL,
    "created_at" timestamp with time zone NOT NULL,
    "updated_at" timestamp with time zone NOT NULL,
    "is_deleted" boolean NOT NULL,
    "deleted_at" timestamp with time zone,
    "name" character varying(100) NOT NULL,
    "description" "text" NOT NULL,
    "color" character varying(7) NOT NULL,
    "created_by_id" integer,
    "deleted_by_id" integer,
    "updated_by_id" integer,
    "parent_id" bigint
);


ALTER TABLE "public"."core_expensecategory" OWNER TO "postgres";

--
-- Name: core_expensecategory_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE "public"."core_expensecategory" ALTER COLUMN "id" ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME "public"."core_expensecategory_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: core_expenseinstallment; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE "public"."core_expenseinstallment" (
    "id" bigint NOT NULL,
    "created_at" timestamp with time zone NOT NULL,
    "updated_at" timestamp with time zone NOT NULL,
    "is_deleted" boolean NOT NULL,
    "deleted_at" timestamp with time zone,
    "installment_number" integer NOT NULL,
    "total_installments" integer NOT NULL,
    "amount" numeric(12,2) NOT NULL,
    "due_date" "date" NOT NULL,
    "is_paid" boolean NOT NULL,
    "paid_date" "date",
    "notes" "text" NOT NULL,
    "created_by_id" integer,
    "deleted_by_id" integer,
    "expense_id" bigint NOT NULL,
    "updated_by_id" integer,
    CONSTRAINT "core_expenseinstallment_installment_number_check" CHECK (("installment_number" >= 0)),
    CONSTRAINT "core_expenseinstallment_total_installments_check" CHECK (("total_installments" >= 0)),
    CONSTRAINT "installment_amount_non_negative" CHECK (("amount" >= (0)::numeric))
);


ALTER TABLE "public"."core_expenseinstallment" OWNER TO "postgres";

--
-- Name: core_expenseinstallment_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE "public"."core_expenseinstallment" ALTER COLUMN "id" ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME "public"."core_expenseinstallment_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: core_expensemonthskip; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE "public"."core_expensemonthskip" (
    "id" bigint NOT NULL,
    "created_at" timestamp with time zone NOT NULL,
    "updated_at" timestamp with time zone NOT NULL,
    "reference_month" "date" NOT NULL,
    "created_by_id" integer,
    "expense_id" bigint NOT NULL,
    "updated_by_id" integer
);


ALTER TABLE "public"."core_expensemonthskip" OWNER TO "postgres";

--
-- Name: core_expensemonthskip_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE "public"."core_expensemonthskip" ALTER COLUMN "id" ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME "public"."core_expensemonthskip_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: core_financialsettings; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE "public"."core_financialsettings" (
    "id" bigint NOT NULL,
    "initial_balance" numeric(12,2) NOT NULL,
    "initial_balance_date" "date" NOT NULL,
    "notes" "text" NOT NULL,
    "updated_at" timestamp with time zone NOT NULL,
    "updated_by_id" integer,
    "default_pix_key" character varying(100) NOT NULL,
    "default_pix_key_type" character varying(10) NOT NULL
);


ALTER TABLE "public"."core_financialsettings" OWNER TO "postgres";

--
-- Name: core_financialsettings_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE "public"."core_financialsettings" ALTER COLUMN "id" ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME "public"."core_financialsettings_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: core_furniture; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE "public"."core_furniture" (
    "id" bigint NOT NULL,
    "name" character varying(100) NOT NULL,
    "description" "text" NOT NULL,
    "created_at" timestamp with time zone NOT NULL,
    "created_by_id" integer,
    "deleted_at" timestamp with time zone,
    "deleted_by_id" integer,
    "is_deleted" boolean NOT NULL,
    "updated_at" timestamp with time zone NOT NULL,
    "updated_by_id" integer
);


ALTER TABLE "public"."core_furniture" OWNER TO "postgres";

--
-- Name: core_furniture_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE "public"."core_furniture" ALTER COLUMN "id" ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME "public"."core_furniture_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: core_income; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE "public"."core_income" (
    "id" bigint NOT NULL,
    "created_at" timestamp with time zone NOT NULL,
    "updated_at" timestamp with time zone NOT NULL,
    "is_deleted" boolean NOT NULL,
    "deleted_at" timestamp with time zone,
    "description" character varying(500) NOT NULL,
    "amount" numeric(12,2) NOT NULL,
    "income_date" "date" NOT NULL,
    "is_recurring" boolean NOT NULL,
    "expected_monthly_amount" numeric(12,2),
    "is_received" boolean NOT NULL,
    "received_date" "date",
    "notes" "text" NOT NULL,
    "building_id" bigint,
    "category_id" bigint,
    "created_by_id" integer,
    "deleted_by_id" integer,
    "updated_by_id" integer,
    "person_id" bigint
);


ALTER TABLE "public"."core_income" OWNER TO "postgres";

--
-- Name: core_income_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE "public"."core_income" ALTER COLUMN "id" ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME "public"."core_income_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: core_ipcaindex; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE "public"."core_ipcaindex" (
    "id" bigint NOT NULL,
    "reference_month" "date" NOT NULL,
    "value" numeric(20,13) NOT NULL,
    "fetched_at" timestamp with time zone NOT NULL
);


ALTER TABLE "public"."core_ipcaindex" OWNER TO "postgres";

--
-- Name: core_ipcaindex_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE "public"."core_ipcaindex" ALTER COLUMN "id" ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME "public"."core_ipcaindex_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: core_landlord; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE "public"."core_landlord" (
    "id" bigint NOT NULL,
    "created_at" timestamp with time zone NOT NULL,
    "updated_at" timestamp with time zone NOT NULL,
    "is_deleted" boolean NOT NULL,
    "deleted_at" timestamp with time zone,
    "name" character varying(200) NOT NULL,
    "nationality" character varying(100) NOT NULL,
    "marital_status" character varying(50) NOT NULL,
    "cpf_cnpj" character varying(20) NOT NULL,
    "rg" character varying(20) NOT NULL,
    "phone" character varying(20) NOT NULL,
    "email" character varying(254) NOT NULL,
    "street" character varying(200) NOT NULL,
    "street_number" character varying(20) NOT NULL,
    "complement" character varying(100) NOT NULL,
    "neighborhood" character varying(100) NOT NULL,
    "city" character varying(100) NOT NULL,
    "state" character varying(50) NOT NULL,
    "zip_code" character varying(10) NOT NULL,
    "country" character varying(100) NOT NULL,
    "is_active" boolean NOT NULL,
    "created_by_id" integer,
    "deleted_by_id" integer,
    "updated_by_id" integer,
    "rent_adjustment_percentage" numeric(5,2) NOT NULL
);


ALTER TABLE "public"."core_landlord" OWNER TO "postgres";

--
-- Name: core_landlord_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE "public"."core_landlord" ALTER COLUMN "id" ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME "public"."core_landlord_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: core_lease; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE "public"."core_lease" (
    "id" bigint NOT NULL,
    "start_date" "date" NOT NULL,
    "validity_months" integer NOT NULL,
    "tag_fee" numeric(10,2) NOT NULL,
    "contract_generated" boolean NOT NULL,
    "contract_signed" boolean NOT NULL,
    "interfone_configured" boolean NOT NULL,
    "apartment_id" bigint NOT NULL,
    "responsible_tenant_id" bigint NOT NULL,
    "number_of_tenants" integer NOT NULL,
    "created_at" timestamp with time zone NOT NULL,
    "created_by_id" integer,
    "deleted_at" timestamp with time zone,
    "deleted_by_id" integer,
    "is_deleted" boolean NOT NULL,
    "updated_at" timestamp with time zone NOT NULL,
    "updated_by_id" integer,
    "is_salary_offset" boolean NOT NULL,
    "prepaid_until" "date",
    "cleaning_fee_paid" boolean NOT NULL,
    "deposit_amount" numeric(10,2),
    "tag_deposit_paid" boolean NOT NULL,
    "resident_dependent_id" bigint,
    "rental_value" numeric(10,2) NOT NULL,
    "last_rent_increase_date" "date",
    "pending_rental_value" numeric(10,2),
    "pending_rental_value_date" "date",
    CONSTRAINT "core_lease_number_of_tenants_check" CHECK (("number_of_tenants" >= 0)),
    CONSTRAINT "core_lease_validity_months_check" CHECK (("validity_months" >= 0)),
    CONSTRAINT "lease_rental_value_non_negative" CHECK (("rental_value" >= (0)::numeric))
);


ALTER TABLE "public"."core_lease" OWNER TO "postgres";

--
-- Name: core_lease_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE "public"."core_lease" ALTER COLUMN "id" ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME "public"."core_lease_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: core_lease_tenants; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE "public"."core_lease_tenants" (
    "id" bigint NOT NULL,
    "lease_id" bigint NOT NULL,
    "tenant_id" bigint NOT NULL
);


ALTER TABLE "public"."core_lease_tenants" OWNER TO "postgres";

--
-- Name: core_lease_tenants_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE "public"."core_lease_tenants" ALTER COLUMN "id" ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME "public"."core_lease_tenants_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: core_monthsnapshot; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE "public"."core_monthsnapshot" (
    "id" bigint NOT NULL,
    "created_at" timestamp with time zone NOT NULL,
    "updated_at" timestamp with time zone NOT NULL,
    "reference_month" "date" NOT NULL,
    "total_rent_income" numeric(12,2) NOT NULL,
    "total_extra_income" numeric(12,2) NOT NULL,
    "total_person_payments_received" numeric(12,2) NOT NULL,
    "total_income" numeric(12,2) NOT NULL,
    "total_card_installments" numeric(12,2) NOT NULL,
    "total_loan_installments" numeric(12,2) NOT NULL,
    "total_utility_bills" numeric(12,2) NOT NULL,
    "total_fixed_expenses" numeric(12,2) NOT NULL,
    "total_one_time_expenses" numeric(12,2) NOT NULL,
    "total_employee_salary" numeric(12,2) NOT NULL,
    "total_owner_repayments" numeric(12,2) NOT NULL,
    "total_person_stipends" numeric(12,2) NOT NULL,
    "total_debt_installments" numeric(12,2) NOT NULL,
    "total_property_tax" numeric(12,2) NOT NULL,
    "total_expenses" numeric(12,2) NOT NULL,
    "net_balance" numeric(12,2) NOT NULL,
    "cumulative_ending_balance" numeric(12,2) NOT NULL,
    "detailed_breakdown" "jsonb" NOT NULL,
    "is_finalized" boolean NOT NULL,
    "finalized_at" timestamp with time zone,
    "notes" "text" NOT NULL,
    "created_by_id" integer,
    "updated_by_id" integer
);


ALTER TABLE "public"."core_monthsnapshot" OWNER TO "postgres";

--
-- Name: core_monthsnapshot_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE "public"."core_monthsnapshot" ALTER COLUMN "id" ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME "public"."core_monthsnapshot_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: core_notification; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE "public"."core_notification" (
    "id" bigint NOT NULL,
    "created_at" timestamp with time zone NOT NULL,
    "updated_at" timestamp with time zone NOT NULL,
    "type" character varying(30) NOT NULL,
    "title" character varying(200) NOT NULL,
    "body" "text" NOT NULL,
    "is_read" boolean NOT NULL,
    "read_at" timestamp with time zone,
    "sent_at" timestamp with time zone NOT NULL,
    "data" "jsonb",
    "created_by_id" integer,
    "recipient_id" integer NOT NULL,
    "updated_by_id" integer
);


ALTER TABLE "public"."core_notification" OWNER TO "postgres";

--
-- Name: core_notification_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE "public"."core_notification" ALTER COLUMN "id" ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME "public"."core_notification_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: core_oauth_exchange_code; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE "public"."core_oauth_exchange_code" (
    "id" bigint NOT NULL,
    "code" "uuid" NOT NULL,
    "access_token" "text" NOT NULL,
    "refresh_token" "text" NOT NULL,
    "created_at" timestamp with time zone NOT NULL,
    "is_used" boolean NOT NULL,
    "user_id" integer NOT NULL
);


ALTER TABLE "public"."core_oauth_exchange_code" OWNER TO "postgres";

--
-- Name: core_oauth_exchange_code_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE "public"."core_oauth_exchange_code" ALTER COLUMN "id" ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME "public"."core_oauth_exchange_code_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: core_paymentproof; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE "public"."core_paymentproof" (
    "id" bigint NOT NULL,
    "created_at" timestamp with time zone NOT NULL,
    "updated_at" timestamp with time zone NOT NULL,
    "is_deleted" boolean NOT NULL,
    "deleted_at" timestamp with time zone,
    "reference_month" "date" NOT NULL,
    "file" character varying(100) NOT NULL,
    "pix_code" "text" NOT NULL,
    "status" character varying(10) NOT NULL,
    "reviewed_at" timestamp with time zone,
    "rejection_reason" "text" NOT NULL,
    "created_by_id" integer,
    "deleted_by_id" integer,
    "lease_id" bigint NOT NULL,
    "reviewed_by_id" integer,
    "updated_by_id" integer
);


ALTER TABLE "public"."core_paymentproof" OWNER TO "postgres";

--
-- Name: core_paymentproof_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE "public"."core_paymentproof" ALTER COLUMN "id" ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME "public"."core_paymentproof_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: core_person; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE "public"."core_person" (
    "id" bigint NOT NULL,
    "created_at" timestamp with time zone NOT NULL,
    "updated_at" timestamp with time zone NOT NULL,
    "is_deleted" boolean NOT NULL,
    "deleted_at" timestamp with time zone,
    "name" character varying(200) NOT NULL,
    "relationship" character varying(50) NOT NULL,
    "phone" character varying(20) NOT NULL,
    "email" character varying(254) NOT NULL,
    "is_owner" boolean NOT NULL,
    "is_employee" boolean NOT NULL,
    "notes" "text" NOT NULL,
    "created_by_id" integer,
    "deleted_by_id" integer,
    "updated_by_id" integer,
    "user_id" integer,
    "initial_balance" numeric(12,2) NOT NULL,
    "initial_balance_date" "date",
    "pix_key" character varying(100) NOT NULL,
    "pix_key_type" character varying(10) NOT NULL
);


ALTER TABLE "public"."core_person" OWNER TO "postgres";

--
-- Name: core_person_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE "public"."core_person" ALTER COLUMN "id" ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME "public"."core_person_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: core_personincome; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE "public"."core_personincome" (
    "id" bigint NOT NULL,
    "created_at" timestamp with time zone NOT NULL,
    "updated_at" timestamp with time zone NOT NULL,
    "is_deleted" boolean NOT NULL,
    "deleted_at" timestamp with time zone,
    "income_type" character varying(20) NOT NULL,
    "fixed_amount" numeric(12,2),
    "start_date" "date" NOT NULL,
    "end_date" "date",
    "is_active" boolean NOT NULL,
    "notes" "text" NOT NULL,
    "apartment_id" bigint,
    "created_by_id" integer,
    "deleted_by_id" integer,
    "person_id" bigint NOT NULL,
    "updated_by_id" integer
);


ALTER TABLE "public"."core_personincome" OWNER TO "postgres";

--
-- Name: core_personincome_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE "public"."core_personincome" ALTER COLUMN "id" ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME "public"."core_personincome_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: core_personpayment; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE "public"."core_personpayment" (
    "id" bigint NOT NULL,
    "created_at" timestamp with time zone NOT NULL,
    "updated_at" timestamp with time zone NOT NULL,
    "is_deleted" boolean NOT NULL,
    "deleted_at" timestamp with time zone,
    "reference_month" "date" NOT NULL,
    "amount" numeric(12,2) NOT NULL,
    "payment_date" "date" NOT NULL,
    "notes" "text" NOT NULL,
    "created_by_id" integer,
    "deleted_by_id" integer,
    "person_id" bigint NOT NULL,
    "updated_by_id" integer,
    CONSTRAINT "person_payment_amount_positive" CHECK (("amount" > (0)::numeric))
);


ALTER TABLE "public"."core_personpayment" OWNER TO "postgres";

--
-- Name: core_personpayment_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE "public"."core_personpayment" ALTER COLUMN "id" ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME "public"."core_personpayment_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: core_personpaymentschedule; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE "public"."core_personpaymentschedule" (
    "id" bigint NOT NULL,
    "created_at" timestamp with time zone NOT NULL,
    "updated_at" timestamp with time zone NOT NULL,
    "is_deleted" boolean NOT NULL,
    "deleted_at" timestamp with time zone,
    "reference_month" "date" NOT NULL,
    "due_day" smallint NOT NULL,
    "amount" numeric(12,2) NOT NULL,
    "created_by_id" integer,
    "deleted_by_id" integer,
    "person_id" bigint NOT NULL,
    "updated_by_id" integer,
    CONSTRAINT "core_personpaymentschedule_due_day_check" CHECK (("due_day" >= 0))
);


ALTER TABLE "public"."core_personpaymentschedule" OWNER TO "postgres";

--
-- Name: core_personpaymentschedule_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE "public"."core_personpaymentschedule" ALTER COLUMN "id" ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME "public"."core_personpaymentschedule_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: core_rentadjustment; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE "public"."core_rentadjustment" (
    "id" bigint NOT NULL,
    "created_at" timestamp with time zone NOT NULL,
    "updated_at" timestamp with time zone NOT NULL,
    "is_deleted" boolean NOT NULL,
    "deleted_at" timestamp with time zone,
    "adjustment_date" "date" NOT NULL,
    "percentage" numeric(5,2) NOT NULL,
    "previous_value" numeric(10,2) NOT NULL,
    "new_value" numeric(10,2) NOT NULL,
    "apartment_updated" boolean NOT NULL,
    "created_by_id" integer,
    "deleted_by_id" integer,
    "lease_id" bigint NOT NULL,
    "updated_by_id" integer
);


ALTER TABLE "public"."core_rentadjustment" OWNER TO "postgres";

--
-- Name: core_rentadjustment_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE "public"."core_rentadjustment" ALTER COLUMN "id" ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME "public"."core_rentadjustment_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: core_rentpayment; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE "public"."core_rentpayment" (
    "id" bigint NOT NULL,
    "created_at" timestamp with time zone NOT NULL,
    "updated_at" timestamp with time zone NOT NULL,
    "is_deleted" boolean NOT NULL,
    "deleted_at" timestamp with time zone,
    "reference_month" "date" NOT NULL,
    "amount_paid" numeric(12,2) NOT NULL,
    "payment_date" "date" NOT NULL,
    "notes" "text" NOT NULL,
    "created_by_id" integer,
    "deleted_by_id" integer,
    "lease_id" bigint NOT NULL,
    "updated_by_id" integer,
    CONSTRAINT "rent_payment_amount_positive" CHECK (("amount_paid" > (0)::numeric))
);


ALTER TABLE "public"."core_rentpayment" OWNER TO "postgres";

--
-- Name: core_rentpayment_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE "public"."core_rentpayment" ALTER COLUMN "id" ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME "public"."core_rentpayment_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: core_tenant; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE "public"."core_tenant" (
    "id" bigint NOT NULL,
    "name" character varying(150) NOT NULL,
    "cpf_cnpj" character varying(20) NOT NULL,
    "is_company" boolean NOT NULL,
    "rg" character varying(20) NOT NULL,
    "phone" character varying(20) NOT NULL,
    "marital_status" character varying(50) NOT NULL,
    "profession" character varying(100) NOT NULL,
    "due_day" integer CONSTRAINT "core_tenant_rent_due_day_not_null" NOT NULL,
    "user_id" integer,
    "created_at" timestamp with time zone NOT NULL,
    "created_by_id" integer,
    "deleted_at" timestamp with time zone,
    "deleted_by_id" integer,
    "is_deleted" boolean NOT NULL,
    "updated_at" timestamp with time zone NOT NULL,
    "updated_by_id" integer,
    "warning_count" integer NOT NULL,
    CONSTRAINT "core_tenant_rent_due_day_check" CHECK (("due_day" >= 0)),
    CONSTRAINT "core_tenant_warning_count_check" CHECK (("warning_count" >= 0))
);


ALTER TABLE "public"."core_tenant" OWNER TO "postgres";

--
-- Name: core_tenant_furnitures; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE "public"."core_tenant_furnitures" (
    "id" bigint NOT NULL,
    "tenant_id" bigint NOT NULL,
    "furniture_id" bigint NOT NULL
);


ALTER TABLE "public"."core_tenant_furnitures" OWNER TO "postgres";

--
-- Name: core_tenant_furnitures_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE "public"."core_tenant_furnitures" ALTER COLUMN "id" ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME "public"."core_tenant_furnitures_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: core_tenant_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE "public"."core_tenant" ALTER COLUMN "id" ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME "public"."core_tenant_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: core_whatsappverification; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE "public"."core_whatsappverification" (
    "id" bigint NOT NULL,
    "cpf_cnpj" character varying(20) NOT NULL,
    "code" character varying(6) NOT NULL,
    "phone" character varying(20) NOT NULL,
    "created_at" timestamp with time zone NOT NULL,
    "expires_at" timestamp with time zone NOT NULL,
    "attempts" integer NOT NULL,
    "is_used" boolean NOT NULL,
    CONSTRAINT "core_whatsappverification_attempts_check" CHECK (("attempts" >= 0))
);


ALTER TABLE "public"."core_whatsappverification" OWNER TO "postgres";

--
-- Name: core_whatsappverification_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE "public"."core_whatsappverification" ALTER COLUMN "id" ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME "public"."core_whatsappverification_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: django_admin_log; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE "public"."django_admin_log" (
    "id" integer NOT NULL,
    "action_time" timestamp with time zone NOT NULL,
    "object_id" "text",
    "object_repr" character varying(200) NOT NULL,
    "action_flag" smallint NOT NULL,
    "change_message" "text" NOT NULL,
    "content_type_id" integer,
    "user_id" integer NOT NULL,
    CONSTRAINT "django_admin_log_action_flag_check" CHECK (("action_flag" >= 0))
);


ALTER TABLE "public"."django_admin_log" OWNER TO "postgres";

--
-- Name: django_admin_log_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE "public"."django_admin_log" ALTER COLUMN "id" ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME "public"."django_admin_log_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: django_content_type; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE "public"."django_content_type" (
    "id" integer NOT NULL,
    "app_label" character varying(100) NOT NULL,
    "model" character varying(100) NOT NULL
);


ALTER TABLE "public"."django_content_type" OWNER TO "postgres";

--
-- Name: django_content_type_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE "public"."django_content_type" ALTER COLUMN "id" ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME "public"."django_content_type_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: django_migrations; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE "public"."django_migrations" (
    "id" bigint NOT NULL,
    "app" character varying(255) NOT NULL,
    "name" character varying(255) NOT NULL,
    "applied" timestamp with time zone NOT NULL
);


ALTER TABLE "public"."django_migrations" OWNER TO "postgres";

--
-- Name: django_migrations_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE "public"."django_migrations" ALTER COLUMN "id" ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME "public"."django_migrations_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: django_session; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE "public"."django_session" (
    "session_key" character varying(40) NOT NULL,
    "session_data" "text" NOT NULL,
    "expire_date" timestamp with time zone NOT NULL
);


ALTER TABLE "public"."django_session" OWNER TO "postgres";

--
-- Name: django_site; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE "public"."django_site" (
    "id" integer NOT NULL,
    "domain" character varying(100) NOT NULL,
    "name" character varying(50) NOT NULL
);


ALTER TABLE "public"."django_site" OWNER TO "postgres";

--
-- Name: django_site_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE "public"."django_site" ALTER COLUMN "id" ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME "public"."django_site_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: socialaccount_socialaccount; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE "public"."socialaccount_socialaccount" (
    "id" integer NOT NULL,
    "provider" character varying(200) NOT NULL,
    "uid" character varying(191) NOT NULL,
    "last_login" timestamp with time zone NOT NULL,
    "date_joined" timestamp with time zone NOT NULL,
    "extra_data" "jsonb" NOT NULL,
    "user_id" integer NOT NULL
);


ALTER TABLE "public"."socialaccount_socialaccount" OWNER TO "postgres";

--
-- Name: socialaccount_socialaccount_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE "public"."socialaccount_socialaccount" ALTER COLUMN "id" ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME "public"."socialaccount_socialaccount_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: socialaccount_socialapp; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE "public"."socialaccount_socialapp" (
    "id" integer NOT NULL,
    "provider" character varying(30) NOT NULL,
    "name" character varying(40) NOT NULL,
    "client_id" character varying(191) NOT NULL,
    "secret" character varying(191) NOT NULL,
    "key" character varying(191) NOT NULL,
    "provider_id" character varying(200) NOT NULL,
    "settings" "jsonb" NOT NULL
);


ALTER TABLE "public"."socialaccount_socialapp" OWNER TO "postgres";

--
-- Name: socialaccount_socialapp_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE "public"."socialaccount_socialapp" ALTER COLUMN "id" ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME "public"."socialaccount_socialapp_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: socialaccount_socialapp_sites; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE "public"."socialaccount_socialapp_sites" (
    "id" bigint NOT NULL,
    "socialapp_id" integer NOT NULL,
    "site_id" integer NOT NULL
);


ALTER TABLE "public"."socialaccount_socialapp_sites" OWNER TO "postgres";

--
-- Name: socialaccount_socialapp_sites_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE "public"."socialaccount_socialapp_sites" ALTER COLUMN "id" ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME "public"."socialaccount_socialapp_sites_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: socialaccount_socialtoken; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE "public"."socialaccount_socialtoken" (
    "id" integer NOT NULL,
    "token" "text" NOT NULL,
    "token_secret" "text" NOT NULL,
    "expires_at" timestamp with time zone,
    "account_id" integer NOT NULL,
    "app_id" integer
);


ALTER TABLE "public"."socialaccount_socialtoken" OWNER TO "postgres";

--
-- Name: socialaccount_socialtoken_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE "public"."socialaccount_socialtoken" ALTER COLUMN "id" ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME "public"."socialaccount_socialtoken_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: token_blacklist_blacklistedtoken; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE "public"."token_blacklist_blacklistedtoken" (
    "id" bigint NOT NULL,
    "blacklisted_at" timestamp with time zone NOT NULL,
    "token_id" bigint NOT NULL
);


ALTER TABLE "public"."token_blacklist_blacklistedtoken" OWNER TO "postgres";

--
-- Name: token_blacklist_blacklistedtoken_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE "public"."token_blacklist_blacklistedtoken" ALTER COLUMN "id" ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME "public"."token_blacklist_blacklistedtoken_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: token_blacklist_outstandingtoken; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE "public"."token_blacklist_outstandingtoken" (
    "id" bigint NOT NULL,
    "token" "text" NOT NULL,
    "created_at" timestamp with time zone,
    "expires_at" timestamp with time zone NOT NULL,
    "user_id" integer,
    "jti" character varying(255) NOT NULL
);


ALTER TABLE "public"."token_blacklist_outstandingtoken" OWNER TO "postgres";

--
-- Name: token_blacklist_outstandingtoken_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE "public"."token_blacklist_outstandingtoken" ALTER COLUMN "id" ADD GENERATED BY DEFAULT AS IDENTITY (
    SEQUENCE NAME "public"."token_blacklist_outstandingtoken_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Data for Name: account_emailaddress; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY "public"."account_emailaddress" ("id", "email", "verified", "primary", "user_id") FROM stdin;
\.


--
-- Data for Name: account_emailconfirmation; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY "public"."account_emailconfirmation" ("id", "created", "sent", "key", "email_address_id") FROM stdin;
\.


--
-- Data for Name: auth_group; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY "public"."auth_group" ("id", "name") FROM stdin;
\.


--
-- Data for Name: auth_group_permissions; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY "public"."auth_group_permissions" ("id", "group_id", "permission_id") FROM stdin;
\.


--
-- Data for Name: auth_permission; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY "public"."auth_permission" ("id", "name", "content_type_id", "codename") FROM stdin;
1	Can add log entry	1	add_logentry
2	Can change log entry	1	change_logentry
3	Can delete log entry	1	delete_logentry
4	Can view log entry	1	view_logentry
5	Can add permission	2	add_permission
6	Can change permission	2	change_permission
7	Can delete permission	2	delete_permission
8	Can view permission	2	view_permission
9	Can add group	3	add_group
10	Can change group	3	change_group
11	Can delete group	3	delete_group
12	Can view group	3	view_group
13	Can add user	4	add_user
14	Can change user	4	change_user
15	Can delete user	4	delete_user
16	Can view user	4	view_user
17	Can add content type	5	add_contenttype
18	Can change content type	5	change_contenttype
19	Can delete content type	5	delete_contenttype
20	Can view content type	5	view_contenttype
21	Can add session	6	add_session
22	Can change session	6	change_session
23	Can delete session	6	delete_session
24	Can view session	6	view_session
25	Can add building	7	add_building
26	Can change building	7	change_building
27	Can delete building	7	delete_building
28	Can view building	7	view_building
29	Can add furniture	8	add_furniture
30	Can change furniture	8	change_furniture
31	Can delete furniture	8	delete_furniture
32	Can view furniture	8	view_furniture
33	Can add apartment	9	add_apartment
34	Can change apartment	9	change_apartment
35	Can delete apartment	9	delete_apartment
36	Can view apartment	9	view_apartment
37	Can add tenant	10	add_tenant
38	Can change tenant	10	change_tenant
39	Can delete tenant	10	delete_tenant
40	Can view tenant	10	view_tenant
41	Can add lease	11	add_lease
42	Can change lease	11	change_lease
43	Can delete lease	11	delete_lease
44	Can view lease	11	view_lease
45	Can add dependent	12	add_dependent
46	Can change dependent	12	change_dependent
47	Can delete dependent	12	delete_dependent
48	Can view dependent	12	view_dependent
49	Can add site	13	add_site
50	Can change site	13	change_site
51	Can delete site	13	delete_site
52	Can view site	13	view_site
53	Can add blacklisted token	14	add_blacklistedtoken
54	Can change blacklisted token	14	change_blacklistedtoken
55	Can delete blacklisted token	14	delete_blacklistedtoken
56	Can view blacklisted token	14	view_blacklistedtoken
57	Can add outstanding token	15	add_outstandingtoken
58	Can change outstanding token	15	change_outstandingtoken
59	Can delete outstanding token	15	delete_outstandingtoken
60	Can view outstanding token	15	view_outstandingtoken
61	Can add email address	16	add_emailaddress
62	Can change email address	16	change_emailaddress
63	Can delete email address	16	delete_emailaddress
64	Can view email address	16	view_emailaddress
65	Can add email confirmation	17	add_emailconfirmation
66	Can change email confirmation	17	change_emailconfirmation
67	Can delete email confirmation	17	delete_emailconfirmation
68	Can view email confirmation	17	view_emailconfirmation
69	Can add social account	18	add_socialaccount
70	Can change social account	18	change_socialaccount
71	Can delete social account	18	delete_socialaccount
72	Can view social account	18	view_socialaccount
73	Can add social application	19	add_socialapp
74	Can change social application	19	change_socialapp
75	Can delete social application	19	delete_socialapp
76	Can view social application	19	view_socialapp
77	Can add social application token	20	add_socialtoken
78	Can change social application token	20	change_socialtoken
79	Can delete social application token	20	delete_socialtoken
80	Can view social application token	20	view_socialtoken
81	Can add Locador	21	add_landlord
82	Can change Locador	21	change_landlord
83	Can delete Locador	21	delete_landlord
84	Can view Locador	21	view_landlord
85	Can add Regra do Condomínio	22	add_contractrule
86	Can change Regra do Condomínio	22	change_contractrule
87	Can delete Regra do Condomínio	22	delete_contractrule
88	Can view Regra do Condomínio	22	view_contractrule
89	Can add credit card	23	add_creditcard
90	Can change credit card	23	change_creditcard
91	Can delete credit card	23	delete_creditcard
92	Can view credit card	23	view_creditcard
93	Can add expense category	24	add_expensecategory
94	Can change expense category	24	change_expensecategory
95	Can delete expense category	24	delete_expensecategory
96	Can view expense category	24	view_expensecategory
97	Can add financial settings	25	add_financialsettings
98	Can change financial settings	25	change_financialsettings
99	Can delete financial settings	25	delete_financialsettings
100	Can view financial settings	25	view_financialsettings
101	Can add person	26	add_person
102	Can change person	26	change_person
103	Can delete person	26	delete_person
104	Can view person	26	view_person
105	Can add income	27	add_income
106	Can change income	27	change_income
107	Can delete income	27	delete_income
108	Can view income	27	view_income
109	Can add expense	28	add_expense
110	Can change expense	28	change_expense
111	Can delete expense	28	delete_expense
112	Can view expense	28	view_expense
113	Can add employee payment	29	add_employeepayment
114	Can change employee payment	29	change_employeepayment
115	Can delete employee payment	29	delete_employeepayment
116	Can view employee payment	29	view_employeepayment
117	Can add person income	30	add_personincome
118	Can change person income	30	change_personincome
119	Can delete person income	30	delete_personincome
120	Can view person income	30	view_personincome
121	Can add rent payment	31	add_rentpayment
122	Can change rent payment	31	change_rentpayment
123	Can delete rent payment	31	delete_rentpayment
124	Can view rent payment	31	view_rentpayment
125	Can add expense installment	32	add_expenseinstallment
126	Can change expense installment	32	change_expenseinstallment
127	Can delete expense installment	32	delete_expenseinstallment
128	Can view expense installment	32	view_expenseinstallment
129	Can add person payment	33	add_personpayment
130	Can change person payment	33	change_personpayment
131	Can delete person payment	33	delete_personpayment
132	Can view person payment	33	view_personpayment
133	Can add rent adjustment	34	add_rentadjustment
134	Can change rent adjustment	34	change_rentadjustment
135	Can delete rent adjustment	34	delete_rentadjustment
136	Can view rent adjustment	34	view_rentadjustment
137	Can add ipca index	35	add_ipcaindex
138	Can change ipca index	35	change_ipcaindex
139	Can delete ipca index	35	delete_ipcaindex
140	Can view ipca index	35	view_ipcaindex
141	Can add person payment schedule	36	add_personpaymentschedule
142	Can change person payment schedule	36	change_personpaymentschedule
143	Can delete person payment schedule	36	delete_personpaymentschedule
144	Can view person payment schedule	36	view_personpaymentschedule
145	Can add expense month skip	37	add_expensemonthskip
146	Can change expense month skip	37	change_expensemonthskip
147	Can delete expense month skip	37	delete_expensemonthskip
148	Can view expense month skip	37	view_expensemonthskip
149	Can add month snapshot	38	add_monthsnapshot
150	Can change month snapshot	38	change_monthsnapshot
151	Can delete month snapshot	38	delete_monthsnapshot
152	Can view month snapshot	38	view_monthsnapshot
153	Can add device token	39	add_devicetoken
154	Can change device token	39	change_devicetoken
155	Can delete device token	39	delete_devicetoken
156	Can view device token	39	view_devicetoken
157	Can add whats app verification	40	add_whatsappverification
158	Can change whats app verification	40	change_whatsappverification
159	Can delete whats app verification	40	delete_whatsappverification
160	Can view whats app verification	40	view_whatsappverification
161	Can add notification	41	add_notification
162	Can change notification	41	change_notification
163	Can delete notification	41	delete_notification
164	Can view notification	41	view_notification
165	Can add payment proof	42	add_paymentproof
166	Can change payment proof	42	change_paymentproof
167	Can delete payment proof	42	delete_paymentproof
168	Can view payment proof	42	view_paymentproof
169	Can add o auth exchange code	43	add_oauthexchangecode
170	Can change o auth exchange code	43	change_oauthexchangecode
171	Can delete o auth exchange code	43	delete_oauthexchangecode
172	Can view o auth exchange code	43	view_oauthexchangecode
\.


--
-- Data for Name: auth_user; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY "public"."auth_user" ("id", "password", "last_login", "is_superuser", "username", "first_name", "last_name", "email", "is_staff", "is_active", "date_joined") FROM stdin;
5	pbkdf2_sha256$720000$w6bxNKx23C40mBohM77Da7$CFdVkjpZl4iG9WiHFMzXWTucCLCMgulm/YO8hVF2Fw4=	\N	t	alvarosps			alvaro123sps@gmail.com	t	t	2025-12-23 11:34:13.588588-03
6	pbkdf2_sha256$1000000$c9zfVy0v0xJH7PR766WGU6$ap/q79one1yzTtEhiSRkxTzD7pGRkygo7HM6+M3RAYg=	\N	f	debug_admin			debug@test.com	t	t	2026-03-24 00:52:59.068827-03
7	pbkdf2_sha256$1000000$PVRLm3PIS1v9oohwueDaIe$GsEgTByE5Rqp+cOZxuDaWpxhijruF7hZQSgYkpcdnYU=	\N	t	testadmin2				t	t	2026-03-24 10:14:25.400898-03
8	pbkdf2_sha256$1000000$3CHfY8V4QFqFh6uSvXp5vl$jbB7JWOlkTO6U9ouLMeLWPLnnhLrHJpTEXuvAZhGQNo=	\N	t	admin_test_debug			debug@test.com	t	t	2026-03-26 14:19:13.596512-03
3	pbkdf2_sha256$1000000$H6lKD2l9ZrxsPMgpFHp0iM$WBI+jfKyzm8PyS4PI6FvEQJeHycyHYQ23uGRafINyQg=	2026-04-05 15:02:03.047948-03	t	admin			admin@admin.com	t	t	2025-05-22 10:44:13.404187-03
16	pbkdf2_sha256$1000000$LeJg5CHhpd00gIlD3YiGue$TZVBGPiONlMVO99pLVoL1K3YhowSQLaqebc03RQHXFQ=	\N	t	admin.condominio			admin@gerenciadorcondominios.com.br	t	t	2026-06-01 16:35:55.620962-03
\.


--
-- Data for Name: auth_user_groups; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY "public"."auth_user_groups" ("id", "user_id", "group_id") FROM stdin;
\.


--
-- Data for Name: auth_user_user_permissions; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY "public"."auth_user_user_permissions" ("id", "user_id", "permission_id") FROM stdin;
\.


--
-- Data for Name: core_apartment; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY "public"."core_apartment" ("id", "number", "rental_value", "cleaning_fee", "max_tenants", "is_rented", "last_rent_increase_date", "building_id", "created_at", "created_by_id", "deleted_at", "deleted_by_id", "is_deleted", "updated_at", "updated_by_id", "owner_id", "rental_value_double") FROM stdin;
44	201	1800.00	200.00	2	f	\N	3	2026-03-26 13:44:22.382586-03	\N	2026-03-27 10:41:46.215015-03	\N	t	2026-03-26 13:44:22.382589-03	\N	\N	\N
46	102	1800.00	250.00	2	f	\N	5	2026-03-26 14:19:13.868916-03	8	2026-03-27 10:41:50.029391-03	\N	t	2026-03-26 14:19:13.868919-03	8	\N	\N
2	204	1250.00	100.00	2	t	2026-02-22	1	2025-12-21 13:19:51.309441-03	\N	\N	\N	f	2026-03-27 11:50:26.226861-03	\N	\N	1350.00
13	205	934.00	100.00	1	t	2026-03-27	2	2025-12-21 13:19:51.309441-03	\N	\N	\N	f	2026-03-27 11:56:10.637617-03	\N	\N	\N
21	109	730.00	50.00	1	t	2025-04-30	1	2025-12-21 13:19:51.309441-03	\N	\N	\N	f	2025-12-21 13:19:51.372958-03	\N	\N	\N
4	208	750.00	100.00	1	t	2025-03-07	1	2025-12-21 13:19:51.309441-03	\N	\N	\N	f	2025-12-21 13:19:51.372958-03	\N	\N	\N
22	110	750.00	100.00	1	t	2025-01-13	1	2025-12-21 13:19:51.309441-03	\N	\N	\N	f	2025-12-21 13:19:51.372958-03	\N	\N	\N
20	107	745.00	80.00	1	t	2025-02-11	1	2025-12-21 13:19:51.309441-03	\N	\N	\N	f	2025-12-21 13:19:51.372958-03	\N	\N	\N
14	206	1200.00	100.00	2	t	2024-11-17	2	2025-12-21 13:19:51.309441-03	\N	\N	\N	f	2026-03-27 11:56:32.982822-03	\N	\N	1300.00
9	104	900.00	100.00	1	f	2025-05-18	2	2025-12-21 13:19:51.309441-03	\N	\N	\N	f	2026-03-26 12:50:11.274919-03	\N	\N	\N
6	106	1000.00	100.00	2	t	2025-04-08	1	2025-12-21 13:19:51.309441-03	\N	\N	\N	f	2025-12-21 13:19:51.372958-03	\N	\N	1100.00
1	113	1300.00	100.00	2	t	2026-02-02	1	2025-12-21 13:19:51.309441-03	\N	\N	\N	f	2026-03-24 13:29:39.555572-03	\N	\N	1400.00
10	105	1000.00	100.00	2	t	2026-02-01	2	2025-12-21 13:19:51.309441-03	\N	\N	\N	f	2026-03-24 13:21:02.291699-03	\N	\N	1100.00
11	201	934.00	100.00	1	t	2025-05-07	2	2025-12-21 13:19:51.309441-03	\N	\N	\N	f	2025-12-21 13:19:51.372958-03	\N	\N	\N
39	212	900.00	100.00	2	t	2025-09-10	1	2025-12-21 13:19:51.309441-03	\N	\N	\N	f	2026-03-27 11:53:04.831951-03	\N	\N	1000.00
41	214	1250.00	100.00	1	t	2026-03-02	1	2025-12-21 13:19:51.309441-03	\N	\N	\N	f	2026-03-26 13:13:04.324551-03	\N	\N	\N
40	213	860.00	100.00	1	t	2025-08-14	1	2025-12-21 13:19:51.309441-03	\N	\N	\N	f	2026-03-27 11:53:28.704557-03	\N	\N	\N
28	118	630.00	80.00	1	f	2025-04-21	1	2025-12-21 13:19:51.309441-03	\N	2026-03-24 14:17:15.096984-03	\N	t	2025-12-21 13:19:51.372958-03	\N	\N	\N
3	202	1400.00	100.00	2	t	2026-03-25	2	2025-12-21 13:19:51.309441-03	\N	\N	\N	f	2026-03-27 11:55:35.451339-03	\N	\N	1500.00
36	209	900.00	100.00	1	t	2026-05-15	1	2025-12-21 13:19:51.309441-03	\N	\N	\N	f	2026-03-27 14:22:06.659317-03	\N	\N	\N
18	104	1300.00	100.00	2	f	2026-03-24	1	2025-12-21 13:19:51.309441-03	\N	\N	\N	f	2026-03-26 10:15:59.015309-03	\N	\N	1400.00
16	102	1200.00	100.00	2	t	2025-12-04	1	2025-12-21 13:19:51.309441-03	\N	\N	\N	f	2026-03-27 11:42:05.649284-03	\N	\N	1300.00
15	101	1300.00	100.00	2	t	2026-03-27	1	2025-12-21 13:19:51.309441-03	\N	\N	\N	f	2026-03-27 11:46:06.242276-03	\N	2	1400.00
7	115	680.00	100.00	1	f	2025-03-21	1	2025-12-21 13:19:51.309441-03	\N	\N	\N	f	2025-12-21 13:19:51.372958-03	\N	\N	\N
26	116	745.00	80.00	1	f	2025-02-01	1	2025-12-21 13:19:51.309441-03	\N	\N	\N	f	2025-12-21 13:19:51.372958-03	\N	\N	\N
43	100	1300.00	100.00	2	t	2025-03-22	2	2025-12-21 13:19:51.309441-03	\N	\N	\N	f	2025-12-21 13:19:51.372958-03	\N	\N	1400.00
37	210	860.00	100.00	1	t	2025-02-18	1	2025-12-21 13:19:51.309441-03	\N	\N	\N	f	2025-12-21 13:19:51.372958-03	\N	\N	\N
27	117	730.00	100.00	1	t	2025-05-27	1	2025-12-21 13:19:51.309441-03	\N	\N	\N	f	2025-12-21 13:19:51.372958-03	\N	\N	\N
17	103	1300.00	100.00	2	t	2026-03-27	1	2025-12-21 13:19:51.309441-03	\N	\N	\N	f	2026-03-27 11:46:31.390606-03	\N	2	1400.00
33	205	934.00	100.00	1	t	2025-05-15	1	2025-12-21 13:19:51.309441-03	\N	\N	\N	f	2025-12-21 13:19:51.372958-03	\N	\N	\N
42	108	810.00	100.00	1	t	2025-11-20	1	2025-12-21 13:19:51.309441-03	\N	\N	\N	f	2025-12-21 13:19:51.372958-03	\N	\N	\N
19	105	1100.00	100.00	1	t	2025-11-20	1	2025-12-21 13:19:51.309441-03	\N	\N	\N	f	2025-12-21 13:19:51.372958-03	\N	\N	\N
25	114	630.00	80.00	1	t	2026-01-08	1	2025-12-21 13:19:51.309441-03	\N	\N	\N	f	2026-03-27 11:48:22.171873-03	\N	\N	\N
29	200	1400.00	100.00	2	t	2026-01-30	1	2025-12-21 13:19:51.309441-03	\N	\N	\N	f	2026-03-27 11:48:55.945659-03	\N	3	1500.00
23	111	890.00	100.00	2	t	2025-11-20	1	2025-12-21 13:19:51.309441-03	\N	\N	\N	f	2025-12-21 13:19:51.372958-03	\N	\N	990.00
24	112	934.00	100.00	2	t	2025-11-20	1	2025-12-21 13:19:51.309441-03	\N	\N	\N	f	2025-12-21 13:19:51.372958-03	\N	\N	1034.00
30	201	1300.00	100.00	2	t	2025-12-05	1	2025-12-21 13:19:51.309441-03	\N	\N	\N	f	2026-03-27 11:49:20.088023-03	\N	\N	1400.00
31	202	950.00	100.00	2	t	2025-05-01	1	2025-12-21 13:19:51.309441-03	\N	\N	\N	f	2026-03-27 11:49:47.230557-03	\N	\N	1050.00
12	203	1400.00	100.00	1	t	2026-01-01	2	2025-12-21 13:19:51.309441-03	\N	\N	\N	f	2026-03-26 13:05:27.965496-03	\N	\N	\N
32	203	1400.00	100.00	2	t	2025-11-20	1	2025-12-21 13:19:51.309441-03	\N	\N	\N	f	2025-12-21 13:19:51.372958-03	\N	3	1500.00
8	103	1200.00	100.00	2	t	2026-03-13	2	2025-12-21 13:19:51.309441-03	\N	\N	\N	f	2026-03-24 13:08:00.670775-03	\N	\N	1300.00
5	204	1400.00	100.00	2	f	2025-11-20	2	2025-12-21 13:19:51.309441-03	\N	\N	\N	f	2025-12-21 13:19:51.372958-03	\N	\N	1500.00
34	206	750.00	100.00	1	t	2025-07-30	1	2025-12-21 13:19:51.309441-03	\N	\N	\N	f	2026-03-27 11:51:27.140189-03	\N	\N	\N
35	207	1400.00	100.00	2	t	2026-03-07	1	2025-12-21 13:19:51.309441-03	\N	\N	\N	f	2026-03-27 11:51:48.330558-03	\N	\N	1500.00
38	211	892.00	100.00	1	t	2025-12-09	1	2025-12-21 13:19:51.309441-03	\N	\N	\N	f	2026-03-27 11:52:43.225133-03	\N	\N	\N
\.


--
-- Data for Name: core_apartment_furnitures; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY "public"."core_apartment_furnitures" ("id", "apartment_id", "furniture_id") FROM stdin;
1	1	1
2	1	2
3	1	3
4	1	4
5	1	5
6	1	6
7	1	7
8	1	8
9	1	9
12	2	1
13	2	2
14	2	3
15	2	4
16	2	5
17	2	6
18	2	7
19	2	8
20	2	10
21	2	11
22	3	1
23	3	2
24	3	3
25	3	5
26	3	6
27	3	7
28	3	8
29	3	9
30	3	10
31	3	11
32	3	12
33	3	13
34	4	1
35	4	3
36	4	5
37	4	8
38	4	10
39	4	11
40	4	12
41	4	14
42	4	15
43	4	16
44	5	1
45	5	2
46	5	3
47	5	4
48	5	5
49	5	6
50	5	7
51	5	8
52	5	9
53	5	10
54	5	11
55	5	13
56	6	1
57	6	2
58	6	3
59	6	4
60	6	5
61	6	6
62	6	7
63	6	8
64	6	10
65	6	11
66	6	17
67	7	1
68	7	2
69	7	3
70	7	5
71	7	6
72	7	8
73	7	11
74	7	13
75	7	16
76	8	1
77	8	2
78	8	3
79	8	4
80	8	5
81	8	6
82	8	7
83	8	8
84	8	10
85	8	11
86	9	1
87	9	2
88	9	3
89	9	4
90	9	5
91	9	6
92	9	9
93	9	11
94	9	16
95	9	18
96	9	19
97	10	1
98	10	2
99	10	3
100	10	4
101	10	5
102	10	6
103	10	7
104	10	10
105	11	1
106	11	2
107	11	3
108	11	5
109	11	6
110	11	7
111	11	10
112	11	11
113	12	1
114	12	2
115	12	3
116	12	4
117	12	5
118	12	6
119	12	7
120	12	8
121	12	9
122	12	10
123	12	11
124	12	13
125	12	18
126	13	1
127	13	2
128	13	3
129	13	4
130	13	5
131	13	6
132	13	7
133	13	8
134	13	10
135	13	11
136	14	1
137	14	3
138	14	5
139	14	6
140	14	7
141	14	8
142	14	9
143	14	10
144	14	11
145	14	19
146	14	20
147	14	21
148	15	1
149	15	2
150	15	3
151	15	4
152	15	5
153	15	6
154	15	7
155	15	8
156	15	10
157	15	11
158	15	19
159	15	22
160	16	1
161	16	3
162	16	4
163	16	6
164	16	7
165	16	8
166	16	9
167	16	10
168	16	11
169	16	23
170	16	24
171	16	25
172	17	1
173	17	2
174	17	3
175	17	4
176	17	5
177	17	6
178	17	7
179	17	8
180	17	10
181	17	11
182	18	1
183	18	3
184	18	5
185	18	6
186	18	7
187	18	8
188	18	10
189	18	11
190	18	12
191	18	13
192	18	23
193	19	1
194	19	3
195	19	4
196	19	5
197	19	6
198	19	7
199	19	8
200	19	9
201	19	10
202	19	11
203	19	17
204	19	23
205	20	1
206	20	2
207	20	3
208	20	5
209	20	8
210	20	10
211	20	11
212	20	16
213	21	1
214	21	3
215	21	5
216	21	6
217	21	8
218	21	10
219	21	11
220	21	16
221	21	18
222	21	27
223	22	1
224	22	2
225	22	3
226	22	5
227	22	6
228	22	10
229	22	11
230	22	16
231	23	1
232	23	3
233	23	5
234	23	6
235	23	7
236	23	8
237	23	10
238	23	11
239	23	13
240	23	23
241	23	28
242	24	1
243	24	2
244	24	3
245	24	5
246	24	6
247	24	7
248	24	8
249	24	10
250	24	11
251	24	12
252	25	1
253	25	2
254	25	3
255	25	5
256	25	6
257	25	8
258	25	11
259	25	16
260	25	19
261	26	1
262	26	2
263	26	3
264	26	5
265	26	6
266	26	11
267	26	16
268	27	1
269	27	3
270	27	5
271	27	6
272	27	8
273	27	9
274	27	10
275	27	11
276	27	18
277	27	19
278	27	29
279	28	3
280	28	6
281	28	8
282	28	11
283	28	14
284	28	19
285	28	30
286	28	31
287	29	32
288	29	1
289	29	34
290	29	3
291	29	35
292	29	6
293	29	8
294	29	10
295	29	11
296	29	13
297	29	25
298	29	28
299	30	1
300	30	3
301	30	35
302	30	36
303	30	6
304	30	8
305	30	10
306	30	11
307	30	12
308	30	13
309	30	23
310	31	1
311	31	2
312	31	3
313	31	5
314	31	6
315	31	7
316	31	8
317	31	9
318	31	10
319	31	11
320	31	12
321	31	18
322	31	19
323	32	1
324	32	3
325	32	35
326	32	5
327	32	6
328	32	37
329	32	8
330	32	38
331	32	10
332	32	11
333	32	12
334	32	23
335	32	28
336	33	1
337	33	2
338	33	3
339	33	4
340	33	5
341	33	6
342	33	7
343	33	8
344	33	10
345	33	11
346	34	1
347	34	3
348	34	5
349	34	8
350	34	9
351	34	10
352	34	11
353	34	27
354	35	1
355	35	3
356	35	4
357	35	5
358	35	6
359	35	39
360	35	8
361	35	9
362	35	10
363	35	11
364	35	19
365	36	1
366	36	2
367	36	3
368	36	4
369	36	5
370	36	6
371	36	7
372	36	8
373	36	10
374	36	11
375	37	1
376	37	2
377	37	3
378	37	5
379	37	7
380	37	10
381	37	11
382	38	1
383	38	3
384	38	4
385	38	5
386	38	6
387	38	7
388	38	8
389	38	9
390	38	10
391	38	11
392	38	19
393	38	27
394	39	1
395	39	3
396	39	6
397	39	7
398	39	8
399	39	9
400	39	10
401	39	11
402	39	12
403	39	19
404	39	23
405	40	32
406	40	1
407	40	3
408	40	5
409	40	6
410	40	7
411	40	8
412	40	9
413	40	10
414	40	11
415	40	12
416	40	13
417	40	40
418	41	1
419	41	2
420	41	3
421	41	5
422	41	6
423	41	7
424	41	8
425	41	12
426	41	19
427	42	1
429	42	3
430	42	5
431	42	6
433	42	19
434	42	32
435	42	41
436	43	1
437	43	2
438	43	3
439	43	4
440	43	5
441	43	6
442	43	35
443	43	8
444	43	10
445	43	11
446	39	25
447	1	10
448	1	11
\.


--
-- Data for Name: core_building; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY "public"."core_building" ("id", "street_number", "name", "address", "created_at", "created_by_id", "deleted_at", "deleted_by_id", "is_deleted", "updated_at", "updated_by_id") FROM stdin;
1	836	Condomínio Steinmetz	Av. Circular 836	2025-12-21 13:19:51.387958-03	\N	\N	\N	f	2025-12-21 13:19:51.439957-03	\N
2	850	Condomínio Bielavicius	Av. Circular 850	2025-12-21 13:19:51.387958-03	\N	\N	\N	f	2025-12-21 13:19:51.439957-03	\N
4	99999	Teste 99999	Endereço teste 99999	2026-03-26 14:14:15.187185-03	\N	2026-03-26 18:12:06.388762-03	\N	t	2026-03-26 14:14:15.187191-03	\N
3	7777	Test	Test	2026-03-26 13:44:22.33897-03	\N	2026-03-27 10:41:56.449433-03	\N	t	2026-03-26 13:44:22.338976-03	\N
5	19999	Debug Bld	Debug Addr	2026-03-26 14:19:13.866412-03	8	2026-03-27 10:41:58.672379-03	\N	t	2026-03-26 14:19:13.866416-03	8
\.


--
-- Data for Name: core_contractrule; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY "public"."core_contractrule" ("id", "created_at", "updated_at", "is_deleted", "deleted_at", "content", "order", "is_active", "created_by_id", "updated_by_id", "deleted_by_id") FROM stdin;
1	2026-01-20 15:05:31.899324-03	2026-01-20 15:05:31.899327-03	f	\N	É <strong>proíbido fumar</strong> nas <strong>áreas comuns</strong> do condomínio, <strong>inclusive</strong> na <strong>área comum entre os 2 portões de frente na</strong><strong> Avenida Circular 836</strong>, e na <strong>garagem da Avenida Circular 850</strong>. Dentro dos kitnets é permitido fumar, porém é obrigatório fechar as janelas.	0	t	\N	\N	\N
2	2026-01-20 15:05:31.902743-03	2026-01-20 15:05:31.902745-03	f	\N	É <strong>proibído perturbar o sossego e o bem-estar público</strong> da população pela emissão de sons e ruídos  por quaisquer fontes ou atividades que ultrapassem os níveis máximos de intensidade fixados por lei. O <strong>horário de silêncio</strong> é <strong>entre 23:00 e 8:00 de Domingo a</strong><strong> Segunda-feira</strong> e <strong>entre 00:00 e 9:00 na Sexta-feira e Sábado</strong>.<strong> Vale ressaltar que fora desse horário nãó é permitido sons que perturbem os vizinhos durante o dia</strong>.	1	t	\N	\N	\N
3	2026-01-20 15:05:31.903188-03	2026-01-20 15:05:31.90319-03	f	\N	Áreas comuns, como a área de frente do prédio e corredores, são de propriedade do condomínio, motivo pelo qual nenhum morador pode utilizá-la para seu interesse particular, como armazenamento de itens pessoais ou outros usos particulares. A <strong>única exceção</strong> é que o LOCADOR permite que <strong>motocicletas</strong> sejam deixados na área comum em frente ao condomínio, <strong>entre os 2 portões de frente na Av. Circular 836</strong>.	2	t	\N	\N	\N
4	2026-01-20 15:05:31.903554-03	2026-01-20 15:05:31.903557-03	f	\N	<strong>É proíbido deixar qualquer portão do condomínio aberto.</strong>	3	t	\N	\N	\N
5	2026-01-20 15:05:31.90388-03	2026-01-20 15:05:31.903885-03	f	\N	<strong>É proíbido abrir o portão para não moradores do condomínio, sem consentimento da pessoa que está sendo buscada. Para receber</strong><strong> visitas ou entregas, SEMPRE INFORME O NÚMERO DO SEU APARTAMENTO, para receber a ligação do interfone e poder ir até o portão</strong><strong> para receber a visita / entrega</strong>.	4	t	\N	\N	\N
6	2026-01-20 15:05:31.904224-03	2026-01-20 15:05:31.904227-03	f	\N	É <strong>proíbido</strong> a moradia de <strong>animais de estimação</strong> nos kitnets, e também a circulação dos mesmos nas áreas comuns do condomínio.	5	t	\N	\N	\N
7	2026-01-20 15:05:31.904964-03	2026-01-20 15:05:31.904966-03	f	\N	Para <strong>moradores da Av. Circular 850, é proíbido o uso da garagem</strong>, para deixar <strong>qualquer tipo de veículo</strong>.	6	t	\N	\N	\N
\.


--
-- Data for Name: core_creditcard; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY "public"."core_creditcard" ("id", "created_at", "updated_at", "is_deleted", "deleted_at", "nickname", "last_four_digits", "closing_day", "due_day", "is_active", "created_by_id", "deleted_by_id", "updated_by_id", "person_id") FROM stdin;
1	2026-03-22 22:48:04.274084-03	2026-03-22 22:48:04.274088-03	f	\N	Itau Azul Rodrigo	7160	1	9	t	\N	\N	\N	1
2	2026-03-22 22:48:04.277303-03	2026-03-22 22:48:04.277305-03	f	\N	Itau Visa Rodrigo	9608	27	3	t	\N	\N	\N	1
3	2026-03-22 22:48:04.279373-03	2026-03-22 22:48:04.279375-03	f	\N	Caixa Rodrigo	5443	27	7	t	\N	\N	\N	1
4	2026-03-22 22:48:04.281055-03	2026-03-22 22:48:04.281057-03	f	\N	Trigg Alvaro		1	10	t	\N	\N	\N	3
5	2026-03-22 22:48:04.282568-03	2026-03-22 22:48:04.28257-03	f	\N	Players Alvaro		1	10	t	\N	\N	\N	3
6	2026-03-22 22:48:04.284147-03	2026-03-22 22:48:04.284149-03	f	\N	Samsung Alvaro		1	10	t	\N	\N	\N	3
7	2026-03-22 22:48:04.2856-03	2026-03-22 22:48:04.285601-03	f	\N	Nubank Camila	7957	8	16	t	\N	\N	\N	6
8	2026-03-22 22:48:04.287098-03	2026-03-22 22:48:04.2871-03	f	\N	Renner Camila	2581	9	25	t	\N	\N	\N	6
9	2026-03-22 22:48:04.288382-03	2026-03-22 22:48:04.288384-03	f	\N	Mercado Pago Camila	4609	15	20	t	\N	\N	\N	6
\.


--
-- Data for Name: core_dependent; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY "public"."core_dependent" ("id", "name", "phone", "tenant_id", "created_at", "created_by_id", "deleted_at", "deleted_by_id", "is_deleted", "updated_at", "updated_by_id", "cpf_cnpj") FROM stdin;
1	Vanessa Baia	(92) 98425-5480	1	2025-12-21 13:19:51.45996-03	\N	\N	\N	f	2025-12-21 13:19:51.51947-03	\N	\N
2	Rafael Farias	(51) 99142-3261	28	2025-12-21 13:19:51.45996-03	\N	\N	\N	f	2025-12-21 13:19:51.51947-03	\N	\N
\.


--
-- Data for Name: core_devicetoken; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY "public"."core_devicetoken" ("id", "created_at", "updated_at", "token", "platform", "is_active", "created_by_id", "updated_by_id", "user_id") FROM stdin;
\.


--
-- Data for Name: core_employeepayment; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY "public"."core_employeepayment" ("id", "created_at", "updated_at", "is_deleted", "deleted_at", "reference_month", "base_salary", "variable_amount", "rent_offset", "cleaning_count", "payment_date", "is_paid", "notes", "created_by_id", "deleted_by_id", "updated_by_id", "person_id") FROM stdin;
1	2026-03-22 22:49:56.318539-03	2026-03-23 19:39:44.402133-03	f	\N	2026-03-01	800.00	400.00	0.00	0	2026-03-05	t	Salário fixo R$800 + variável por serviços extras (faxinas, etc). rent_offset = valor do aluguel do kitnet 206/850 (informativo, não sai do caixa).	\N	\N	\N	5
3	2026-04-01 15:35:18.259489-03	2026-04-01 15:35:18.259493-03	f	\N	2026-04-01	800.00	0.00	0.00	0	\N	f		\N	\N	\N	5
\.


--
-- Data for Name: core_expense; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY "public"."core_expense" ("id", "created_at", "updated_at", "is_deleted", "deleted_at", "description", "expense_type", "total_amount", "expense_date", "is_installment", "total_installments", "is_debt_installment", "is_recurring", "expected_monthly_amount", "recurrence_day", "is_paid", "paid_date", "bank_name", "interest_rate", "notes", "building_id", "created_by_id", "credit_card_id", "deleted_by_id", "updated_by_id", "category_id", "person_id", "is_offset", "end_date") FROM stdin;
1	2026-03-22 22:49:55.273938-03	2026-03-22 22:49:55.273941-03	f	\N	MEGA BRICK	card_purchase	600.00	2025-10-28	t	10	f	f	\N	\N	f	\N		\N		\N	\N	1	\N	\N	3	1	f	\N
2	2026-03-22 22:49:55.305994-03	2026-03-22 22:49:55.305997-03	f	\N	SHOPEE *Hippie outros Bauru	card_purchase	541.98	2025-12-05	t	9	f	f	\N	\N	f	\N		\N		\N	\N	1	\N	\N	\N	1	f	\N
3	2026-03-22 22:49:55.311778-03	2026-03-22 22:49:55.31178-03	f	\N	PANVEL MATRIZE ELDORADO DO SUL	card_purchase	124.68	2025-12-11	t	4	f	f	\N	\N	f	\N		\N		\N	\N	1	\N	\N	1	1	f	\N
4	2026-03-22 22:49:55.314313-03	2026-03-22 22:49:55.314314-03	f	\N	RENNER CABREUVA	card_purchase	259.56	2025-12-22	t	6	f	f	\N	\N	f	\N		\N		\N	\N	1	\N	\N	4	1	f	\N
5	2026-03-22 22:49:55.317691-03	2026-03-22 22:49:55.317693-03	f	\N	LOJAS RENNER SANTA MARIA	card_purchase	150.00	2025-12-30	t	3	f	f	\N	\N	f	\N		\N	Última parcela	\N	\N	1	\N	\N	4	1	f	\N
6	2026-03-22 22:49:55.320136-03	2026-03-22 22:49:55.320138-03	f	\N	BRAS ATACADO PORTO ALEGRE	card_purchase	281.40	2026-01-06	t	3	f	f	\N	\N	f	\N		\N		\N	\N	1	\N	\N	1	1	f	\N
7	2026-03-22 22:49:55.321996-03	2026-03-22 22:49:55.321998-03	f	\N	SHOPEE *Lapisd Paranavai	card_purchase	149.68	2026-01-08	t	2	f	f	\N	\N	f	\N		\N	Última parcela	\N	\N	1	\N	\N	\N	1	f	\N
8	2026-03-22 22:49:55.323316-03	2026-03-22 22:49:55.323318-03	f	\N	PANVEL FILIAL PORTO ALEGRE	card_purchase	156.54	2026-01-08	t	3	f	f	\N	\N	f	\N		\N		\N	\N	1	\N	\N	1	1	f	\N
9	2026-03-22 22:49:55.324681-03	2026-03-22 22:49:55.324683-03	f	\N	AgroRural GRAVATAI	card_purchase	588.40	2026-01-09	t	2	f	f	\N	\N	f	\N		\N	Última parcela	\N	\N	1	\N	\N	1	1	f	\N
10	2026-03-22 22:49:55.325685-03	2026-03-22 22:49:55.325687-03	f	\N	REFRICRIL DIST PORTO ALEGRE	card_purchase	222.50	2026-01-13	t	2	f	f	\N	\N	f	\N		\N	Última parcela	\N	\N	1	\N	\N	3	1	f	\N
11	2026-03-22 22:49:55.326705-03	2026-03-22 22:49:55.326706-03	f	\N	PANVEL FILIAL PORTO ALEGRE	card_purchase	99.10	2026-01-16	t	2	f	f	\N	\N	f	\N		\N	Última parcela	\N	\N	1	\N	\N	1	1	f	\N
12	2026-03-22 22:49:55.328028-03	2026-03-22 22:49:55.32803-03	f	\N	MERCADO LIVRE Arujá	card_purchase	216.96	2026-02-02	t	2	f	f	\N	\N	f	\N		\N		\N	\N	1	\N	\N	\N	1	f	\N
13	2026-03-22 22:49:55.329356-03	2026-03-22 22:49:55.329357-03	f	\N	MERCADO LIVRE São Paulo	card_purchase	30.46	2026-02-02	t	2	f	f	\N	\N	f	\N		\N		\N	\N	1	\N	\N	\N	1	f	\N
14	2026-03-22 22:49:55.330397-03	2026-03-22 22:49:55.330399-03	f	\N	SHOPEE *Mehlev Lençóis Paulista	card_purchase	234.00	2026-02-03	t	3	f	f	\N	\N	f	\N		\N		\N	\N	1	\N	\N	\N	1	f	\N
15	2026-03-22 22:49:55.331696-03	2026-03-22 22:49:55.331698-03	f	\N	CASAS BAHIA Rio de Janeiro	card_purchase	108.10	2026-02-05	t	2	f	f	\N	\N	f	\N		\N		\N	\N	1	\N	\N	\N	1	f	\N
16	2026-03-22 22:49:55.33368-03	2026-03-22 22:49:55.333682-03	f	\N	MARISA PORTO ALEGRE	card_purchase	180.00	2026-02-06	t	3	f	f	\N	\N	f	\N		\N		\N	\N	1	\N	\N	\N	1	f	\N
17	2026-03-22 22:49:55.335488-03	2026-03-22 22:49:55.33549-03	f	\N	JIM.COM DOUGLA GLORINHA	card_purchase	1073.60	2026-02-12	t	4	f	f	\N	\N	f	\N		\N		\N	\N	1	\N	\N	1	1	f	\N
304	2026-04-01 14:02:44.699514-03	2026-04-01 14:02:44.699518-03	f	\N	PayU*A	card_purchase	799.96	2026-04-01	t	7	f	f	\N	\N	f	\N		\N		\N	\N	6	\N	\N	\N	3	f	\N
311	2026-04-01 14:57:24.667834-03	2026-04-01 14:57:24.667837-03	f	\N	Luz 850	electricity_bill	926.50	2026-04-01	f	\N	f	f	\N	\N	f	\N		\N		2	\N	\N	\N	\N	3	\N	f	\N
33	2026-03-22 22:49:55.34501-03	2026-03-22 22:49:55.345011-03	f	\N	LEROY MERLIN PORTO ALEGRE	card_purchase	708.06	2026-03-06	t	6	f	f	\N	\N	f	\N		\N		\N	\N	1	\N	\N	3	1	f	\N
34	2026-03-22 22:49:55.348107-03	2026-03-22 22:49:55.348108-03	f	\N	MERCADOLIVRE 2 PRODUTOS Borda da Mata	card_purchase	129.96	2026-03-20	t	4	f	f	\N	\N	f	\N		\N		\N	\N	1	\N	\N	\N	1	f	\N
41	2026-03-22 22:49:55.353994-03	2026-03-22 22:49:55.353996-03	f	\N	CLINICA VETERINARIA PORTO ALEGRE	card_purchase	1130.00	2025-11-04	t	5	f	f	\N	\N	f	\N		\N		\N	\N	2	\N	\N	1	1	f	\N
42	2026-03-22 22:49:55.357114-03	2026-03-22 22:49:55.357116-03	f	\N	REFRICRIL DIST PORTO ALEGRE	card_purchase	505.44	2026-01-06	t	3	f	f	\N	\N	f	\N		\N		\N	\N	2	\N	\N	3	1	f	\N
43	2026-03-22 22:49:55.359456-03	2026-03-22 22:49:55.359458-03	f	\N	MSS COMERCIO D PORTO ALEGRE	card_purchase	250.00	2026-01-06	t	5	f	f	\N	\N	f	\N		\N		\N	\N	2	\N	\N	3	1	f	\N
44	2026-03-22 22:49:55.362227-03	2026-03-22 22:49:55.362229-03	f	\N	TORRA TORRA PORTO ALEGRE	card_purchase	204.90	2026-01-06	t	3	f	f	\N	\N	f	\N		\N		\N	\N	2	\N	\N	3	1	f	\N
45	2026-03-22 22:49:55.363972-03	2026-03-22 22:49:55.363973-03	f	\N	PATILLER CALÇADOS PORTO ALEGRE	card_purchase	119.00	2026-01-06	t	2	f	f	\N	\N	f	\N		\N	Última parcela	\N	\N	2	\N	\N	1	1	f	\N
46	2026-03-22 22:49:55.365347-03	2026-03-22 22:49:55.365349-03	f	\N	MEGA BRICK PORTO ALEGRE	card_purchase	1000.00	2026-01-08	t	10	f	f	\N	\N	f	\N		\N		\N	\N	2	\N	\N	3	1	f	\N
47	2026-03-22 22:49:55.370703-03	2026-03-22 22:49:55.370705-03	f	\N	CASA DO PAPEL PORTO ALEGRE	card_purchase	290.49	2026-01-08	t	3	f	f	\N	\N	f	\N		\N		\N	\N	2	\N	\N	1	1	f	\N
48	2026-03-22 22:49:55.372593-03	2026-03-22 22:49:55.372595-03	f	\N	PG *MIXXON MOD São Paulo	card_purchase	597.08	2026-02-04	t	4	f	f	\N	\N	f	\N		\N		\N	\N	2	\N	\N	\N	1	f	\N
49	2026-03-22 22:49:55.375113-03	2026-03-22 22:49:55.375115-03	f	\N	CASAS BAHIA Rio de Janeiro	card_purchase	108.08	2026-02-05	t	2	f	f	\N	\N	f	\N		\N		\N	\N	2	\N	\N	\N	1	f	\N
50	2026-03-22 22:49:55.376572-03	2026-03-22 22:49:55.376574-03	f	\N	00013 SH IGUATEMI PORTO ALEGRE	card_purchase	305.73	2026-02-13	t	3	f	f	\N	\N	f	\N		\N		\N	\N	2	\N	\N	4	1	f	\N
305	2026-04-01 14:03:33.047366-03	2026-04-01 14:03:33.047369-03	f	\N	Mercado livre 1	card_purchase	759.96	2026-04-01	t	12	f	f	\N	\N	f	\N		\N		\N	\N	6	\N	\N	\N	3	f	\N
312	2026-04-01 15:01:20.946169-03	2026-04-01 15:01:20.946172-03	f	\N	Luz 836	electricity_bill	169.97	2026-04-01	f	\N	f	f	\N	\N	f	\N		\N		1	\N	\N	\N	\N	3	\N	f	\N
54	2026-03-22 22:49:55.38031-03	2026-03-22 22:49:55.380312-03	f	\N	CASA MARIA PORTO ALEGRE	card_purchase	413.25	2026-03-03	t	5	f	f	\N	\N	f	\N		\N		\N	\N	2	\N	\N	3	1	f	\N
55	2026-03-22 22:49:55.383913-03	2026-03-22 22:49:55.383915-03	f	\N	MERCADOLIVRE 2 PRODUTOS Auriflama	card_purchase	81.06	2026-03-04	t	3	f	f	\N	\N	f	\N		\N		\N	\N	2	\N	\N	\N	1	f	\N
56	2026-03-22 22:49:55.386086-03	2026-03-22 22:49:55.386088-03	f	\N	PANVEL FILIAL 165 PORTO ALEGRE	card_purchase	91.46	2026-03-04	t	2	f	f	\N	\N	f	\N		\N		\N	\N	2	\N	\N	1	1	f	\N
57	2026-03-22 22:49:55.387686-03	2026-03-22 22:49:55.387688-03	f	\N	PANVEL FILIAL 369 PORTO ALEGRE	card_purchase	218.96	2026-03-11	t	2	f	f	\N	\N	f	\N		\N		\N	\N	2	\N	\N	1	1	f	\N
58	2026-03-22 22:49:55.38895-03	2026-03-22 22:49:55.388952-03	f	\N	00013 SH IGUATEMI POA	card_purchase	179.82	2026-03-20	t	3	f	f	\N	\N	f	\N		\N		\N	\N	2	\N	\N	4	1	f	\N
67	2026-03-22 22:49:55.395388-03	2026-03-22 22:49:55.39539-03	f	\N	SCHUMANN MOVEIS	card_purchase	316.20	2025-05-19	t	10	f	f	\N	\N	f	\N		\N	Última parcela	\N	\N	3	\N	\N	3	1	f	\N
68	2026-03-22 22:49:55.400634-03	2026-03-22 22:49:55.400636-03	f	\N	MEGA BRICK	card_purchase	1300.00	2025-09-09	t	10	f	f	\N	\N	f	\N		\N		\N	\N	3	\N	\N	3	1	f	\N
69	2026-03-22 22:49:55.405364-03	2026-03-22 22:49:55.405367-03	f	\N	SHOPEE AMORDEC	card_purchase	367.80	2025-11-06	t	6	f	f	\N	\N	f	\N		\N		\N	\N	3	\N	\N	\N	1	f	\N
70	2026-03-22 22:49:55.408926-03	2026-03-22 22:49:55.408949-03	f	\N	EC 6P	card_purchase	164.70	2025-12-07	t	5	f	f	\N	\N	f	\N		\N		\N	\N	3	\N	\N	\N	1	f	\N
71	2026-03-22 22:49:55.411963-03	2026-03-22 22:49:55.411965-03	f	\N	FERRAGEM PARATI	card_purchase	1179.24	2025-12-08	t	4	f	f	\N	\N	f	\N		\N	Última parcela	\N	\N	3	\N	\N	3	1	f	\N
72	2026-03-22 22:49:55.414448-03	2026-03-22 22:49:55.41445-03	f	\N	SHOPEE MEHLEVA	card_purchase	224.97	2026-01-10	t	3	f	f	\N	\N	f	\N		\N	Última parcela	\N	\N	3	\N	\N	\N	1	f	\N
73	2026-03-22 22:49:55.416381-03	2026-03-22 22:49:55.416383-03	f	\N	SHOPEE SHPSTEC	card_purchase	388.40	2026-01-24	t	4	f	f	\N	\N	f	\N		\N		\N	\N	3	\N	\N	\N	1	f	\N
74	2026-03-22 22:49:55.418926-03	2026-03-22 22:49:55.418928-03	f	\N	MEGA BRICK	card_purchase	600.00	2026-02-03	t	6	f	f	\N	\N	f	\N		\N		\N	\N	3	\N	\N	3	1	f	\N
75	2026-03-22 22:49:55.422986-03	2026-03-22 22:49:55.422988-03	f	\N	MERCADOLIVRE ME	card_purchase	415.98	2026-02-05	t	2	f	f	\N	\N	f	\N		\N	Última parcela	\N	\N	3	\N	\N	\N	1	f	\N
76	2026-03-22 22:49:55.42461-03	2026-03-22 22:49:55.424612-03	f	\N	SHOPEE MULTIDE	card_purchase	161.12	2026-02-06	t	2	f	f	\N	\N	f	\N		\N	Última parcela	\N	\N	3	\N	\N	\N	1	f	\N
77	2026-03-22 22:49:55.426202-03	2026-03-22 22:49:55.426204-03	f	\N	MERCADOLIVRE 2P	card_purchase	123.22	2026-02-10	t	2	f	f	\N	\N	f	\N		\N	Última parcela	\N	\N	3	\N	\N	\N	1	f	\N
78	2026-03-22 22:49:55.427693-03	2026-03-22 22:49:55.427695-03	f	\N	EC MERCADO	card_purchase	335.96	2026-02-10	t	4	f	f	\N	\N	f	\N		\N		\N	\N	3	\N	\N	\N	1	f	\N
79	2026-03-22 22:49:55.430266-03	2026-03-22 22:49:55.430268-03	f	\N	PAYGO VIDRACARI	card_purchase	355.02	2026-02-12	t	3	f	f	\N	\N	f	\N		\N		\N	\N	3	\N	\N	3	1	f	\N
80	2026-03-22 22:49:55.432446-03	2026-03-22 22:49:55.432448-03	f	\N	AGRORURAL	card_purchase	357.88	2026-02-19	t	2	f	f	\N	\N	f	\N		\N	Última parcela	\N	\N	3	\N	\N	1	1	f	\N
81	2026-03-22 22:49:55.433851-03	2026-03-22 22:49:55.433853-03	f	\N	TUMELERO 019	card_purchase	537.00	2026-03-08	t	6	f	f	\N	\N	f	\N		\N		\N	\N	3	\N	\N	3	1	f	\N
82	2026-03-22 22:49:55.437037-03	2026-03-22 22:49:55.437038-03	f	\N	MERCADOLIVRE 3P	card_purchase	114.34	2026-03-10	t	2	f	f	\N	\N	f	\N		\N		\N	\N	3	\N	\N	\N	1	f	\N
83	2026-03-22 22:49:55.438449-03	2026-03-22 22:49:55.438451-03	f	\N	DUPORTO REFRIGERAÇÃO	card_purchase	100.00	2026-03-11	t	2	f	f	\N	\N	f	\N		\N		\N	\N	3	\N	\N	3	1	f	\N
84	2026-03-22 22:49:55.439821-03	2026-03-22 22:49:55.439823-03	f	\N	EC 2P	card_purchase	107.24	2026-03-14	t	4	f	f	\N	\N	f	\N		\N		\N	\N	3	\N	\N	\N	1	f	\N
85	2026-03-22 22:49:55.442253-03	2026-03-22 22:49:55.442255-03	f	\N	PANVEL FILIAL 3	card_purchase	290.76	2026-03-14	t	3	f	f	\N	\N	f	\N		\N		\N	\N	3	\N	\N	1	1	f	\N
86	2026-03-22 22:49:55.444512-03	2026-03-22 22:49:55.444513-03	f	\N	D TUDO	card_purchase	199.80	2026-03-19	t	3	f	f	\N	\N	f	\N		\N		\N	\N	3	\N	\N	3	1	f	\N
306	2026-04-01 14:10:02.019273-03	2026-04-01 14:10:02.019275-03	f	\N	Mega Brick	card_purchase	400.20	2026-04-01	t	6	f	f	\N	\N	f	\N		\N		\N	\N	6	\N	\N	\N	3	f	\N
105	2026-03-22 22:49:55.456151-03	2026-03-22 22:49:55.456153-03	f	\N	Anuidade Caixa Elo (parcela)	card_purchase	414.00	2025-11-27	t	12	f	f	\N	\N	f	\N		\N	Anuidade anual parcelada em 12x	\N	\N	3	\N	\N	\N	1	f	\N
313	2026-04-01 15:11:36.167842-03	2026-04-01 15:11:36.167845-03	f	\N	Água 836	water_bill	1286.95	2026-04-04	f	\N	f	f	\N	\N	f	\N		\N		1	\N	\N	\N	\N	3	\N	f	\N
109	2026-03-22 22:49:55.464076-03	2026-03-22 22:49:55.464078-03	f	\N	Kalunga Iguatemi Porto	card_purchase	100.82	2026-01-08	t	2	f	f	\N	\N	f	\N		\N	Última parcela	\N	\N	7	\N	\N	\N	6	f	\N
110	2026-03-22 22:49:55.465401-03	2026-03-22 22:49:55.465403-03	f	\N	Shopee *Originattomoda	card_purchase	243.36	2026-01-08	t	4	f	f	\N	\N	f	\N		\N		\N	\N	7	\N	\N	1	6	f	\N
111	2026-03-22 22:49:55.467633-03	2026-03-22 22:49:55.467635-03	f	\N	Riachuelo	card_purchase	119.98	2026-01-08	t	2	f	f	\N	\N	f	\N		\N	Última parcela	\N	\N	7	\N	\N	1	6	f	\N
112	2026-03-22 22:49:55.469121-03	2026-03-22 22:49:55.469123-03	f	\N	Mercadolivre*Lojasrad	card_purchase	25.89	2025-12-08	t	3	f	f	\N	\N	f	\N		\N	Última parcela	\N	\N	7	\N	\N	\N	6	f	\N
113	2026-03-22 22:49:55.471206-03	2026-03-22 22:49:55.471208-03	f	\N	Amazon Marketplace Cc	card_purchase	192.96	2026-01-08	t	6	f	f	\N	\N	f	\N		\N		\N	\N	7	\N	\N	\N	6	f	\N
114	2026-03-22 22:49:55.474934-03	2026-03-22 22:49:55.474936-03	f	\N	Riachuelo (2)	card_purchase	269.97	2026-01-08	t	3	f	f	\N	\N	f	\N		\N		\N	\N	7	\N	\N	1	6	f	\N
115	2026-03-22 22:49:55.476748-03	2026-03-22 22:49:55.47675-03	f	\N	Amazon Prime	card_purchase	166.80	2025-10-08	t	12	f	f	\N	\N	f	\N		\N		\N	\N	7	\N	\N	\N	6	f	\N
116	2026-03-22 22:49:55.48378-03	2026-03-22 22:49:55.483782-03	f	\N	Mercadolivre*Vendasml	card_purchase	165.00	2025-10-08	t	5	f	f	\N	\N	f	\N		\N	Última parcela	\N	\N	7	\N	\N	\N	6	f	\N
117	2026-03-22 22:49:55.486629-03	2026-03-22 22:49:55.48666-03	f	\N	Alpinapresentes	card_purchase	159.88	2026-01-08	t	2	f	f	\N	\N	f	\N		\N	Última parcela	\N	\N	7	\N	\N	\N	6	f	\N
118	2026-03-22 22:49:55.488271-03	2026-03-22 22:49:55.488273-03	f	\N	00013 Sh Iguatemi Poa (3x)	card_purchase	358.95	2026-01-08	t	3	f	f	\N	\N	f	\N		\N		\N	\N	7	\N	\N	1	6	f	\N
119	2026-03-22 22:49:55.490518-03	2026-03-22 22:49:55.49052-03	f	\N	Kalunga Iguatemi Porto (3x)	card_purchase	127.80	2026-01-08	t	3	f	f	\N	\N	f	\N		\N		\N	\N	7	\N	\N	\N	6	f	\N
120	2026-03-22 22:49:55.492297-03	2026-03-22 22:49:55.492299-03	f	\N	Mercado*Mercadolivre (6x)	card_purchase	46.32	2026-01-08	t	6	f	f	\N	\N	f	\N		\N		\N	\N	7	\N	\N	\N	6	f	\N
121	2026-03-22 22:49:55.496785-03	2026-03-22 22:49:55.496787-03	f	\N	00013 Sh Iguatemi Poa (2x)	card_purchase	116.90	2026-01-08	t	2	f	f	\N	\N	f	\N		\N	Última parcela	\N	\N	7	\N	\N	1	6	f	\N
122	2026-03-22 22:49:55.498319-03	2026-03-22 22:49:55.498321-03	f	\N	Mercadolivre*Mercadol (5x)	card_purchase	159.00	2026-02-12	t	5	f	f	\N	\N	f	\N		\N		\N	\N	7	\N	\N	\N	6	f	\N
123	2026-03-22 22:49:55.500918-03	2026-03-22 22:49:55.50092-03	f	\N	Bourbon Country (2x)	card_purchase	89.70	2026-02-14	t	2	f	f	\N	\N	f	\N		\N		\N	\N	7	\N	\N	1	6	f	\N
124	2026-03-22 22:49:55.502098-03	2026-03-22 22:49:55.5021-03	f	\N	Bella Kasa Comercio (5x)	card_purchase	336.10	2026-02-15	t	5	f	f	\N	\N	f	\N		\N		\N	\N	7	\N	\N	\N	6	f	\N
125	2026-03-22 22:49:55.504367-03	2026-03-22 22:49:55.504368-03	f	\N	028 Rs Poa Wallig Sh (3x)	card_purchase	345.06	2026-02-15	t	3	f	f	\N	\N	f	\N		\N		\N	\N	7	\N	\N	1	6	f	\N
126	2026-03-22 22:49:55.506028-03	2026-03-22 22:49:55.50603-03	f	\N	Loja (2x)	card_purchase	199.76	2026-02-15	t	2	f	f	\N	\N	f	\N		\N		\N	\N	7	\N	\N	\N	6	f	\N
127	2026-03-22 22:49:55.507542-03	2026-03-22 22:49:55.507543-03	f	\N	ZP*OLX NuPay (3x)	card_purchase	185.91	2026-02-27	t	3	f	f	\N	\N	f	\N		\N		\N	\N	7	\N	\N	\N	6	f	\N
128	2026-03-22 22:49:55.509326-03	2026-03-22 22:49:55.509328-03	f	\N	Mercadolivre*5produtos (4x)	card_purchase	152.04	2026-02-28	t	4	f	f	\N	\N	f	\N		\N		\N	\N	7	\N	\N	\N	6	f	\N
129	2026-03-22 22:49:55.511429-03	2026-03-22 22:49:55.51143-03	f	\N	Casa Maria (5x)	card_purchase	400.00	2026-03-04	t	5	f	f	\N	\N	f	\N		\N		\N	\N	7	\N	\N	\N	6	f	\N
130	2026-03-22 22:49:55.514107-03	2026-03-22 22:49:55.514109-03	f	\N	Ingresso.com (financ.)	card_purchase	114.94	2026-01-08	t	2	f	f	\N	\N	f	\N		\N	Última parcela. Total R$114,94 (R$107,49 + IOF + juros)	\N	\N	7	\N	\N	\N	6	f	\N
131	2026-03-22 22:49:55.515628-03	2026-03-22 22:49:55.51563-03	f	\N	Maxsuel Ferreira dos Santos (financ.)	card_purchase	124.28	2026-01-08	t	2	f	f	\N	\N	f	\N		\N	Última parcela. Total R$124,28 (R$120 + IOF + juros)	\N	\N	7	\N	\N	\N	6	f	\N
132	2026-03-22 22:49:55.516823-03	2026-03-22 22:49:55.516825-03	f	\N	Elton Rafael Benet Kruger (financ.)	card_purchase	1067.61	2025-12-08	t	3	f	f	\N	\N	f	\N		\N	Última parcela. Total R$1.067,61 (R$900 + IOF + juros)	\N	\N	7	\N	\N	\N	6	f	\N
133	2026-03-22 22:49:55.518588-03	2026-03-22 22:49:55.51859-03	f	\N	Amazon Brasil (financ.)	card_purchase	112.86	2026-02-16	t	2	f	f	\N	\N	f	\N		\N	Total R$112,85 (R$98,14 + IOF + juros)	\N	\N	7	\N	\N	\N	6	f	\N
134	2026-03-22 22:49:55.519916-03	2026-03-22 22:49:55.519917-03	f	\N	Amazon BR (financ.)	card_purchase	101.90	2026-02-16	t	2	f	f	\N	\N	f	\N		\N	Total R$101,90 (R$89,80 + IOF + juros)	\N	\N	7	\N	\N	\N	6	f	\N
135	2026-03-22 22:49:55.521759-03	2026-03-22 22:49:55.521761-03	f	\N	Edilson Alves Barbosa (financ.)	card_purchase	283.98	2026-02-23	t	3	f	f	\N	\N	f	\N		\N	Total R$283,99 (R$240 + IOF + juros)	\N	\N	7	\N	\N	\N	6	f	\N
192	2026-03-22 22:49:55.871826-03	2026-03-23 19:18:06.21438-03	t	2026-03-30 18:17:49.213934-03	P/ Tracker	personal_loan	1060.00	2025-10-30	t	10	f	f	\N	\N	f	\N		\N		\N	\N	\N	\N	\N	2	1	f	\N
190	2026-03-22 22:49:55.630108-03	2026-03-23 19:17:45.268232-03	t	2026-03-30 18:18:01.786195-03	Bomba	personal_loan	45900.00	2025-09-30	t	510	f	f	\N	\N	f	\N		\N		\N	\N	\N	\N	\N	2	1	f	\N
307	2026-04-01 14:10:37.297532-03	2026-04-01 14:10:37.297535-03	f	\N	Mega brick 1	card_purchase	1250.00	2026-04-01	t	10	f	f	\N	\N	f	\N		\N		\N	\N	5	\N	\N	\N	3	f	\N
263	2026-03-22 22:49:56.266745-03	2026-04-01 15:27:01.891332-03	f	\N	Parcelamento IPTU 836 - 2017/2017	property_tax	17032.20	2025-09-30	t	60	t	f	\N	\N	t	2026-03-30		\N	Inscrição 516449. Possui protesto ativo. Site mostra apenas 7 parcelas por vez.	1	\N	\N	\N	\N	3	\N	f	\N
161	2026-03-22 22:49:55.539121-03	2026-03-22 22:49:55.539123-03	f	\N	MERCADOLIVRE SJSEQUIPA	card_purchase	663.36	2025-04-12	t	12	f	f	\N	\N	f	\N		\N		\N	\N	8	\N	\N	\N	6	f	\N
162	2026-03-22 22:49:55.545425-03	2026-03-22 22:49:55.545427-03	f	\N	MERCADO EBAZARCOMBRLT	card_purchase	463.30	2025-07-23	t	10	f	f	\N	\N	f	\N		\N		\N	\N	8	\N	\N	\N	6	f	\N
163	2026-03-22 22:49:55.550397-03	2026-03-22 22:49:55.550399-03	f	\N	APP MEUSAPATOPRET	card_purchase	654.30	2025-10-16	t	6	f	f	\N	\N	f	\N		\N		\N	\N	8	\N	\N	1	6	f	\N
164	2026-03-22 22:49:55.553044-03	2026-03-22 22:49:55.553046-03	f	\N	PICPAY CAMILA STEINM	card_purchase	612.50	2025-12-09	t	5	f	f	\N	\N	f	\N		\N		\N	\N	8	\N	\N	\N	6	f	\N
165	2026-03-22 22:49:55.555076-03	2026-03-22 22:49:55.555077-03	f	\N	MERCADO GURIADOSUL	card_purchase	260.82	2025-12-16	t	3	f	f	\N	\N	f	\N		\N	Última parcela	\N	\N	8	\N	\N	\N	6	f	\N
166	2026-03-22 22:49:55.556768-03	2026-03-22 22:49:55.55677-03	f	\N	GOCASE GOCASE	card_purchase	564.42	2026-01-11	t	3	f	f	\N	\N	f	\N		\N	Última parcela	\N	\N	8	\N	\N	\N	6	f	\N
167	2026-03-22 22:49:55.558103-03	2026-03-22 22:49:55.558104-03	f	\N	VIZ PAGAMENTO CONFIRMA	card_purchase	330.24	2026-01-12	t	6	f	f	\N	\N	f	\N		\N		\N	\N	8	\N	\N	\N	6	f	\N
168	2026-03-22 22:49:55.560692-03	2026-03-22 22:49:55.560694-03	f	\N	Lojas Renner S.A (2x)	card_purchase	87.02	2026-01-15	t	2	f	f	\N	\N	f	\N		\N	Última parcela	\N	\N	8	\N	\N	1	6	f	\N
169	2026-03-22 22:49:55.561698-03	2026-03-22 22:49:55.561699-03	f	\N	MERCADO MERCADOLIVRE (7x)	card_purchase	399.00	2026-01-17	t	7	f	f	\N	\N	f	\N		\N		\N	\N	8	\N	\N	\N	6	f	\N
170	2026-03-22 22:49:55.564282-03	2026-03-22 22:49:55.564284-03	f	\N	Lojas Renner S.A (7x)	card_purchase	496.72	2026-01-29	t	7	f	f	\N	\N	f	\N		\N		\N	\N	8	\N	\N	1	6	f	\N
171	2026-03-22 22:49:55.567661-03	2026-03-22 22:49:55.567663-03	f	\N	CEA	card_purchase	384.00	2026-01-30	t	3	f	f	\N	\N	f	\N		\N		\N	\N	8	\N	\N	1	6	f	\N
172	2026-03-22 22:49:55.569569-03	2026-03-22 22:49:55.569571-03	f	\N	Anuidade Renner	card_purchase	286.80	2026-01-11	t	12	f	f	\N	\N	f	\N		\N	Anuidade parcelada 12x	\N	\N	8	\N	\N	\N	6	f	\N
175	2026-03-22 22:49:55.575335-03	2026-03-22 22:49:55.575337-03	f	\N	MP*EKASA	card_purchase	441.00	2025-01-05	t	15	f	f	\N	\N	f	\N		\N	Última parcela	\N	\N	9	\N	\N	\N	6	f	\N
176	2026-03-22 22:49:55.580755-03	2026-03-22 22:49:55.580757-03	f	\N	MERCADOLIVRE*DINOTELECOM	card_purchase	540.00	2025-04-04	t	18	f	f	\N	\N	f	\N		\N		\N	\N	9	\N	\N	\N	6	f	\N
177	2026-03-22 22:49:55.587294-03	2026-03-22 22:49:55.587295-03	f	\N	Vejastore	card_purchase	670.00	2025-07-07	t	10	f	f	\N	\N	f	\N		\N		\N	\N	9	\N	\N	\N	6	f	\N
178	2026-03-22 22:49:55.590746-03	2026-03-22 22:49:55.590747-03	f	\N	MERCADOLIVRE*ACOMPONENTES	card_purchase	91.92	2025-09-02	t	8	f	f	\N	\N	f	\N		\N		\N	\N	9	\N	\N	\N	6	f	\N
179	2026-03-22 22:49:55.5935-03	2026-03-22 22:49:55.593501-03	f	\N	MP*TOPSVIRTUAL	card_purchase	119.88	2025-12-15	t	6	f	f	\N	\N	f	\N		\N		\N	\N	9	\N	\N	\N	6	f	\N
180	2026-03-22 22:49:55.595631-03	2026-03-22 22:49:55.595632-03	f	\N	MP*LOJASRADAN	card_purchase	174.00	2025-12-31	t	8	f	f	\N	\N	f	\N		\N		\N	\N	9	\N	\N	\N	6	f	\N
181	2026-03-22 22:49:55.599372-03	2026-03-22 22:49:55.599374-03	f	\N	MP*MERCADOLIVRE	card_purchase	213.52	2026-01-25	t	8	f	f	\N	\N	f	\N		\N		\N	\N	9	\N	\N	\N	6	f	\N
182	2026-03-22 22:49:55.603255-03	2026-03-22 22:49:55.603257-03	f	\N	MERCADOLIVRE*MERCADOLI	card_purchase	50.30	2026-02-04	t	2	f	f	\N	\N	f	\N		\N	Última parcela	\N	\N	9	\N	\N	\N	6	f	\N
185	2026-03-22 22:49:55.605569-03	2026-03-22 22:49:55.605571-03	f	\N	Emprestimo R$15000 Nubank	bank_loan	10800.00	2026-03-10	t	9	f	f	\N	\N	f	\N	Nubank	\N		\N	\N	\N	\N	\N	1	1	f	\N
186	2026-03-22 22:49:55.609174-03	2026-03-22 22:49:55.609175-03	f	\N	Panvel	personal_loan	288.65	2026-03-30	t	5	f	f	\N	\N	f	\N		\N		\N	\N	\N	\N	\N	1	1	f	\N
194	2026-03-22 22:49:55.881651-03	2026-03-22 22:49:55.881652-03	f	\N	Tracker	personal_loan	2094.00	2025-12-30	t	6	f	f	\N	\N	f	\N		\N		\N	\N	\N	\N	\N	2	1	f	\N
198	2026-03-22 22:49:55.897749-03	2026-03-22 22:49:55.897751-03	f	\N	Ferragem Parati	personal_loan	288.65	2026-03-30	t	5	f	f	\N	\N	f	\N		\N		\N	\N	\N	\N	\N	\N	1	f	\N
199	2026-03-22 22:49:55.900765-03	2026-03-22 22:49:55.900766-03	f	\N	Empréstimo pedido a Camila de R$1000.00	personal_loan	1000.00	2026-03-30	t	10	f	f	\N	\N	f	\N		\N	Rodrigo pediu empréstimo de R$1000 a Camila, como não se tinha a vista, ficou de se pagar em 10xR$100.00	\N	\N	\N	\N	\N	5	1	f	\N
200	2026-03-22 22:49:55.905348-03	2026-03-22 22:49:55.90535-03	f	\N	Cadeira	personal_loan	1245.00	2026-03-30	t	10	f	f	\N	\N	f	\N		\N		\N	\N	\N	\N	\N	4	1	f	\N
201	2026-03-22 22:49:55.909847-03	2026-03-22 22:49:55.909849-03	f	\N	Panvel 3	personal_loan	1138.90	2026-03-30	t	5	f	f	\N	\N	f	\N		\N		\N	\N	\N	\N	\N	1	1	f	\N
202	2026-03-22 22:49:55.912164-03	2026-03-22 22:49:55.912166-03	f	\N	Fogão	personal_loan	193.00	2026-02-10	t	2	f	f	\N	\N	f	\N		\N	2 parcelas restantes em mar/2026	\N	\N	\N	\N	\N	3	2	f	\N
204	2026-03-22 22:49:55.913693-03	2026-03-22 22:49:55.913695-03	f	\N	Geladeira (9x)	personal_loan	925.02	2026-02-10	t	9	f	f	\N	\N	f	\N		\N	9 parcelas restantes em mar/2026	\N	\N	\N	\N	\N	3	2	f	\N
187	2026-03-22 22:49:55.611644-03	2026-03-23 18:37:22.336307-03	f	\N	TV	personal_loan	4410.00	2025-03-30	t	15	f	f	\N	\N	f	\N		\N		\N	\N	\N	\N	\N	1	1	f	\N
189	2026-03-22 22:49:55.623628-03	2026-03-23 19:17:28.800583-03	f	\N	Roteador	personal_loan	1800.00	2025-09-30	t	12	f	f	\N	\N	f	\N		\N		\N	\N	\N	\N	\N	\N	1	f	\N
188	2026-03-22 22:49:55.61914-03	2026-03-23 19:08:31.478139-03	f	\N	Modulo	personal_loan	2020.00	2025-08-30	t	10	f	f	\N	\N	f	\N		\N		\N	\N	\N	\N	\N	2	1	f	\N
193	2026-03-22 22:49:55.878381-03	2026-03-23 19:22:43.957711-03	f	\N	Pneu	personal_loan	888.00	2025-10-30	t	6	f	f	\N	\N	f	\N		\N		\N	\N	\N	\N	\N	2	1	f	\N
191	2026-03-22 22:49:55.864717-03	2026-03-23 19:22:04.784538-03	f	\N	Geladeira ML	personal_loan	1992.00	2025-09-30	t	12	f	f	\N	\N	f	\N		\N		\N	\N	\N	\N	\N	3	1	f	\N
195	2026-03-22 22:49:55.884308-03	2026-03-23 19:22:55.512103-03	f	\N	Panificadora	personal_loan	497.00	2026-01-30	t	7	f	f	\N	\N	f	\N		\N		\N	\N	\N	\N	\N	1	1	f	\N
196	2026-03-22 22:49:55.888639-03	2026-03-23 19:23:06.098069-03	f	\N	Geladeira Shoppe	personal_loan	1659.00	2026-02-28	t	10	f	f	\N	\N	f	\N		\N		\N	\N	\N	\N	\N	3	1	f	\N
197	2026-03-22 22:49:55.894766-03	2026-03-23 19:23:32.017829-03	f	\N	Panvel 2	personal_loan	136.00	2026-02-28	t	4	f	f	\N	\N	f	\N		\N		\N	\N	\N	\N	\N	1	1	f	\N
205	2026-03-22 22:49:55.918495-03	2026-03-22 22:49:55.918497-03	f	\N	Aspirador	personal_loan	1442.00	2026-02-10	t	14	f	f	\N	\N	f	\N		\N	14 parcelas restantes em mar/2026	\N	\N	\N	\N	\N	3	2	f	\N
206	2026-03-22 22:49:55.925791-03	2026-03-22 22:49:55.925793-03	f	\N	Geladeira (14x)	personal_loan	1302.00	2026-02-10	t	14	f	f	\N	\N	f	\N		\N	14 parcelas restantes em mar/2026	\N	\N	\N	\N	\N	3	2	f	\N
207	2026-03-22 22:49:55.930697-03	2026-03-22 22:49:55.930699-03	f	\N	Geladeira (8x)	personal_loan	1072.00	2026-02-10	t	8	f	f	\N	\N	f	\N		\N	8 parcelas restantes em mar/2026	\N	\N	\N	\N	\N	3	2	f	\N
208	2026-03-22 22:49:55.933527-03	2026-03-22 22:49:55.933528-03	f	\N	Alarme	personal_loan	576.00	2026-02-10	t	8	f	f	\N	\N	f	\N		\N	8 parcelas restantes em mar/2026	\N	\N	\N	\N	\N	3	2	f	\N
209	2026-03-22 22:49:55.936779-03	2026-03-22 22:49:55.936781-03	f	\N	Starlink	personal_loan	1147.30	2026-02-10	t	7	f	f	\N	\N	f	\N		\N	7 parcelas restantes em mar/2026	\N	\N	\N	\N	\N	3	2	f	\N
210	2026-03-22 22:49:55.940336-03	2026-03-22 22:49:55.940338-03	f	\N	Geladeira (7x)	personal_loan	1316.00	2026-02-10	t	7	f	f	\N	\N	f	\N		\N	7 parcelas restantes em mar/2026	\N	\N	\N	\N	\N	3	2	f	\N
211	2026-03-22 22:49:55.943914-03	2026-03-22 22:49:55.943916-03	f	\N	Livros Isabela	personal_loan	450.00	2026-02-10	t	10	f	f	\N	\N	f	\N		\N	10 parcelas restantes em mar/2026	\N	\N	\N	\N	\N	1	2	f	\N
308	2026-04-01 14:10:57.801832-03	2026-04-01 14:10:57.801837-03	f	\N	Mega brick 2	card_purchase	300.00	2026-04-01	t	6	f	f	\N	\N	f	\N		\N		\N	\N	5	\N	\N	\N	3	f	\N
213	2026-03-22 22:49:55.949216-03	2026-03-22 22:49:55.949218-03	f	\N	Escada Pai	personal_loan	496.40	2026-02-10	t	8	f	f	\N	\N	f	\N		\N	8 parcelas restantes em mar/2026	\N	\N	\N	\N	\N	3	2	f	\N
214	2026-03-22 22:49:55.953275-03	2026-03-22 22:49:55.953277-03	f	\N	Projetor	personal_loan	850.00	2026-02-10	t	17	f	f	\N	\N	f	\N		\N	17 parcelas restantes em mar/2026	\N	\N	\N	\N	\N	\N	2	f	\N
215	2026-03-22 22:49:55.962114-03	2026-03-22 22:49:55.962115-03	f	\N	Tela Projetor	personal_loan	150.00	2026-02-10	t	3	f	f	\N	\N	f	\N		\N	3 parcelas restantes em mar/2026	\N	\N	\N	\N	\N	\N	2	f	\N
216	2026-03-22 22:49:55.964398-03	2026-03-22 22:49:55.9644-03	f	\N	Tinta	personal_loan	720.00	2026-02-10	t	8	f	f	\N	\N	f	\N		\N	8 parcelas restantes em mar/2026	\N	\N	\N	\N	\N	3	2	f	\N
217	2026-03-22 22:49:55.968599-03	2026-03-22 22:49:55.968601-03	f	\N	Mesa	personal_loan	1389.06	2026-02-10	t	18	f	f	\N	\N	f	\N		\N	18 parcelas restantes em mar/2026	\N	\N	\N	\N	\N	3	2	f	\N
218	2026-03-22 22:49:55.978388-03	2026-03-22 22:49:55.97839-03	f	\N	Placas Solar	personal_loan	57000.00	2024-05-10	t	60	f	f	\N	\N	f	\N		\N	60 parcelas total, 39 restantes em mar/2026 (parcela 22/60)	\N	\N	\N	\N	\N	3	4	f	\N
219	2026-03-22 22:49:56.008046-03	2026-03-22 22:49:56.008048-03	f	\N	Bolsa Camila	personal_loan	480.00	2026-02-10	t	4	f	f	\N	\N	f	\N		\N	Mar a Jun/2026	\N	\N	\N	\N	\N	4	4	f	\N
220	2026-03-22 22:49:56.010611-03	2026-03-22 22:49:56.010613-03	f	\N	Perfume Camila	personal_loan	97.00	2026-02-10	f	\N	f	f	\N	\N	f	\N		\N	Última parcela	\N	\N	\N	\N	\N	4	4	f	\N
221	2026-03-22 22:49:56.011226-03	2026-03-22 22:49:56.011228-03	f	\N	Financiamento Strada	personal_loan	53585.00	2024-12-10	t	35	f	f	\N	\N	f	\N		\N		\N	\N	\N	\N	\N	2	3	f	\N
222	2026-03-22 22:49:56.027037-03	2026-03-22 22:49:56.02704-03	f	\N	Fogão Zaffari	personal_loan	1200.00	2025-05-10	t	10	f	f	\N	\N	f	\N		\N	Última parcela	\N	\N	\N	\N	\N	3	3	f	\N
223	2026-03-22 22:49:56.032525-03	2026-03-22 22:49:56.032528-03	f	\N	Cartão Renner Junho	personal_loan	1400.40	2025-05-10	t	12	f	f	\N	\N	f	\N		\N		\N	\N	\N	\N	\N	4	3	f	\N
224	2026-03-22 22:49:56.038488-03	2026-03-22 22:49:56.03849-03	f	\N	Cheque especial Itau	personal_loan	4620.00	2025-07-10	t	24	f	f	\N	\N	f	\N		\N		\N	\N	\N	\N	\N	\N	3	f	\N
225	2026-03-22 22:49:56.048295-03	2026-03-22 22:49:56.048297-03	f	\N	Faculdade Camila Julho	personal_loan	1898.00	2025-07-10	t	10	f	f	\N	\N	f	\N		\N		\N	\N	\N	\N	\N	4	3	f	\N
226	2026-03-22 22:49:56.054088-03	2026-03-22 22:49:56.05409-03	f	\N	Parcelamento Unimed	personal_loan	2510.82	2025-07-10	t	18	f	f	\N	\N	f	\N		\N		\N	\N	\N	\N	\N	1	3	f	\N
227	2026-03-22 22:49:56.062894-03	2026-03-22 22:49:56.062896-03	f	\N	Parcela 1 dos IPTUs	personal_loan	2945.76	2025-09-10	t	12	f	f	\N	\N	f	\N		\N		\N	\N	\N	\N	\N	3	3	f	\N
228	2026-03-22 22:49:56.068754-03	2026-03-22 22:49:56.068755-03	f	\N	Faculdade Camila Setembro	personal_loan	1910.90	2025-10-10	t	10	f	f	\N	\N	f	\N		\N		\N	\N	\N	\N	\N	4	3	f	\N
229	2026-03-22 22:49:56.073703-03	2026-03-22 22:49:56.073704-03	f	\N	Placas Solares Sunnyhub	personal_loan	90300.00	2025-11-10	t	60	f	f	\N	\N	f	\N		\N		\N	\N	\N	\N	\N	3	3	f	\N
230	2026-03-22 22:49:56.104047-03	2026-03-22 22:49:56.104049-03	f	\N	Carro Camila	personal_loan	145656.00	2025-12-10	t	48	f	f	\N	\N	f	\N		\N		\N	\N	\N	\N	\N	4	3	f	\N
231	2026-03-22 22:49:56.129808-03	2026-03-22 22:49:56.12981-03	f	\N	Parcela valores nov/dez	personal_loan	7024.80	2025-12-10	t	12	f	f	\N	\N	f	\N		\N		\N	\N	\N	\N	\N	\N	3	f	\N
232	2026-03-22 22:49:56.135629-03	2026-03-22 22:49:56.135631-03	f	\N	Zaffari compras	personal_loan	351.72	2026-01-10	t	6	f	f	\N	\N	f	\N		\N		\N	\N	\N	\N	\N	1	3	f	\N
233	2026-03-22 22:49:56.138572-03	2026-03-22 22:49:56.138574-03	f	\N	IPVA Strada	personal_loan	1554.00	2025-12-10	t	6	f	f	\N	\N	f	\N		\N		\N	\N	\N	\N	\N	2	3	f	\N
234	2026-03-22 22:49:56.141615-03	2026-03-22 22:49:56.141617-03	f	\N	Tags prédio	personal_loan	448.86	2026-01-10	t	6	f	f	\N	\N	f	\N		\N		\N	\N	\N	\N	\N	3	3	f	\N
235	2026-03-22 22:49:56.144669-03	2026-03-22 22:49:56.144671-03	f	\N	Leroy 1	personal_loan	685.60	2026-02-10	t	10	f	f	\N	\N	f	\N		\N		\N	\N	\N	\N	\N	3	3	f	\N
236	2026-03-22 22:49:56.149257-03	2026-03-22 22:49:56.149259-03	f	\N	Leroy 2	personal_loan	255.30	2026-02-10	t	10	f	f	\N	\N	f	\N		\N		\N	\N	\N	\N	\N	3	3	f	\N
237	2026-03-22 22:49:56.153967-03	2026-03-22 22:49:56.153969-03	f	\N	Ferragem 1	personal_loan	658.08	2026-02-10	t	4	f	f	\N	\N	f	\N		\N		\N	\N	\N	\N	\N	3	3	f	\N
238	2026-03-22 22:49:56.156098-03	2026-03-22 22:49:56.1561-03	f	\N	Mega Brick 1	personal_loan	850.20	2026-02-10	t	6	f	f	\N	\N	f	\N		\N		\N	\N	\N	\N	\N	3	3	f	\N
239	2026-03-22 22:49:56.159512-03	2026-03-22 22:49:56.159514-03	f	\N	Compra cartão Leroy	personal_loan	520.00	2026-02-10	t	10	f	f	\N	\N	f	\N		\N		\N	\N	\N	\N	\N	3	3	f	\N
240	2026-03-22 22:49:56.164002-03	2026-03-22 22:49:56.164004-03	f	\N	Duporto Peças	personal_loan	342.00	2026-02-10	t	2	f	f	\N	\N	f	\N		\N		\N	\N	\N	\N	\N	\N	3	f	\N
241	2026-03-22 22:49:56.16532-03	2026-03-22 22:49:56.165322-03	f	\N	Leroy 3	personal_loan	180.99	2026-02-10	t	9	f	f	\N	\N	f	\N		\N		\N	\N	\N	\N	\N	3	3	f	\N
242	2026-03-22 22:49:56.169571-03	2026-03-22 22:49:56.169573-03	f	\N	[DESCONTO] TV presente aniversário Célia	personal_loan	2950.00	2025-07-10	t	10	f	f	\N	\N	f	\N		\N	Desconto: compra para os sogros	\N	\N	\N	\N	\N	1	3	t	\N
243	2026-03-22 22:49:56.174394-03	2026-03-22 22:49:56.174396-03	f	\N	[DESCONTO] Máquina secar roupas (Rodrigo)	personal_loan	4050.00	2025-08-10	t	12	f	f	\N	\N	f	\N		\N	Desconto: Rodrigo comprou para eles	\N	\N	\N	\N	\N	1	3	t	\N
314	2026-04-01 15:55:27.792875-03	2026-04-01 15:55:27.792879-03	f	\N	Empréstimo Alessandra	personal_loan	5000.00	2026-04-01	t	5	f	f	\N	\N	f	\N		\N		\N	\N	\N	\N	\N	3	7	f	\N
245	2026-03-22 22:49:56.184679-03	2026-03-22 22:49:56.184681-03	f	\N	[DESCONTO] Carro Camila (desconto)	personal_loan	73656.00	2025-12-10	t	48	f	f	\N	\N	f	\N		\N	Desconto: metade do financiamento é da Camila	\N	\N	\N	\N	\N	4	3	t	\N
246	2026-03-22 22:49:56.205414-03	2026-03-22 22:49:56.205416-03	f	\N	Água - Prédio 850 - 2026-02	water_bill	414.89	2026-02-01	f	\N	f	f	\N	\N	t	2026-02-15		\N	[PARCELAMENTO_INCLUSO:Parcelamento Água 850] Relógio DMAE 463540. Parcelamento de R$850/mês começa em abril/2026.	2	\N	\N	\N	\N	\N	\N	f	\N
247	2026-03-22 22:49:56.205963-03	2026-03-22 22:49:56.205965-03	f	\N	Água - Prédio 850 - 2026-03	water_bill	696.04	2026-03-01	f	\N	f	f	\N	\N	t	2026-03-15		\N	[PARCELAMENTO_INCLUSO:Parcelamento Água 850] Relógio DMAE 463540. Parcelamento de R$850/mês começa em abril/2026.	2	\N	\N	\N	\N	\N	\N	f	\N
248	2026-03-22 22:49:56.206497-03	2026-03-22 22:49:56.206499-03	f	\N	Luz - Relógio Principal (Av. Circular 840) - 2026-01	electricity_bill	1493.50	2026-01-01	f	\N	f	f	\N	\N	t	2026-01-15		\N		1	\N	\N	\N	\N	\N	\N	f	\N
249	2026-03-22 22:49:56.207142-03	2026-03-22 22:49:56.207144-03	f	\N	Luz - Relógio Principal (Av. Circular 840) - 2026-02	electricity_bill	384.98	2026-02-01	f	\N	f	f	\N	\N	t	2026-02-15		\N		1	\N	\N	\N	\N	\N	\N	f	\N
250	2026-03-22 22:49:56.207598-03	2026-03-22 22:49:56.2076-03	f	\N	Luz - Relógio Principal (Av. Circular 840) - 2026-03	electricity_bill	453.77	2026-03-01	f	\N	f	f	\N	\N	f	\N		\N		1	\N	\N	\N	\N	\N	\N	f	\N
251	2026-03-22 22:49:56.208129-03	2026-03-22 22:49:56.208131-03	f	\N	Luz - Relógio 2 Kitnets (Av. Circular 836) - 2026-01	electricity_bill	211.53	2026-01-01	f	\N	f	f	\N	\N	t	2026-01-15		\N	Relógio conectado a apenas 2 kitnets, será desligado. Endereço CEEE: Av. Circular 836 (mesmo prédio físico que 840)	1	\N	\N	\N	\N	\N	\N	f	\N
252	2026-03-22 22:49:56.208598-03	2026-03-22 22:49:56.2086-03	f	\N	Luz - Relógio 2 Kitnets (Av. Circular 836) - 2026-02	electricity_bill	108.61	2026-02-01	f	\N	f	f	\N	\N	t	2026-02-15		\N	Relógio conectado a apenas 2 kitnets, será desligado. Endereço CEEE: Av. Circular 836 (mesmo prédio físico que 840)	1	\N	\N	\N	\N	\N	\N	f	\N
253	2026-03-22 22:49:56.209106-03	2026-03-22 22:49:56.209108-03	f	\N	Luz - Relógio 2 Kitnets (Av. Circular 836) - 2026-03	electricity_bill	174.61	2026-03-01	f	\N	f	f	\N	\N	f	\N		\N	Relógio conectado a apenas 2 kitnets, será desligado. Endereço CEEE: Av. Circular 836 (mesmo prédio físico que 840)	1	\N	\N	\N	\N	\N	\N	f	\N
254	2026-03-22 22:49:56.20964-03	2026-03-22 22:49:56.209642-03	f	\N	Luz - Prédio 850 - 2026-01	electricity_bill	970.42	2026-01-01	f	\N	f	f	\N	\N	t	2026-01-15		\N	[PARCELAMENTO_INCLUSO:Parcelamento Luz 850]	2	\N	\N	\N	\N	\N	\N	f	\N
255	2026-03-22 22:49:56.210117-03	2026-03-22 22:49:56.210119-03	f	\N	Luz - Prédio 850 - 2026-02	electricity_bill	957.88	2026-02-01	f	\N	f	f	\N	\N	t	2026-02-15		\N	[PARCELAMENTO_INCLUSO:Parcelamento Luz 850]	2	\N	\N	\N	\N	\N	\N	f	\N
256	2026-03-22 22:49:56.210611-03	2026-03-22 22:49:56.210613-03	f	\N	Luz - Prédio 850 - 2026-03	electricity_bill	1015.35	2026-03-01	f	\N	f	f	\N	\N	f	\N		\N	[PARCELAMENTO_INCLUSO:Parcelamento Luz 850]	2	\N	\N	\N	\N	\N	\N	f	\N
257	2026-03-22 22:49:56.211189-03	2026-03-22 22:49:56.21119-03	f	\N	Parcelamento dívida luz prédio 850	electricity_bill	15104.40	2024-11-11	t	24	t	f	\N	\N	f	\N		\N	Parcela inclusa na fatura de luz do prédio 850. Valor do consumo real = valor_fatura - 629.35	2	\N	\N	\N	\N	3	\N	f	\N
259	2026-03-22 22:49:56.249765-03	2026-03-22 22:49:56.249766-03	f	\N	IPTU 2026 - Prédio 836 (IPTU consta como 828)	property_tax	9291.76	2026-01-10	t	10	f	f	\N	\N	f	\N		\N	Não tem parcelamento ainda, provavelmente vão parcelar como divida	1	\N	\N	\N	\N	\N	\N	f	\N
309	2026-04-01 14:12:13.978181-03	2026-04-01 14:12:13.978184-03	f	\N	Internet Sitio	fixed_expense	235.52	2026-04-01	f	\N	f	t	235.52	\N	f	\N		\N		\N	\N	\N	\N	\N	1	3	f	\N
275	2026-03-22 22:49:56.289751-03	2026-04-01 14:59:32.57255-03	f	\N	Conta de luz - Sítio	electricity_bill	400.00	2026-01-01	f	\N	f	t	200.00	\N	f	\N		\N	0	\N	\N	\N	\N	\N	1	\N	f	\N
258	2026-03-22 22:49:56.2237-03	2026-03-22 22:49:56.223702-03	t	2026-04-01 15:01:44.587112-03	Parcelamento dívida água prédio 850	water_bill	51000.00	2026-04-04	t	60	t	f	\N	\N	f	\N		\N	1ª parcela em abril/2026. Vai ser inclusa na fatura de água do 850.	2	\N	\N	\N	\N	3	\N	f	\N
315	2026-04-01 18:17:22.536531-03	2026-04-01 18:17:22.536536-03	f	\N	BISTEK SUPERMERCADOS	card_purchase	176.22	2026-03-08	f	\N	f	f	\N	\N	f	\N		\N		\N	\N	3	\N	\N	\N	1	f	\N
265	2026-03-22 22:49:56.273923-03	2026-03-30 15:46:52.344915-03	f	\N	Parcelamento IPTU 850 - 2022/2022, 2023/2023, 2024/2024, 2025/2025	property_tax	2002.98	2025-09-30	t	60	t	f	\N	\N	t	2026-03-30		\N	Inscrição 516481.	2	\N	\N	\N	\N	3	\N	f	\N
267	2026-03-22 22:49:56.278591-03	2026-03-30 15:46:54.169017-03	f	\N	Parcelamento IPTU 850 - 2011/2012, 2010/2011, 2012/2013, 2013/2013	property_tax	8230.02	2021-11-30	t	60	t	f	\N	\N	t	2026-03-30		\N	Inscrição 516503. 53 parcelas total, 51 pagas. Apenas pendentes listadas.	2	\N	\N	\N	\N	3	\N	f	\N
268	2026-03-22 22:49:56.280048-03	2026-03-30 15:46:52.934837-03	f	\N	Parcelamento IPTU 850 - 2024/2024, 2025/2025	property_tax	12273.44	2025-09-30	t	60	t	f	\N	\N	t	2026-03-30		\N	Inscrição 516503.	2	\N	\N	\N	\N	3	\N	f	\N
269	2026-03-22 22:49:56.283889-03	2026-03-30 15:46:51.661323-03	f	\N	Parcelamento IPTU 850 - 2022/2022, 2023/2023	property_tax	13793.01	2025-09-30	t	60	t	f	\N	\N	t	2026-03-30		\N	Inscrição 516503.	2	\N	\N	\N	\N	3	\N	f	\N
262	2026-03-22 22:49:56.263352-03	2026-04-01 15:27:16.479506-03	f	\N	Parcelamento IPTU 836 - 2022/2022, 2023/2023	property_tax	23411.40	2025-09-30	t	60	t	f	\N	\N	t	2026-03-30		\N	Termo 992989. Possui protesto ativo.	1	\N	\N	\N	\N	3	\N	f	\N
270	2026-03-22 22:49:56.287191-03	2026-03-22 22:49:56.287193-03	f	\N	Internet - Prédio 836	fixed_expense	129.90	2026-01-01	f	\N	f	t	129.90	15	f	\N		\N		1	\N	\N	\N	\N	3	\N	f	\N
271	2026-03-22 22:49:56.287727-03	2026-03-22 22:49:56.287729-03	f	\N	Internet - Prédio 850	fixed_expense	129.90	2026-01-01	f	\N	f	t	129.90	15	f	\N		\N		2	\N	\N	\N	\N	3	\N	f	\N
264	2026-03-22 22:49:56.270346-03	2026-04-01 15:26:40.96666-03	f	\N	Multa IPTU 836 - 2017/2024	property_tax	2895.00	2025-09-30	t	60	t	f	\N	\N	t	2026-03-30		\N	Inscrição 516449. Multa IPTU.	1	\N	\N	\N	\N	3	\N	f	\N
273	2026-03-22 22:49:56.2887-03	2026-03-22 22:49:56.288702-03	f	\N	Ração galinhas	fixed_expense	400.00	2026-01-01	f	\N	f	t	400.00	\N	f	\N		\N		\N	\N	\N	\N	\N	1	\N	f	\N
274	2026-03-22 22:49:56.289211-03	2026-03-22 22:49:56.289213-03	f	\N	Detergentes	fixed_expense	150.00	2026-01-01	f	\N	f	t	150.00	\N	f	\N		\N	Produtos de limpeza para os kitnets	\N	\N	\N	\N	\N	3	\N	f	\N
316	2026-04-01 18:17:22.539384-03	2026-04-01 18:17:22.539387-03	f	\N	POSTO CARLAO	card_purchase	128.11	2026-03-08	f	\N	f	f	\N	\N	f	\N		\N		\N	\N	3	\N	\N	\N	1	f	\N
276	2026-03-22 22:49:56.290229-03	2026-03-22 22:49:56.290231-03	f	\N	Claro	fixed_expense	443.09	2026-01-01	f	\N	f	t	443.09	\N	f	\N		\N		\N	\N	\N	\N	\N	3	\N	f	\N
277	2026-03-22 22:49:56.290692-03	2026-03-22 22:49:56.290693-03	f	\N	Unimed - Plano de Saúde	fixed_expense	2230.00	2026-01-01	f	\N	f	t	2230.00	\N	f	\N		\N	Rodrigo paga o plano de saúde dos sogros	\N	\N	\N	\N	\N	1	1	f	\N
278	2026-03-22 22:49:56.291154-03	2026-03-22 22:49:56.291156-03	f	\N	Faculdade Junior	fixed_expense	200.00	2026-03-01	f	\N	f	t	200.00	10	f	\N		\N	Mensalidade da faculdade do Junior, termina em dez/2026	\N	\N	\N	\N	\N	1	4	f	\N
279	2026-03-22 22:49:56.291606-03	2026-03-22 22:49:56.291608-03	f	\N	Prestação terras sítio (Eloênio)	fixed_expense	500.00	2026-03-01	f	\N	f	t	500.00	\N	f	\N		\N	Prestação de terras do sítio paga a Eloênio (terceiro, não familiar)	\N	\N	\N	\N	\N	1	\N	f	\N
280	2026-03-22 22:49:56.292052-03	2026-03-22 22:49:56.292053-03	f	\N	Zaffari (Alvaro)	one_time_expense	200.00	2026-03-01	f	\N	f	f	\N	\N	t	2026-03-10		\N	Pagamento único mar/2026	\N	\N	\N	\N	\N	1	3	f	\N
281	2026-03-22 22:49:56.292514-03	2026-03-22 22:49:56.292516-03	f	\N	Bistek (Alvaro)	one_time_expense	400.00	2026-03-01	f	\N	f	f	\N	\N	t	2026-03-10		\N	Pagamento único mar/2026	\N	\N	\N	\N	\N	1	3	f	\N
282	2026-03-22 22:49:56.293008-03	2026-03-22 22:49:56.29301-03	f	\N	Entrada Parcelamento Conta de Água Prédio 850	one_time_expense	4000.00	2026-03-21	f	\N	f	f	\N	\N	t	2026-03-21		\N		\N	\N	\N	\N	\N	3	3	f	\N
244	2026-03-22 22:49:56.180166-03	2026-03-23 16:04:11.258746-03	f	\N	[DESCONTO] Cadeira Camila (Tiago)	personal_loan	1245.00	2026-02-10	t	10	f	f	\N	\N	f	\N		\N		\N	\N	\N	\N	\N	4	3	t	\N
283	2026-03-23 16:33:17.544773-03	2026-03-23 16:33:17.544781-03	f	\N	Perfume Camila	personal_loan	97.00	2025-03-23	t	1	f	f	\N	\N	f	\N		\N		\N	\N	\N	\N	\N	\N	4	f	\N
284	2026-03-23 16:47:17.479718-03	2026-03-23 16:49:53.889562-03	f	\N	Perfume Camila	personal_loan	97.00	2026-03-23	f	\N	f	f	\N	\N	f	\N		\N		\N	\N	\N	\N	\N	4	4	f	\N
285	2026-03-23 17:12:53.950439-03	2026-03-23 17:12:53.950448-03	f	\N	Euro Oculos	personal_loan	95.50	2026-03-23	t	1	f	f	\N	\N	f	\N		\N		\N	\N	\N	\N	\N	1	2	f	\N
286	2026-03-23 17:14:27.044724-03	2026-03-23 17:15:45.853451-03	f	\N	Escola Isabela	fixed_expense	500.00	2026-03-23	f	\N	f	t	500.00	\N	f	\N		\N		\N	\N	\N	\N	\N	1	2	f	\N
287	2026-03-23 18:02:26.799823-03	2026-03-23 18:02:26.799833-03	f	\N	Fogão	personal_loan	600.00	2026-03-23	f	\N	f	f	\N	\N	f	\N		\N		\N	\N	\N	\N	\N	3	2	f	\N
317	2026-04-01 18:17:22.539978-03	2026-04-01 18:17:22.53998-03	f	\N	DL GOOGLE YOUTUBE	card_purchase	53.90	2026-03-09	f	\N	f	f	\N	\N	f	\N		\N		\N	\N	3	\N	\N	\N	1	f	\N
288	2026-03-23 18:13:54.85548-03	2026-03-23 18:58:15.618806-03	f	\N	Panvel 1	personal_loan	345.18	2026-03-23	t	6	f	f	\N	\N	f	\N		\N		\N	\N	\N	\N	\N	1	1	f	\N
291	2026-03-23 19:17:07.730314-03	2026-03-23 19:17:07.730321-03	f	\N	Modulo	personal_loan	2020.00	2026-03-23	t	10	f	f	\N	\N	f	\N		\N		\N	\N	\N	\N	\N	1	1	f	\N
292	2026-03-23 19:19:16.499836-03	2026-03-23 19:19:16.499843-03	f	\N	Máquina de Secar	personal_loan	4044.00	2026-03-23	t	12	f	f	\N	\N	f	\N		\N	Parcela paga Alvaro (Desconto)	\N	\N	\N	\N	\N	4	1	f	\N
293	2026-03-23 19:24:00.158855-03	2026-03-23 19:24:00.158862-03	f	\N	Ferragem Parati	personal_loan	1000.00	2026-03-23	t	4	f	f	\N	\N	f	\N		\N		\N	\N	\N	\N	\N	3	1	f	\N
294	2026-03-23 19:24:35.177717-03	2026-03-23 19:24:35.177724-03	f	\N	Emprestimo p/ Rodrigo R$1000	personal_loan	1000.00	2026-03-23	t	10	f	f	\N	\N	f	\N		\N		\N	\N	\N	\N	\N	5	1	f	\N
295	2026-03-23 19:29:26.827895-03	2026-03-23 19:29:26.827901-03	t	2026-03-23 19:33:36.772824-03	Rosa - Aluguel	employee_salary	1000.00	2026-03-23	f	\N	f	f	\N	\N	f	\N		\N		\N	\N	\N	\N	\N	3	\N	f	\N
296	2026-03-27 16:07:35.352158-03	2026-03-27 16:07:35.352169-03	f	\N	Pagamento IPTU fev e março	personal_loan	4485.00	2026-03-27	f	\N	f	f	\N	\N	f	\N		\N		\N	\N	\N	\N	\N	3	3	f	\N
297	2026-03-30 13:03:01.190459-03	2026-03-30 13:03:01.190464-03	f	\N	Empréstimo Nubank	bank_loan	8677.92	2026-07-31	t	12	f	f	\N	\N	f	\N		\N		\N	\N	\N	\N	\N	3	6	f	\N
298	2026-03-30 13:07:23.413695-03	2026-03-30 13:07:23.413701-03	f	\N	Empréstimo entrada parcelamento DMAE 850	one_time_expense	2000.00	2026-03-16	f	\N	f	f	\N	\N	f	\N		\N		\N	\N	\N	\N	\N	3	2	f	\N
272	2026-03-22 22:49:56.288211-03	2026-03-22 22:49:56.288213-03	t	2026-03-30 15:47:40.928589-03	Internet - Sítio	fixed_expense	200.00	2026-01-01	f	\N	f	t	200.00	10	f	\N		\N	Vai iniciar em Abril/2026 no valor de R$232.52/mês	\N	\N	\N	\N	\N	1	\N	f	\N
300	2026-03-30 13:12:27.697193-03	2026-03-30 13:12:27.697198-03	f	\N	Pagamento Cartão Rodrigo	personal_loan	1599.00	2026-03-28	f	\N	f	f	\N	\N	f	\N		\N		\N	\N	\N	\N	\N	1	3	f	\N
301	2026-03-30 13:37:34.798093-03	2026-03-30 13:37:34.7981-03	f	\N	Fisioterapia Célia	one_time_expense	350.00	2026-03-30	f	\N	f	f	\N	\N	f	\N		\N		\N	\N	\N	\N	\N	6	\N	f	\N
299	2026-03-30 13:09:06.224368-03	2026-03-30 13:09:06.22438-03	t	2026-03-30 13:37:39.094019-03	Fisioterapia Célia	one_time_expense	350.00	2026-03-30	f	\N	f	f	\N	\N	f	\N		\N		\N	\N	\N	\N	\N	1	\N	f	\N
302	2026-03-30 13:48:38.006573-03	2026-03-30 13:48:38.006586-03	f	\N	Roupeiro e Comoda - Mega Brick	one_time_expense	1500.00	2026-03-30	f	\N	f	f	\N	\N	f	\N		\N		\N	\N	\N	\N	\N	3	\N	f	\N
303	2026-03-30 13:49:13.645484-03	2026-03-30 13:49:13.64549-03	f	\N	Aereo, Balcão pia, prateleira, balcão p/ forno - Mega Brick	one_time_expense	950.00	2026-03-30	f	\N	f	f	\N	\N	f	\N		\N		\N	\N	\N	\N	\N	3	\N	f	\N
310	2026-04-01 14:56:03.931364-03	2026-04-01 14:56:03.931367-03	f	\N	Luz placas 840	electricity_bill	483.74	2026-04-01	f	\N	f	f	\N	\N	f	\N		\N		1	\N	\N	\N	\N	3	\N	f	\N
266	2026-03-22 22:49:56.277232-03	2026-03-30 15:46:53.534773-03	f	\N	Parcelamento IPTU 850 - 2018/2018, 2020/2021, 2021/2021	property_tax	5251.24	2021-11-30	t	60	t	f	\N	\N	t	2026-03-30		\N	Inscrição 516503. 53 parcelas total, 51 pagas. Apenas pendentes listadas.	2	\N	\N	\N	\N	3	\N	f	\N
261	2026-03-22 22:49:56.259775-03	2026-04-01 15:28:14.926137-03	f	\N	Parcelamento IPTU 836 - 2020/2021, 2021/2021, 2024/2024, 2025/2025	property_tax	30787.20	2025-09-30	t	60	t	f	\N	\N	t	2026-03-30		\N	Termo 992988. Possui protesto ativo.	1	\N	\N	\N	\N	3	\N	f	\N
318	2026-04-01 18:17:22.540405-03	2026-04-01 18:17:22.540406-03	f	\N	FRUTEIRAO DO FORTE	card_purchase	72.22	2026-03-10	f	\N	f	f	\N	\N	f	\N		\N		\N	\N	3	\N	\N	\N	1	f	\N
319	2026-04-01 18:17:22.540742-03	2026-04-01 18:17:22.540744-03	f	\N	CAPPTA FPS COMERCIO D	card_purchase	342.00	2026-03-12	f	\N	f	f	\N	\N	f	\N		\N		\N	\N	3	\N	\N	\N	1	f	\N
320	2026-04-01 18:17:22.541061-03	2026-04-01 18:17:22.541063-03	f	\N	SERRABEN	card_purchase	65.02	2026-03-13	f	\N	f	f	\N	\N	f	\N		\N		\N	\N	3	\N	\N	\N	1	f	\N
321	2026-04-01 18:17:22.541389-03	2026-04-01 18:17:22.541391-03	f	\N	PANVEL FILIAL 369	card_purchase	29.43	2026-03-14	f	\N	f	f	\N	\N	f	\N		\N		\N	\N	3	\N	\N	\N	1	f	\N
322	2026-04-01 18:17:22.54174-03	2026-04-01 18:17:22.541742-03	f	\N	MERCADOLIVRE 2PRODUTOS	card_purchase	40.64	2026-03-14	f	\N	f	f	\N	\N	f	\N		\N		\N	\N	3	\N	\N	\N	1	f	\N
323	2026-04-01 18:17:22.542154-03	2026-04-01 18:17:22.542156-03	f	\N	SUPERMERCADOS JM RAMOS	card_purchase	49.63	2026-03-14	f	\N	f	f	\N	\N	f	\N		\N		\N	\N	3	\N	\N	\N	1	f	\N
324	2026-04-01 18:17:22.542988-03	2026-04-01 18:17:22.542992-03	f	\N	POSTO FLEX CARLAO	card_purchase	154.58	2026-03-14	f	\N	f	f	\N	\N	f	\N		\N		\N	\N	3	\N	\N	\N	1	f	\N
325	2026-04-01 18:17:22.543811-03	2026-04-01 18:17:22.543813-03	f	\N	MP FRUTEIRAO DO FORTE	card_purchase	43.68	2026-03-14	f	\N	f	f	\N	\N	f	\N		\N		\N	\N	3	\N	\N	\N	1	f	\N
326	2026-04-01 18:17:22.544382-03	2026-04-01 18:17:22.544384-03	f	\N	CARLOS ALBERTO	card_purchase	110.00	2026-03-17	f	\N	f	f	\N	\N	f	\N		\N		\N	\N	3	\N	\N	\N	1	f	\N
327	2026-04-01 18:17:22.544869-03	2026-04-01 18:17:22.544871-03	f	\N	MCDONALDS	card_purchase	55.80	2026-03-17	f	\N	f	f	\N	\N	f	\N		\N		\N	\N	3	\N	\N	\N	1	f	\N
328	2026-04-01 18:17:22.545727-03	2026-04-01 18:17:22.545729-03	f	\N	BIGMIX	card_purchase	97.73	2026-03-18	f	\N	f	f	\N	\N	f	\N		\N		\N	\N	3	\N	\N	\N	1	f	\N
329	2026-04-01 18:17:22.546222-03	2026-04-01 18:17:22.546224-03	f	\N	POSTO FLEX	card_purchase	165.85	2026-03-19	f	\N	f	f	\N	\N	f	\N		\N		\N	\N	3	\N	\N	\N	1	f	\N
330	2026-04-01 18:17:22.546729-03	2026-04-01 18:17:22.54673-03	f	\N	MP FRUTEIRAO DO FORTE	card_purchase	68.10	2026-03-19	f	\N	f	f	\N	\N	f	\N		\N		\N	\N	3	\N	\N	\N	1	f	\N
331	2026-04-01 18:17:22.547191-03	2026-04-01 18:17:22.547193-03	f	\N	BISTEK SUPERMERCADOS	card_purchase	351.60	2026-03-19	f	\N	f	f	\N	\N	f	\N		\N		\N	\N	3	\N	\N	\N	1	f	\N
332	2026-04-01 18:17:22.547771-03	2026-04-01 18:17:22.547773-03	f	\N	MP MAURO CESAR DAS	card_purchase	32.00	2026-03-19	f	\N	f	f	\N	\N	f	\N		\N		\N	\N	3	\N	\N	\N	1	f	\N
333	2026-04-01 18:17:22.548257-03	2026-04-01 18:17:22.548259-03	f	\N	COM DE COMBUSTIVEIS AP	card_purchase	150.00	2026-03-21	f	\N	f	f	\N	\N	f	\N		\N		\N	\N	3	\N	\N	\N	1	f	\N
334	2026-04-01 18:17:22.54865-03	2026-04-01 18:17:22.548651-03	f	\N	CARLOS ALBERTO	card_purchase	120.00	2026-03-23	f	\N	f	f	\N	\N	f	\N		\N		\N	\N	3	\N	\N	\N	1	f	\N
335	2026-04-01 18:17:22.549009-03	2026-04-01 18:17:22.54901-03	f	\N	MP FRUTEIRAO DO FORTE	card_purchase	19.27	2026-03-24	f	\N	f	f	\N	\N	f	\N		\N		\N	\N	3	\N	\N	\N	1	f	\N
336	2026-04-01 18:17:22.549335-03	2026-04-01 18:17:22.549337-03	f	\N	MERCADOLIVRE 2PRODUTOS	card_purchase	71.52	2026-03-24	t	2	f	f	\N	\N	f	\N		\N		\N	\N	3	\N	\N	\N	1	f	\N
\.


--
-- Data for Name: core_expensecategory; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY "public"."core_expensecategory" ("id", "created_at", "updated_at", "is_deleted", "deleted_at", "name", "description", "color", "created_by_id", "deleted_by_id", "updated_by_id", "parent_id") FROM stdin;
1	2026-03-22 22:48:04.230359-03	2026-03-22 22:48:04.230363-03	f	\N	Pessoal	Gastos pessoais dos sogros	#EC4899	\N	\N	\N	\N
2	2026-03-22 22:48:04.234819-03	2026-03-22 22:48:04.234822-03	f	\N	Carros	Gastos com veículos	#8B5CF6	\N	\N	\N	\N
4	2026-03-22 22:48:04.2375-03	2026-03-22 22:48:04.237502-03	f	\N	Camila	Gastos relacionados à Camila	#06B6D4	\N	\N	\N	\N
5	2026-03-22 22:48:04.238867-03	2026-03-22 22:48:04.238869-03	f	\N	Ajuda	Valores emprestados/adiantados pelos filhos cobrados em parcelas	#22C55E	\N	\N	\N	\N
6	2026-03-22 22:48:04.240186-03	2026-03-22 22:48:04.240188-03	f	\N	Saúde	Consultas, exames, plano de saúde	#EC4899	\N	\N	\N	1
7	2026-03-22 22:48:04.241486-03	2026-03-22 22:48:04.241488-03	f	\N	Mercado	Supermercado, feira, fruteira	#EC4899	\N	\N	\N	1
8	2026-03-22 22:48:04.242748-03	2026-03-22 22:48:04.242768-03	f	\N	Farmácia	Medicamentos e produtos de farmácia	#EC4899	\N	\N	\N	1
9	2026-03-22 22:48:04.244123-03	2026-03-22 22:48:04.244125-03	f	\N	Vestuário	Roupas e calçados	#EC4899	\N	\N	\N	1
10	2026-03-22 22:48:04.24546-03	2026-03-22 22:48:04.245462-03	f	\N	Gasolina	Combustível	#8B5CF6	\N	\N	\N	2
11	2026-03-22 22:48:04.246788-03	2026-03-22 22:48:04.24679-03	f	\N	Pedágio	Pedágios	#8B5CF6	\N	\N	\N	2
12	2026-03-22 22:48:04.248094-03	2026-03-22 22:48:04.248096-03	f	\N	Manutenção Veículo	Peças, oficina, revisão	#8B5CF6	\N	\N	\N	2
13	2026-03-22 22:48:04.249452-03	2026-03-22 22:48:04.249455-03	f	\N	Manutenção	Reparos e manutenção dos prédios	#F97316	\N	\N	\N	3
14	2026-03-22 22:48:04.250926-03	2026-03-22 22:48:04.250951-03	f	\N	Material de Construção	Cimento, tinta, ferragens	#F97316	\N	\N	\N	3
15	2026-03-22 22:48:04.252243-03	2026-03-22 22:48:04.252245-03	f	\N	Internet	Planos de internet dos prédios	#F97316	\N	\N	\N	3
16	2026-03-22 22:48:04.253619-03	2026-03-22 22:48:04.253621-03	f	\N	Faxinas	Faxinas nos kitnets desocupados	#F97316	\N	\N	\N	3
17	2026-03-23 17:12:06.827036-03	2026-03-23 17:12:06.827042-03	f	\N	Presentes	Presentes e lembranças	#F472B6	3	\N	3	1
18	2026-03-30 15:58:24.940774-03	2026-03-30 15:58:24.940782-03	f	\N	Móveis		#F97316	\N	\N	\N	3
3	2026-03-22 22:48:04.236137-03	2026-03-30 15:58:34.93574-03	f	\N	Condomínio	Gastos com os prédios	#F97316	\N	\N	\N	\N
\.


--
-- Data for Name: core_expenseinstallment; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY "public"."core_expenseinstallment" ("id", "created_at", "updated_at", "is_deleted", "deleted_at", "installment_number", "total_installments", "amount", "due_date", "is_paid", "paid_date", "notes", "created_by_id", "deleted_by_id", "expense_id", "updated_by_id") FROM stdin;
2551	2026-04-01 14:02:44.777003-03	2026-04-01 14:02:44.777007-03	f	\N	1	7	114.28	2025-10-02	t	2025-10-02		\N	\N	304	\N
2564	2026-04-01 14:03:33.439108-03	2026-04-01 14:03:33.439111-03	f	\N	7	12	63.33	2026-07-02	f	\N		\N	\N	305	\N
2576	2026-04-01 14:10:37.34195-03	2026-04-01 14:10:37.341953-03	f	\N	1	10	125.00	2026-02-01	t	2026-02-01		\N	\N	307	\N
2588	2026-04-01 14:10:57.936513-03	2026-04-01 14:10:57.936517-03	f	\N	3	6	50.00	2026-05-02	f	\N		\N	\N	308	\N
2272	2026-03-23 19:17:45.288049-03	2026-03-23 19:17:45.288052-03	t	2026-04-01 15:03:39.725269-03	331	510	90.00	2053-03-30	f	\N		3	\N	190	3
2232	2026-03-23 19:17:45.28668-03	2026-03-23 19:17:45.286683-03	t	2026-04-01 15:03:39.725269-03	291	510	90.00	2049-11-30	f	\N		3	\N	190	3
2171	2026-03-23 19:17:45.28469-03	2026-03-23 19:17:45.284692-03	t	2026-04-01 15:03:39.725269-03	230	510	90.00	2044-10-30	f	\N		3	\N	190	3
2121	2026-03-23 19:17:45.282881-03	2026-03-23 19:17:45.282884-03	t	2026-04-01 15:03:39.725269-03	180	510	90.00	2040-08-30	f	\N		3	\N	190	3
2157	2026-03-23 19:17:45.284082-03	2026-03-23 19:17:45.284085-03	t	2026-04-01 15:03:39.725269-03	216	510	90.00	2043-08-30	f	\N		3	\N	190	3
2191	2026-03-23 19:17:45.285334-03	2026-03-23 19:17:45.285336-03	t	2026-04-01 15:03:39.725269-03	250	510	90.00	2046-06-30	f	\N		3	\N	190	3
2150	2026-03-23 19:17:45.283856-03	2026-03-23 19:17:45.283858-03	t	2026-04-01 15:03:39.725269-03	209	510	90.00	2043-01-30	f	\N		3	\N	190	3
2043	2026-03-23 19:17:45.280126-03	2026-03-23 19:17:45.280128-03	t	2026-04-01 15:03:39.725269-03	102	510	90.00	2034-03-02	f	\N		3	\N	190	3
2061	2026-03-23 19:17:45.280702-03	2026-03-23 19:17:45.280705-03	t	2026-04-01 15:03:39.725269-03	120	510	90.00	2035-08-30	f	\N		3	\N	190	3
2391	2026-03-23 19:17:45.291618-03	2026-03-23 19:17:45.291621-03	t	2026-04-01 15:03:39.725269-03	450	510	90.00	2063-03-02	f	\N		3	\N	190	3
2302	2026-03-23 19:17:45.288714-03	2026-03-23 19:17:45.288715-03	t	2026-04-01 15:03:39.725269-03	361	510	90.00	2055-09-30	f	\N		3	\N	190	3
1987	2026-03-23 19:17:45.278575-03	2026-03-23 19:17:45.278576-03	t	2026-04-01 15:03:39.725269-03	46	510	90.00	2029-06-30	f	\N		3	\N	190	3
2238	2026-03-23 19:17:45.286887-03	2026-03-23 19:17:45.286889-03	t	2026-04-01 15:03:39.725269-03	297	510	90.00	2050-05-30	f	\N		3	\N	190	3
2233	2026-03-23 19:17:45.286713-03	2026-03-23 19:17:45.286716-03	t	2026-04-01 15:03:39.725269-03	292	510	90.00	2049-12-30	f	\N		3	\N	190	3
1948	2026-03-23 19:17:45.277916-03	2026-03-23 19:17:45.277917-03	t	2026-04-01 15:03:39.725269-03	7	510	90.00	2026-03-30	f	\N		3	\N	190	3
2389	2026-03-23 19:17:45.291551-03	2026-03-23 19:17:45.291553-03	t	2026-04-01 15:03:39.725269-03	448	510	90.00	2062-12-30	f	\N		3	\N	190	3
2218	2026-03-23 19:17:45.286215-03	2026-03-23 19:17:45.286218-03	t	2026-04-01 15:03:39.725269-03	277	510	90.00	2048-09-30	f	\N		3	\N	190	3
1947	2026-03-23 19:17:45.277897-03	2026-03-23 19:17:45.277898-03	t	2026-04-01 15:03:39.725269-03	6	510	90.00	2026-03-02	t	2026-03-02		3	\N	190	3
2235	2026-03-23 19:17:45.286783-03	2026-03-23 19:17:45.286786-03	t	2026-04-01 15:03:39.725269-03	294	510	90.00	2050-03-02	f	\N		3	\N	190	3
2214	2026-03-23 19:17:45.286074-03	2026-03-23 19:17:45.286076-03	t	2026-04-01 15:03:39.725269-03	273	510	90.00	2048-05-30	f	\N		3	\N	190	3
2136	2026-03-23 19:17:45.283398-03	2026-03-23 19:17:45.283401-03	t	2026-04-01 15:03:39.725269-03	195	510	90.00	2041-11-30	f	\N		3	\N	190	3
2370	2026-03-23 19:17:45.290859-03	2026-03-23 19:17:45.290862-03	t	2026-04-01 15:03:39.725269-03	429	510	90.00	2061-05-30	f	\N		3	\N	190	3
2245	2026-03-23 19:17:45.287123-03	2026-03-23 19:17:45.287125-03	t	2026-04-01 15:03:39.725269-03	304	510	90.00	2050-12-30	f	\N		3	\N	190	3
1951	2026-03-23 19:17:45.277971-03	2026-03-23 19:17:45.277972-03	t	2026-04-01 15:03:39.725269-03	10	510	90.00	2026-06-30	f	\N		3	\N	190	3
1966	2026-03-23 19:17:45.278229-03	2026-03-23 19:17:45.278231-03	t	2026-04-01 15:03:39.725269-03	25	510	90.00	2027-09-30	f	\N		3	\N	190	3
2294	2026-03-23 19:17:45.288577-03	2026-03-23 19:17:45.288578-03	t	2026-04-01 15:03:39.725269-03	353	510	90.00	2055-01-30	f	\N		3	\N	190	3
2324	2026-03-23 19:17:45.289082-03	2026-03-23 19:17:45.289083-03	t	2026-04-01 15:03:39.725269-03	383	510	90.00	2057-07-30	f	\N		3	\N	190	3
2345	2026-03-23 19:17:45.290011-03	2026-03-23 19:17:45.290013-03	t	2026-04-01 15:03:39.725269-03	404	510	90.00	2059-04-30	f	\N		3	\N	190	3
2303	2026-03-23 19:17:45.288731-03	2026-03-23 19:17:45.288732-03	t	2026-04-01 15:03:39.725269-03	362	510	90.00	2055-10-30	f	\N		3	\N	190	3
2119	2026-03-23 19:17:45.282814-03	2026-03-23 19:17:45.282816-03	t	2026-04-01 15:03:39.725269-03	178	510	90.00	2040-06-30	f	\N		3	\N	190	3
1968	2026-03-23 19:17:45.278263-03	2026-03-23 19:17:45.278264-03	t	2026-04-01 15:03:39.725269-03	27	510	90.00	2027-11-30	f	\N		3	\N	190	3
2109	2026-03-23 19:17:45.282262-03	2026-03-23 19:17:45.282265-03	t	2026-04-01 15:03:39.725269-03	168	510	90.00	2039-08-30	f	\N		3	\N	190	3
2273	2026-03-23 19:17:45.288083-03	2026-03-23 19:17:45.288086-03	t	2026-04-01 15:03:39.725269-03	332	510	90.00	2053-04-30	f	\N		3	\N	190	3
2149	2026-03-23 19:17:45.283823-03	2026-03-23 19:17:45.283826-03	t	2026-04-01 15:03:39.725269-03	208	510	90.00	2042-12-30	f	\N		3	\N	190	3
2012	2026-03-23 19:17:45.278984-03	2026-03-23 19:17:45.278985-03	t	2026-04-01 15:03:39.725269-03	71	510	90.00	2031-07-30	f	\N		3	\N	190	3
2446	2026-03-23 19:17:45.29337-03	2026-03-23 19:17:45.293371-03	t	2026-04-01 15:03:39.725269-03	505	510	90.00	2067-09-30	f	\N		3	\N	190	3
2266	2026-03-23 19:17:45.287851-03	2026-03-23 19:17:45.287853-03	t	2026-04-01 15:03:39.725269-03	325	510	90.00	2052-09-30	f	\N		3	\N	190	3
2162	2026-03-23 19:17:45.284271-03	2026-03-23 19:17:45.284272-03	t	2026-04-01 15:03:39.725269-03	221	510	90.00	2044-01-30	f	\N		3	\N	190	3
2151	2026-03-23 19:17:45.283889-03	2026-03-23 19:17:45.283892-03	t	2026-04-01 15:03:39.725269-03	210	510	90.00	2043-03-02	f	\N		3	\N	190	3
2378	2026-03-23 19:17:45.291177-03	2026-03-23 19:17:45.29118-03	t	2026-04-01 15:03:39.725269-03	437	510	90.00	2062-01-30	f	\N		3	\N	190	3
2252	2026-03-23 19:17:45.287365-03	2026-03-23 19:17:45.287367-03	t	2026-04-01 15:03:39.725269-03	311	510	90.00	2051-07-30	f	\N		3	\N	190	3
2231	2026-03-23 19:17:45.286646-03	2026-03-23 19:17:45.286649-03	t	2026-04-01 15:03:39.725269-03	290	510	90.00	2049-10-30	f	\N		3	\N	190	3
2427	2026-03-23 19:17:45.292857-03	2026-03-23 19:17:45.29286-03	t	2026-04-01 15:03:39.725269-03	486	510	90.00	2066-03-02	f	\N		3	\N	190	3
2029	2026-03-23 19:17:45.279675-03	2026-03-23 19:17:45.279678-03	t	2026-04-01 15:03:39.725269-03	88	510	90.00	2032-12-30	f	\N		3	\N	190	3
2085	2026-03-23 19:17:45.28148-03	2026-03-23 19:17:45.281483-03	t	2026-04-01 15:03:39.725269-03	144	510	90.00	2037-08-30	f	\N		3	\N	190	3
2130	2026-03-23 19:17:45.283202-03	2026-03-23 19:17:45.283205-03	t	2026-04-01 15:03:39.725269-03	189	510	90.00	2041-05-30	f	\N		3	\N	190	3
1956	2026-03-23 19:17:45.278058-03	2026-03-23 19:17:45.278059-03	t	2026-04-01 15:03:39.725269-03	15	510	90.00	2026-11-30	f	\N		3	\N	190	3
2244	2026-03-23 19:17:45.287089-03	2026-03-23 19:17:45.287091-03	t	2026-04-01 15:03:39.725269-03	303	510	90.00	2050-11-30	f	\N		3	\N	190	3
2084	2026-03-23 19:17:45.281449-03	2026-03-23 19:17:45.281451-03	t	2026-04-01 15:03:39.725269-03	143	510	90.00	2037-07-30	f	\N		3	\N	190	3
2066	2026-03-23 19:17:45.280861-03	2026-03-23 19:17:45.280874-03	t	2026-04-01 15:03:39.725269-03	125	510	90.00	2036-01-30	f	\N		3	\N	190	3
2383	2026-03-23 19:17:45.291348-03	2026-03-23 19:17:45.29135-03	t	2026-04-01 15:03:39.725269-03	442	510	90.00	2062-06-30	f	\N		3	\N	190	3
2348	2026-03-23 19:17:45.290113-03	2026-03-23 19:17:45.290115-03	t	2026-04-01 15:03:39.725269-03	407	510	90.00	2059-07-30	f	\N		3	\N	190	3
2086	2026-03-23 19:17:45.281512-03	2026-03-23 19:17:45.281514-03	t	2026-04-01 15:03:39.725269-03	145	510	90.00	2037-09-30	f	\N		3	\N	190	3
2222	2026-03-23 19:17:45.286343-03	2026-03-23 19:17:45.286345-03	t	2026-04-01 15:03:39.725269-03	281	510	90.00	2049-01-30	f	\N		3	\N	190	3
2216	2026-03-23 19:17:45.286138-03	2026-03-23 19:17:45.286141-03	t	2026-04-01 15:03:39.725269-03	275	510	90.00	2048-07-30	f	\N		3	\N	190	3
2005	2026-03-23 19:17:45.278867-03	2026-03-23 19:17:45.278868-03	t	2026-04-01 15:03:39.725269-03	64	510	90.00	2030-12-30	f	\N		3	\N	190	3
2360	2026-03-23 19:17:45.290518-03	2026-03-23 19:17:45.29052-03	t	2026-04-01 15:03:39.725269-03	419	510	90.00	2060-07-30	f	\N		3	\N	190	3
2330	2026-03-23 19:17:45.2895-03	2026-03-23 19:17:45.289502-03	t	2026-04-01 15:03:39.725269-03	389	510	90.00	2058-01-30	f	\N		3	\N	190	3
2445	2026-03-23 19:17:45.293352-03	2026-03-23 19:17:45.293353-03	t	2026-04-01 15:03:39.725269-03	504	510	90.00	2067-08-30	f	\N		3	\N	190	3
2347	2026-03-23 19:17:45.290079-03	2026-03-23 19:17:45.290081-03	t	2026-04-01 15:03:39.725269-03	406	510	90.00	2059-06-30	f	\N		3	\N	190	3
2329	2026-03-23 19:17:45.289465-03	2026-03-23 19:17:45.289468-03	t	2026-04-01 15:03:39.725269-03	388	510	90.00	2057-12-30	f	\N		3	\N	190	3
2060	2026-03-23 19:17:45.280671-03	2026-03-23 19:17:45.280674-03	t	2026-04-01 15:03:39.725269-03	119	510	90.00	2035-07-30	f	\N		3	\N	190	3
2552	2026-04-01 14:02:44.841426-03	2026-04-01 14:02:44.841431-03	f	\N	2	7	114.28	2025-11-01	t	2025-11-01		\N	\N	304	\N
2565	2026-04-01 14:03:33.480374-03	2026-04-01 14:03:33.480377-03	f	\N	8	12	63.33	2026-08-01	f	\N		\N	\N	305	\N
2577	2026-04-01 14:10:37.38287-03	2026-04-01 14:10:37.382873-03	f	\N	2	10	125.00	2026-03-04	t	2026-03-04		\N	\N	307	\N
2589	2026-04-01 14:10:57.974816-03	2026-04-01 14:10:57.97482-03	f	\N	4	6	50.00	2026-06-01	f	\N		\N	\N	308	\N
2221	2026-03-23 19:17:45.286311-03	2026-03-23 19:17:45.286313-03	t	2026-04-01 15:03:39.725269-03	280	510	90.00	2048-12-30	f	\N		3	\N	190	3
2169	2026-03-23 19:17:45.284623-03	2026-03-23 19:17:45.284625-03	t	2026-04-01 15:03:39.725269-03	228	510	90.00	2044-08-30	f	\N		3	\N	190	3
2306	2026-03-23 19:17:45.288781-03	2026-03-23 19:17:45.288782-03	t	2026-04-01 15:03:39.725269-03	365	510	90.00	2056-01-30	f	\N		3	\N	190	3
2417	2026-03-23 19:17:45.292511-03	2026-03-23 19:17:45.292514-03	t	2026-04-01 15:03:39.725269-03	476	510	90.00	2065-04-30	f	\N		3	\N	190	3
2411	2026-03-23 19:17:45.292307-03	2026-03-23 19:17:45.29231-03	t	2026-04-01 15:03:39.725269-03	470	510	90.00	2064-10-30	f	\N		3	\N	190	3
2261	2026-03-23 19:17:45.287682-03	2026-03-23 19:17:45.287685-03	t	2026-04-01 15:03:39.725269-03	320	510	90.00	2052-04-30	f	\N		3	\N	190	3
1980	2026-03-23 19:17:45.27846-03	2026-03-23 19:17:45.278461-03	t	2026-04-01 15:03:39.725269-03	39	510	90.00	2028-11-30	f	\N		3	\N	190	3
2327	2026-03-23 19:17:45.289394-03	2026-03-23 19:17:45.289397-03	t	2026-04-01 15:03:39.725269-03	386	510	90.00	2057-10-30	f	\N		3	\N	190	3
2368	2026-03-23 19:17:45.29079-03	2026-03-23 19:17:45.290793-03	t	2026-04-01 15:03:39.725269-03	427	510	90.00	2061-03-30	f	\N		3	\N	190	3
2380	2026-03-23 19:17:45.291245-03	2026-03-23 19:17:45.291247-03	t	2026-04-01 15:03:39.725269-03	439	510	90.00	2062-03-30	f	\N		3	\N	190	3
2367	2026-03-23 19:17:45.290756-03	2026-03-23 19:17:45.290759-03	t	2026-04-01 15:03:39.725269-03	426	510	90.00	2061-03-02	f	\N		3	\N	190	3
2058	2026-03-23 19:17:45.280608-03	2026-03-23 19:17:45.280611-03	t	2026-04-01 15:03:39.725269-03	117	510	90.00	2035-05-30	f	\N		3	\N	190	3
1986	2026-03-23 19:17:45.278558-03	2026-03-23 19:17:45.278559-03	t	2026-04-01 15:03:39.725269-03	45	510	90.00	2029-05-30	f	\N		3	\N	190	3
2281	2026-03-23 19:17:45.288352-03	2026-03-23 19:17:45.288353-03	t	2026-04-01 15:03:39.725269-03	340	510	90.00	2053-12-30	f	\N		3	\N	190	3
2255	2026-03-23 19:17:45.28747-03	2026-03-23 19:17:45.287473-03	t	2026-04-01 15:03:39.725269-03	314	510	90.00	2051-10-30	f	\N		3	\N	190	3
2137	2026-03-23 19:17:45.283432-03	2026-03-23 19:17:45.283435-03	t	2026-04-01 15:03:39.725269-03	196	510	90.00	2041-12-30	f	\N		3	\N	190	3
1995	2026-03-23 19:17:45.278705-03	2026-03-23 19:17:45.278706-03	t	2026-04-01 15:03:39.725269-03	54	510	90.00	2030-03-02	f	\N		3	\N	190	3
2230	2026-03-23 19:17:45.286613-03	2026-03-23 19:17:45.286616-03	t	2026-04-01 15:03:39.725269-03	289	510	90.00	2049-09-30	f	\N		3	\N	190	3
2449	2026-03-23 19:17:45.293422-03	2026-03-23 19:17:45.293423-03	t	2026-04-01 15:03:39.725269-03	508	510	90.00	2067-12-30	f	\N		3	\N	190	3
2096	2026-03-23 19:17:45.281836-03	2026-03-23 19:17:45.281838-03	t	2026-04-01 15:03:39.725269-03	155	510	90.00	2038-07-30	f	\N		3	\N	190	3
2217	2026-03-23 19:17:45.286182-03	2026-03-23 19:17:45.286185-03	t	2026-04-01 15:03:39.725269-03	276	510	90.00	2048-08-30	f	\N		3	\N	190	3
2156	2026-03-23 19:17:45.28405-03	2026-03-23 19:17:45.284053-03	t	2026-04-01 15:03:39.725269-03	215	510	90.00	2043-07-30	f	\N		3	\N	190	3
2093	2026-03-23 19:17:45.281739-03	2026-03-23 19:17:45.281741-03	t	2026-04-01 15:03:39.725269-03	152	510	90.00	2038-04-30	f	\N		3	\N	190	3
2118	2026-03-23 19:17:45.28278-03	2026-03-23 19:17:45.282783-03	t	2026-04-01 15:03:39.725269-03	177	510	90.00	2040-05-30	f	\N		3	\N	190	3
2091	2026-03-23 19:17:45.281675-03	2026-03-23 19:17:45.281677-03	t	2026-04-01 15:03:39.725269-03	150	510	90.00	2038-03-02	f	\N		3	\N	190	3
2350	2026-03-23 19:17:45.290181-03	2026-03-23 19:17:45.290183-03	t	2026-04-01 15:03:39.725269-03	409	510	90.00	2059-09-30	f	\N		3	\N	190	3
2317	2026-03-23 19:17:45.288963-03	2026-03-23 19:17:45.288964-03	t	2026-04-01 15:03:39.725269-03	376	510	90.00	2056-12-30	f	\N		3	\N	190	3
2326	2026-03-23 19:17:45.289353-03	2026-03-23 19:17:45.289356-03	t	2026-04-01 15:03:39.725269-03	385	510	90.00	2057-09-30	f	\N		3	\N	190	3
2250	2026-03-23 19:17:45.287291-03	2026-03-23 19:17:45.287294-03	t	2026-04-01 15:03:39.725269-03	309	510	90.00	2051-05-30	f	\N		3	\N	190	3
2105	2026-03-23 19:17:45.282129-03	2026-03-23 19:17:45.282131-03	t	2026-04-01 15:03:39.725269-03	164	510	90.00	2039-04-30	f	\N		3	\N	190	3
2184	2026-03-23 19:17:45.285112-03	2026-03-23 19:17:45.285115-03	t	2026-04-01 15:03:39.725269-03	243	510	90.00	2045-11-30	f	\N		3	\N	190	3
2224	2026-03-23 19:17:45.28641-03	2026-03-23 19:17:45.286412-03	t	2026-04-01 15:03:39.725269-03	283	510	90.00	2049-03-30	f	\N		3	\N	190	3
2410	2026-03-23 19:17:45.292273-03	2026-03-23 19:17:45.292276-03	t	2026-04-01 15:03:39.725269-03	469	510	90.00	2064-09-30	f	\N		3	\N	190	3
2254	2026-03-23 19:17:45.287435-03	2026-03-23 19:17:45.287438-03	t	2026-04-01 15:03:39.725269-03	313	510	90.00	2051-09-30	f	\N		3	\N	190	3
2426	2026-03-23 19:17:45.292823-03	2026-03-23 19:17:45.292826-03	t	2026-04-01 15:03:39.725269-03	485	510	90.00	2066-01-30	f	\N		3	\N	190	3
2143	2026-03-23 19:17:45.28363-03	2026-03-23 19:17:45.283632-03	t	2026-04-01 15:03:39.725269-03	202	510	90.00	2042-06-30	f	\N		3	\N	190	3
2087	2026-03-23 19:17:45.281544-03	2026-03-23 19:17:45.281546-03	t	2026-04-01 15:03:39.725269-03	146	510	90.00	2037-10-30	f	\N		3	\N	190	3
1946	2026-03-23 19:17:45.277878-03	2026-03-23 19:17:45.277879-03	t	2026-04-01 15:03:39.725269-03	5	510	90.00	2026-01-30	t	2026-01-30		3	\N	190	3
2339	2026-03-23 19:17:45.289804-03	2026-03-23 19:17:45.289806-03	t	2026-04-01 15:03:39.725269-03	398	510	90.00	2058-10-30	f	\N		3	\N	190	3
1976	2026-03-23 19:17:45.278395-03	2026-03-23 19:17:45.278396-03	t	2026-04-01 15:03:39.725269-03	35	510	90.00	2028-07-30	f	\N		3	\N	190	3
2186	2026-03-23 19:17:45.285175-03	2026-03-23 19:17:45.285178-03	t	2026-04-01 15:03:39.725269-03	245	510	90.00	2046-01-30	f	\N		3	\N	190	3
2083	2026-03-23 19:17:45.281417-03	2026-03-23 19:17:45.28142-03	t	2026-04-01 15:03:39.725269-03	142	510	90.00	2037-06-30	f	\N		3	\N	190	3
1961	2026-03-23 19:17:45.278145-03	2026-03-23 19:17:45.278146-03	t	2026-04-01 15:03:39.725269-03	20	510	90.00	2027-04-30	f	\N		3	\N	190	3
2219	2026-03-23 19:17:45.286247-03	2026-03-23 19:17:45.28625-03	t	2026-04-01 15:03:39.725269-03	278	510	90.00	2048-10-30	f	\N		3	\N	190	3
2072	2026-03-23 19:17:45.281066-03	2026-03-23 19:17:45.281069-03	t	2026-04-01 15:03:39.725269-03	131	510	90.00	2036-07-30	f	\N		3	\N	190	3
2396	2026-03-23 19:17:45.291792-03	2026-03-23 19:17:45.291795-03	t	2026-04-01 15:03:39.725269-03	455	510	90.00	2063-07-30	f	\N		3	\N	190	3
2095	2026-03-23 19:17:45.281804-03	2026-03-23 19:17:45.281806-03	t	2026-04-01 15:03:39.725269-03	154	510	90.00	2038-06-30	f	\N		3	\N	190	3
2436	2026-03-23 19:17:45.293194-03	2026-03-23 19:17:45.293195-03	t	2026-04-01 15:03:39.725269-03	495	510	90.00	2066-11-30	f	\N		3	\N	190	3
2049	2026-03-23 19:17:45.280317-03	2026-03-23 19:17:45.28032-03	t	2026-04-01 15:03:39.725269-03	108	510	90.00	2034-08-30	f	\N		3	\N	190	3
2341	2026-03-23 19:17:45.289871-03	2026-03-23 19:17:45.289874-03	t	2026-04-01 15:03:39.725269-03	400	510	90.00	2058-12-30	f	\N		3	\N	190	3
2447	2026-03-23 19:17:45.293387-03	2026-03-23 19:17:45.293388-03	t	2026-04-01 15:03:39.725269-03	506	510	90.00	2067-10-30	f	\N		3	\N	190	3
2318	2026-03-23 19:17:45.28898-03	2026-03-23 19:17:45.288982-03	t	2026-04-01 15:03:39.725269-03	377	510	90.00	2057-01-30	f	\N		3	\N	190	3
2253	2026-03-23 19:17:45.287399-03	2026-03-23 19:17:45.287402-03	t	2026-04-01 15:03:39.725269-03	312	510	90.00	2051-08-30	f	\N		3	\N	190	3
1974	2026-03-23 19:17:45.278361-03	2026-03-23 19:17:45.278363-03	t	2026-04-01 15:03:39.725269-03	33	510	90.00	2028-05-30	f	\N		3	\N	190	3
1977	2026-03-23 19:17:45.278411-03	2026-03-23 19:17:45.278412-03	t	2026-04-01 15:03:39.725269-03	36	510	90.00	2028-08-30	f	\N		3	\N	190	3
2022	2026-03-23 19:17:45.279447-03	2026-03-23 19:17:45.27945-03	t	2026-04-01 15:03:39.725269-03	81	510	90.00	2032-05-30	f	\N		3	\N	190	3
1983	2026-03-23 19:17:45.278509-03	2026-03-23 19:17:45.27851-03	t	2026-04-01 15:03:39.725269-03	42	510	90.00	2029-03-02	f	\N		3	\N	190	3
2314	2026-03-23 19:17:45.288913-03	2026-03-23 19:17:45.288914-03	t	2026-04-01 15:03:39.725269-03	373	510	90.00	2056-09-30	f	\N		3	\N	190	3
2114	2026-03-23 19:17:45.282627-03	2026-03-23 19:17:45.28263-03	t	2026-04-01 15:03:39.725269-03	173	510	90.00	2040-01-30	f	\N		3	\N	190	3
2037	2026-03-23 19:17:45.279933-03	2026-03-23 19:17:45.279936-03	t	2026-04-01 15:03:39.725269-03	96	510	90.00	2033-08-30	f	\N		3	\N	190	3
2297	2026-03-23 19:17:45.28863-03	2026-03-23 19:17:45.288631-03	t	2026-04-01 15:03:39.725269-03	356	510	90.00	2055-04-30	f	\N		3	\N	190	3
2053	2026-03-23 19:17:45.28045-03	2026-03-23 19:17:45.280452-03	t	2026-04-01 15:03:39.725269-03	112	510	90.00	2034-12-30	f	\N		3	\N	190	3
2553	2026-04-01 14:02:44.889065-03	2026-04-01 14:02:44.88907-03	f	\N	3	7	114.28	2025-12-02	t	2025-12-02		\N	\N	304	\N
2566	2026-04-01 14:03:33.520856-03	2026-04-01 14:03:33.52086-03	f	\N	9	12	63.33	2026-09-01	f	\N		\N	\N	305	\N
2578	2026-04-01 14:10:37.420401-03	2026-04-01 14:10:37.420403-03	f	\N	3	10	125.00	2026-04-01	f	\N		\N	\N	307	\N
2590	2026-04-01 14:10:58.123747-03	2026-04-01 14:10:58.12375-03	f	\N	5	6	50.00	2026-07-02	f	\N		\N	\N	308	\N
2390	2026-03-23 19:17:45.291584-03	2026-03-23 19:17:45.291587-03	t	2026-04-01 15:03:39.725269-03	449	510	90.00	2063-01-30	f	\N		3	\N	190	3
2471	2026-03-23 19:18:06.218541-03	2026-03-23 19:18:06.218544-03	t	2026-04-01 15:03:39.725269-03	8	10	106.00	2026-05-30	f	\N		3	\N	192	3
2193	2026-03-23 19:17:45.285397-03	2026-03-23 19:17:45.2854-03	t	2026-04-01 15:03:39.725269-03	252	510	90.00	2046-08-30	f	\N		3	\N	190	3
2363	2026-03-23 19:17:45.290619-03	2026-03-23 19:17:45.290621-03	t	2026-04-01 15:03:39.725269-03	422	510	90.00	2060-10-30	f	\N		3	\N	190	3
2355	2026-03-23 19:17:45.29035-03	2026-03-23 19:17:45.290353-03	t	2026-04-01 15:03:39.725269-03	414	510	90.00	2060-03-01	f	\N		3	\N	190	3
2342	2026-03-23 19:17:45.289905-03	2026-03-23 19:17:45.289908-03	t	2026-04-01 15:03:39.725269-03	401	510	90.00	2059-01-30	f	\N		3	\N	190	3
2160	2026-03-23 19:17:45.284236-03	2026-03-23 19:17:45.284237-03	t	2026-04-01 15:03:39.725269-03	219	510	90.00	2043-11-30	f	\N		3	\N	190	3
2126	2026-03-23 19:17:45.283049-03	2026-03-23 19:17:45.283052-03	t	2026-04-01 15:03:39.725269-03	185	510	90.00	2041-01-30	f	\N		3	\N	190	3
2271	2026-03-23 19:17:45.288015-03	2026-03-23 19:17:45.288017-03	t	2026-04-01 15:03:39.725269-03	330	510	90.00	2053-03-02	f	\N		3	\N	190	3
2433	2026-03-23 19:17:45.293139-03	2026-03-23 19:17:45.29314-03	t	2026-04-01 15:03:39.725269-03	492	510	90.00	2066-08-30	f	\N		3	\N	190	3
2362	2026-03-23 19:17:45.290585-03	2026-03-23 19:17:45.290587-03	t	2026-04-01 15:03:39.725269-03	421	510	90.00	2060-09-30	f	\N		3	\N	190	3
2334	2026-03-23 19:17:45.289636-03	2026-03-23 19:17:45.289638-03	t	2026-04-01 15:03:39.725269-03	393	510	90.00	2058-05-30	f	\N		3	\N	190	3
2270	2026-03-23 19:17:45.287982-03	2026-03-23 19:17:45.287985-03	t	2026-04-01 15:03:39.725269-03	329	510	90.00	2053-01-30	f	\N		3	\N	190	3
2077	2026-03-23 19:17:45.281226-03	2026-03-23 19:17:45.281228-03	t	2026-04-01 15:03:39.725269-03	136	510	90.00	2036-12-30	f	\N		3	\N	190	3
2018	2026-03-23 19:17:45.279308-03	2026-03-23 19:17:45.279311-03	t	2026-04-01 15:03:39.725269-03	77	510	90.00	2032-01-30	f	\N		3	\N	190	3
2243	2026-03-23 19:17:45.287055-03	2026-03-23 19:17:45.287058-03	t	2026-04-01 15:03:39.725269-03	302	510	90.00	2050-10-30	f	\N		3	\N	190	3
2034	2026-03-23 19:17:45.279835-03	2026-03-23 19:17:45.279838-03	t	2026-04-01 15:03:39.725269-03	93	510	90.00	2033-05-30	f	\N		3	\N	190	3
2372	2026-03-23 19:17:45.290927-03	2026-03-23 19:17:45.29093-03	t	2026-04-01 15:03:39.725269-03	431	510	90.00	2061-07-30	f	\N		3	\N	190	3
2292	2026-03-23 19:17:45.288543-03	2026-03-23 19:17:45.288544-03	t	2026-04-01 15:03:39.725269-03	351	510	90.00	2054-11-30	f	\N		3	\N	190	3
2406	2026-03-23 19:17:45.292136-03	2026-03-23 19:17:45.292139-03	t	2026-04-01 15:03:39.725269-03	465	510	90.00	2064-05-30	f	\N		3	\N	190	3
2179	2026-03-23 19:17:45.284953-03	2026-03-23 19:17:45.284956-03	t	2026-04-01 15:03:39.725269-03	238	510	90.00	2045-06-30	f	\N		3	\N	190	3
1994	2026-03-23 19:17:45.278688-03	2026-03-23 19:17:45.278689-03	t	2026-04-01 15:03:39.725269-03	53	510	90.00	2030-01-30	f	\N		3	\N	190	3
2089	2026-03-23 19:17:45.281609-03	2026-03-23 19:17:45.281611-03	t	2026-04-01 15:03:39.725269-03	148	510	90.00	2037-12-30	f	\N		3	\N	190	3
2014	2026-03-23 19:17:45.279017-03	2026-03-23 19:17:45.279018-03	t	2026-04-01 15:03:39.725269-03	73	510	90.00	2031-09-30	f	\N		3	\N	190	3
2161	2026-03-23 19:17:45.284253-03	2026-03-23 19:17:45.284254-03	t	2026-04-01 15:03:39.725269-03	220	510	90.00	2043-12-30	f	\N		3	\N	190	3
2418	2026-03-23 19:17:45.292545-03	2026-03-23 19:17:45.292548-03	t	2026-04-01 15:03:39.725269-03	477	510	90.00	2065-05-30	f	\N		3	\N	190	3
2310	2026-03-23 19:17:45.288846-03	2026-03-23 19:17:45.288848-03	t	2026-04-01 15:03:39.725269-03	369	510	90.00	2056-05-30	f	\N		3	\N	190	3
2155	2026-03-23 19:17:45.284018-03	2026-03-23 19:17:45.284021-03	t	2026-04-01 15:03:39.725269-03	214	510	90.00	2043-06-30	f	\N		3	\N	190	3
2164	2026-03-23 19:17:45.284304-03	2026-03-23 19:17:45.284305-03	t	2026-04-01 15:03:39.725269-03	223	510	90.00	2044-03-30	f	\N		3	\N	190	3
1985	2026-03-23 19:17:45.278542-03	2026-03-23 19:17:45.278543-03	t	2026-04-01 15:03:39.725269-03	44	510	90.00	2029-04-30	f	\N		3	\N	190	3
2158	2026-03-23 19:17:45.284181-03	2026-03-23 19:17:45.284184-03	t	2026-04-01 15:03:39.725269-03	217	510	90.00	2043-09-30	f	\N		3	\N	190	3
2376	2026-03-23 19:17:45.291108-03	2026-03-23 19:17:45.291111-03	t	2026-04-01 15:03:39.725269-03	435	510	90.00	2061-11-30	f	\N		3	\N	190	3
2194	2026-03-23 19:17:45.28543-03	2026-03-23 19:17:45.285433-03	t	2026-04-01 15:03:39.725269-03	253	510	90.00	2046-09-30	f	\N		3	\N	190	3
2225	2026-03-23 19:17:45.286443-03	2026-03-23 19:17:45.286445-03	t	2026-04-01 15:03:39.725269-03	284	510	90.00	2049-04-30	f	\N		3	\N	190	3
2413	2026-03-23 19:17:45.292376-03	2026-03-23 19:17:45.292378-03	t	2026-04-01 15:03:39.725269-03	472	510	90.00	2064-12-30	f	\N		3	\N	190	3
2374	2026-03-23 19:17:45.29104-03	2026-03-23 19:17:45.291042-03	t	2026-04-01 15:03:39.725269-03	433	510	90.00	2061-09-30	f	\N		3	\N	190	3
2428	2026-03-23 19:17:45.292891-03	2026-03-23 19:17:45.292894-03	t	2026-04-01 15:03:39.725269-03	487	510	90.00	2066-03-30	f	\N		3	\N	190	3
2100	2026-03-23 19:17:45.281967-03	2026-03-23 19:17:45.281969-03	t	2026-04-01 15:03:39.725269-03	159	510	90.00	2038-11-30	f	\N		3	\N	190	3
2062	2026-03-23 19:17:45.280734-03	2026-03-23 19:17:45.280736-03	t	2026-04-01 15:03:39.725269-03	121	510	90.00	2035-09-30	f	\N		3	\N	190	3
2386	2026-03-23 19:17:45.291449-03	2026-03-23 19:17:45.291451-03	t	2026-04-01 15:03:39.725269-03	445	510	90.00	2062-09-30	f	\N		3	\N	190	3
2353	2026-03-23 19:17:45.290282-03	2026-03-23 19:17:45.290285-03	t	2026-04-01 15:03:39.725269-03	412	510	90.00	2059-12-30	f	\N		3	\N	190	3
2240	2026-03-23 19:17:45.286954-03	2026-03-23 19:17:45.286957-03	t	2026-04-01 15:03:39.725269-03	299	510	90.00	2050-07-30	f	\N		3	\N	190	3
2284	2026-03-23 19:17:45.288405-03	2026-03-23 19:17:45.288406-03	t	2026-04-01 15:03:39.725269-03	343	510	90.00	2054-03-30	f	\N		3	\N	190	3
2122	2026-03-23 19:17:45.282914-03	2026-03-23 19:17:45.282916-03	t	2026-04-01 15:03:39.725269-03	181	510	90.00	2040-09-30	f	\N		3	\N	190	3
2206	2026-03-23 19:17:45.285816-03	2026-03-23 19:17:45.285819-03	t	2026-04-01 15:03:39.725269-03	265	510	90.00	2047-09-30	f	\N		3	\N	190	3
1944	2026-03-23 19:17:45.277835-03	2026-03-23 19:17:45.277836-03	t	2026-04-01 15:03:39.725269-03	3	510	90.00	2025-11-30	t	2025-11-30		3	\N	190	3
2129	2026-03-23 19:17:45.283169-03	2026-03-23 19:17:45.283172-03	t	2026-04-01 15:03:39.725269-03	188	510	90.00	2041-04-30	f	\N		3	\N	190	3
2440	2026-03-23 19:17:45.293265-03	2026-03-23 19:17:45.293266-03	t	2026-04-01 15:03:39.725269-03	499	510	90.00	2067-03-30	f	\N		3	\N	190	3
2267	2026-03-23 19:17:45.287884-03	2026-03-23 19:17:45.287886-03	t	2026-04-01 15:03:39.725269-03	326	510	90.00	2052-10-30	f	\N		3	\N	190	3
2032	2026-03-23 19:17:45.279771-03	2026-03-23 19:17:45.279773-03	t	2026-04-01 15:03:39.725269-03	91	510	90.00	2033-03-30	f	\N		3	\N	190	3
2153	2026-03-23 19:17:45.283954-03	2026-03-23 19:17:45.283956-03	t	2026-04-01 15:03:39.725269-03	212	510	90.00	2043-04-30	f	\N		3	\N	190	3
2181	2026-03-23 19:17:45.285017-03	2026-03-23 19:17:45.28502-03	t	2026-04-01 15:03:39.725269-03	240	510	90.00	2045-08-30	f	\N		3	\N	190	3
2112	2026-03-23 19:17:45.282535-03	2026-03-23 19:17:45.282538-03	t	2026-04-01 15:03:39.725269-03	171	510	90.00	2039-11-30	f	\N		3	\N	190	3
2325	2026-03-23 19:17:45.289268-03	2026-03-23 19:17:45.289275-03	t	2026-04-01 15:03:39.725269-03	384	510	90.00	2057-08-30	f	\N		3	\N	190	3
2379	2026-03-23 19:17:45.29121-03	2026-03-23 19:17:45.291213-03	t	2026-04-01 15:03:39.725269-03	438	510	90.00	2062-03-02	f	\N		3	\N	190	3
2322	2026-03-23 19:17:45.289049-03	2026-03-23 19:17:45.28905-03	t	2026-04-01 15:03:39.725269-03	381	510	90.00	2057-05-30	f	\N		3	\N	190	3
2145	2026-03-23 19:17:45.283694-03	2026-03-23 19:17:45.283697-03	t	2026-04-01 15:03:39.725269-03	204	510	90.00	2042-08-30	f	\N		3	\N	190	3
2398	2026-03-23 19:17:45.29186-03	2026-03-23 19:17:45.291863-03	t	2026-04-01 15:03:39.725269-03	457	510	90.00	2063-09-30	f	\N		3	\N	190	3
1988	2026-03-23 19:17:45.278591-03	2026-03-23 19:17:45.278592-03	t	2026-04-01 15:03:39.725269-03	47	510	90.00	2029-07-30	f	\N		3	\N	190	3
2381	2026-03-23 19:17:45.291279-03	2026-03-23 19:17:45.291281-03	t	2026-04-01 15:03:39.725269-03	440	510	90.00	2062-04-30	f	\N		3	\N	190	3
2008	2026-03-23 19:17:45.278919-03	2026-03-23 19:17:45.27892-03	t	2026-04-01 15:03:39.725269-03	67	510	90.00	2031-03-30	f	\N		3	\N	190	3
2279	2026-03-23 19:17:45.288318-03	2026-03-23 19:17:45.288319-03	t	2026-04-01 15:03:39.725269-03	338	510	90.00	2053-10-30	f	\N		3	\N	190	3
2554	2026-04-01 14:02:45.032284-03	2026-04-01 14:02:45.032288-03	f	\N	4	7	114.28	2026-01-01	t	2026-01-01		\N	\N	304	\N
2567	2026-04-01 14:03:33.559957-03	2026-04-01 14:03:33.55996-03	f	\N	10	12	63.33	2026-10-02	f	\N		\N	\N	305	\N
2579	2026-04-01 14:10:37.4585-03	2026-04-01 14:10:37.458503-03	f	\N	4	10	125.00	2026-05-02	f	\N		\N	\N	307	\N
2591	2026-04-01 14:10:58.164358-03	2026-04-01 14:10:58.164362-03	f	\N	6	6	50.00	2026-08-01	f	\N		\N	\N	308	\N
2079	2026-03-23 19:17:45.28129-03	2026-03-23 19:17:45.281292-03	t	2026-04-01 15:03:39.725269-03	138	510	90.00	2037-03-02	f	\N		3	\N	190	3
2210	2026-03-23 19:17:45.285944-03	2026-03-23 19:17:45.285946-03	t	2026-04-01 15:03:39.725269-03	269	510	90.00	2048-01-30	f	\N		3	\N	190	3
1945	2026-03-23 19:17:45.277856-03	2026-03-23 19:17:45.277858-03	t	2026-04-01 15:03:39.725269-03	4	510	90.00	2025-12-30	t	2025-12-30		3	\N	190	3
2424	2026-03-23 19:17:45.292755-03	2026-03-23 19:17:45.292757-03	t	2026-04-01 15:03:39.725269-03	483	510	90.00	2065-11-30	f	\N		3	\N	190	3
2223	2026-03-23 19:17:45.286376-03	2026-03-23 19:17:45.286379-03	t	2026-04-01 15:03:39.725269-03	282	510	90.00	2049-03-02	f	\N		3	\N	190	3
2227	2026-03-23 19:17:45.28651-03	2026-03-23 19:17:45.286513-03	t	2026-04-01 15:03:39.725269-03	286	510	90.00	2049-06-30	f	\N		3	\N	190	3
2030	2026-03-23 19:17:45.279707-03	2026-03-23 19:17:45.279709-03	t	2026-04-01 15:03:39.725269-03	89	510	90.00	2033-01-30	f	\N		3	\N	190	3
2395	2026-03-23 19:17:45.291758-03	2026-03-23 19:17:45.291761-03	t	2026-04-01 15:03:39.725269-03	454	510	90.00	2063-06-30	f	\N		3	\N	190	3
2074	2026-03-23 19:17:45.28113-03	2026-03-23 19:17:45.281132-03	t	2026-04-01 15:03:39.725269-03	133	510	90.00	2036-09-30	f	\N		3	\N	190	3
2047	2026-03-23 19:17:45.280253-03	2026-03-23 19:17:45.280255-03	t	2026-04-01 15:03:39.725269-03	106	510	90.00	2034-06-30	f	\N		3	\N	190	3
2290	2026-03-23 19:17:45.288509-03	2026-03-23 19:17:45.28851-03	t	2026-04-01 15:03:39.725269-03	349	510	90.00	2054-09-30	f	\N		3	\N	190	3
2104	2026-03-23 19:17:45.282096-03	2026-03-23 19:17:45.282099-03	t	2026-04-01 15:03:39.725269-03	163	510	90.00	2039-03-30	f	\N		3	\N	190	3
1993	2026-03-23 19:17:45.278672-03	2026-03-23 19:17:45.278673-03	t	2026-04-01 15:03:39.725269-03	52	510	90.00	2029-12-30	f	\N		3	\N	190	3
2026	2026-03-23 19:17:45.279578-03	2026-03-23 19:17:45.27958-03	t	2026-04-01 15:03:39.725269-03	85	510	90.00	2032-09-30	f	\N		3	\N	190	3
2004	2026-03-23 19:17:45.27885-03	2026-03-23 19:17:45.278851-03	t	2026-04-01 15:03:39.725269-03	63	510	90.00	2030-11-30	f	\N		3	\N	190	3
2448	2026-03-23 19:17:45.293404-03	2026-03-23 19:17:45.293405-03	t	2026-04-01 15:03:39.725269-03	507	510	90.00	2067-11-30	f	\N		3	\N	190	3
2174	2026-03-23 19:17:45.284787-03	2026-03-23 19:17:45.28479-03	t	2026-04-01 15:03:39.725269-03	233	510	90.00	2045-01-30	f	\N		3	\N	190	3
2343	2026-03-23 19:17:45.289944-03	2026-03-23 19:17:45.289946-03	t	2026-04-01 15:03:39.725269-03	402	510	90.00	2059-03-02	f	\N		3	\N	190	3
2262	2026-03-23 19:17:45.287716-03	2026-03-23 19:17:45.287718-03	t	2026-04-01 15:03:39.725269-03	321	510	90.00	2052-05-30	f	\N		3	\N	190	3
2237	2026-03-23 19:17:45.286852-03	2026-03-23 19:17:45.286855-03	t	2026-04-01 15:03:39.725269-03	296	510	90.00	2050-04-30	f	\N		3	\N	190	3
2078	2026-03-23 19:17:45.281258-03	2026-03-23 19:17:45.28126-03	t	2026-04-01 15:03:39.725269-03	137	510	90.00	2037-01-30	f	\N		3	\N	190	3
2248	2026-03-23 19:17:45.287222-03	2026-03-23 19:17:45.287225-03	t	2026-04-01 15:03:39.725269-03	307	510	90.00	2051-03-30	f	\N		3	\N	190	3
2288	2026-03-23 19:17:45.288473-03	2026-03-23 19:17:45.288474-03	t	2026-04-01 15:03:39.725269-03	347	510	90.00	2054-07-30	f	\N		3	\N	190	3
2405	2026-03-23 19:17:45.292101-03	2026-03-23 19:17:45.292104-03	t	2026-04-01 15:03:39.725269-03	464	510	90.00	2064-04-30	f	\N		3	\N	190	3
2041	2026-03-23 19:17:45.280063-03	2026-03-23 19:17:45.280065-03	t	2026-04-01 15:03:39.725269-03	100	510	90.00	2033-12-30	f	\N		3	\N	190	3
2412	2026-03-23 19:17:45.292341-03	2026-03-23 19:17:45.292344-03	t	2026-04-01 15:03:39.725269-03	471	510	90.00	2064-11-30	f	\N		3	\N	190	3
2287	2026-03-23 19:17:45.288456-03	2026-03-23 19:17:45.288457-03	t	2026-04-01 15:03:39.725269-03	346	510	90.00	2054-06-30	f	\N		3	\N	190	3
2315	2026-03-23 19:17:45.28893-03	2026-03-23 19:17:45.288931-03	t	2026-04-01 15:03:39.725269-03	374	510	90.00	2056-10-30	f	\N		3	\N	190	3
2010	2026-03-23 19:17:45.278952-03	2026-03-23 19:17:45.278953-03	t	2026-04-01 15:03:39.725269-03	69	510	90.00	2031-05-30	f	\N		3	\N	190	3
2019	2026-03-23 19:17:45.279347-03	2026-03-23 19:17:45.27935-03	t	2026-04-01 15:03:39.725269-03	78	510	90.00	2032-03-01	f	\N		3	\N	190	3
2036	2026-03-23 19:17:45.279902-03	2026-03-23 19:17:45.279904-03	t	2026-04-01 15:03:39.725269-03	95	510	90.00	2033-07-30	f	\N		3	\N	190	3
2320	2026-03-23 19:17:45.289015-03	2026-03-23 19:17:45.289016-03	t	2026-04-01 15:03:39.725269-03	379	510	90.00	2057-03-30	f	\N		3	\N	190	3
2195	2026-03-23 19:17:45.285463-03	2026-03-23 19:17:45.285466-03	t	2026-04-01 15:03:39.725269-03	254	510	90.00	2046-10-30	f	\N		3	\N	190	3
2166	2026-03-23 19:17:45.284338-03	2026-03-23 19:17:45.284429-03	t	2026-04-01 15:03:39.725269-03	225	510	90.00	2044-05-30	f	\N		3	\N	190	3
2027	2026-03-23 19:17:45.279611-03	2026-03-23 19:17:45.279614-03	t	2026-04-01 15:03:39.725269-03	86	510	90.00	2032-10-30	f	\N		3	\N	190	3
2421	2026-03-23 19:17:45.292651-03	2026-03-23 19:17:45.292654-03	t	2026-04-01 15:03:39.725269-03	480	510	90.00	2065-08-30	f	\N		3	\N	190	3
1949	2026-03-23 19:17:45.277935-03	2026-03-23 19:17:45.277936-03	t	2026-04-01 15:03:39.725269-03	8	510	90.00	2026-04-30	f	\N		3	\N	190	3
2188	2026-03-23 19:17:45.285239-03	2026-03-23 19:17:45.285241-03	t	2026-04-01 15:03:39.725269-03	247	510	90.00	2046-03-30	f	\N		3	\N	190	3
2236	2026-03-23 19:17:45.286818-03	2026-03-23 19:17:45.286821-03	t	2026-04-01 15:03:39.725269-03	295	510	90.00	2050-03-30	f	\N		3	\N	190	3
2154	2026-03-23 19:17:45.283986-03	2026-03-23 19:17:45.283989-03	t	2026-04-01 15:03:39.725269-03	213	510	90.00	2043-05-30	f	\N		3	\N	190	3
2088	2026-03-23 19:17:45.281577-03	2026-03-23 19:17:45.28158-03	t	2026-04-01 15:03:39.725269-03	147	510	90.00	2037-11-30	f	\N		3	\N	190	3
2081	2026-03-23 19:17:45.281354-03	2026-03-23 19:17:45.281357-03	t	2026-04-01 15:03:39.725269-03	140	510	90.00	2037-04-30	f	\N		3	\N	190	3
2295	2026-03-23 19:17:45.288597-03	2026-03-23 19:17:45.288598-03	t	2026-04-01 15:03:39.725269-03	354	510	90.00	2055-03-02	f	\N		3	\N	190	3
1998	2026-03-23 19:17:45.278754-03	2026-03-23 19:17:45.278755-03	t	2026-04-01 15:03:39.725269-03	57	510	90.00	2030-05-30	f	\N		3	\N	190	3
2007	2026-03-23 19:17:45.278902-03	2026-03-23 19:17:45.278903-03	t	2026-04-01 15:03:39.725269-03	66	510	90.00	2031-03-02	f	\N		3	\N	190	3
2199	2026-03-23 19:17:45.285595-03	2026-03-23 19:17:45.285597-03	t	2026-04-01 15:03:39.725269-03	258	510	90.00	2047-03-02	f	\N		3	\N	190	3
2239	2026-03-23 19:17:45.28692-03	2026-03-23 19:17:45.286923-03	t	2026-04-01 15:03:39.725269-03	298	510	90.00	2050-06-30	f	\N		3	\N	190	3
2323	2026-03-23 19:17:45.289065-03	2026-03-23 19:17:45.289067-03	t	2026-04-01 15:03:39.725269-03	382	510	90.00	2057-06-30	f	\N		3	\N	190	3
2107	2026-03-23 19:17:45.282197-03	2026-03-23 19:17:45.2822-03	t	2026-04-01 15:03:39.725269-03	166	510	90.00	2039-06-30	f	\N		3	\N	190	3
2354	2026-03-23 19:17:45.290316-03	2026-03-23 19:17:45.290319-03	t	2026-04-01 15:03:39.725269-03	413	510	90.00	2060-01-30	f	\N		3	\N	190	3
2257	2026-03-23 19:17:45.28754-03	2026-03-23 19:17:45.287542-03	t	2026-04-01 15:03:39.725269-03	316	510	90.00	2051-12-30	f	\N		3	\N	190	3
2209	2026-03-23 19:17:45.285911-03	2026-03-23 19:17:45.285914-03	t	2026-04-01 15:03:39.725269-03	268	510	90.00	2047-12-30	f	\N		3	\N	190	3
2175	2026-03-23 19:17:45.284825-03	2026-03-23 19:17:45.284827-03	t	2026-04-01 15:03:39.725269-03	234	510	90.00	2045-03-02	f	\N		3	\N	190	3
2384	2026-03-23 19:17:45.291381-03	2026-03-23 19:17:45.291384-03	t	2026-04-01 15:03:39.725269-03	443	510	90.00	2062-07-30	f	\N		3	\N	190	3
1999	2026-03-23 19:17:45.27877-03	2026-03-23 19:17:45.278771-03	t	2026-04-01 15:03:39.725269-03	58	510	90.00	2030-06-30	f	\N		3	\N	190	3
2177	2026-03-23 19:17:45.28489-03	2026-03-23 19:17:45.284892-03	t	2026-04-01 15:03:39.725269-03	236	510	90.00	2045-04-30	f	\N		3	\N	190	3
1957	2026-03-23 19:17:45.278076-03	2026-03-23 19:17:45.278078-03	t	2026-04-01 15:03:39.725269-03	16	510	90.00	2026-12-30	f	\N		3	\N	190	3
2260	2026-03-23 19:17:45.287648-03	2026-03-23 19:17:45.287651-03	t	2026-04-01 15:03:39.725269-03	319	510	90.00	2052-03-30	f	\N		3	\N	190	3
2387	2026-03-23 19:17:45.291483-03	2026-03-23 19:17:45.291486-03	t	2026-04-01 15:03:39.725269-03	446	510	90.00	2062-10-30	f	\N		3	\N	190	3
2102	2026-03-23 19:17:45.282032-03	2026-03-23 19:17:45.282035-03	t	2026-04-01 15:03:39.725269-03	161	510	90.00	2039-01-30	f	\N		3	\N	190	3
2373	2026-03-23 19:17:45.291-03	2026-03-23 19:17:45.291004-03	t	2026-04-01 15:03:39.725269-03	432	510	90.00	2061-08-30	f	\N		3	\N	190	3
2377	2026-03-23 19:17:45.291143-03	2026-03-23 19:17:45.291146-03	t	2026-04-01 15:03:39.725269-03	436	510	90.00	2061-12-30	f	\N		3	\N	190	3
2555	2026-04-01 14:02:45.06982-03	2026-04-01 14:02:45.069824-03	f	\N	5	7	114.28	2026-02-01	t	2026-02-01		\N	\N	304	\N
2568	2026-04-01 14:03:33.598944-03	2026-04-01 14:03:33.598947-03	f	\N	11	12	63.33	2026-11-01	f	\N		\N	\N	305	\N
2580	2026-04-01 14:10:37.610246-03	2026-04-01 14:10:37.610248-03	f	\N	5	10	125.00	2026-06-01	f	\N		\N	\N	307	\N
1728	2026-03-22 22:49:56.219905-03	2026-04-01 14:40:28.148747-03	f	\N	16	24	629.35	2026-03-11	t	2026-03-11		\N	\N	257	\N
2277	2026-03-23 19:17:45.288282-03	2026-03-23 19:17:45.288283-03	t	2026-04-01 15:03:39.725269-03	336	510	90.00	2053-08-30	f	\N		3	\N	190	3
2402	2026-03-23 19:17:45.291999-03	2026-03-23 19:17:45.292002-03	t	2026-04-01 15:03:39.725269-03	461	510	90.00	2064-01-30	f	\N		3	\N	190	3
2192	2026-03-23 19:17:45.285366-03	2026-03-23 19:17:45.285368-03	t	2026-04-01 15:03:39.725269-03	251	510	90.00	2046-07-30	f	\N		3	\N	190	3
2249	2026-03-23 19:17:45.287256-03	2026-03-23 19:17:45.287259-03	t	2026-04-01 15:03:39.725269-03	308	510	90.00	2051-04-30	f	\N		3	\N	190	3
2269	2026-03-23 19:17:45.287949-03	2026-03-23 19:17:45.287951-03	t	2026-04-01 15:03:39.725269-03	328	510	90.00	2052-12-30	f	\N		3	\N	190	3
2076	2026-03-23 19:17:45.281194-03	2026-03-23 19:17:45.281196-03	t	2026-04-01 15:03:39.725269-03	135	510	90.00	2036-11-30	f	\N		3	\N	190	3
2356	2026-03-23 19:17:45.290384-03	2026-03-23 19:17:45.290386-03	t	2026-04-01 15:03:39.725269-03	415	510	90.00	2060-03-30	f	\N		3	\N	190	3
2346	2026-03-23 19:17:45.290044-03	2026-03-23 19:17:45.290047-03	t	2026-04-01 15:03:39.725269-03	405	510	90.00	2059-05-30	f	\N		3	\N	190	3
2308	2026-03-23 19:17:45.288814-03	2026-03-23 19:17:45.288815-03	t	2026-04-01 15:03:39.725269-03	367	510	90.00	2056-03-30	f	\N		3	\N	190	3
1958	2026-03-23 19:17:45.278093-03	2026-03-23 19:17:45.278094-03	t	2026-04-01 15:03:39.725269-03	17	510	90.00	2027-01-30	f	\N		3	\N	190	3
1973	2026-03-23 19:17:45.278345-03	2026-03-23 19:17:45.278346-03	t	2026-04-01 15:03:39.725269-03	32	510	90.00	2028-04-30	f	\N		3	\N	190	3
2013	2026-03-23 19:17:45.279001-03	2026-03-23 19:17:45.279002-03	t	2026-04-01 15:03:39.725269-03	72	510	90.00	2031-08-30	f	\N		3	\N	190	3
2003	2026-03-23 19:17:45.278834-03	2026-03-23 19:17:45.278835-03	t	2026-04-01 15:03:39.725269-03	62	510	90.00	2030-10-30	f	\N		3	\N	190	3
2097	2026-03-23 19:17:45.281868-03	2026-03-23 19:17:45.28187-03	t	2026-04-01 15:03:39.725269-03	156	510	90.00	2038-08-30	f	\N		3	\N	190	3
2435	2026-03-23 19:17:45.293176-03	2026-03-23 19:17:45.293177-03	t	2026-04-01 15:03:39.725269-03	494	510	90.00	2066-10-30	f	\N		3	\N	190	3
2422	2026-03-23 19:17:45.292686-03	2026-03-23 19:17:45.292689-03	t	2026-04-01 15:03:39.725269-03	481	510	90.00	2065-09-30	f	\N		3	\N	190	3
2408	2026-03-23 19:17:45.292205-03	2026-03-23 19:17:45.292207-03	t	2026-04-01 15:03:39.725269-03	467	510	90.00	2064-07-30	f	\N		3	\N	190	3
1953	2026-03-23 19:17:45.278006-03	2026-03-23 19:17:45.278007-03	t	2026-04-01 15:03:39.725269-03	12	510	90.00	2026-08-30	f	\N		3	\N	190	3
2141	2026-03-23 19:17:45.283562-03	2026-03-23 19:17:45.283565-03	t	2026-04-01 15:03:39.725269-03	200	510	90.00	2042-04-30	f	\N		3	\N	190	3
1997	2026-03-23 19:17:45.278738-03	2026-03-23 19:17:45.278739-03	t	2026-04-01 15:03:39.725269-03	56	510	90.00	2030-04-30	f	\N		3	\N	190	3
2382	2026-03-23 19:17:45.291313-03	2026-03-23 19:17:45.291316-03	t	2026-04-01 15:03:39.725269-03	441	510	90.00	2062-05-30	f	\N		3	\N	190	3
2113	2026-03-23 19:17:45.282584-03	2026-03-23 19:17:45.282586-03	t	2026-04-01 15:03:39.725269-03	172	510	90.00	2039-12-30	f	\N		3	\N	190	3
2371	2026-03-23 19:17:45.290893-03	2026-03-23 19:17:45.290896-03	t	2026-04-01 15:03:39.725269-03	430	510	90.00	2061-06-30	f	\N		3	\N	190	3
2247	2026-03-23 19:17:45.287189-03	2026-03-23 19:17:45.287192-03	t	2026-04-01 15:03:39.725269-03	306	510	90.00	2051-03-02	f	\N		3	\N	190	3
2016	2026-03-23 19:17:45.279187-03	2026-03-23 19:17:45.279193-03	t	2026-04-01 15:03:39.725269-03	75	510	90.00	2031-11-30	f	\N		3	\N	190	3
2258	2026-03-23 19:17:45.287575-03	2026-03-23 19:17:45.287577-03	t	2026-04-01 15:03:39.725269-03	317	510	90.00	2052-01-30	f	\N		3	\N	190	3
2450	2026-03-23 19:17:45.29344-03	2026-03-23 19:17:45.293441-03	t	2026-04-01 15:03:39.725269-03	509	510	90.00	2068-01-30	f	\N		3	\N	190	3
2349	2026-03-23 19:17:45.290146-03	2026-03-23 19:17:45.290149-03	t	2026-04-01 15:03:39.725269-03	408	510	90.00	2059-08-30	f	\N		3	\N	190	3
2268	2026-03-23 19:17:45.287917-03	2026-03-23 19:17:45.287919-03	t	2026-04-01 15:03:39.725269-03	327	510	90.00	2052-11-30	f	\N		3	\N	190	3
2289	2026-03-23 19:17:45.288491-03	2026-03-23 19:17:45.288492-03	t	2026-04-01 15:03:39.725269-03	348	510	90.00	2054-08-30	f	\N		3	\N	190	3
2138	2026-03-23 19:17:45.283465-03	2026-03-23 19:17:45.283467-03	t	2026-04-01 15:03:39.725269-03	197	510	90.00	2042-01-30	f	\N		3	\N	190	3
2212	2026-03-23 19:17:45.28601-03	2026-03-23 19:17:45.286012-03	t	2026-04-01 15:03:39.725269-03	271	510	90.00	2048-03-30	f	\N		3	\N	190	3
2472	2026-03-23 19:18:06.218577-03	2026-03-23 19:18:06.21858-03	t	2026-04-01 15:03:39.725269-03	9	10	106.00	2026-06-30	f	\N		3	\N	192	3
2197	2026-03-23 19:17:45.285529-03	2026-03-23 19:17:45.285531-03	t	2026-04-01 15:03:39.725269-03	256	510	90.00	2046-12-30	f	\N		3	\N	190	3
2337	2026-03-23 19:17:45.289737-03	2026-03-23 19:17:45.28974-03	t	2026-04-01 15:03:39.725269-03	396	510	90.00	2058-08-30	f	\N		3	\N	190	3
2000	2026-03-23 19:17:45.278786-03	2026-03-23 19:17:45.278787-03	t	2026-04-01 15:03:39.725269-03	59	510	90.00	2030-07-30	f	\N		3	\N	190	3
2473	2026-03-23 19:18:06.218613-03	2026-03-23 19:18:06.218615-03	t	2026-04-01 15:03:39.725269-03	10	10	106.00	2026-07-30	f	\N		3	\N	192	3
2067	2026-03-23 19:17:45.280905-03	2026-03-23 19:17:45.280907-03	t	2026-04-01 15:03:39.725269-03	126	510	90.00	2036-03-01	f	\N		3	\N	190	3
2203	2026-03-23 19:17:45.285722-03	2026-03-23 19:17:45.285724-03	t	2026-04-01 15:03:39.725269-03	262	510	90.00	2047-06-30	f	\N		3	\N	190	3
2336	2026-03-23 19:17:45.289704-03	2026-03-23 19:17:45.289706-03	t	2026-04-01 15:03:39.725269-03	395	510	90.00	2058-07-30	f	\N		3	\N	190	3
2432	2026-03-23 19:17:45.293122-03	2026-03-23 19:17:45.293123-03	t	2026-04-01 15:03:39.725269-03	491	510	90.00	2066-07-30	f	\N		3	\N	190	3
2442	2026-03-23 19:17:45.293299-03	2026-03-23 19:17:45.293301-03	t	2026-04-01 15:03:39.725269-03	501	510	90.00	2067-05-30	f	\N		3	\N	190	3
2278	2026-03-23 19:17:45.288301-03	2026-03-23 19:17:45.288302-03	t	2026-04-01 15:03:39.725269-03	337	510	90.00	2053-09-30	f	\N		3	\N	190	3
2056	2026-03-23 19:17:45.280545-03	2026-03-23 19:17:45.280547-03	t	2026-04-01 15:03:39.725269-03	115	510	90.00	2035-03-30	f	\N		3	\N	190	3
1960	2026-03-23 19:17:45.278127-03	2026-03-23 19:17:45.278128-03	t	2026-04-01 15:03:39.725269-03	19	510	90.00	2027-03-30	f	\N		3	\N	190	3
2117	2026-03-23 19:17:45.282744-03	2026-03-23 19:17:45.282747-03	t	2026-04-01 15:03:39.725269-03	176	510	90.00	2040-04-30	f	\N		3	\N	190	3
1981	2026-03-23 19:17:45.278476-03	2026-03-23 19:17:45.278478-03	t	2026-04-01 15:03:39.725269-03	40	510	90.00	2028-12-30	f	\N		3	\N	190	3
2144	2026-03-23 19:17:45.283662-03	2026-03-23 19:17:45.283664-03	t	2026-04-01 15:03:39.725269-03	203	510	90.00	2042-07-30	f	\N		3	\N	190	3
2280	2026-03-23 19:17:45.288335-03	2026-03-23 19:17:45.288336-03	t	2026-04-01 15:03:39.725269-03	339	510	90.00	2053-11-30	f	\N		3	\N	190	3
2409	2026-03-23 19:17:45.292239-03	2026-03-23 19:17:45.292241-03	t	2026-04-01 15:03:39.725269-03	468	510	90.00	2064-08-30	f	\N		3	\N	190	3
2316	2026-03-23 19:17:45.288946-03	2026-03-23 19:17:45.288947-03	t	2026-04-01 15:03:39.725269-03	375	510	90.00	2056-11-30	f	\N		3	\N	190	3
2020	2026-03-23 19:17:45.279382-03	2026-03-23 19:17:45.279384-03	t	2026-04-01 15:03:39.725269-03	79	510	90.00	2032-03-30	f	\N		3	\N	190	3
1962	2026-03-23 19:17:45.278162-03	2026-03-23 19:17:45.278163-03	t	2026-04-01 15:03:39.725269-03	21	510	90.00	2027-05-30	f	\N		3	\N	190	3
2208	2026-03-23 19:17:45.285879-03	2026-03-23 19:17:45.285882-03	t	2026-04-01 15:03:39.725269-03	267	510	90.00	2047-11-30	f	\N		3	\N	190	3
2358	2026-03-23 19:17:45.29045-03	2026-03-23 19:17:45.290453-03	t	2026-04-01 15:03:39.725269-03	417	510	90.00	2060-05-30	f	\N		3	\N	190	3
2242	2026-03-23 19:17:45.287022-03	2026-03-23 19:17:45.287024-03	t	2026-04-01 15:03:39.725269-03	301	510	90.00	2050-09-30	f	\N		3	\N	190	3
2024	2026-03-23 19:17:45.279512-03	2026-03-23 19:17:45.279515-03	t	2026-04-01 15:03:39.725269-03	83	510	90.00	2032-07-30	f	\N		3	\N	190	3
2142	2026-03-23 19:17:45.283595-03	2026-03-23 19:17:45.283597-03	t	2026-04-01 15:03:39.725269-03	201	510	90.00	2042-05-30	f	\N		3	\N	190	3
2132	2026-03-23 19:17:45.283269-03	2026-03-23 19:17:45.283272-03	t	2026-04-01 15:03:39.725269-03	191	510	90.00	2041-07-30	f	\N		3	\N	190	3
2293	2026-03-23 19:17:45.288559-03	2026-03-23 19:17:45.28856-03	t	2026-04-01 15:03:39.725269-03	352	510	90.00	2054-12-30	f	\N		3	\N	190	3
2187	2026-03-23 19:17:45.285207-03	2026-03-23 19:17:45.285209-03	t	2026-04-01 15:03:39.725269-03	246	510	90.00	2046-03-02	f	\N		3	\N	190	3
2282	2026-03-23 19:17:45.288371-03	2026-03-23 19:17:45.288372-03	t	2026-04-01 15:03:39.725269-03	341	510	90.00	2054-01-30	f	\N		3	\N	190	3
2556	2026-04-01 14:02:45.116315-03	2026-04-01 14:02:45.116318-03	f	\N	6	7	114.28	2026-03-04	t	2026-03-04		\N	\N	304	\N
2569	2026-04-01 14:03:33.641166-03	2026-04-01 14:03:33.641169-03	f	\N	12	12	63.33	2026-12-02	f	\N		\N	\N	305	\N
2581	2026-04-01 14:10:37.645176-03	2026-04-01 14:10:37.645179-03	f	\N	6	10	125.00	2026-07-02	f	\N		\N	\N	307	\N
1738	2026-03-22 22:49:56.224702-03	2026-03-22 22:49:56.224704-03	t	2026-04-01 15:03:29.308341-03	2	60	850.00	2026-05-04	f	\N		\N	\N	258	\N
1739	2026-03-22 22:49:56.225094-03	2026-03-22 22:49:56.225096-03	t	2026-04-01 15:03:29.308341-03	3	60	850.00	2026-06-04	f	\N		\N	\N	258	\N
1740	2026-03-22 22:49:56.225804-03	2026-03-22 22:49:56.225806-03	t	2026-04-01 15:03:29.308341-03	4	60	850.00	2026-07-04	f	\N		\N	\N	258	\N
1741	2026-03-22 22:49:56.226452-03	2026-03-22 22:49:56.226454-03	t	2026-04-01 15:03:29.308341-03	5	60	850.00	2026-08-04	f	\N		\N	\N	258	\N
1742	2026-03-22 22:49:56.226887-03	2026-03-22 22:49:56.226889-03	t	2026-04-01 15:03:29.308341-03	6	60	850.00	2026-09-04	f	\N		\N	\N	258	\N
1743	2026-03-22 22:49:56.227358-03	2026-03-22 22:49:56.22736-03	t	2026-04-01 15:03:29.308341-03	7	60	850.00	2026-10-04	f	\N		\N	\N	258	\N
1744	2026-03-22 22:49:56.227795-03	2026-03-22 22:49:56.227797-03	t	2026-04-01 15:03:29.308341-03	8	60	850.00	2026-11-04	f	\N		\N	\N	258	\N
1745	2026-03-22 22:49:56.22822-03	2026-03-22 22:49:56.228222-03	t	2026-04-01 15:03:29.308341-03	9	60	850.00	2026-12-04	f	\N		\N	\N	258	\N
1746	2026-03-22 22:49:56.22866-03	2026-03-22 22:49:56.228662-03	t	2026-04-01 15:03:29.308341-03	10	60	850.00	2027-01-04	f	\N		\N	\N	258	\N
1747	2026-03-22 22:49:56.229103-03	2026-03-22 22:49:56.229104-03	t	2026-04-01 15:03:29.308341-03	11	60	850.00	2027-02-04	f	\N		\N	\N	258	\N
1748	2026-03-22 22:49:56.229516-03	2026-03-22 22:49:56.229518-03	t	2026-04-01 15:03:29.308341-03	12	60	850.00	2027-03-04	f	\N		\N	\N	258	\N
1749	2026-03-22 22:49:56.229916-03	2026-03-22 22:49:56.229918-03	t	2026-04-01 15:03:29.308341-03	13	60	850.00	2027-04-04	f	\N		\N	\N	258	\N
1750	2026-03-22 22:49:56.230328-03	2026-03-22 22:49:56.230329-03	t	2026-04-01 15:03:29.308341-03	14	60	850.00	2027-05-04	f	\N		\N	\N	258	\N
1751	2026-03-22 22:49:56.230844-03	2026-03-22 22:49:56.230846-03	t	2026-04-01 15:03:29.308341-03	15	60	850.00	2027-06-04	f	\N		\N	\N	258	\N
1752	2026-03-22 22:49:56.231273-03	2026-03-22 22:49:56.231275-03	t	2026-04-01 15:03:29.308341-03	16	60	850.00	2027-07-04	f	\N		\N	\N	258	\N
1753	2026-03-22 22:49:56.231629-03	2026-03-22 22:49:56.231631-03	t	2026-04-01 15:03:29.308341-03	17	60	850.00	2027-08-04	f	\N		\N	\N	258	\N
1754	2026-03-22 22:49:56.231986-03	2026-03-22 22:49:56.231988-03	t	2026-04-01 15:03:29.308341-03	18	60	850.00	2027-09-04	f	\N		\N	\N	258	\N
1755	2026-03-22 22:49:56.232349-03	2026-03-22 22:49:56.232351-03	t	2026-04-01 15:03:29.308341-03	19	60	850.00	2027-10-04	f	\N		\N	\N	258	\N
1756	2026-03-22 22:49:56.232667-03	2026-03-22 22:49:56.232669-03	t	2026-04-01 15:03:29.308341-03	20	60	850.00	2027-11-04	f	\N		\N	\N	258	\N
1757	2026-03-22 22:49:56.232967-03	2026-03-22 22:49:56.232968-03	t	2026-04-01 15:03:29.308341-03	21	60	850.00	2027-12-04	f	\N		\N	\N	258	\N
1758	2026-03-22 22:49:56.233274-03	2026-03-22 22:49:56.233275-03	t	2026-04-01 15:03:29.308341-03	22	60	850.00	2028-01-04	f	\N		\N	\N	258	\N
1759	2026-03-22 22:49:56.233564-03	2026-03-22 22:49:56.233565-03	t	2026-04-01 15:03:29.308341-03	23	60	850.00	2028-02-04	f	\N		\N	\N	258	\N
1760	2026-03-22 22:49:56.233901-03	2026-03-22 22:49:56.233902-03	t	2026-04-01 15:03:29.308341-03	24	60	850.00	2028-03-04	f	\N		\N	\N	258	\N
1761	2026-03-22 22:49:56.234199-03	2026-03-22 22:49:56.234201-03	t	2026-04-01 15:03:29.308341-03	25	60	850.00	2028-04-04	f	\N		\N	\N	258	\N
1762	2026-03-22 22:49:56.234507-03	2026-03-22 22:49:56.234508-03	t	2026-04-01 15:03:29.308341-03	26	60	850.00	2028-05-04	f	\N		\N	\N	258	\N
1763	2026-03-22 22:49:56.234812-03	2026-03-22 22:49:56.234814-03	t	2026-04-01 15:03:29.308341-03	27	60	850.00	2028-06-04	f	\N		\N	\N	258	\N
1764	2026-03-22 22:49:56.235111-03	2026-03-22 22:49:56.235113-03	t	2026-04-01 15:03:29.308341-03	28	60	850.00	2028-07-04	f	\N		\N	\N	258	\N
1765	2026-03-22 22:49:56.236008-03	2026-03-22 22:49:56.23601-03	t	2026-04-01 15:03:29.308341-03	29	60	850.00	2028-08-04	f	\N		\N	\N	258	\N
1766	2026-03-22 22:49:56.236531-03	2026-03-22 22:49:56.236533-03	t	2026-04-01 15:03:29.308341-03	30	60	850.00	2028-09-04	f	\N		\N	\N	258	\N
1767	2026-03-22 22:49:56.236986-03	2026-03-22 22:49:56.236988-03	t	2026-04-01 15:03:29.308341-03	31	60	850.00	2028-10-04	f	\N		\N	\N	258	\N
1768	2026-03-22 22:49:56.237383-03	2026-03-22 22:49:56.237385-03	t	2026-04-01 15:03:29.308341-03	32	60	850.00	2028-11-04	f	\N		\N	\N	258	\N
1769	2026-03-22 22:49:56.237748-03	2026-03-22 22:49:56.23775-03	t	2026-04-01 15:03:29.308341-03	33	60	850.00	2028-12-04	f	\N		\N	\N	258	\N
1770	2026-03-22 22:49:56.238291-03	2026-03-22 22:49:56.238292-03	t	2026-04-01 15:03:29.308341-03	34	60	850.00	2029-01-04	f	\N		\N	\N	258	\N
1771	2026-03-22 22:49:56.23875-03	2026-03-22 22:49:56.238752-03	t	2026-04-01 15:03:29.308341-03	35	60	850.00	2029-02-04	f	\N		\N	\N	258	\N
1772	2026-03-22 22:49:56.239295-03	2026-03-22 22:49:56.239297-03	t	2026-04-01 15:03:29.308341-03	36	60	850.00	2029-03-04	f	\N		\N	\N	258	\N
1773	2026-03-22 22:49:56.239817-03	2026-03-22 22:49:56.23982-03	t	2026-04-01 15:03:29.308341-03	37	60	850.00	2029-04-04	f	\N		\N	\N	258	\N
1774	2026-03-22 22:49:56.240201-03	2026-03-22 22:49:56.240203-03	t	2026-04-01 15:03:29.308341-03	38	60	850.00	2029-05-04	f	\N		\N	\N	258	\N
1775	2026-03-22 22:49:56.240668-03	2026-03-22 22:49:56.240669-03	t	2026-04-01 15:03:29.308341-03	39	60	850.00	2029-06-04	f	\N		\N	\N	258	\N
1776	2026-03-22 22:49:56.241123-03	2026-03-22 22:49:56.241125-03	t	2026-04-01 15:03:29.308341-03	40	60	850.00	2029-07-04	f	\N		\N	\N	258	\N
1777	2026-03-22 22:49:56.24158-03	2026-03-22 22:49:56.241582-03	t	2026-04-01 15:03:29.308341-03	41	60	850.00	2029-08-04	f	\N		\N	\N	258	\N
1778	2026-03-22 22:49:56.24202-03	2026-03-22 22:49:56.242022-03	t	2026-04-01 15:03:29.308341-03	42	60	850.00	2029-09-04	f	\N		\N	\N	258	\N
1779	2026-03-22 22:49:56.242414-03	2026-03-22 22:49:56.242416-03	t	2026-04-01 15:03:29.308341-03	43	60	850.00	2029-10-04	f	\N		\N	\N	258	\N
1780	2026-03-22 22:49:56.242856-03	2026-03-22 22:49:56.242858-03	t	2026-04-01 15:03:29.308341-03	44	60	850.00	2029-11-04	f	\N		\N	\N	258	\N
1781	2026-03-22 22:49:56.243489-03	2026-03-22 22:49:56.243491-03	t	2026-04-01 15:03:29.308341-03	45	60	850.00	2029-12-04	f	\N		\N	\N	258	\N
1782	2026-03-22 22:49:56.243929-03	2026-03-22 22:49:56.243931-03	t	2026-04-01 15:03:29.308341-03	46	60	850.00	2030-01-04	f	\N		\N	\N	258	\N
1783	2026-03-22 22:49:56.244348-03	2026-03-22 22:49:56.24435-03	t	2026-04-01 15:03:29.308341-03	47	60	850.00	2030-02-04	f	\N		\N	\N	258	\N
1784	2026-03-22 22:49:56.244781-03	2026-03-22 22:49:56.244783-03	t	2026-04-01 15:03:29.308341-03	48	60	850.00	2030-03-04	f	\N		\N	\N	258	\N
1785	2026-03-22 22:49:56.245224-03	2026-03-22 22:49:56.245225-03	t	2026-04-01 15:03:29.308341-03	49	60	850.00	2030-04-04	f	\N		\N	\N	258	\N
1786	2026-03-22 22:49:56.24564-03	2026-03-22 22:49:56.245642-03	t	2026-04-01 15:03:29.308341-03	50	60	850.00	2030-05-04	f	\N		\N	\N	258	\N
1787	2026-03-22 22:49:56.246009-03	2026-03-22 22:49:56.246011-03	t	2026-04-01 15:03:29.308341-03	51	60	850.00	2030-06-04	f	\N		\N	\N	258	\N
1788	2026-03-22 22:49:56.246385-03	2026-03-22 22:49:56.246386-03	t	2026-04-01 15:03:29.308341-03	52	60	850.00	2030-07-04	f	\N		\N	\N	258	\N
1789	2026-03-22 22:49:56.246715-03	2026-03-22 22:49:56.246717-03	t	2026-04-01 15:03:29.308341-03	53	60	850.00	2030-08-04	f	\N		\N	\N	258	\N
1790	2026-03-22 22:49:56.247104-03	2026-03-22 22:49:56.247106-03	t	2026-04-01 15:03:29.308341-03	54	60	850.00	2030-09-04	f	\N		\N	\N	258	\N
1791	2026-03-22 22:49:56.247492-03	2026-03-22 22:49:56.247494-03	t	2026-04-01 15:03:29.308341-03	55	60	850.00	2030-10-04	f	\N		\N	\N	258	\N
1792	2026-03-22 22:49:56.24785-03	2026-03-22 22:49:56.247852-03	t	2026-04-01 15:03:29.308341-03	56	60	850.00	2030-11-04	f	\N		\N	\N	258	\N
1793	2026-03-22 22:49:56.248165-03	2026-03-22 22:49:56.248167-03	t	2026-04-01 15:03:29.308341-03	57	60	850.00	2030-12-04	f	\N		\N	\N	258	\N
1794	2026-03-22 22:49:56.248504-03	2026-03-22 22:49:56.248506-03	t	2026-04-01 15:03:29.308341-03	58	60	850.00	2031-01-04	f	\N		\N	\N	258	\N
1795	2026-03-22 22:49:56.248943-03	2026-03-22 22:49:56.248945-03	t	2026-04-01 15:03:29.308341-03	59	60	850.00	2031-02-04	f	\N		\N	\N	258	\N
1796	2026-03-22 22:49:56.249355-03	2026-03-22 22:49:56.249357-03	t	2026-04-01 15:03:29.308341-03	60	60	850.00	2031-03-04	f	\N		\N	\N	258	\N
2466	2026-03-23 19:18:06.218347-03	2026-03-23 19:18:06.21835-03	t	2026-04-01 15:03:39.725269-03	3	10	106.00	2025-12-30	t	2025-12-30		3	\N	192	3
2465	2026-03-23 19:18:06.218301-03	2026-03-23 19:18:06.218304-03	t	2026-04-01 15:03:39.725269-03	2	10	106.00	2025-11-30	t	2025-11-30		3	\N	192	3
2464	2026-03-23 19:18:06.218216-03	2026-03-23 19:18:06.218223-03	t	2026-04-01 15:03:39.725269-03	1	10	106.00	2025-10-30	t	2025-10-30		3	\N	192	3
1943	2026-03-23 19:17:45.277812-03	2026-03-23 19:17:45.277814-03	t	2026-04-01 15:03:39.725269-03	2	510	90.00	2025-10-30	t	2025-10-30		3	\N	190	3
2205	2026-03-23 19:17:45.285785-03	2026-03-23 19:17:45.285787-03	t	2026-04-01 15:03:39.725269-03	264	510	90.00	2047-08-30	f	\N		3	\N	190	3
2286	2026-03-23 19:17:45.288438-03	2026-03-23 19:17:45.28844-03	t	2026-04-01 15:03:39.725269-03	345	510	90.00	2054-05-30	f	\N		3	\N	190	3
2437	2026-03-23 19:17:45.293212-03	2026-03-23 19:17:45.293213-03	t	2026-04-01 15:03:39.725269-03	496	510	90.00	2066-12-30	f	\N		3	\N	190	3
2139	2026-03-23 19:17:45.283497-03	2026-03-23 19:17:45.2835-03	t	2026-04-01 15:03:39.725269-03	198	510	90.00	2042-03-02	f	\N		3	\N	190	3
479	2026-03-22 22:49:55.609566-03	2026-03-22 22:49:55.609568-03	f	\N	1	5	57.73	2026-04-30	f	\N		\N	\N	186	\N
480	2026-03-22 22:49:55.610106-03	2026-03-22 22:49:55.610108-03	f	\N	2	5	57.73	2026-05-30	f	\N		\N	\N	186	\N
481	2026-03-22 22:49:55.610531-03	2026-03-22 22:49:55.610533-03	f	\N	3	5	57.73	2026-06-30	f	\N		\N	\N	186	\N
482	2026-03-22 22:49:55.610896-03	2026-03-22 22:49:55.610898-03	f	\N	4	5	57.73	2026-07-30	f	\N		\N	\N	186	\N
483	2026-03-22 22:49:55.611239-03	2026-03-22 22:49:55.611241-03	f	\N	5	5	57.73	2026-08-30	f	\N		\N	\N	186	\N
484	2026-03-22 22:49:55.612071-03	2026-03-22 22:49:55.612072-03	f	\N	1	15	294.00	2025-04-30	t	2025-04-30		\N	\N	187	\N
485	2026-03-22 22:49:55.612443-03	2026-03-22 22:49:55.612445-03	f	\N	2	15	294.00	2025-05-30	t	2025-05-30		\N	\N	187	\N
486	2026-03-22 22:49:55.612807-03	2026-03-22 22:49:55.612809-03	f	\N	3	15	294.00	2025-06-30	t	2025-06-30		\N	\N	187	\N
487	2026-03-22 22:49:55.613171-03	2026-03-22 22:49:55.613172-03	f	\N	4	15	294.00	2025-07-30	t	2025-07-30		\N	\N	187	\N
488	2026-03-22 22:49:55.61378-03	2026-03-22 22:49:55.613782-03	f	\N	5	15	294.00	2025-08-30	t	2025-08-30		\N	\N	187	\N
489	2026-03-22 22:49:55.614248-03	2026-03-22 22:49:55.61425-03	f	\N	6	15	294.00	2025-09-30	t	2025-09-30		\N	\N	187	\N
490	2026-03-22 22:49:55.614649-03	2026-03-22 22:49:55.614651-03	f	\N	7	15	294.00	2025-10-30	t	2025-10-30		\N	\N	187	\N
491	2026-03-22 22:49:55.615145-03	2026-03-22 22:49:55.615147-03	f	\N	8	15	294.00	2025-11-30	t	2025-11-30		\N	\N	187	\N
492	2026-03-22 22:49:55.615641-03	2026-03-22 22:49:55.615643-03	f	\N	9	15	294.00	2025-12-30	t	2025-12-30		\N	\N	187	\N
493	2026-03-22 22:49:55.616125-03	2026-03-22 22:49:55.616126-03	f	\N	10	15	294.00	2026-01-30	t	2026-01-30		\N	\N	187	\N
494	2026-03-22 22:49:55.616681-03	2026-03-22 22:49:55.616683-03	f	\N	11	15	294.00	2026-02-28	t	2026-02-28		\N	\N	187	\N
2485	2026-03-23 19:19:17.473464-03	2026-03-23 19:19:17.473472-03	f	\N	12	12	337.00	2026-08-23	f	\N		\N	\N	292	\N
2530	2026-03-23 19:24:35.443888-03	2026-03-23 19:24:35.443893-03	f	\N	2	10	100.00	2026-03-23	f	\N		\N	\N	294	\N
2540	2026-03-30 13:03:01.457918-03	2026-03-30 13:03:01.457922-03	f	\N	2	12	723.16	2025-12-31	t	2025-12-31		\N	\N	297	\N
2557	2026-04-01 14:02:45.151962-03	2026-04-01 14:02:45.151965-03	f	\N	7	7	114.28	2026-04-01	f	\N		\N	\N	304	\N
2570	2026-04-01 14:10:02.06709-03	2026-04-01 14:10:02.067093-03	f	\N	1	6	66.70	2026-03-04	t	2026-03-04		\N	\N	306	\N
2582	2026-04-01 14:10:37.679225-03	2026-04-01 14:10:37.679228-03	f	\N	7	10	125.00	2026-08-01	f	\N		\N	\N	307	\N
2021	2026-03-23 19:17:45.279415-03	2026-03-23 19:17:45.279417-03	t	2026-04-01 15:03:39.725269-03	80	510	90.00	2032-04-30	f	\N		3	\N	190	3
1964	2026-03-23 19:17:45.278196-03	2026-03-23 19:17:45.278197-03	t	2026-04-01 15:03:39.725269-03	23	510	90.00	2027-07-30	f	\N		3	\N	190	3
1969	2026-03-23 19:17:45.278279-03	2026-03-23 19:17:45.27828-03	t	2026-04-01 15:03:39.725269-03	28	510	90.00	2027-12-30	f	\N		3	\N	190	3
2468	2026-03-23 19:18:06.21843-03	2026-03-23 19:18:06.218432-03	t	2026-04-01 15:03:39.725269-03	5	10	106.00	2026-03-02	t	2026-03-02		3	\N	192	3
2335	2026-03-23 19:17:45.28967-03	2026-03-23 19:17:45.289672-03	t	2026-04-01 15:03:39.725269-03	394	510	90.00	2058-06-30	f	\N		3	\N	190	3
1989	2026-03-23 19:17:45.278607-03	2026-03-23 19:17:45.278608-03	t	2026-04-01 15:03:39.725269-03	48	510	90.00	2029-08-30	f	\N		3	\N	190	3
2407	2026-03-23 19:17:45.29217-03	2026-03-23 19:17:45.292173-03	t	2026-04-01 15:03:39.725269-03	466	510	90.00	2064-06-30	f	\N		3	\N	190	3
2285	2026-03-23 19:17:45.288422-03	2026-03-23 19:17:45.288423-03	t	2026-04-01 15:03:39.725269-03	344	510	90.00	2054-04-30	f	\N		3	\N	190	3
2414	2026-03-23 19:17:45.292409-03	2026-03-23 19:17:45.292412-03	t	2026-04-01 15:03:39.725269-03	473	510	90.00	2065-01-30	f	\N		3	\N	190	3
2425	2026-03-23 19:17:45.292789-03	2026-03-23 19:17:45.292791-03	t	2026-04-01 15:03:39.725269-03	484	510	90.00	2065-12-30	f	\N		3	\N	190	3
2080	2026-03-23 19:17:45.281322-03	2026-03-23 19:17:45.281324-03	t	2026-04-01 15:03:39.725269-03	139	510	90.00	2037-03-30	f	\N		3	\N	190	3
2128	2026-03-23 19:17:45.283135-03	2026-03-23 19:17:45.283138-03	t	2026-04-01 15:03:39.725269-03	187	510	90.00	2041-03-30	f	\N		3	\N	190	3
2094	2026-03-23 19:17:45.281771-03	2026-03-23 19:17:45.281774-03	t	2026-04-01 15:03:39.725269-03	153	510	90.00	2038-05-30	f	\N		3	\N	190	3
2299	2026-03-23 19:17:45.288664-03	2026-03-23 19:17:45.288665-03	t	2026-04-01 15:03:39.725269-03	358	510	90.00	2055-06-30	f	\N		3	\N	190	3
2009	2026-03-23 19:17:45.278936-03	2026-03-23 19:17:45.278937-03	t	2026-04-01 15:03:39.725269-03	68	510	90.00	2031-04-30	f	\N		3	\N	190	3
2196	2026-03-23 19:17:45.285496-03	2026-03-23 19:17:45.285499-03	t	2026-04-01 15:03:39.725269-03	255	510	90.00	2046-11-30	f	\N		3	\N	190	3
2108	2026-03-23 19:17:45.28223-03	2026-03-23 19:17:45.282233-03	t	2026-04-01 15:03:39.725269-03	167	510	90.00	2039-07-30	f	\N		3	\N	190	3
2331	2026-03-23 19:17:45.289534-03	2026-03-23 19:17:45.289536-03	t	2026-04-01 15:03:39.725269-03	390	510	90.00	2058-03-02	f	\N		3	\N	190	3
2075	2026-03-23 19:17:45.281162-03	2026-03-23 19:17:45.281164-03	t	2026-04-01 15:03:39.725269-03	134	510	90.00	2036-10-30	f	\N		3	\N	190	3
2124	2026-03-23 19:17:45.282982-03	2026-03-23 19:17:45.282984-03	t	2026-04-01 15:03:39.725269-03	183	510	90.00	2040-11-30	f	\N		3	\N	190	3
2182	2026-03-23 19:17:45.285049-03	2026-03-23 19:17:45.285051-03	t	2026-04-01 15:03:39.725269-03	241	510	90.00	2045-09-30	f	\N		3	\N	190	3
2228	2026-03-23 19:17:45.286545-03	2026-03-23 19:17:45.286548-03	t	2026-04-01 15:03:39.725269-03	287	510	90.00	2049-07-30	f	\N		3	\N	190	3
2365	2026-03-23 19:17:45.290688-03	2026-03-23 19:17:45.290691-03	t	2026-04-01 15:03:39.725269-03	424	510	90.00	2060-12-30	f	\N		3	\N	190	3
2055	2026-03-23 19:17:45.280513-03	2026-03-23 19:17:45.280516-03	t	2026-04-01 15:03:39.725269-03	114	510	90.00	2035-03-02	f	\N		3	\N	190	3
2423	2026-03-23 19:17:45.292719-03	2026-03-23 19:17:45.292723-03	t	2026-04-01 15:03:39.725269-03	482	510	90.00	2065-10-30	f	\N		3	\N	190	3
2125	2026-03-23 19:17:45.283015-03	2026-03-23 19:17:45.283018-03	t	2026-04-01 15:03:39.725269-03	184	510	90.00	2040-12-30	f	\N		3	\N	190	3
2038	2026-03-23 19:17:45.279966-03	2026-03-23 19:17:45.279968-03	t	2026-04-01 15:03:39.725269-03	97	510	90.00	2033-09-30	f	\N		3	\N	190	3
2204	2026-03-23 19:17:45.285753-03	2026-03-23 19:17:45.285755-03	t	2026-04-01 15:03:39.725269-03	263	510	90.00	2047-07-30	f	\N		3	\N	190	3
2392	2026-03-23 19:17:45.291652-03	2026-03-23 19:17:45.291654-03	t	2026-04-01 15:03:39.725269-03	451	510	90.00	2063-03-30	f	\N		3	\N	190	3
2469	2026-03-23 19:18:06.218468-03	2026-03-23 19:18:06.21847-03	t	2026-04-01 15:03:39.725269-03	6	10	106.00	2026-03-30	f	\N		3	\N	192	3
499	2026-03-22 22:49:55.619598-03	2026-03-22 22:49:55.6196-03	t	2026-03-23 19:08:31.688388-03	1	10	202.00	2025-09-30	t	2025-09-30		\N	\N	188	\N
500	2026-03-22 22:49:55.61995-03	2026-03-22 22:49:55.619951-03	t	2026-03-23 19:08:31.769971-03	2	10	202.00	2025-10-30	t	2025-10-30		\N	\N	188	\N
501	2026-03-22 22:49:55.620288-03	2026-03-22 22:49:55.62029-03	t	2026-03-23 19:08:31.857349-03	3	10	202.00	2025-11-30	t	2025-11-30		\N	\N	188	\N
502	2026-03-22 22:49:55.62074-03	2026-03-22 22:49:55.620742-03	t	2026-03-23 19:08:31.939703-03	4	10	202.00	2025-12-30	t	2025-12-30		\N	\N	188	\N
503	2026-03-22 22:49:55.621286-03	2026-03-22 22:49:55.621288-03	t	2026-03-23 19:08:32.025322-03	5	10	202.00	2026-01-30	t	2026-01-30		\N	\N	188	\N
504	2026-03-22 22:49:55.621696-03	2026-03-22 22:49:55.621698-03	t	2026-03-23 19:08:32.110465-03	6	10	202.00	2026-02-28	t	2026-02-28		\N	\N	188	\N
505	2026-03-22 22:49:55.622076-03	2026-03-22 22:49:55.622078-03	t	2026-03-23 19:08:32.208001-03	7	10	202.00	2026-03-30	t	2026-03-30		\N	\N	188	\N
506	2026-03-22 22:49:55.622429-03	2026-03-22 22:49:55.622431-03	t	2026-03-23 19:08:32.295401-03	8	10	202.00	2026-04-30	f	\N		\N	\N	188	\N
507	2026-03-22 22:49:55.622784-03	2026-03-22 22:49:55.622785-03	t	2026-03-23 19:08:32.373201-03	9	10	202.00	2026-05-30	f	\N		\N	\N	188	\N
508	2026-03-22 22:49:55.623129-03	2026-03-22 22:49:55.623131-03	t	2026-03-23 19:08:32.457462-03	10	10	202.00	2026-06-30	f	\N		\N	\N	188	\N
2474	2026-03-23 19:19:16.588282-03	2026-03-23 19:19:16.588291-03	f	\N	1	12	337.00	2025-09-23	t	2025-09-23		\N	\N	292	\N
2486	2026-03-23 19:22:04.791751-03	2026-03-23 19:22:04.791757-03	f	\N	1	12	166.00	2025-10-02	t	2025-10-02		3	\N	191	3
2487	2026-03-23 19:22:04.79184-03	2026-03-23 19:22:04.791843-03	f	\N	2	12	166.00	2025-11-02	t	2025-11-02		3	\N	191	3
2488	2026-03-23 19:22:04.791883-03	2026-03-23 19:22:04.791885-03	f	\N	3	12	166.00	2025-12-02	t	2025-12-02		3	\N	191	3
2489	2026-03-23 19:22:04.791921-03	2026-03-23 19:22:04.791924-03	f	\N	4	12	166.00	2026-01-02	t	2026-01-02		3	\N	191	3
2490	2026-03-23 19:22:04.791957-03	2026-03-23 19:22:04.791959-03	f	\N	5	12	166.00	2026-02-02	t	2026-02-02		3	\N	191	3
2491	2026-03-23 19:22:04.791993-03	2026-03-23 19:22:04.791996-03	f	\N	6	12	166.00	2026-03-02	f	\N		3	\N	191	3
2492	2026-03-23 19:22:04.792029-03	2026-03-23 19:22:04.792032-03	f	\N	7	12	166.00	2026-04-02	f	\N		3	\N	191	3
2493	2026-03-23 19:22:04.792065-03	2026-03-23 19:22:04.792067-03	f	\N	8	12	166.00	2026-05-02	f	\N		3	\N	191	3
2494	2026-03-23 19:22:04.7921-03	2026-03-23 19:22:04.792102-03	f	\N	9	12	166.00	2026-06-02	f	\N		3	\N	191	3
2495	2026-03-23 19:22:04.792136-03	2026-03-23 19:22:04.792138-03	f	\N	10	12	166.00	2026-07-02	f	\N		3	\N	191	3
2496	2026-03-23 19:22:04.792171-03	2026-03-23 19:22:04.792173-03	f	\N	11	12	166.00	2026-08-02	f	\N		3	\N	191	3
2497	2026-03-23 19:22:04.792206-03	2026-03-23 19:22:04.792209-03	f	\N	12	12	166.00	2026-09-02	f	\N		3	\N	191	3
2531	2026-03-23 19:24:35.616619-03	2026-03-23 19:24:35.616626-03	f	\N	3	10	100.00	2026-04-23	f	\N		\N	\N	294	\N
2541	2026-03-30 13:03:01.507918-03	2026-03-30 13:03:01.507924-03	f	\N	3	12	723.16	2026-01-31	t	2026-01-31		\N	\N	297	\N
2558	2026-04-01 14:03:33.094166-03	2026-04-01 14:03:33.094173-03	f	\N	1	12	63.33	2026-01-01	t	2026-01-01		\N	\N	305	\N
2571	2026-04-01 14:10:02.207435-03	2026-04-01 14:10:02.207438-03	f	\N	2	6	66.70	2026-04-01	f	\N		\N	\N	306	\N
2583	2026-04-01 14:10:37.714694-03	2026-04-01 14:10:37.714698-03	f	\N	8	10	125.00	2026-09-01	f	\N		\N	\N	307	\N
2298	2026-03-23 19:17:45.288647-03	2026-03-23 19:17:45.288648-03	t	2026-04-01 15:03:39.725269-03	357	510	90.00	2055-05-30	f	\N		3	\N	190	3
2215	2026-03-23 19:17:45.286106-03	2026-03-23 19:17:45.286108-03	t	2026-04-01 15:03:39.725269-03	274	510	90.00	2048-06-30	f	\N		3	\N	190	3
2403	2026-03-23 19:17:45.292033-03	2026-03-23 19:17:45.292035-03	t	2026-04-01 15:03:39.725269-03	462	510	90.00	2064-03-01	f	\N		3	\N	190	3
2311	2026-03-23 19:17:45.288863-03	2026-03-23 19:17:45.288864-03	t	2026-04-01 15:03:39.725269-03	370	510	90.00	2056-06-30	f	\N		3	\N	190	3
1963	2026-03-23 19:17:45.278179-03	2026-03-23 19:17:45.27818-03	t	2026-04-01 15:03:39.725269-03	22	510	90.00	2027-06-30	f	\N		3	\N	190	3
2276	2026-03-23 19:17:45.288256-03	2026-03-23 19:17:45.28826-03	t	2026-04-01 15:03:39.725269-03	335	510	90.00	2053-07-30	f	\N		3	\N	190	3
2152	2026-03-23 19:17:45.283922-03	2026-03-23 19:17:45.283924-03	t	2026-04-01 15:03:39.725269-03	211	510	90.00	2043-03-30	f	\N		3	\N	190	3
2040	2026-03-23 19:17:45.28003-03	2026-03-23 19:17:45.280034-03	t	2026-04-01 15:03:39.725269-03	99	510	90.00	2033-11-30	f	\N		3	\N	190	3
2385	2026-03-23 19:17:45.291415-03	2026-03-23 19:17:45.291418-03	t	2026-04-01 15:03:39.725269-03	444	510	90.00	2062-08-30	f	\N		3	\N	190	3
2025	2026-03-23 19:17:45.279545-03	2026-03-23 19:17:45.279548-03	t	2026-04-01 15:03:39.725269-03	84	510	90.00	2032-08-30	f	\N		3	\N	190	3
2394	2026-03-23 19:17:45.291724-03	2026-03-23 19:17:45.291727-03	t	2026-04-01 15:03:39.725269-03	453	510	90.00	2063-05-30	f	\N		3	\N	190	3
2420	2026-03-23 19:17:45.292617-03	2026-03-23 19:17:45.29262-03	t	2026-04-01 15:03:39.725269-03	479	510	90.00	2065-07-30	f	\N		3	\N	190	3
2172	2026-03-23 19:17:45.284723-03	2026-03-23 19:17:45.284725-03	t	2026-04-01 15:03:39.725269-03	231	510	90.00	2044-11-30	f	\N		3	\N	190	3
2300	2026-03-23 19:17:45.28868-03	2026-03-23 19:17:45.288681-03	t	2026-04-01 15:03:39.725269-03	359	510	90.00	2055-07-30	f	\N		3	\N	190	3
2115	2026-03-23 19:17:45.28267-03	2026-03-23 19:17:45.282673-03	t	2026-04-01 15:03:39.725269-03	174	510	90.00	2040-03-01	f	\N		3	\N	190	3
2082	2026-03-23 19:17:45.281386-03	2026-03-23 19:17:45.281388-03	t	2026-04-01 15:03:39.725269-03	141	510	90.00	2037-05-30	f	\N		3	\N	190	3
2357	2026-03-23 19:17:45.290417-03	2026-03-23 19:17:45.29042-03	t	2026-04-01 15:03:39.725269-03	416	510	90.00	2060-04-30	f	\N		3	\N	190	3
2259	2026-03-23 19:17:45.287612-03	2026-03-23 19:17:45.287615-03	t	2026-04-01 15:03:39.725269-03	318	510	90.00	2052-03-01	f	\N		3	\N	190	3
2054	2026-03-23 19:17:45.280482-03	2026-03-23 19:17:45.280484-03	t	2026-04-01 15:03:39.725269-03	113	510	90.00	2035-01-30	f	\N		3	\N	190	3
2332	2026-03-23 19:17:45.289568-03	2026-03-23 19:17:45.28957-03	t	2026-04-01 15:03:39.725269-03	391	510	90.00	2058-03-30	f	\N		3	\N	190	3
2404	2026-03-23 19:17:45.292067-03	2026-03-23 19:17:45.29207-03	t	2026-04-01 15:03:39.725269-03	463	510	90.00	2064-03-30	f	\N		3	\N	190	3
1978	2026-03-23 19:17:45.278427-03	2026-03-23 19:17:45.278429-03	t	2026-04-01 15:03:39.725269-03	37	510	90.00	2028-09-30	f	\N		3	\N	190	3
2006	2026-03-23 19:17:45.278883-03	2026-03-23 19:17:45.278884-03	t	2026-04-01 15:03:39.725269-03	65	510	90.00	2031-01-30	f	\N		3	\N	190	3
2065	2026-03-23 19:17:45.280829-03	2026-03-23 19:17:45.280831-03	t	2026-04-01 15:03:39.725269-03	124	510	90.00	2035-12-30	f	\N		3	\N	190	3
2313	2026-03-23 19:17:45.288896-03	2026-03-23 19:17:45.288898-03	t	2026-04-01 15:03:39.725269-03	372	510	90.00	2056-08-30	f	\N		3	\N	190	3
2366	2026-03-23 19:17:45.290723-03	2026-03-23 19:17:45.290725-03	t	2026-04-01 15:03:39.725269-03	425	510	90.00	2061-01-30	f	\N		3	\N	190	3
2291	2026-03-23 19:17:45.288526-03	2026-03-23 19:17:45.288527-03	t	2026-04-01 15:03:39.725269-03	350	510	90.00	2054-10-30	f	\N		3	\N	190	3
2400	2026-03-23 19:17:45.291933-03	2026-03-23 19:17:45.291935-03	t	2026-04-01 15:03:39.725269-03	459	510	90.00	2063-11-30	f	\N		3	\N	190	3
2146	2026-03-23 19:17:45.283727-03	2026-03-23 19:17:45.28373-03	t	2026-04-01 15:03:39.725269-03	205	510	90.00	2042-09-30	f	\N		3	\N	190	3
2321	2026-03-23 19:17:45.289031-03	2026-03-23 19:17:45.289032-03	t	2026-04-01 15:03:39.725269-03	380	510	90.00	2057-04-30	f	\N		3	\N	190	3
2226	2026-03-23 19:17:45.286477-03	2026-03-23 19:17:45.286479-03	t	2026-04-01 15:03:39.725269-03	285	510	90.00	2049-05-30	f	\N		3	\N	190	3
2071	2026-03-23 19:17:45.281034-03	2026-03-23 19:17:45.281037-03	t	2026-04-01 15:03:39.725269-03	130	510	90.00	2036-06-30	f	\N		3	\N	190	3
1954	2026-03-23 19:17:45.278023-03	2026-03-23 19:17:45.278025-03	t	2026-04-01 15:03:39.725269-03	13	510	90.00	2026-09-30	f	\N		3	\N	190	3
2352	2026-03-23 19:17:45.290248-03	2026-03-23 19:17:45.290251-03	t	2026-04-01 15:03:39.725269-03	411	510	90.00	2059-11-30	f	\N		3	\N	190	3
2419	2026-03-23 19:17:45.292579-03	2026-03-23 19:17:45.292582-03	t	2026-04-01 15:03:39.725269-03	478	510	90.00	2065-06-30	f	\N		3	\N	190	3
2057	2026-03-23 19:17:45.280577-03	2026-03-23 19:17:45.280579-03	t	2026-04-01 15:03:39.725269-03	116	510	90.00	2035-04-30	f	\N		3	\N	190	3
2301	2026-03-23 19:17:45.288697-03	2026-03-23 19:17:45.288698-03	t	2026-04-01 15:03:39.725269-03	360	510	90.00	2055-08-30	f	\N		3	\N	190	3
2176	2026-03-23 19:17:45.284857-03	2026-03-23 19:17:45.28486-03	t	2026-04-01 15:03:39.725269-03	235	510	90.00	2045-03-30	f	\N		3	\N	190	3
2068	2026-03-23 19:17:45.280936-03	2026-03-23 19:17:45.280939-03	t	2026-04-01 15:03:39.725269-03	127	510	90.00	2036-03-30	f	\N		3	\N	190	3
2059	2026-03-23 19:17:45.28064-03	2026-03-23 19:17:45.280642-03	t	2026-04-01 15:03:39.725269-03	118	510	90.00	2035-06-30	f	\N		3	\N	190	3
2028	2026-03-23 19:17:45.279643-03	2026-03-23 19:17:45.279646-03	t	2026-04-01 15:03:39.725269-03	87	510	90.00	2032-11-30	f	\N		3	\N	190	3
1984	2026-03-23 19:17:45.278525-03	2026-03-23 19:17:45.278526-03	t	2026-04-01 15:03:39.725269-03	43	510	90.00	2029-03-30	f	\N		3	\N	190	3
2063	2026-03-23 19:17:45.280766-03	2026-03-23 19:17:45.280768-03	t	2026-04-01 15:03:39.725269-03	122	510	90.00	2035-10-30	f	\N		3	\N	190	3
2265	2026-03-23 19:17:45.287818-03	2026-03-23 19:17:45.28782-03	t	2026-04-01 15:03:39.725269-03	324	510	90.00	2052-08-30	f	\N		3	\N	190	3
2168	2026-03-23 19:17:45.284588-03	2026-03-23 19:17:45.284591-03	t	2026-04-01 15:03:39.725269-03	227	510	90.00	2044-07-30	f	\N		3	\N	190	3
2307	2026-03-23 19:17:45.288797-03	2026-03-23 19:17:45.288798-03	t	2026-04-01 15:03:39.725269-03	366	510	90.00	2056-03-01	f	\N		3	\N	190	3
2147	2026-03-23 19:17:45.283759-03	2026-03-23 19:17:45.283762-03	t	2026-04-01 15:03:39.725269-03	206	510	90.00	2042-10-30	f	\N		3	\N	190	3
2229	2026-03-23 19:17:45.286579-03	2026-03-23 19:17:45.286582-03	t	2026-04-01 15:03:39.725269-03	288	510	90.00	2049-08-30	f	\N		3	\N	190	3
2015	2026-03-23 19:17:45.279033-03	2026-03-23 19:17:45.279034-03	t	2026-04-01 15:03:39.725269-03	74	510	90.00	2031-10-30	f	\N		3	\N	190	3
1990	2026-03-23 19:17:45.278623-03	2026-03-23 19:17:45.278624-03	t	2026-04-01 15:03:39.725269-03	49	510	90.00	2029-09-30	f	\N		3	\N	190	3
2475	2026-03-23 19:19:16.656264-03	2026-03-23 19:19:16.656271-03	f	\N	2	12	337.00	2025-10-23	t	2025-10-23		\N	\N	292	\N
2498	2026-03-23 19:22:43.965322-03	2026-03-23 19:22:43.965332-03	f	\N	1	6	148.00	2025-10-30	t	2025-10-30		3	\N	193	3
2499	2026-03-23 19:22:43.965434-03	2026-03-23 19:22:43.965437-03	f	\N	2	6	148.00	2025-11-30	t	2025-11-30		3	\N	193	3
2500	2026-03-23 19:22:43.965472-03	2026-03-23 19:22:43.965475-03	f	\N	3	6	148.00	2025-12-30	t	2025-12-30		3	\N	193	3
2501	2026-03-23 19:22:43.965502-03	2026-03-23 19:22:43.965505-03	f	\N	4	6	148.00	2026-01-30	t	2026-01-30		3	\N	193	3
2502	2026-03-23 19:22:43.965531-03	2026-03-23 19:22:43.965534-03	f	\N	5	6	148.00	2026-03-02	t	2026-03-02		3	\N	193	3
2503	2026-03-23 19:22:43.96556-03	2026-03-23 19:22:43.965563-03	f	\N	6	6	148.00	2026-03-30	f	\N		3	\N	193	3
2532	2026-03-23 19:24:35.668018-03	2026-03-23 19:24:35.668022-03	f	\N	4	10	100.00	2026-05-23	f	\N		\N	\N	294	\N
2542	2026-03-30 13:03:01.567176-03	2026-03-30 13:03:01.567182-03	f	\N	4	12	723.16	2026-03-03	t	2026-03-03		\N	\N	297	\N
1	2026-03-22 22:49:55.295088-03	2026-03-22 22:49:55.295091-03	f	\N	2	10	60.00	2025-11-09	t	2025-11-09		\N	\N	1	\N
2	2026-03-22 22:49:55.301476-03	2026-03-22 22:49:55.30148-03	f	\N	3	10	60.00	2025-12-09	t	2025-12-09		\N	\N	1	\N
3	2026-03-22 22:49:55.302195-03	2026-03-22 22:49:55.302197-03	f	\N	4	10	60.00	2026-01-09	t	2026-01-09		\N	\N	1	\N
4	2026-03-22 22:49:55.302785-03	2026-03-22 22:49:55.302786-03	f	\N	5	10	60.00	2026-02-09	t	2026-02-09		\N	\N	1	\N
5	2026-03-22 22:49:55.303206-03	2026-03-22 22:49:55.303208-03	f	\N	6	10	60.00	2026-03-09	f	\N		\N	\N	1	\N
6	2026-03-22 22:49:55.303621-03	2026-03-22 22:49:55.303623-03	f	\N	7	10	60.00	2026-04-09	f	\N		\N	\N	1	\N
7	2026-03-22 22:49:55.304132-03	2026-03-22 22:49:55.304134-03	f	\N	8	10	60.00	2026-05-09	f	\N		\N	\N	1	\N
8	2026-03-22 22:49:55.304579-03	2026-03-22 22:49:55.304581-03	f	\N	9	10	60.00	2026-06-09	f	\N		\N	\N	1	\N
9	2026-03-22 22:49:55.305021-03	2026-03-22 22:49:55.305023-03	f	\N	10	10	60.00	2026-07-09	f	\N		\N	\N	1	\N
11	2026-03-22 22:49:55.306921-03	2026-03-22 22:49:55.306923-03	f	\N	2	9	60.22	2026-01-09	t	2026-01-09		\N	\N	2	\N
12	2026-03-22 22:49:55.307457-03	2026-03-22 22:49:55.307459-03	f	\N	3	9	60.22	2026-02-09	t	2026-02-09		\N	\N	2	\N
13	2026-03-22 22:49:55.307968-03	2026-03-22 22:49:55.30797-03	f	\N	4	9	60.22	2026-03-09	f	\N		\N	\N	2	\N
14	2026-03-22 22:49:55.308567-03	2026-03-22 22:49:55.308569-03	f	\N	5	9	60.22	2026-04-09	f	\N		\N	\N	2	\N
15	2026-03-22 22:49:55.30903-03	2026-03-22 22:49:55.309032-03	f	\N	6	9	60.22	2026-05-09	f	\N		\N	\N	2	\N
16	2026-03-22 22:49:55.309558-03	2026-03-22 22:49:55.30956-03	f	\N	7	9	60.22	2026-06-09	f	\N		\N	\N	2	\N
17	2026-03-22 22:49:55.31015-03	2026-03-22 22:49:55.310151-03	f	\N	8	9	60.22	2026-07-09	f	\N		\N	\N	2	\N
18	2026-03-22 22:49:55.310662-03	2026-03-22 22:49:55.310691-03	f	\N	9	9	60.22	2026-08-09	f	\N		\N	\N	2	\N
20	2026-03-22 22:49:55.312471-03	2026-03-22 22:49:55.312473-03	f	\N	2	4	31.17	2026-01-09	t	2026-01-09		\N	\N	3	\N
21	2026-03-22 22:49:55.312967-03	2026-03-22 22:49:55.312969-03	f	\N	3	4	31.17	2026-02-09	t	2026-02-09		\N	\N	3	\N
22	2026-03-22 22:49:55.313411-03	2026-03-22 22:49:55.313413-03	f	\N	4	4	31.17	2026-03-09	f	\N		\N	\N	3	\N
24	2026-03-22 22:49:55.314926-03	2026-03-22 22:49:55.314929-03	f	\N	2	6	43.26	2026-01-09	t	2026-01-09		\N	\N	4	\N
25	2026-03-22 22:49:55.315522-03	2026-03-22 22:49:55.315524-03	f	\N	3	6	43.26	2026-02-09	t	2026-02-09		\N	\N	4	\N
26	2026-03-22 22:49:55.315954-03	2026-03-22 22:49:55.315955-03	f	\N	4	6	43.26	2026-03-09	f	\N		\N	\N	4	\N
27	2026-03-22 22:49:55.316331-03	2026-03-22 22:49:55.316333-03	f	\N	5	6	43.26	2026-04-09	f	\N		\N	\N	4	\N
28	2026-03-22 22:49:55.316778-03	2026-03-22 22:49:55.31678-03	f	\N	6	6	43.26	2026-05-09	f	\N		\N	\N	4	\N
30	2026-03-22 22:49:55.31847-03	2026-03-22 22:49:55.318472-03	f	\N	2	3	50.00	2026-01-09	t	2026-01-09		\N	\N	5	\N
31	2026-03-22 22:49:55.318934-03	2026-03-22 22:49:55.318936-03	f	\N	3	3	50.00	2026-02-09	t	2026-02-09		\N	\N	5	\N
33	2026-03-22 22:49:55.320652-03	2026-03-22 22:49:55.320654-03	f	\N	2	3	93.80	2026-02-09	t	2026-02-09		\N	\N	6	\N
34	2026-03-22 22:49:55.321112-03	2026-03-22 22:49:55.321114-03	f	\N	3	3	93.80	2026-03-09	f	\N		\N	\N	6	\N
36	2026-03-22 22:49:55.322497-03	2026-03-22 22:49:55.322499-03	f	\N	2	2	74.84	2026-02-09	t	2026-02-09		\N	\N	7	\N
38	2026-03-22 22:49:55.323736-03	2026-03-22 22:49:55.323737-03	f	\N	2	3	52.18	2026-02-09	t	2026-02-09		\N	\N	8	\N
39	2026-03-22 22:49:55.324059-03	2026-03-22 22:49:55.324061-03	f	\N	3	3	52.18	2026-03-09	f	\N		\N	\N	8	\N
41	2026-03-22 22:49:55.325059-03	2026-03-22 22:49:55.32506-03	f	\N	2	2	294.20	2026-02-09	t	2026-02-09		\N	\N	9	\N
43	2026-03-22 22:49:55.326084-03	2026-03-22 22:49:55.326086-03	f	\N	2	2	111.25	2026-02-09	t	2026-02-09		\N	\N	10	\N
45	2026-03-22 22:49:55.327171-03	2026-03-22 22:49:55.327173-03	f	\N	2	2	49.55	2026-02-09	t	2026-02-09		\N	\N	11	\N
47	2026-03-22 22:49:55.328563-03	2026-03-22 22:49:55.328565-03	f	\N	2	2	108.48	2026-03-09	f	\N		\N	\N	12	\N
49	2026-03-22 22:49:55.329787-03	2026-03-22 22:49:55.329788-03	f	\N	2	2	15.23	2026-03-09	f	\N		\N	\N	13	\N
51	2026-03-22 22:49:55.330749-03	2026-03-22 22:49:55.330751-03	f	\N	2	3	78.00	2026-03-09	f	\N		\N	\N	14	\N
52	2026-03-22 22:49:55.33106-03	2026-03-22 22:49:55.331062-03	f	\N	3	3	78.00	2026-04-09	f	\N		\N	\N	14	\N
54	2026-03-22 22:49:55.332076-03	2026-03-22 22:49:55.332077-03	f	\N	2	2	54.05	2026-03-09	f	\N		\N	\N	15	\N
56	2026-03-22 22:49:55.33411-03	2026-03-22 22:49:55.334111-03	f	\N	2	3	60.00	2026-03-09	f	\N		\N	\N	16	\N
57	2026-03-22 22:49:55.334415-03	2026-03-22 22:49:55.334417-03	f	\N	3	3	60.00	2026-04-09	f	\N		\N	\N	16	\N
59	2026-03-22 22:49:55.336033-03	2026-03-22 22:49:55.336035-03	f	\N	2	4	268.40	2026-03-09	f	\N		\N	\N	17	\N
60	2026-03-22 22:49:55.336573-03	2026-03-22 22:49:55.336575-03	f	\N	3	4	268.40	2026-04-09	f	\N		\N	\N	17	\N
61	2026-03-22 22:49:55.337103-03	2026-03-22 22:49:55.337105-03	f	\N	4	4	268.40	2026-05-09	f	\N		\N	\N	17	\N
63	2026-03-22 22:49:55.345395-03	2026-03-22 22:49:55.345396-03	f	\N	2	6	118.01	2026-04-09	f	\N		\N	\N	33	\N
64	2026-03-22 22:49:55.345753-03	2026-03-22 22:49:55.345755-03	f	\N	3	6	118.01	2026-05-09	f	\N		\N	\N	33	\N
65	2026-03-22 22:49:55.346196-03	2026-03-22 22:49:55.346198-03	f	\N	4	6	118.01	2026-06-09	f	\N		\N	\N	33	\N
66	2026-03-22 22:49:55.346724-03	2026-03-22 22:49:55.346725-03	f	\N	5	6	118.01	2026-07-09	f	\N		\N	\N	33	\N
67	2026-03-22 22:49:55.347125-03	2026-03-22 22:49:55.347127-03	f	\N	6	6	118.01	2026-08-09	f	\N		\N	\N	33	\N
69	2026-03-22 22:49:55.348764-03	2026-03-22 22:49:55.348766-03	f	\N	2	4	32.49	2026-04-09	f	\N		\N	\N	34	\N
70	2026-03-22 22:49:55.349265-03	2026-03-22 22:49:55.349267-03	f	\N	3	4	32.49	2026-05-09	f	\N		\N	\N	34	\N
71	2026-03-22 22:49:55.34962-03	2026-03-22 22:49:55.349622-03	f	\N	4	4	32.49	2026-06-09	f	\N		\N	\N	34	\N
73	2026-03-22 22:49:55.354572-03	2026-03-22 22:49:55.354574-03	f	\N	2	5	226.00	2025-12-03	t	2025-12-03		\N	\N	41	\N
74	2026-03-22 22:49:55.355136-03	2026-03-22 22:49:55.355138-03	f	\N	3	5	226.00	2026-01-03	t	2026-01-03		\N	\N	41	\N
75	2026-03-22 22:49:55.355668-03	2026-03-22 22:49:55.35567-03	f	\N	4	5	226.00	2026-02-03	t	2026-02-03		\N	\N	41	\N
76	2026-03-22 22:49:55.356171-03	2026-03-22 22:49:55.356173-03	f	\N	5	5	226.00	2026-03-03	f	\N		\N	\N	41	\N
78	2026-03-22 22:49:55.357662-03	2026-03-22 22:49:55.357664-03	f	\N	2	3	168.48	2026-02-03	t	2026-02-03		\N	\N	42	\N
79	2026-03-22 22:49:55.358093-03	2026-03-22 22:49:55.358094-03	f	\N	3	3	168.48	2026-03-03	f	\N		\N	\N	42	\N
81	2026-03-22 22:49:55.359935-03	2026-03-22 22:49:55.359937-03	f	\N	2	5	50.00	2026-02-03	t	2026-02-03		\N	\N	43	\N
82	2026-03-22 22:49:55.360405-03	2026-03-22 22:49:55.360407-03	f	\N	3	5	50.00	2026-03-03	f	\N		\N	\N	43	\N
83	2026-03-22 22:49:55.360945-03	2026-03-22 22:49:55.360947-03	f	\N	4	5	50.00	2026-04-03	f	\N		\N	\N	43	\N
84	2026-03-22 22:49:55.361354-03	2026-03-22 22:49:55.361355-03	f	\N	5	5	50.00	2026-05-03	f	\N		\N	\N	43	\N
86	2026-03-22 22:49:55.362738-03	2026-03-22 22:49:55.36274-03	f	\N	2	3	68.30	2026-02-03	t	2026-02-03		\N	\N	44	\N
87	2026-03-22 22:49:55.363171-03	2026-03-22 22:49:55.363173-03	f	\N	3	3	68.30	2026-03-03	f	\N		\N	\N	44	\N
89	2026-03-22 22:49:55.364459-03	2026-03-22 22:49:55.364461-03	f	\N	2	2	59.50	2026-02-03	t	2026-02-03		\N	\N	45	\N
91	2026-03-22 22:49:55.366205-03	2026-03-22 22:49:55.366207-03	f	\N	2	10	100.00	2026-02-03	t	2026-02-03		\N	\N	46	\N
92	2026-03-22 22:49:55.366658-03	2026-03-22 22:49:55.36666-03	f	\N	3	10	100.00	2026-03-03	f	\N		\N	\N	46	\N
93	2026-03-22 22:49:55.367075-03	2026-03-22 22:49:55.367077-03	f	\N	4	10	100.00	2026-04-03	f	\N		\N	\N	46	\N
2476	2026-03-23 19:19:16.727252-03	2026-03-23 19:19:16.727259-03	f	\N	3	12	337.00	2025-11-23	t	2025-11-23		\N	\N	292	\N
2504	2026-03-23 19:22:55.516795-03	2026-03-23 19:22:55.516803-03	f	\N	1	7	71.00	2026-01-28	t	2026-01-28		3	\N	195	3
2505	2026-03-23 19:22:55.516904-03	2026-03-23 19:22:55.516907-03	f	\N	2	7	71.00	2026-02-28	t	2026-02-28		3	\N	195	3
2506	2026-03-23 19:22:55.516938-03	2026-03-23 19:22:55.51694-03	f	\N	3	7	71.00	2026-03-28	f	\N		3	\N	195	3
2507	2026-03-23 19:22:55.516968-03	2026-03-23 19:22:55.51697-03	f	\N	4	7	71.00	2026-04-28	f	\N		3	\N	195	3
2508	2026-03-23 19:22:55.516994-03	2026-03-23 19:22:55.516997-03	f	\N	5	7	71.00	2026-05-28	f	\N		3	\N	195	3
2509	2026-03-23 19:22:55.517023-03	2026-03-23 19:22:55.517025-03	f	\N	6	7	71.00	2026-06-28	f	\N		3	\N	195	3
2510	2026-03-23 19:22:55.517051-03	2026-03-23 19:22:55.517053-03	f	\N	7	7	71.00	2026-07-28	f	\N		3	\N	195	3
2533	2026-03-23 19:24:35.712069-03	2026-03-23 19:24:35.712076-03	f	\N	5	10	100.00	2026-06-23	f	\N		\N	\N	294	\N
2543	2026-03-30 13:03:01.722352-03	2026-03-30 13:03:01.722355-03	f	\N	5	12	723.16	2026-03-31	t	2026-03-31		\N	\N	297	\N
94	2026-03-22 22:49:55.367479-03	2026-03-22 22:49:55.36748-03	f	\N	5	10	100.00	2026-05-03	f	\N		\N	\N	46	\N
95	2026-03-22 22:49:55.367922-03	2026-03-22 22:49:55.367924-03	f	\N	6	10	100.00	2026-06-03	f	\N		\N	\N	46	\N
96	2026-03-22 22:49:55.368551-03	2026-03-22 22:49:55.368552-03	f	\N	7	10	100.00	2026-07-03	f	\N		\N	\N	46	\N
97	2026-03-22 22:49:55.368981-03	2026-03-22 22:49:55.368983-03	f	\N	8	10	100.00	2026-08-03	f	\N		\N	\N	46	\N
98	2026-03-22 22:49:55.369456-03	2026-03-22 22:49:55.369457-03	f	\N	9	10	100.00	2026-09-03	f	\N		\N	\N	46	\N
99	2026-03-22 22:49:55.369848-03	2026-03-22 22:49:55.369849-03	f	\N	10	10	100.00	2026-10-03	f	\N		\N	\N	46	\N
101	2026-03-22 22:49:55.371252-03	2026-03-22 22:49:55.371254-03	f	\N	2	3	96.83	2026-02-03	t	2026-02-03		\N	\N	47	\N
102	2026-03-22 22:49:55.371665-03	2026-03-22 22:49:55.371667-03	f	\N	3	3	96.83	2026-03-03	f	\N		\N	\N	47	\N
104	2026-03-22 22:49:55.373157-03	2026-03-22 22:49:55.373159-03	f	\N	2	4	149.27	2026-03-03	f	\N		\N	\N	48	\N
105	2026-03-22 22:49:55.373701-03	2026-03-22 22:49:55.373703-03	f	\N	3	4	149.27	2026-04-03	f	\N		\N	\N	48	\N
106	2026-03-22 22:49:55.374223-03	2026-03-22 22:49:55.374225-03	f	\N	4	4	149.27	2026-05-03	f	\N		\N	\N	48	\N
108	2026-03-22 22:49:55.375589-03	2026-03-22 22:49:55.375591-03	f	\N	2	2	54.04	2026-03-03	f	\N		\N	\N	49	\N
110	2026-03-22 22:49:55.377097-03	2026-03-22 22:49:55.377099-03	f	\N	2	3	101.91	2026-03-03	f	\N		\N	\N	50	\N
111	2026-03-22 22:49:55.377478-03	2026-03-22 22:49:55.37748-03	f	\N	3	3	101.91	2026-04-03	f	\N		\N	\N	50	\N
113	2026-03-22 22:49:55.380756-03	2026-03-22 22:49:55.380758-03	f	\N	2	5	82.65	2026-04-03	f	\N		\N	\N	54	\N
114	2026-03-22 22:49:55.381137-03	2026-03-22 22:49:55.381239-03	f	\N	3	5	82.65	2026-05-03	f	\N		\N	\N	54	\N
115	2026-03-22 22:49:55.381986-03	2026-03-22 22:49:55.381988-03	f	\N	4	5	82.65	2026-06-03	f	\N		\N	\N	54	\N
116	2026-03-22 22:49:55.382823-03	2026-03-22 22:49:55.382825-03	f	\N	5	5	82.65	2026-07-03	f	\N		\N	\N	54	\N
118	2026-03-22 22:49:55.384503-03	2026-03-22 22:49:55.384505-03	f	\N	2	3	27.02	2026-04-03	f	\N		\N	\N	55	\N
119	2026-03-22 22:49:55.38502-03	2026-03-22 22:49:55.385022-03	f	\N	3	3	27.02	2026-05-03	f	\N		\N	\N	55	\N
121	2026-03-22 22:49:55.38668-03	2026-03-22 22:49:55.386682-03	f	\N	2	2	45.73	2026-04-03	f	\N		\N	\N	56	\N
123	2026-03-22 22:49:55.388148-03	2026-03-22 22:49:55.38815-03	f	\N	2	2	109.48	2026-04-03	f	\N		\N	\N	57	\N
125	2026-03-22 22:49:55.389488-03	2026-03-22 22:49:55.38949-03	f	\N	2	3	59.94	2026-04-03	f	\N		\N	\N	58	\N
126	2026-03-22 22:49:55.389971-03	2026-03-22 22:49:55.389973-03	f	\N	3	3	59.94	2026-05-03	f	\N		\N	\N	58	\N
138	2026-03-22 22:49:55.401064-03	2026-03-22 22:49:55.401065-03	f	\N	2	10	130.00	2025-10-07	t	2025-10-07		\N	\N	68	\N
139	2026-03-22 22:49:55.401396-03	2026-03-22 22:49:55.401398-03	f	\N	3	10	130.00	2025-11-07	t	2025-11-07		\N	\N	68	\N
140	2026-03-22 22:49:55.401755-03	2026-03-22 22:49:55.401757-03	f	\N	4	10	130.00	2025-12-07	t	2025-12-07		\N	\N	68	\N
141	2026-03-22 22:49:55.402103-03	2026-03-22 22:49:55.402105-03	f	\N	5	10	130.00	2026-01-07	t	2026-01-07		\N	\N	68	\N
142	2026-03-22 22:49:55.402442-03	2026-03-22 22:49:55.402444-03	f	\N	6	10	130.00	2026-02-07	t	2026-02-07		\N	\N	68	\N
143	2026-03-22 22:49:55.402824-03	2026-03-22 22:49:55.402826-03	f	\N	7	10	130.00	2026-03-07	t	2026-03-07		\N	\N	68	\N
144	2026-03-22 22:49:55.403305-03	2026-03-22 22:49:55.403307-03	f	\N	8	10	130.00	2026-04-07	f	\N		\N	\N	68	\N
145	2026-03-22 22:49:55.40389-03	2026-03-22 22:49:55.403892-03	f	\N	9	10	130.00	2026-05-07	f	\N		\N	\N	68	\N
146	2026-03-22 22:49:55.404438-03	2026-03-22 22:49:55.40444-03	f	\N	10	10	130.00	2026-06-07	f	\N		\N	\N	68	\N
148	2026-03-22 22:49:55.405946-03	2026-03-22 22:49:55.405947-03	f	\N	2	6	61.30	2025-12-07	t	2025-12-07		\N	\N	69	\N
149	2026-03-22 22:49:55.406404-03	2026-03-22 22:49:55.406405-03	f	\N	3	6	61.30	2026-01-07	t	2026-01-07		\N	\N	69	\N
150	2026-03-22 22:49:55.406947-03	2026-03-22 22:49:55.406949-03	f	\N	4	6	61.30	2026-02-07	t	2026-02-07		\N	\N	69	\N
151	2026-03-22 22:49:55.407535-03	2026-03-22 22:49:55.407537-03	f	\N	5	6	61.30	2026-03-07	t	2026-03-07		\N	\N	69	\N
152	2026-03-22 22:49:55.408013-03	2026-03-22 22:49:55.408015-03	f	\N	6	6	61.30	2026-04-07	f	\N		\N	\N	69	\N
154	2026-03-22 22:49:55.409504-03	2026-03-22 22:49:55.409506-03	f	\N	2	5	32.94	2026-01-07	t	2026-01-07		\N	\N	70	\N
155	2026-03-22 22:49:55.410016-03	2026-03-22 22:49:55.410018-03	f	\N	3	5	32.94	2026-02-07	t	2026-02-07		\N	\N	70	\N
156	2026-03-22 22:49:55.41055-03	2026-03-22 22:49:55.410552-03	f	\N	4	5	32.94	2026-03-07	t	2026-03-07		\N	\N	70	\N
157	2026-03-22 22:49:55.410995-03	2026-03-22 22:49:55.410997-03	f	\N	5	5	32.94	2026-04-07	f	\N		\N	\N	70	\N
166	2026-03-22 22:49:55.41687-03	2026-03-22 22:49:55.416872-03	f	\N	2	4	97.10	2026-02-07	t	2026-02-07		\N	\N	73	\N
167	2026-03-22 22:49:55.417332-03	2026-03-22 22:49:55.417334-03	f	\N	3	4	97.10	2026-03-07	t	2026-03-07		\N	\N	73	\N
168	2026-03-22 22:49:55.417789-03	2026-03-22 22:49:55.417791-03	f	\N	4	4	97.10	2026-04-07	f	\N		\N	\N	73	\N
170	2026-03-22 22:49:55.419616-03	2026-03-22 22:49:55.419618-03	f	\N	2	6	100.00	2026-03-07	t	2026-03-07		\N	\N	74	\N
171	2026-03-22 22:49:55.420107-03	2026-03-22 22:49:55.420109-03	f	\N	3	6	100.00	2026-04-07	f	\N		\N	\N	74	\N
172	2026-03-22 22:49:55.420632-03	2026-03-22 22:49:55.420634-03	f	\N	4	6	100.00	2026-05-07	f	\N		\N	\N	74	\N
173	2026-03-22 22:49:55.421117-03	2026-03-22 22:49:55.421119-03	f	\N	5	6	100.00	2026-06-07	f	\N		\N	\N	74	\N
174	2026-03-22 22:49:55.421656-03	2026-03-22 22:49:55.421658-03	f	\N	6	6	100.00	2026-07-07	f	\N		\N	\N	74	\N
182	2026-03-22 22:49:55.428194-03	2026-03-22 22:49:55.428196-03	f	\N	2	4	83.99	2026-03-07	t	2026-03-07		\N	\N	78	\N
161	2026-03-22 22:49:55.413591-03	2026-04-01 18:20:18.210141-03	f	\N	4	4	294.81	2026-04-07	t	2026-04-07		\N	\N	71	\N
163	2026-03-22 22:49:55.414952-03	2026-04-01 18:20:18.212868-03	f	\N	2	3	74.99	2026-03-07	t	2026-03-07		\N	\N	72	\N
164	2026-03-22 22:49:55.415436-03	2026-04-01 18:20:18.213829-03	f	\N	3	3	74.99	2026-04-07	t	2026-04-07		\N	\N	72	\N
176	2026-03-22 22:49:55.423679-03	2026-04-01 18:20:18.216195-03	f	\N	2	2	207.99	2026-04-07	t	2026-04-07		\N	\N	75	\N
178	2026-03-22 22:49:55.425174-03	2026-04-01 18:20:18.218476-03	f	\N	2	2	80.56	2026-04-07	t	2026-04-07		\N	\N	76	\N
180	2026-03-22 22:49:55.42675-03	2026-04-01 18:20:18.22245-03	f	\N	2	2	61.61	2026-04-07	t	2026-04-07		\N	\N	77	\N
128	2026-03-22 22:49:55.395982-03	2026-04-01 18:20:18.224164-03	f	\N	2	10	31.62	2025-08-07	t	2025-08-07		\N	\N	67	\N
129	2026-03-22 22:49:55.396908-03	2026-04-01 18:20:18.224701-03	f	\N	3	10	31.62	2025-09-07	t	2025-09-07		\N	\N	67	\N
130	2026-03-22 22:49:55.397425-03	2026-04-01 18:20:18.22529-03	f	\N	4	10	31.62	2025-10-07	t	2025-10-07		\N	\N	67	\N
131	2026-03-22 22:49:55.397927-03	2026-04-01 18:20:18.225977-03	f	\N	5	10	31.62	2025-11-07	t	2025-11-07		\N	\N	67	\N
132	2026-03-22 22:49:55.398375-03	2026-04-01 18:20:18.226528-03	f	\N	6	10	31.62	2025-12-07	t	2025-12-07		\N	\N	67	\N
133	2026-03-22 22:49:55.398814-03	2026-04-01 18:20:18.226986-03	f	\N	7	10	31.62	2026-01-07	t	2026-01-07		\N	\N	67	\N
134	2026-03-22 22:49:55.399173-03	2026-04-01 18:20:18.227401-03	f	\N	8	10	31.62	2026-02-07	t	2026-02-07		\N	\N	67	\N
135	2026-03-22 22:49:55.399519-03	2026-04-01 18:20:18.228034-03	f	\N	9	10	31.62	2026-03-07	t	2026-03-07		\N	\N	67	\N
136	2026-03-22 22:49:55.399899-03	2026-04-01 18:20:18.228528-03	f	\N	10	10	31.62	2026-04-07	t	2026-04-07		\N	\N	67	\N
2477	2026-03-23 19:19:16.797962-03	2026-03-23 19:19:16.79797-03	f	\N	4	12	337.00	2025-12-23	t	2025-12-23		\N	\N	292	\N
2511	2026-03-23 19:23:06.105725-03	2026-03-23 19:23:06.105732-03	f	\N	1	10	165.90	2026-03-02	t	2026-03-02		3	\N	196	3
2512	2026-03-23 19:23:06.105807-03	2026-03-23 19:23:06.105809-03	f	\N	2	10	165.90	2026-03-30	f	\N		3	\N	196	3
2513	2026-03-23 19:23:06.105838-03	2026-03-23 19:23:06.10584-03	f	\N	3	10	165.90	2026-04-30	f	\N		3	\N	196	3
2514	2026-03-23 19:23:06.105871-03	2026-03-23 19:23:06.105873-03	f	\N	4	10	165.90	2026-05-30	f	\N		3	\N	196	3
2515	2026-03-23 19:23:06.105899-03	2026-03-23 19:23:06.105901-03	f	\N	5	10	165.90	2026-06-30	f	\N		3	\N	196	3
2516	2026-03-23 19:23:06.105925-03	2026-03-23 19:23:06.105927-03	f	\N	6	10	165.90	2026-07-30	f	\N		3	\N	196	3
2517	2026-03-23 19:23:06.105953-03	2026-03-23 19:23:06.105955-03	f	\N	7	10	165.90	2026-08-30	f	\N		3	\N	196	3
2518	2026-03-23 19:23:06.105979-03	2026-03-23 19:23:06.105981-03	f	\N	8	10	165.90	2026-09-30	f	\N		3	\N	196	3
2519	2026-03-23 19:23:06.106005-03	2026-03-23 19:23:06.106007-03	f	\N	9	10	165.90	2026-10-30	f	\N		3	\N	196	3
2520	2026-03-23 19:23:06.106031-03	2026-03-23 19:23:06.106033-03	f	\N	10	10	165.90	2026-11-30	f	\N		3	\N	196	3
2534	2026-03-23 19:24:35.782942-03	2026-03-23 19:24:35.782951-03	f	\N	6	10	100.00	2026-07-23	f	\N		\N	\N	294	\N
2544	2026-03-30 13:03:01.767422-03	2026-03-30 13:03:01.767425-03	f	\N	6	12	723.16	2026-05-01	t	2026-05-01		\N	\N	297	\N
183	2026-03-22 22:49:55.428855-03	2026-03-22 22:49:55.428857-03	f	\N	3	4	83.99	2026-04-07	f	\N		\N	\N	78	\N
184	2026-03-22 22:49:55.429306-03	2026-03-22 22:49:55.429308-03	f	\N	4	4	83.99	2026-05-07	f	\N		\N	\N	78	\N
186	2026-03-22 22:49:55.431039-03	2026-03-22 22:49:55.431041-03	f	\N	2	3	118.34	2026-03-07	t	2026-03-07		\N	\N	79	\N
187	2026-03-22 22:49:55.431524-03	2026-03-22 22:49:55.431526-03	f	\N	3	3	118.34	2026-04-07	f	\N		\N	\N	79	\N
191	2026-03-22 22:49:55.434336-03	2026-03-22 22:49:55.434338-03	f	\N	2	6	89.50	2026-04-07	f	\N		\N	\N	81	\N
192	2026-03-22 22:49:55.43473-03	2026-03-22 22:49:55.434731-03	f	\N	3	6	89.50	2026-05-07	f	\N		\N	\N	81	\N
193	2026-03-22 22:49:55.435125-03	2026-03-22 22:49:55.435127-03	f	\N	4	6	89.50	2026-06-07	f	\N		\N	\N	81	\N
194	2026-03-22 22:49:55.435514-03	2026-03-22 22:49:55.435516-03	f	\N	5	6	89.50	2026-07-07	f	\N		\N	\N	81	\N
195	2026-03-22 22:49:55.435934-03	2026-03-22 22:49:55.435936-03	f	\N	6	6	89.50	2026-08-07	f	\N		\N	\N	81	\N
197	2026-03-22 22:49:55.437602-03	2026-03-22 22:49:55.437604-03	f	\N	2	2	57.17	2026-04-07	f	\N		\N	\N	82	\N
199	2026-03-22 22:49:55.438902-03	2026-03-22 22:49:55.438904-03	f	\N	2	2	50.00	2026-04-07	f	\N		\N	\N	83	\N
201	2026-03-22 22:49:55.440294-03	2026-03-22 22:49:55.440296-03	f	\N	2	4	26.81	2026-04-07	f	\N		\N	\N	84	\N
202	2026-03-22 22:49:55.440724-03	2026-03-22 22:49:55.440726-03	f	\N	3	4	26.81	2026-05-07	f	\N		\N	\N	84	\N
203	2026-03-22 22:49:55.441236-03	2026-03-22 22:49:55.441238-03	f	\N	4	4	26.81	2026-06-07	f	\N		\N	\N	84	\N
205	2026-03-22 22:49:55.44272-03	2026-03-22 22:49:55.442722-03	f	\N	2	3	96.92	2026-04-07	f	\N		\N	\N	85	\N
206	2026-03-22 22:49:55.443206-03	2026-03-22 22:49:55.443208-03	f	\N	3	3	96.92	2026-05-07	f	\N		\N	\N	85	\N
208	2026-03-22 22:49:55.445033-03	2026-03-22 22:49:55.445035-03	f	\N	2	3	66.60	2026-04-07	f	\N		\N	\N	86	\N
209	2026-03-22 22:49:55.44551-03	2026-03-22 22:49:55.445512-03	f	\N	3	3	66.60	2026-05-07	f	\N		\N	\N	86	\N
211	2026-03-22 22:49:55.456642-03	2026-03-22 22:49:55.456644-03	f	\N	2	12	34.50	2025-12-07	t	2025-12-07		\N	\N	105	\N
212	2026-03-22 22:49:55.457035-03	2026-03-22 22:49:55.457037-03	f	\N	3	12	34.50	2026-01-07	t	2026-01-07		\N	\N	105	\N
213	2026-03-22 22:49:55.457431-03	2026-03-22 22:49:55.457433-03	f	\N	4	12	34.50	2026-02-07	t	2026-02-07		\N	\N	105	\N
214	2026-03-22 22:49:55.457869-03	2026-03-22 22:49:55.457871-03	f	\N	5	12	34.50	2026-03-07	t	2026-03-07		\N	\N	105	\N
215	2026-03-22 22:49:55.458327-03	2026-03-22 22:49:55.458329-03	f	\N	6	12	34.50	2026-04-07	f	\N		\N	\N	105	\N
216	2026-03-22 22:49:55.459017-03	2026-03-22 22:49:55.459019-03	f	\N	7	12	34.50	2026-05-07	f	\N		\N	\N	105	\N
217	2026-03-22 22:49:55.459578-03	2026-03-22 22:49:55.45958-03	f	\N	8	12	34.50	2026-06-07	f	\N		\N	\N	105	\N
218	2026-03-22 22:49:55.46012-03	2026-03-22 22:49:55.460122-03	f	\N	9	12	34.50	2026-07-07	f	\N		\N	\N	105	\N
219	2026-03-22 22:49:55.460562-03	2026-03-22 22:49:55.460564-03	f	\N	10	12	34.50	2026-08-07	f	\N		\N	\N	105	\N
220	2026-03-22 22:49:55.461032-03	2026-03-22 22:49:55.461034-03	f	\N	11	12	34.50	2026-09-07	f	\N		\N	\N	105	\N
221	2026-03-22 22:49:55.461457-03	2026-03-22 22:49:55.461459-03	f	\N	12	12	34.50	2026-10-07	f	\N		\N	\N	105	\N
223	2026-03-22 22:49:55.464568-03	2026-03-22 22:49:55.464569-03	f	\N	2	2	50.41	2026-02-16	t	2026-02-16		\N	\N	109	\N
225	2026-03-22 22:49:55.465894-03	2026-03-22 22:49:55.465896-03	f	\N	2	4	60.84	2026-02-16	t	2026-02-16		\N	\N	110	\N
226	2026-03-22 22:49:55.466336-03	2026-03-22 22:49:55.466338-03	f	\N	3	4	60.84	2026-03-16	f	\N		\N	\N	110	\N
227	2026-03-22 22:49:55.466779-03	2026-03-22 22:49:55.46678-03	f	\N	4	4	60.84	2026-04-16	f	\N		\N	\N	110	\N
229	2026-03-22 22:49:55.468147-03	2026-03-22 22:49:55.468149-03	f	\N	2	2	59.99	2026-02-16	t	2026-02-16		\N	\N	111	\N
231	2026-03-22 22:49:55.469689-03	2026-03-22 22:49:55.469691-03	f	\N	2	3	8.63	2026-01-16	t	2026-01-16		\N	\N	112	\N
232	2026-03-22 22:49:55.470221-03	2026-03-22 22:49:55.470223-03	f	\N	3	3	8.63	2026-02-16	t	2026-02-16		\N	\N	112	\N
234	2026-03-22 22:49:55.471725-03	2026-03-22 22:49:55.471727-03	f	\N	2	6	32.16	2026-02-16	t	2026-02-16		\N	\N	113	\N
235	2026-03-22 22:49:55.472127-03	2026-03-22 22:49:55.472129-03	f	\N	3	6	32.16	2026-03-16	f	\N		\N	\N	113	\N
236	2026-03-22 22:49:55.472761-03	2026-03-22 22:49:55.472763-03	f	\N	4	6	32.16	2026-04-16	f	\N		\N	\N	113	\N
237	2026-03-22 22:49:55.47314-03	2026-03-22 22:49:55.473142-03	f	\N	5	6	32.16	2026-05-16	f	\N		\N	\N	113	\N
238	2026-03-22 22:49:55.473584-03	2026-03-22 22:49:55.473587-03	f	\N	6	6	32.16	2026-06-16	f	\N		\N	\N	113	\N
240	2026-03-22 22:49:55.475421-03	2026-03-22 22:49:55.475423-03	f	\N	2	3	89.99	2026-02-16	t	2026-02-16		\N	\N	114	\N
241	2026-03-22 22:49:55.475817-03	2026-03-22 22:49:55.475819-03	f	\N	3	3	89.99	2026-03-16	f	\N		\N	\N	114	\N
243	2026-03-22 22:49:55.477356-03	2026-03-22 22:49:55.477358-03	f	\N	2	12	13.90	2025-11-16	t	2025-11-16		\N	\N	115	\N
244	2026-03-22 22:49:55.477845-03	2026-03-22 22:49:55.477847-03	f	\N	3	12	13.90	2025-12-16	t	2025-12-16		\N	\N	115	\N
245	2026-03-22 22:49:55.478512-03	2026-03-22 22:49:55.478514-03	f	\N	4	12	13.90	2026-01-16	t	2026-01-16		\N	\N	115	\N
246	2026-03-22 22:49:55.479021-03	2026-03-22 22:49:55.479023-03	f	\N	5	12	13.90	2026-02-16	t	2026-02-16		\N	\N	115	\N
247	2026-03-22 22:49:55.479637-03	2026-03-22 22:49:55.479638-03	f	\N	6	12	13.90	2026-03-16	f	\N		\N	\N	115	\N
248	2026-03-22 22:49:55.480114-03	2026-03-22 22:49:55.480116-03	f	\N	7	12	13.90	2026-04-16	f	\N		\N	\N	115	\N
249	2026-03-22 22:49:55.480648-03	2026-03-22 22:49:55.48065-03	f	\N	8	12	13.90	2026-05-16	f	\N		\N	\N	115	\N
250	2026-03-22 22:49:55.481072-03	2026-03-22 22:49:55.481073-03	f	\N	9	12	13.90	2026-06-16	f	\N		\N	\N	115	\N
251	2026-03-22 22:49:55.481523-03	2026-03-22 22:49:55.481526-03	f	\N	10	12	13.90	2026-07-16	f	\N		\N	\N	115	\N
252	2026-03-22 22:49:55.482045-03	2026-03-22 22:49:55.482047-03	f	\N	11	12	13.90	2026-08-16	f	\N		\N	\N	115	\N
253	2026-03-22 22:49:55.482616-03	2026-03-22 22:49:55.482618-03	f	\N	12	12	13.90	2026-09-16	f	\N		\N	\N	115	\N
255	2026-03-22 22:49:55.48446-03	2026-03-22 22:49:55.484462-03	f	\N	2	5	33.00	2025-11-16	t	2025-11-16		\N	\N	116	\N
256	2026-03-22 22:49:55.484932-03	2026-03-22 22:49:55.484933-03	f	\N	3	5	33.00	2025-12-16	t	2025-12-16		\N	\N	116	\N
257	2026-03-22 22:49:55.485389-03	2026-03-22 22:49:55.485391-03	f	\N	4	5	33.00	2026-01-16	t	2026-01-16		\N	\N	116	\N
258	2026-03-22 22:49:55.485796-03	2026-03-22 22:49:55.485797-03	f	\N	5	5	33.00	2026-02-16	t	2026-02-16		\N	\N	116	\N
260	2026-03-22 22:49:55.487264-03	2026-03-22 22:49:55.487266-03	f	\N	2	2	79.94	2026-02-16	t	2026-02-16		\N	\N	117	\N
262	2026-03-22 22:49:55.488962-03	2026-03-22 22:49:55.488964-03	f	\N	2	3	119.65	2026-02-16	t	2026-02-16		\N	\N	118	\N
263	2026-03-22 22:49:55.489482-03	2026-03-22 22:49:55.489483-03	f	\N	3	3	119.65	2026-03-16	f	\N		\N	\N	118	\N
265	2026-03-22 22:49:55.490994-03	2026-03-22 22:49:55.490995-03	f	\N	2	3	42.60	2026-02-16	t	2026-02-16		\N	\N	119	\N
266	2026-03-22 22:49:55.491412-03	2026-03-22 22:49:55.491414-03	f	\N	3	3	42.60	2026-03-16	f	\N		\N	\N	119	\N
268	2026-03-22 22:49:55.492864-03	2026-03-22 22:49:55.492866-03	f	\N	2	6	7.72	2026-02-16	t	2026-02-16		\N	\N	120	\N
2478	2026-03-23 19:19:16.872133-03	2026-03-23 19:19:16.872141-03	f	\N	5	12	337.00	2026-01-23	t	2026-01-23		\N	\N	292	\N
2521	2026-03-23 19:23:32.023372-03	2026-03-23 19:23:32.02338-03	f	\N	1	4	34.00	2026-03-02	t	2026-03-02		3	\N	197	3
2522	2026-03-23 19:23:32.023479-03	2026-03-23 19:23:32.023482-03	f	\N	2	4	34.00	2026-03-30	f	\N		3	\N	197	3
2523	2026-03-23 19:23:32.023524-03	2026-03-23 19:23:32.023527-03	f	\N	3	4	34.00	2026-04-30	f	\N		3	\N	197	3
2524	2026-03-23 19:23:32.023563-03	2026-03-23 19:23:32.023566-03	f	\N	4	4	34.00	2026-05-30	f	\N		3	\N	197	3
2535	2026-03-23 19:24:35.849427-03	2026-03-23 19:24:35.849437-03	f	\N	7	10	100.00	2026-08-23	f	\N		\N	\N	294	\N
2545	2026-03-30 13:03:01.815913-03	2026-03-30 13:03:01.81592-03	f	\N	7	12	723.16	2026-05-31	t	2026-05-31		\N	\N	297	\N
269	2026-03-22 22:49:55.493475-03	2026-03-22 22:49:55.493477-03	f	\N	3	6	7.72	2026-03-16	f	\N		\N	\N	120	\N
270	2026-03-22 22:49:55.494013-03	2026-03-22 22:49:55.494015-03	f	\N	4	6	7.72	2026-04-16	f	\N		\N	\N	120	\N
271	2026-03-22 22:49:55.494525-03	2026-03-22 22:49:55.494526-03	f	\N	5	6	7.72	2026-05-16	f	\N		\N	\N	120	\N
272	2026-03-22 22:49:55.495026-03	2026-03-22 22:49:55.495028-03	f	\N	6	6	7.72	2026-06-16	f	\N		\N	\N	120	\N
274	2026-03-22 22:49:55.497334-03	2026-03-22 22:49:55.497336-03	f	\N	2	2	58.45	2026-02-16	t	2026-02-16		\N	\N	121	\N
276	2026-03-22 22:49:55.498784-03	2026-03-22 22:49:55.498785-03	f	\N	2	5	31.80	2026-03-16	f	\N		\N	\N	122	\N
277	2026-03-22 22:49:55.499163-03	2026-03-22 22:49:55.499164-03	f	\N	3	5	31.80	2026-04-16	f	\N		\N	\N	122	\N
278	2026-03-22 22:49:55.49958-03	2026-03-22 22:49:55.499582-03	f	\N	4	5	31.80	2026-05-16	f	\N		\N	\N	122	\N
279	2026-03-22 22:49:55.499973-03	2026-03-22 22:49:55.499974-03	f	\N	5	5	31.80	2026-06-16	f	\N		\N	\N	122	\N
281	2026-03-22 22:49:55.501383-03	2026-03-22 22:49:55.501385-03	f	\N	2	2	44.85	2026-03-16	f	\N		\N	\N	123	\N
283	2026-03-22 22:49:55.50254-03	2026-03-22 22:49:55.502542-03	f	\N	2	5	67.22	2026-03-16	f	\N		\N	\N	124	\N
284	2026-03-22 22:49:55.503049-03	2026-03-22 22:49:55.503051-03	f	\N	3	5	67.22	2026-04-16	f	\N		\N	\N	124	\N
285	2026-03-22 22:49:55.503422-03	2026-03-22 22:49:55.503423-03	f	\N	4	5	67.22	2026-05-16	f	\N		\N	\N	124	\N
286	2026-03-22 22:49:55.503751-03	2026-03-22 22:49:55.503752-03	f	\N	5	5	67.22	2026-06-16	f	\N		\N	\N	124	\N
288	2026-03-22 22:49:55.504784-03	2026-03-22 22:49:55.504786-03	f	\N	2	3	115.02	2026-03-16	f	\N		\N	\N	125	\N
289	2026-03-22 22:49:55.505269-03	2026-03-22 22:49:55.505271-03	f	\N	3	3	115.02	2026-04-16	f	\N		\N	\N	125	\N
291	2026-03-22 22:49:55.506502-03	2026-03-22 22:49:55.506505-03	f	\N	2	2	99.88	2026-03-16	f	\N		\N	\N	126	\N
293	2026-03-22 22:49:55.507986-03	2026-03-22 22:49:55.507988-03	f	\N	2	3	61.97	2026-03-16	f	\N		\N	\N	127	\N
294	2026-03-22 22:49:55.508401-03	2026-03-22 22:49:55.508402-03	f	\N	3	3	61.97	2026-04-16	f	\N		\N	\N	127	\N
296	2026-03-22 22:49:55.509793-03	2026-03-22 22:49:55.509795-03	f	\N	2	4	38.01	2026-03-16	f	\N		\N	\N	128	\N
297	2026-03-22 22:49:55.510207-03	2026-03-22 22:49:55.510209-03	f	\N	3	4	38.01	2026-04-16	f	\N		\N	\N	128	\N
298	2026-03-22 22:49:55.510624-03	2026-03-22 22:49:55.510626-03	f	\N	4	4	38.01	2026-05-16	f	\N		\N	\N	128	\N
300	2026-03-22 22:49:55.511949-03	2026-03-22 22:49:55.511951-03	f	\N	2	5	80.00	2026-03-16	f	\N		\N	\N	129	\N
301	2026-03-22 22:49:55.512389-03	2026-03-22 22:49:55.512391-03	f	\N	3	5	80.00	2026-04-16	f	\N		\N	\N	129	\N
302	2026-03-22 22:49:55.5128-03	2026-03-22 22:49:55.512802-03	f	\N	4	5	80.00	2026-05-16	f	\N		\N	\N	129	\N
303	2026-03-22 22:49:55.513243-03	2026-03-22 22:49:55.513245-03	f	\N	5	5	80.00	2026-06-16	f	\N		\N	\N	129	\N
305	2026-03-22 22:49:55.514698-03	2026-03-22 22:49:55.5147-03	f	\N	2	2	57.47	2026-02-16	t	2026-02-16		\N	\N	130	\N
307	2026-03-22 22:49:55.516111-03	2026-03-22 22:49:55.516113-03	f	\N	2	2	62.14	2026-02-16	t	2026-02-16		\N	\N	131	\N
309	2026-03-22 22:49:55.51733-03	2026-03-22 22:49:55.517332-03	f	\N	2	3	355.87	2026-01-16	t	2026-01-16		\N	\N	132	\N
310	2026-03-22 22:49:55.517752-03	2026-03-22 22:49:55.517754-03	f	\N	3	3	355.87	2026-02-16	t	2026-02-16		\N	\N	132	\N
312	2026-03-22 22:49:55.519056-03	2026-03-22 22:49:55.519058-03	f	\N	2	2	56.43	2026-03-16	f	\N		\N	\N	133	\N
314	2026-03-22 22:49:55.520374-03	2026-03-22 22:49:55.520376-03	f	\N	2	2	50.95	2026-03-16	f	\N		\N	\N	134	\N
316	2026-03-22 22:49:55.522381-03	2026-03-22 22:49:55.522383-03	f	\N	2	3	94.66	2026-03-16	f	\N		\N	\N	135	\N
317	2026-03-22 22:49:55.523138-03	2026-03-22 22:49:55.523141-03	f	\N	3	3	94.66	2026-04-16	f	\N		\N	\N	135	\N
319	2026-03-22 22:49:55.539719-03	2026-03-22 22:49:55.539721-03	f	\N	2	12	55.28	2025-05-25	t	2025-05-25		\N	\N	161	\N
320	2026-03-22 22:49:55.540285-03	2026-03-22 22:49:55.540287-03	f	\N	3	12	55.28	2025-06-25	t	2025-06-25		\N	\N	161	\N
321	2026-03-22 22:49:55.540789-03	2026-03-22 22:49:55.540791-03	f	\N	4	12	55.28	2025-07-25	t	2025-07-25		\N	\N	161	\N
322	2026-03-22 22:49:55.54125-03	2026-03-22 22:49:55.541252-03	f	\N	5	12	55.28	2025-08-25	t	2025-08-25		\N	\N	161	\N
323	2026-03-22 22:49:55.541645-03	2026-03-22 22:49:55.541647-03	f	\N	6	12	55.28	2025-09-25	t	2025-09-25		\N	\N	161	\N
324	2026-03-22 22:49:55.542085-03	2026-03-22 22:49:55.542087-03	f	\N	7	12	55.28	2025-10-25	t	2025-10-25		\N	\N	161	\N
325	2026-03-22 22:49:55.542456-03	2026-03-22 22:49:55.542458-03	f	\N	8	12	55.28	2025-11-25	t	2025-11-25		\N	\N	161	\N
326	2026-03-22 22:49:55.542869-03	2026-03-22 22:49:55.542871-03	f	\N	9	12	55.28	2025-12-25	t	2025-12-25		\N	\N	161	\N
327	2026-03-22 22:49:55.543358-03	2026-03-22 22:49:55.54336-03	f	\N	10	12	55.28	2026-01-25	t	2026-01-25		\N	\N	161	\N
328	2026-03-22 22:49:55.544081-03	2026-03-22 22:49:55.544083-03	f	\N	11	12	55.28	2026-02-25	t	2026-02-25		\N	\N	161	\N
329	2026-03-22 22:49:55.544524-03	2026-03-22 22:49:55.544525-03	f	\N	12	12	55.28	2026-03-25	f	\N		\N	\N	161	\N
331	2026-03-22 22:49:55.545905-03	2026-03-22 22:49:55.545907-03	f	\N	2	10	46.33	2025-08-25	t	2025-08-25		\N	\N	162	\N
332	2026-03-22 22:49:55.546435-03	2026-03-22 22:49:55.546437-03	f	\N	3	10	46.33	2025-09-25	t	2025-09-25		\N	\N	162	\N
333	2026-03-22 22:49:55.546988-03	2026-03-22 22:49:55.54699-03	f	\N	4	10	46.33	2025-10-25	t	2025-10-25		\N	\N	162	\N
334	2026-03-22 22:49:55.547496-03	2026-03-22 22:49:55.547498-03	f	\N	5	10	46.33	2025-11-25	t	2025-11-25		\N	\N	162	\N
335	2026-03-22 22:49:55.547933-03	2026-03-22 22:49:55.547934-03	f	\N	6	10	46.33	2025-12-25	t	2025-12-25		\N	\N	162	\N
336	2026-03-22 22:49:55.54832-03	2026-03-22 22:49:55.548322-03	f	\N	7	10	46.33	2026-01-25	t	2026-01-25		\N	\N	162	\N
337	2026-03-22 22:49:55.548788-03	2026-03-22 22:49:55.54879-03	f	\N	8	10	46.33	2026-02-25	t	2026-02-25		\N	\N	162	\N
338	2026-03-22 22:49:55.549201-03	2026-03-22 22:49:55.549203-03	f	\N	9	10	46.33	2026-03-25	f	\N		\N	\N	162	\N
339	2026-03-22 22:49:55.549603-03	2026-03-22 22:49:55.549605-03	f	\N	10	10	46.33	2026-04-25	f	\N		\N	\N	162	\N
341	2026-03-22 22:49:55.550883-03	2026-03-22 22:49:55.550884-03	f	\N	2	6	109.05	2025-11-25	t	2025-11-25		\N	\N	163	\N
342	2026-03-22 22:49:55.551478-03	2026-03-22 22:49:55.55148-03	f	\N	3	6	109.05	2025-12-25	t	2025-12-25		\N	\N	163	\N
343	2026-03-22 22:49:55.551828-03	2026-03-22 22:49:55.551829-03	f	\N	4	6	109.05	2026-01-25	t	2026-01-25		\N	\N	163	\N
344	2026-03-22 22:49:55.552134-03	2026-03-22 22:49:55.552135-03	f	\N	5	6	109.05	2026-02-25	t	2026-02-25		\N	\N	163	\N
345	2026-03-22 22:49:55.552444-03	2026-03-22 22:49:55.552445-03	f	\N	6	6	109.05	2026-03-25	f	\N		\N	\N	163	\N
347	2026-03-22 22:49:55.553468-03	2026-03-22 22:49:55.553469-03	f	\N	2	5	122.50	2025-12-25	t	2025-12-25		\N	\N	164	\N
348	2026-03-22 22:49:55.553776-03	2026-03-22 22:49:55.553778-03	f	\N	3	5	122.50	2026-01-25	t	2026-01-25		\N	\N	164	\N
349	2026-03-22 22:49:55.554063-03	2026-03-22 22:49:55.554065-03	f	\N	4	5	122.50	2026-02-25	t	2026-02-25		\N	\N	164	\N
350	2026-03-22 22:49:55.554446-03	2026-03-22 22:49:55.554447-03	f	\N	5	5	122.50	2026-03-25	f	\N		\N	\N	164	\N
352	2026-03-22 22:49:55.555499-03	2026-03-22 22:49:55.555501-03	f	\N	2	3	86.94	2026-01-25	t	2026-01-25		\N	\N	165	\N
353	2026-03-22 22:49:55.55594-03	2026-03-22 22:49:55.555942-03	f	\N	3	3	86.94	2026-02-25	t	2026-02-25		\N	\N	165	\N
355	2026-03-22 22:49:55.557198-03	2026-03-22 22:49:55.5572-03	f	\N	2	3	188.14	2026-01-25	t	2026-01-25		\N	\N	166	\N
356	2026-03-22 22:49:55.557506-03	2026-03-22 22:49:55.557508-03	f	\N	3	3	188.14	2026-02-25	t	2026-02-25		\N	\N	166	\N
358	2026-03-22 22:49:55.558585-03	2026-03-22 22:49:55.558587-03	f	\N	2	6	55.04	2026-02-25	t	2026-02-25		\N	\N	167	\N
359	2026-03-22 22:49:55.559049-03	2026-03-22 22:49:55.559051-03	f	\N	3	6	55.04	2026-03-25	f	\N		\N	\N	167	\N
360	2026-03-22 22:49:55.559389-03	2026-03-22 22:49:55.559391-03	f	\N	4	6	55.04	2026-04-25	f	\N		\N	\N	167	\N
361	2026-03-22 22:49:55.559694-03	2026-03-22 22:49:55.559695-03	f	\N	5	6	55.04	2026-05-25	f	\N		\N	\N	167	\N
2479	2026-03-23 19:19:16.951087-03	2026-03-23 19:19:16.951094-03	f	\N	6	12	337.00	2026-02-23	t	2026-02-23		\N	\N	292	\N
2525	2026-03-23 19:24:00.246425-03	2026-03-23 19:24:00.246433-03	f	\N	1	4	250.00	2026-02-23	t	2026-02-23		\N	\N	293	\N
2536	2026-03-23 19:24:35.911301-03	2026-03-23 19:24:35.911312-03	f	\N	8	10	100.00	2026-09-23	f	\N		\N	\N	294	\N
2546	2026-03-30 13:03:01.862293-03	2026-03-30 13:03:01.862297-03	f	\N	8	12	723.16	2026-07-01	t	2026-07-01		\N	\N	297	\N
362	2026-03-22 22:49:55.559988-03	2026-03-22 22:49:55.55999-03	f	\N	6	6	55.04	2026-06-25	f	\N		\N	\N	167	\N
364	2026-03-22 22:49:55.561106-03	2026-03-22 22:49:55.561108-03	f	\N	2	2	43.51	2026-02-25	t	2026-02-25		\N	\N	168	\N
366	2026-03-22 22:49:55.562111-03	2026-03-22 22:49:55.562112-03	f	\N	2	7	57.00	2026-02-25	t	2026-02-25		\N	\N	169	\N
367	2026-03-22 22:49:55.562417-03	2026-03-22 22:49:55.562419-03	f	\N	3	7	57.00	2026-03-25	f	\N		\N	\N	169	\N
368	2026-03-22 22:49:55.562703-03	2026-03-22 22:49:55.562704-03	f	\N	4	7	57.00	2026-04-25	f	\N		\N	\N	169	\N
369	2026-03-22 22:49:55.562978-03	2026-03-22 22:49:55.562979-03	f	\N	5	7	57.00	2026-05-25	f	\N		\N	\N	169	\N
370	2026-03-22 22:49:55.563259-03	2026-03-22 22:49:55.563261-03	f	\N	6	7	57.00	2026-06-25	f	\N		\N	\N	169	\N
371	2026-03-22 22:49:55.563549-03	2026-03-22 22:49:55.563551-03	f	\N	7	7	57.00	2026-07-25	f	\N		\N	\N	169	\N
373	2026-03-22 22:49:55.564842-03	2026-03-22 22:49:55.564844-03	f	\N	2	7	70.96	2026-02-25	t	2026-02-25		\N	\N	170	\N
374	2026-03-22 22:49:55.565196-03	2026-03-22 22:49:55.565198-03	f	\N	3	7	70.96	2026-03-25	f	\N		\N	\N	170	\N
375	2026-03-22 22:49:55.565511-03	2026-03-22 22:49:55.565512-03	f	\N	4	7	70.96	2026-04-25	f	\N		\N	\N	170	\N
376	2026-03-22 22:49:55.56581-03	2026-03-22 22:49:55.565811-03	f	\N	5	7	70.96	2026-05-25	f	\N		\N	\N	170	\N
377	2026-03-22 22:49:55.566108-03	2026-03-22 22:49:55.56611-03	f	\N	6	7	70.96	2026-06-25	f	\N		\N	\N	170	\N
378	2026-03-22 22:49:55.566493-03	2026-03-22 22:49:55.566495-03	f	\N	7	7	70.96	2026-07-25	f	\N		\N	\N	170	\N
380	2026-03-22 22:49:55.568142-03	2026-03-22 22:49:55.568144-03	f	\N	2	3	128.00	2026-02-25	t	2026-02-25		\N	\N	171	\N
381	2026-03-22 22:49:55.568632-03	2026-03-22 22:49:55.568634-03	f	\N	3	3	128.00	2026-03-25	f	\N		\N	\N	171	\N
383	2026-03-22 22:49:55.570018-03	2026-03-22 22:49:55.57002-03	f	\N	2	12	23.90	2026-01-25	t	2026-01-25		\N	\N	172	\N
384	2026-03-22 22:49:55.570356-03	2026-03-22 22:49:55.570358-03	f	\N	3	12	23.90	2026-02-25	t	2026-02-25		\N	\N	172	\N
385	2026-03-22 22:49:55.570668-03	2026-03-22 22:49:55.57067-03	f	\N	4	12	23.90	2026-03-25	f	\N		\N	\N	172	\N
386	2026-03-22 22:49:55.571051-03	2026-03-22 22:49:55.571053-03	f	\N	5	12	23.90	2026-04-25	f	\N		\N	\N	172	\N
387	2026-03-22 22:49:55.571441-03	2026-03-22 22:49:55.571443-03	f	\N	6	12	23.90	2026-05-25	f	\N		\N	\N	172	\N
388	2026-03-22 22:49:55.571747-03	2026-03-22 22:49:55.571749-03	f	\N	7	12	23.90	2026-06-25	f	\N		\N	\N	172	\N
389	2026-03-22 22:49:55.572046-03	2026-03-22 22:49:55.572048-03	f	\N	8	12	23.90	2026-07-25	f	\N		\N	\N	172	\N
390	2026-03-22 22:49:55.572458-03	2026-03-22 22:49:55.57246-03	f	\N	9	12	23.90	2026-08-25	f	\N		\N	\N	172	\N
391	2026-03-22 22:49:55.572919-03	2026-03-22 22:49:55.572921-03	f	\N	10	12	23.90	2026-09-25	f	\N		\N	\N	172	\N
392	2026-03-22 22:49:55.573298-03	2026-03-22 22:49:55.5733-03	f	\N	11	12	23.90	2026-10-25	f	\N		\N	\N	172	\N
393	2026-03-22 22:49:55.573744-03	2026-03-22 22:49:55.573746-03	f	\N	12	12	23.90	2026-11-25	f	\N		\N	\N	172	\N
395	2026-03-22 22:49:55.575739-03	2026-03-22 22:49:55.57574-03	f	\N	2	15	29.40	2025-01-20	t	2025-01-20		\N	\N	175	\N
396	2026-03-22 22:49:55.576058-03	2026-03-22 22:49:55.57606-03	f	\N	3	15	29.40	2025-02-20	t	2025-02-20		\N	\N	175	\N
397	2026-03-22 22:49:55.576417-03	2026-03-22 22:49:55.576419-03	f	\N	4	15	29.40	2025-03-20	t	2025-03-20		\N	\N	175	\N
398	2026-03-22 22:49:55.576766-03	2026-03-22 22:49:55.576767-03	f	\N	5	15	29.40	2025-04-20	t	2025-04-20		\N	\N	175	\N
399	2026-03-22 22:49:55.577069-03	2026-03-22 22:49:55.577071-03	f	\N	6	15	29.40	2025-05-20	t	2025-05-20		\N	\N	175	\N
400	2026-03-22 22:49:55.577354-03	2026-03-22 22:49:55.577356-03	f	\N	7	15	29.40	2025-06-20	t	2025-06-20		\N	\N	175	\N
401	2026-03-22 22:49:55.577634-03	2026-03-22 22:49:55.577636-03	f	\N	8	15	29.40	2025-07-20	t	2025-07-20		\N	\N	175	\N
402	2026-03-22 22:49:55.57792-03	2026-03-22 22:49:55.577921-03	f	\N	9	15	29.40	2025-08-20	t	2025-08-20		\N	\N	175	\N
403	2026-03-22 22:49:55.578218-03	2026-03-22 22:49:55.57822-03	f	\N	10	15	29.40	2025-09-20	t	2025-09-20		\N	\N	175	\N
404	2026-03-22 22:49:55.578577-03	2026-03-22 22:49:55.578578-03	f	\N	11	15	29.40	2025-10-20	t	2025-10-20		\N	\N	175	\N
405	2026-03-22 22:49:55.578928-03	2026-03-22 22:49:55.57893-03	f	\N	12	15	29.40	2025-11-20	t	2025-11-20		\N	\N	175	\N
406	2026-03-22 22:49:55.579244-03	2026-03-22 22:49:55.579246-03	f	\N	13	15	29.40	2025-12-20	t	2025-12-20		\N	\N	175	\N
407	2026-03-22 22:49:55.579537-03	2026-03-22 22:49:55.579538-03	f	\N	14	15	29.40	2026-01-20	t	2026-01-20		\N	\N	175	\N
408	2026-03-22 22:49:55.579819-03	2026-03-22 22:49:55.57982-03	f	\N	15	15	29.40	2026-02-20	t	2026-02-20		\N	\N	175	\N
410	2026-03-22 22:49:55.581262-03	2026-03-22 22:49:55.581264-03	f	\N	2	18	30.00	2025-04-20	t	2025-04-20		\N	\N	176	\N
411	2026-03-22 22:49:55.581678-03	2026-03-22 22:49:55.58168-03	f	\N	3	18	30.00	2025-05-20	t	2025-05-20		\N	\N	176	\N
412	2026-03-22 22:49:55.582027-03	2026-03-22 22:49:55.582029-03	f	\N	4	18	30.00	2025-06-20	t	2025-06-20		\N	\N	176	\N
413	2026-03-22 22:49:55.582399-03	2026-03-22 22:49:55.582401-03	f	\N	5	18	30.00	2025-07-20	t	2025-07-20		\N	\N	176	\N
414	2026-03-22 22:49:55.582757-03	2026-03-22 22:49:55.582758-03	f	\N	6	18	30.00	2025-08-20	t	2025-08-20		\N	\N	176	\N
415	2026-03-22 22:49:55.583128-03	2026-03-22 22:49:55.58313-03	f	\N	7	18	30.00	2025-09-20	t	2025-09-20		\N	\N	176	\N
416	2026-03-22 22:49:55.583464-03	2026-03-22 22:49:55.583465-03	f	\N	8	18	30.00	2025-10-20	t	2025-10-20		\N	\N	176	\N
417	2026-03-22 22:49:55.58377-03	2026-03-22 22:49:55.583772-03	f	\N	9	18	30.00	2025-11-20	t	2025-11-20		\N	\N	176	\N
418	2026-03-22 22:49:55.584065-03	2026-03-22 22:49:55.584066-03	f	\N	10	18	30.00	2025-12-20	t	2025-12-20		\N	\N	176	\N
419	2026-03-22 22:49:55.584349-03	2026-03-22 22:49:55.584351-03	f	\N	11	18	30.00	2026-01-20	t	2026-01-20		\N	\N	176	\N
420	2026-03-22 22:49:55.584718-03	2026-03-22 22:49:55.58472-03	f	\N	12	18	30.00	2026-02-20	t	2026-02-20		\N	\N	176	\N
421	2026-03-22 22:49:55.585038-03	2026-03-22 22:49:55.58504-03	f	\N	13	18	30.00	2026-03-20	f	\N		\N	\N	176	\N
422	2026-03-22 22:49:55.58535-03	2026-03-22 22:49:55.585352-03	f	\N	14	18	30.00	2026-04-20	f	\N		\N	\N	176	\N
423	2026-03-22 22:49:55.585655-03	2026-03-22 22:49:55.585657-03	f	\N	15	18	30.00	2026-05-20	f	\N		\N	\N	176	\N
424	2026-03-22 22:49:55.58596-03	2026-03-22 22:49:55.585961-03	f	\N	16	18	30.00	2026-06-20	f	\N		\N	\N	176	\N
425	2026-03-22 22:49:55.586246-03	2026-03-22 22:49:55.586248-03	f	\N	17	18	30.00	2026-07-20	f	\N		\N	\N	176	\N
426	2026-03-22 22:49:55.586525-03	2026-03-22 22:49:55.586526-03	f	\N	18	18	30.00	2026-08-20	f	\N		\N	\N	176	\N
428	2026-03-22 22:49:55.587693-03	2026-03-22 22:49:55.587695-03	f	\N	2	10	67.00	2025-07-20	t	2025-07-20		\N	\N	177	\N
429	2026-03-22 22:49:55.588-03	2026-03-22 22:49:55.588002-03	f	\N	3	10	67.00	2025-08-20	t	2025-08-20		\N	\N	177	\N
430	2026-03-22 22:49:55.58834-03	2026-03-22 22:49:55.588341-03	f	\N	4	10	67.00	2025-09-20	t	2025-09-20		\N	\N	177	\N
431	2026-03-22 22:49:55.588632-03	2026-03-22 22:49:55.588633-03	f	\N	5	10	67.00	2025-10-20	t	2025-10-20		\N	\N	177	\N
432	2026-03-22 22:49:55.588958-03	2026-03-22 22:49:55.588959-03	f	\N	6	10	67.00	2025-11-20	t	2025-11-20		\N	\N	177	\N
433	2026-03-22 22:49:55.589288-03	2026-03-22 22:49:55.58929-03	f	\N	7	10	67.00	2025-12-20	t	2025-12-20		\N	\N	177	\N
434	2026-03-22 22:49:55.589583-03	2026-03-22 22:49:55.589585-03	f	\N	8	10	67.00	2026-01-20	t	2026-01-20		\N	\N	177	\N
435	2026-03-22 22:49:55.589865-03	2026-03-22 22:49:55.589867-03	f	\N	9	10	67.00	2026-02-20	t	2026-02-20		\N	\N	177	\N
436	2026-03-22 22:49:55.590141-03	2026-03-22 22:49:55.590143-03	f	\N	10	10	67.00	2026-03-20	f	\N		\N	\N	177	\N
438	2026-03-22 22:49:55.591162-03	2026-03-22 22:49:55.591164-03	f	\N	2	8	11.49	2025-09-20	t	2025-09-20		\N	\N	178	\N
439	2026-03-22 22:49:55.591461-03	2026-03-22 22:49:55.591463-03	f	\N	3	8	11.49	2025-10-20	t	2025-10-20		\N	\N	178	\N
440	2026-03-22 22:49:55.591763-03	2026-03-22 22:49:55.591764-03	f	\N	4	8	11.49	2025-11-20	t	2025-11-20		\N	\N	178	\N
441	2026-03-22 22:49:55.592051-03	2026-03-22 22:49:55.592052-03	f	\N	5	8	11.49	2025-12-20	t	2025-12-20		\N	\N	178	\N
442	2026-03-22 22:49:55.592332-03	2026-03-22 22:49:55.592333-03	f	\N	6	8	11.49	2026-01-20	t	2026-01-20		\N	\N	178	\N
443	2026-03-22 22:49:55.592611-03	2026-03-22 22:49:55.592613-03	f	\N	7	8	11.49	2026-02-20	t	2026-02-20		\N	\N	178	\N
2480	2026-03-23 19:19:17.018326-03	2026-03-23 19:19:17.018334-03	f	\N	7	12	337.00	2026-03-23	f	\N		\N	\N	292	\N
2526	2026-03-23 19:24:00.328988-03	2026-03-23 19:24:00.328996-03	f	\N	2	4	250.00	2026-03-23	f	\N		\N	\N	293	\N
2537	2026-03-23 19:24:35.98064-03	2026-03-23 19:24:35.980648-03	f	\N	9	10	100.00	2026-10-23	f	\N		\N	\N	294	\N
2547	2026-03-30 13:03:01.909912-03	2026-03-30 13:03:01.909918-03	f	\N	9	12	723.16	2026-07-31	f	\N		\N	\N	297	\N
2559	2026-04-01 14:03:33.235404-03	2026-04-01 14:03:33.235407-03	f	\N	2	12	63.33	2026-02-01	t	2026-02-01		\N	\N	305	\N
2572	2026-04-01 14:10:02.242873-03	2026-04-01 14:10:02.242876-03	f	\N	3	6	66.70	2026-05-02	f	\N		\N	\N	306	\N
2584	2026-04-01 14:10:37.757224-03	2026-04-01 14:10:37.757228-03	f	\N	9	10	125.00	2026-10-02	f	\N		\N	\N	307	\N
2200	2026-03-23 19:17:45.285627-03	2026-03-23 19:17:45.28563-03	t	2026-04-01 15:03:39.725269-03	259	510	90.00	2047-03-30	f	\N		3	\N	190	3
2116	2026-03-23 19:17:45.28271-03	2026-03-23 19:17:45.282713-03	t	2026-04-01 15:03:39.725269-03	175	510	90.00	2040-03-30	f	\N		3	\N	190	3
1979	2026-03-23 19:17:45.278444-03	2026-03-23 19:17:45.278445-03	t	2026-04-01 15:03:39.725269-03	38	510	90.00	2028-10-30	f	\N		3	\N	190	3
2351	2026-03-23 19:17:45.290214-03	2026-03-23 19:17:45.290217-03	t	2026-04-01 15:03:39.725269-03	410	510	90.00	2059-10-30	f	\N		3	\N	190	3
1975	2026-03-23 19:17:45.278379-03	2026-03-23 19:17:45.27838-03	t	2026-04-01 15:03:39.725269-03	34	510	90.00	2028-06-30	f	\N		3	\N	190	3
1970	2026-03-23 19:17:45.278296-03	2026-03-23 19:17:45.278297-03	t	2026-04-01 15:03:39.725269-03	29	510	90.00	2028-01-30	f	\N		3	\N	190	3
1982	2026-03-23 19:17:45.278493-03	2026-03-23 19:17:45.278494-03	t	2026-04-01 15:03:39.725269-03	41	510	90.00	2029-01-30	f	\N		3	\N	190	3
2183	2026-03-23 19:17:45.285081-03	2026-03-23 19:17:45.285083-03	t	2026-04-01 15:03:39.725269-03	242	510	90.00	2045-10-30	f	\N		3	\N	190	3
1942	2026-03-23 19:17:45.277741-03	2026-03-23 19:17:45.277746-03	t	2026-04-01 15:03:39.725269-03	1	510	90.00	2025-09-30	t	2025-09-30		3	\N	190	3
1992	2026-03-23 19:17:45.278656-03	2026-03-23 19:17:45.278657-03	t	2026-04-01 15:03:39.725269-03	51	510	90.00	2029-11-30	f	\N		3	\N	190	3
2397	2026-03-23 19:17:45.291825-03	2026-03-23 19:17:45.291828-03	t	2026-04-01 15:03:39.725269-03	456	510	90.00	2063-08-30	f	\N		3	\N	190	3
2296	2026-03-23 19:17:45.288614-03	2026-03-23 19:17:45.288615-03	t	2026-04-01 15:03:39.725269-03	355	510	90.00	2055-03-30	f	\N		3	\N	190	3
2275	2026-03-23 19:17:45.288149-03	2026-03-23 19:17:45.288152-03	t	2026-04-01 15:03:39.725269-03	334	510	90.00	2053-06-30	f	\N		3	\N	190	3
1059	2026-03-22 22:49:55.882147-03	2026-03-22 22:49:55.882149-03	f	\N	1	6	349.00	2026-01-30	t	2026-01-30		\N	\N	194	\N
1060	2026-03-22 22:49:55.882523-03	2026-03-22 22:49:55.882525-03	f	\N	2	6	349.00	2026-02-28	t	2026-02-28		\N	\N	194	\N
1061	2026-03-22 22:49:55.882908-03	2026-03-22 22:49:55.88291-03	f	\N	3	6	349.00	2026-03-30	t	2026-03-30		\N	\N	194	\N
1062	2026-03-22 22:49:55.883251-03	2026-03-22 22:49:55.883252-03	f	\N	4	6	349.00	2026-04-30	f	\N		\N	\N	194	\N
1063	2026-03-22 22:49:55.883567-03	2026-03-22 22:49:55.883569-03	f	\N	5	6	349.00	2026-05-30	f	\N		\N	\N	194	\N
1064	2026-03-22 22:49:55.883898-03	2026-03-22 22:49:55.8839-03	f	\N	6	6	349.00	2026-06-30	f	\N		\N	\N	194	\N
2470	2026-03-23 19:18:06.218504-03	2026-03-23 19:18:06.218507-03	t	2026-04-01 15:03:39.725269-03	7	10	106.00	2026-04-30	f	\N		3	\N	192	3
2023	2026-03-23 19:17:45.27948-03	2026-03-23 19:17:45.279482-03	t	2026-04-01 15:03:39.725269-03	82	510	90.00	2032-06-30	f	\N		3	\N	190	3
2167	2026-03-23 19:17:45.284546-03	2026-03-23 19:17:45.284549-03	t	2026-04-01 15:03:39.725269-03	226	510	90.00	2044-06-30	f	\N		3	\N	190	3
2045	2026-03-23 19:17:45.280189-03	2026-03-23 19:17:45.280191-03	t	2026-04-01 15:03:39.725269-03	104	510	90.00	2034-04-30	f	\N		3	\N	190	3
2140	2026-03-23 19:17:45.28353-03	2026-03-23 19:17:45.283532-03	t	2026-04-01 15:03:39.725269-03	199	510	90.00	2042-03-30	f	\N		3	\N	190	3
1967	2026-03-23 19:17:45.278246-03	2026-03-23 19:17:45.278247-03	t	2026-04-01 15:03:39.725269-03	26	510	90.00	2027-10-30	f	\N		3	\N	190	3
1086	2026-03-22 22:49:55.898596-03	2026-03-22 22:49:55.898598-03	f	\N	1	5	57.73	2026-04-30	f	\N		\N	\N	198	\N
1087	2026-03-22 22:49:55.899047-03	2026-03-22 22:49:55.899049-03	f	\N	2	5	57.73	2026-05-30	f	\N		\N	\N	198	\N
1088	2026-03-22 22:49:55.899481-03	2026-03-22 22:49:55.899483-03	f	\N	3	5	57.73	2026-06-30	f	\N		\N	\N	198	\N
1089	2026-03-22 22:49:55.899835-03	2026-03-22 22:49:55.899837-03	f	\N	4	5	57.73	2026-07-30	f	\N		\N	\N	198	\N
1090	2026-03-22 22:49:55.900312-03	2026-03-22 22:49:55.900314-03	f	\N	5	5	57.73	2026-08-30	f	\N		\N	\N	198	\N
1091	2026-03-22 22:49:55.901288-03	2026-03-22 22:49:55.90129-03	f	\N	1	10	100.00	2026-04-30	f	\N		\N	\N	199	\N
1092	2026-03-22 22:49:55.901651-03	2026-03-22 22:49:55.901653-03	f	\N	2	10	100.00	2026-05-30	f	\N		\N	\N	199	\N
1093	2026-03-22 22:49:55.902034-03	2026-03-22 22:49:55.902036-03	f	\N	3	10	100.00	2026-06-30	f	\N		\N	\N	199	\N
1094	2026-03-22 22:49:55.902463-03	2026-03-22 22:49:55.902465-03	f	\N	4	10	100.00	2026-07-30	f	\N		\N	\N	199	\N
1095	2026-03-22 22:49:55.902901-03	2026-03-22 22:49:55.902903-03	f	\N	5	10	100.00	2026-08-30	f	\N		\N	\N	199	\N
1096	2026-03-22 22:49:55.90327-03	2026-03-22 22:49:55.903272-03	f	\N	6	10	100.00	2026-09-30	f	\N		\N	\N	199	\N
1097	2026-03-22 22:49:55.903653-03	2026-03-22 22:49:55.903655-03	f	\N	7	10	100.00	2026-10-30	f	\N		\N	\N	199	\N
1098	2026-03-22 22:49:55.904122-03	2026-03-22 22:49:55.904124-03	f	\N	8	10	100.00	2026-11-30	f	\N		\N	\N	199	\N
1099	2026-03-22 22:49:55.904529-03	2026-03-22 22:49:55.90453-03	f	\N	9	10	100.00	2026-12-30	f	\N		\N	\N	199	\N
1100	2026-03-22 22:49:55.904914-03	2026-03-22 22:49:55.904916-03	f	\N	10	10	100.00	2027-01-30	f	\N		\N	\N	199	\N
1101	2026-03-22 22:49:55.905949-03	2026-03-22 22:49:55.905951-03	f	\N	1	10	124.50	2026-04-30	f	\N		\N	\N	200	\N
1102	2026-03-22 22:49:55.906347-03	2026-03-22 22:49:55.906348-03	f	\N	2	10	124.50	2026-05-30	f	\N		\N	\N	200	\N
1103	2026-03-22 22:49:55.906709-03	2026-03-22 22:49:55.906711-03	f	\N	3	10	124.50	2026-06-30	f	\N		\N	\N	200	\N
1104	2026-03-22 22:49:55.907043-03	2026-03-22 22:49:55.907044-03	f	\N	4	10	124.50	2026-07-30	f	\N		\N	\N	200	\N
1105	2026-03-22 22:49:55.907393-03	2026-03-22 22:49:55.907394-03	f	\N	5	10	124.50	2026-08-30	f	\N		\N	\N	200	\N
1106	2026-03-22 22:49:55.90773-03	2026-03-22 22:49:55.907732-03	f	\N	6	10	124.50	2026-09-30	f	\N		\N	\N	200	\N
1107	2026-03-22 22:49:55.908232-03	2026-03-22 22:49:55.908234-03	f	\N	7	10	124.50	2026-10-30	f	\N		\N	\N	200	\N
1108	2026-03-22 22:49:55.90867-03	2026-03-22 22:49:55.908672-03	f	\N	8	10	124.50	2026-11-30	f	\N		\N	\N	200	\N
1109	2026-03-22 22:49:55.909103-03	2026-03-22 22:49:55.909104-03	f	\N	9	10	124.50	2026-12-30	f	\N		\N	\N	200	\N
1110	2026-03-22 22:49:55.909494-03	2026-03-22 22:49:55.909495-03	f	\N	10	10	124.50	2027-01-30	f	\N		\N	\N	200	\N
1111	2026-03-22 22:49:55.910288-03	2026-03-22 22:49:55.91029-03	f	\N	1	5	227.78	2026-04-30	f	\N		\N	\N	201	\N
1112	2026-03-22 22:49:55.910632-03	2026-03-22 22:49:55.910633-03	f	\N	2	5	227.78	2026-05-30	f	\N		\N	\N	201	\N
1113	2026-03-22 22:49:55.910993-03	2026-03-22 22:49:55.910995-03	f	\N	3	5	227.78	2026-06-30	f	\N		\N	\N	201	\N
1114	2026-03-22 22:49:55.911421-03	2026-03-22 22:49:55.911423-03	f	\N	4	5	227.78	2026-07-30	f	\N		\N	\N	201	\N
1115	2026-03-22 22:49:55.911801-03	2026-03-22 22:49:55.911803-03	f	\N	5	5	227.78	2026-08-30	f	\N		\N	\N	201	\N
1116	2026-03-22 22:49:55.912651-03	2026-03-22 22:49:55.912653-03	f	\N	1	2	96.50	2026-03-10	f	\N		\N	\N	202	\N
1117	2026-03-22 22:49:55.912979-03	2026-03-22 22:49:55.91298-03	f	\N	2	2	96.50	2026-04-10	f	\N		\N	\N	202	\N
1118	2026-03-22 22:49:55.914387-03	2026-03-22 22:49:55.91441-03	f	\N	1	9	102.78	2026-03-10	f	\N		\N	\N	204	\N
444	2026-03-22 22:49:55.592908-03	2026-03-22 22:49:55.592909-03	f	\N	8	8	11.49	2026-03-20	f	\N		\N	\N	178	\N
446	2026-03-22 22:49:55.593885-03	2026-03-22 22:49:55.593886-03	f	\N	2	6	19.98	2026-01-20	t	2026-01-20		\N	\N	179	\N
447	2026-03-22 22:49:55.594183-03	2026-03-22 22:49:55.594185-03	f	\N	3	6	19.98	2026-02-20	t	2026-02-20		\N	\N	179	\N
448	2026-03-22 22:49:55.594485-03	2026-03-22 22:49:55.594487-03	f	\N	4	6	19.98	2026-03-20	f	\N		\N	\N	179	\N
449	2026-03-22 22:49:55.594773-03	2026-03-22 22:49:55.594775-03	f	\N	5	6	19.98	2026-04-20	f	\N		\N	\N	179	\N
450	2026-03-22 22:49:55.595054-03	2026-03-22 22:49:55.595056-03	f	\N	6	6	19.98	2026-05-20	f	\N		\N	\N	179	\N
452	2026-03-22 22:49:55.596037-03	2026-03-22 22:49:55.596039-03	f	\N	2	8	21.75	2026-01-20	t	2026-01-20		\N	\N	180	\N
453	2026-03-22 22:49:55.596332-03	2026-03-22 22:49:55.596334-03	f	\N	3	8	21.75	2026-02-20	t	2026-02-20		\N	\N	180	\N
454	2026-03-22 22:49:55.596615-03	2026-03-22 22:49:55.596616-03	f	\N	4	8	21.75	2026-03-20	f	\N		\N	\N	180	\N
455	2026-03-22 22:49:55.596894-03	2026-03-22 22:49:55.596896-03	f	\N	5	8	21.75	2026-04-20	f	\N		\N	\N	180	\N
1119	2026-03-22 22:49:55.915071-03	2026-03-22 22:49:55.915073-03	f	\N	2	9	102.78	2026-04-10	f	\N		\N	\N	204	\N
1120	2026-03-22 22:49:55.915475-03	2026-03-22 22:49:55.915477-03	f	\N	3	9	102.78	2026-05-10	f	\N		\N	\N	204	\N
1121	2026-03-22 22:49:55.915869-03	2026-03-22 22:49:55.915871-03	f	\N	4	9	102.78	2026-06-10	f	\N		\N	\N	204	\N
1122	2026-03-22 22:49:55.916377-03	2026-03-22 22:49:55.916379-03	f	\N	5	9	102.78	2026-07-10	f	\N		\N	\N	204	\N
1123	2026-03-22 22:49:55.916784-03	2026-03-22 22:49:55.916786-03	f	\N	6	9	102.78	2026-08-10	f	\N		\N	\N	204	\N
1124	2026-03-22 22:49:55.917123-03	2026-03-22 22:49:55.917124-03	f	\N	7	9	102.78	2026-09-10	f	\N		\N	\N	204	\N
1125	2026-03-22 22:49:55.917586-03	2026-03-22 22:49:55.917588-03	f	\N	8	9	102.78	2026-10-10	f	\N		\N	\N	204	\N
1126	2026-03-22 22:49:55.918056-03	2026-03-22 22:49:55.918058-03	f	\N	9	9	102.78	2026-11-10	f	\N		\N	\N	204	\N
1127	2026-03-22 22:49:55.919045-03	2026-03-22 22:49:55.919048-03	f	\N	1	14	103.00	2026-03-10	f	\N		\N	\N	205	\N
1128	2026-03-22 22:49:55.91973-03	2026-03-22 22:49:55.919732-03	f	\N	2	14	103.00	2026-04-10	f	\N		\N	\N	205	\N
1129	2026-03-22 22:49:55.920323-03	2026-03-22 22:49:55.920324-03	f	\N	3	14	103.00	2026-05-10	f	\N		\N	\N	205	\N
1130	2026-03-22 22:49:55.920817-03	2026-03-22 22:49:55.920819-03	f	\N	4	14	103.00	2026-06-10	f	\N		\N	\N	205	\N
1131	2026-03-22 22:49:55.921202-03	2026-03-22 22:49:55.921204-03	f	\N	5	14	103.00	2026-07-10	f	\N		\N	\N	205	\N
1132	2026-03-22 22:49:55.921603-03	2026-03-22 22:49:55.921605-03	f	\N	6	14	103.00	2026-08-10	f	\N		\N	\N	205	\N
1133	2026-03-22 22:49:55.922046-03	2026-03-22 22:49:55.922048-03	f	\N	7	14	103.00	2026-09-10	f	\N		\N	\N	205	\N
1134	2026-03-22 22:49:55.922509-03	2026-03-22 22:49:55.922512-03	f	\N	8	14	103.00	2026-10-10	f	\N		\N	\N	205	\N
1135	2026-03-22 22:49:55.923382-03	2026-03-22 22:49:55.923386-03	f	\N	9	14	103.00	2026-11-10	f	\N		\N	\N	205	\N
1136	2026-03-22 22:49:55.923905-03	2026-03-22 22:49:55.923907-03	f	\N	10	14	103.00	2026-12-10	f	\N		\N	\N	205	\N
1137	2026-03-22 22:49:55.924299-03	2026-03-22 22:49:55.924301-03	f	\N	11	14	103.00	2027-01-10	f	\N		\N	\N	205	\N
1138	2026-03-22 22:49:55.924677-03	2026-03-22 22:49:55.924679-03	f	\N	12	14	103.00	2027-02-10	f	\N		\N	\N	205	\N
1139	2026-03-22 22:49:55.925016-03	2026-03-22 22:49:55.925018-03	f	\N	13	14	103.00	2027-03-10	f	\N		\N	\N	205	\N
1140	2026-03-22 22:49:55.925334-03	2026-03-22 22:49:55.925336-03	f	\N	14	14	103.00	2027-04-10	f	\N		\N	\N	205	\N
1141	2026-03-22 22:49:55.926215-03	2026-03-22 22:49:55.926217-03	f	\N	1	14	93.00	2026-03-10	f	\N		\N	\N	206	\N
1142	2026-03-22 22:49:55.926576-03	2026-03-22 22:49:55.926578-03	f	\N	2	14	93.00	2026-04-10	f	\N		\N	\N	206	\N
1143	2026-03-22 22:49:55.926897-03	2026-03-22 22:49:55.926899-03	f	\N	3	14	93.00	2026-05-10	f	\N		\N	\N	206	\N
1144	2026-03-22 22:49:55.92726-03	2026-03-22 22:49:55.927262-03	f	\N	4	14	93.00	2026-06-10	f	\N		\N	\N	206	\N
1145	2026-03-22 22:49:55.927588-03	2026-03-22 22:49:55.92759-03	f	\N	5	14	93.00	2026-07-10	f	\N		\N	\N	206	\N
1146	2026-03-22 22:49:55.927872-03	2026-03-22 22:49:55.927874-03	f	\N	6	14	93.00	2026-08-10	f	\N		\N	\N	206	\N
1147	2026-03-22 22:49:55.928147-03	2026-03-22 22:49:55.928149-03	f	\N	7	14	93.00	2026-09-10	f	\N		\N	\N	206	\N
1148	2026-03-22 22:49:55.928447-03	2026-03-22 22:49:55.928449-03	f	\N	8	14	93.00	2026-10-10	f	\N		\N	\N	206	\N
1149	2026-03-22 22:49:55.928744-03	2026-03-22 22:49:55.928746-03	f	\N	9	14	93.00	2026-11-10	f	\N		\N	\N	206	\N
1150	2026-03-22 22:49:55.929025-03	2026-03-22 22:49:55.929027-03	f	\N	10	14	93.00	2026-12-10	f	\N		\N	\N	206	\N
1151	2026-03-22 22:49:55.929303-03	2026-03-22 22:49:55.929305-03	f	\N	11	14	93.00	2027-01-10	f	\N		\N	\N	206	\N
1152	2026-03-22 22:49:55.929574-03	2026-03-22 22:49:55.929575-03	f	\N	12	14	93.00	2027-02-10	f	\N		\N	\N	206	\N
1153	2026-03-22 22:49:55.92995-03	2026-03-22 22:49:55.929952-03	f	\N	13	14	93.00	2027-03-10	f	\N		\N	\N	206	\N
1154	2026-03-22 22:49:55.930304-03	2026-03-22 22:49:55.930306-03	f	\N	14	14	93.00	2027-04-10	f	\N		\N	\N	206	\N
1155	2026-03-22 22:49:55.931139-03	2026-03-22 22:49:55.931141-03	f	\N	1	8	134.00	2026-03-10	f	\N		\N	\N	207	\N
1156	2026-03-22 22:49:55.931471-03	2026-03-22 22:49:55.931473-03	f	\N	2	8	134.00	2026-04-10	f	\N		\N	\N	207	\N
1157	2026-03-22 22:49:55.93177-03	2026-03-22 22:49:55.931771-03	f	\N	3	8	134.00	2026-05-10	f	\N		\N	\N	207	\N
1158	2026-03-22 22:49:55.932053-03	2026-03-22 22:49:55.932055-03	f	\N	4	8	134.00	2026-06-10	f	\N		\N	\N	207	\N
1159	2026-03-22 22:49:55.93234-03	2026-03-22 22:49:55.932342-03	f	\N	5	8	134.00	2026-07-10	f	\N		\N	\N	207	\N
1160	2026-03-22 22:49:55.932638-03	2026-03-22 22:49:55.93264-03	f	\N	6	8	134.00	2026-08-10	f	\N		\N	\N	207	\N
1161	2026-03-22 22:49:55.932926-03	2026-03-22 22:49:55.932927-03	f	\N	7	8	134.00	2026-09-10	f	\N		\N	\N	207	\N
1162	2026-03-22 22:49:55.933217-03	2026-03-22 22:49:55.933219-03	f	\N	8	8	134.00	2026-10-10	f	\N		\N	\N	207	\N
1163	2026-03-22 22:49:55.933973-03	2026-03-22 22:49:55.933975-03	f	\N	1	8	72.00	2026-03-10	f	\N		\N	\N	208	\N
1164	2026-03-22 22:49:55.93438-03	2026-03-22 22:49:55.934382-03	f	\N	2	8	72.00	2026-04-10	f	\N		\N	\N	208	\N
1165	2026-03-22 22:49:55.934802-03	2026-03-22 22:49:55.934804-03	f	\N	3	8	72.00	2026-05-10	f	\N		\N	\N	208	\N
1166	2026-03-22 22:49:55.935216-03	2026-03-22 22:49:55.935217-03	f	\N	4	8	72.00	2026-06-10	f	\N		\N	\N	208	\N
1167	2026-03-22 22:49:55.935555-03	2026-03-22 22:49:55.935557-03	f	\N	5	8	72.00	2026-07-10	f	\N		\N	\N	208	\N
1168	2026-03-22 22:49:55.935865-03	2026-03-22 22:49:55.935867-03	f	\N	6	8	72.00	2026-08-10	f	\N		\N	\N	208	\N
1169	2026-03-22 22:49:55.936176-03	2026-03-22 22:49:55.936177-03	f	\N	7	8	72.00	2026-09-10	f	\N		\N	\N	208	\N
1170	2026-03-22 22:49:55.936466-03	2026-03-22 22:49:55.936468-03	f	\N	8	8	72.00	2026-10-10	f	\N		\N	\N	208	\N
1171	2026-03-22 22:49:55.937171-03	2026-03-22 22:49:55.937173-03	f	\N	1	7	163.90	2026-03-10	f	\N		\N	\N	209	\N
1172	2026-03-22 22:49:55.937486-03	2026-03-22 22:49:55.937488-03	f	\N	2	7	163.90	2026-04-10	f	\N		\N	\N	209	\N
1173	2026-03-22 22:49:55.938229-03	2026-03-22 22:49:55.938231-03	f	\N	3	7	163.90	2026-05-10	f	\N		\N	\N	209	\N
1174	2026-03-22 22:49:55.938684-03	2026-03-22 22:49:55.938685-03	f	\N	4	7	163.90	2026-06-10	f	\N		\N	\N	209	\N
1175	2026-03-22 22:49:55.93911-03	2026-03-22 22:49:55.939112-03	f	\N	5	7	163.90	2026-07-10	f	\N		\N	\N	209	\N
1176	2026-03-22 22:49:55.939524-03	2026-03-22 22:49:55.939526-03	f	\N	6	7	163.90	2026-08-10	f	\N		\N	\N	209	\N
1177	2026-03-22 22:49:55.939927-03	2026-03-22 22:49:55.939929-03	f	\N	7	7	163.90	2026-09-10	f	\N		\N	\N	209	\N
1178	2026-03-22 22:49:55.940839-03	2026-03-22 22:49:55.940842-03	f	\N	1	7	188.00	2026-03-10	f	\N		\N	\N	210	\N
1179	2026-03-22 22:49:55.941276-03	2026-03-22 22:49:55.941278-03	f	\N	2	7	188.00	2026-04-10	f	\N		\N	\N	210	\N
1180	2026-03-22 22:49:55.941771-03	2026-03-22 22:49:55.941773-03	f	\N	3	7	188.00	2026-05-10	f	\N		\N	\N	210	\N
1181	2026-03-22 22:49:55.942205-03	2026-03-22 22:49:55.942206-03	f	\N	4	7	188.00	2026-06-10	f	\N		\N	\N	210	\N
1182	2026-03-22 22:49:55.942615-03	2026-03-22 22:49:55.942617-03	f	\N	5	7	188.00	2026-07-10	f	\N		\N	\N	210	\N
1183	2026-03-22 22:49:55.94304-03	2026-03-22 22:49:55.943042-03	f	\N	6	7	188.00	2026-08-10	f	\N		\N	\N	210	\N
1184	2026-03-22 22:49:55.943471-03	2026-03-22 22:49:55.943473-03	f	\N	7	7	188.00	2026-09-10	f	\N		\N	\N	210	\N
1185	2026-03-22 22:49:55.944411-03	2026-03-22 22:49:55.944413-03	f	\N	1	10	45.00	2026-03-10	f	\N		\N	\N	211	\N
1186	2026-03-22 22:49:55.944813-03	2026-03-22 22:49:55.944814-03	f	\N	2	10	45.00	2026-04-10	f	\N		\N	\N	211	\N
1187	2026-03-22 22:49:55.945201-03	2026-03-22 22:49:55.945203-03	f	\N	3	10	45.00	2026-05-10	f	\N		\N	\N	211	\N
1188	2026-03-22 22:49:55.945573-03	2026-03-22 22:49:55.945575-03	f	\N	4	10	45.00	2026-06-10	f	\N		\N	\N	211	\N
1189	2026-03-22 22:49:55.945996-03	2026-03-22 22:49:55.945998-03	f	\N	5	10	45.00	2026-07-10	f	\N		\N	\N	211	\N
1190	2026-03-22 22:49:55.94648-03	2026-03-22 22:49:55.946482-03	f	\N	6	10	45.00	2026-08-10	f	\N		\N	\N	211	\N
1191	2026-03-22 22:49:55.946918-03	2026-03-22 22:49:55.94692-03	f	\N	7	10	45.00	2026-09-10	f	\N		\N	\N	211	\N
1192	2026-03-22 22:49:55.947387-03	2026-03-22 22:49:55.947389-03	f	\N	8	10	45.00	2026-10-10	f	\N		\N	\N	211	\N
1193	2026-03-22 22:49:55.94782-03	2026-03-22 22:49:55.947822-03	f	\N	9	10	45.00	2026-11-10	f	\N		\N	\N	211	\N
1194	2026-03-22 22:49:55.948248-03	2026-03-22 22:49:55.94825-03	f	\N	10	10	45.00	2026-12-10	f	\N		\N	\N	211	\N
1195	2026-03-22 22:49:55.949681-03	2026-03-22 22:49:55.949683-03	f	\N	1	8	62.05	2026-03-10	f	\N		\N	\N	213	\N
1196	2026-03-22 22:49:55.950057-03	2026-03-22 22:49:55.950059-03	f	\N	2	8	62.05	2026-04-10	f	\N		\N	\N	213	\N
1197	2026-03-22 22:49:55.950543-03	2026-03-22 22:49:55.950545-03	f	\N	3	8	62.05	2026-05-10	f	\N		\N	\N	213	\N
1198	2026-03-22 22:49:55.95095-03	2026-03-22 22:49:55.950951-03	f	\N	4	8	62.05	2026-06-10	f	\N		\N	\N	213	\N
1199	2026-03-22 22:49:55.951342-03	2026-03-22 22:49:55.951344-03	f	\N	5	8	62.05	2026-07-10	f	\N		\N	\N	213	\N
1200	2026-03-22 22:49:55.951763-03	2026-03-22 22:49:55.951765-03	f	\N	6	8	62.05	2026-08-10	f	\N		\N	\N	213	\N
1201	2026-03-22 22:49:55.952196-03	2026-03-22 22:49:55.952197-03	f	\N	7	8	62.05	2026-09-10	f	\N		\N	\N	213	\N
1202	2026-03-22 22:49:55.952575-03	2026-03-22 22:49:55.952577-03	f	\N	8	8	62.05	2026-10-10	f	\N		\N	\N	213	\N
1203	2026-03-22 22:49:55.953956-03	2026-03-22 22:49:55.953958-03	f	\N	1	17	50.00	2026-03-10	f	\N		\N	\N	214	\N
1204	2026-03-22 22:49:55.954667-03	2026-03-22 22:49:55.954669-03	f	\N	2	17	50.00	2026-04-10	f	\N		\N	\N	214	\N
1205	2026-03-22 22:49:55.955106-03	2026-03-22 22:49:55.955108-03	f	\N	3	17	50.00	2026-05-10	f	\N		\N	\N	214	\N
1206	2026-03-22 22:49:55.955535-03	2026-03-22 22:49:55.955537-03	f	\N	4	17	50.00	2026-06-10	f	\N		\N	\N	214	\N
1207	2026-03-22 22:49:55.955951-03	2026-03-22 22:49:55.955953-03	f	\N	5	17	50.00	2026-07-10	f	\N		\N	\N	214	\N
1208	2026-03-22 22:49:55.956377-03	2026-03-22 22:49:55.956379-03	f	\N	6	17	50.00	2026-08-10	f	\N		\N	\N	214	\N
1209	2026-03-22 22:49:55.95684-03	2026-03-22 22:49:55.956841-03	f	\N	7	17	50.00	2026-09-10	f	\N		\N	\N	214	\N
1210	2026-03-22 22:49:55.957203-03	2026-03-22 22:49:55.957205-03	f	\N	8	17	50.00	2026-10-10	f	\N		\N	\N	214	\N
1211	2026-03-22 22:49:55.957534-03	2026-03-22 22:49:55.957536-03	f	\N	9	17	50.00	2026-11-10	f	\N		\N	\N	214	\N
1212	2026-03-22 22:49:55.958027-03	2026-03-22 22:49:55.958029-03	f	\N	10	17	50.00	2026-12-10	f	\N		\N	\N	214	\N
1213	2026-03-22 22:49:55.95848-03	2026-03-22 22:49:55.958481-03	f	\N	11	17	50.00	2027-01-10	f	\N		\N	\N	214	\N
1214	2026-03-22 22:49:55.958949-03	2026-03-22 22:49:55.958951-03	f	\N	12	17	50.00	2027-02-10	f	\N		\N	\N	214	\N
1215	2026-03-22 22:49:55.959563-03	2026-03-22 22:49:55.959565-03	f	\N	13	17	50.00	2027-03-10	f	\N		\N	\N	214	\N
1216	2026-03-22 22:49:55.960132-03	2026-03-22 22:49:55.960134-03	f	\N	14	17	50.00	2027-04-10	f	\N		\N	\N	214	\N
1217	2026-03-22 22:49:55.960542-03	2026-03-22 22:49:55.960544-03	f	\N	15	17	50.00	2027-05-10	f	\N		\N	\N	214	\N
1218	2026-03-22 22:49:55.961009-03	2026-03-22 22:49:55.961011-03	f	\N	16	17	50.00	2027-06-10	f	\N		\N	\N	214	\N
1219	2026-03-22 22:49:55.961492-03	2026-03-22 22:49:55.961494-03	f	\N	17	17	50.00	2027-07-10	f	\N		\N	\N	214	\N
1220	2026-03-22 22:49:55.962715-03	2026-03-22 22:49:55.962717-03	f	\N	1	3	50.00	2026-03-10	f	\N		\N	\N	215	\N
1221	2026-03-22 22:49:55.963319-03	2026-03-22 22:49:55.963321-03	f	\N	2	3	50.00	2026-04-10	f	\N		\N	\N	215	\N
1222	2026-03-22 22:49:55.963886-03	2026-03-22 22:49:55.963888-03	f	\N	3	3	50.00	2026-05-10	f	\N		\N	\N	215	\N
1223	2026-03-22 22:49:55.964957-03	2026-03-22 22:49:55.964959-03	f	\N	1	8	90.00	2026-03-10	f	\N		\N	\N	216	\N
1224	2026-03-22 22:49:55.965421-03	2026-03-22 22:49:55.965423-03	f	\N	2	8	90.00	2026-04-10	f	\N		\N	\N	216	\N
1225	2026-03-22 22:49:55.96596-03	2026-03-22 22:49:55.965962-03	f	\N	3	8	90.00	2026-05-10	f	\N		\N	\N	216	\N
1226	2026-03-22 22:49:55.966317-03	2026-03-22 22:49:55.966319-03	f	\N	4	8	90.00	2026-06-10	f	\N		\N	\N	216	\N
1227	2026-03-22 22:49:55.966675-03	2026-03-22 22:49:55.966677-03	f	\N	5	8	90.00	2026-07-10	f	\N		\N	\N	216	\N
1228	2026-03-22 22:49:55.967065-03	2026-03-22 22:49:55.967067-03	f	\N	6	8	90.00	2026-08-10	f	\N		\N	\N	216	\N
1229	2026-03-22 22:49:55.967511-03	2026-03-22 22:49:55.967513-03	f	\N	7	8	90.00	2026-09-10	f	\N		\N	\N	216	\N
1230	2026-03-22 22:49:55.968104-03	2026-03-22 22:49:55.968105-03	f	\N	8	8	90.00	2026-10-10	f	\N		\N	\N	216	\N
1231	2026-03-22 22:49:55.96953-03	2026-03-22 22:49:55.969532-03	f	\N	1	18	77.17	2026-03-10	f	\N		\N	\N	217	\N
1232	2026-03-22 22:49:55.970071-03	2026-03-22 22:49:55.970095-03	f	\N	2	18	77.17	2026-04-10	f	\N		\N	\N	217	\N
1233	2026-03-22 22:49:55.970647-03	2026-03-22 22:49:55.970649-03	f	\N	3	18	77.17	2026-05-10	f	\N		\N	\N	217	\N
1234	2026-03-22 22:49:55.971187-03	2026-03-22 22:49:55.971189-03	f	\N	4	18	77.17	2026-06-10	f	\N		\N	\N	217	\N
1235	2026-03-22 22:49:55.971762-03	2026-03-22 22:49:55.971763-03	f	\N	5	18	77.17	2026-07-10	f	\N		\N	\N	217	\N
1236	2026-03-22 22:49:55.972324-03	2026-03-22 22:49:55.972326-03	f	\N	6	18	77.17	2026-08-10	f	\N		\N	\N	217	\N
1237	2026-03-22 22:49:55.972959-03	2026-03-22 22:49:55.972961-03	f	\N	7	18	77.17	2026-09-10	f	\N		\N	\N	217	\N
1238	2026-03-22 22:49:55.973381-03	2026-03-22 22:49:55.973408-03	f	\N	8	18	77.17	2026-10-10	f	\N		\N	\N	217	\N
1239	2026-03-22 22:49:55.973849-03	2026-03-22 22:49:55.973851-03	f	\N	9	18	77.17	2026-11-10	f	\N		\N	\N	217	\N
1240	2026-03-22 22:49:55.974318-03	2026-03-22 22:49:55.97432-03	f	\N	10	18	77.17	2026-12-10	f	\N		\N	\N	217	\N
1241	2026-03-22 22:49:55.974738-03	2026-03-22 22:49:55.97474-03	f	\N	11	18	77.17	2027-01-10	f	\N		\N	\N	217	\N
1242	2026-03-22 22:49:55.975189-03	2026-03-22 22:49:55.975191-03	f	\N	12	18	77.17	2027-02-10	f	\N		\N	\N	217	\N
1243	2026-03-22 22:49:55.97568-03	2026-03-22 22:49:55.975682-03	f	\N	13	18	77.17	2027-03-10	f	\N		\N	\N	217	\N
1244	2026-03-22 22:49:55.976189-03	2026-03-22 22:49:55.976191-03	f	\N	14	18	77.17	2027-04-10	f	\N		\N	\N	217	\N
1245	2026-03-22 22:49:55.976615-03	2026-03-22 22:49:55.976616-03	f	\N	15	18	77.17	2027-05-10	f	\N		\N	\N	217	\N
1246	2026-03-22 22:49:55.977011-03	2026-03-22 22:49:55.977013-03	f	\N	16	18	77.17	2027-06-10	f	\N		\N	\N	217	\N
1247	2026-03-22 22:49:55.97747-03	2026-03-22 22:49:55.977472-03	f	\N	17	18	77.17	2027-07-10	f	\N		\N	\N	217	\N
1248	2026-03-22 22:49:55.977894-03	2026-03-22 22:49:55.977896-03	f	\N	18	18	77.17	2027-08-10	f	\N		\N	\N	217	\N
1249	2026-03-22 22:49:55.979066-03	2026-03-22 22:49:55.979068-03	f	\N	1	60	950.00	2024-06-10	t	2024-06-10		\N	\N	218	\N
1250	2026-03-22 22:49:55.979638-03	2026-03-22 22:49:55.979639-03	f	\N	2	60	950.00	2024-07-10	t	2024-07-10		\N	\N	218	\N
1251	2026-03-22 22:49:55.980069-03	2026-03-22 22:49:55.980071-03	f	\N	3	60	950.00	2024-08-10	t	2024-08-10		\N	\N	218	\N
1252	2026-03-22 22:49:55.980694-03	2026-03-22 22:49:55.980696-03	f	\N	4	60	950.00	2024-09-10	t	2024-09-10		\N	\N	218	\N
1253	2026-03-22 22:49:55.981196-03	2026-03-22 22:49:55.981198-03	f	\N	5	60	950.00	2024-10-10	t	2024-10-10		\N	\N	218	\N
1254	2026-03-22 22:49:55.981626-03	2026-03-22 22:49:55.981628-03	f	\N	6	60	950.00	2024-11-10	t	2024-11-10		\N	\N	218	\N
1255	2026-03-22 22:49:55.982186-03	2026-03-22 22:49:55.982188-03	f	\N	7	60	950.00	2024-12-10	t	2024-12-10		\N	\N	218	\N
1256	2026-03-22 22:49:55.982638-03	2026-03-22 22:49:55.98264-03	f	\N	8	60	950.00	2025-01-10	t	2025-01-10		\N	\N	218	\N
1257	2026-03-22 22:49:55.983085-03	2026-03-22 22:49:55.983087-03	f	\N	9	60	950.00	2025-02-10	t	2025-02-10		\N	\N	218	\N
1258	2026-03-22 22:49:55.983584-03	2026-03-22 22:49:55.983587-03	f	\N	10	60	950.00	2025-03-10	t	2025-03-10		\N	\N	218	\N
1259	2026-03-22 22:49:55.984114-03	2026-03-22 22:49:55.984115-03	f	\N	11	60	950.00	2025-04-10	t	2025-04-10		\N	\N	218	\N
1260	2026-03-22 22:49:55.984641-03	2026-03-22 22:49:55.984642-03	f	\N	12	60	950.00	2025-05-10	t	2025-05-10		\N	\N	218	\N
1261	2026-03-22 22:49:55.985435-03	2026-03-22 22:49:55.985437-03	f	\N	13	60	950.00	2025-06-10	t	2025-06-10		\N	\N	218	\N
1262	2026-03-22 22:49:55.98593-03	2026-03-22 22:49:55.985932-03	f	\N	14	60	950.00	2025-07-10	t	2025-07-10		\N	\N	218	\N
1263	2026-03-22 22:49:55.986394-03	2026-03-22 22:49:55.986396-03	f	\N	15	60	950.00	2025-08-10	t	2025-08-10		\N	\N	218	\N
1264	2026-03-22 22:49:55.986929-03	2026-03-22 22:49:55.986931-03	f	\N	16	60	950.00	2025-09-10	t	2025-09-10		\N	\N	218	\N
1265	2026-03-22 22:49:55.987364-03	2026-03-22 22:49:55.987366-03	f	\N	17	60	950.00	2025-10-10	t	2025-10-10		\N	\N	218	\N
1266	2026-03-22 22:49:55.98781-03	2026-03-22 22:49:55.987812-03	f	\N	18	60	950.00	2025-11-10	t	2025-11-10		\N	\N	218	\N
1267	2026-03-22 22:49:55.988226-03	2026-03-22 22:49:55.988227-03	f	\N	19	60	950.00	2025-12-10	t	2025-12-10		\N	\N	218	\N
1268	2026-03-22 22:49:55.988706-03	2026-03-22 22:49:55.988708-03	f	\N	20	60	950.00	2026-01-10	t	2026-01-10		\N	\N	218	\N
1269	2026-03-22 22:49:55.98914-03	2026-03-22 22:49:55.989142-03	f	\N	21	60	950.00	2026-02-10	t	2026-02-10		\N	\N	218	\N
1270	2026-03-22 22:49:55.989574-03	2026-03-22 22:49:55.989575-03	f	\N	22	60	950.00	2026-03-10	f	\N		\N	\N	218	\N
1271	2026-03-22 22:49:55.990068-03	2026-03-22 22:49:55.99007-03	f	\N	23	60	950.00	2026-04-10	f	\N		\N	\N	218	\N
1272	2026-03-22 22:49:55.990486-03	2026-03-22 22:49:55.990487-03	f	\N	24	60	950.00	2026-05-10	f	\N		\N	\N	218	\N
1273	2026-03-22 22:49:55.990965-03	2026-03-22 22:49:55.990967-03	f	\N	25	60	950.00	2026-06-10	f	\N		\N	\N	218	\N
1274	2026-03-22 22:49:55.991442-03	2026-03-22 22:49:55.991444-03	f	\N	26	60	950.00	2026-07-10	f	\N		\N	\N	218	\N
1275	2026-03-22 22:49:55.991983-03	2026-03-22 22:49:55.991985-03	f	\N	27	60	950.00	2026-08-10	f	\N		\N	\N	218	\N
1276	2026-03-22 22:49:55.992422-03	2026-03-22 22:49:55.992424-03	f	\N	28	60	950.00	2026-09-10	f	\N		\N	\N	218	\N
1277	2026-03-22 22:49:55.992866-03	2026-03-22 22:49:55.992867-03	f	\N	29	60	950.00	2026-10-10	f	\N		\N	\N	218	\N
1278	2026-03-22 22:49:55.99329-03	2026-03-22 22:49:55.993293-03	f	\N	30	60	950.00	2026-11-10	f	\N		\N	\N	218	\N
1279	2026-03-22 22:49:55.993738-03	2026-03-22 22:49:55.99374-03	f	\N	31	60	950.00	2026-12-10	f	\N		\N	\N	218	\N
1280	2026-03-22 22:49:55.994164-03	2026-03-22 22:49:55.994166-03	f	\N	32	60	950.00	2027-01-10	f	\N		\N	\N	218	\N
1281	2026-03-22 22:49:55.994639-03	2026-03-22 22:49:55.994641-03	f	\N	33	60	950.00	2027-02-10	f	\N		\N	\N	218	\N
1282	2026-03-22 22:49:55.995058-03	2026-03-22 22:49:55.995059-03	f	\N	34	60	950.00	2027-03-10	f	\N		\N	\N	218	\N
1283	2026-03-22 22:49:55.995453-03	2026-03-22 22:49:55.995455-03	f	\N	35	60	950.00	2027-04-10	f	\N		\N	\N	218	\N
1284	2026-03-22 22:49:55.995845-03	2026-03-22 22:49:55.995847-03	f	\N	36	60	950.00	2027-05-10	f	\N		\N	\N	218	\N
1285	2026-03-22 22:49:55.996314-03	2026-03-22 22:49:55.996315-03	f	\N	37	60	950.00	2027-06-10	f	\N		\N	\N	218	\N
1286	2026-03-22 22:49:55.996872-03	2026-03-22 22:49:55.996873-03	f	\N	38	60	950.00	2027-07-10	f	\N		\N	\N	218	\N
1287	2026-03-22 22:49:55.997315-03	2026-03-22 22:49:55.997317-03	f	\N	39	60	950.00	2027-08-10	f	\N		\N	\N	218	\N
1288	2026-03-22 22:49:55.997848-03	2026-03-22 22:49:55.99785-03	f	\N	40	60	950.00	2027-09-10	f	\N		\N	\N	218	\N
1289	2026-03-22 22:49:55.998278-03	2026-03-22 22:49:55.99828-03	f	\N	41	60	950.00	2027-10-10	f	\N		\N	\N	218	\N
1290	2026-03-22 22:49:55.998824-03	2026-03-22 22:49:55.998826-03	f	\N	42	60	950.00	2027-11-10	f	\N		\N	\N	218	\N
1291	2026-03-22 22:49:55.999239-03	2026-03-22 22:49:55.999241-03	f	\N	43	60	950.00	2027-12-10	f	\N		\N	\N	218	\N
1292	2026-03-22 22:49:55.999668-03	2026-03-22 22:49:55.99967-03	f	\N	44	60	950.00	2028-01-10	f	\N		\N	\N	218	\N
1293	2026-03-22 22:49:56.000206-03	2026-03-22 22:49:56.000208-03	f	\N	45	60	950.00	2028-02-10	f	\N		\N	\N	218	\N
1294	2026-03-22 22:49:56.001164-03	2026-03-22 22:49:56.001165-03	f	\N	46	60	950.00	2028-03-10	f	\N		\N	\N	218	\N
1295	2026-03-22 22:49:56.001639-03	2026-03-22 22:49:56.001641-03	f	\N	47	60	950.00	2028-04-10	f	\N		\N	\N	218	\N
1296	2026-03-22 22:49:56.002088-03	2026-03-22 22:49:56.00209-03	f	\N	48	60	950.00	2028-05-10	f	\N		\N	\N	218	\N
1297	2026-03-22 22:49:56.002869-03	2026-03-22 22:49:56.00287-03	f	\N	49	60	950.00	2028-06-10	f	\N		\N	\N	218	\N
1298	2026-03-22 22:49:56.003318-03	2026-03-22 22:49:56.00332-03	f	\N	50	60	950.00	2028-07-10	f	\N		\N	\N	218	\N
1299	2026-03-22 22:49:56.003794-03	2026-03-22 22:49:56.003796-03	f	\N	51	60	950.00	2028-08-10	f	\N		\N	\N	218	\N
1300	2026-03-22 22:49:56.004221-03	2026-03-22 22:49:56.004223-03	f	\N	52	60	950.00	2028-09-10	f	\N		\N	\N	218	\N
1301	2026-03-22 22:49:56.004639-03	2026-03-22 22:49:56.004641-03	f	\N	53	60	950.00	2028-10-10	f	\N		\N	\N	218	\N
1302	2026-03-22 22:49:56.005069-03	2026-03-22 22:49:56.005071-03	f	\N	54	60	950.00	2028-11-10	f	\N		\N	\N	218	\N
1303	2026-03-22 22:49:56.005494-03	2026-03-22 22:49:56.005496-03	f	\N	55	60	950.00	2028-12-10	f	\N		\N	\N	218	\N
1304	2026-03-22 22:49:56.005941-03	2026-03-22 22:49:56.005943-03	f	\N	56	60	950.00	2029-01-10	f	\N		\N	\N	218	\N
1305	2026-03-22 22:49:56.006356-03	2026-03-22 22:49:56.006358-03	f	\N	57	60	950.00	2029-02-10	f	\N		\N	\N	218	\N
1306	2026-03-22 22:49:56.00677-03	2026-03-22 22:49:56.006772-03	f	\N	58	60	950.00	2029-03-10	f	\N		\N	\N	218	\N
1307	2026-03-22 22:49:56.00724-03	2026-03-22 22:49:56.007242-03	f	\N	59	60	950.00	2029-04-10	f	\N		\N	\N	218	\N
1308	2026-03-22 22:49:56.007649-03	2026-03-22 22:49:56.007651-03	f	\N	60	60	950.00	2029-05-10	f	\N		\N	\N	218	\N
1309	2026-03-22 22:49:56.008625-03	2026-03-22 22:49:56.008627-03	f	\N	1	4	120.00	2026-03-10	f	\N		\N	\N	219	\N
1310	2026-03-22 22:49:56.009208-03	2026-03-22 22:49:56.00921-03	f	\N	2	4	120.00	2026-04-10	f	\N		\N	\N	219	\N
1311	2026-03-22 22:49:56.009679-03	2026-03-22 22:49:56.009681-03	f	\N	3	4	120.00	2026-05-10	f	\N		\N	\N	219	\N
1312	2026-03-22 22:49:56.010155-03	2026-03-22 22:49:56.010156-03	f	\N	4	4	120.00	2026-06-10	f	\N		\N	\N	219	\N
1313	2026-03-22 22:49:56.011698-03	2026-03-22 22:49:56.0117-03	f	\N	1	35	1531.00	2025-01-10	t	2025-01-10		\N	\N	221	\N
1314	2026-03-22 22:49:56.012103-03	2026-03-22 22:49:56.012105-03	f	\N	2	35	1531.00	2025-02-10	t	2025-02-10		\N	\N	221	\N
1315	2026-03-22 22:49:56.01251-03	2026-03-22 22:49:56.012512-03	f	\N	3	35	1531.00	2025-03-10	t	2025-03-10		\N	\N	221	\N
1316	2026-03-22 22:49:56.013047-03	2026-03-22 22:49:56.013049-03	f	\N	4	35	1531.00	2025-04-10	t	2025-04-10		\N	\N	221	\N
1317	2026-03-22 22:49:56.013478-03	2026-03-22 22:49:56.01348-03	f	\N	5	35	1531.00	2025-05-10	t	2025-05-10		\N	\N	221	\N
1318	2026-03-22 22:49:56.013892-03	2026-03-22 22:49:56.013893-03	f	\N	6	35	1531.00	2025-06-10	t	2025-06-10		\N	\N	221	\N
1319	2026-03-22 22:49:56.014289-03	2026-03-22 22:49:56.014291-03	f	\N	7	35	1531.00	2025-07-10	t	2025-07-10		\N	\N	221	\N
1320	2026-03-22 22:49:56.014661-03	2026-03-22 22:49:56.014663-03	f	\N	8	35	1531.00	2025-08-10	t	2025-08-10		\N	\N	221	\N
1321	2026-03-22 22:49:56.015061-03	2026-03-22 22:49:56.015063-03	f	\N	9	35	1531.00	2025-09-10	t	2025-09-10		\N	\N	221	\N
1322	2026-03-22 22:49:56.015429-03	2026-03-22 22:49:56.01543-03	f	\N	10	35	1531.00	2025-10-10	t	2025-10-10		\N	\N	221	\N
1323	2026-03-22 22:49:56.015763-03	2026-03-22 22:49:56.015764-03	f	\N	11	35	1531.00	2025-11-10	t	2025-11-10		\N	\N	221	\N
1324	2026-03-22 22:49:56.016105-03	2026-03-22 22:49:56.016106-03	f	\N	12	35	1531.00	2025-12-10	t	2025-12-10		\N	\N	221	\N
1325	2026-03-22 22:49:56.016811-03	2026-03-22 22:49:56.016813-03	f	\N	13	35	1531.00	2026-01-10	t	2026-01-10		\N	\N	221	\N
1326	2026-03-22 22:49:56.017255-03	2026-03-22 22:49:56.017257-03	f	\N	14	35	1531.00	2026-02-10	t	2026-02-10		\N	\N	221	\N
1327	2026-03-22 22:49:56.017624-03	2026-03-22 22:49:56.017626-03	f	\N	15	35	1531.00	2026-03-10	f	\N		\N	\N	221	\N
1328	2026-03-22 22:49:56.018048-03	2026-03-22 22:49:56.01805-03	f	\N	16	35	1531.00	2026-04-10	f	\N		\N	\N	221	\N
1329	2026-03-22 22:49:56.018501-03	2026-03-22 22:49:56.018503-03	f	\N	17	35	1531.00	2026-05-10	f	\N		\N	\N	221	\N
1330	2026-03-22 22:49:56.018994-03	2026-03-22 22:49:56.018996-03	f	\N	18	35	1531.00	2026-06-10	f	\N		\N	\N	221	\N
1331	2026-03-22 22:49:56.01954-03	2026-03-22 22:49:56.019542-03	f	\N	19	35	1531.00	2026-07-10	f	\N		\N	\N	221	\N
1332	2026-03-22 22:49:56.0201-03	2026-03-22 22:49:56.020102-03	f	\N	20	35	1531.00	2026-08-10	f	\N		\N	\N	221	\N
1333	2026-03-22 22:49:56.020616-03	2026-03-22 22:49:56.020618-03	f	\N	21	35	1531.00	2026-09-10	f	\N		\N	\N	221	\N
1334	2026-03-22 22:49:56.021084-03	2026-03-22 22:49:56.021086-03	f	\N	22	35	1531.00	2026-10-10	f	\N		\N	\N	221	\N
1335	2026-03-22 22:49:56.021647-03	2026-03-22 22:49:56.021649-03	f	\N	23	35	1531.00	2026-11-10	f	\N		\N	\N	221	\N
1336	2026-03-22 22:49:56.022079-03	2026-03-22 22:49:56.022081-03	f	\N	24	35	1531.00	2026-12-10	f	\N		\N	\N	221	\N
1337	2026-03-22 22:49:56.022494-03	2026-03-22 22:49:56.022496-03	f	\N	25	35	1531.00	2027-01-10	f	\N		\N	\N	221	\N
1338	2026-03-22 22:49:56.022937-03	2026-03-22 22:49:56.022939-03	f	\N	26	35	1531.00	2027-02-10	f	\N		\N	\N	221	\N
1339	2026-03-22 22:49:56.023381-03	2026-03-22 22:49:56.023384-03	f	\N	27	35	1531.00	2027-03-10	f	\N		\N	\N	221	\N
1340	2026-03-22 22:49:56.023829-03	2026-03-22 22:49:56.023831-03	f	\N	28	35	1531.00	2027-04-10	f	\N		\N	\N	221	\N
1341	2026-03-22 22:49:56.024235-03	2026-03-22 22:49:56.024237-03	f	\N	29	35	1531.00	2027-05-10	f	\N		\N	\N	221	\N
1342	2026-03-22 22:49:56.024615-03	2026-03-22 22:49:56.024617-03	f	\N	30	35	1531.00	2027-06-10	f	\N		\N	\N	221	\N
1343	2026-03-22 22:49:56.024986-03	2026-03-22 22:49:56.024988-03	f	\N	31	35	1531.00	2027-07-10	f	\N		\N	\N	221	\N
1344	2026-03-22 22:49:56.025394-03	2026-03-22 22:49:56.025396-03	f	\N	32	35	1531.00	2027-08-10	f	\N		\N	\N	221	\N
1345	2026-03-22 22:49:56.025805-03	2026-03-22 22:49:56.025806-03	f	\N	33	35	1531.00	2027-09-10	f	\N		\N	\N	221	\N
1346	2026-03-22 22:49:56.026176-03	2026-03-22 22:49:56.026178-03	f	\N	34	35	1531.00	2027-10-10	f	\N		\N	\N	221	\N
1347	2026-03-22 22:49:56.026582-03	2026-03-22 22:49:56.026583-03	f	\N	35	35	1531.00	2027-11-10	f	\N		\N	\N	221	\N
1348	2026-03-22 22:49:56.027573-03	2026-03-22 22:49:56.027575-03	f	\N	1	10	120.00	2025-06-10	t	2025-06-10		\N	\N	222	\N
1349	2026-03-22 22:49:56.027955-03	2026-03-22 22:49:56.027957-03	f	\N	2	10	120.00	2025-07-10	t	2025-07-10		\N	\N	222	\N
1350	2026-03-22 22:49:56.028436-03	2026-03-22 22:49:56.028438-03	f	\N	3	10	120.00	2025-08-10	t	2025-08-10		\N	\N	222	\N
1351	2026-03-22 22:49:56.028872-03	2026-03-22 22:49:56.028874-03	f	\N	4	10	120.00	2025-09-10	t	2025-09-10		\N	\N	222	\N
1352	2026-03-22 22:49:56.029289-03	2026-03-22 22:49:56.029291-03	f	\N	5	10	120.00	2025-10-10	t	2025-10-10		\N	\N	222	\N
1353	2026-03-22 22:49:56.02968-03	2026-03-22 22:49:56.029682-03	f	\N	6	10	120.00	2025-11-10	t	2025-11-10		\N	\N	222	\N
1354	2026-03-22 22:49:56.030122-03	2026-03-22 22:49:56.030124-03	f	\N	7	10	120.00	2025-12-10	t	2025-12-10		\N	\N	222	\N
1355	2026-03-22 22:49:56.030518-03	2026-03-22 22:49:56.03052-03	f	\N	8	10	120.00	2026-01-10	t	2026-01-10		\N	\N	222	\N
1356	2026-03-22 22:49:56.031174-03	2026-03-22 22:49:56.031176-03	f	\N	9	10	120.00	2026-02-10	t	2026-02-10		\N	\N	222	\N
1357	2026-03-22 22:49:56.031972-03	2026-03-22 22:49:56.031976-03	f	\N	10	10	120.00	2026-03-10	f	\N		\N	\N	222	\N
1358	2026-03-22 22:49:56.033178-03	2026-03-22 22:49:56.033205-03	f	\N	1	12	116.70	2025-06-10	t	2025-06-10		\N	\N	223	\N
1359	2026-03-22 22:49:56.033773-03	2026-03-22 22:49:56.033775-03	f	\N	2	12	116.70	2025-07-10	t	2025-07-10		\N	\N	223	\N
1360	2026-03-22 22:49:56.034251-03	2026-03-22 22:49:56.034253-03	f	\N	3	12	116.70	2025-08-10	t	2025-08-10		\N	\N	223	\N
1361	2026-03-22 22:49:56.0347-03	2026-03-22 22:49:56.034701-03	f	\N	4	12	116.70	2025-09-10	t	2025-09-10		\N	\N	223	\N
1362	2026-03-22 22:49:56.035135-03	2026-03-22 22:49:56.035137-03	f	\N	5	12	116.70	2025-10-10	t	2025-10-10		\N	\N	223	\N
1363	2026-03-22 22:49:56.035632-03	2026-03-22 22:49:56.035634-03	f	\N	6	12	116.70	2025-11-10	t	2025-11-10		\N	\N	223	\N
1364	2026-03-22 22:49:56.036058-03	2026-03-22 22:49:56.03606-03	f	\N	7	12	116.70	2025-12-10	t	2025-12-10		\N	\N	223	\N
1365	2026-03-22 22:49:56.036467-03	2026-03-22 22:49:56.036468-03	f	\N	8	12	116.70	2026-01-10	t	2026-01-10		\N	\N	223	\N
1366	2026-03-22 22:49:56.036852-03	2026-03-22 22:49:56.036853-03	f	\N	9	12	116.70	2026-02-10	t	2026-02-10		\N	\N	223	\N
1367	2026-03-22 22:49:56.037174-03	2026-03-22 22:49:56.037175-03	f	\N	10	12	116.70	2026-03-10	f	\N		\N	\N	223	\N
1368	2026-03-22 22:49:56.037619-03	2026-03-22 22:49:56.037621-03	f	\N	11	12	116.70	2026-04-10	f	\N		\N	\N	223	\N
1369	2026-03-22 22:49:56.038058-03	2026-03-22 22:49:56.03806-03	f	\N	12	12	116.70	2026-05-10	f	\N		\N	\N	223	\N
1370	2026-03-22 22:49:56.039074-03	2026-03-22 22:49:56.039076-03	f	\N	1	24	192.50	2025-08-10	t	2025-08-10		\N	\N	224	\N
1371	2026-03-22 22:49:56.039546-03	2026-03-22 22:49:56.039548-03	f	\N	2	24	192.50	2025-09-10	t	2025-09-10		\N	\N	224	\N
1372	2026-03-22 22:49:56.039973-03	2026-03-22 22:49:56.039974-03	f	\N	3	24	192.50	2025-10-10	t	2025-10-10		\N	\N	224	\N
1373	2026-03-22 22:49:56.040459-03	2026-03-22 22:49:56.040461-03	f	\N	4	24	192.50	2025-11-10	t	2025-11-10		\N	\N	224	\N
1374	2026-03-22 22:49:56.040898-03	2026-03-22 22:49:56.040899-03	f	\N	5	24	192.50	2025-12-10	t	2025-12-10		\N	\N	224	\N
1375	2026-03-22 22:49:56.041311-03	2026-03-22 22:49:56.041313-03	f	\N	6	24	192.50	2026-01-10	t	2026-01-10		\N	\N	224	\N
1376	2026-03-22 22:49:56.041738-03	2026-03-22 22:49:56.04174-03	f	\N	7	24	192.50	2026-02-10	t	2026-02-10		\N	\N	224	\N
1377	2026-03-22 22:49:56.042121-03	2026-03-22 22:49:56.042123-03	f	\N	8	24	192.50	2026-03-10	f	\N		\N	\N	224	\N
1378	2026-03-22 22:49:56.042539-03	2026-03-22 22:49:56.042541-03	f	\N	9	24	192.50	2026-04-10	f	\N		\N	\N	224	\N
1379	2026-03-22 22:49:56.042986-03	2026-03-22 22:49:56.042988-03	f	\N	10	24	192.50	2026-05-10	f	\N		\N	\N	224	\N
1380	2026-03-22 22:49:56.043385-03	2026-03-22 22:49:56.043387-03	f	\N	11	24	192.50	2026-06-10	f	\N		\N	\N	224	\N
1381	2026-03-22 22:49:56.043739-03	2026-03-22 22:49:56.043741-03	f	\N	12	24	192.50	2026-07-10	f	\N		\N	\N	224	\N
1382	2026-03-22 22:49:56.0441-03	2026-03-22 22:49:56.044101-03	f	\N	13	24	192.50	2026-08-10	f	\N		\N	\N	224	\N
1383	2026-03-22 22:49:56.04444-03	2026-03-22 22:49:56.044442-03	f	\N	14	24	192.50	2026-09-10	f	\N		\N	\N	224	\N
1384	2026-03-22 22:49:56.044746-03	2026-03-22 22:49:56.044748-03	f	\N	15	24	192.50	2026-10-10	f	\N		\N	\N	224	\N
1385	2026-03-22 22:49:56.045037-03	2026-03-22 22:49:56.045039-03	f	\N	16	24	192.50	2026-11-10	f	\N		\N	\N	224	\N
1386	2026-03-22 22:49:56.04533-03	2026-03-22 22:49:56.045331-03	f	\N	17	24	192.50	2026-12-10	f	\N		\N	\N	224	\N
1387	2026-03-22 22:49:56.045621-03	2026-03-22 22:49:56.045623-03	f	\N	18	24	192.50	2027-01-10	f	\N		\N	\N	224	\N
1388	2026-03-22 22:49:56.045923-03	2026-03-22 22:49:56.045925-03	f	\N	19	24	192.50	2027-02-10	f	\N		\N	\N	224	\N
1389	2026-03-22 22:49:56.046218-03	2026-03-22 22:49:56.046219-03	f	\N	20	24	192.50	2027-03-10	f	\N		\N	\N	224	\N
1390	2026-03-22 22:49:56.046518-03	2026-03-22 22:49:56.04652-03	f	\N	21	24	192.50	2027-04-10	f	\N		\N	\N	224	\N
1391	2026-03-22 22:49:56.046802-03	2026-03-22 22:49:56.046803-03	f	\N	22	24	192.50	2027-05-10	f	\N		\N	\N	224	\N
1392	2026-03-22 22:49:56.047089-03	2026-03-22 22:49:56.04709-03	f	\N	23	24	192.50	2027-06-10	f	\N		\N	\N	224	\N
1393	2026-03-22 22:49:56.04779-03	2026-03-22 22:49:56.047792-03	f	\N	24	24	192.50	2027-07-10	f	\N		\N	\N	224	\N
1394	2026-03-22 22:49:56.048844-03	2026-03-22 22:49:56.048846-03	f	\N	1	10	189.80	2025-08-10	t	2025-08-10		\N	\N	225	\N
1395	2026-03-22 22:49:56.049463-03	2026-03-22 22:49:56.049465-03	f	\N	2	10	189.80	2025-09-10	t	2025-09-10		\N	\N	225	\N
1396	2026-03-22 22:49:56.049953-03	2026-03-22 22:49:56.049976-03	f	\N	3	10	189.80	2025-10-10	t	2025-10-10		\N	\N	225	\N
1397	2026-03-22 22:49:56.05054-03	2026-03-22 22:49:56.050542-03	f	\N	4	10	189.80	2025-11-10	t	2025-11-10		\N	\N	225	\N
1398	2026-03-22 22:49:56.051138-03	2026-03-22 22:49:56.05114-03	f	\N	5	10	189.80	2025-12-10	t	2025-12-10		\N	\N	225	\N
1399	2026-03-22 22:49:56.051651-03	2026-03-22 22:49:56.051653-03	f	\N	6	10	189.80	2026-01-10	t	2026-01-10		\N	\N	225	\N
1400	2026-03-22 22:49:56.052112-03	2026-03-22 22:49:56.052113-03	f	\N	7	10	189.80	2026-02-10	t	2026-02-10		\N	\N	225	\N
1401	2026-03-22 22:49:56.052623-03	2026-03-22 22:49:56.052625-03	f	\N	8	10	189.80	2026-03-10	f	\N		\N	\N	225	\N
1402	2026-03-22 22:49:56.053111-03	2026-03-22 22:49:56.053113-03	f	\N	9	10	189.80	2026-04-10	f	\N		\N	\N	225	\N
1403	2026-03-22 22:49:56.053598-03	2026-03-22 22:49:56.0536-03	f	\N	10	10	189.80	2026-05-10	f	\N		\N	\N	225	\N
1404	2026-03-22 22:49:56.054629-03	2026-03-22 22:49:56.054631-03	f	\N	1	18	139.49	2025-08-10	t	2025-08-10		\N	\N	226	\N
1405	2026-03-22 22:49:56.055083-03	2026-03-22 22:49:56.055085-03	f	\N	2	18	139.49	2025-09-10	t	2025-09-10		\N	\N	226	\N
1406	2026-03-22 22:49:56.055569-03	2026-03-22 22:49:56.055571-03	f	\N	3	18	139.49	2025-10-10	t	2025-10-10		\N	\N	226	\N
1407	2026-03-22 22:49:56.056059-03	2026-03-22 22:49:56.056061-03	f	\N	4	18	139.49	2025-11-10	t	2025-11-10		\N	\N	226	\N
1408	2026-03-22 22:49:56.056471-03	2026-03-22 22:49:56.056473-03	f	\N	5	18	139.49	2025-12-10	t	2025-12-10		\N	\N	226	\N
1409	2026-03-22 22:49:56.056902-03	2026-03-22 22:49:56.056904-03	f	\N	6	18	139.49	2026-01-10	t	2026-01-10		\N	\N	226	\N
1410	2026-03-22 22:49:56.057323-03	2026-03-22 22:49:56.057325-03	f	\N	7	18	139.49	2026-02-10	t	2026-02-10		\N	\N	226	\N
1411	2026-03-22 22:49:56.057731-03	2026-03-22 22:49:56.057733-03	f	\N	8	18	139.49	2026-03-10	f	\N		\N	\N	226	\N
1412	2026-03-22 22:49:56.058185-03	2026-03-22 22:49:56.058187-03	f	\N	9	18	139.49	2026-04-10	f	\N		\N	\N	226	\N
1413	2026-03-22 22:49:56.058656-03	2026-03-22 22:49:56.058658-03	f	\N	10	18	139.49	2026-05-10	f	\N		\N	\N	226	\N
1414	2026-03-22 22:49:56.059079-03	2026-03-22 22:49:56.059081-03	f	\N	11	18	139.49	2026-06-10	f	\N		\N	\N	226	\N
1415	2026-03-22 22:49:56.059491-03	2026-03-22 22:49:56.059493-03	f	\N	12	18	139.49	2026-07-10	f	\N		\N	\N	226	\N
1416	2026-03-22 22:49:56.059902-03	2026-03-22 22:49:56.059904-03	f	\N	13	18	139.49	2026-08-10	f	\N		\N	\N	226	\N
1417	2026-03-22 22:49:56.060327-03	2026-03-22 22:49:56.060329-03	f	\N	14	18	139.49	2026-09-10	f	\N		\N	\N	226	\N
1418	2026-03-22 22:49:56.060757-03	2026-03-22 22:49:56.060759-03	f	\N	15	18	139.49	2026-10-10	f	\N		\N	\N	226	\N
1419	2026-03-22 22:49:56.06115-03	2026-03-22 22:49:56.061151-03	f	\N	16	18	139.49	2026-11-10	f	\N		\N	\N	226	\N
1420	2026-03-22 22:49:56.061569-03	2026-03-22 22:49:56.061571-03	f	\N	17	18	139.49	2026-12-10	f	\N		\N	\N	226	\N
1421	2026-03-22 22:49:56.062014-03	2026-03-22 22:49:56.062016-03	f	\N	18	18	139.49	2027-01-10	f	\N		\N	\N	226	\N
1422	2026-03-22 22:49:56.063449-03	2026-03-22 22:49:56.063451-03	f	\N	1	12	245.48	2025-10-10	t	2025-10-10		\N	\N	227	\N
1423	2026-03-22 22:49:56.064013-03	2026-03-22 22:49:56.064015-03	f	\N	2	12	245.48	2025-11-10	t	2025-11-10		\N	\N	227	\N
1424	2026-03-22 22:49:56.064511-03	2026-03-22 22:49:56.064513-03	f	\N	3	12	245.48	2025-12-10	t	2025-12-10		\N	\N	227	\N
1425	2026-03-22 22:49:56.064946-03	2026-03-22 22:49:56.064947-03	f	\N	4	12	245.48	2026-01-10	t	2026-01-10		\N	\N	227	\N
1426	2026-03-22 22:49:56.065364-03	2026-03-22 22:49:56.065366-03	f	\N	5	12	245.48	2026-02-10	t	2026-02-10		\N	\N	227	\N
1427	2026-03-22 22:49:56.065774-03	2026-03-22 22:49:56.065776-03	f	\N	6	12	245.48	2026-03-10	f	\N		\N	\N	227	\N
1428	2026-03-22 22:49:56.066222-03	2026-03-22 22:49:56.066224-03	f	\N	7	12	245.48	2026-04-10	f	\N		\N	\N	227	\N
1429	2026-03-22 22:49:56.06667-03	2026-03-22 22:49:56.066672-03	f	\N	8	12	245.48	2026-05-10	f	\N		\N	\N	227	\N
1430	2026-03-22 22:49:56.067099-03	2026-03-22 22:49:56.067101-03	f	\N	9	12	245.48	2026-06-10	f	\N		\N	\N	227	\N
1431	2026-03-22 22:49:56.067512-03	2026-03-22 22:49:56.067514-03	f	\N	10	12	245.48	2026-07-10	f	\N		\N	\N	227	\N
1432	2026-03-22 22:49:56.067921-03	2026-03-22 22:49:56.067923-03	f	\N	11	12	245.48	2026-08-10	f	\N		\N	\N	227	\N
1433	2026-03-22 22:49:56.068357-03	2026-03-22 22:49:56.068358-03	f	\N	12	12	245.48	2026-09-10	f	\N		\N	\N	227	\N
1434	2026-03-22 22:49:56.069271-03	2026-03-22 22:49:56.069273-03	f	\N	1	10	191.09	2025-11-10	t	2025-11-10		\N	\N	228	\N
1435	2026-03-22 22:49:56.069697-03	2026-03-22 22:49:56.069698-03	f	\N	2	10	191.09	2025-12-10	t	2025-12-10		\N	\N	228	\N
1436	2026-03-22 22:49:56.070114-03	2026-03-22 22:49:56.070116-03	f	\N	3	10	191.09	2026-01-10	t	2026-01-10		\N	\N	228	\N
1437	2026-03-22 22:49:56.070616-03	2026-03-22 22:49:56.070618-03	f	\N	4	10	191.09	2026-02-10	t	2026-02-10		\N	\N	228	\N
1438	2026-03-22 22:49:56.071189-03	2026-03-22 22:49:56.07119-03	f	\N	5	10	191.09	2026-03-10	f	\N		\N	\N	228	\N
1439	2026-03-22 22:49:56.071617-03	2026-03-22 22:49:56.071619-03	f	\N	6	10	191.09	2026-04-10	f	\N		\N	\N	228	\N
1440	2026-03-22 22:49:56.072017-03	2026-03-22 22:49:56.072019-03	f	\N	7	10	191.09	2026-05-10	f	\N		\N	\N	228	\N
1441	2026-03-22 22:49:56.072431-03	2026-03-22 22:49:56.072433-03	f	\N	8	10	191.09	2026-06-10	f	\N		\N	\N	228	\N
1442	2026-03-22 22:49:56.072863-03	2026-03-22 22:49:56.072865-03	f	\N	9	10	191.09	2026-07-10	f	\N		\N	\N	228	\N
1443	2026-03-22 22:49:56.073262-03	2026-03-22 22:49:56.073264-03	f	\N	10	10	191.09	2026-08-10	f	\N		\N	\N	228	\N
1444	2026-03-22 22:49:56.074219-03	2026-03-22 22:49:56.074221-03	f	\N	1	60	1505.00	2025-12-10	t	2025-12-10		\N	\N	229	\N
1445	2026-03-22 22:49:56.074659-03	2026-03-22 22:49:56.07466-03	f	\N	2	60	1505.00	2026-01-10	t	2026-01-10		\N	\N	229	\N
1446	2026-03-22 22:49:56.075098-03	2026-03-22 22:49:56.0751-03	f	\N	3	60	1505.00	2026-02-10	t	2026-02-10		\N	\N	229	\N
1447	2026-03-22 22:49:56.075535-03	2026-03-22 22:49:56.075537-03	f	\N	4	60	1505.00	2026-03-10	f	\N		\N	\N	229	\N
1448	2026-03-22 22:49:56.075994-03	2026-03-22 22:49:56.075996-03	f	\N	5	60	1505.00	2026-04-10	f	\N		\N	\N	229	\N
1449	2026-03-22 22:49:56.076404-03	2026-03-22 22:49:56.076406-03	f	\N	6	60	1505.00	2026-05-10	f	\N		\N	\N	229	\N
1450	2026-03-22 22:49:56.076844-03	2026-03-22 22:49:56.076845-03	f	\N	7	60	1505.00	2026-06-10	f	\N		\N	\N	229	\N
1451	2026-03-22 22:49:56.077259-03	2026-03-22 22:49:56.077261-03	f	\N	8	60	1505.00	2026-07-10	f	\N		\N	\N	229	\N
1452	2026-03-22 22:49:56.077691-03	2026-03-22 22:49:56.077693-03	f	\N	9	60	1505.00	2026-08-10	f	\N		\N	\N	229	\N
1453	2026-03-22 22:49:56.078293-03	2026-03-22 22:49:56.078295-03	f	\N	10	60	1505.00	2026-09-10	f	\N		\N	\N	229	\N
1454	2026-03-22 22:49:56.078739-03	2026-03-22 22:49:56.078741-03	f	\N	11	60	1505.00	2026-10-10	f	\N		\N	\N	229	\N
1455	2026-03-22 22:49:56.079212-03	2026-03-22 22:49:56.079214-03	f	\N	12	60	1505.00	2026-11-10	f	\N		\N	\N	229	\N
1456	2026-03-22 22:49:56.079731-03	2026-03-22 22:49:56.079733-03	f	\N	13	60	1505.00	2026-12-10	f	\N		\N	\N	229	\N
1457	2026-03-22 22:49:56.080161-03	2026-03-22 22:49:56.080163-03	f	\N	14	60	1505.00	2027-01-10	f	\N		\N	\N	229	\N
1458	2026-03-22 22:49:56.080722-03	2026-03-22 22:49:56.080724-03	f	\N	15	60	1505.00	2027-02-10	f	\N		\N	\N	229	\N
1459	2026-03-22 22:49:56.081286-03	2026-03-22 22:49:56.081288-03	f	\N	16	60	1505.00	2027-03-10	f	\N		\N	\N	229	\N
1460	2026-03-22 22:49:56.081765-03	2026-03-22 22:49:56.081767-03	f	\N	17	60	1505.00	2027-04-10	f	\N		\N	\N	229	\N
1461	2026-03-22 22:49:56.082295-03	2026-03-22 22:49:56.082297-03	f	\N	18	60	1505.00	2027-05-10	f	\N		\N	\N	229	\N
1462	2026-03-22 22:49:56.082754-03	2026-03-22 22:49:56.082756-03	f	\N	19	60	1505.00	2027-06-10	f	\N		\N	\N	229	\N
1463	2026-03-22 22:49:56.083169-03	2026-03-22 22:49:56.083171-03	f	\N	20	60	1505.00	2027-07-10	f	\N		\N	\N	229	\N
1464	2026-03-22 22:49:56.083746-03	2026-03-22 22:49:56.083749-03	f	\N	21	60	1505.00	2027-08-10	f	\N		\N	\N	229	\N
1465	2026-03-22 22:49:56.084248-03	2026-03-22 22:49:56.084249-03	f	\N	22	60	1505.00	2027-09-10	f	\N		\N	\N	229	\N
1466	2026-03-22 22:49:56.08483-03	2026-03-22 22:49:56.084831-03	f	\N	23	60	1505.00	2027-10-10	f	\N		\N	\N	229	\N
1467	2026-03-22 22:49:56.08531-03	2026-03-22 22:49:56.085311-03	f	\N	24	60	1505.00	2027-11-10	f	\N		\N	\N	229	\N
1468	2026-03-22 22:49:56.085811-03	2026-03-22 22:49:56.085814-03	f	\N	25	60	1505.00	2027-12-10	f	\N		\N	\N	229	\N
1469	2026-03-22 22:49:56.086275-03	2026-03-22 22:49:56.086277-03	f	\N	26	60	1505.00	2028-01-10	f	\N		\N	\N	229	\N
1470	2026-03-22 22:49:56.086735-03	2026-03-22 22:49:56.086737-03	f	\N	27	60	1505.00	2028-02-10	f	\N		\N	\N	229	\N
1471	2026-03-22 22:49:56.0873-03	2026-03-22 22:49:56.087302-03	f	\N	28	60	1505.00	2028-03-10	f	\N		\N	\N	229	\N
1472	2026-03-22 22:49:56.087745-03	2026-03-22 22:49:56.087747-03	f	\N	29	60	1505.00	2028-04-10	f	\N		\N	\N	229	\N
1473	2026-03-22 22:49:56.08837-03	2026-03-22 22:49:56.088373-03	f	\N	30	60	1505.00	2028-05-10	f	\N		\N	\N	229	\N
1474	2026-03-22 22:49:56.089122-03	2026-03-22 22:49:56.089124-03	f	\N	31	60	1505.00	2028-06-10	f	\N		\N	\N	229	\N
1475	2026-03-22 22:49:56.089566-03	2026-03-22 22:49:56.089568-03	f	\N	32	60	1505.00	2028-07-10	f	\N		\N	\N	229	\N
1476	2026-03-22 22:49:56.090054-03	2026-03-22 22:49:56.090056-03	f	\N	33	60	1505.00	2028-08-10	f	\N		\N	\N	229	\N
1477	2026-03-22 22:49:56.090589-03	2026-03-22 22:49:56.090591-03	f	\N	34	60	1505.00	2028-09-10	f	\N		\N	\N	229	\N
1478	2026-03-22 22:49:56.091098-03	2026-03-22 22:49:56.0911-03	f	\N	35	60	1505.00	2028-10-10	f	\N		\N	\N	229	\N
1479	2026-03-22 22:49:56.091584-03	2026-03-22 22:49:56.091585-03	f	\N	36	60	1505.00	2028-11-10	f	\N		\N	\N	229	\N
1480	2026-03-22 22:49:56.092113-03	2026-03-22 22:49:56.092115-03	f	\N	37	60	1505.00	2028-12-10	f	\N		\N	\N	229	\N
1481	2026-03-22 22:49:56.092574-03	2026-03-22 22:49:56.092576-03	f	\N	38	60	1505.00	2029-01-10	f	\N		\N	\N	229	\N
1482	2026-03-22 22:49:56.093115-03	2026-03-22 22:49:56.093117-03	f	\N	39	60	1505.00	2029-02-10	f	\N		\N	\N	229	\N
1483	2026-03-22 22:49:56.093581-03	2026-03-22 22:49:56.093583-03	f	\N	40	60	1505.00	2029-03-10	f	\N		\N	\N	229	\N
1484	2026-03-22 22:49:56.094062-03	2026-03-22 22:49:56.094064-03	f	\N	41	60	1505.00	2029-04-10	f	\N		\N	\N	229	\N
1485	2026-03-22 22:49:56.09476-03	2026-03-22 22:49:56.094762-03	f	\N	42	60	1505.00	2029-05-10	f	\N		\N	\N	229	\N
1486	2026-03-22 22:49:56.095211-03	2026-03-22 22:49:56.095213-03	f	\N	43	60	1505.00	2029-06-10	f	\N		\N	\N	229	\N
1487	2026-03-22 22:49:56.095648-03	2026-03-22 22:49:56.09565-03	f	\N	44	60	1505.00	2029-07-10	f	\N		\N	\N	229	\N
1488	2026-03-22 22:49:56.096045-03	2026-03-22 22:49:56.096047-03	f	\N	45	60	1505.00	2029-08-10	f	\N		\N	\N	229	\N
1489	2026-03-22 22:49:56.096483-03	2026-03-22 22:49:56.096485-03	f	\N	46	60	1505.00	2029-09-10	f	\N		\N	\N	229	\N
1490	2026-03-22 22:49:56.096905-03	2026-03-22 22:49:56.096907-03	f	\N	47	60	1505.00	2029-10-10	f	\N		\N	\N	229	\N
1491	2026-03-22 22:49:56.097474-03	2026-03-22 22:49:56.097476-03	f	\N	48	60	1505.00	2029-11-10	f	\N		\N	\N	229	\N
1492	2026-03-22 22:49:56.097947-03	2026-03-22 22:49:56.097949-03	f	\N	49	60	1505.00	2029-12-10	f	\N		\N	\N	229	\N
1493	2026-03-22 22:49:56.098468-03	2026-03-22 22:49:56.09847-03	f	\N	50	60	1505.00	2030-01-10	f	\N		\N	\N	229	\N
1494	2026-03-22 22:49:56.098906-03	2026-03-22 22:49:56.098908-03	f	\N	51	60	1505.00	2030-02-10	f	\N		\N	\N	229	\N
1495	2026-03-22 22:49:56.099431-03	2026-03-22 22:49:56.099433-03	f	\N	52	60	1505.00	2030-03-10	f	\N		\N	\N	229	\N
1496	2026-03-22 22:49:56.099886-03	2026-03-22 22:49:56.099888-03	f	\N	53	60	1505.00	2030-04-10	f	\N		\N	\N	229	\N
1497	2026-03-22 22:49:56.100342-03	2026-03-22 22:49:56.100344-03	f	\N	54	60	1505.00	2030-05-10	f	\N		\N	\N	229	\N
1498	2026-03-22 22:49:56.10097-03	2026-03-22 22:49:56.100972-03	f	\N	55	60	1505.00	2030-06-10	f	\N		\N	\N	229	\N
1499	2026-03-22 22:49:56.101533-03	2026-03-22 22:49:56.101535-03	f	\N	56	60	1505.00	2030-07-10	f	\N		\N	\N	229	\N
1500	2026-03-22 22:49:56.101989-03	2026-03-22 22:49:56.101991-03	f	\N	57	60	1505.00	2030-08-10	f	\N		\N	\N	229	\N
1501	2026-03-22 22:49:56.102508-03	2026-03-22 22:49:56.102509-03	f	\N	58	60	1505.00	2030-09-10	f	\N		\N	\N	229	\N
1502	2026-03-22 22:49:56.102992-03	2026-03-22 22:49:56.102994-03	f	\N	59	60	1505.00	2030-10-10	f	\N		\N	\N	229	\N
1503	2026-03-22 22:49:56.103578-03	2026-03-22 22:49:56.10358-03	f	\N	60	60	1505.00	2030-11-10	f	\N		\N	\N	229	\N
1504	2026-03-22 22:49:56.104619-03	2026-03-22 22:49:56.104621-03	f	\N	1	48	3034.50	2026-01-10	t	2026-01-10		\N	\N	230	\N
1505	2026-03-22 22:49:56.105099-03	2026-03-22 22:49:56.105101-03	f	\N	2	48	3034.50	2026-02-10	t	2026-02-10		\N	\N	230	\N
1506	2026-03-22 22:49:56.105567-03	2026-03-22 22:49:56.105568-03	f	\N	3	48	3034.50	2026-03-10	f	\N		\N	\N	230	\N
1507	2026-03-22 22:49:56.106236-03	2026-03-22 22:49:56.106238-03	f	\N	4	48	3034.50	2026-04-10	f	\N		\N	\N	230	\N
1508	2026-03-22 22:49:56.106831-03	2026-03-22 22:49:56.106833-03	f	\N	5	48	3034.50	2026-05-10	f	\N		\N	\N	230	\N
1509	2026-03-22 22:49:56.107318-03	2026-03-22 22:49:56.10732-03	f	\N	6	48	3034.50	2026-06-10	f	\N		\N	\N	230	\N
1510	2026-03-22 22:49:56.107804-03	2026-03-22 22:49:56.107806-03	f	\N	7	48	3034.50	2026-07-10	f	\N		\N	\N	230	\N
1511	2026-03-22 22:49:56.10835-03	2026-03-22 22:49:56.108352-03	f	\N	8	48	3034.50	2026-08-10	f	\N		\N	\N	230	\N
1512	2026-03-22 22:49:56.108761-03	2026-03-22 22:49:56.108763-03	f	\N	9	48	3034.50	2026-09-10	f	\N		\N	\N	230	\N
1513	2026-03-22 22:49:56.109209-03	2026-03-22 22:49:56.109211-03	f	\N	10	48	3034.50	2026-10-10	f	\N		\N	\N	230	\N
1514	2026-03-22 22:49:56.10992-03	2026-03-22 22:49:56.109922-03	f	\N	11	48	3034.50	2026-11-10	f	\N		\N	\N	230	\N
1515	2026-03-22 22:49:56.110867-03	2026-03-22 22:49:56.110869-03	f	\N	12	48	3034.50	2026-12-10	f	\N		\N	\N	230	\N
1516	2026-03-22 22:49:56.111464-03	2026-03-22 22:49:56.111466-03	f	\N	13	48	3034.50	2027-01-10	f	\N		\N	\N	230	\N
1517	2026-03-22 22:49:56.112086-03	2026-03-22 22:49:56.112088-03	f	\N	14	48	3034.50	2027-02-10	f	\N		\N	\N	230	\N
1518	2026-03-22 22:49:56.112545-03	2026-03-22 22:49:56.112546-03	f	\N	15	48	3034.50	2027-03-10	f	\N		\N	\N	230	\N
1519	2026-03-22 22:49:56.113054-03	2026-03-22 22:49:56.113056-03	f	\N	16	48	3034.50	2027-04-10	f	\N		\N	\N	230	\N
1520	2026-03-22 22:49:56.113665-03	2026-03-22 22:49:56.113683-03	f	\N	17	48	3034.50	2027-05-10	f	\N		\N	\N	230	\N
1521	2026-03-22 22:49:56.114493-03	2026-03-22 22:49:56.114495-03	f	\N	18	48	3034.50	2027-06-10	f	\N		\N	\N	230	\N
1522	2026-03-22 22:49:56.114976-03	2026-03-22 22:49:56.114978-03	f	\N	19	48	3034.50	2027-07-10	f	\N		\N	\N	230	\N
1523	2026-03-22 22:49:56.115791-03	2026-03-22 22:49:56.115795-03	f	\N	20	48	3034.50	2027-08-10	f	\N		\N	\N	230	\N
1524	2026-03-22 22:49:56.11647-03	2026-03-22 22:49:56.116472-03	f	\N	21	48	3034.50	2027-09-10	f	\N		\N	\N	230	\N
1525	2026-03-22 22:49:56.117162-03	2026-03-22 22:49:56.117165-03	f	\N	22	48	3034.50	2027-10-10	f	\N		\N	\N	230	\N
1526	2026-03-22 22:49:56.117663-03	2026-03-22 22:49:56.117665-03	f	\N	23	48	3034.50	2027-11-10	f	\N		\N	\N	230	\N
1527	2026-03-22 22:49:56.118096-03	2026-03-22 22:49:56.118098-03	f	\N	24	48	3034.50	2027-12-10	f	\N		\N	\N	230	\N
1528	2026-03-22 22:49:56.118577-03	2026-03-22 22:49:56.118578-03	f	\N	25	48	3034.50	2028-01-10	f	\N		\N	\N	230	\N
1529	2026-03-22 22:49:56.119099-03	2026-03-22 22:49:56.119101-03	f	\N	26	48	3034.50	2028-02-10	f	\N		\N	\N	230	\N
1530	2026-03-22 22:49:56.119594-03	2026-03-22 22:49:56.119596-03	f	\N	27	48	3034.50	2028-03-10	f	\N		\N	\N	230	\N
1531	2026-03-22 22:49:56.120067-03	2026-03-22 22:49:56.120068-03	f	\N	28	48	3034.50	2028-04-10	f	\N		\N	\N	230	\N
1532	2026-03-22 22:49:56.120608-03	2026-03-22 22:49:56.12061-03	f	\N	29	48	3034.50	2028-05-10	f	\N		\N	\N	230	\N
1533	2026-03-22 22:49:56.121079-03	2026-03-22 22:49:56.121081-03	f	\N	30	48	3034.50	2028-06-10	f	\N		\N	\N	230	\N
1534	2026-03-22 22:49:56.121528-03	2026-03-22 22:49:56.12153-03	f	\N	31	48	3034.50	2028-07-10	f	\N		\N	\N	230	\N
1535	2026-03-22 22:49:56.122037-03	2026-03-22 22:49:56.122039-03	f	\N	32	48	3034.50	2028-08-10	f	\N		\N	\N	230	\N
1536	2026-03-22 22:49:56.122465-03	2026-03-22 22:49:56.122467-03	f	\N	33	48	3034.50	2028-09-10	f	\N		\N	\N	230	\N
1537	2026-03-22 22:49:56.122901-03	2026-03-22 22:49:56.122903-03	f	\N	34	48	3034.50	2028-10-10	f	\N		\N	\N	230	\N
1538	2026-03-22 22:49:56.123327-03	2026-03-22 22:49:56.123329-03	f	\N	35	48	3034.50	2028-11-10	f	\N		\N	\N	230	\N
1539	2026-03-22 22:49:56.123688-03	2026-03-22 22:49:56.123689-03	f	\N	36	48	3034.50	2028-12-10	f	\N		\N	\N	230	\N
1540	2026-03-22 22:49:56.124078-03	2026-03-22 22:49:56.12408-03	f	\N	37	48	3034.50	2029-01-10	f	\N		\N	\N	230	\N
1541	2026-03-22 22:49:56.124487-03	2026-03-22 22:49:56.124489-03	f	\N	38	48	3034.50	2029-02-10	f	\N		\N	\N	230	\N
1542	2026-03-22 22:49:56.124932-03	2026-03-22 22:49:56.124934-03	f	\N	39	48	3034.50	2029-03-10	f	\N		\N	\N	230	\N
1543	2026-03-22 22:49:56.125364-03	2026-03-22 22:49:56.125365-03	f	\N	40	48	3034.50	2029-04-10	f	\N		\N	\N	230	\N
1544	2026-03-22 22:49:56.126005-03	2026-03-22 22:49:56.126006-03	f	\N	41	48	3034.50	2029-05-10	f	\N		\N	\N	230	\N
1545	2026-03-22 22:49:56.126486-03	2026-03-22 22:49:56.126488-03	f	\N	42	48	3034.50	2029-06-10	f	\N		\N	\N	230	\N
1546	2026-03-22 22:49:56.126994-03	2026-03-22 22:49:56.126996-03	f	\N	43	48	3034.50	2029-07-10	f	\N		\N	\N	230	\N
1547	2026-03-22 22:49:56.127465-03	2026-03-22 22:49:56.127467-03	f	\N	44	48	3034.50	2029-08-10	f	\N		\N	\N	230	\N
1548	2026-03-22 22:49:56.127891-03	2026-03-22 22:49:56.127893-03	f	\N	45	48	3034.50	2029-09-10	f	\N		\N	\N	230	\N
1549	2026-03-22 22:49:56.128323-03	2026-03-22 22:49:56.128324-03	f	\N	46	48	3034.50	2029-10-10	f	\N		\N	\N	230	\N
1550	2026-03-22 22:49:56.12882-03	2026-03-22 22:49:56.128822-03	f	\N	47	48	3034.50	2029-11-10	f	\N		\N	\N	230	\N
1551	2026-03-22 22:49:56.129307-03	2026-03-22 22:49:56.129309-03	f	\N	48	48	3034.50	2029-12-10	f	\N		\N	\N	230	\N
1552	2026-03-22 22:49:56.130329-03	2026-03-22 22:49:56.130334-03	f	\N	1	12	585.40	2026-01-10	t	2026-01-10		\N	\N	231	\N
1553	2026-03-22 22:49:56.130877-03	2026-03-22 22:49:56.130878-03	f	\N	2	12	585.40	2026-02-10	t	2026-02-10		\N	\N	231	\N
1554	2026-03-22 22:49:56.13135-03	2026-03-22 22:49:56.131352-03	f	\N	3	12	585.40	2026-03-10	f	\N		\N	\N	231	\N
1555	2026-03-22 22:49:56.131761-03	2026-03-22 22:49:56.131763-03	f	\N	4	12	585.40	2026-04-10	f	\N		\N	\N	231	\N
1556	2026-03-22 22:49:56.132187-03	2026-03-22 22:49:56.132189-03	f	\N	5	12	585.40	2026-05-10	f	\N		\N	\N	231	\N
1557	2026-03-22 22:49:56.132661-03	2026-03-22 22:49:56.132663-03	f	\N	6	12	585.40	2026-06-10	f	\N		\N	\N	231	\N
1558	2026-03-22 22:49:56.133113-03	2026-03-22 22:49:56.133115-03	f	\N	7	12	585.40	2026-07-10	f	\N		\N	\N	231	\N
1559	2026-03-22 22:49:56.133633-03	2026-03-22 22:49:56.133634-03	f	\N	8	12	585.40	2026-08-10	f	\N		\N	\N	231	\N
1560	2026-03-22 22:49:56.134067-03	2026-03-22 22:49:56.134069-03	f	\N	9	12	585.40	2026-09-10	f	\N		\N	\N	231	\N
1561	2026-03-22 22:49:56.13441-03	2026-03-22 22:49:56.134412-03	f	\N	10	12	585.40	2026-10-10	f	\N		\N	\N	231	\N
1562	2026-03-22 22:49:56.134775-03	2026-03-22 22:49:56.134777-03	f	\N	11	12	585.40	2026-11-10	f	\N		\N	\N	231	\N
1563	2026-03-22 22:49:56.135172-03	2026-03-22 22:49:56.135174-03	f	\N	12	12	585.40	2026-12-10	f	\N		\N	\N	231	\N
1564	2026-03-22 22:49:56.136135-03	2026-03-22 22:49:56.136136-03	f	\N	1	6	58.62	2026-02-10	t	2026-02-10		\N	\N	232	\N
1565	2026-03-22 22:49:56.136495-03	2026-03-22 22:49:56.136496-03	f	\N	2	6	58.62	2026-03-10	f	\N		\N	\N	232	\N
1566	2026-03-22 22:49:56.136954-03	2026-03-22 22:49:56.136955-03	f	\N	3	6	58.62	2026-04-10	f	\N		\N	\N	232	\N
1567	2026-03-22 22:49:56.137337-03	2026-03-22 22:49:56.137339-03	f	\N	4	6	58.62	2026-05-10	f	\N		\N	\N	232	\N
1568	2026-03-22 22:49:56.137761-03	2026-03-22 22:49:56.137763-03	f	\N	5	6	58.62	2026-06-10	f	\N		\N	\N	232	\N
1569	2026-03-22 22:49:56.138127-03	2026-03-22 22:49:56.138129-03	f	\N	6	6	58.62	2026-07-10	f	\N		\N	\N	232	\N
1570	2026-03-22 22:49:56.13912-03	2026-03-22 22:49:56.139122-03	f	\N	1	6	259.00	2026-01-10	t	2026-01-10		\N	\N	233	\N
1571	2026-03-22 22:49:56.139509-03	2026-03-22 22:49:56.13951-03	f	\N	2	6	259.00	2026-02-10	t	2026-02-10		\N	\N	233	\N
1572	2026-03-22 22:49:56.139886-03	2026-03-22 22:49:56.139887-03	f	\N	3	6	259.00	2026-03-10	f	\N		\N	\N	233	\N
1573	2026-03-22 22:49:56.140244-03	2026-03-22 22:49:56.140246-03	f	\N	4	6	259.00	2026-04-10	f	\N		\N	\N	233	\N
1574	2026-03-22 22:49:56.140679-03	2026-03-22 22:49:56.140681-03	f	\N	5	6	259.00	2026-05-10	f	\N		\N	\N	233	\N
1575	2026-03-22 22:49:56.141095-03	2026-03-22 22:49:56.141096-03	f	\N	6	6	259.00	2026-06-10	f	\N		\N	\N	233	\N
1576	2026-03-22 22:49:56.142261-03	2026-03-22 22:49:56.142263-03	f	\N	1	6	74.81	2026-02-10	t	2026-02-10		\N	\N	234	\N
1577	2026-03-22 22:49:56.142706-03	2026-03-22 22:49:56.142708-03	f	\N	2	6	74.81	2026-03-10	f	\N		\N	\N	234	\N
1578	2026-03-22 22:49:56.143127-03	2026-03-22 22:49:56.143129-03	f	\N	3	6	74.81	2026-04-10	f	\N		\N	\N	234	\N
1579	2026-03-22 22:49:56.143511-03	2026-03-22 22:49:56.143513-03	f	\N	4	6	74.81	2026-05-10	f	\N		\N	\N	234	\N
1580	2026-03-22 22:49:56.143878-03	2026-03-22 22:49:56.14388-03	f	\N	5	6	74.81	2026-06-10	f	\N		\N	\N	234	\N
1581	2026-03-22 22:49:56.144276-03	2026-03-22 22:49:56.144277-03	f	\N	6	6	74.81	2026-07-10	f	\N		\N	\N	234	\N
1582	2026-03-22 22:49:56.145128-03	2026-03-22 22:49:56.145129-03	f	\N	1	10	68.56	2026-03-10	f	\N		\N	\N	235	\N
1583	2026-03-22 22:49:56.145493-03	2026-03-22 22:49:56.145495-03	f	\N	2	10	68.56	2026-04-10	f	\N		\N	\N	235	\N
1584	2026-03-22 22:49:56.145848-03	2026-03-22 22:49:56.145849-03	f	\N	3	10	68.56	2026-05-10	f	\N		\N	\N	235	\N
1585	2026-03-22 22:49:56.146241-03	2026-03-22 22:49:56.146243-03	f	\N	4	10	68.56	2026-06-10	f	\N		\N	\N	235	\N
1586	2026-03-22 22:49:56.146633-03	2026-03-22 22:49:56.146634-03	f	\N	5	10	68.56	2026-07-10	f	\N		\N	\N	235	\N
1587	2026-03-22 22:49:56.14702-03	2026-03-22 22:49:56.147022-03	f	\N	6	10	68.56	2026-08-10	f	\N		\N	\N	235	\N
1588	2026-03-22 22:49:56.147396-03	2026-03-22 22:49:56.147398-03	f	\N	7	10	68.56	2026-09-10	f	\N		\N	\N	235	\N
1589	2026-03-22 22:49:56.147791-03	2026-03-22 22:49:56.147793-03	f	\N	8	10	68.56	2026-10-10	f	\N		\N	\N	235	\N
1590	2026-03-22 22:49:56.148205-03	2026-03-22 22:49:56.148207-03	f	\N	9	10	68.56	2026-11-10	f	\N		\N	\N	235	\N
1591	2026-03-22 22:49:56.148793-03	2026-03-22 22:49:56.148795-03	f	\N	10	10	68.56	2026-12-10	f	\N		\N	\N	235	\N
1592	2026-03-22 22:49:56.149726-03	2026-03-22 22:49:56.149728-03	f	\N	1	10	25.53	2026-03-10	f	\N		\N	\N	236	\N
1593	2026-03-22 22:49:56.150159-03	2026-03-22 22:49:56.150161-03	f	\N	2	10	25.53	2026-04-10	f	\N		\N	\N	236	\N
1594	2026-03-22 22:49:56.150581-03	2026-03-22 22:49:56.150583-03	f	\N	3	10	25.53	2026-05-10	f	\N		\N	\N	236	\N
1595	2026-03-22 22:49:56.150987-03	2026-03-22 22:49:56.150988-03	f	\N	4	10	25.53	2026-06-10	f	\N		\N	\N	236	\N
1596	2026-03-22 22:49:56.151404-03	2026-03-22 22:49:56.151406-03	f	\N	5	10	25.53	2026-07-10	f	\N		\N	\N	236	\N
1597	2026-03-22 22:49:56.151812-03	2026-03-22 22:49:56.151814-03	f	\N	6	10	25.53	2026-08-10	f	\N		\N	\N	236	\N
1598	2026-03-22 22:49:56.152148-03	2026-03-22 22:49:56.15215-03	f	\N	7	10	25.53	2026-09-10	f	\N		\N	\N	236	\N
1599	2026-03-22 22:49:56.152571-03	2026-03-22 22:49:56.152573-03	f	\N	8	10	25.53	2026-10-10	f	\N		\N	\N	236	\N
1600	2026-03-22 22:49:56.153004-03	2026-03-22 22:49:56.153005-03	f	\N	9	10	25.53	2026-11-10	f	\N		\N	\N	236	\N
1601	2026-03-22 22:49:56.153546-03	2026-03-22 22:49:56.153547-03	f	\N	10	10	25.53	2026-12-10	f	\N		\N	\N	236	\N
1602	2026-03-22 22:49:56.154482-03	2026-03-22 22:49:56.154484-03	f	\N	1	4	164.52	2026-03-10	f	\N		\N	\N	237	\N
1603	2026-03-22 22:49:56.154911-03	2026-03-22 22:49:56.154913-03	f	\N	2	4	164.52	2026-04-10	f	\N		\N	\N	237	\N
1604	2026-03-22 22:49:56.155303-03	2026-03-22 22:49:56.155305-03	f	\N	3	4	164.52	2026-05-10	f	\N		\N	\N	237	\N
1605	2026-03-22 22:49:56.155725-03	2026-03-22 22:49:56.155727-03	f	\N	4	4	164.52	2026-06-10	f	\N		\N	\N	237	\N
1606	2026-03-22 22:49:56.156559-03	2026-03-22 22:49:56.15656-03	f	\N	1	6	141.70	2026-03-10	f	\N		\N	\N	238	\N
1607	2026-03-22 22:49:56.156971-03	2026-03-22 22:49:56.156972-03	f	\N	2	6	141.70	2026-04-10	f	\N		\N	\N	238	\N
1608	2026-03-22 22:49:56.157628-03	2026-03-22 22:49:56.15763-03	f	\N	3	6	141.70	2026-05-10	f	\N		\N	\N	238	\N
1609	2026-03-22 22:49:56.158084-03	2026-03-22 22:49:56.158086-03	f	\N	4	6	141.70	2026-06-10	f	\N		\N	\N	238	\N
1610	2026-03-22 22:49:56.158521-03	2026-03-22 22:49:56.158523-03	f	\N	5	6	141.70	2026-07-10	f	\N		\N	\N	238	\N
1611	2026-03-22 22:49:56.159051-03	2026-03-22 22:49:56.159053-03	f	\N	6	6	141.70	2026-08-10	f	\N		\N	\N	238	\N
1612	2026-03-22 22:49:56.15999-03	2026-03-22 22:49:56.159992-03	f	\N	1	10	52.00	2026-03-10	f	\N		\N	\N	239	\N
1613	2026-03-22 22:49:56.160376-03	2026-03-22 22:49:56.160378-03	f	\N	2	10	52.00	2026-04-10	f	\N		\N	\N	239	\N
1614	2026-03-22 22:49:56.160789-03	2026-03-22 22:49:56.16079-03	f	\N	3	10	52.00	2026-05-10	f	\N		\N	\N	239	\N
1615	2026-03-22 22:49:56.161148-03	2026-03-22 22:49:56.161149-03	f	\N	4	10	52.00	2026-06-10	f	\N		\N	\N	239	\N
1616	2026-03-22 22:49:56.161602-03	2026-03-22 22:49:56.161604-03	f	\N	5	10	52.00	2026-07-10	f	\N		\N	\N	239	\N
1617	2026-03-22 22:49:56.162007-03	2026-03-22 22:49:56.162009-03	f	\N	6	10	52.00	2026-08-10	f	\N		\N	\N	239	\N
1618	2026-03-22 22:49:56.162455-03	2026-03-22 22:49:56.162456-03	f	\N	7	10	52.00	2026-09-10	f	\N		\N	\N	239	\N
1619	2026-03-22 22:49:56.162874-03	2026-03-22 22:49:56.162876-03	f	\N	8	10	52.00	2026-10-10	f	\N		\N	\N	239	\N
1620	2026-03-22 22:49:56.163219-03	2026-03-22 22:49:56.16322-03	f	\N	9	10	52.00	2026-11-10	f	\N		\N	\N	239	\N
1621	2026-03-22 22:49:56.163545-03	2026-03-22 22:49:56.163546-03	f	\N	10	10	52.00	2026-12-10	f	\N		\N	\N	239	\N
1622	2026-03-22 22:49:56.164522-03	2026-03-22 22:49:56.164524-03	f	\N	1	2	171.00	2026-03-10	f	\N		\N	\N	240	\N
1623	2026-03-22 22:49:56.164909-03	2026-03-22 22:49:56.164911-03	f	\N	2	2	171.00	2026-04-10	f	\N		\N	\N	240	\N
1624	2026-03-22 22:49:56.165791-03	2026-03-22 22:49:56.165793-03	f	\N	1	9	20.11	2026-03-10	f	\N		\N	\N	241	\N
1625	2026-03-22 22:49:56.166262-03	2026-03-22 22:49:56.166264-03	f	\N	2	9	20.11	2026-04-10	f	\N		\N	\N	241	\N
1626	2026-03-22 22:49:56.166841-03	2026-03-22 22:49:56.166843-03	f	\N	3	9	20.11	2026-05-10	f	\N		\N	\N	241	\N
1627	2026-03-22 22:49:56.167252-03	2026-03-22 22:49:56.167254-03	f	\N	4	9	20.11	2026-06-10	f	\N		\N	\N	241	\N
1628	2026-03-22 22:49:56.167645-03	2026-03-22 22:49:56.167647-03	f	\N	5	9	20.11	2026-07-10	f	\N		\N	\N	241	\N
1629	2026-03-22 22:49:56.168007-03	2026-03-22 22:49:56.168008-03	f	\N	6	9	20.11	2026-08-10	f	\N		\N	\N	241	\N
1630	2026-03-22 22:49:56.168383-03	2026-03-22 22:49:56.168384-03	f	\N	7	9	20.11	2026-09-10	f	\N		\N	\N	241	\N
1631	2026-03-22 22:49:56.168847-03	2026-03-22 22:49:56.168849-03	f	\N	8	9	20.11	2026-10-10	f	\N		\N	\N	241	\N
1632	2026-03-22 22:49:56.169229-03	2026-03-22 22:49:56.169231-03	f	\N	9	9	20.11	2026-11-10	f	\N		\N	\N	241	\N
1633	2026-03-22 22:49:56.170009-03	2026-03-22 22:49:56.170011-03	f	\N	1	10	295.00	2025-08-10	t	2025-08-10		\N	\N	242	\N
1634	2026-03-22 22:49:56.170365-03	2026-03-22 22:49:56.170367-03	f	\N	2	10	295.00	2025-09-10	t	2025-09-10		\N	\N	242	\N
1635	2026-03-22 22:49:56.170688-03	2026-03-22 22:49:56.17069-03	f	\N	3	10	295.00	2025-10-10	t	2025-10-10		\N	\N	242	\N
1636	2026-03-22 22:49:56.17103-03	2026-03-22 22:49:56.171032-03	f	\N	4	10	295.00	2025-11-10	t	2025-11-10		\N	\N	242	\N
1637	2026-03-22 22:49:56.171457-03	2026-03-22 22:49:56.171459-03	f	\N	5	10	295.00	2025-12-10	t	2025-12-10		\N	\N	242	\N
1638	2026-03-22 22:49:56.171905-03	2026-03-22 22:49:56.171907-03	f	\N	6	10	295.00	2026-01-10	t	2026-01-10		\N	\N	242	\N
1639	2026-03-22 22:49:56.172722-03	2026-03-22 22:49:56.172724-03	f	\N	7	10	295.00	2026-02-10	t	2026-02-10		\N	\N	242	\N
1640	2026-03-22 22:49:56.173126-03	2026-03-22 22:49:56.173128-03	f	\N	8	10	295.00	2026-03-10	f	\N		\N	\N	242	\N
1641	2026-03-22 22:49:56.173549-03	2026-03-22 22:49:56.173551-03	f	\N	9	10	295.00	2026-04-10	f	\N		\N	\N	242	\N
1642	2026-03-22 22:49:56.174006-03	2026-03-22 22:49:56.174008-03	f	\N	10	10	295.00	2026-05-10	f	\N		\N	\N	242	\N
1643	2026-03-22 22:49:56.17486-03	2026-03-22 22:49:56.174861-03	f	\N	1	12	337.50	2025-09-10	t	2025-09-10		\N	\N	243	\N
1644	2026-03-22 22:49:56.175275-03	2026-03-22 22:49:56.175277-03	f	\N	2	12	337.50	2025-10-10	t	2025-10-10		\N	\N	243	\N
1645	2026-03-22 22:49:56.175682-03	2026-03-22 22:49:56.175684-03	f	\N	3	12	337.50	2025-11-10	t	2025-11-10		\N	\N	243	\N
1646	2026-03-22 22:49:56.176119-03	2026-03-22 22:49:56.176121-03	f	\N	4	12	337.50	2025-12-10	t	2025-12-10		\N	\N	243	\N
1647	2026-03-22 22:49:56.176525-03	2026-03-22 22:49:56.176527-03	f	\N	5	12	337.50	2026-01-10	t	2026-01-10		\N	\N	243	\N
1648	2026-03-22 22:49:56.176974-03	2026-03-22 22:49:56.176976-03	f	\N	6	12	337.50	2026-02-10	t	2026-02-10		\N	\N	243	\N
1649	2026-03-22 22:49:56.177335-03	2026-03-22 22:49:56.177336-03	f	\N	7	12	337.50	2026-03-10	f	\N		\N	\N	243	\N
1650	2026-03-22 22:49:56.1777-03	2026-03-22 22:49:56.177702-03	f	\N	8	12	337.50	2026-04-10	f	\N		\N	\N	243	\N
1651	2026-03-22 22:49:56.1781-03	2026-03-22 22:49:56.178102-03	f	\N	9	12	337.50	2026-05-10	f	\N		\N	\N	243	\N
1652	2026-03-22 22:49:56.178646-03	2026-03-22 22:49:56.178648-03	f	\N	10	12	337.50	2026-06-10	f	\N		\N	\N	243	\N
1653	2026-03-22 22:49:56.179366-03	2026-03-22 22:49:56.179368-03	f	\N	11	12	337.50	2026-07-10	f	\N		\N	\N	243	\N
1654	2026-03-22 22:49:56.179796-03	2026-03-22 22:49:56.179798-03	f	\N	12	12	337.50	2026-08-10	f	\N		\N	\N	243	\N
2481	2026-03-23 19:19:17.087985-03	2026-03-23 19:19:17.087993-03	f	\N	8	12	337.00	2026-04-23	f	\N		\N	\N	292	\N
1656	2026-03-22 22:49:56.180913-03	2026-03-22 22:49:56.180915-03	f	\N	2	10	124.50	2026-04-10	f	\N		\N	\N	244	\N
1657	2026-03-22 22:49:56.181328-03	2026-03-22 22:49:56.18133-03	f	\N	3	10	124.50	2026-05-10	f	\N		\N	\N	244	\N
1658	2026-03-22 22:49:56.181697-03	2026-03-22 22:49:56.181699-03	f	\N	4	10	124.50	2026-06-10	f	\N		\N	\N	244	\N
1659	2026-03-22 22:49:56.1821-03	2026-03-22 22:49:56.182102-03	f	\N	5	10	124.50	2026-07-10	f	\N		\N	\N	244	\N
1660	2026-03-22 22:49:56.18254-03	2026-03-22 22:49:56.182542-03	f	\N	6	10	124.50	2026-08-10	f	\N		\N	\N	244	\N
1661	2026-03-22 22:49:56.182963-03	2026-03-22 22:49:56.182965-03	f	\N	7	10	124.50	2026-09-10	f	\N		\N	\N	244	\N
1662	2026-03-22 22:49:56.183396-03	2026-03-22 22:49:56.183398-03	f	\N	8	10	124.50	2026-10-10	f	\N		\N	\N	244	\N
1663	2026-03-22 22:49:56.18394-03	2026-03-22 22:49:56.183941-03	f	\N	9	10	124.50	2026-11-10	f	\N		\N	\N	244	\N
1664	2026-03-22 22:49:56.184332-03	2026-03-22 22:49:56.184334-03	f	\N	10	10	124.50	2026-12-10	f	\N		\N	\N	244	\N
1665	2026-03-22 22:49:56.185132-03	2026-03-22 22:49:56.185133-03	f	\N	1	48	1534.50	2026-01-10	t	2026-01-10		\N	\N	245	\N
1666	2026-03-22 22:49:56.185512-03	2026-03-22 22:49:56.185514-03	f	\N	2	48	1534.50	2026-02-10	t	2026-02-10		\N	\N	245	\N
1667	2026-03-22 22:49:56.185858-03	2026-03-22 22:49:56.18586-03	f	\N	3	48	1534.50	2026-03-10	f	\N		\N	\N	245	\N
1668	2026-03-22 22:49:56.186173-03	2026-03-22 22:49:56.186175-03	f	\N	4	48	1534.50	2026-04-10	f	\N		\N	\N	245	\N
1669	2026-03-22 22:49:56.186614-03	2026-03-22 22:49:56.186616-03	f	\N	5	48	1534.50	2026-05-10	f	\N		\N	\N	245	\N
1670	2026-03-22 22:49:56.187057-03	2026-03-22 22:49:56.187059-03	f	\N	6	48	1534.50	2026-06-10	f	\N		\N	\N	245	\N
1671	2026-03-22 22:49:56.187387-03	2026-03-22 22:49:56.187389-03	f	\N	7	48	1534.50	2026-07-10	f	\N		\N	\N	245	\N
1672	2026-03-22 22:49:56.187986-03	2026-03-22 22:49:56.187988-03	f	\N	8	48	1534.50	2026-08-10	f	\N		\N	\N	245	\N
1673	2026-03-22 22:49:56.188502-03	2026-03-22 22:49:56.188504-03	f	\N	9	48	1534.50	2026-09-10	f	\N		\N	\N	245	\N
1674	2026-03-22 22:49:56.189052-03	2026-03-22 22:49:56.189054-03	f	\N	10	48	1534.50	2026-10-10	f	\N		\N	\N	245	\N
1675	2026-03-22 22:49:56.189489-03	2026-03-22 22:49:56.189491-03	f	\N	11	48	1534.50	2026-11-10	f	\N		\N	\N	245	\N
1676	2026-03-22 22:49:56.189923-03	2026-03-22 22:49:56.189924-03	f	\N	12	48	1534.50	2026-12-10	f	\N		\N	\N	245	\N
1677	2026-03-22 22:49:56.190366-03	2026-03-22 22:49:56.190368-03	f	\N	13	48	1534.50	2027-01-10	f	\N		\N	\N	245	\N
1678	2026-03-22 22:49:56.190812-03	2026-03-22 22:49:56.190814-03	f	\N	14	48	1534.50	2027-02-10	f	\N		\N	\N	245	\N
1679	2026-03-22 22:49:56.191244-03	2026-03-22 22:49:56.191246-03	f	\N	15	48	1534.50	2027-03-10	f	\N		\N	\N	245	\N
1680	2026-03-22 22:49:56.191692-03	2026-03-22 22:49:56.191694-03	f	\N	16	48	1534.50	2027-04-10	f	\N		\N	\N	245	\N
1681	2026-03-22 22:49:56.192055-03	2026-03-22 22:49:56.192057-03	f	\N	17	48	1534.50	2027-05-10	f	\N		\N	\N	245	\N
1682	2026-03-22 22:49:56.192462-03	2026-03-22 22:49:56.192464-03	f	\N	18	48	1534.50	2027-06-10	f	\N		\N	\N	245	\N
1683	2026-03-22 22:49:56.192899-03	2026-03-22 22:49:56.192901-03	f	\N	19	48	1534.50	2027-07-10	f	\N		\N	\N	245	\N
1684	2026-03-22 22:49:56.193304-03	2026-03-22 22:49:56.193306-03	f	\N	20	48	1534.50	2027-08-10	f	\N		\N	\N	245	\N
1685	2026-03-22 22:49:56.193729-03	2026-03-22 22:49:56.193731-03	f	\N	21	48	1534.50	2027-09-10	f	\N		\N	\N	245	\N
1686	2026-03-22 22:49:56.194163-03	2026-03-22 22:49:56.194165-03	f	\N	22	48	1534.50	2027-10-10	f	\N		\N	\N	245	\N
1687	2026-03-22 22:49:56.19454-03	2026-03-22 22:49:56.194542-03	f	\N	23	48	1534.50	2027-11-10	f	\N		\N	\N	245	\N
1688	2026-03-22 22:49:56.194869-03	2026-03-22 22:49:56.194871-03	f	\N	24	48	1534.50	2027-12-10	f	\N		\N	\N	245	\N
1689	2026-03-22 22:49:56.195173-03	2026-03-22 22:49:56.195175-03	f	\N	25	48	1534.50	2028-01-10	f	\N		\N	\N	245	\N
1690	2026-03-22 22:49:56.195698-03	2026-03-22 22:49:56.1957-03	f	\N	26	48	1534.50	2028-02-10	f	\N		\N	\N	245	\N
1691	2026-03-22 22:49:56.19612-03	2026-03-22 22:49:56.196121-03	f	\N	27	48	1534.50	2028-03-10	f	\N		\N	\N	245	\N
1692	2026-03-22 22:49:56.196474-03	2026-03-22 22:49:56.196476-03	f	\N	28	48	1534.50	2028-04-10	f	\N		\N	\N	245	\N
1693	2026-03-22 22:49:56.196796-03	2026-03-22 22:49:56.196797-03	f	\N	29	48	1534.50	2028-05-10	f	\N		\N	\N	245	\N
1694	2026-03-22 22:49:56.197313-03	2026-03-22 22:49:56.197315-03	f	\N	30	48	1534.50	2028-06-10	f	\N		\N	\N	245	\N
1695	2026-03-22 22:49:56.197753-03	2026-03-22 22:49:56.197755-03	f	\N	31	48	1534.50	2028-07-10	f	\N		\N	\N	245	\N
1696	2026-03-22 22:49:56.198095-03	2026-03-22 22:49:56.198096-03	f	\N	32	48	1534.50	2028-08-10	f	\N		\N	\N	245	\N
1697	2026-03-22 22:49:56.198403-03	2026-03-22 22:49:56.198405-03	f	\N	33	48	1534.50	2028-09-10	f	\N		\N	\N	245	\N
1698	2026-03-22 22:49:56.198825-03	2026-03-22 22:49:56.198827-03	f	\N	34	48	1534.50	2028-10-10	f	\N		\N	\N	245	\N
1699	2026-03-22 22:49:56.199305-03	2026-03-22 22:49:56.199307-03	f	\N	35	48	1534.50	2028-11-10	f	\N		\N	\N	245	\N
1700	2026-03-22 22:49:56.199737-03	2026-03-22 22:49:56.199738-03	f	\N	36	48	1534.50	2028-12-10	f	\N		\N	\N	245	\N
1701	2026-03-22 22:49:56.200062-03	2026-03-22 22:49:56.200064-03	f	\N	37	48	1534.50	2029-01-10	f	\N		\N	\N	245	\N
1702	2026-03-22 22:49:56.20054-03	2026-03-22 22:49:56.200542-03	f	\N	38	48	1534.50	2029-02-10	f	\N		\N	\N	245	\N
1703	2026-03-22 22:49:56.201118-03	2026-03-22 22:49:56.20112-03	f	\N	39	48	1534.50	2029-03-10	f	\N		\N	\N	245	\N
1704	2026-03-22 22:49:56.201654-03	2026-03-22 22:49:56.201656-03	f	\N	40	48	1534.50	2029-04-10	f	\N		\N	\N	245	\N
1705	2026-03-22 22:49:56.202089-03	2026-03-22 22:49:56.202091-03	f	\N	41	48	1534.50	2029-05-10	f	\N		\N	\N	245	\N
1706	2026-03-22 22:49:56.202458-03	2026-03-22 22:49:56.20246-03	f	\N	42	48	1534.50	2029-06-10	f	\N		\N	\N	245	\N
1707	2026-03-22 22:49:56.202804-03	2026-03-22 22:49:56.202806-03	f	\N	43	48	1534.50	2029-07-10	f	\N		\N	\N	245	\N
1708	2026-03-22 22:49:56.203133-03	2026-03-22 22:49:56.203135-03	f	\N	44	48	1534.50	2029-08-10	f	\N		\N	\N	245	\N
1709	2026-03-22 22:49:56.203725-03	2026-03-22 22:49:56.203727-03	f	\N	45	48	1534.50	2029-09-10	f	\N		\N	\N	245	\N
1710	2026-03-22 22:49:56.204102-03	2026-03-22 22:49:56.204104-03	f	\N	46	48	1534.50	2029-10-10	f	\N		\N	\N	245	\N
1711	2026-03-22 22:49:56.204593-03	2026-03-22 22:49:56.204595-03	f	\N	47	48	1534.50	2029-11-10	f	\N		\N	\N	245	\N
1712	2026-03-22 22:49:56.204992-03	2026-03-22 22:49:56.204994-03	f	\N	48	48	1534.50	2029-12-10	f	\N		\N	\N	245	\N
1713	2026-03-22 22:49:56.213205-03	2026-03-22 22:49:56.213207-03	f	\N	1	24	629.35	2024-12-11	t	2024-12-11		\N	\N	257	\N
1714	2026-03-22 22:49:56.213645-03	2026-03-22 22:49:56.213647-03	f	\N	2	24	629.35	2025-01-11	t	2025-01-11		\N	\N	257	\N
1715	2026-03-22 22:49:56.214093-03	2026-03-22 22:49:56.214095-03	f	\N	3	24	629.35	2025-02-11	t	2025-02-11		\N	\N	257	\N
1716	2026-03-22 22:49:56.214531-03	2026-03-22 22:49:56.214533-03	f	\N	4	24	629.35	2025-03-11	t	2025-03-11		\N	\N	257	\N
1717	2026-03-22 22:49:56.214974-03	2026-03-22 22:49:56.214976-03	f	\N	5	24	629.35	2025-04-11	t	2025-04-11		\N	\N	257	\N
1718	2026-03-22 22:49:56.21538-03	2026-03-22 22:49:56.215382-03	f	\N	6	24	629.35	2025-05-11	t	2025-05-11		\N	\N	257	\N
1719	2026-03-22 22:49:56.21579-03	2026-03-22 22:49:56.215792-03	f	\N	7	24	629.35	2025-06-11	t	2025-06-11		\N	\N	257	\N
1720	2026-03-22 22:49:56.216182-03	2026-03-22 22:49:56.216184-03	f	\N	8	24	629.35	2025-07-11	t	2025-07-11		\N	\N	257	\N
1721	2026-03-22 22:49:56.216541-03	2026-03-22 22:49:56.216543-03	f	\N	9	24	629.35	2025-08-11	t	2025-08-11		\N	\N	257	\N
1722	2026-03-22 22:49:56.216957-03	2026-03-22 22:49:56.216958-03	f	\N	10	24	629.35	2025-09-11	t	2025-09-11		\N	\N	257	\N
1723	2026-03-22 22:49:56.217365-03	2026-03-22 22:49:56.217367-03	f	\N	11	24	629.35	2025-10-11	t	2025-10-11		\N	\N	257	\N
1724	2026-03-22 22:49:56.217714-03	2026-03-22 22:49:56.217716-03	f	\N	12	24	629.35	2025-11-11	t	2025-11-11		\N	\N	257	\N
1725	2026-03-22 22:49:56.218141-03	2026-03-22 22:49:56.218143-03	f	\N	13	24	629.35	2025-12-11	t	2025-12-11		\N	\N	257	\N
1726	2026-03-22 22:49:56.218619-03	2026-03-22 22:49:56.21862-03	f	\N	14	24	629.35	2026-01-11	t	2026-01-11		\N	\N	257	\N
1727	2026-03-22 22:49:56.21902-03	2026-03-22 22:49:56.219022-03	f	\N	15	24	629.35	2026-02-11	t	2026-02-11		\N	\N	257	\N
1729	2026-03-22 22:49:56.220414-03	2026-03-22 22:49:56.220417-03	f	\N	17	24	629.35	2026-04-11	f	\N		\N	\N	257	\N
1730	2026-03-22 22:49:56.22085-03	2026-03-22 22:49:56.220852-03	f	\N	18	24	629.35	2026-05-11	f	\N		\N	\N	257	\N
1731	2026-03-22 22:49:56.221285-03	2026-03-22 22:49:56.221287-03	f	\N	19	24	629.35	2026-06-11	f	\N		\N	\N	257	\N
1732	2026-03-22 22:49:56.221612-03	2026-03-22 22:49:56.221613-03	f	\N	20	24	629.35	2026-07-11	f	\N		\N	\N	257	\N
1733	2026-03-22 22:49:56.222011-03	2026-03-22 22:49:56.222013-03	f	\N	21	24	629.35	2026-08-11	f	\N		\N	\N	257	\N
1734	2026-03-22 22:49:56.222409-03	2026-03-22 22:49:56.222411-03	f	\N	22	24	629.35	2026-09-11	f	\N		\N	\N	257	\N
1735	2026-03-22 22:49:56.222831-03	2026-03-22 22:49:56.222833-03	f	\N	23	24	629.35	2026-10-11	f	\N		\N	\N	257	\N
1736	2026-03-22 22:49:56.223263-03	2026-03-22 22:49:56.223265-03	f	\N	24	24	629.35	2026-11-11	f	\N		\N	\N	257	\N
1737	2026-03-22 22:49:56.224266-03	2026-03-22 22:49:56.224268-03	t	2026-04-01 15:03:29.308341-03	1	60	850.00	2026-04-04	f	\N		\N	\N	258	\N
2560	2026-04-01 14:03:33.273433-03	2026-04-01 14:03:33.273436-03	f	\N	3	12	63.33	2026-03-04	t	2026-03-04		\N	\N	305	\N
1799	2026-03-22 22:49:56.251117-03	2026-03-22 22:49:56.251119-03	f	\N	3	10	0.00	2026-04-10	f	\N		\N	\N	259	\N
1800	2026-03-22 22:49:56.251734-03	2026-03-22 22:49:56.251735-03	f	\N	4	10	0.00	2026-05-10	f	\N		\N	\N	259	\N
1801	2026-03-22 22:49:56.252155-03	2026-03-22 22:49:56.252157-03	f	\N	5	10	0.00	2026-06-10	f	\N		\N	\N	259	\N
1802	2026-03-22 22:49:56.252537-03	2026-03-22 22:49:56.252538-03	f	\N	6	10	0.00	2026-07-10	f	\N		\N	\N	259	\N
1803	2026-03-22 22:49:56.252946-03	2026-03-22 22:49:56.252948-03	f	\N	7	10	0.00	2026-08-10	f	\N		\N	\N	259	\N
1804	2026-03-22 22:49:56.253408-03	2026-03-22 22:49:56.25341-03	f	\N	8	10	0.00	2026-09-10	f	\N		\N	\N	259	\N
1805	2026-03-22 22:49:56.253875-03	2026-03-22 22:49:56.253877-03	f	\N	9	10	0.00	2026-10-10	f	\N		\N	\N	259	\N
1806	2026-03-22 22:49:56.25435-03	2026-03-22 22:49:56.254352-03	f	\N	10	10	0.00	2026-11-10	f	\N		\N	\N	259	\N
1797	2026-03-22 22:49:56.25037-03	2026-03-30 15:37:52.278154-03	f	\N	1	10	0.00	2026-02-10	t	2026-03-30		\N	\N	259	\N
1798	2026-03-22 22:49:56.250765-03	2026-03-30 15:46:31.894085-03	f	\N	2	10	0.00	2026-03-10	t	2026-03-30		\N	\N	259	\N
2561	2026-04-01 14:03:33.318763-03	2026-04-01 14:03:33.318766-03	f	\N	4	12	63.33	2026-04-01	f	\N		\N	\N	305	\N
2573	2026-04-01 14:10:02.281553-03	2026-04-01 14:10:02.281556-03	f	\N	4	6	66.70	2026-06-01	f	\N		\N	\N	306	\N
2585	2026-04-01 14:10:37.793766-03	2026-04-01 14:10:37.793769-03	f	\N	10	10	125.00	2026-11-01	f	\N		\N	\N	307	\N
2211	2026-03-23 19:17:45.285977-03	2026-03-23 19:17:45.28598-03	t	2026-04-01 15:03:39.725269-03	270	510	90.00	2048-03-01	f	\N		3	\N	190	3
2189	2026-03-23 19:17:45.285271-03	2026-03-23 19:17:45.285273-03	t	2026-04-01 15:03:39.725269-03	248	510	90.00	2046-04-30	f	\N		3	\N	190	3
2011	2026-03-23 19:17:45.278968-03	2026-03-23 19:17:45.278969-03	t	2026-04-01 15:03:39.725269-03	70	510	90.00	2031-06-30	f	\N		3	\N	190	3
1965	2026-03-23 19:17:45.278213-03	2026-03-23 19:17:45.278214-03	t	2026-04-01 15:03:39.725269-03	24	510	90.00	2027-08-30	f	\N		3	\N	190	3
2044	2026-03-23 19:17:45.280158-03	2026-03-23 19:17:45.28016-03	t	2026-04-01 15:03:39.725269-03	103	510	90.00	2034-03-30	f	\N		3	\N	190	3
2333	2026-03-23 19:17:45.289602-03	2026-03-23 19:17:45.289604-03	t	2026-04-01 15:03:39.725269-03	392	510	90.00	2058-04-30	f	\N		3	\N	190	3
2099	2026-03-23 19:17:45.281933-03	2026-03-23 19:17:45.281936-03	t	2026-04-01 15:03:39.725269-03	158	510	90.00	2038-10-30	f	\N		3	\N	190	3
2035	2026-03-23 19:17:45.279869-03	2026-03-23 19:17:45.279872-03	t	2026-04-01 15:03:39.725269-03	94	510	90.00	2033-06-30	f	\N		3	\N	190	3
2198	2026-03-23 19:17:45.285562-03	2026-03-23 19:17:45.285564-03	t	2026-04-01 15:03:39.725269-03	257	510	90.00	2047-01-30	f	\N		3	\N	190	3
1655	2026-03-22 22:49:56.18058-03	2026-03-23 16:04:11.123114-03	f	\N	1	10	124.50	2026-03-10	f	\N		\N	\N	244	\N
1870	2026-03-23 17:12:54.073526-03	2026-03-23 17:12:54.073535-03	f	\N	1	1	95.50	2026-03-23	f	\N		3	\N	285	3
1871	2026-03-23 18:10:15.464425-03	2026-03-23 18:10:15.464435-03	f	\N	1	9	1200.00	2026-03-10	f	\N		\N	\N	185	\N
1872	2026-03-23 18:10:15.471351-03	2026-03-23 18:10:15.471355-03	f	\N	2	9	1200.00	2026-04-10	f	\N		\N	\N	185	\N
1873	2026-03-23 18:10:15.472864-03	2026-03-23 18:10:15.472869-03	f	\N	3	9	1200.00	2026-05-10	f	\N		\N	\N	185	\N
1874	2026-03-23 18:10:15.474234-03	2026-03-23 18:10:15.474238-03	f	\N	4	9	1200.00	2026-06-10	f	\N		\N	\N	185	\N
1875	2026-03-23 18:10:15.476481-03	2026-03-23 18:10:15.476487-03	f	\N	5	9	1200.00	2026-07-10	f	\N		\N	\N	185	\N
1876	2026-03-23 18:10:15.477764-03	2026-03-23 18:10:15.477769-03	f	\N	6	9	1200.00	2026-08-10	f	\N		\N	\N	185	\N
1877	2026-03-23 18:10:15.480716-03	2026-03-23 18:10:15.480721-03	f	\N	7	9	1200.00	2026-09-10	f	\N		\N	\N	185	\N
1878	2026-03-23 18:10:15.482072-03	2026-03-23 18:10:15.482076-03	f	\N	8	9	1200.00	2026-10-10	f	\N		\N	\N	185	\N
1879	2026-03-23 18:10:15.483193-03	2026-03-23 18:10:15.483196-03	f	\N	9	9	1200.00	2026-11-10	f	\N		\N	\N	185	\N
2482	2026-03-23 19:19:17.150106-03	2026-03-23 19:19:17.150115-03	f	\N	9	12	337.00	2026-05-23	f	\N		\N	\N	292	\N
2527	2026-03-23 19:24:00.401632-03	2026-03-23 19:24:00.40164-03	f	\N	3	4	250.00	2026-04-23	f	\N		\N	\N	293	\N
2538	2026-03-23 19:24:36.053547-03	2026-03-23 19:24:36.053556-03	f	\N	10	10	100.00	2026-11-23	f	\N		\N	\N	294	\N
2548	2026-03-30 13:03:01.964281-03	2026-03-30 13:03:01.964288-03	f	\N	10	12	723.16	2026-08-31	f	\N		\N	\N	297	\N
2159	2026-03-23 19:17:45.284215-03	2026-03-23 19:17:45.284216-03	t	2026-04-01 15:03:39.725269-03	218	510	90.00	2043-10-30	f	\N		3	\N	190	3
2180	2026-03-23 19:17:45.284985-03	2026-03-23 19:17:45.284988-03	t	2026-04-01 15:03:39.725269-03	239	510	90.00	2045-07-30	f	\N		3	\N	190	3
1952	2026-03-23 19:17:45.277988-03	2026-03-23 19:17:45.277989-03	t	2026-04-01 15:03:39.725269-03	11	510	90.00	2026-07-30	f	\N		3	\N	190	3
1853	2026-03-22 22:49:56.278146-03	2026-03-30 15:46:53.531255-03	f	\N	53	60	159.11	2026-03-31	t	2026-03-30		\N	\N	266	\N
1863	2026-03-22 22:49:56.284398-03	2026-03-22 22:49:56.2844-03	f	\N	1	60	236.59	2025-09-30	t	2025-09-30		\N	\N	269	\N
1855	2026-03-22 22:49:56.279565-03	2026-03-30 15:46:54.165374-03	f	\N	53	60	252.09	2026-03-31	t	2026-03-30		\N	\N	267	\N
1856	2026-03-22 22:49:56.2805-03	2026-03-22 22:49:56.280502-03	f	\N	1	60	210.51	2025-09-30	t	2025-09-30		\N	\N	268	\N
456	2026-03-22 22:49:55.597333-03	2026-03-22 22:49:55.597335-03	f	\N	6	8	21.75	2026-05-20	f	\N		\N	\N	180	\N
457	2026-03-22 22:49:55.597769-03	2026-03-22 22:49:55.597771-03	f	\N	7	8	21.75	2026-06-20	f	\N		\N	\N	180	\N
458	2026-03-22 22:49:55.598345-03	2026-03-22 22:49:55.598348-03	f	\N	8	8	21.75	2026-07-20	f	\N		\N	\N	180	\N
460	2026-03-22 22:49:55.599825-03	2026-03-22 22:49:55.599827-03	f	\N	2	8	26.69	2026-02-20	t	2026-02-20		\N	\N	181	\N
461	2026-03-22 22:49:55.600184-03	2026-03-22 22:49:55.600185-03	f	\N	3	8	26.69	2026-03-20	f	\N		\N	\N	181	\N
462	2026-03-22 22:49:55.600516-03	2026-03-22 22:49:55.600518-03	f	\N	4	8	26.69	2026-04-20	f	\N		\N	\N	181	\N
463	2026-03-22 22:49:55.600919-03	2026-03-22 22:49:55.60092-03	f	\N	5	8	26.69	2026-05-20	f	\N		\N	\N	181	\N
464	2026-03-22 22:49:55.601335-03	2026-03-22 22:49:55.601337-03	f	\N	6	8	26.69	2026-06-20	f	\N		\N	\N	181	\N
465	2026-03-22 22:49:55.601772-03	2026-03-22 22:49:55.601775-03	f	\N	7	8	26.69	2026-07-20	f	\N		\N	\N	181	\N
466	2026-03-22 22:49:55.602272-03	2026-03-22 22:49:55.602274-03	f	\N	8	8	26.69	2026-08-20	f	\N		\N	\N	181	\N
468	2026-03-22 22:49:55.603747-03	2026-03-22 22:49:55.603748-03	f	\N	2	2	25.15	2026-02-20	t	2026-02-20		\N	\N	182	\N
2001	2026-03-23 19:17:45.278802-03	2026-03-23 19:17:45.278803-03	t	2026-04-01 15:03:39.725269-03	60	510	90.00	2030-08-30	f	\N		3	\N	190	3
2101	2026-03-23 19:17:45.281999-03	2026-03-23 19:17:45.282001-03	t	2026-04-01 15:03:39.725269-03	160	510	90.00	2038-12-30	f	\N		3	\N	190	3
1950	2026-03-23 19:17:45.277953-03	2026-03-23 19:17:45.277954-03	t	2026-04-01 15:03:39.725269-03	9	510	90.00	2026-05-30	f	\N		3	\N	190	3
1852	2026-03-22 22:49:56.277745-03	2026-03-30 15:37:59.068056-03	f	\N	52	60	158.06	2026-02-27	t	2026-03-30		\N	\N	266	\N
1854	2026-03-22 22:49:56.279077-03	2026-03-30 15:38:01.511589-03	f	\N	52	60	250.43	2026-02-27	t	2026-03-30		\N	\N	267	\N
1857	2026-03-22 22:49:56.280948-03	2026-03-22 22:49:56.28095-03	f	\N	2	60	212.62	2025-10-31	t	2025-10-31		\N	\N	268	\N
1858	2026-03-22 22:49:56.281446-03	2026-03-22 22:49:56.281448-03	f	\N	3	60	214.73	2025-11-28	t	2025-12-28		\N	\N	268	\N
1859	2026-03-22 22:49:56.281842-03	2026-03-22 22:49:56.281843-03	f	\N	4	60	216.83	2025-12-30	t	2026-01-29		\N	\N	268	\N
1860	2026-03-22 22:49:56.282317-03	2026-03-22 22:49:56.282319-03	f	\N	5	60	218.94	2026-01-30	t	2026-01-29		\N	\N	268	\N
1862	2026-03-22 22:49:56.283323-03	2026-03-30 15:46:52.931031-03	f	\N	7	60	223.15	2026-03-31	t	2026-03-30		\N	\N	268	\N
1864	2026-03-22 22:49:56.284826-03	2026-03-22 22:49:56.284828-03	f	\N	2	60	238.95	2025-10-31	t	2025-10-31		\N	\N	269	\N
1865	2026-03-22 22:49:56.285214-03	2026-03-22 22:49:56.285215-03	f	\N	3	60	241.32	2025-11-28	t	2025-12-28		\N	\N	269	\N
1866	2026-03-22 22:49:56.28557-03	2026-03-22 22:49:56.285572-03	f	\N	4	60	243.68	2025-12-30	t	2026-01-29		\N	\N	269	\N
1867	2026-03-22 22:49:56.285912-03	2026-03-22 22:49:56.285914-03	f	\N	5	60	246.05	2026-01-30	t	2026-01-29		\N	\N	269	\N
1869	2026-03-22 22:49:56.286769-03	2026-03-30 15:46:51.657276-03	f	\N	7	60	250.78	2026-03-31	t	2026-03-30		\N	\N	269	\N
1868	2026-03-22 22:49:56.286326-03	2026-03-30 15:38:03.998396-03	f	\N	6	60	248.41	2026-02-27	t	2026-03-30		\N	\N	269	\N
2483	2026-03-23 19:19:17.227884-03	2026-03-23 19:19:17.227891-03	f	\N	10	12	337.00	2026-06-23	f	\N		\N	\N	292	\N
2528	2026-03-23 19:24:00.471153-03	2026-03-23 19:24:00.471161-03	f	\N	4	4	250.00	2026-05-23	f	\N		\N	\N	293	\N
2549	2026-03-30 13:03:02.012385-03	2026-03-30 13:03:02.012388-03	f	\N	11	12	723.16	2026-10-01	f	\N		\N	\N	297	\N
2562	2026-04-01 14:03:33.357237-03	2026-04-01 14:03:33.35724-03	f	\N	5	12	63.33	2026-05-02	f	\N		\N	\N	305	\N
2574	2026-04-01 14:10:02.321187-03	2026-04-01 14:10:02.32119-03	f	\N	5	6	66.70	2026-07-02	f	\N		\N	\N	306	\N
1910	2026-03-23 18:50:14.84398-03	2026-03-23 18:50:14.843987-03	f	\N	13	15	294.00	2026-03-30	f	\N		3	\N	187	3
1911	2026-03-23 18:50:14.86311-03	2026-03-23 18:50:14.863117-03	f	\N	14	15	294.00	2026-04-30	f	\N		3	\N	187	3
1912	2026-03-23 18:50:14.8646-03	2026-03-23 18:50:14.864605-03	f	\N	15	15	294.00	2026-05-30	f	\N		3	\N	187	3
1913	2026-03-23 18:52:41.184634-03	2026-03-23 18:52:41.18464-03	f	\N	12	15	294.00	2026-02-28	t	2026-02-28		3	\N	187	3
1914	2026-03-23 18:58:15.637224-03	2026-03-23 18:58:15.637233-03	f	\N	1	6	57.53	2026-01-23	t	2026-01-23		3	\N	288	3
1915	2026-03-23 18:58:15.641608-03	2026-03-23 18:58:15.641613-03	f	\N	2	6	57.53	2026-02-23	t	2026-02-23		3	\N	288	3
1916	2026-03-23 18:58:15.643739-03	2026-03-23 18:58:15.643744-03	f	\N	3	6	57.53	2026-03-23	f	\N		3	\N	288	3
1917	2026-03-23 18:58:15.645238-03	2026-03-23 18:58:15.645244-03	f	\N	4	6	57.53	2026-04-23	f	\N		3	\N	288	3
1918	2026-03-23 18:58:15.646472-03	2026-03-23 18:58:15.646476-03	f	\N	5	6	57.53	2026-05-23	f	\N		3	\N	288	3
1919	2026-03-23 18:58:15.648013-03	2026-03-23 18:58:15.648017-03	f	\N	6	6	57.53	2026-06-23	f	\N		3	\N	288	3
1920	2026-03-23 19:17:07.833275-03	2026-03-23 19:17:07.833283-03	f	\N	1	10	202.00	2025-08-23	t	2025-08-23		\N	\N	291	\N
1921	2026-03-23 19:17:07.906453-03	2026-03-23 19:17:07.90646-03	f	\N	2	10	202.00	2025-09-23	t	2025-09-23		\N	\N	291	\N
1922	2026-03-23 19:17:07.984085-03	2026-03-23 19:17:07.984093-03	f	\N	3	10	202.00	2025-10-23	t	2025-10-23		\N	\N	291	\N
1923	2026-03-23 19:17:08.066141-03	2026-03-23 19:17:08.066149-03	f	\N	4	10	202.00	2025-11-23	t	2025-11-23		\N	\N	291	\N
1924	2026-03-23 19:17:08.138995-03	2026-03-23 19:17:08.139002-03	f	\N	5	10	202.00	2025-12-23	t	2025-12-23		\N	\N	291	\N
1925	2026-03-23 19:17:08.206202-03	2026-03-23 19:17:08.20621-03	f	\N	6	10	202.00	2026-01-23	t	2026-01-23		\N	\N	291	\N
1926	2026-03-23 19:17:08.281007-03	2026-03-23 19:17:08.281015-03	f	\N	7	10	202.00	2026-02-23	t	2026-02-23		\N	\N	291	\N
1927	2026-03-23 19:17:08.364012-03	2026-03-23 19:17:08.36402-03	f	\N	8	10	202.00	2026-03-23	f	\N		\N	\N	291	\N
1928	2026-03-23 19:17:08.465684-03	2026-03-23 19:17:08.465692-03	f	\N	9	10	202.00	2026-04-23	f	\N		\N	\N	291	\N
1929	2026-03-23 19:17:08.538217-03	2026-03-23 19:17:08.538225-03	f	\N	10	10	202.00	2026-05-23	f	\N		\N	\N	291	\N
1930	2026-03-23 19:17:28.807068-03	2026-03-23 19:17:28.807075-03	f	\N	1	12	150.00	2025-09-30	t	2025-09-30		3	\N	189	3
1931	2026-03-23 19:17:28.807153-03	2026-03-23 19:17:28.807156-03	f	\N	2	12	150.00	2025-10-30	t	2025-10-30		3	\N	189	3
1932	2026-03-23 19:17:28.807186-03	2026-03-23 19:17:28.807189-03	f	\N	3	12	150.00	2025-11-30	t	2025-11-30		3	\N	189	3
1933	2026-03-23 19:17:28.807215-03	2026-03-23 19:17:28.807218-03	f	\N	4	12	150.00	2025-12-30	t	2025-12-30		3	\N	189	3
1934	2026-03-23 19:17:28.807244-03	2026-03-23 19:17:28.807246-03	f	\N	5	12	150.00	2026-01-30	t	2026-01-30		3	\N	189	3
1935	2026-03-23 19:17:28.80727-03	2026-03-23 19:17:28.807272-03	f	\N	6	12	150.00	2026-03-02	t	2026-03-02		3	\N	189	3
1936	2026-03-23 19:17:28.807297-03	2026-03-23 19:17:28.807299-03	f	\N	7	12	150.00	2026-03-30	f	\N		3	\N	189	3
1937	2026-03-23 19:17:28.807324-03	2026-03-23 19:17:28.807326-03	f	\N	8	12	150.00	2026-04-30	f	\N		3	\N	189	3
1938	2026-03-23 19:17:28.80735-03	2026-03-23 19:17:28.807353-03	f	\N	9	12	150.00	2026-05-30	f	\N		3	\N	189	3
1939	2026-03-23 19:17:28.807377-03	2026-03-23 19:17:28.807379-03	f	\N	10	12	150.00	2026-06-30	f	\N		3	\N	189	3
1940	2026-03-23 19:17:28.807405-03	2026-03-23 19:17:28.807407-03	f	\N	11	12	150.00	2026-07-30	f	\N		3	\N	189	3
1941	2026-03-23 19:17:28.80743-03	2026-03-23 19:17:28.807432-03	f	\N	12	12	150.00	2026-08-30	f	\N		3	\N	189	3
2586	2026-04-01 14:10:57.850843-03	2026-04-01 14:10:57.850846-03	f	\N	1	6	50.00	2026-03-04	t	2026-03-04		\N	\N	308	\N
1845	2026-03-22 22:49:56.274414-03	2026-03-22 22:49:56.274416-03	f	\N	1	60	125.98	2025-09-30	t	2025-09-30		\N	\N	265	\N
1846	2026-03-22 22:49:56.2749-03	2026-03-22 22:49:56.274902-03	f	\N	2	60	127.23	2025-10-31	t	2025-11-28		\N	\N	265	\N
1847	2026-03-22 22:49:56.275336-03	2026-03-22 22:49:56.275338-03	f	\N	3	60	128.49	2025-11-28	t	2025-12-28		\N	\N	265	\N
1848	2026-03-22 22:49:56.275748-03	2026-03-22 22:49:56.27575-03	f	\N	4	60	129.75	2025-12-30	t	2026-01-29		\N	\N	265	\N
1849	2026-03-22 22:49:56.276072-03	2026-03-22 22:49:56.276074-03	f	\N	5	60	131.01	2026-01-30	t	2026-01-29		\N	\N	265	\N
1851	2026-03-22 22:49:56.276813-03	2026-03-30 15:46:52.341225-03	f	\N	7	60	133.53	2026-03-31	t	2026-03-30		\N	\N	265	\N
1850	2026-03-22 22:49:56.276455-03	2026-03-30 15:37:58.327089-03	f	\N	6	60	132.27	2026-02-27	t	2026-03-30		\N	\N	265	\N
2751	2026-04-01 15:25:34.210107-03	2026-04-01 15:25:34.210109-03	f	\N	8	60	133.53	2026-04-30	f	\N		\N	\N	265	\N
2752	2026-04-01 15:25:34.210696-03	2026-04-01 15:25:34.210698-03	f	\N	9	60	133.53	2026-05-31	f	\N		\N	\N	265	\N
2753	2026-04-01 15:25:34.211219-03	2026-04-01 15:25:34.211222-03	f	\N	10	60	133.53	2026-06-30	f	\N		\N	\N	265	\N
2754	2026-04-01 15:25:34.211774-03	2026-04-01 15:25:34.211775-03	f	\N	11	60	133.53	2026-07-31	f	\N		\N	\N	265	\N
2755	2026-04-01 15:25:34.212332-03	2026-04-01 15:25:34.212334-03	f	\N	12	60	133.53	2026-08-31	f	\N		\N	\N	265	\N
2756	2026-04-01 15:25:34.212841-03	2026-04-01 15:25:34.212843-03	f	\N	13	60	133.53	2026-09-30	f	\N		\N	\N	265	\N
2757	2026-04-01 15:25:34.21336-03	2026-04-01 15:25:34.213361-03	f	\N	14	60	133.53	2026-10-31	f	\N		\N	\N	265	\N
2758	2026-04-01 15:25:34.21393-03	2026-04-01 15:25:34.213932-03	f	\N	15	60	133.53	2026-11-30	f	\N		\N	\N	265	\N
2759	2026-04-01 15:25:34.214435-03	2026-04-01 15:25:34.214437-03	f	\N	16	60	133.53	2026-12-31	f	\N		\N	\N	265	\N
2760	2026-04-01 15:25:34.214965-03	2026-04-01 15:25:34.214967-03	f	\N	17	60	133.53	2027-01-31	f	\N		\N	\N	265	\N
2761	2026-04-01 15:25:34.215453-03	2026-04-01 15:25:34.215455-03	f	\N	18	60	133.53	2027-02-28	f	\N		\N	\N	265	\N
2762	2026-04-01 15:25:34.215962-03	2026-04-01 15:25:34.215964-03	f	\N	19	60	133.53	2027-03-31	f	\N		\N	\N	265	\N
2763	2026-04-01 15:25:34.216477-03	2026-04-01 15:25:34.216478-03	f	\N	20	60	133.53	2027-04-30	f	\N		\N	\N	265	\N
2764	2026-04-01 15:25:34.216992-03	2026-04-01 15:25:34.216994-03	f	\N	21	60	133.53	2027-05-31	f	\N		\N	\N	265	\N
2765	2026-04-01 15:25:34.217588-03	2026-04-01 15:25:34.21759-03	f	\N	22	60	133.53	2027-06-30	f	\N		\N	\N	265	\N
2766	2026-04-01 15:25:34.21813-03	2026-04-01 15:25:34.218131-03	f	\N	23	60	133.53	2027-07-31	f	\N		\N	\N	265	\N
2767	2026-04-01 15:25:34.218646-03	2026-04-01 15:25:34.218647-03	f	\N	24	60	133.53	2027-08-31	f	\N		\N	\N	265	\N
2768	2026-04-01 15:25:34.219159-03	2026-04-01 15:25:34.219161-03	f	\N	25	60	133.53	2027-09-30	f	\N		\N	\N	265	\N
2769	2026-04-01 15:25:34.219654-03	2026-04-01 15:25:34.219655-03	f	\N	26	60	133.53	2027-10-31	f	\N		\N	\N	265	\N
2770	2026-04-01 15:25:34.220123-03	2026-04-01 15:25:34.220124-03	f	\N	27	60	133.53	2027-11-30	f	\N		\N	\N	265	\N
2771	2026-04-01 15:25:34.220599-03	2026-04-01 15:25:34.2206-03	f	\N	28	60	133.53	2027-12-31	f	\N		\N	\N	265	\N
2772	2026-04-01 15:25:34.221073-03	2026-04-01 15:25:34.221075-03	f	\N	29	60	133.53	2028-01-31	f	\N		\N	\N	265	\N
2773	2026-04-01 15:25:34.221532-03	2026-04-01 15:25:34.221534-03	f	\N	30	60	133.53	2028-02-29	f	\N		\N	\N	265	\N
2774	2026-04-01 15:25:34.221974-03	2026-04-01 15:25:34.221975-03	f	\N	31	60	133.53	2028-03-31	f	\N		\N	\N	265	\N
2775	2026-04-01 15:25:34.222395-03	2026-04-01 15:25:34.222396-03	f	\N	32	60	133.53	2028-04-30	f	\N		\N	\N	265	\N
2776	2026-04-01 15:25:34.22286-03	2026-04-01 15:25:34.222861-03	f	\N	33	60	133.53	2028-05-31	f	\N		\N	\N	265	\N
2777	2026-04-01 15:25:34.223291-03	2026-04-01 15:25:34.223292-03	f	\N	34	60	133.53	2028-06-30	f	\N		\N	\N	265	\N
2778	2026-04-01 15:25:34.223776-03	2026-04-01 15:25:34.223779-03	f	\N	35	60	133.53	2028-07-31	f	\N		\N	\N	265	\N
2779	2026-04-01 15:25:34.224308-03	2026-04-01 15:25:34.22431-03	f	\N	36	60	133.53	2028-08-31	f	\N		\N	\N	265	\N
2780	2026-04-01 15:25:34.224797-03	2026-04-01 15:25:34.224799-03	f	\N	37	60	133.53	2028-09-30	f	\N		\N	\N	265	\N
2781	2026-04-01 15:25:34.225359-03	2026-04-01 15:25:34.225361-03	f	\N	38	60	133.53	2028-10-31	f	\N		\N	\N	265	\N
2782	2026-04-01 15:25:34.225888-03	2026-04-01 15:25:34.22589-03	f	\N	39	60	133.53	2028-11-30	f	\N		\N	\N	265	\N
2783	2026-04-01 15:25:34.226389-03	2026-04-01 15:25:34.22639-03	f	\N	40	60	133.53	2028-12-31	f	\N		\N	\N	265	\N
2784	2026-04-01 15:25:34.226914-03	2026-04-01 15:25:34.226917-03	f	\N	41	60	133.53	2029-01-31	f	\N		\N	\N	265	\N
2785	2026-04-01 15:25:34.227498-03	2026-04-01 15:25:34.2275-03	f	\N	42	60	133.53	2029-02-28	f	\N		\N	\N	265	\N
2786	2026-04-01 15:25:34.228016-03	2026-04-01 15:25:34.228017-03	f	\N	43	60	133.53	2029-03-31	f	\N		\N	\N	265	\N
2787	2026-04-01 15:25:34.228566-03	2026-04-01 15:25:34.228567-03	f	\N	44	60	133.53	2029-04-30	f	\N		\N	\N	265	\N
2788	2026-04-01 15:25:34.229129-03	2026-04-01 15:25:34.22913-03	f	\N	45	60	133.53	2029-05-31	f	\N		\N	\N	265	\N
2789	2026-04-01 15:25:34.229651-03	2026-04-01 15:25:34.229653-03	f	\N	46	60	133.53	2029-06-30	f	\N		\N	\N	265	\N
2790	2026-04-01 15:25:34.230154-03	2026-04-01 15:25:34.230156-03	f	\N	47	60	133.53	2029-07-31	f	\N		\N	\N	265	\N
2791	2026-04-01 15:25:34.230644-03	2026-04-01 15:25:34.230645-03	f	\N	48	60	133.53	2029-08-31	f	\N		\N	\N	265	\N
2792	2026-04-01 15:25:34.231156-03	2026-04-01 15:25:34.231158-03	f	\N	49	60	133.53	2029-09-30	f	\N		\N	\N	265	\N
2793	2026-04-01 15:25:34.231676-03	2026-04-01 15:25:34.231678-03	f	\N	50	60	133.53	2029-10-31	f	\N		\N	\N	265	\N
2794	2026-04-01 15:25:34.232181-03	2026-04-01 15:25:34.232182-03	f	\N	51	60	133.53	2029-11-30	f	\N		\N	\N	265	\N
2795	2026-04-01 15:25:34.232728-03	2026-04-01 15:25:34.23273-03	f	\N	52	60	133.53	2029-12-31	f	\N		\N	\N	265	\N
2796	2026-04-01 15:25:34.233232-03	2026-04-01 15:25:34.233234-03	f	\N	53	60	133.53	2030-01-31	f	\N		\N	\N	265	\N
2797	2026-04-01 15:25:34.233874-03	2026-04-01 15:25:34.233876-03	f	\N	54	60	133.53	2030-02-28	f	\N		\N	\N	265	\N
2798	2026-04-01 15:25:34.234396-03	2026-04-01 15:25:34.234398-03	f	\N	55	60	133.53	2030-03-31	f	\N		\N	\N	265	\N
2799	2026-04-01 15:25:34.23493-03	2026-04-01 15:25:34.234932-03	f	\N	56	60	133.53	2030-04-30	f	\N		\N	\N	265	\N
2800	2026-04-01 15:25:34.235444-03	2026-04-01 15:25:34.235448-03	f	\N	57	60	133.53	2030-05-31	f	\N		\N	\N	265	\N
2801	2026-04-01 15:25:34.23596-03	2026-04-01 15:25:34.235961-03	f	\N	58	60	133.53	2030-06-30	f	\N		\N	\N	265	\N
2802	2026-04-01 15:25:34.23658-03	2026-04-01 15:25:34.236582-03	f	\N	59	60	133.53	2030-07-31	f	\N		\N	\N	265	\N
2803	2026-04-01 15:25:34.237107-03	2026-04-01 15:25:34.237108-03	f	\N	60	60	133.53	2030-08-31	f	\N		\N	\N	265	\N
2804	2026-04-01 15:25:34.239522-03	2026-04-01 15:25:34.239524-03	f	\N	54	60	159.11	2026-04-30	f	\N		\N	\N	266	\N
2805	2026-04-01 15:25:34.240099-03	2026-04-01 15:25:34.240101-03	f	\N	55	60	159.11	2026-05-31	f	\N		\N	\N	266	\N
2806	2026-04-01 15:25:34.240662-03	2026-04-01 15:25:34.240664-03	f	\N	56	60	159.11	2026-06-30	f	\N		\N	\N	266	\N
2807	2026-04-01 15:25:34.241125-03	2026-04-01 15:25:34.241127-03	f	\N	57	60	159.11	2026-07-31	f	\N		\N	\N	266	\N
2808	2026-04-01 15:25:34.241613-03	2026-04-01 15:25:34.241615-03	f	\N	58	60	159.11	2026-08-31	f	\N		\N	\N	266	\N
2809	2026-04-01 15:25:34.242066-03	2026-04-01 15:25:34.242067-03	f	\N	59	60	159.11	2026-09-30	f	\N		\N	\N	266	\N
2810	2026-04-01 15:25:34.242606-03	2026-04-01 15:25:34.242608-03	f	\N	60	60	159.11	2026-10-31	f	\N		\N	\N	266	\N
2811	2026-04-01 15:25:34.244789-03	2026-04-01 15:25:34.244791-03	f	\N	54	60	252.09	2026-04-30	f	\N		\N	\N	267	\N
2812	2026-04-01 15:25:34.245323-03	2026-04-01 15:25:34.245325-03	f	\N	55	60	252.09	2026-05-31	f	\N		\N	\N	267	\N
2813	2026-04-01 15:25:34.24582-03	2026-04-01 15:25:34.245822-03	f	\N	56	60	252.09	2026-06-30	f	\N		\N	\N	267	\N
2814	2026-04-01 15:25:34.246332-03	2026-04-01 15:25:34.246333-03	f	\N	57	60	252.09	2026-07-31	f	\N		\N	\N	267	\N
2815	2026-04-01 15:25:34.246849-03	2026-04-01 15:25:34.246851-03	f	\N	58	60	252.09	2026-08-31	f	\N		\N	\N	267	\N
2816	2026-04-01 15:25:34.247371-03	2026-04-01 15:25:34.247373-03	f	\N	59	60	252.09	2026-09-30	f	\N		\N	\N	267	\N
2817	2026-04-01 15:25:34.247891-03	2026-04-01 15:25:34.247892-03	f	\N	60	60	252.09	2026-10-31	f	\N		\N	\N	267	\N
1861	2026-03-22 22:49:56.282713-03	2026-03-30 15:38:02.47652-03	f	\N	6	60	221.04	2026-02-27	t	2026-03-30		\N	\N	268	\N
2818	2026-04-01 15:25:34.250162-03	2026-04-01 15:25:34.250163-03	f	\N	8	60	223.15	2026-04-30	f	\N		\N	\N	268	\N
2819	2026-04-01 15:25:34.250688-03	2026-04-01 15:25:34.25069-03	f	\N	9	60	223.15	2026-05-31	f	\N		\N	\N	268	\N
2820	2026-04-01 15:25:34.251187-03	2026-04-01 15:25:34.251189-03	f	\N	10	60	223.15	2026-06-30	f	\N		\N	\N	268	\N
2821	2026-04-01 15:25:34.251717-03	2026-04-01 15:25:34.251719-03	f	\N	11	60	223.15	2026-07-31	f	\N		\N	\N	268	\N
2822	2026-04-01 15:25:34.252217-03	2026-04-01 15:25:34.252219-03	f	\N	12	60	223.15	2026-08-31	f	\N		\N	\N	268	\N
2823	2026-04-01 15:25:34.25274-03	2026-04-01 15:25:34.252741-03	f	\N	13	60	223.15	2026-09-30	f	\N		\N	\N	268	\N
2824	2026-04-01 15:25:34.253272-03	2026-04-01 15:25:34.253274-03	f	\N	14	60	223.15	2026-10-31	f	\N		\N	\N	268	\N
2825	2026-04-01 15:25:34.253783-03	2026-04-01 15:25:34.253785-03	f	\N	15	60	223.15	2026-11-30	f	\N		\N	\N	268	\N
2826	2026-04-01 15:25:34.254296-03	2026-04-01 15:25:34.254298-03	f	\N	16	60	223.15	2026-12-31	f	\N		\N	\N	268	\N
2827	2026-04-01 15:25:34.254791-03	2026-04-01 15:25:34.254793-03	f	\N	17	60	223.15	2027-01-31	f	\N		\N	\N	268	\N
2828	2026-04-01 15:25:34.255288-03	2026-04-01 15:25:34.25529-03	f	\N	18	60	223.15	2027-02-28	f	\N		\N	\N	268	\N
2829	2026-04-01 15:25:34.255826-03	2026-04-01 15:25:34.255828-03	f	\N	19	60	223.15	2027-03-31	f	\N		\N	\N	268	\N
2830	2026-04-01 15:25:34.256334-03	2026-04-01 15:25:34.256336-03	f	\N	20	60	223.15	2027-04-30	f	\N		\N	\N	268	\N
2831	2026-04-01 15:25:34.256862-03	2026-04-01 15:25:34.256864-03	f	\N	21	60	223.15	2027-05-31	f	\N		\N	\N	268	\N
2832	2026-04-01 15:25:34.257406-03	2026-04-01 15:25:34.257408-03	f	\N	22	60	223.15	2027-06-30	f	\N		\N	\N	268	\N
2833	2026-04-01 15:25:34.258355-03	2026-04-01 15:25:34.258356-03	f	\N	23	60	223.15	2027-07-31	f	\N		\N	\N	268	\N
2834	2026-04-01 15:25:34.258872-03	2026-04-01 15:25:34.258874-03	f	\N	24	60	223.15	2027-08-31	f	\N		\N	\N	268	\N
2835	2026-04-01 15:25:34.259402-03	2026-04-01 15:25:34.259404-03	f	\N	25	60	223.15	2027-09-30	f	\N		\N	\N	268	\N
2836	2026-04-01 15:25:34.259936-03	2026-04-01 15:25:34.259938-03	f	\N	26	60	223.15	2027-10-31	f	\N		\N	\N	268	\N
2837	2026-04-01 15:25:34.260467-03	2026-04-01 15:25:34.260469-03	f	\N	27	60	223.15	2027-11-30	f	\N		\N	\N	268	\N
2838	2026-04-01 15:25:34.260971-03	2026-04-01 15:25:34.260973-03	f	\N	28	60	223.15	2027-12-31	f	\N		\N	\N	268	\N
2839	2026-04-01 15:25:34.261546-03	2026-04-01 15:25:34.261548-03	f	\N	29	60	223.15	2028-01-31	f	\N		\N	\N	268	\N
2840	2026-04-01 15:25:34.262071-03	2026-04-01 15:25:34.262073-03	f	\N	30	60	223.15	2028-02-29	f	\N		\N	\N	268	\N
2841	2026-04-01 15:25:34.262623-03	2026-04-01 15:25:34.262625-03	f	\N	31	60	223.15	2028-03-31	f	\N		\N	\N	268	\N
2842	2026-04-01 15:25:34.26311-03	2026-04-01 15:25:34.263112-03	f	\N	32	60	223.15	2028-04-30	f	\N		\N	\N	268	\N
2843	2026-04-01 15:25:34.263596-03	2026-04-01 15:25:34.263598-03	f	\N	33	60	223.15	2028-05-31	f	\N		\N	\N	268	\N
2844	2026-04-01 15:25:34.264112-03	2026-04-01 15:25:34.264114-03	f	\N	34	60	223.15	2028-06-30	f	\N		\N	\N	268	\N
2845	2026-04-01 15:25:34.264619-03	2026-04-01 15:25:34.264621-03	f	\N	35	60	223.15	2028-07-31	f	\N		\N	\N	268	\N
2846	2026-04-01 15:25:34.265121-03	2026-04-01 15:25:34.265122-03	f	\N	36	60	223.15	2028-08-31	f	\N		\N	\N	268	\N
2847	2026-04-01 15:25:34.265604-03	2026-04-01 15:25:34.265606-03	f	\N	37	60	223.15	2028-09-30	f	\N		\N	\N	268	\N
2848	2026-04-01 15:25:34.266107-03	2026-04-01 15:25:34.266109-03	f	\N	38	60	223.15	2028-10-31	f	\N		\N	\N	268	\N
2849	2026-04-01 15:25:34.266658-03	2026-04-01 15:25:34.266659-03	f	\N	39	60	223.15	2028-11-30	f	\N		\N	\N	268	\N
2850	2026-04-01 15:25:34.267154-03	2026-04-01 15:25:34.267156-03	f	\N	40	60	223.15	2028-12-31	f	\N		\N	\N	268	\N
2851	2026-04-01 15:25:34.267703-03	2026-04-01 15:25:34.267705-03	f	\N	41	60	223.15	2029-01-31	f	\N		\N	\N	268	\N
2852	2026-04-01 15:25:34.268296-03	2026-04-01 15:25:34.268297-03	f	\N	42	60	223.15	2029-02-28	f	\N		\N	\N	268	\N
2853	2026-04-01 15:25:34.268781-03	2026-04-01 15:25:34.268783-03	f	\N	43	60	223.15	2029-03-31	f	\N		\N	\N	268	\N
2854	2026-04-01 15:25:34.269301-03	2026-04-01 15:25:34.269303-03	f	\N	44	60	223.15	2029-04-30	f	\N		\N	\N	268	\N
2855	2026-04-01 15:25:34.269796-03	2026-04-01 15:25:34.269797-03	f	\N	45	60	223.15	2029-05-31	f	\N		\N	\N	268	\N
2856	2026-04-01 15:25:34.270303-03	2026-04-01 15:25:34.270305-03	f	\N	46	60	223.15	2029-06-30	f	\N		\N	\N	268	\N
2857	2026-04-01 15:25:34.27081-03	2026-04-01 15:25:34.270812-03	f	\N	47	60	223.15	2029-07-31	f	\N		\N	\N	268	\N
2858	2026-04-01 15:25:34.271378-03	2026-04-01 15:25:34.27138-03	f	\N	48	60	223.15	2029-08-31	f	\N		\N	\N	268	\N
2859	2026-04-01 15:25:34.271925-03	2026-04-01 15:25:34.271927-03	f	\N	49	60	223.15	2029-09-30	f	\N		\N	\N	268	\N
2860	2026-04-01 15:25:34.272426-03	2026-04-01 15:25:34.272428-03	f	\N	50	60	223.15	2029-10-31	f	\N		\N	\N	268	\N
2861	2026-04-01 15:25:34.273173-03	2026-04-01 15:25:34.273175-03	f	\N	51	60	223.15	2029-11-30	f	\N		\N	\N	268	\N
2862	2026-04-01 15:25:34.27367-03	2026-04-01 15:25:34.273672-03	f	\N	52	60	223.15	2029-12-31	f	\N		\N	\N	268	\N
2863	2026-04-01 15:25:34.274173-03	2026-04-01 15:25:34.274175-03	f	\N	53	60	223.15	2030-01-31	f	\N		\N	\N	268	\N
2864	2026-04-01 15:25:34.274639-03	2026-04-01 15:25:34.274641-03	f	\N	54	60	223.15	2030-02-28	f	\N		\N	\N	268	\N
2865	2026-04-01 15:25:34.27512-03	2026-04-01 15:25:34.275122-03	f	\N	55	60	223.15	2030-03-31	f	\N		\N	\N	268	\N
2866	2026-04-01 15:25:34.275738-03	2026-04-01 15:25:34.275739-03	f	\N	56	60	223.15	2030-04-30	f	\N		\N	\N	268	\N
2867	2026-04-01 15:25:34.276249-03	2026-04-01 15:25:34.276251-03	f	\N	57	60	223.15	2030-05-31	f	\N		\N	\N	268	\N
2868	2026-04-01 15:25:34.276804-03	2026-04-01 15:25:34.276807-03	f	\N	58	60	223.15	2030-06-30	f	\N		\N	\N	268	\N
2869	2026-04-01 15:25:34.277361-03	2026-04-01 15:25:34.277363-03	f	\N	59	60	223.15	2030-07-31	f	\N		\N	\N	268	\N
2870	2026-04-01 15:25:34.277935-03	2026-04-01 15:25:34.277938-03	f	\N	60	60	223.15	2030-08-31	f	\N		\N	\N	268	\N
2871	2026-04-01 15:25:34.280286-03	2026-04-01 15:25:34.280288-03	f	\N	8	60	250.78	2026-04-30	f	\N		\N	\N	269	\N
2872	2026-04-01 15:25:34.280839-03	2026-04-01 15:25:34.28084-03	f	\N	9	60	250.78	2026-05-31	f	\N		\N	\N	269	\N
2873	2026-04-01 15:25:34.281344-03	2026-04-01 15:25:34.281345-03	f	\N	10	60	250.78	2026-06-30	f	\N		\N	\N	269	\N
2874	2026-04-01 15:25:34.281827-03	2026-04-01 15:25:34.281829-03	f	\N	11	60	250.78	2026-07-31	f	\N		\N	\N	269	\N
2875	2026-04-01 15:25:34.282345-03	2026-04-01 15:25:34.282347-03	f	\N	12	60	250.78	2026-08-31	f	\N		\N	\N	269	\N
2876	2026-04-01 15:25:34.28283-03	2026-04-01 15:25:34.282832-03	f	\N	13	60	250.78	2026-09-30	f	\N		\N	\N	269	\N
2877	2026-04-01 15:25:34.283351-03	2026-04-01 15:25:34.283353-03	f	\N	14	60	250.78	2026-10-31	f	\N		\N	\N	269	\N
2878	2026-04-01 15:25:34.283868-03	2026-04-01 15:25:34.28387-03	f	\N	15	60	250.78	2026-11-30	f	\N		\N	\N	269	\N
2879	2026-04-01 15:25:34.284433-03	2026-04-01 15:25:34.284435-03	f	\N	16	60	250.78	2026-12-31	f	\N		\N	\N	269	\N
2880	2026-04-01 15:25:34.284961-03	2026-04-01 15:25:34.284962-03	f	\N	17	60	250.78	2027-01-31	f	\N		\N	\N	269	\N
2881	2026-04-01 15:25:34.285627-03	2026-04-01 15:25:34.285629-03	f	\N	18	60	250.78	2027-02-28	f	\N		\N	\N	269	\N
2882	2026-04-01 15:25:34.286178-03	2026-04-01 15:25:34.28618-03	f	\N	19	60	250.78	2027-03-31	f	\N		\N	\N	269	\N
2883	2026-04-01 15:25:34.286718-03	2026-04-01 15:25:34.28672-03	f	\N	20	60	250.78	2027-04-30	f	\N		\N	\N	269	\N
2884	2026-04-01 15:25:34.287258-03	2026-04-01 15:25:34.28726-03	f	\N	21	60	250.78	2027-05-31	f	\N		\N	\N	269	\N
2885	2026-04-01 15:25:34.287798-03	2026-04-01 15:25:34.2878-03	f	\N	22	60	250.78	2027-06-30	f	\N		\N	\N	269	\N
2886	2026-04-01 15:25:34.288302-03	2026-04-01 15:25:34.288303-03	f	\N	23	60	250.78	2027-07-31	f	\N		\N	\N	269	\N
2887	2026-04-01 15:25:34.288991-03	2026-04-01 15:25:34.288993-03	f	\N	24	60	250.78	2027-08-31	f	\N		\N	\N	269	\N
2888	2026-04-01 15:25:34.289493-03	2026-04-01 15:25:34.289494-03	f	\N	25	60	250.78	2027-09-30	f	\N		\N	\N	269	\N
2889	2026-04-01 15:25:34.290032-03	2026-04-01 15:25:34.290034-03	f	\N	26	60	250.78	2027-10-31	f	\N		\N	\N	269	\N
2890	2026-04-01 15:25:34.290587-03	2026-04-01 15:25:34.290589-03	f	\N	27	60	250.78	2027-11-30	f	\N		\N	\N	269	\N
2891	2026-04-01 15:25:34.291072-03	2026-04-01 15:25:34.291074-03	f	\N	28	60	250.78	2027-12-31	f	\N		\N	\N	269	\N
2892	2026-04-01 15:25:34.291551-03	2026-04-01 15:25:34.291553-03	f	\N	29	60	250.78	2028-01-31	f	\N		\N	\N	269	\N
2893	2026-04-01 15:25:34.292062-03	2026-04-01 15:25:34.292064-03	f	\N	30	60	250.78	2028-02-29	f	\N		\N	\N	269	\N
2894	2026-04-01 15:25:34.292623-03	2026-04-01 15:25:34.292625-03	f	\N	31	60	250.78	2028-03-31	f	\N		\N	\N	269	\N
2895	2026-04-01 15:25:34.293163-03	2026-04-01 15:25:34.293165-03	f	\N	32	60	250.78	2028-04-30	f	\N		\N	\N	269	\N
2896	2026-04-01 15:25:34.293684-03	2026-04-01 15:25:34.293686-03	f	\N	33	60	250.78	2028-05-31	f	\N		\N	\N	269	\N
2897	2026-04-01 15:25:34.294181-03	2026-04-01 15:25:34.294183-03	f	\N	34	60	250.78	2028-06-30	f	\N		\N	\N	269	\N
2898	2026-04-01 15:25:34.294726-03	2026-04-01 15:25:34.294728-03	f	\N	35	60	250.78	2028-07-31	f	\N		\N	\N	269	\N
2899	2026-04-01 15:25:34.295256-03	2026-04-01 15:25:34.295258-03	f	\N	36	60	250.78	2028-08-31	f	\N		\N	\N	269	\N
2900	2026-04-01 15:25:34.295788-03	2026-04-01 15:25:34.295789-03	f	\N	37	60	250.78	2028-09-30	f	\N		\N	\N	269	\N
2901	2026-04-01 15:25:34.296308-03	2026-04-01 15:25:34.29631-03	f	\N	38	60	250.78	2028-10-31	f	\N		\N	\N	269	\N
2902	2026-04-01 15:25:34.296837-03	2026-04-01 15:25:34.296839-03	f	\N	39	60	250.78	2028-11-30	f	\N		\N	\N	269	\N
2903	2026-04-01 15:25:34.297467-03	2026-04-01 15:25:34.297469-03	f	\N	40	60	250.78	2028-12-31	f	\N		\N	\N	269	\N
2904	2026-04-01 15:25:34.297977-03	2026-04-01 15:25:34.297979-03	f	\N	41	60	250.78	2029-01-31	f	\N		\N	\N	269	\N
2905	2026-04-01 15:25:34.298476-03	2026-04-01 15:25:34.298478-03	f	\N	42	60	250.78	2029-02-28	f	\N		\N	\N	269	\N
2906	2026-04-01 15:25:34.299009-03	2026-04-01 15:25:34.299011-03	f	\N	43	60	250.78	2029-03-31	f	\N		\N	\N	269	\N
2907	2026-04-01 15:25:34.299527-03	2026-04-01 15:25:34.299529-03	f	\N	44	60	250.78	2029-04-30	f	\N		\N	\N	269	\N
2908	2026-04-01 15:25:34.300041-03	2026-04-01 15:25:34.300043-03	f	\N	45	60	250.78	2029-05-31	f	\N		\N	\N	269	\N
2909	2026-04-01 15:25:34.300584-03	2026-04-01 15:25:34.300586-03	f	\N	46	60	250.78	2029-06-30	f	\N		\N	\N	269	\N
2910	2026-04-01 15:25:34.301099-03	2026-04-01 15:25:34.3011-03	f	\N	47	60	250.78	2029-07-31	f	\N		\N	\N	269	\N
2911	2026-04-01 15:25:34.301603-03	2026-04-01 15:25:34.301605-03	f	\N	48	60	250.78	2029-08-31	f	\N		\N	\N	269	\N
2912	2026-04-01 15:25:34.302126-03	2026-04-01 15:25:34.302128-03	f	\N	49	60	250.78	2029-09-30	f	\N		\N	\N	269	\N
2913	2026-04-01 15:25:34.302702-03	2026-04-01 15:25:34.302704-03	f	\N	50	60	250.78	2029-10-31	f	\N		\N	\N	269	\N
2914	2026-04-01 15:25:34.303212-03	2026-04-01 15:25:34.303214-03	f	\N	51	60	250.78	2029-11-30	f	\N		\N	\N	269	\N
2915	2026-04-01 15:25:34.303893-03	2026-04-01 15:25:34.303895-03	f	\N	52	60	250.78	2029-12-31	f	\N		\N	\N	269	\N
2916	2026-04-01 15:25:34.304679-03	2026-04-01 15:25:34.30468-03	f	\N	53	60	250.78	2030-01-31	f	\N		\N	\N	269	\N
2917	2026-04-01 15:25:34.305874-03	2026-04-01 15:25:34.305876-03	f	\N	54	60	250.78	2030-02-28	f	\N		\N	\N	269	\N
2918	2026-04-01 15:25:34.306559-03	2026-04-01 15:25:34.306561-03	f	\N	55	60	250.78	2030-03-31	f	\N		\N	\N	269	\N
2919	2026-04-01 15:25:34.307139-03	2026-04-01 15:25:34.307141-03	f	\N	56	60	250.78	2030-04-30	f	\N		\N	\N	269	\N
2920	2026-04-01 15:25:34.307776-03	2026-04-01 15:25:34.307778-03	f	\N	57	60	250.78	2030-05-31	f	\N		\N	\N	269	\N
2921	2026-04-01 15:25:34.308314-03	2026-04-01 15:25:34.308316-03	f	\N	58	60	250.78	2030-06-30	f	\N		\N	\N	269	\N
2922	2026-04-01 15:25:34.308803-03	2026-04-01 15:25:34.308805-03	f	\N	59	60	250.78	2030-07-31	f	\N		\N	\N	269	\N
2923	2026-04-01 15:25:34.30928-03	2026-04-01 15:25:34.309281-03	f	\N	60	60	250.78	2030-08-31	f	\N		\N	\N	269	\N
3139	2026-04-01 15:27:16.482168-03	2026-04-01 15:27:16.482169-03	f	\N	43	60	390.19	2029-03-04	f	\N		3	\N	262	3
3140	2026-04-01 15:27:16.482182-03	2026-04-01 15:27:16.482182-03	f	\N	44	60	390.19	2029-04-01	f	\N		3	\N	262	3
3141	2026-04-01 15:27:16.482195-03	2026-04-01 15:27:16.482196-03	f	\N	45	60	390.19	2029-05-02	f	\N		3	\N	262	3
3142	2026-04-01 15:27:16.482208-03	2026-04-01 15:27:16.482209-03	f	\N	46	60	390.19	2029-06-01	f	\N		3	\N	262	3
3143	2026-04-01 15:27:16.482223-03	2026-04-01 15:27:16.482224-03	f	\N	47	60	390.19	2029-07-02	f	\N		3	\N	262	3
3144	2026-04-01 15:27:16.482237-03	2026-04-01 15:27:16.482238-03	f	\N	48	60	390.19	2029-08-01	f	\N		3	\N	262	3
3145	2026-04-01 15:27:16.482252-03	2026-04-01 15:27:16.482253-03	f	\N	49	60	390.19	2029-09-01	f	\N		3	\N	262	3
3146	2026-04-01 15:27:16.482266-03	2026-04-01 15:27:16.482267-03	f	\N	50	60	390.19	2029-10-02	f	\N		3	\N	262	3
3147	2026-04-01 15:27:16.482281-03	2026-04-01 15:27:16.482282-03	f	\N	51	60	390.19	2029-11-01	f	\N		3	\N	262	3
3148	2026-04-01 15:27:16.482295-03	2026-04-01 15:27:16.482296-03	f	\N	52	60	390.19	2029-12-02	f	\N		3	\N	262	3
3149	2026-04-01 15:27:16.482309-03	2026-04-01 15:27:16.48231-03	f	\N	53	60	390.19	2030-01-01	f	\N		3	\N	262	3
3150	2026-04-01 15:27:16.482324-03	2026-04-01 15:27:16.482325-03	f	\N	54	60	390.19	2030-02-01	f	\N		3	\N	262	3
3151	2026-04-01 15:27:16.482338-03	2026-04-01 15:27:16.482339-03	f	\N	55	60	390.19	2030-03-04	f	\N		3	\N	262	3
3152	2026-04-01 15:27:16.482352-03	2026-04-01 15:27:16.482354-03	f	\N	56	60	390.19	2030-04-01	f	\N		3	\N	262	3
3153	2026-04-01 15:27:16.482367-03	2026-04-01 15:27:16.482368-03	f	\N	57	60	390.19	2030-05-02	f	\N		3	\N	262	3
3154	2026-04-01 15:27:16.482383-03	2026-04-01 15:27:16.482384-03	f	\N	58	60	390.19	2030-06-01	f	\N		3	\N	262	3
3155	2026-04-01 15:27:16.482397-03	2026-04-01 15:27:16.482398-03	f	\N	59	60	390.19	2030-07-02	f	\N		3	\N	262	3
3156	2026-04-01 15:27:16.482412-03	2026-04-01 15:27:16.482413-03	f	\N	60	60	390.19	2030-08-01	f	\N		3	\N	262	3
3186	2026-04-01 15:28:14.930779-03	2026-04-01 15:28:14.93078-03	f	\N	30	60	513.12	2028-02-01	f	\N		3	\N	261	3
3187	2026-04-01 15:28:14.930794-03	2026-04-01 15:28:14.930795-03	f	\N	31	60	513.12	2028-03-03	f	\N		3	\N	261	3
3188	2026-04-01 15:28:14.930808-03	2026-04-01 15:28:14.930809-03	f	\N	32	60	513.12	2028-04-01	f	\N		3	\N	261	3
3189	2026-04-01 15:28:14.930822-03	2026-04-01 15:28:14.930823-03	f	\N	33	60	513.12	2028-05-02	f	\N		3	\N	261	3
3190	2026-04-01 15:28:14.930836-03	2026-04-01 15:28:14.930837-03	f	\N	34	60	513.12	2028-06-01	f	\N		3	\N	261	3
3191	2026-04-01 15:28:14.93085-03	2026-04-01 15:28:14.930851-03	f	\N	35	60	513.12	2028-07-02	f	\N		3	\N	261	3
3192	2026-04-01 15:28:14.930866-03	2026-04-01 15:28:14.930867-03	f	\N	36	60	513.12	2028-08-01	f	\N		3	\N	261	3
2977	2026-04-01 15:26:40.96936-03	2026-04-01 15:26:40.969368-03	f	\N	1	60	48.25	2025-09-01	t	2025-09-01		3	\N	264	3
2978	2026-04-01 15:26:40.969446-03	2026-04-01 15:26:40.969449-03	f	\N	2	60	48.25	2025-10-02	t	2025-10-02		3	\N	264	3
2979	2026-04-01 15:26:40.969484-03	2026-04-01 15:26:40.969487-03	f	\N	3	60	48.25	2025-11-01	t	2025-11-01		3	\N	264	3
2980	2026-04-01 15:26:40.969518-03	2026-04-01 15:26:40.969521-03	f	\N	4	60	48.25	2025-12-02	t	2025-12-02		3	\N	264	3
2981	2026-04-01 15:26:40.96955-03	2026-04-01 15:26:40.969552-03	f	\N	5	60	48.25	2026-01-01	t	2026-01-01		3	\N	264	3
2982	2026-04-01 15:26:40.969581-03	2026-04-01 15:26:40.969583-03	f	\N	6	60	48.25	2026-02-01	t	2026-02-01		3	\N	264	3
2983	2026-04-01 15:26:40.969611-03	2026-04-01 15:26:40.969613-03	f	\N	7	60	48.25	2026-03-04	t	2026-03-04		3	\N	264	3
2984	2026-04-01 15:26:40.969641-03	2026-04-01 15:26:40.969643-03	f	\N	8	60	48.25	2026-04-01	f	\N		3	\N	264	3
2985	2026-04-01 15:26:40.969671-03	2026-04-01 15:26:40.969673-03	f	\N	9	60	48.25	2026-05-02	f	\N		3	\N	264	3
2986	2026-04-01 15:26:40.969702-03	2026-04-01 15:26:40.969704-03	f	\N	10	60	48.25	2026-06-01	f	\N		3	\N	264	3
2987	2026-04-01 15:26:40.969732-03	2026-04-01 15:26:40.969734-03	f	\N	11	60	48.25	2026-07-02	f	\N		3	\N	264	3
2988	2026-04-01 15:26:40.969762-03	2026-04-01 15:26:40.969765-03	f	\N	12	60	48.25	2026-08-01	f	\N		3	\N	264	3
2989	2026-04-01 15:26:40.969792-03	2026-04-01 15:26:40.969794-03	f	\N	13	60	48.25	2026-09-01	f	\N		3	\N	264	3
2990	2026-04-01 15:26:40.969822-03	2026-04-01 15:26:40.969824-03	f	\N	14	60	48.25	2026-10-02	f	\N		3	\N	264	3
2991	2026-04-01 15:26:40.969853-03	2026-04-01 15:26:40.969855-03	f	\N	15	60	48.25	2026-11-01	f	\N		3	\N	264	3
2992	2026-04-01 15:26:40.969882-03	2026-04-01 15:26:40.969884-03	f	\N	16	60	48.25	2026-12-02	f	\N		3	\N	264	3
2993	2026-04-01 15:26:40.969911-03	2026-04-01 15:26:40.969913-03	f	\N	17	60	48.25	2027-01-01	f	\N		3	\N	264	3
2994	2026-04-01 15:26:40.969943-03	2026-04-01 15:26:40.969946-03	f	\N	18	60	48.25	2027-02-01	f	\N		3	\N	264	3
2995	2026-04-01 15:26:40.969974-03	2026-04-01 15:26:40.969976-03	f	\N	19	60	48.25	2027-03-04	f	\N		3	\N	264	3
2996	2026-04-01 15:26:40.970003-03	2026-04-01 15:26:40.970005-03	f	\N	20	60	48.25	2027-04-01	f	\N		3	\N	264	3
2997	2026-04-01 15:26:40.970033-03	2026-04-01 15:26:40.970035-03	f	\N	21	60	48.25	2027-05-02	f	\N		3	\N	264	3
2998	2026-04-01 15:26:40.970062-03	2026-04-01 15:26:40.970065-03	f	\N	22	60	48.25	2027-06-01	f	\N		3	\N	264	3
2999	2026-04-01 15:26:40.970091-03	2026-04-01 15:26:40.970094-03	f	\N	23	60	48.25	2027-07-02	f	\N		3	\N	264	3
3000	2026-04-01 15:26:40.97012-03	2026-04-01 15:26:40.970123-03	f	\N	24	60	48.25	2027-08-01	f	\N		3	\N	264	3
3001	2026-04-01 15:26:40.97015-03	2026-04-01 15:26:40.970152-03	f	\N	25	60	48.25	2027-09-01	f	\N		3	\N	264	3
3002	2026-04-01 15:26:40.970179-03	2026-04-01 15:26:40.970181-03	f	\N	26	60	48.25	2027-10-02	f	\N		3	\N	264	3
3003	2026-04-01 15:26:40.970208-03	2026-04-01 15:26:40.97021-03	f	\N	27	60	48.25	2027-11-01	f	\N		3	\N	264	3
3004	2026-04-01 15:26:40.970237-03	2026-04-01 15:26:40.970239-03	f	\N	28	60	48.25	2027-12-02	f	\N		3	\N	264	3
3005	2026-04-01 15:26:40.970266-03	2026-04-01 15:26:40.970268-03	f	\N	29	60	48.25	2028-01-01	f	\N		3	\N	264	3
3006	2026-04-01 15:26:40.970295-03	2026-04-01 15:26:40.970297-03	f	\N	30	60	48.25	2028-02-01	f	\N		3	\N	264	3
3007	2026-04-01 15:26:40.970324-03	2026-04-01 15:26:40.970326-03	f	\N	31	60	48.25	2028-03-03	f	\N		3	\N	264	3
3008	2026-04-01 15:26:40.970352-03	2026-04-01 15:26:40.970354-03	f	\N	32	60	48.25	2028-04-01	f	\N		3	\N	264	3
3009	2026-04-01 15:26:40.970382-03	2026-04-01 15:26:40.970384-03	f	\N	33	60	48.25	2028-05-02	f	\N		3	\N	264	3
3010	2026-04-01 15:26:40.970411-03	2026-04-01 15:26:40.970413-03	f	\N	34	60	48.25	2028-06-01	f	\N		3	\N	264	3
3011	2026-04-01 15:26:40.970439-03	2026-04-01 15:26:40.970441-03	f	\N	35	60	48.25	2028-07-02	f	\N		3	\N	264	3
3012	2026-04-01 15:26:40.970468-03	2026-04-01 15:26:40.97047-03	f	\N	36	60	48.25	2028-08-01	f	\N		3	\N	264	3
3013	2026-04-01 15:26:40.970497-03	2026-04-01 15:26:40.970499-03	f	\N	37	60	48.25	2028-09-01	f	\N		3	\N	264	3
3014	2026-04-01 15:26:40.970525-03	2026-04-01 15:26:40.970527-03	f	\N	38	60	48.25	2028-10-02	f	\N		3	\N	264	3
3015	2026-04-01 15:26:40.970554-03	2026-04-01 15:26:40.970556-03	f	\N	39	60	48.25	2028-11-01	f	\N		3	\N	264	3
3016	2026-04-01 15:26:40.970582-03	2026-04-01 15:26:40.970585-03	f	\N	40	60	48.25	2028-12-02	f	\N		3	\N	264	3
3017	2026-04-01 15:26:40.970611-03	2026-04-01 15:26:40.970613-03	f	\N	41	60	48.25	2029-01-01	f	\N		3	\N	264	3
3018	2026-04-01 15:26:40.97064-03	2026-04-01 15:26:40.970642-03	f	\N	42	60	48.25	2029-02-01	f	\N		3	\N	264	3
3019	2026-04-01 15:26:40.97067-03	2026-04-01 15:26:40.970672-03	f	\N	43	60	48.25	2029-03-04	f	\N		3	\N	264	3
3020	2026-04-01 15:26:40.970698-03	2026-04-01 15:26:40.9707-03	f	\N	44	60	48.25	2029-04-01	f	\N		3	\N	264	3
3021	2026-04-01 15:26:40.970728-03	2026-04-01 15:26:40.97073-03	f	\N	45	60	48.25	2029-05-02	f	\N		3	\N	264	3
3022	2026-04-01 15:26:40.970758-03	2026-04-01 15:26:40.97076-03	f	\N	46	60	48.25	2029-06-01	f	\N		3	\N	264	3
3023	2026-04-01 15:26:40.970787-03	2026-04-01 15:26:40.970789-03	f	\N	47	60	48.25	2029-07-02	f	\N		3	\N	264	3
3024	2026-04-01 15:26:40.970816-03	2026-04-01 15:26:40.970818-03	f	\N	48	60	48.25	2029-08-01	f	\N		3	\N	264	3
3025	2026-04-01 15:26:40.970845-03	2026-04-01 15:26:40.970847-03	f	\N	49	60	48.25	2029-09-01	f	\N		3	\N	264	3
3026	2026-04-01 15:26:40.970874-03	2026-04-01 15:26:40.970876-03	f	\N	50	60	48.25	2029-10-02	f	\N		3	\N	264	3
3027	2026-04-01 15:26:40.970903-03	2026-04-01 15:26:40.970905-03	f	\N	51	60	48.25	2029-11-01	f	\N		3	\N	264	3
3028	2026-04-01 15:26:40.970932-03	2026-04-01 15:26:40.970934-03	f	\N	52	60	48.25	2029-12-02	f	\N		3	\N	264	3
3029	2026-04-01 15:26:40.970961-03	2026-04-01 15:26:40.970963-03	f	\N	53	60	48.25	2030-01-01	f	\N		3	\N	264	3
3030	2026-04-01 15:26:40.97099-03	2026-04-01 15:26:40.970992-03	f	\N	54	60	48.25	2030-02-01	f	\N		3	\N	264	3
3031	2026-04-01 15:26:40.971093-03	2026-04-01 15:26:40.971097-03	f	\N	55	60	48.25	2030-03-04	f	\N		3	\N	264	3
3032	2026-04-01 15:26:40.971139-03	2026-04-01 15:26:40.971142-03	f	\N	56	60	48.25	2030-04-01	f	\N		3	\N	264	3
3033	2026-04-01 15:26:40.971173-03	2026-04-01 15:26:40.971176-03	f	\N	57	60	48.25	2030-05-02	f	\N		3	\N	264	3
3034	2026-04-01 15:26:40.971205-03	2026-04-01 15:26:40.971207-03	f	\N	58	60	48.25	2030-06-01	f	\N		3	\N	264	3
3035	2026-04-01 15:26:40.971236-03	2026-04-01 15:26:40.971238-03	f	\N	59	60	48.25	2030-07-02	f	\N		3	\N	264	3
3036	2026-04-01 15:26:40.971265-03	2026-04-01 15:26:40.971267-03	f	\N	60	60	48.25	2030-08-01	f	\N		3	\N	264	3
3157	2026-04-01 15:28:14.930307-03	2026-04-01 15:28:14.93031-03	f	\N	1	60	513.12	2025-09-01	t	2025-09-01		3	\N	261	3
3158	2026-04-01 15:28:14.930359-03	2026-04-01 15:28:14.93036-03	f	\N	2	60	513.12	2025-10-02	t	2025-10-02		3	\N	261	3
3159	2026-04-01 15:28:14.930376-03	2026-04-01 15:28:14.930377-03	f	\N	3	60	513.12	2025-11-01	t	2025-11-01		3	\N	261	3
3160	2026-04-01 15:28:14.930393-03	2026-04-01 15:28:14.930394-03	f	\N	4	60	513.12	2025-12-02	t	2025-12-02		3	\N	261	3
3161	2026-04-01 15:28:14.930408-03	2026-04-01 15:28:14.930409-03	f	\N	5	60	513.12	2026-01-01	t	2026-01-01		3	\N	261	3
3162	2026-04-01 15:28:14.930423-03	2026-04-01 15:28:14.930424-03	f	\N	6	60	513.12	2026-02-01	t	2026-02-01		3	\N	261	3
3163	2026-04-01 15:28:14.930438-03	2026-04-01 15:28:14.930439-03	f	\N	7	60	513.12	2026-03-04	t	2026-03-04		3	\N	261	3
3164	2026-04-01 15:28:14.930454-03	2026-04-01 15:28:14.930455-03	f	\N	8	60	513.12	2026-04-01	f	\N		3	\N	261	3
3165	2026-04-01 15:28:14.930469-03	2026-04-01 15:28:14.93047-03	f	\N	9	60	513.12	2026-05-02	f	\N		3	\N	261	3
3166	2026-04-01 15:28:14.930484-03	2026-04-01 15:28:14.930485-03	f	\N	10	60	513.12	2026-06-01	f	\N		3	\N	261	3
3167	2026-04-01 15:28:14.930499-03	2026-04-01 15:28:14.9305-03	f	\N	11	60	513.12	2026-07-02	f	\N		3	\N	261	3
3168	2026-04-01 15:28:14.930513-03	2026-04-01 15:28:14.930514-03	f	\N	12	60	513.12	2026-08-01	f	\N		3	\N	261	3
3169	2026-04-01 15:28:14.930527-03	2026-04-01 15:28:14.930528-03	f	\N	13	60	513.12	2026-09-01	f	\N		3	\N	261	3
3170	2026-04-01 15:28:14.930541-03	2026-04-01 15:28:14.930542-03	f	\N	14	60	513.12	2026-10-02	f	\N		3	\N	261	3
3037	2026-04-01 15:27:01.895977-03	2026-04-01 15:27:01.89598-03	f	\N	1	60	283.87	2025-09-01	t	2025-09-01		3	\N	263	3
3038	2026-04-01 15:27:01.89602-03	2026-04-01 15:27:01.896021-03	f	\N	2	60	283.87	2025-10-02	t	2025-10-02		3	\N	263	3
3039	2026-04-01 15:27:01.896038-03	2026-04-01 15:27:01.896039-03	f	\N	3	60	283.87	2025-11-01	t	2025-11-01		3	\N	263	3
3040	2026-04-01 15:27:01.896053-03	2026-04-01 15:27:01.896054-03	f	\N	4	60	283.87	2025-12-02	t	2025-12-02		3	\N	263	3
3041	2026-04-01 15:27:01.896069-03	2026-04-01 15:27:01.89607-03	f	\N	5	60	283.87	2026-01-01	t	2026-01-01		3	\N	263	3
3042	2026-04-01 15:27:01.896085-03	2026-04-01 15:27:01.896086-03	f	\N	6	60	283.87	2026-02-01	t	2026-02-01		3	\N	263	3
3043	2026-04-01 15:27:01.8961-03	2026-04-01 15:27:01.896101-03	f	\N	7	60	283.87	2026-03-04	t	2026-03-04		3	\N	263	3
3044	2026-04-01 15:27:01.896116-03	2026-04-01 15:27:01.896117-03	f	\N	8	60	283.87	2026-04-01	f	\N		3	\N	263	3
3045	2026-04-01 15:27:01.896131-03	2026-04-01 15:27:01.896132-03	f	\N	9	60	283.87	2026-05-02	f	\N		3	\N	263	3
3046	2026-04-01 15:27:01.896145-03	2026-04-01 15:27:01.896146-03	f	\N	10	60	283.87	2026-06-01	f	\N		3	\N	263	3
3047	2026-04-01 15:27:01.896161-03	2026-04-01 15:27:01.896162-03	f	\N	11	60	283.87	2026-07-02	f	\N		3	\N	263	3
3048	2026-04-01 15:27:01.896176-03	2026-04-01 15:27:01.896177-03	f	\N	12	60	283.87	2026-08-01	f	\N		3	\N	263	3
3049	2026-04-01 15:27:01.896191-03	2026-04-01 15:27:01.896192-03	f	\N	13	60	283.87	2026-09-01	f	\N		3	\N	263	3
3050	2026-04-01 15:27:01.896206-03	2026-04-01 15:27:01.896207-03	f	\N	14	60	283.87	2026-10-02	f	\N		3	\N	263	3
3051	2026-04-01 15:27:01.89622-03	2026-04-01 15:27:01.896221-03	f	\N	15	60	283.87	2026-11-01	f	\N		3	\N	263	3
3052	2026-04-01 15:27:01.896235-03	2026-04-01 15:27:01.896236-03	f	\N	16	60	283.87	2026-12-02	f	\N		3	\N	263	3
3053	2026-04-01 15:27:01.896249-03	2026-04-01 15:27:01.89625-03	f	\N	17	60	283.87	2027-01-01	f	\N		3	\N	263	3
3054	2026-04-01 15:27:01.896264-03	2026-04-01 15:27:01.896265-03	f	\N	18	60	283.87	2027-02-01	f	\N		3	\N	263	3
3055	2026-04-01 15:27:01.896279-03	2026-04-01 15:27:01.89628-03	f	\N	19	60	283.87	2027-03-04	f	\N		3	\N	263	3
3056	2026-04-01 15:27:01.896294-03	2026-04-01 15:27:01.896295-03	f	\N	20	60	283.87	2027-04-01	f	\N		3	\N	263	3
3057	2026-04-01 15:27:01.896309-03	2026-04-01 15:27:01.89631-03	f	\N	21	60	283.87	2027-05-02	f	\N		3	\N	263	3
3058	2026-04-01 15:27:01.896324-03	2026-04-01 15:27:01.896325-03	f	\N	22	60	283.87	2027-06-01	f	\N		3	\N	263	3
3059	2026-04-01 15:27:01.896339-03	2026-04-01 15:27:01.89634-03	f	\N	23	60	283.87	2027-07-02	f	\N		3	\N	263	3
3060	2026-04-01 15:27:01.896353-03	2026-04-01 15:27:01.896354-03	f	\N	24	60	283.87	2027-08-01	f	\N		3	\N	263	3
3061	2026-04-01 15:27:01.896369-03	2026-04-01 15:27:01.89637-03	f	\N	25	60	283.87	2027-09-01	f	\N		3	\N	263	3
3062	2026-04-01 15:27:01.896384-03	2026-04-01 15:27:01.896385-03	f	\N	26	60	283.87	2027-10-02	f	\N		3	\N	263	3
3063	2026-04-01 15:27:01.896398-03	2026-04-01 15:27:01.896399-03	f	\N	27	60	283.87	2027-11-01	f	\N		3	\N	263	3
3064	2026-04-01 15:27:01.896413-03	2026-04-01 15:27:01.896414-03	f	\N	28	60	283.87	2027-12-02	f	\N		3	\N	263	3
3065	2026-04-01 15:27:01.896427-03	2026-04-01 15:27:01.896428-03	f	\N	29	60	283.87	2028-01-01	f	\N		3	\N	263	3
3066	2026-04-01 15:27:01.896442-03	2026-04-01 15:27:01.896443-03	f	\N	30	60	283.87	2028-02-01	f	\N		3	\N	263	3
3067	2026-04-01 15:27:01.896457-03	2026-04-01 15:27:01.896458-03	f	\N	31	60	283.87	2028-03-03	f	\N		3	\N	263	3
3068	2026-04-01 15:27:01.896471-03	2026-04-01 15:27:01.896472-03	f	\N	32	60	283.87	2028-04-01	f	\N		3	\N	263	3
3069	2026-04-01 15:27:01.896486-03	2026-04-01 15:27:01.896487-03	f	\N	33	60	283.87	2028-05-02	f	\N		3	\N	263	3
3070	2026-04-01 15:27:01.896501-03	2026-04-01 15:27:01.896502-03	f	\N	34	60	283.87	2028-06-01	f	\N		3	\N	263	3
3071	2026-04-01 15:27:01.896516-03	2026-04-01 15:27:01.896517-03	f	\N	35	60	283.87	2028-07-02	f	\N		3	\N	263	3
3072	2026-04-01 15:27:01.896531-03	2026-04-01 15:27:01.896532-03	f	\N	36	60	283.87	2028-08-01	f	\N		3	\N	263	3
3073	2026-04-01 15:27:01.896545-03	2026-04-01 15:27:01.896546-03	f	\N	37	60	283.87	2028-09-01	f	\N		3	\N	263	3
3074	2026-04-01 15:27:01.89656-03	2026-04-01 15:27:01.896561-03	f	\N	38	60	283.87	2028-10-02	f	\N		3	\N	263	3
3075	2026-04-01 15:27:01.896575-03	2026-04-01 15:27:01.896576-03	f	\N	39	60	283.87	2028-11-01	f	\N		3	\N	263	3
3076	2026-04-01 15:27:01.896588-03	2026-04-01 15:27:01.896589-03	f	\N	40	60	283.87	2028-12-02	f	\N		3	\N	263	3
3077	2026-04-01 15:27:01.896601-03	2026-04-01 15:27:01.896602-03	f	\N	41	60	283.87	2029-01-01	f	\N		3	\N	263	3
3078	2026-04-01 15:27:01.896615-03	2026-04-01 15:27:01.896616-03	f	\N	42	60	283.87	2029-02-01	f	\N		3	\N	263	3
3079	2026-04-01 15:27:01.896628-03	2026-04-01 15:27:01.896629-03	f	\N	43	60	283.87	2029-03-04	f	\N		3	\N	263	3
3080	2026-04-01 15:27:01.896642-03	2026-04-01 15:27:01.896642-03	f	\N	44	60	283.87	2029-04-01	f	\N		3	\N	263	3
3081	2026-04-01 15:27:01.896655-03	2026-04-01 15:27:01.896656-03	f	\N	45	60	283.87	2029-05-02	f	\N		3	\N	263	3
3082	2026-04-01 15:27:01.896668-03	2026-04-01 15:27:01.896669-03	f	\N	46	60	283.87	2029-06-01	f	\N		3	\N	263	3
3083	2026-04-01 15:27:01.896681-03	2026-04-01 15:27:01.896682-03	f	\N	47	60	283.87	2029-07-02	f	\N		3	\N	263	3
3084	2026-04-01 15:27:01.896695-03	2026-04-01 15:27:01.896696-03	f	\N	48	60	283.87	2029-08-01	f	\N		3	\N	263	3
3085	2026-04-01 15:27:01.896708-03	2026-04-01 15:27:01.896709-03	f	\N	49	60	283.87	2029-09-01	f	\N		3	\N	263	3
3086	2026-04-01 15:27:01.896721-03	2026-04-01 15:27:01.896722-03	f	\N	50	60	283.87	2029-10-02	f	\N		3	\N	263	3
3087	2026-04-01 15:27:01.896734-03	2026-04-01 15:27:01.896735-03	f	\N	51	60	283.87	2029-11-01	f	\N		3	\N	263	3
3088	2026-04-01 15:27:01.896748-03	2026-04-01 15:27:01.896749-03	f	\N	52	60	283.87	2029-12-02	f	\N		3	\N	263	3
3089	2026-04-01 15:27:01.896761-03	2026-04-01 15:27:01.896762-03	f	\N	53	60	283.87	2030-01-01	f	\N		3	\N	263	3
3090	2026-04-01 15:27:01.896775-03	2026-04-01 15:27:01.896776-03	f	\N	54	60	283.87	2030-02-01	f	\N		3	\N	263	3
3091	2026-04-01 15:27:01.896788-03	2026-04-01 15:27:01.896789-03	f	\N	55	60	283.87	2030-03-04	f	\N		3	\N	263	3
3092	2026-04-01 15:27:01.896801-03	2026-04-01 15:27:01.896802-03	f	\N	56	60	283.87	2030-04-01	f	\N		3	\N	263	3
3093	2026-04-01 15:27:01.896814-03	2026-04-01 15:27:01.896815-03	f	\N	57	60	283.87	2030-05-02	f	\N		3	\N	263	3
3094	2026-04-01 15:27:01.896828-03	2026-04-01 15:27:01.896829-03	f	\N	58	60	283.87	2030-06-01	f	\N		3	\N	263	3
3095	2026-04-01 15:27:01.896842-03	2026-04-01 15:27:01.896843-03	f	\N	59	60	283.87	2030-07-02	f	\N		3	\N	263	3
3096	2026-04-01 15:27:01.896856-03	2026-04-01 15:27:01.896857-03	f	\N	60	60	283.87	2030-08-01	f	\N		3	\N	263	3
3171	2026-04-01 15:28:14.930555-03	2026-04-01 15:28:14.930556-03	f	\N	15	60	513.12	2026-11-01	f	\N		3	\N	261	3
3172	2026-04-01 15:28:14.930571-03	2026-04-01 15:28:14.930572-03	f	\N	16	60	513.12	2026-12-02	f	\N		3	\N	261	3
3173	2026-04-01 15:28:14.930585-03	2026-04-01 15:28:14.930586-03	f	\N	17	60	513.12	2027-01-01	f	\N		3	\N	261	3
3174	2026-04-01 15:28:14.930599-03	2026-04-01 15:28:14.9306-03	f	\N	18	60	513.12	2027-02-01	f	\N		3	\N	261	3
3175	2026-04-01 15:28:14.930613-03	2026-04-01 15:28:14.930614-03	f	\N	19	60	513.12	2027-03-04	f	\N		3	\N	261	3
3176	2026-04-01 15:28:14.930627-03	2026-04-01 15:28:14.930628-03	f	\N	20	60	513.12	2027-04-01	f	\N		3	\N	261	3
3177	2026-04-01 15:28:14.930642-03	2026-04-01 15:28:14.930643-03	f	\N	21	60	513.12	2027-05-02	f	\N		3	\N	261	3
3178	2026-04-01 15:28:14.930656-03	2026-04-01 15:28:14.930657-03	f	\N	22	60	513.12	2027-06-01	f	\N		3	\N	261	3
3179	2026-04-01 15:28:14.93067-03	2026-04-01 15:28:14.930671-03	f	\N	23	60	513.12	2027-07-02	f	\N		3	\N	261	3
3180	2026-04-01 15:28:14.930684-03	2026-04-01 15:28:14.930685-03	f	\N	24	60	513.12	2027-08-01	f	\N		3	\N	261	3
3181	2026-04-01 15:28:14.930698-03	2026-04-01 15:28:14.930699-03	f	\N	25	60	513.12	2027-09-01	f	\N		3	\N	261	3
3182	2026-04-01 15:28:14.930718-03	2026-04-01 15:28:14.930719-03	f	\N	26	60	513.12	2027-10-02	f	\N		3	\N	261	3
3183	2026-04-01 15:28:14.930733-03	2026-04-01 15:28:14.930734-03	f	\N	27	60	513.12	2027-11-01	f	\N		3	\N	261	3
3184	2026-04-01 15:28:14.93075-03	2026-04-01 15:28:14.93075-03	f	\N	28	60	513.12	2027-12-02	f	\N		3	\N	261	3
3185	2026-04-01 15:28:14.930764-03	2026-04-01 15:28:14.930765-03	f	\N	29	60	513.12	2028-01-01	f	\N		3	\N	261	3
3097	2026-04-01 15:27:16.481528-03	2026-04-01 15:27:16.48153-03	f	\N	1	60	390.19	2025-09-01	t	2025-09-01		3	\N	262	3
3098	2026-04-01 15:27:16.481565-03	2026-04-01 15:27:16.481566-03	f	\N	2	60	390.19	2025-10-02	t	2025-10-02		3	\N	262	3
3099	2026-04-01 15:27:16.481583-03	2026-04-01 15:27:16.481584-03	f	\N	3	60	390.19	2025-11-01	t	2025-11-01		3	\N	262	3
3100	2026-04-01 15:27:16.481598-03	2026-04-01 15:27:16.481599-03	f	\N	4	60	390.19	2025-12-02	t	2025-12-02		3	\N	262	3
3101	2026-04-01 15:27:16.481614-03	2026-04-01 15:27:16.481615-03	f	\N	5	60	390.19	2026-01-01	t	2026-01-01		3	\N	262	3
3102	2026-04-01 15:27:16.48163-03	2026-04-01 15:27:16.481631-03	f	\N	6	60	390.19	2026-02-01	t	2026-02-01		3	\N	262	3
3103	2026-04-01 15:27:16.481644-03	2026-04-01 15:27:16.481645-03	f	\N	7	60	390.19	2026-03-04	t	2026-03-04		3	\N	262	3
3104	2026-04-01 15:27:16.481659-03	2026-04-01 15:27:16.481661-03	f	\N	8	60	390.19	2026-04-01	f	\N		3	\N	262	3
3105	2026-04-01 15:27:16.481676-03	2026-04-01 15:27:16.481677-03	f	\N	9	60	390.19	2026-05-02	f	\N		3	\N	262	3
3106	2026-04-01 15:27:16.481691-03	2026-04-01 15:27:16.481693-03	f	\N	10	60	390.19	2026-06-01	f	\N		3	\N	262	3
3107	2026-04-01 15:27:16.481706-03	2026-04-01 15:27:16.481707-03	f	\N	11	60	390.19	2026-07-02	f	\N		3	\N	262	3
3108	2026-04-01 15:27:16.481721-03	2026-04-01 15:27:16.481722-03	f	\N	12	60	390.19	2026-08-01	f	\N		3	\N	262	3
3109	2026-04-01 15:27:16.481735-03	2026-04-01 15:27:16.481736-03	f	\N	13	60	390.19	2026-09-01	f	\N		3	\N	262	3
3110	2026-04-01 15:27:16.48175-03	2026-04-01 15:27:16.481751-03	f	\N	14	60	390.19	2026-10-02	f	\N		3	\N	262	3
3111	2026-04-01 15:27:16.481765-03	2026-04-01 15:27:16.481766-03	f	\N	15	60	390.19	2026-11-01	f	\N		3	\N	262	3
3112	2026-04-01 15:27:16.481779-03	2026-04-01 15:27:16.48178-03	f	\N	16	60	390.19	2026-12-02	f	\N		3	\N	262	3
3113	2026-04-01 15:27:16.481793-03	2026-04-01 15:27:16.481794-03	f	\N	17	60	390.19	2027-01-01	f	\N		3	\N	262	3
3114	2026-04-01 15:27:16.481808-03	2026-04-01 15:27:16.481809-03	f	\N	18	60	390.19	2027-02-01	f	\N		3	\N	262	3
3115	2026-04-01 15:27:16.481822-03	2026-04-01 15:27:16.481823-03	f	\N	19	60	390.19	2027-03-04	f	\N		3	\N	262	3
3116	2026-04-01 15:27:16.481837-03	2026-04-01 15:27:16.481838-03	f	\N	20	60	390.19	2027-04-01	f	\N		3	\N	262	3
3117	2026-04-01 15:27:16.481851-03	2026-04-01 15:27:16.481852-03	f	\N	21	60	390.19	2027-05-02	f	\N		3	\N	262	3
3118	2026-04-01 15:27:16.481868-03	2026-04-01 15:27:16.48187-03	f	\N	22	60	390.19	2027-06-01	f	\N		3	\N	262	3
3119	2026-04-01 15:27:16.481883-03	2026-04-01 15:27:16.481884-03	f	\N	23	60	390.19	2027-07-02	f	\N		3	\N	262	3
3120	2026-04-01 15:27:16.481898-03	2026-04-01 15:27:16.481899-03	f	\N	24	60	390.19	2027-08-01	f	\N		3	\N	262	3
2563	2026-04-01 14:03:33.397307-03	2026-04-01 14:03:33.39731-03	f	\N	6	12	63.33	2026-06-01	f	\N		\N	\N	305	\N
2575	2026-04-01 14:10:02.358806-03	2026-04-01 14:10:02.35881-03	f	\N	6	6	66.70	2026-08-01	f	\N		\N	\N	306	\N
2587	2026-04-01 14:10:57.897821-03	2026-04-01 14:10:57.897824-03	f	\N	2	6	50.00	2026-04-01	f	\N		\N	\N	308	\N
2429	2026-03-23 19:17:45.292925-03	2026-03-23 19:17:45.292928-03	t	2026-04-01 15:03:39.725269-03	488	510	90.00	2066-04-30	f	\N		3	\N	190	3
2431	2026-03-23 19:17:45.293101-03	2026-03-23 19:17:45.293103-03	t	2026-04-01 15:03:39.725269-03	490	510	90.00	2066-06-30	f	\N		3	\N	190	3
2438	2026-03-23 19:17:45.29323-03	2026-03-23 19:17:45.293231-03	t	2026-04-01 15:03:39.725269-03	497	510	90.00	2067-01-30	f	\N		3	\N	190	3
2443	2026-03-23 19:17:45.293317-03	2026-03-23 19:17:45.293318-03	t	2026-04-01 15:03:39.725269-03	502	510	90.00	2067-06-30	f	\N		3	\N	190	3
2434	2026-03-23 19:17:45.293157-03	2026-03-23 19:17:45.293158-03	t	2026-04-01 15:03:39.725269-03	493	510	90.00	2066-09-30	f	\N		3	\N	190	3
2451	2026-03-23 19:17:45.293458-03	2026-03-23 19:17:45.293459-03	t	2026-04-01 15:03:39.725269-03	510	510	90.00	2068-03-01	f	\N		3	\N	190	3
2439	2026-03-23 19:17:45.293247-03	2026-03-23 19:17:45.293248-03	t	2026-04-01 15:03:39.725269-03	498	510	90.00	2067-03-02	f	\N		3	\N	190	3
2441	2026-03-23 19:17:45.293282-03	2026-03-23 19:17:45.293284-03	t	2026-04-01 15:03:39.725269-03	500	510	90.00	2067-04-30	f	\N		3	\N	190	3
2430	2026-03-23 19:17:45.293035-03	2026-03-23 19:17:45.29304-03	t	2026-04-01 15:03:39.725269-03	489	510	90.00	2066-05-30	f	\N		3	\N	190	3
2484	2026-03-23 19:19:17.302772-03	2026-03-23 19:19:17.302779-03	f	\N	11	12	337.00	2026-07-23	f	\N		\N	\N	292	\N
2529	2026-03-23 19:24:35.267508-03	2026-03-23 19:24:35.267515-03	f	\N	1	10	100.00	2026-02-23	t	2026-02-23		\N	\N	294	\N
2539	2026-03-30 13:03:01.29519-03	2026-03-30 13:03:01.295199-03	f	\N	1	12	723.16	2025-12-01	t	2025-12-01		\N	\N	297	\N
2550	2026-03-30 13:03:02.061685-03	2026-03-30 13:03:02.061688-03	f	\N	12	12	723.16	2026-10-31	f	\N		\N	\N	297	\N
2092	2026-03-23 19:17:45.281707-03	2026-03-23 19:17:45.281709-03	t	2026-04-01 15:03:39.725269-03	151	510	90.00	2038-03-30	f	\N		3	\N	190	3
2173	2026-03-23 19:17:45.284755-03	2026-03-23 19:17:45.284758-03	t	2026-04-01 15:03:39.725269-03	232	510	90.00	2044-12-30	f	\N		3	\N	190	3
2220	2026-03-23 19:17:45.286279-03	2026-03-23 19:17:45.286281-03	t	2026-04-01 15:03:39.725269-03	279	510	90.00	2048-11-30	f	\N		3	\N	190	3
2127	2026-03-23 19:17:45.283101-03	2026-03-23 19:17:45.283104-03	t	2026-04-01 15:03:39.725269-03	186	510	90.00	2041-03-02	f	\N		3	\N	190	3
1959	2026-03-23 19:17:45.27811-03	2026-03-23 19:17:45.278111-03	t	2026-04-01 15:03:39.725269-03	18	510	90.00	2027-03-02	f	\N		3	\N	190	3
2444	2026-03-23 19:17:45.293334-03	2026-03-23 19:17:45.293335-03	t	2026-04-01 15:03:39.725269-03	503	510	90.00	2067-07-30	f	\N		3	\N	190	3
1991	2026-03-23 19:17:45.278639-03	2026-03-23 19:17:45.27864-03	t	2026-04-01 15:03:39.725269-03	50	510	90.00	2029-10-30	f	\N		3	\N	190	3
2338	2026-03-23 19:17:45.289771-03	2026-03-23 19:17:45.289773-03	t	2026-04-01 15:03:39.725269-03	397	510	90.00	2058-09-30	f	\N		3	\N	190	3
2234	2026-03-23 19:17:45.286748-03	2026-03-23 19:17:45.28675-03	t	2026-04-01 15:03:39.725269-03	293	510	90.00	2050-01-30	f	\N		3	\N	190	3
2106	2026-03-23 19:17:45.282162-03	2026-03-23 19:17:45.282164-03	t	2026-04-01 15:03:39.725269-03	165	510	90.00	2039-05-30	f	\N		3	\N	190	3
1971	2026-03-23 19:17:45.278312-03	2026-03-23 19:17:45.278313-03	t	2026-04-01 15:03:39.725269-03	30	510	90.00	2028-03-01	f	\N		3	\N	190	3
2098	2026-03-23 19:17:45.2819-03	2026-03-23 19:17:45.281903-03	t	2026-04-01 15:03:39.725269-03	157	510	90.00	2038-09-30	f	\N		3	\N	190	3
2190	2026-03-23 19:17:45.285302-03	2026-03-23 19:17:45.285305-03	t	2026-04-01 15:03:39.725269-03	249	510	90.00	2046-05-30	f	\N		3	\N	190	3
2178	2026-03-23 19:17:45.284922-03	2026-03-23 19:17:45.284924-03	t	2026-04-01 15:03:39.725269-03	237	510	90.00	2045-05-30	f	\N		3	\N	190	3
2073	2026-03-23 19:17:45.281099-03	2026-03-23 19:17:45.281101-03	t	2026-04-01 15:03:39.725269-03	132	510	90.00	2036-08-30	f	\N		3	\N	190	3
2017	2026-03-23 19:17:45.279268-03	2026-03-23 19:17:45.279271-03	t	2026-04-01 15:03:39.725269-03	76	510	90.00	2031-12-30	f	\N		3	\N	190	3
2344	2026-03-23 19:17:45.289977-03	2026-03-23 19:17:45.28998-03	t	2026-04-01 15:03:39.725269-03	403	510	90.00	2059-03-30	f	\N		3	\N	190	3
2241	2026-03-23 19:17:45.286988-03	2026-03-23 19:17:45.286991-03	t	2026-04-01 15:03:39.725269-03	300	510	90.00	2050-08-30	f	\N		3	\N	190	3
2361	2026-03-23 19:17:45.290551-03	2026-03-23 19:17:45.290554-03	t	2026-04-01 15:03:39.725269-03	420	510	90.00	2060-08-30	f	\N		3	\N	190	3
2393	2026-03-23 19:17:45.29169-03	2026-03-23 19:17:45.291693-03	t	2026-04-01 15:03:39.725269-03	452	510	90.00	2063-04-30	f	\N		3	\N	190	3
2246	2026-03-23 19:17:45.287156-03	2026-03-23 19:17:45.287159-03	t	2026-04-01 15:03:39.725269-03	305	510	90.00	2051-01-30	f	\N		3	\N	190	3
2274	2026-03-23 19:17:45.288116-03	2026-03-23 19:17:45.288119-03	t	2026-04-01 15:03:39.725269-03	333	510	90.00	2053-05-30	f	\N		3	\N	190	3
2170	2026-03-23 19:17:45.284657-03	2026-03-23 19:17:45.284659-03	t	2026-04-01 15:03:39.725269-03	229	510	90.00	2044-09-30	f	\N		3	\N	190	3
2369	2026-03-23 19:17:45.290824-03	2026-03-23 19:17:45.290827-03	t	2026-04-01 15:03:39.725269-03	428	510	90.00	2061-04-30	f	\N		3	\N	190	3
2264	2026-03-23 19:17:45.287784-03	2026-03-23 19:17:45.287787-03	t	2026-04-01 15:03:39.725269-03	323	510	90.00	2052-07-30	f	\N		3	\N	190	3
2415	2026-03-23 19:17:45.292443-03	2026-03-23 19:17:45.292446-03	t	2026-04-01 15:03:39.725269-03	474	510	90.00	2065-03-02	f	\N		3	\N	190	3
2131	2026-03-23 19:17:45.283236-03	2026-03-23 19:17:45.283239-03	t	2026-04-01 15:03:39.725269-03	190	510	90.00	2041-06-30	f	\N		3	\N	190	3
2401	2026-03-23 19:17:45.291966-03	2026-03-23 19:17:45.291968-03	t	2026-04-01 15:03:39.725269-03	460	510	90.00	2063-12-30	f	\N		3	\N	190	3
2388	2026-03-23 19:17:45.291517-03	2026-03-23 19:17:45.291519-03	t	2026-04-01 15:03:39.725269-03	447	510	90.00	2062-11-30	f	\N		3	\N	190	3
2319	2026-03-23 19:17:45.288997-03	2026-03-23 19:17:45.288998-03	t	2026-04-01 15:03:39.725269-03	378	510	90.00	2057-03-02	f	\N		3	\N	190	3
2263	2026-03-23 19:17:45.28775-03	2026-03-23 19:17:45.287753-03	t	2026-04-01 15:03:39.725269-03	322	510	90.00	2052-06-30	f	\N		3	\N	190	3
2467	2026-03-23 19:18:06.21839-03	2026-03-23 19:18:06.218393-03	t	2026-04-01 15:03:39.725269-03	4	10	106.00	2026-01-30	t	2026-01-30		3	\N	192	3
2050	2026-03-23 19:17:45.28035-03	2026-03-23 19:17:45.280352-03	t	2026-04-01 15:03:39.725269-03	109	510	90.00	2034-09-30	f	\N		3	\N	190	3
2312	2026-03-23 19:17:45.288879-03	2026-03-23 19:17:45.28888-03	t	2026-04-01 15:03:39.725269-03	371	510	90.00	2056-07-30	f	\N		3	\N	190	3
2416	2026-03-23 19:17:45.292476-03	2026-03-23 19:17:45.292479-03	t	2026-04-01 15:03:39.725269-03	475	510	90.00	2065-03-30	f	\N		3	\N	190	3
2251	2026-03-23 19:17:45.287329-03	2026-03-23 19:17:45.287332-03	t	2026-04-01 15:03:39.725269-03	310	510	90.00	2051-06-30	f	\N		3	\N	190	3
2002	2026-03-23 19:17:45.278818-03	2026-03-23 19:17:45.278819-03	t	2026-04-01 15:03:39.725269-03	61	510	90.00	2030-09-30	f	\N		3	\N	190	3
2133	2026-03-23 19:17:45.283301-03	2026-03-23 19:17:45.283304-03	t	2026-04-01 15:03:39.725269-03	192	510	90.00	2041-08-30	f	\N		3	\N	190	3
2064	2026-03-23 19:17:45.280798-03	2026-03-23 19:17:45.2808-03	t	2026-04-01 15:03:39.725269-03	123	510	90.00	2035-11-30	f	\N		3	\N	190	3
2283	2026-03-23 19:17:45.288388-03	2026-03-23 19:17:45.288389-03	t	2026-04-01 15:03:39.725269-03	342	510	90.00	2054-03-02	f	\N		3	\N	190	3
2070	2026-03-23 19:17:45.281-03	2026-03-23 19:17:45.281003-03	t	2026-04-01 15:03:39.725269-03	129	510	90.00	2036-05-30	f	\N		3	\N	190	3
2090	2026-03-23 19:17:45.281641-03	2026-03-23 19:17:45.281643-03	t	2026-04-01 15:03:39.725269-03	149	510	90.00	2038-01-30	f	\N		3	\N	190	3
2048	2026-03-23 19:17:45.280285-03	2026-03-23 19:17:45.280287-03	t	2026-04-01 15:03:39.725269-03	107	510	90.00	2034-07-30	f	\N		3	\N	190	3
2201	2026-03-23 19:17:45.285659-03	2026-03-23 19:17:45.285661-03	t	2026-04-01 15:03:39.725269-03	260	510	90.00	2047-04-30	f	\N		3	\N	190	3
2202	2026-03-23 19:17:45.28569-03	2026-03-23 19:17:45.285693-03	t	2026-04-01 15:03:39.725269-03	261	510	90.00	2047-05-30	f	\N		3	\N	190	3
2051	2026-03-23 19:17:45.280383-03	2026-03-23 19:17:45.280385-03	t	2026-04-01 15:03:39.725269-03	110	510	90.00	2034-10-30	f	\N		3	\N	190	3
2328	2026-03-23 19:17:45.28943-03	2026-03-23 19:17:45.289433-03	t	2026-04-01 15:03:39.725269-03	387	510	90.00	2057-11-30	f	\N		3	\N	190	3
2305	2026-03-23 19:17:45.288764-03	2026-03-23 19:17:45.288765-03	t	2026-04-01 15:03:39.725269-03	364	510	90.00	2055-12-30	f	\N		3	\N	190	3
2135	2026-03-23 19:17:45.283366-03	2026-03-23 19:17:45.283369-03	t	2026-04-01 15:03:39.725269-03	194	510	90.00	2041-10-30	f	\N		3	\N	190	3
2052	2026-03-23 19:17:45.280414-03	2026-03-23 19:17:45.280417-03	t	2026-04-01 15:03:39.725269-03	111	510	90.00	2034-11-30	f	\N		3	\N	190	3
2213	2026-03-23 19:17:45.286042-03	2026-03-23 19:17:45.286044-03	t	2026-04-01 15:03:39.725269-03	272	510	90.00	2048-04-30	f	\N		3	\N	190	3
2103	2026-03-23 19:17:45.282064-03	2026-03-23 19:17:45.282067-03	t	2026-04-01 15:03:39.725269-03	162	510	90.00	2039-03-02	f	\N		3	\N	190	3
2123	2026-03-23 19:17:45.282948-03	2026-03-23 19:17:45.28295-03	t	2026-04-01 15:03:39.725269-03	182	510	90.00	2040-10-30	f	\N		3	\N	190	3
2340	2026-03-23 19:17:45.289838-03	2026-03-23 19:17:45.28984-03	t	2026-04-01 15:03:39.725269-03	399	510	90.00	2058-11-30	f	\N		3	\N	190	3
2256	2026-03-23 19:17:45.287504-03	2026-03-23 19:17:45.287507-03	t	2026-04-01 15:03:39.725269-03	315	510	90.00	2051-11-30	f	\N		3	\N	190	3
2375	2026-03-23 19:17:45.291073-03	2026-03-23 19:17:45.291076-03	t	2026-04-01 15:03:39.725269-03	434	510	90.00	2061-10-30	f	\N		3	\N	190	3
1996	2026-03-23 19:17:45.278721-03	2026-03-23 19:17:45.278722-03	t	2026-04-01 15:03:39.725269-03	55	510	90.00	2030-03-30	f	\N		3	\N	190	3
2120	2026-03-23 19:17:45.282848-03	2026-03-23 19:17:45.28285-03	t	2026-04-01 15:03:39.725269-03	179	510	90.00	2040-07-30	f	\N		3	\N	190	3
2163	2026-03-23 19:17:45.284288-03	2026-03-23 19:17:45.284289-03	t	2026-04-01 15:03:39.725269-03	222	510	90.00	2044-03-01	f	\N		3	\N	190	3
2111	2026-03-23 19:17:45.282478-03	2026-03-23 19:17:45.282482-03	t	2026-04-01 15:03:39.725269-03	170	510	90.00	2039-10-30	f	\N		3	\N	190	3
2042	2026-03-23 19:17:45.280094-03	2026-03-23 19:17:45.280097-03	t	2026-04-01 15:03:39.725269-03	101	510	90.00	2034-01-30	f	\N		3	\N	190	3
2134	2026-03-23 19:17:45.283334-03	2026-03-23 19:17:45.283336-03	t	2026-04-01 15:03:39.725269-03	193	510	90.00	2041-09-30	f	\N		3	\N	190	3
2165	2026-03-23 19:17:45.284321-03	2026-03-23 19:17:45.284322-03	t	2026-04-01 15:03:39.725269-03	224	510	90.00	2044-04-30	f	\N		3	\N	190	3
2046	2026-03-23 19:17:45.280221-03	2026-03-23 19:17:45.280223-03	t	2026-04-01 15:03:39.725269-03	105	510	90.00	2034-05-30	f	\N		3	\N	190	3
2039	2026-03-23 19:17:45.279998-03	2026-03-23 19:17:45.28-03	t	2026-04-01 15:03:39.725269-03	98	510	90.00	2033-10-30	f	\N		3	\N	190	3
2364	2026-03-23 19:17:45.290653-03	2026-03-23 19:17:45.290655-03	t	2026-04-01 15:03:39.725269-03	423	510	90.00	2060-11-30	f	\N		3	\N	190	3
2304	2026-03-23 19:17:45.288747-03	2026-03-23 19:17:45.288748-03	t	2026-04-01 15:03:39.725269-03	363	510	90.00	2055-11-30	f	\N		3	\N	190	3
2033	2026-03-23 19:17:45.279802-03	2026-03-23 19:17:45.279805-03	t	2026-04-01 15:03:39.725269-03	92	510	90.00	2033-04-30	f	\N		3	\N	190	3
2031	2026-03-23 19:17:45.279739-03	2026-03-23 19:17:45.279741-03	t	2026-04-01 15:03:39.725269-03	90	510	90.00	2033-03-02	f	\N		3	\N	190	3
2309	2026-03-23 19:17:45.28883-03	2026-03-23 19:17:45.288831-03	t	2026-04-01 15:03:39.725269-03	368	510	90.00	2056-04-30	f	\N		3	\N	190	3
2399	2026-03-23 19:17:45.291898-03	2026-03-23 19:17:45.291901-03	t	2026-04-01 15:03:39.725269-03	458	510	90.00	2063-10-30	f	\N		3	\N	190	3
1972	2026-03-23 19:17:45.278328-03	2026-03-23 19:17:45.278329-03	t	2026-04-01 15:03:39.725269-03	31	510	90.00	2028-03-30	f	\N		3	\N	190	3
2207	2026-03-23 19:17:45.285848-03	2026-03-23 19:17:45.28585-03	t	2026-04-01 15:03:39.725269-03	266	510	90.00	2047-10-30	f	\N		3	\N	190	3
2359	2026-03-23 19:17:45.290484-03	2026-03-23 19:17:45.290487-03	t	2026-04-01 15:03:39.725269-03	418	510	90.00	2060-06-30	f	\N		3	\N	190	3
2148	2026-03-23 19:17:45.283791-03	2026-03-23 19:17:45.283794-03	t	2026-04-01 15:03:39.725269-03	207	510	90.00	2042-11-30	f	\N		3	\N	190	3
2069	2026-03-23 19:17:45.280969-03	2026-03-23 19:17:45.280971-03	t	2026-04-01 15:03:39.725269-03	128	510	90.00	2036-04-30	f	\N		3	\N	190	3
2110	2026-03-23 19:17:45.282295-03	2026-03-23 19:17:45.282403-03	t	2026-04-01 15:03:39.725269-03	169	510	90.00	2039-09-30	f	\N		3	\N	190	3
1955	2026-03-23 19:17:45.27804-03	2026-03-23 19:17:45.278041-03	t	2026-04-01 15:03:39.725269-03	14	510	90.00	2026-10-30	f	\N		3	\N	190	3
2185	2026-03-23 19:17:45.285144-03	2026-03-23 19:17:45.285146-03	t	2026-04-01 15:03:39.725269-03	244	510	90.00	2045-12-30	f	\N		3	\N	190	3
3121	2026-04-01 15:27:16.481913-03	2026-04-01 15:27:16.481914-03	f	\N	25	60	390.19	2027-09-01	f	\N		3	\N	262	3
3122	2026-04-01 15:27:16.481927-03	2026-04-01 15:27:16.481928-03	f	\N	26	60	390.19	2027-10-02	f	\N		3	\N	262	3
3123	2026-04-01 15:27:16.481942-03	2026-04-01 15:27:16.481943-03	f	\N	27	60	390.19	2027-11-01	f	\N		3	\N	262	3
3124	2026-04-01 15:27:16.481956-03	2026-04-01 15:27:16.481957-03	f	\N	28	60	390.19	2027-12-02	f	\N		3	\N	262	3
3125	2026-04-01 15:27:16.481971-03	2026-04-01 15:27:16.481971-03	f	\N	29	60	390.19	2028-01-01	f	\N		3	\N	262	3
3126	2026-04-01 15:27:16.481985-03	2026-04-01 15:27:16.481986-03	f	\N	30	60	390.19	2028-02-01	f	\N		3	\N	262	3
3127	2026-04-01 15:27:16.481999-03	2026-04-01 15:27:16.482-03	f	\N	31	60	390.19	2028-03-03	f	\N		3	\N	262	3
3128	2026-04-01 15:27:16.482013-03	2026-04-01 15:27:16.482014-03	f	\N	32	60	390.19	2028-04-01	f	\N		3	\N	262	3
3129	2026-04-01 15:27:16.482028-03	2026-04-01 15:27:16.482029-03	f	\N	33	60	390.19	2028-05-02	f	\N		3	\N	262	3
3130	2026-04-01 15:27:16.482043-03	2026-04-01 15:27:16.482043-03	f	\N	34	60	390.19	2028-06-01	f	\N		3	\N	262	3
3131	2026-04-01 15:27:16.482057-03	2026-04-01 15:27:16.482058-03	f	\N	35	60	390.19	2028-07-02	f	\N		3	\N	262	3
3132	2026-04-01 15:27:16.482072-03	2026-04-01 15:27:16.482073-03	f	\N	36	60	390.19	2028-08-01	f	\N		3	\N	262	3
3133	2026-04-01 15:27:16.482087-03	2026-04-01 15:27:16.482088-03	f	\N	37	60	390.19	2028-09-01	f	\N		3	\N	262	3
3134	2026-04-01 15:27:16.482101-03	2026-04-01 15:27:16.482102-03	f	\N	38	60	390.19	2028-10-02	f	\N		3	\N	262	3
3135	2026-04-01 15:27:16.482114-03	2026-04-01 15:27:16.482115-03	f	\N	39	60	390.19	2028-11-01	f	\N		3	\N	262	3
3136	2026-04-01 15:27:16.482128-03	2026-04-01 15:27:16.482129-03	f	\N	40	60	390.19	2028-12-02	f	\N		3	\N	262	3
3137	2026-04-01 15:27:16.482141-03	2026-04-01 15:27:16.482142-03	f	\N	41	60	390.19	2029-01-01	f	\N		3	\N	262	3
3138	2026-04-01 15:27:16.482155-03	2026-04-01 15:27:16.482156-03	f	\N	42	60	390.19	2029-02-01	f	\N		3	\N	262	3
3193	2026-04-01 15:28:14.930879-03	2026-04-01 15:28:14.93088-03	f	\N	37	60	513.12	2028-09-01	f	\N		3	\N	261	3
3194	2026-04-01 15:28:14.930894-03	2026-04-01 15:28:14.930895-03	f	\N	38	60	513.12	2028-10-02	f	\N		3	\N	261	3
3195	2026-04-01 15:28:14.930908-03	2026-04-01 15:28:14.930909-03	f	\N	39	60	513.12	2028-11-01	f	\N		3	\N	261	3
3196	2026-04-01 15:28:14.930922-03	2026-04-01 15:28:14.930923-03	f	\N	40	60	513.12	2028-12-02	f	\N		3	\N	261	3
3197	2026-04-01 15:28:14.930936-03	2026-04-01 15:28:14.930937-03	f	\N	41	60	513.12	2029-01-01	f	\N		3	\N	261	3
3198	2026-04-01 15:28:14.93095-03	2026-04-01 15:28:14.930951-03	f	\N	42	60	513.12	2029-02-01	f	\N		3	\N	261	3
3199	2026-04-01 15:28:14.930965-03	2026-04-01 15:28:14.930966-03	f	\N	43	60	513.12	2029-03-04	f	\N		3	\N	261	3
3200	2026-04-01 15:28:14.930979-03	2026-04-01 15:28:14.93098-03	f	\N	44	60	513.12	2029-04-01	f	\N		3	\N	261	3
3201	2026-04-01 15:28:14.930993-03	2026-04-01 15:28:14.930994-03	f	\N	45	60	513.12	2029-05-02	f	\N		3	\N	261	3
3202	2026-04-01 15:28:14.931007-03	2026-04-01 15:28:14.931008-03	f	\N	46	60	513.12	2029-06-01	f	\N		3	\N	261	3
3203	2026-04-01 15:28:14.931022-03	2026-04-01 15:28:14.931023-03	f	\N	47	60	513.12	2029-07-02	f	\N		3	\N	261	3
3204	2026-04-01 15:28:14.931036-03	2026-04-01 15:28:14.931037-03	f	\N	48	60	513.12	2029-08-01	f	\N		3	\N	261	3
3205	2026-04-01 15:28:14.931051-03	2026-04-01 15:28:14.931052-03	f	\N	49	60	513.12	2029-09-01	f	\N		3	\N	261	3
3206	2026-04-01 15:28:14.931065-03	2026-04-01 15:28:14.931066-03	f	\N	50	60	513.12	2029-10-02	f	\N		3	\N	261	3
3207	2026-04-01 15:28:14.931082-03	2026-04-01 15:28:14.931083-03	f	\N	51	60	513.12	2029-11-01	f	\N		3	\N	261	3
3208	2026-04-01 15:28:14.931097-03	2026-04-01 15:28:14.931098-03	f	\N	52	60	513.12	2029-12-02	f	\N		3	\N	261	3
3209	2026-04-01 15:28:14.931112-03	2026-04-01 15:28:14.931113-03	f	\N	53	60	513.12	2030-01-01	f	\N		3	\N	261	3
3210	2026-04-01 15:28:14.931127-03	2026-04-01 15:28:14.931128-03	f	\N	54	60	513.12	2030-02-01	f	\N		3	\N	261	3
3211	2026-04-01 15:28:14.931141-03	2026-04-01 15:28:14.931142-03	f	\N	55	60	513.12	2030-03-04	f	\N		3	\N	261	3
3212	2026-04-01 15:28:14.931158-03	2026-04-01 15:28:14.931159-03	f	\N	56	60	513.12	2030-04-01	f	\N		3	\N	261	3
3213	2026-04-01 15:28:14.931173-03	2026-04-01 15:28:14.931174-03	f	\N	57	60	513.12	2030-05-02	f	\N		3	\N	261	3
3214	2026-04-01 15:28:14.931187-03	2026-04-01 15:28:14.931188-03	f	\N	58	60	513.12	2030-06-01	f	\N		3	\N	261	3
3215	2026-04-01 15:28:14.931202-03	2026-04-01 15:28:14.931204-03	f	\N	59	60	513.12	2030-07-02	f	\N		3	\N	261	3
3216	2026-04-01 15:28:14.931218-03	2026-04-01 15:28:14.931219-03	f	\N	60	60	513.12	2030-08-01	f	\N		3	\N	261	3
3217	2026-04-01 15:55:27.861565-03	2026-04-01 15:55:27.861569-03	f	\N	1	5	1000.00	2026-04-01	f	\N		3	\N	314	3
3218	2026-04-01 15:55:27.86164-03	2026-04-01 15:55:27.861641-03	f	\N	2	5	1000.00	2026-05-01	f	\N		3	\N	314	3
3219	2026-04-01 15:55:27.861669-03	2026-04-01 15:55:27.86167-03	f	\N	3	5	1000.00	2026-06-01	f	\N		3	\N	314	3
3220	2026-04-01 15:55:27.86169-03	2026-04-01 15:55:27.861692-03	f	\N	4	5	1000.00	2026-07-01	f	\N		3	\N	314	3
3221	2026-04-01 15:55:27.861712-03	2026-04-01 15:55:27.861713-03	f	\N	5	5	1000.00	2026-08-01	f	\N		3	\N	314	3
3222	2026-04-01 18:17:22.549686-03	2026-04-01 18:17:22.549688-03	f	\N	1	2	35.76	2026-04-08	f	\N		\N	\N	336	\N
3223	2026-04-01 18:17:22.550774-03	2026-04-01 18:17:22.550776-03	f	\N	2	2	35.76	2026-05-08	f	\N		\N	\N	336	\N
159	2026-03-22 22:49:55.412478-03	2026-04-01 18:20:18.198283-03	f	\N	2	4	294.81	2026-02-07	t	2026-02-07		\N	\N	71	\N
160	2026-03-22 22:49:55.413132-03	2026-04-01 18:20:18.200945-03	f	\N	3	4	294.81	2026-03-07	t	2026-03-07		\N	\N	71	\N
189	2026-03-22 22:49:55.432954-03	2026-04-01 18:20:18.220503-03	f	\N	2	2	178.94	2026-04-07	t	2026-04-07		\N	\N	80	\N
\.


--
-- Data for Name: core_expensemonthskip; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY "public"."core_expensemonthskip" ("id", "created_at", "updated_at", "reference_month", "created_by_id", "expense_id", "updated_by_id") FROM stdin;
\.


--
-- Data for Name: core_financialsettings; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY "public"."core_financialsettings" ("id", "initial_balance", "initial_balance_date", "notes", "updated_at", "updated_by_id", "default_pix_key", "default_pix_key_type") FROM stdin;
1	0.00	2026-03-01	Saldo inicial estimado em março/2026	2026-03-22 22:48:04.219654-03	\N		
\.


--
-- Data for Name: core_furniture; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY "public"."core_furniture" ("id", "name", "description", "created_at", "created_by_id", "deleted_at", "deleted_by_id", "is_deleted", "updated_at", "updated_by_id") FROM stdin;
1	Fogão		2025-12-21 13:19:51.535468-03	\N	\N	\N	f	2025-12-21 13:19:51.628017-03	\N
2	Mesa com cadeiras		2025-12-21 13:19:51.535468-03	\N	\N	\N	f	2025-12-21 13:19:51.628017-03	\N
3	Armário de Cozinha		2025-12-21 13:19:51.535468-03	\N	\N	\N	f	2025-12-21 13:19:51.628017-03	\N
4	1 Sofá		2025-12-21 13:19:51.535468-03	\N	\N	\N	f	2025-12-21 13:19:51.628017-03	\N
5	Geladeira		2025-12-21 13:19:51.535468-03	\N	\N	\N	f	2025-12-21 13:19:51.628017-03	\N
6	Roupeiro		2025-12-21 13:19:51.535468-03	\N	\N	\N	f	2025-12-21 13:19:51.628017-03	\N
7	Cama de casal com colchão		2025-12-21 13:19:51.535468-03	\N	\N	\N	f	2025-12-21 13:19:51.628017-03	\N
8	Chuveiro		2025-12-21 13:19:51.535468-03	\N	\N	\N	f	2025-12-21 13:19:51.628017-03	\N
9	1 Rack		2025-12-21 13:19:51.535468-03	\N	\N	\N	f	2025-12-21 13:19:51.628017-03	\N
10	Máquina de lavar roupas		2025-12-21 13:19:51.535468-03	\N	\N	\N	f	2025-12-21 13:19:51.628017-03	\N
11	Botijão de gás		2025-12-21 13:19:51.535468-03	\N	\N	\N	f	2025-12-21 13:19:51.628017-03	\N
12	1 Poltrona		2025-12-21 13:19:51.535468-03	\N	\N	\N	f	2025-12-21 13:19:51.628017-03	\N
13	1 cortina blackout		2025-12-21 13:19:51.535468-03	\N	\N	\N	f	2025-12-21 13:19:51.628017-03	\N
14	Mesa com 1 cadeira		2025-12-21 13:19:51.535468-03	\N	\N	\N	f	2025-12-21 13:19:51.628017-03	\N
15	1 Cortina		2025-12-21 13:19:51.535468-03	\N	\N	\N	f	2025-12-21 13:19:51.628017-03	\N
16	Cama de solteiro com colchão		2025-12-21 13:19:51.535468-03	\N	\N	\N	f	2025-12-21 13:19:51.628017-03	\N
17	2 cortinas blackout		2025-12-21 13:19:51.535468-03	\N	\N	\N	f	2025-12-21 13:19:51.628017-03	\N
18	Armário Aéreo		2025-12-21 13:19:51.535468-03	\N	\N	\N	f	2025-12-21 13:19:51.628017-03	\N
19	Cortinas		2025-12-21 13:19:51.535468-03	\N	\N	\N	f	2025-12-21 13:19:51.628017-03	\N
20	Mesa com 4 cadeiras		2025-12-21 13:19:51.535468-03	\N	\N	\N	f	2025-12-21 13:19:51.628017-03	\N
21	2 Poltronas		2025-12-21 13:19:51.535468-03	\N	\N	\N	f	2025-12-21 13:19:51.628017-03	\N
22	Escrivaninha com cadeira		2025-12-21 13:19:51.535468-03	\N	\N	\N	f	2025-12-21 13:19:51.628017-03	\N
23	Mesa com 2 cadeiras		2025-12-21 13:19:51.535468-03	\N	\N	\N	f	2025-12-21 13:19:51.628017-03	\N
24	2 Cortinas		2025-12-21 13:19:51.535468-03	\N	\N	\N	f	2025-12-21 13:19:51.628017-03	\N
25	Geladeira Duplex		2025-12-21 13:19:51.535468-03	\N	\N	\N	f	2025-12-21 13:19:51.628017-03	\N
26	Cama de solteiro sem colchão		2025-12-21 13:19:51.535468-03	\N	\N	\N	f	2025-12-21 13:19:51.628017-03	\N
27	Mesa com 1 Banqueta		2025-12-21 13:19:51.535468-03	\N	\N	\N	f	2025-12-21 13:19:51.628017-03	\N
28	Cômoda		2025-12-21 13:19:51.535468-03	\N	\N	\N	f	2025-12-21 13:19:51.628017-03	\N
29	Mesa com Banquetas		2025-12-21 13:19:51.535468-03	\N	\N	\N	f	2025-12-21 13:19:51.628017-03	\N
30	Fogão de mesa		2025-12-21 13:19:51.535468-03	\N	\N	\N	f	2025-12-21 13:19:51.628017-03	\N
31	Frigobar		2025-12-21 13:19:51.535468-03	\N	\N	\N	f	2025-12-21 13:19:51.628017-03	\N
32	Mesa com 2 Banquetas		2025-12-21 13:19:51.535468-03	\N	\N	\N	f	2025-12-21 13:19:51.628017-03	\N
33	1 Sofá Cama		2025-12-21 13:19:51.535468-03	\N	\N	\N	f	2025-12-21 13:19:51.628017-03	\N
34	Escrivaninha		2025-12-21 13:19:51.535468-03	\N	\N	\N	f	2025-12-21 13:19:51.628017-03	\N
35	Cama de casal baú com colchão		2025-12-21 13:19:51.535468-03	\N	\N	\N	f	2025-12-21 13:19:51.628017-03	\N
36	Armário de canto		2025-12-21 13:19:51.535468-03	\N	\N	\N	f	2025-12-21 13:19:51.628017-03	\N
37	4 cortinas blackout		2025-12-21 13:19:51.535468-03	\N	\N	\N	f	2025-12-21 13:19:51.628017-03	\N
38	1 Luminária		2025-12-21 13:19:51.535468-03	\N	\N	\N	f	2025-12-21 13:19:51.628017-03	\N
39	Mesa com 3 cadeiras		2025-12-21 13:19:51.535468-03	\N	\N	\N	f	2025-12-21 13:19:51.628017-03	\N
40	Armário multiuso		2025-12-21 13:19:51.535468-03	\N	\N	\N	f	2025-12-21 13:19:51.628017-03	\N
41	Cama baú de solteiro com colchão		2025-12-21 13:19:51.535468-03	\N	\N	\N	f	2025-12-21 13:19:51.628017-03	\N
\.


--
-- Data for Name: core_income; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY "public"."core_income" ("id", "created_at", "updated_at", "is_deleted", "deleted_at", "description", "amount", "income_date", "is_recurring", "expected_monthly_amount", "is_received", "received_date", "notes", "building_id", "category_id", "created_by_id", "deleted_by_id", "updated_by_id", "person_id") FROM stdin;
1	2026-03-22 22:49:56.293598-03	2026-03-22 22:49:56.2936-03	f	\N	Aposentadoria Raul	1030.00	2024-01-01	t	1030.00	f	\N		\N	\N	\N	\N	\N	\N
2	2026-03-23 20:43:44.722714-03	2026-03-23 20:43:44.722738-03	f	\N	Empréstimo Alessandra	5000.00	2026-03-09	f	\N	t	\N		\N	\N	\N	\N	\N	7
\.


--
-- Data for Name: core_ipcaindex; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY "public"."core_ipcaindex" ("id", "reference_month", "value", "fetched_at") FROM stdin;
1	2024-03-01	6869.1400000000000	2026-03-27 13:39:29.33648-03
2	2024-04-01	6895.2400000000000	2026-03-27 13:39:29.36-03
3	2024-05-01	6926.9600000000000	2026-03-27 13:39:29.361247-03
4	2024-06-01	6941.5100000000000	2026-03-27 13:39:29.362506-03
5	2024-07-01	6967.8900000000000	2026-03-27 13:39:29.363517-03
6	2024-08-01	6966.5000000000000	2026-03-27 13:39:29.364612-03
7	2024-09-01	6997.1500000000000	2026-03-27 13:39:29.365671-03
8	2024-10-01	7036.3300000000000	2026-03-27 13:39:29.366526-03
9	2024-11-01	7063.7700000000000	2026-03-27 13:39:29.367406-03
10	2024-12-01	7100.5000000000000	2026-03-27 13:39:29.368323-03
11	2025-01-01	7111.8600000000000	2026-03-27 13:39:29.369807-03
12	2025-02-01	7205.0300000000000	2026-03-27 13:39:29.370982-03
13	2025-03-01	7245.3800000000000	2026-03-27 13:39:29.372466-03
14	2025-04-01	7276.5400000000000	2026-03-27 13:39:29.373568-03
15	2025-05-01	7295.4600000000000	2026-03-27 13:39:29.374824-03
16	2025-06-01	7312.9700000000000	2026-03-27 13:39:29.375893-03
17	2025-07-01	7331.9800000000000	2026-03-27 13:39:29.377145-03
18	2025-08-01	7323.9100000000000	2026-03-27 13:39:29.378342-03
19	2025-09-01	7359.0600000000000	2026-03-27 13:39:29.379777-03
20	2025-10-01	7365.6800000000000	2026-03-27 13:39:29.380918-03
21	2025-11-01	7378.9400000000000	2026-03-27 13:39:29.382195-03
22	2025-12-01	7403.2900000000000	2026-03-27 13:39:29.38352-03
23	2026-01-01	7427.7200000000000	2026-03-27 13:39:29.384732-03
24	2026-02-01	7479.7100000000000	2026-03-27 13:39:29.385766-03
25	2026-03-01	7545.5300000000000	2026-04-20 18:35:29.742336-03
\.


--
-- Data for Name: core_landlord; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY "public"."core_landlord" ("id", "created_at", "updated_at", "is_deleted", "deleted_at", "name", "nationality", "marital_status", "cpf_cnpj", "rg", "phone", "email", "street", "street_number", "complement", "neighborhood", "city", "state", "zip_code", "country", "is_active", "created_by_id", "deleted_by_id", "updated_by_id", "rent_adjustment_percentage") FROM stdin;
1	2026-01-19 17:12:51.381667-03	2026-03-27 12:35:43.705848-03	f	\N	Célia Maria Steinmetz	Brasileira	Casado(a)	957.236.250-04		(51) 99598-9025		Av. Circular	850		Vila Jardim	Porto Alegre	Rio Grande do Sul	91320-180	Brasil	t	\N	\N	\N	2.67
\.


--
-- Data for Name: core_lease; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY "public"."core_lease" ("id", "start_date", "validity_months", "tag_fee", "contract_generated", "contract_signed", "interfone_configured", "apartment_id", "responsible_tenant_id", "number_of_tenants", "created_at", "created_by_id", "deleted_at", "deleted_by_id", "is_deleted", "updated_at", "updated_by_id", "is_salary_offset", "prepaid_until", "cleaning_fee_paid", "deposit_amount", "tag_deposit_paid", "resident_dependent_id", "rental_value", "last_rent_increase_date", "pending_rental_value", "pending_rental_value_date") FROM stdin;
38	2025-09-01	12	50.00	t	t	t	39	48	1	2025-12-21 13:19:51.647193-03	\N	\N	\N	f	2026-03-27 11:53:04.949845-03	\N	f	\N	t	\N	t	\N	900.00	2025-09-10	\N	\N
4	2025-03-07	12	50.00	t	t	t	4	4	1	2025-12-21 13:19:51.647193-03	\N	\N	\N	f	2026-03-27 14:39:38.446262-03	\N	f	\N	t	\N	t	\N	750.00	2025-03-07	780.00	2026-05-07
41	2025-03-22	12	0.00	t	t	t	43	42	1	2025-12-21 13:19:51.647193-03	\N	\N	\N	f	2026-03-27 14:51:54.782973-03	\N	f	\N	t	\N	t	\N	1300.00	2025-03-22	1350.00	2026-05-22
19	2020-12-11	12	50.00	t	t	t	20	19	1	2025-12-21 13:19:51.647193-03	\N	\N	\N	f	2026-03-27 14:54:41.667793-03	\N	f	\N	f	\N	t	\N	745.00	2025-02-11	780.00	2026-05-11
44	2025-06-02	12	50.00	f	f	f	2	45	1	2025-12-21 13:19:51.647193-03	\N	2026-03-24 16:21:15.348523-03	3	t	2025-12-21 13:19:51.697775-03	\N	f	\N	t	1000.00	t	\N	1250.00	\N	\N	\N
9	2024-04-18	12	50.00	f	f	f	9	9	1	2025-12-21 13:19:51.647193-03	\N	2026-03-24 12:43:57.02727-03	3	t	2025-12-21 13:19:51.697775-03	\N	f	\N	f	\N	t	\N	900.00	\N	\N	\N
10	2017-11-09	12	80.00	f	f	f	10	10	2	2025-12-21 13:19:51.647193-03	\N	2026-03-24 12:44:08.884545-03	3	t	2025-12-21 13:19:51.697775-03	\N	f	\N	f	1300.00	t	\N	1000.00	\N	\N	\N
1	2025-07-23	12	50.00	f	f	f	1	51	1	2025-12-21 13:19:51.647193-03	\N	2026-03-24 13:13:36.517904-03	3	t	2025-12-21 13:19:51.697775-03	\N	f	2026-09-29	t	\N	t	\N	1300.00	\N	\N	\N
34	2024-07-28	12	80.00	f	f	f	35	12	1	2025-12-21 13:19:51.647193-03	\N	2026-03-24 13:31:23.330968-03	3	t	2025-12-21 13:19:51.697775-03	\N	f	\N	t	\N	t	\N	1400.00	\N	\N	\N
5	2025-11-13	12	80.00	t	f	f	5	53	2	2025-12-21 13:19:51.647193-03	\N	2026-03-22 22:49:36.866341-03	\N	t	2025-12-21 13:19:51.697775-03	\N	f	\N	t	\N	t	\N	1400.00	\N	\N	\N
7	2026-01-09	12	50.00	t	t	t	7	57	1	2025-12-21 13:19:51.647193-03	\N	2026-03-22 22:48:47.593268-03	\N	t	2026-01-20 20:24:50.975307-03	\N	f	\N	f	\N	f	\N	680.00	\N	\N	\N
23	2026-01-12	12	50.00	t	t	t	24	7	1	2025-12-21 13:19:51.647193-03	\N	\N	\N	f	2026-03-24 16:02:29.994842-03	\N	f	\N	t	\N	t	\N	934.00	2025-11-20	\N	\N
40	2024-10-28	6	50.00	t	t	t	42	41	1	2025-12-21 13:19:51.647193-03	\N	\N	\N	f	2025-12-21 13:19:51.697775-03	\N	f	\N	t	\N	t	\N	810.00	2025-11-20	\N	\N
32	2022-05-15	12	50.00	t	t	t	33	32	1	2025-12-21 13:19:51.647193-03	\N	\N	\N	f	2025-12-21 13:19:51.697775-03	\N	f	\N	t	\N	t	\N	934.00	2025-05-15	\N	\N
6	2025-04-08	12	50.00	t	t	t	6	6	1	2025-12-21 13:19:51.647193-03	\N	\N	\N	f	2025-12-21 13:19:51.697775-03	\N	f	\N	t	\N	t	\N	1000.00	2025-04-08	\N	\N
26	2024-05-27	12	50.00	t	t	t	27	26	1	2025-12-21 13:19:51.647193-03	\N	\N	\N	f	2025-12-21 13:19:51.697775-03	\N	f	\N	f	\N	t	\N	730.00	2025-05-27	\N	\N
52	2026-03-26	12	50.00	f	f	f	41	64	1	2026-03-26 18:12:31.001666-03	\N	\N	\N	f	2026-03-26 18:12:31.001673-03	\N	f	\N	t	\N	t	\N	1250.00	2026-03-02	\N	\N
15	2025-12-04	12	50.00	t	t	t	16	54	1	2025-12-21 13:19:51.647193-03	\N	\N	\N	f	2026-03-27 11:45:50.847548-03	\N	f	\N	t	\N	t	\N	1200.00	2025-12-04	\N	\N
50	2026-02-22	12	50.00	f	f	f	2	62	1	2026-03-24 16:27:01.441542-03	\N	\N	\N	f	2026-03-27 11:50:26.338997-03	\N	f	\N	t	\N	t	\N	1250.00	2026-02-22	\N	\N
48	2024-07-27	12	50.00	t	f	t	1	12	1	2026-03-24 13:31:29.475724-03	\N	\N	\N	f	2026-03-24 15:58:27.65496-03	\N	f	\N	t	\N	t	\N	1300.00	2026-02-02	\N	\N
31	2025-11-09	12	80.00	t	t	t	32	50	2	2025-12-21 13:19:51.647193-03	\N	\N	\N	f	2026-03-24 15:59:54.84437-03	\N	f	\N	t	1400.00	t	\N	1400.00	2025-11-20	\N	\N
45	2026-03-13	12	50.00	t	f	t	8	28	1	2026-03-24 13:09:06.528056-03	\N	\N	\N	f	2026-03-24 16:00:04.05228-03	\N	f	\N	t	\N	t	\N	1200.00	2026-03-13	\N	\N
24	2026-01-08	12	50.00	t	t	t	25	56	1	2025-12-21 13:19:51.647193-03	\N	\N	\N	f	2026-03-27 11:48:22.298108-03	\N	f	\N	f	\N	f	\N	630.00	2026-01-08	\N	\N
25	2023-09-09	12	50.00	t	t	t	26	25	1	2025-12-21 13:19:51.647193-03	\N	2026-03-22 22:48:59.903123-03	\N	t	2025-12-21 13:19:51.697775-03	\N	f	\N	f	\N	t	\N	745.00	\N	\N	\N
43	2026-01-30	12	50.00	t	t	t	29	59	1	2025-12-21 13:19:51.647193-03	\N	\N	\N	f	2026-03-27 11:48:56.17644-03	\N	f	\N	t	\N	t	\N	1400.00	2026-01-30	\N	\N
36	2024-02-18	12	50.00	t	t	t	37	37	1	2025-12-21 13:19:51.647193-03	\N	\N	\N	f	2026-03-27 14:54:11.19354-03	\N	f	\N	f	\N	t	\N	860.00	2025-02-18	920.00	2026-05-18
29	2025-12-25	12	50.00	t	t	t	30	58	1	2025-12-21 13:19:51.647193-03	\N	\N	\N	f	2026-03-27 11:49:20.220412-03	\N	f	\N	t	\N	t	\N	1300.00	2025-12-05	\N	\N
2	2024-11-17	12	50.00	t	t	t	14	2	1	2025-12-21 13:19:51.647193-03	\N	\N	\N	f	2026-03-27 11:56:33.117947-03	\N	f	\N	t	\N	t	\N	1200.00	2024-11-17	\N	\N
17	2025-07-29	12	80.00	t	f	f	18	47	2	2025-12-21 13:19:51.647193-03	\N	2026-03-22 22:48:35.268803-03	\N	t	2025-12-21 13:19:51.697775-03	\N	f	\N	t	\N	t	\N	1300.00	\N	\N	\N
30	2024-05-01	12	50.00	t	t	t	31	30	1	2025-12-21 13:19:51.647193-03	\N	\N	\N	f	2026-03-27 11:49:47.342352-03	\N	f	\N	f	\N	t	\N	950.00	2025-05-01	\N	\N
42	2023-07-30	12	80.00	t	f	t	3	28	2	2025-12-21 13:19:51.647193-03	\N	2026-03-22 22:49:24.558018-03	\N	t	2025-12-21 13:19:51.697775-03	\N	f	\N	t	\N	t	\N	1400.00	\N	\N	\N
33	2024-07-30	12	50.00	t	t	t	34	33	1	2025-12-21 13:19:51.647193-03	\N	\N	\N	f	2026-03-27 11:51:27.250972-03	\N	f	\N	t	\N	t	\N	750.00	2025-07-30	\N	\N
53	2026-03-07	12	50.00	t	f	f	35	65	1	2026-03-27 10:24:10.937534-03	\N	\N	\N	f	2026-03-27 11:51:48.4517-03	\N	f	\N	t	\N	t	\N	1400.00	2026-03-07	\N	\N
37	2025-12-09	6	50.00	t	t	t	38	55	1	2025-12-21 13:19:51.647193-03	\N	\N	\N	f	2026-03-27 11:52:43.326712-03	\N	f	\N	t	1000.00	t	\N	892.00	2025-12-09	\N	\N
39	2025-08-14	12	50.00	t	t	t	40	49	1	2025-12-21 13:19:51.647193-03	\N	\N	\N	f	2026-03-27 11:53:28.826144-03	\N	f	\N	t	\N	t	\N	860.00	2025-08-14	\N	\N
49	2026-03-25	12	50.00	f	f	t	3	61	1	2026-03-24 15:06:55.295517-03	\N	\N	\N	f	2026-03-27 11:55:35.585865-03	\N	f	\N	t	\N	t	\N	1400.00	2026-03-25	\N	\N
13	2019-11-27	12	50.00	t	t	t	13	13	1	2025-12-21 13:19:51.647193-03	\N	\N	\N	f	2026-03-27 11:56:10.766556-03	\N	t	\N	t	\N	t	\N	1000.00	2026-03-27	\N	\N
8	2024-11-30	12	80.00	t	t	t	8	8	2	2025-12-21 13:19:51.647193-03	\N	2026-03-22 22:49:12.237015-03	\N	t	2025-12-21 13:19:51.697775-03	\N	f	\N	f	\N	t	\N	1200.00	\N	\N	\N
46	2025-07-22	12	50.00	f	f	f	9	51	1	2026-03-24 13:13:42.666396-03	\N	2026-03-24 13:21:48.310774-03	3	t	2026-03-24 13:13:42.666398-03	\N	f	\N	t	\N	t	\N	900.00	\N	\N	\N
20	2024-04-30	12	50.00	t	t	t	21	20	1	2025-12-21 13:19:51.647193-03	\N	\N	\N	f	2026-03-27 14:21:16.86777-03	\N	f	\N	f	\N	t	\N	730.00	2025-04-30	\N	\N
12	2025-06-01	12	80.00	f	f	f	12	44	2	2025-12-21 13:19:51.647193-03	\N	2026-03-24 13:51:09.858546-03	3	t	2025-12-21 13:19:51.697775-03	\N	f	\N	t	\N	t	\N	1400.00	\N	\N	\N
27	2024-04-21	12	50.00	f	f	f	28	27	1	2025-12-21 13:19:51.647193-03	\N	2026-03-24 14:16:18.011635-03	3	t	2025-12-21 13:19:51.697775-03	\N	f	\N	f	\N	t	\N	630.00	\N	\N	\N
11	2022-02-07	12	50.00	t	t	t	11	11	1	2025-12-21 13:19:51.647193-03	\N	\N	\N	f	2025-12-21 13:19:51.697775-03	\N	f	\N	t	\N	t	\N	934.00	2025-05-07	\N	\N
14	2024-07-15	12	50.00	t	t	t	15	14	1	2025-12-21 13:19:51.647193-03	\N	\N	\N	f	2026-03-27 11:46:06.380046-03	\N	f	\N	t	\N	t	\N	1300.00	2026-03-27	\N	\N
16	2024-11-12	12	50.00	t	t	t	17	16	1	2025-12-21 13:19:51.647193-03	\N	\N	\N	f	2026-03-27 11:46:31.526421-03	\N	f	\N	t	\N	t	\N	1300.00	2026-03-27	\N	\N
22	2024-09-25	12	50.00	t	t	t	23	22	1	2025-12-21 13:19:51.647193-03	\N	\N	\N	f	2025-12-21 13:19:51.697775-03	\N	f	\N	f	\N	t	\N	890.00	2025-11-20	\N	\N
18	2024-10-24	12	50.00	t	t	t	19	18	1	2025-12-21 13:19:51.647193-03	\N	\N	\N	f	2025-12-21 13:19:51.697775-03	\N	f	\N	f	\N	t	\N	1100.00	2025-11-20	\N	\N
47	2025-07-21	12	50.00	t	f	t	10	51	1	2026-03-24 13:21:54.431043-03	\N	\N	\N	f	2026-03-24 16:07:40.952756-03	\N	f	\N	t	\N	t	\N	1000.00	2026-02-01	\N	\N
51	2025-11-13	12	50.00	f	f	f	12	53	1	2026-03-26 13:09:33.951932-03	\N	\N	\N	f	2026-03-26 13:09:33.95194-03	\N	f	\N	t	\N	t	\N	1400.00	2026-01-01	\N	\N
35	2024-03-15	12	50.00	t	t	t	36	36	1	2025-12-21 13:19:51.647193-03	\N	\N	\N	f	2026-03-27 14:22:06.656655-03	\N	f	\N	f	\N	t	\N	900.00	2026-05-15	\N	\N
21	2022-01-13	12	50.00	t	t	t	22	21	1	2025-12-21 13:19:51.647193-03	\N	\N	\N	f	2026-03-27 14:45:39.078459-03	\N	f	\N	f	\N	t	\N	750.00	2025-01-13	800.00	2026-05-13
\.


--
-- Data for Name: core_lease_tenants; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY "public"."core_lease_tenants" ("id", "lease_id", "tenant_id") FROM stdin;
2	2	2
4	4	4
6	6	6
8	8	8
9	9	9
10	10	10
11	11	11
13	13	13
14	14	14
16	16	16
18	18	18
19	19	19
20	20	20
21	21	21
22	22	22
25	25	25
26	26	26
27	27	27
31	30	30
33	32	32
34	33	33
36	35	36
37	36	37
41	40	41
42	41	42
43	42	28
47	12	44
49	44	45
53	38	48
54	39	49
56	34	12
57	1	51
60	31	50
61	17	47
62	5	53
63	15	54
64	37	55
65	24	56
66	7	57
67	23	7
68	29	58
69	45	28
70	46	51
71	47	51
72	48	12
73	49	61
74	43	59
75	50	62
76	51	53
77	52	64
78	53	65
\.


--
-- Data for Name: core_monthsnapshot; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY "public"."core_monthsnapshot" ("id", "created_at", "updated_at", "reference_month", "total_rent_income", "total_extra_income", "total_person_payments_received", "total_income", "total_card_installments", "total_loan_installments", "total_utility_bills", "total_fixed_expenses", "total_one_time_expenses", "total_employee_salary", "total_owner_repayments", "total_person_stipends", "total_debt_installments", "total_property_tax", "total_expenses", "net_balance", "cumulative_ending_balance", "detailed_breakdown", "is_finalized", "finalized_at", "notes", "created_by_id", "updated_by_id") FROM stdin;
\.


--
-- Data for Name: core_notification; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY "public"."core_notification" ("id", "created_at", "updated_at", "type", "title", "body", "is_read", "read_at", "sent_at", "data", "created_by_id", "recipient_id", "updated_by_id") FROM stdin;
\.


--
-- Data for Name: core_oauth_exchange_code; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY "public"."core_oauth_exchange_code" ("id", "code", "access_token", "refresh_token", "created_at", "is_used", "user_id") FROM stdin;
\.


--
-- Data for Name: core_paymentproof; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY "public"."core_paymentproof" ("id", "created_at", "updated_at", "is_deleted", "deleted_at", "reference_month", "file", "pix_code", "status", "reviewed_at", "rejection_reason", "created_by_id", "deleted_by_id", "lease_id", "reviewed_by_id", "updated_by_id") FROM stdin;
\.


--
-- Data for Name: core_person; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY "public"."core_person" ("id", "created_at", "updated_at", "is_deleted", "deleted_at", "name", "relationship", "phone", "email", "is_owner", "is_employee", "notes", "created_by_id", "deleted_by_id", "updated_by_id", "user_id", "initial_balance", "initial_balance_date", "pix_key", "pix_key_type") FROM stdin;
1	2026-03-22 22:48:04.257589-03	2026-03-22 22:48:04.257613-03	f	\N	Rodrigo	filho			f	f		\N	\N	\N	\N	0.00	\N		
2	2026-03-22 22:48:04.261052-03	2026-03-22 22:48:04.261055-03	f	\N	Tiago	filho			t	f	Proprietário dos kitnets 101 e 103 do prédio 836	\N	\N	\N	\N	0.00	\N		
4	2026-03-22 22:48:04.265593-03	2026-03-22 22:48:04.265596-03	f	\N	Junior	filho			f	f		\N	\N	\N	\N	0.00	\N		
5	2026-03-22 22:48:04.266913-03	2026-03-22 22:48:04.266915-03	f	\N	Rosa	funcionária			f	t	Mora no kitnet 206 do prédio 850. Aluguel compensado no salário.	\N	\N	\N	\N	0.00	\N		
6	2026-03-22 22:48:04.268146-03	2026-03-22 22:48:04.268148-03	f	\N	Camila	filha			f	f		\N	\N	\N	\N	0.00	\N		
7	2026-03-23 20:32:07.377975-03	2026-03-23 20:32:07.378004-03	f	\N	Alessandra	Outro			f	f		\N	\N	\N	\N	0.00	\N		
3	2026-03-22 22:48:04.264007-03	2026-03-22 22:48:04.26401-03	f	\N	Alvaro	genro			t	f	Proprietário dos kitnets 200 e 203 do prédio 836	\N	\N	\N	\N	1449.00	2026-02-01		
\.


--
-- Data for Name: core_personincome; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY "public"."core_personincome" ("id", "created_at", "updated_at", "is_deleted", "deleted_at", "income_type", "fixed_amount", "start_date", "end_date", "is_active", "notes", "apartment_id", "created_by_id", "deleted_by_id", "person_id", "updated_by_id") FROM stdin;
1	2026-03-22 22:48:04.300726-03	2026-03-22 22:48:04.30073-03	f	\N	apartment_rent	\N	2026-01-01	\N	t	Proprietário	15	\N	\N	2	\N
2	2026-03-22 22:48:04.304601-03	2026-03-22 22:48:04.304604-03	f	\N	apartment_rent	\N	2026-01-01	\N	t	Proprietário	17	\N	\N	2	\N
3	2026-03-22 22:48:04.306695-03	2026-03-22 22:48:04.306697-03	f	\N	apartment_rent	\N	2026-01-01	\N	t	Proprietário	29	\N	\N	3	\N
4	2026-03-22 22:48:04.308838-03	2026-03-22 22:48:04.30884-03	f	\N	apartment_rent	\N	2026-01-01	\N	t	Proprietário	32	\N	\N	3	\N
5	2026-03-22 22:48:04.310367-03	2026-03-22 22:48:04.310369-03	f	\N	fixed_stipend	1100.00	2026-01-01	\N	t	Equivalente a 1 kitnet	\N	\N	\N	1	\N
6	2026-03-22 22:48:04.31258-03	2026-03-22 22:48:04.312583-03	f	\N	fixed_stipend	1100.00	2026-01-01	\N	t	Equivalente a 1 kitnet	\N	\N	\N	4	\N
\.


--
-- Data for Name: core_personpayment; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY "public"."core_personpayment" ("id", "created_at", "updated_at", "is_deleted", "deleted_at", "reference_month", "amount", "payment_date", "notes", "created_by_id", "deleted_by_id", "person_id", "updated_by_id") FROM stdin;
1	2026-03-22 22:49:56.321058-03	2026-03-22 22:49:56.321061-03	f	\N	2026-03-01	1922.90	2026-03-10	Pago integral março	\N	\N	2	\N
2	2026-03-22 22:49:56.324719-03	2026-03-22 22:49:56.324721-03	f	\N	2026-03-01	5000.00	2026-03-05	Pagamento parcial março	\N	\N	1	\N
3	2026-03-22 22:49:56.32539-03	2026-03-22 22:49:56.325392-03	f	\N	2026-03-01	767.00	2026-03-10	Pagamento parcial março, falta R$400	\N	\N	4	\N
4	2026-03-23 18:03:35.429784-03	2026-03-23 18:03:35.429791-03	f	\N	2026-03-01	600.00	2026-03-23	Pagamento empréstimo adicionado	3	\N	2	3
6	2026-03-30 13:38:02.095323-03	2026-03-30 13:38:02.095328-03	t	2026-04-01 14:20:29.416598-03	2026-03-01	1100.00	2026-03-30		\N	\N	1	\N
5	2026-03-23 19:34:02.488806-03	2026-04-01 14:20:29.43318-03	f	\N	2026-03-01	6241.02	2026-03-23		\N	\N	1	\N
7	2026-04-01 15:30:52.423069-03	2026-04-01 15:30:52.423076-03	f	\N	2026-04-01	1207.00	2026-04-01		\N	\N	1	\N
\.


--
-- Data for Name: core_personpaymentschedule; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY "public"."core_personpaymentschedule" ("id", "created_at", "updated_at", "is_deleted", "deleted_at", "reference_month", "due_day", "amount", "created_by_id", "deleted_by_id", "person_id", "updated_by_id") FROM stdin;
\.


--
-- Data for Name: core_rentadjustment; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY "public"."core_rentadjustment" ("id", "created_at", "updated_at", "is_deleted", "deleted_at", "adjustment_date", "percentage", "previous_value", "new_value", "apartment_updated", "created_by_id", "deleted_by_id", "lease_id", "updated_by_id") FROM stdin;
1	2026-03-27 14:22:06.631675-03	2026-03-27 14:22:06.631681-03	f	\N	2026-05-15	4.65	860.00	900.00	t	\N	\N	35	\N
2	2026-03-27 14:38:46.524427-03	2026-03-27 14:38:46.524449-03	f	\N	2026-05-22	3.85	1300.00	1350.00	t	\N	\N	41	\N
3	2026-03-27 14:39:38.439208-03	2026-03-27 14:39:38.439212-03	f	\N	2026-05-07	4.00	750.00	780.00	t	\N	\N	4	\N
4	2026-03-27 14:45:39.063849-03	2026-03-27 14:45:39.063857-03	f	\N	2026-05-13	6.67	750.00	800.00	t	\N	\N	21	\N
7	2026-03-27 14:51:19.818353-03	2026-03-27 14:51:19.81836-03	f	\N	2026-05-22	3.85	1300.00	1350.00	t	\N	\N	41	\N
8	2026-03-27 14:51:54.772737-03	2026-03-27 14:51:54.772743-03	f	\N	2026-05-22	3.85	1300.00	1350.00	t	\N	\N	41	\N
9	2026-03-27 14:54:11.174489-03	2026-03-27 14:54:11.174496-03	f	\N	2026-05-18	6.98	860.00	920.00	t	\N	\N	36	\N
10	2026-03-27 14:54:41.657628-03	2026-03-27 14:54:41.657634-03	f	\N	2026-05-11	4.70	745.00	780.00	t	\N	\N	19	\N
\.


--
-- Data for Name: core_rentpayment; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY "public"."core_rentpayment" ("id", "created_at", "updated_at", "is_deleted", "deleted_at", "reference_month", "amount_paid", "payment_date", "notes", "created_by_id", "deleted_by_id", "lease_id", "updated_by_id") FROM stdin;
2	2026-03-27 11:56:48.039228-03	2026-03-27 11:56:48.039238-03	f	\N	2026-03-01	1300.00	2026-03-27		3	\N	41	3
3	2026-03-27 11:56:51.31287-03	2026-03-27 11:56:51.312878-03	f	\N	2026-03-01	750.00	2026-03-27		3	\N	4	3
4	2026-03-27 11:56:52.203353-03	2026-03-27 11:56:52.203363-03	f	\N	2026-03-01	934.00	2026-03-27		3	\N	32	3
5	2026-03-27 11:56:53.069319-03	2026-03-27 11:56:53.069329-03	f	\N	2026-03-01	934.00	2026-03-27		3	\N	23	3
6	2026-03-27 11:56:56.748901-03	2026-03-27 11:56:56.748908-03	f	\N	2026-03-01	1000.00	2026-03-27		3	\N	6	3
7	2026-03-27 11:56:57.266569-03	2026-03-27 11:56:57.266578-03	f	\N	2026-03-01	745.00	2026-03-27		3	\N	19	3
8	2026-03-27 11:56:57.74152-03	2026-03-27 11:56:57.741528-03	f	\N	2026-03-01	1200.00	2026-03-27		3	\N	15	3
9	2026-03-27 11:56:58.852929-03	2026-03-27 11:56:58.852937-03	f	\N	2026-03-01	1000.00	2026-03-27		3	\N	47	3
10	2026-03-27 11:56:59.416956-03	2026-03-27 11:56:59.416962-03	f	\N	2026-03-01	1400.00	2026-03-27		3	\N	51	3
11	2026-03-27 11:57:01.541557-03	2026-03-27 11:57:01.541564-03	f	\N	2026-03-01	900.00	2026-03-27		3	\N	38	3
12	2026-03-27 11:57:02.043829-03	2026-03-27 11:57:02.043836-03	f	\N	2026-03-01	730.00	2026-03-27		3	\N	26	3
13	2026-03-27 11:57:02.434836-03	2026-03-27 11:57:02.434844-03	f	\N	2026-03-01	860.00	2026-03-27		3	\N	35	3
14	2026-03-27 11:57:03.025207-03	2026-03-27 11:57:03.025214-03	f	\N	2026-03-01	950.00	2026-03-27		3	\N	30	3
15	2026-03-27 11:57:03.663067-03	2026-03-27 11:57:03.663075-03	f	\N	2026-03-01	750.00	2026-03-27		3	\N	21	3
16	2026-03-27 11:57:04.783138-03	2026-03-27 11:57:04.783146-03	f	\N	2026-03-01	860.00	2026-03-27		3	\N	39	3
17	2026-03-27 11:57:05.591228-03	2026-03-27 11:57:05.591235-03	f	\N	2026-03-01	890.00	2026-03-27		3	\N	22	3
18	2026-03-27 11:57:05.935211-03	2026-03-27 11:57:05.935219-03	f	\N	2026-03-01	860.00	2026-03-27		3	\N	36	3
19	2026-03-27 11:57:06.316683-03	2026-03-27 11:57:06.316691-03	f	\N	2026-03-01	750.00	2026-03-27		3	\N	33	3
20	2026-03-27 11:57:06.756228-03	2026-03-27 11:57:06.756235-03	f	\N	2026-03-01	1100.00	2026-03-27		3	\N	18	3
21	2026-03-27 11:57:07.789171-03	2026-03-27 11:57:07.789179-03	f	\N	2026-03-01	892.00	2026-03-27		3	\N	37	3
22	2026-03-27 11:57:08.714845-03	2026-03-27 11:57:08.714854-03	f	\N	2026-03-01	630.00	2026-03-27		3	\N	24	3
23	2026-03-27 11:57:10.355837-03	2026-03-27 11:57:10.355845-03	f	\N	2026-03-01	1300.00	2026-03-27		3	\N	29	3
24	2026-03-27 11:57:10.817011-03	2026-03-27 11:57:10.817019-03	f	\N	2026-03-01	934.00	2026-03-27		3	\N	11	3
25	2026-03-27 11:57:11.275005-03	2026-03-27 11:57:11.275011-03	f	\N	2026-03-01	1400.00	2026-03-27		3	\N	49	3
26	2026-03-27 11:57:12.60477-03	2026-03-27 11:57:12.604778-03	f	\N	2026-03-01	1250.00	2026-03-27		3	\N	50	3
27	2026-03-27 11:57:13.378238-03	2026-03-27 11:57:13.378245-03	f	\N	2026-03-01	1250.00	2026-03-27		3	\N	52	3
28	2026-03-27 11:57:14.85116-03	2026-03-27 11:57:14.851168-03	f	\N	2026-03-01	1400.00	2026-03-27		3	\N	53	3
29	2026-03-30 12:52:21.896475-03	2026-03-30 12:52:21.896479-03	f	\N	2026-03-01	1300.00	2026-03-30		3	\N	48	3
30	2026-03-30 12:52:29.573937-03	2026-03-30 12:52:29.573941-03	f	\N	2026-03-01	810.00	2026-03-30		3	\N	40	3
\.


--
-- Data for Name: core_tenant; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY "public"."core_tenant" ("id", "name", "cpf_cnpj", "is_company", "rg", "phone", "marital_status", "profession", "due_day", "user_id", "created_at", "created_by_id", "deleted_at", "deleted_by_id", "is_deleted", "updated_at", "updated_by_id", "warning_count") FROM stdin;
1	Rafael Legnaghi da Silva	004.279.882-50	f	24659592	(92) 98230-9914	Solteiro	Auxiliar de Logística	30	\N	2025-12-21 13:19:51.718464-03	\N	\N	\N	f	2025-12-21 13:19:51.779977-03	\N	0
5	Luiz Edgar Rosa Junior	018.573.750-17	f	01857375017	(47) 99278-3236	Solteiro	Obras/Janelas	7	\N	2025-12-21 13:19:51.718464-03	\N	\N	\N	f	2025-12-21 13:19:51.779977-03	\N	0
17	André Becker de Oliveira	488.807.950-15	f	1077736542	(51) 98687-5678	Casado	Aposentado	10	\N	2025-12-21 13:19:51.718464-03	\N	\N	\N	f	2025-12-21 13:19:51.779977-03	\N	0
23	Hugo Daniel Maassen	905.807.530-34	f	5003453767	(51) 99857-4597	Solteiro	Motorista	7	\N	2025-12-21 13:19:51.718464-03	\N	\N	\N	f	2025-12-21 13:19:51.779977-03	\N	0
24	Mateus William de Matos	853.634.440-04	f	9117479296	(51) 99273-6729	Solteiro	-	11	\N	2025-12-21 13:19:51.718464-03	\N	\N	\N	f	2025-12-21 13:19:51.779977-03	\N	0
31	Felipe Matheus Gatti	036.582.420-86	f	2110831175	(51) 99246-0217	Solteiro	Assistente comercial	1	\N	2025-12-21 13:19:51.718464-03	\N	\N	\N	f	2025-12-21 13:19:51.779977-03	\N	0
34	Lucas Anselmo da Silva	102.550.434-81	f	3445752	(83) 99421-6063	Solteiro	Cozinheiro	1	\N	2025-12-21 13:19:51.718464-03	\N	\N	\N	f	2025-12-21 13:19:51.779977-03	\N	0
35	Adelson Anselmo da Silva	060.221.444-00	f	8139346781	-	-	-	1	\N	2025-12-21 13:19:51.718464-03	\N	\N	\N	f	2025-12-21 13:19:51.779977-03	\N	0
39	Helia Renata Menezes da Silva	035.695.580-02	f	6112158149	(53) 99951-5324	Solteiro	Auxiliar de departamento pessoal	27	\N	2025-12-21 13:19:51.718464-03	\N	\N	\N	f	2025-12-21 13:19:51.779977-03	\N	0
3	José Antônio Soares	475.244.130-68	f	8031698601	(51)99398-4501	Solteiro	Empresário (Empresa Energia Solar)	10	\N	2025-12-21 13:19:51.718464-03	\N	\N	\N	f	2025-12-21 13:19:51.779977-03	\N	0
43	Cristiano dos Santos Gomes	01690196084	f	5098362972	(51) 99525-5911	Solteiro	Barista	28	\N	2025-12-21 13:19:51.718464-03	\N	\N	\N	f	2025-12-21 13:19:51.779977-03	\N	0
46	Kevyn Cristiano Maciel Silva	043.038.460-23	f	8110296582	99212-8337	Solteiro	Barbeiro Autônomo	2	\N	2025-12-21 13:19:51.718464-03	\N	\N	\N	f	2025-12-21 13:19:51.779977-03	\N	0
52	Makyson Rodrigues Pereira	042.004.502-32	f	7899711	(51) 98914-4688	Solteiro	Garçom	23	\N	2025-12-21 13:19:51.718464-03	\N	\N	\N	f	2025-12-21 13:19:51.779977-03	\N	0
42	Leonardo Araújo Santos	015.674.960-24	f	2100730635	(51) 99530-9344	Solteiro	Product Manager	10	\N	2025-12-21 13:19:51.718464-03	\N	\N	\N	f	2025-12-21 13:19:51.779977-03	\N	0
4	Thais Santiago Ferreira Senna	051.443.010-96	f	5132596635	(51) 98121-9267	Solteira	Tecnica em Segurança do trabalho	7	\N	2025-12-21 13:19:51.718464-03	\N	\N	\N	f	2025-12-21 13:19:51.779977-03	\N	0
41	Tainá Francisca Menezes da Silveira	038.811.610-23	f	9130325393	(51) 99560-1750	Solteiro	Garçonete	28	\N	2025-12-21 13:19:51.718464-03	\N	\N	\N	f	2025-12-21 13:19:51.779977-03	\N	0
32	Pedro Machado Toledo	441.023.180-53	f	8016513221	(51) 98452-4151	Divorciado	Vigia	15	\N	2025-12-21 13:19:51.718464-03	\N	\N	\N	f	2025-12-21 13:19:51.779977-03	\N	0
7	Débora Eli de Oliveira Flores	032.303.160-96	f	1121244212	(51) 99765-8113	Solteira	Recepção/coleta, exames laboratoriais	10	\N	2025-12-21 13:19:51.718464-03	\N	\N	\N	f	2025-12-21 13:19:51.779977-03	\N	0
10	Juarez Nunes Alves Junior	464.229.600-00	f	1034202026	(51) 98147-1932	Solteiro	Auxiliar de limpeza	9	\N	2025-12-21 13:19:51.718464-03	\N	\N	\N	f	2025-12-21 13:19:51.779977-03	\N	0
9	Taiane Santiago Vincenti	052.507.070-25	f	8120866151	(51) 98468-3190	Solteiro	Auxiliar de escritório	18	\N	2025-12-21 13:19:51.718464-03	\N	\N	\N	f	2025-12-21 13:19:51.779977-03	\N	0
45	Fabio Luis Both	601.545.190-49	f	01174512165	981494003	Solteiro	Motorista	10	\N	2025-12-21 13:19:51.718464-03	\N	\N	\N	f	2025-12-21 13:19:51.779977-03	\N	0
6	Ezequiel Miranda Siqueira	048.191.290-82	f	9110711091	(55) 99146-2131	Solteiro	Assistente Social	8	\N	2025-12-21 13:19:51.718464-03	\N	\N	\N	f	2025-12-21 13:19:51.779977-03	\N	0
19	Luis Felipe Leal	911.086.910-72	f	7046438871	(51) 99346-1895	Solteiro	Autonomo	11	\N	2025-12-21 13:19:51.718464-03	\N	\N	\N	f	2025-12-21 13:19:51.779977-03	\N	0
15	Lucas Alves Lima	117.941.586-85	f		(34) 99163-6884	Solteiro	Analista da Telecom	17	\N	2025-12-21 13:19:51.718464-03	\N	\N	\N	f	2025-12-21 13:19:51.779977-03	\N	0
29	Camila Corrêa Xaviar	808.352.520-00	f		(51) 99328-5494	Solteiro	Corretora de Imóveis	30	\N	2025-12-21 13:19:51.718464-03	\N	\N	\N	f	2025-12-21 13:19:51.779977-03	\N	0
38	Joaquim Garcez de Moraes Junior	329.967.487-00	f		(51) 99470-3883	Casado	Médico	27	\N	2025-12-21 13:19:51.718464-03	\N	\N	\N	f	2025-12-21 13:19:51.779977-03	\N	0
40	Jefferson Arley Rosero Marín	706.514.282-54	f		(44) 99912-9026	Solteiro	Cozinheiro	860	\N	2025-12-21 13:19:51.718464-03	\N	\N	\N	f	2025-12-21 13:19:51.779977-03	\N	0
54	Isadora Fontanella Rodrigues	038.391.780-88	f		(55) 99921-3456	Solteiro(a)	Consultor de Vendas	4	\N	2025-12-21 13:19:51.718464-03	\N	\N	\N	f	2025-12-21 13:19:51.779977-03	\N	0
51	Marcos Vinicius Gomes Mafra	048.104.202-48	f		(48) 99910-3080	Solteiro	Garçom	23	\N	2025-12-21 13:19:51.718464-03	\N	\N	\N	f	2025-12-21 13:19:51.779977-03	\N	0
53	Érica Mendes Siqueira	601.366.230-42	f	5135207099	(51) 985610664	Solteiro(a)	Recepcionista	13	\N	2025-12-21 13:19:51.718464-03	\N	\N	\N	f	2025-12-21 13:19:51.779977-03	\N	0
48	Franciele farias dos Santos	032.356.060-17	f	5116421917	(51) 99165-0991	Solteiro(a)	Assistente administrativo	1	\N	2025-12-21 13:19:51.718464-03	\N	\N	\N	f	2025-12-21 13:19:51.779977-03	\N	0
12	Adriana Caldas	008.490.880-70	f		(51) 98139-1790	Solteiro	Auxiliar de Limpeza	29	\N	2025-12-21 13:19:51.718464-03	\N	\N	\N	f	2025-12-21 13:19:51.779977-03	\N	0
26	Matheus de Oliveira Ruas	044.789.570-29	f		(47) 99680-4990	Solteiro	Auxiliar de Produção	5	\N	2025-12-21 13:19:51.718464-03	\N	\N	\N	f	2025-12-21 13:19:51.779977-03	\N	0
57	Edwin Daniel Rodriguez Rondon	602.894.470-03	f		(47) 99668-5107	Solteiro(a)	funcionário COOTRAPIVA	1	\N	2026-01-20 20:22:43.739451-03	\N	\N	\N	f	2026-01-20 20:22:43.739456-03	\N	0
25	Adriano Ramos	020.689.550-08	f	670211412	(51) 982439244	Solteiro	Gerente de Mercado	9	\N	2025-12-21 13:19:51.718464-03	\N	\N	\N	f	2025-12-21 13:19:51.779977-03	\N	0
36	Luiz Carlos Toledo	008.273.828-98	f		(51) 99879-8034	Solteiro	Aposentado	15	\N	2025-12-21 13:19:51.718464-03	\N	\N	\N	f	2025-12-21 13:19:51.779977-03	\N	0
30	Salomão Batista Barbosa	023.101-466-09	f	20836165	(51) 98598-6403	Solteiro	Atendente	1	\N	2025-12-21 13:19:51.718464-03	\N	\N	\N	f	2025-12-21 13:19:51.779977-03	\N	0
50	Alexandre Mendonça Tonaizer	895.676.170-15	f	7974747	(51) 980132447	Solteiro(a)	Barbeiro e cabelereiro	1	\N	2025-12-21 13:19:51.718464-03	\N	\N	\N	f	2025-12-21 13:19:51.779977-03	\N	0
21	Luciano da Costa de Souza	644.300.730-15	f	5018012871	(51) 98974-2277	Solteiro	-	13	\N	2025-12-21 13:19:51.718464-03	\N	\N	\N	f	2025-12-21 13:19:51.779977-03	\N	0
49	Gustavo Ferraz Ribeiro	036.549.080-63	f	2119870505	(51) 98048-9747	Solteiro	Operador de máquinas	5	\N	2025-12-21 13:19:51.718464-03	\N	\N	\N	f	2025-12-21 13:19:51.779977-03	\N	0
47	Norbetzi Del Carmen Martínez Flores	066.486.077.00	f		(24) 99940-3227	Solteiro(a)	Professora de Música	29	\N	2025-12-21 13:19:51.718464-03	\N	\N	\N	f	2025-12-21 13:19:51.779977-03	\N	0
14	Rafael Becker Kauer	010.003.350-46	f		(51) 99639-5116	Solteiro	Beneficiário INSS	15	\N	2025-12-21 13:19:51.718464-03	\N	\N	\N	f	2025-12-21 13:19:51.779977-03	\N	0
28	Beatriz Tavares Spolarovi	034.356.810-12	f	1117966414	(51) 99216-6414	Solteiro	Empregada Doméstica	30	\N	2025-12-21 13:19:51.718464-03	\N	\N	\N	f	2025-12-21 13:19:51.779977-03	\N	0
22	Gabriel Guedes Germano	041.604.290-25	f	9108342181	(51) 99203-6302	Solteiro	Auxiliar de Cozinha	25	\N	2025-12-21 13:19:51.718464-03	\N	\N	\N	f	2025-12-21 13:19:51.779977-03	\N	0
37	Gerson Luiz Martins de Freitas Junior	023.339.560-11	f	2103395221	(51) 98152-8821	Solteiro	Coordenador de esporte	18	\N	2025-12-21 13:19:51.718464-03	\N	\N	\N	f	2025-12-21 13:19:51.779977-03	\N	0
20	Jailson Costa Feitoza	278.209.368-19	f	6136181945	(51) 98352-0897	Solteiro	Perito Avaliador de Imóveis	30	\N	2025-12-21 13:19:51.718464-03	\N	\N	\N	f	2025-12-21 13:19:51.779977-03	\N	0
59	Laida Drago Contreira	700.531.030-68	f		(51) 99447-3109	Solteiro(a)	Cozinheira	1	\N	2026-02-03 19:32:34.284219-03	\N	\N	\N	f	2026-02-03 19:32:34.284223-03	\N	0
13	Rosa Altagracia Rodrigues Olguin	602.324.300-20	f	23856643954	(51) 98031-2909	Solteiro	Manicure	1	\N	2025-12-21 13:19:51.718464-03	\N	\N	\N	f	2025-12-21 13:19:51.779977-03	\N	0
33	José Carlos Kichler	038.764.090-80	f		(51) 98317-4236	Solteiro	Garçom	5	\N	2025-12-21 13:19:51.718464-03	\N	\N	\N	f	2025-12-21 13:19:51.779977-03	\N	0
18	Bruno Oliveira Neumann	044.289.560-70	f	6126903902	(51) 99618-3759	Solteiro	Auxiliar de serviços gerais	1	\N	2025-12-21 13:19:51.718464-03	\N	\N	\N	f	2025-12-21 13:19:51.779977-03	\N	0
2	Gabriela Arce Ferreira	040.806.660-12	f	2123619765	(51) 98059-5199	Solteira	Recepcionista de Hotel	17	\N	2025-12-21 13:19:51.718464-03	\N	\N	\N	f	2025-12-21 13:19:51.779977-03	\N	0
16	Rose Elaine Costa Franco	469.799.130-34	f	8036927501	(55) 99646-3517	Solteiro	-	12	\N	2025-12-21 13:19:51.718464-03	\N	\N	\N	f	2025-12-21 13:19:51.779977-03	\N	0
55	Felipe Régis Freitas Vieira	105.134.967-26	f		(21) 99220-5341	Casado(a)	Autonomo	9	\N	2025-12-21 13:19:51.718464-03	\N	\N	\N	f	2025-12-21 13:19:51.779977-03	\N	0
27	Ederson Dornelles Meireles	803.096.319-68	f		(51) 99355-9604	Solteiro	Promotor de Vendas	5	\N	2025-12-21 13:19:51.718464-03	\N	\N	\N	f	2025-12-21 13:19:51.779977-03	\N	0
56	Rafael dos Santos Lima	600.229.850-93	f		(51) 99398-4501	Solteiro(a)	operador de caixa	1	\N	2026-01-20 17:49:48.063554-03	\N	\N	\N	f	2026-01-20 17:49:48.063558-03	\N	0
58	Luis Felipe dos Santos Prestes	026.390.590-09	f		(51) 99625-2081	Solteiro(a)	Barbeiro	1	\N	2026-01-20 20:41:24.305942-03	\N	\N	\N	f	2026-01-20 20:41:24.305947-03	\N	0
8	Juan Yammier Rangel	707.949.162-28	f		(51) 98652-5381	Solteiro	Atendente	7	\N	2025-12-21 13:19:51.718464-03	\N	\N	\N	f	2025-12-21 13:19:51.779977-03	\N	0
44	Jeferson Tome Soares	044.346.111-27	f		99310-2731	Solteiro	Promotor	7	\N	2025-12-21 13:19:51.718464-03	\N	\N	\N	f	2025-12-21 13:19:51.779977-03	\N	0
11	José Ailton Martins de Freitas	872.557.850-34	f	5065301672	(51) 99605-2741	Solteiro	Aposentado	7	\N	2025-12-21 13:19:51.718464-03	\N	\N	\N	f	2025-12-21 13:19:51.779977-03	\N	0
61	Evandro Gomes Monteiro	002.653.917-92	f		(54) 99900-5552	Casado(a)	Técnico Petroquimico	1	\N	2026-03-24 15:06:01.890733-03	\N	\N	\N	f	2026-03-24 15:06:01.890741-03	\N	0
62	Josseender Marramon Viera	019.978.560-00	f		(51) 98552-7853	Solteiro(a)	Encarregado de serviço patrimonial	5	\N	2026-03-24 16:24:39.46469-03	\N	\N	\N	f	2026-03-24 16:24:39.464694-03	\N	0
64	Danielle Souza dos Santos	031.529.082-02	f		(51) 99238-7712	Solteiro(a)	Barista	1	\N	2026-03-26 17:50:49.263734-03	\N	\N	\N	f	2026-03-26 17:50:49.263741-03	\N	0
63	Test	52998224725	f		11999990000	Solteiro(a)	Dev	10	\N	2026-03-26 13:44:22.39956-03	\N	2026-03-27 09:52:03.160214-03	\N	t	2026-03-26 13:44:22.399564-03	\N	0
65	Wesley da Silva Brasileiro	004.552.399-16	f		(51) 98115-4570	Solteiro(a)	Estofaria	7	\N	2026-03-27 10:23:50.670782-03	\N	\N	\N	f	2026-03-27 10:43:05.210651-03	\N	0
\.


--
-- Data for Name: core_tenant_furnitures; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY "public"."core_tenant_furnitures" ("id", "tenant_id", "furniture_id") FROM stdin;
1	1	7
2	2	6
3	37	11
5	47	7
6	47	1
\.


--
-- Data for Name: core_whatsappverification; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY "public"."core_whatsappverification" ("id", "cpf_cnpj", "code", "phone", "created_at", "expires_at", "attempts", "is_used") FROM stdin;
\.


--
-- Data for Name: django_admin_log; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY "public"."django_admin_log" ("id", "action_time", "object_id", "object_repr", "action_flag", "change_message", "content_type_id", "user_id") FROM stdin;
198	2025-06-04 20:18:45.484139-03	44	Gisele Dias Py	1	[{"added": {}}]	10	3
199	2025-06-04 20:20:10.449925-03	23	Locação do Apto 112 - 836	2	[{"changed": {"fields": ["Responsible tenant", "Tenants", "Start date", "Due day", "Rental value", "Contract generated", "Contract signed"]}}]	11	3
200	2025-06-04 20:21:08.524003-03	12	Locação do Apto 203 - 850	2	[{"changed": {"fields": ["Responsible tenant", "Tenants", "Number of tenants", "Start date", "Due day", "Rental value", "Tag fee", "Contract generated", "Contract signed", "Interfone configured"]}}]	11	3
201	2025-06-04 20:22:58.261888-03	1	Locação do Apto 113 - 836	2	[{"changed": {"fields": ["Responsible tenant", "Tenants", "Start date", "Validity months", "Due day", "Rental value", "Tag fee", "Contract generated", "Contract signed"]}}]	11	3
202	2025-06-04 20:26:59.627541-03	45	Fabio Luis Both	1	[{"added": {}}]	10	3
203	2025-06-04 20:28:30.491972-03	44	Locação do Apto 204 - 836	2	[{"changed": {"fields": ["Responsible tenant", "Tenants", "Start date", "Due day", "Contract generated"]}}]	11	3
204	2025-06-04 21:03:22.295276-03	44	Jeferson Tome Soares	2	[{"changed": {"fields": ["Name", "Cpf cnpj", "Rg", "Marital status", "Profession"]}}]	10	3
205	2025-06-04 22:11:47.757292-03	46	Kevyn Cristiano Maciel Silva	1	[{"added": {}}]	10	3
206	2025-06-04 22:13:35.406834-03	39	Locação do Apto 213 - 836	2	[{"changed": {"fields": ["Responsible tenant", "Tenants", "Start date", "Due day", "Rental value", "Contract generated", "Contract signed"]}}]	11	3
207	2025-09-21 16:24:37.943612-03	47	Norbetzi Del Carmen Martínez Flores	1	[{"added": {}}]	10	3
208	2025-09-21 16:25:38.535888-03	38	Locação do Apto 212 - 836	2	[{"changed": {"fields": ["Responsible tenant", "Tenants", "Number of tenants", "Start date", "Due day", "Rental value", "Contract generated", "Contract signed"]}}]	11	3
209	2025-09-21 16:28:34.240007-03	48	Franciele farias dos Santos	1	[{"added": {}}]	10	3
210	2025-09-21 16:32:20.944723-03	15	Locação do Apto 102 - 836	2	[{"changed": {"fields": ["Responsible tenant", "Tenants", "Start date", "Due day", "Rental value", "Contract generated", "Contract signed"]}}]	11	3
211	2025-09-21 16:32:40.865676-03	38	Locação do Apto 212 - 836	2	[{"changed": {"fields": ["Responsible tenant", "Tenants"]}}]	11	3
212	2025-09-21 16:34:11.309309-03	49	Gustavo Ferraz Ribeiro	1	[{"added": {}}]	10	3
213	2025-09-21 16:35:07.559225-03	39	Locação do Apto 213 - 836	2	[{"changed": {"fields": ["Responsible tenant", "Tenants", "Start date", "Due day", "Rental value", "Contract generated"]}}]	11	3
214	2025-09-21 21:58:19.261381-03	50	Alexandre Mendonça Tonaizer	1	[{"added": {}}]	10	3
215	2025-09-21 21:59:16.167166-03	23	Locação do Apto 112 - 836	2	[{"changed": {"fields": ["Tenants", "Number of tenants", "Start date", "Due day", "Rental value", "Tag fee", "Contract generated"]}}]	11	3
216	2025-09-21 21:59:43.34131-03	23	Locação do Apto 112 - 836	2	[{"changed": {"fields": ["Responsible tenant"]}}]	11	3
217	2025-09-21 22:00:35.648932-03	34	Locação do Apto 207 - 836	2	[{"changed": {"fields": ["Responsible tenant", "Tenants", "Number of tenants"]}}]	11	3
218	2025-09-22 14:48:57.211636-03	51	Marcos Vinicius Gomes Mafra	1	[{"added": {}}]	10	3
219	2025-09-22 14:50:24.456233-03	52	Makyson Vinicius Gomes Mafra	1	[{"added": {}}]	10	3
220	2025-09-22 14:51:12.820548-03	1	Locação do Apto 113 - 836	2	[{"changed": {"fields": ["Responsible tenant", "Tenants", "Number of tenants", "Start date", "Rental value", "Contract generated", "Interfone configured"]}}]	11	3
221	2025-09-22 14:51:43.37823-03	17	Locação do Apto 104 - 836	2	[{"changed": {"fields": ["Responsible tenant", "Tenants", "Number of tenants", "Rental value", "Contract generated", "Contract signed", "Interfone configured"]}}]	11	3
222	2025-09-22 14:53:33.591444-03	47	Norbetzi Del Carmen Martínez Flores	2	[{"changed": {"fields": ["Furnitures"]}}]	10	3
223	2025-09-22 14:53:52.822029-03	47	Norbetzi Del Carmen Martínez Flores	2	[{"changed": {"fields": ["Furnitures"]}}]	10	3
224	2025-09-22 14:54:04.767976-03	47	Norbetzi Del Carmen Martínez Flores	2	[{"changed": {"fields": ["Furnitures"]}}]	10	3
225	2025-09-22 14:54:07.585155-03	47	Norbetzi Del Carmen Martínez Flores	2	[]	10	3
226	2025-09-22 14:55:32.324718-03	39	Apto 212 - 836	2	[{"changed": {"fields": ["Furnitures"]}}]	9	3
227	2025-10-17 13:21:04.450437-03	52	Makyson Rodrigues Pereira	2	[{"changed": {"fields": ["Name"]}}]	10	3
228	2025-10-17 13:24:41.247568-03	17	Locação do Apto 104 - 836	2	[{"changed": {"fields": ["Start date", "Contract generated"]}}]	11	3
229	2025-10-17 13:25:28.314929-03	1	Locação do Apto 113 - 836	2	[{"changed": {"fields": ["Due day", "Rental value", "Contract generated"]}}]	11	3
230	2025-10-17 13:26:30.560946-03	17	Locação do Apto 104 - 836	2	[{"changed": {"fields": ["Due day"]}}]	11	3
231	2025-10-18 15:02:30.10169-03	15	Locação do Apto 102 - 836	2	[{"changed": {"fields": ["Start date"]}}]	11	3
232	2025-10-18 16:05:23.545055-03	38	Locação do Apto 212 - 836	2	[{"changed": {"fields": ["Start date"]}}]	11	3
233	2025-11-10 18:01:10.229679-03	23	Locação do Apto 112 - 836	2	[{"changed": {"fields": ["Responsible tenant", "Tenants", "Number of tenants", "Start date", "Due day", "Rental value", "Tag fee", "Contract generated", "Interfone configured"]}}]	11	3
234	2025-11-10 18:44:05.88875-03	31	Locação do Apto 203 - 836	2	[{"changed": {"fields": ["Responsible tenant", "Tenants", "Start date", "Due day", "Rental value", "Tag fee", "Contract generated", "Contract signed", "Interfone configured"]}}]	11	3
235	2025-11-10 19:17:34.690029-03	32	Apto 203 - 836	2	[{"changed": {"fields": ["Interfone configured", "Contract generated", "Contract signed"]}}]	9	3
236	2025-11-10 19:26:47.624185-03	31	Locação do Apto 203 - 836	2	[{"changed": {"fields": ["Number of tenants"]}}]	11	3
237	2025-11-20 13:20:24.586886-03	37	Locação do Apto 211 - 836	2	[{"changed": {"fields": ["Rental value"]}}]	11	3
238	2025-11-20 13:21:14.846739-03	38	Apto 211 - 836	2	[{"changed": {"fields": ["Rental value"]}}]	9	3
239	2025-11-20 13:21:58.837103-03	18	Locação do Apto 105 - 836	2	[{"changed": {"fields": ["Rental value"]}}]	11	3
240	2025-11-20 13:22:15.500723-03	19	Apto 105 - 836	2	[{"changed": {"fields": ["Rental value"]}}]	9	3
241	2025-11-20 13:22:41.762178-03	30	Apto 201 - 836	2	[{"changed": {"fields": ["Rental value"]}}]	9	3
242	2025-11-20 13:22:50.857912-03	29	Locação do Apto 201 - 836	2	[{"changed": {"fields": ["Rental value"]}}]	11	3
243	2025-11-20 13:23:25.676968-03	22	Locação do Apto 111 - 836	2	[{"changed": {"fields": ["Rental value"]}}]	11	3
244	2025-11-20 13:23:45.136692-03	23	Apto 111 - 836	2	[{"changed": {"fields": ["Rental value", "Last rent increase date"]}}]	9	3
245	2025-11-20 13:24:22.653004-03	18	Apto 104 - 836	2	[{"changed": {"fields": ["Rental value"]}}]	9	3
246	2025-11-20 13:25:40.315801-03	42	Apto 108 - 836	2	[{"changed": {"fields": ["Rental value"]}}]	9	3
247	2025-11-20 13:25:56.166112-03	40	Locação do Apto 108 - 836	2	[{"changed": {"fields": ["Rental value"]}}]	11	3
248	2025-11-20 13:26:02.52486-03	42	Apto 108 - 836	2	[{"changed": {"fields": ["Last rent increase date"]}}]	9	3
249	2025-11-20 13:26:15.082586-03	19	Apto 105 - 836	2	[{"changed": {"fields": ["Rental value", "Last rent increase date"]}}]	9	3
250	2025-11-20 13:26:27.859698-03	23	Apto 111 - 836	2	[]	9	3
251	2025-11-20 13:26:35.006388-03	24	Apto 112 - 836	2	[{"changed": {"fields": ["Last rent increase date"]}}]	9	3
252	2025-11-20 13:26:41.255208-03	30	Apto 201 - 836	2	[{"changed": {"fields": ["Last rent increase date"]}}]	9	3
253	2025-11-20 13:26:52.197353-03	32	Apto 203 - 836	2	[{"changed": {"fields": ["Rental value", "Last rent increase date"]}}]	9	3
254	2025-11-20 13:26:58.333866-03	38	Apto 211 - 836	2	[{"changed": {"fields": ["Last rent increase date"]}}]	9	3
255	2025-11-20 13:27:49.30389-03	5	Apto 204 - 850	2	[{"changed": {"fields": ["Rental value", "Last rent increase date"]}}]	9	3
256	2025-11-20 13:28:03.199829-03	5	Apto 204 - 850	2	[{"changed": {"fields": ["Rental value"]}}]	9	3
257	2025-11-20 13:32:37.62182-03	36	Apto 209 - 836	2	[{"changed": {"fields": ["Rental value"]}}]	9	3
258	2025-11-20 13:34:02.268952-03	12	Apto 203 - 850	2	[{"changed": {"fields": ["Rental value"]}}]	9	3
259	2025-11-20 13:44:07.182906-03	16	Apto 102 - 836	2	[{"changed": {"fields": ["Rental value"]}}]	9	3
260	2025-11-20 13:44:13.271144-03	16	Apto 102 - 836	2	[{"changed": {"fields": ["Rental value"]}}]	9	3
261	2025-12-20 23:41:05.304346-03	17	Locação do Apto 104 - 836	2	[{"changed": {"fields": ["Responsible tenant", "Tenants", "Start date", "Due day", "Rental value", "Contract generated"]}}]	11	3
262	2025-12-20 23:57:39.010722-03	53	Érica Mendes Siqueira	1	[{"added": {}}]	10	3
263	2025-12-20 23:58:43.838989-03	5	Locação do Apto 204 - 850	2	[{"changed": {"fields": ["Responsible tenant", "Tenants", "Number of tenants", "Start date", "Due day", "Rental value", "Tag fee", "Contract generated", "Contract signed", "Interfone configured"]}}]	11	3
264	2025-12-21 00:02:54.421193-03	54	Isadora Fontanella Rodrigues	1	[{"added": {}}]	10	3
265	2025-12-21 00:04:05.388897-03	15	Locação do Apto 102 - 836	2	[{"changed": {"fields": ["Responsible tenant", "Tenants", "Number of tenants", "Start date", "Due day", "Tag fee", "Contract generated", "Interfone configured"]}}]	11	3
266	2025-12-21 00:08:09.923927-03	55	Felipe Régis Freitas Vieira	1	[{"added": {}}]	10	3
267	2025-12-21 00:09:04.031209-03	37	Locação do Apto 211 - 836	2	[{"changed": {"fields": ["Responsible tenant", "Tenants", "Start date", "Validity months", "Due day", "Rental value", "Contract generated", "Contract signed", "Interfone configured"]}}]	11	3
268	2025-12-21 11:45:49.914746-03	50	Alexandre Mendonça Tonaizer	2	[{"changed": {"fields": ["Marital status", "Deposit amount"]}}]	10	3
269	2025-12-21 12:22:33.813068-03	17	Locação do Apto 104 - 836	2	[{"changed": {"fields": ["Number of tenants", "Contract generated"]}}]	11	3
270	2025-12-21 12:24:07.652059-03	47	Norbetzi Del Carmen Martínez Flores	2	[{"changed": {"fields": ["Phone", "Marital status", "Rent due day"]}}]	10	3
271	2025-12-21 12:27:02.147772-03	48	Franciele farias dos Santos	2	[{"changed": {"fields": ["Phone", "Marital status", "Cleaning fee paid", "Tag deposit paid"]}}]	10	3
272	2025-12-21 12:27:16.516938-03	47	Norbetzi Del Carmen Martínez Flores	2	[{"changed": {"fields": ["Cleaning fee paid", "Tag deposit paid"]}}]	10	3
273	2025-12-21 12:34:15.682837-03	47	Norbetzi Del Carmen Martínez Flores	2	[{"changed": {"fields": ["Tag deposit paid"]}}]	10	3
274	2025-12-21 12:46:26.789392-03	38	Locação do Apto 212 - 836	2	[{"changed": {"fields": ["Tag fee", "Contract generated", "Interfone configured"]}}]	11	3
\.


--
-- Data for Name: django_content_type; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY "public"."django_content_type" ("id", "app_label", "model") FROM stdin;
1	admin	logentry
2	auth	permission
3	auth	group
4	auth	user
5	contenttypes	contenttype
6	sessions	session
7	core	building
8	core	furniture
9	core	apartment
10	core	tenant
11	core	lease
12	core	dependent
13	sites	site
14	token_blacklist	blacklistedtoken
15	token_blacklist	outstandingtoken
16	account	emailaddress
17	account	emailconfirmation
18	socialaccount	socialaccount
19	socialaccount	socialapp
20	socialaccount	socialtoken
21	core	landlord
22	core	contractrule
23	core	creditcard
24	core	expensecategory
25	core	financialsettings
26	core	person
27	core	income
28	core	expense
29	core	employeepayment
30	core	personincome
31	core	rentpayment
32	core	expenseinstallment
33	core	personpayment
34	core	rentadjustment
35	core	ipcaindex
36	core	personpaymentschedule
37	core	expensemonthskip
38	core	monthsnapshot
39	core	devicetoken
40	core	whatsappverification
41	core	notification
42	core	paymentproof
43	core	oauthexchangecode
\.


--
-- Data for Name: django_migrations; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY "public"."django_migrations" ("id", "app", "name", "applied") FROM stdin;
1	contenttypes	0001_initial	2025-04-14 18:18:10.398874-03
2	auth	0001_initial	2025-04-14 18:18:10.434711-03
3	admin	0001_initial	2025-04-14 18:18:10.445855-03
4	admin	0002_logentry_remove_auto_add	2025-04-14 18:18:10.450144-03
5	admin	0003_logentry_add_action_flag_choices	2025-04-14 18:18:10.454011-03
6	contenttypes	0002_remove_content_type_name	2025-04-14 18:18:10.462411-03
7	auth	0002_alter_permission_name_max_length	2025-04-14 18:18:10.467045-03
8	auth	0003_alter_user_email_max_length	2025-04-14 18:18:10.470942-03
9	auth	0004_alter_user_username_opts	2025-04-14 18:18:10.474832-03
10	auth	0005_alter_user_last_login_null	2025-04-14 18:18:10.479131-03
11	auth	0006_require_contenttypes_0002	2025-04-14 18:18:10.479832-03
12	auth	0007_alter_validators_add_error_messages	2025-04-14 18:18:10.486017-03
13	auth	0008_alter_user_username_max_length	2025-04-14 18:18:10.493199-03
14	auth	0009_alter_user_last_name_max_length	2025-04-14 18:18:10.49776-03
15	auth	0010_alter_group_name_max_length	2025-04-14 18:18:10.502639-03
16	auth	0011_update_proxy_permissions	2025-04-14 18:18:10.506539-03
17	auth	0012_alter_user_first_name_max_length	2025-04-14 18:18:10.510655-03
18	core	0001_initial	2025-04-14 18:18:10.563372-03
19	sessions	0001_initial	2025-04-14 18:18:10.568346-03
20	core	0002_lease_number_of_tenants	2025-04-14 18:45:33.817305-03
21	core	refactor_database	2025-10-19 16:33:34.295576-03
22	core	0001_add_validators_and_indexes	2025-10-19 16:33:34.295576-03
23	account	0001_initial	2025-10-19 16:52:08.957419-03
24	account	0002_email_max_length	2025-10-19 16:52:08.97417-03
25	account	0003_alter_emailaddress_create_unique_verified_email	2025-10-19 16:52:08.987894-03
26	account	0004_alter_emailaddress_drop_unique_email	2025-10-19 16:52:09.0174-03
27	account	0005_emailaddress_idx_upper_email	2025-10-19 16:52:09.037441-03
28	sites	0001_initial	2025-10-19 16:52:09.04147-03
29	sites	0002_alter_domain_unique	2025-10-19 16:52:09.051833-03
30	socialaccount	0001_initial	2025-10-19 16:52:09.160725-03
31	socialaccount	0002_token_max_lengths	2025-10-19 16:52:09.181519-03
32	socialaccount	0003_extra_data_default_dict	2025-10-19 16:52:09.188046-03
33	socialaccount	0004_app_provider_id_settings	2025-10-19 16:52:09.208624-03
34	socialaccount	0005_socialtoken_nullable_app	2025-10-19 16:52:09.230271-03
35	socialaccount	0006_alter_socialaccount_extra_data	2025-10-19 16:52:09.248279-03
36	token_blacklist	0001_initial	2025-10-19 16:52:09.305529-03
37	token_blacklist	0002_outstandingtoken_jti_hex	2025-10-19 16:52:09.317568-03
38	token_blacklist	0003_auto_20171017_2007	2025-10-19 16:52:09.338085-03
39	token_blacklist	0004_auto_20171017_2013	2025-10-19 16:52:09.352788-03
40	token_blacklist	0005_remove_outstandingtoken_jti	2025-10-19 16:52:09.363379-03
41	token_blacklist	0006_auto_20171017_2113	2025-10-19 16:52:09.366889-03
42	token_blacklist	0007_auto_20171017_2214	2025-10-19 16:52:09.397385-03
43	token_blacklist	0008_migrate_to_bigautofield	2025-10-19 16:52:09.454623-03
44	token_blacklist	0010_fix_migrate_to_bigautofield	2025-10-19 16:52:09.476494-03
45	token_blacklist	0011_linearizes_history	2025-10-19 16:52:09.476494-03
46	token_blacklist	0012_alter_outstandingtoken_user	2025-10-19 16:52:09.490105-03
47	core	0002_add_composite_indexes	2025-10-19 20:31:26.676645-03
48	core	0003_add_tenant_user_fk	2025-12-21 13:08:09.346697-03
49	core	0004_tenant_user	2025-12-21 13:08:09.376082-03
50	core	0005_add_audit_softdelete_mixins	2025-12-21 13:19:51.841977-03
51	core	0003_refactor_database	2025-12-22 00:08:40.589227-03
52	core	0004_add_validators_and_indexes	2025-12-22 00:08:40.864505-03
53	core	0005_add_composite_indexes	2025-12-22 18:12:57.206149-03
54	core	0006_add_tenant_user_fk	2025-12-22 18:12:57.21432-03
55	core	0007_tenant_user	2025-12-22 18:12:57.21432-03
56	core	0008_add_audit_softdelete_mixins	2025-12-22 18:12:57.21432-03
57	account	0006_emailaddress_lower	2026-01-19 14:54:07.438497-03
58	account	0007_emailaddress_idx_email	2026-01-19 14:54:07.458656-03
59	account	0008_emailaddress_unique_primary_email_fixup	2026-01-19 14:54:07.479959-03
60	account	0009_emailaddress_unique_primary_email	2026-01-19 14:54:07.490931-03
61	core	0009_alter_dependent_phone_alter_tenant_phone	2026-01-19 14:54:07.508789-03
62	core	0010_add_landlord_model	2026-01-19 16:47:52.377044-03
63	core	0011_contractrule	2026-01-20 15:05:31.91562-03
64	core	0012_add_financial_module	2026-03-21 23:44:32.519549-03
65	core	0013_add_expense_category_parent	2026-03-22 22:45:25.940805-03
66	core	0014_add_expense_is_offset	2026-03-22 22:45:25.965118-03
67	core	0015_add_person_payment	2026-03-22 22:45:26.008805-03
68	core	0016_add_expense_end_date	2026-03-22 22:45:26.026828-03
69	token_blacklist	0013_alter_blacklistedtoken_options_and_more	2026-03-22 22:45:26.048485-03
70	core	0012_add_new_fields	2026-03-23 21:40:24.944031-03
71	core	0017_add_new_fields	2026-03-23 21:44:30.779265-03
72	core	0018_migrate_data_and_rename	2026-03-23 21:47:39.498701-03
73	core	0019_remove_old_fields	2026-03-23 21:54:53.435395-03
74	core	0020_lease_apartment_fk	2026-03-24 11:42:02.421153-03
75	core	0021_person_initial_balance	2026-03-24 19:06:44.174784-03
76	core	0022_occupancy_pricing	2026-03-26 13:30:02.083032-03
77	core	0023_rentadjustment	2026-03-26 19:39:28.224769-03
78	core	0024_lease_last_rent_increase_date	2026-03-27 12:06:37.943162-03
79	core	0025_populate_lease_last_rent_increase_date	2026-03-27 12:06:54.492878-03
80	core	0026_financial_settings_rent_adjustment_percentage	2026-03-27 12:26:15.879128-03
81	core	0027_remove_financialsettings_rent_adjustment_percentage_and_more	2026-03-27 12:29:17.275259-03
82	core	0028_ipca_index	2026-03-27 13:33:57.483619-03
83	core	0029_lease_pending_rental_value	2026-03-27 14:32:34.050326-03
84	core	0030_person_payment_schedule	2026-03-28 14:58:41.763831-03
85	core	0031_month_snapshot	2026-03-28 18:24:08.764691-03
86	core	0032_mobile_models	2026-03-29 23:28:22.682002-03
87	core	0033_mobile_models	2026-03-29 23:29:07.401478-03
88	core	0034_alter_paymentproof_managers	2026-03-29 23:33:51.077827-03
89	core	0035_data_integrity_protect_cascade_constraints	2026-04-06 18:07:56.45924-03
90	core	0036_add_missing_indexes	2026-04-06 18:07:56.611209-03
91	core	0037_soft_delete_unique_constraints	2026-04-06 18:07:56.989097-03
92	core	0038_add_check_constraints	2026-06-01 13:38:51.123479-03
93	core	0039_person_payment_schedule_protect	2026-06-01 13:38:51.16564-03
94	core	0040_fix_expense_check_constraint	2026-06-01 13:38:51.229272-03
95	core	0041_add_oauth_exchange_code	2026-06-01 13:38:51.330408-03
96	core	0042_add_expense_indexes	2026-06-01 13:38:51.439185-03
\.


--
-- Data for Name: django_session; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY "public"."django_session" ("session_key", "session_data", "expire_date") FROM stdin;
19q6x4b12fvl3mkr60fbhjoaie8jgijn	.eJxVjEEOwiAQRe_C2hCgA4JL9z0DGZhBqoYmpV0Z765NutDtf-_9l4i4rTVunZc4kbgILU6_W8L84LYDumO7zTLPbV2mJHdFHrTLcSZ-Xg_376Bir986GDDW-sJgPZIJmZJx5BRQsKWoAUIY2KAvREzq7MlrrR1oBvIlA4j3B9hCN7s:1u4UWz:-qIqDDLVifY3vUHj4MO9-pGfE845w32r6L_fWm9ZbV8	2025-04-28 21:52:05.831095-03
tgy6ttyr8pe0tq7v1hbmxzadge7qq35x	.eJxVjEEOwiAQRe_C2hCgMxRcuvcMhM4MtmpoUtqV8e7apAvd_vfef6mUt3VMW5MlTazOyqnT7zZkekjdAd9zvc2a5rou06B3RR-06evM8rwc7t_BmNv4rQUKsxCC6Qic8YAw2BAKdV6KKb30YiVaX3KkEJgJPErvgNBGwIDq_QH2cTfw:1uAuvj:6N0B0OcPWOM5H30UAGMVgepm66O5riXeWE6rLiYMYBM	2025-05-16 15:16:11.011842-03
2q8acr8uj9zkscm3lbmulo102yoa06fh	.eJxVjEEOwiAQAP_C2ZAVEMGjd99AdtmtVA0kpT0Z_25IetDrzGTeKuG2lrR1WdLM6qKsOvwywvyUOgQ_sN6bzq2uy0x6JHq3Xd8ay-u6t3-Dgr2MLfgj8RRPiOggGgCCyZqzC5C98YGzRPLOGhcoZgEmMALBe0dClp36fAHPvTeM:1uI6DZ:c4mpxLeCu3MXC121M5P6DdeLT49pmSvGS0Mv8pO-iyI	2025-06-05 10:44:17.838359-03
xnobf55ya3614i7ha28z3crw2tp5bcvk	.eJxVjEEOwiAQAP_C2ZAVEMGjd99AdtmtVA0kpT0Z_25IetDrzGTeKuG2lrR1WdLM6qKsOvwywvyUOgQ_sN6bzq2uy0x6JHq3Xd8ay-u6t3-Dgr2MLfgj8RRPiOggGgCCyZqzC5C98YGzRPLOGhcoZgEmMALBe0dClp36fAHPvTeM:1uQYfJ:dmcAhNM5cFQwcHNU3YN3m7-SHO2WwQbGRWoE-aRYo8k	2025-06-28 18:43:53.390619-03
2209plqfm8cku7geyeiktl00cx8rufu7	.eJxVjEEOwiAQAP_C2ZAVEMGjd99AdtmtVA0kpT0Z_25IetDrzGTeKuG2lrR1WdLM6qKsOvwywvyUOgQ_sN6bzq2uy0x6JHq3Xd8ay-u6t3-Dgr2MLfgj8RRPiOggGgCCyZqzC5C98YGzRPLOGhcoZgEmMALBe0dClp36fAHPvTeM:1uXfYs:d4PFm3QC8nB262rYhVUa7SEQn4k5Fmxbyo5Fm0l1QNQ	2025-07-18 09:30:38.209383-03
zsswtyfk62fzbtoes3h614lfrh4ywvt8	.eJxVjEEOwiAQAP_C2ZAVEMGjd99AdtmtVA0kpT0Z_25IetDrzGTeKuG2lrR1WdLM6qKsOvwywvyUOgQ_sN6bzq2uy0x6JHq3Xd8ay-u6t3-Dgr2MLfgj8RRPiOggGgCCyZqzC5C98YGzRPLOGhcoZgEmMALBe0dClp36fAHPvTeM:1uZH93:L9JR0TsC7yFhnSliHgg8EYgdiTvIl9eRI55_kB_LMSg	2025-07-22 19:50:37.162482-03
xgbe5n6la8ppwnq4yvxc8r4gs35onrak	.eJxVjMsOwiAQRf-FtSG8KS7d-w1kGAapGkhKuzL-uzbpQrf3nHNfLMK21rgNWuKc2ZlpdvrdEuCD2g7yHdqtc-xtXebEd4UfdPBrz_S8HO7fQYVRvzWpQB7thCClLo4SOCjeZKNQ6JInoQwqIw0FsIUEOiyeQnHKS0BUlr0__iQ4kA:1utogY:Z8bIKJ-jkgr6MxortSjS6OgMp_TAbIi2EyQxVmftwD8	2025-09-17 11:42:06.828219-03
no8g5d4zrz327pll7orljd8xmpgoiok2	.eJxVjMsOwiAQRf-FtSG8KS7d-w1kGAapGkhKuzL-uzbpQrf3nHNfLMK21rgNWuKc2ZlpdvrdEuCD2g7yHdqtc-xtXebEd4UfdPBrz_S8HO7fQYVRvzWpQB7thCClLo4SOCjeZKNQ6JInoQwqIw0FsIUEOiyeQnHKS0BUlr0__iQ4kA:1v0PcJ:Al3WJbx6fxxyWxRfFUvvjL0jFL7tWqrVxZ87PQwm_K4	2025-10-05 16:20:59.429025-03
ceca86iwg8ipudmy2yaymfp1wcbotl4e	.eJxVjMsOwiAQRf-FtSG8KS7d-w1kGAapGkhKuzL-uzbpQrf3nHNfLMK21rgNWuKc2ZlpdvrdEuCD2g7yHdqtc-xtXebEd4UfdPBrz_S8HO7fQYVRvzWpQB7thCClLo4SOCjeZKNQ6JInoQwqIw0FsIUEOiyeQnHKS0BUlr0__iQ4kA:1v6FzF:uf1wj-HJnOSvFTo2wb9hJG7JNS3l4WBsei4J1dZOLUU	2025-10-21 19:16:49.541498-03
dy9knv53mdanhpoija5nsnybmdhse9vj	.eJxVjEEOwiAQRe_C2hBaBiku3fcMZJgZpGpoUtqV8e7apAvd_vfef6mI21ri1mSJE6uLsur0uyWkh9Qd8B3rbdY013WZkt4VfdCmx5nleT3cv4OCrXzrEDiggGMHxGdMAwkQIWVPLnjI4gebDEJgy5CcN75nTyZ3lHIntlfvDxXEOP8:1vIYmW:jL0LthUBdE7ixzbeaVHclSHxjf5o2CceUEKtWZp0DmE	2025-11-24 17:46:32.943822-03
offzj8ahcw2bnqmhvqvroow1yyxeclwp	.eJxVjEEOwiAQRe_C2hBaBiku3fcMZJgZpGpoUtqV8e7apAvd_vfef6mI21ri1mSJE6uLsur0uyWkh9Qd8B3rbdY013WZkt4VfdCmx5nleT3cv4OCrXzrEDiggGMHxGdMAwkQIWVPLnjI4gebDEJgy5CcN75nTyZ3lHIntlfvDxXEOP8:1vIa12:LeDHch0dcl-aDb90cbuiss4NzY7s7G8wkpZTH45DJhE	2025-11-24 19:05:36.099598-03
ntz2j1c1mbtkxh53pezkzat2ol30snfp	.eJxVjEEOwiAQRe_C2hBaBiku3fcMZJgZpGpoUtqV8e7apAvd_vfef6mI21ri1mSJE6uLsur0uyWkh9Qd8B3rbdY013WZkt4VfdCmx5nleT3cv4OCrXzrEDiggGMHxGdMAwkQIWVPLnjI4gebDEJgy5CcN75nTyZ3lHIntlfvDxXEOP8:1vQ5pl:J-wwF1gYmFtafYQIjV2NRZtu2eh20pVmbqJvmVZ7pxQ	2025-12-15 12:29:01.913584-03
xk5dyptimfwdwpi0qwmaouad4uen8ta9	.eJxVjEEOwiAQRe_C2hBaBiku3fcMZJgZpGpoUtqV8e7apAvd_vfef6mI21ri1mSJE6uLsur0uyWkh9Qd8B3rbdY013WZkt4VfdCmx5nleT3cv4OCrXzrEDiggGMHxGdMAwkQIWVPLnjI4gebDEJgy5CcN75nTyZ3lHIntlfvDxXEOP8:1vX9LA:Mv3flogYWhVofLHC2rUqnk7-Glo1aR9UYqzQqCpdgpY	2026-01-03 23:38:36.351762-03
9nsxgievw023ahhq22s4ovw67mhthqop	.eJxVjEEOwiAQRe_C2hBaBiku3fcMZJgZpGpoUtqV8e7apAvd_vfef6mI21ri1mSJE6uLsur0uyWkh9Qd8B3rbdY013WZkt4VfdCmx5nleT3cv4OCrXzrEDiggGMHxGdMAwkQIWVPLnjI4gebDEJgy5CcN75nTyZ3lHIntlfvDxXEOP8:1vdCWE:l8EGRKvCI7FzZB4LkpvEbewJpF04LOX7aT9hoHXJ2vM	2026-01-20 16:15:02.414039-03
xfca1hvkuqkawxblhadunteft5ila1o5	.eJxVjEEOwiAQRe_C2hBoYQZcuu8ZyMBMbdW0SWlXxrsbki50-997_60SHfuUjipbmlldVa8uv1um8pSlAX7Qcl91WZd9m7Nuij5p1cPK8rqd7t_BRHVqdRQXuY8FwI6MSGIxup6tycFxNi6gJ295tF0Bg8EDeXGE0hUAA0F9vtzmN1c:1vhtSE:e3HypKzQh_i_VRCua_iOtXV-hMqQM275OjoIAARkszg	2026-02-02 14:54:18.988911-03
8a6seqjspm0nm51hlnyd3tj9zirawji4	.eJxVjMsKwjAQAP9lzxLyKHn06N1vCJvNxlQlgaY9if8uhR70OjPMGyLuW4374DUuGWYwcPllCenJ7RD5ge3eBfW2rUsSRyJOO8StZ35dz_ZvUHFUmIGyJGWMI3becQpGFlUILeU0BVWKDSbbpB2i15OXgZLDohWzVwU1Gvh8AQO3OMA:1vzcFr:PZCZ4aROzWr16y_K-teCM3fq_LlZaUB5A175Yven4qU	2026-03-23 12:10:47.631465-03
pp1ly4aioi101582jbps36cf0r147n0i	.eJxVjMsKwjAQAP9lzxLyKHn06N1vCJvNxlQlgaY9if8uhR70OjPMGyLuW4374DUuGWYwcPllCenJ7RD5ge3eBfW2rUsSRyJOO8StZ35dz_ZvUHFUmIGyJGWMI3becQpGFlUILeU0BVWKDSbbpB2i15OXgZLDohWzVwU1Gvh8AQO3OMA:1w9RnP:zAyMnJtvAOiXJDZgeujdsl8XOXSibFcxngzEGqz5xgs	2026-04-19 15:02:03.05701-03
\.


--
-- Data for Name: django_site; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY "public"."django_site" ("id", "domain", "name") FROM stdin;
1	localhost:8000	Condominios Manager
\.


--
-- Data for Name: socialaccount_socialaccount; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY "public"."socialaccount_socialaccount" ("id", "provider", "uid", "last_login", "date_joined", "extra_data", "user_id") FROM stdin;
\.


--
-- Data for Name: socialaccount_socialapp; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY "public"."socialaccount_socialapp" ("id", "provider", "name", "client_id", "secret", "key", "provider_id", "settings") FROM stdin;
\.


--
-- Data for Name: socialaccount_socialapp_sites; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY "public"."socialaccount_socialapp_sites" ("id", "socialapp_id", "site_id") FROM stdin;
\.


--
-- Data for Name: socialaccount_socialtoken; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY "public"."socialaccount_socialtoken" ("id", "token", "token_secret", "expires_at", "account_id", "app_id") FROM stdin;
\.


--
-- Data for Name: token_blacklist_blacklistedtoken; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY "public"."token_blacklist_blacklistedtoken" ("id", "blacklisted_at", "token_id") FROM stdin;
1	2026-01-19 16:58:32.524394-03	6
2	2026-01-19 19:26:39.790458-03	7
3	2026-01-20 11:11:29.979213-03	8
4	2026-01-20 14:36:25.34231-03	9
\.


--
-- Data for Name: token_blacklist_outstandingtoken; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY "public"."token_blacklist_outstandingtoken" ("id", "token", "created_at", "expires_at", "user_id", "jti") FROM stdin;
1	eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc2Mjg5ODc2MSwiaWF0IjoxNzYyODEyMzYxLCJqdGkiOiJiZjZhMDA1ZjcwMWQ0NDgyOTMwNjRkY2VmZDljMWNiNCIsInVzZXJfaWQiOjN9.B1U_qZxwKMjcE6KvS4bDF0-EK0anVdTHCTKF9Tv_mHk	2025-11-10 19:06:01.065068-03	2025-11-11 19:06:01-03	3	bf6a005f701d448293064dcefd9c1cb4
2	eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc2NjM3MTMwMSwiaWF0IjoxNzY2Mjg0OTAxLCJqdGkiOiJhZTkzMTZjNjUwMWQ0NjViODg1Zjc5ZmJjNjA4NmFlZSIsInVzZXJfaWQiOjN9.l9ZuoOvINTvgl3HcOiBV7EBsCmJr_gADdNz0HLjyY9s	2025-12-20 23:41:41.068533-03	2025-12-21 23:41:41-03	3	ae9316c6501d465b885f79fbc6086aee
3	eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc2NjQxNDkyNywiaWF0IjoxNzY2MzI4NTI3LCJqdGkiOiIxMTI4YzMyOTBmNGY0YmM4OWE5YTZkYzcwMDA0YTdmMiIsInVzZXJfaWQiOjN9.sBhxZQFrKdw3kkBpKIMn4ekmE69JOTHBlWpuypJSkzE	2025-12-21 11:48:47.253766-03	2025-12-22 11:48:47-03	3	1128c3290f4f4bc89a9a6dc70004a7f2
4	eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc2NjQxODY1MSwiaWF0IjoxNzY2MzMyMjUxLCJqdGkiOiIwODExNmRiMDc0MWE0ZTVkYmU4NjZkOTVlMzRiYTI4MSIsInVzZXJfaWQiOjN9.TC1v7reROkEi5Iqc7MQQ-MuCTsRC4_QZ-ws82AflLms	2025-12-21 12:50:51.184017-03	2025-12-22 12:50:51-03	3	08116db0741a4e5dbe866d95e34ba281
5	eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc2NjU4Nzg2NiwiaWF0IjoxNzY2NTAxNDY2LCJqdGkiOiI4MTI5MjhhZTYwNmM0NDM0YTk2MTZhMmYxNGM4YjkwMyIsInVzZXJfaWQiOjV9.wTPL_vw60VuRtl_fcwA-Bu8Fpmv5_LrTWJ_VX6UNwnE	2025-12-23 11:51:06.971657-03	2025-12-24 11:51:06-03	5	812928ae606c4434a9616a2f14c8b903
6	eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc2ODkzMjExMiwiaWF0IjoxNzY4ODQ1NzEyLCJqdGkiOiJhZWExMmVhNjUwOTY0ZWJhYmU0N2ExZjk3ZGYzYTYzZSIsInVzZXJfaWQiOjN9.WzT4-2_vIoWNn5L4ld_OPWIRjNj5W5tgrqt50Xj8-UM	2026-01-19 15:01:52.334407-03	2026-01-20 15:01:52-03	3	aea12ea650964ebabe47a1f97df3a63e
7	eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc2ODkzOTIzMywiaWF0IjoxNzY4ODUyODMzLCJqdGkiOiIyNjY2MjFiYjEyYmE0N2VmYWQzZmFmNDM4ZWFkNjY4ZCIsInVzZXJfaWQiOjN9.wml89AS-i7x5OmzspWk9vMAA4EsLK2amgnoIXOHAhQg	2026-01-19 17:00:33.65652-03	2026-01-20 17:00:33-03	3	266621bb12ba47efad3faf438ead668d
8	eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc2ODk0ODA4NywiaWF0IjoxNzY4ODYxNjg3LCJqdGkiOiJmYzkzNTVmODgwZWU0MDQ1YThkMjVkZjVhODhmNDYxNCIsInVzZXJfaWQiOjN9.mzfAeJTbjOEjxhJDkb0pPP3O_wr9lc0jStkZCYQT620	2026-01-19 19:28:07.663215-03	2026-01-20 19:28:07-03	3	fc9355f880ee4045a8d25df5a88f4614
9	eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc2OTAxMTg3OCwiaWF0IjoxNzY4OTI1NDc4LCJqdGkiOiI3ZGQ3NjRkNDc0MmE0MGRmYTU4OWZmMTIxOGVmYTBiMiIsInVzZXJfaWQiOjN9.vfvppsxFUBpX072sbLAzAxfnrju5uzc5Qxa7I5Wb20Q	2026-01-20 13:11:18.592288-03	2026-01-21 13:11:18-03	3	7dd764d4742a40dfa589ff1218efa0b2
10	eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTgwMDQ2ODYxMSwiaWF0IjoxNzY4OTMyNjExLCJqdGkiOiI0ZTczN2NjZWE3ZjQ0MmM4YWE2N2FmZTI3ZDkzMWRjNCIsInVzZXJfaWQiOjN9.hDx9XS09qCfnXPMHAf0Q1Orftk2NwYNQb4bUcNMNJoE	2026-01-20 15:10:11.694008-03	2027-01-20 15:10:11-03	3	4e737ccea7f442c8aa67afe27d931dc4
11	eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTgwMTY5Mzg2MCwiaWF0IjoxNzcwMTU3ODYwLCJqdGkiOiIwYTNmOWY0ODY1N2Y0MTEzYTgyZDRlNmFlNTkzYjRkNCIsInVzZXJfaWQiOjN9.zwglWOf4aRV2g6g7BGtQl4421PZHjr7JNfesjJR6VCg	2026-02-03 19:31:00.517342-03	2027-02-03 19:31:00-03	3	0a3f9f48657f4113a82d4e6ae593b4d4
12	eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTgwNTc2NjgwOCwiaWF0IjoxNzc0MjMwODA4LCJqdGkiOiIxODhkZTM3ZGIxMDk0ZjIwYTkyYjRlOGU3Yzc5Y2QxZCIsInVzZXJfaWQiOiIzIn0.UrcS8RMTkNMD1kOFJXY3W3UYISO0gHs58_H5CdxuBV0	2026-03-22 22:53:28.951604-03	2027-03-22 22:53:28-03	3	188de37db1094f20a92b4e8e7c79cd1d
13	eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTgwNTgxODIxOCwiaWF0IjoxNzc0MjgyMjE4LCJqdGkiOiI4NzVhMzRhZGQwZGY0MjJlYjgzYmQwNmEzZjllM2RhMyIsInVzZXJfaWQiOiIzIn0.SVBIqSZe7G_AJBsePNGK_NQ0r0tU-n3gE4Vnc92BztA	2026-03-23 13:10:18.833817-03	2027-03-23 13:10:18-03	3	875a34add0df422eb83bd06a3f9e3da3
14	eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTgwNTgyOTIyNywiaWF0IjoxNzc0MjkzMjI3LCJqdGkiOiI5MjI0MmU1ODg5NTE0MDY1YmEzZTE3ZjgwNTI1OTlhNSIsInVzZXJfaWQiOiIzIn0.GVJCcZRshv9YHkxCYRELlomfoJMLsGduwzGPhHmBCII	2026-03-23 16:13:47.099656-03	2027-03-23 16:13:47-03	3	92242e5889514065ba3e17f8052599a5
15	eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTgwNTgyOTI3MCwiaWF0IjoxNzc0MjkzMjcwLCJqdGkiOiJiNzllYzE4MjVlZTk0MmNjODIyYTVhYmZmZGExZmZmYiIsInVzZXJfaWQiOiIzIn0.5Huc7pgDzcDC-ypeqQ3-r9uXkCgkpOxG8WenTtM0smE	2026-03-23 16:14:30.072465-03	2027-03-23 16:14:30-03	3	b79ec1825ee942cc822a5abffda1fffb
16	eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTgwNTg1ODc0OCwiaWF0IjoxNzc0MzIyNzQ4LCJqdGkiOiI0ZWU1ZWVkMjc1YTU0MDVmOWE4NWRjOWUyNzZiYjZjYSIsInVzZXJfaWQiOiIzIn0.zlbJUospQILksvg1jmVtpkml81BUUyx4doddCv07jGQ	2026-03-24 00:25:48.736483-03	2027-03-24 00:25:48-03	3	4ee5eed275a5405f9a85dc9e276bb6ca
17	eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTgwNjU4OTY4MSwiaWF0IjoxNzc1MDUzNjgxLCJqdGkiOiIxMTAyN2RjMmM4Yzg0NTQzYjdjNjdjYjVjMTU4YmVmNyIsInVzZXJfaWQiOiIzIn0.o-FNGJTec45O0MEmWgAysm_nRDtXQ4JCOa-5WoWB9L4	2026-04-01 11:28:01.471348-03	2027-04-01 11:28:01-03	3	11027dc2c8c84543b7c67cb5c158bef7
18	eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTgwNjk0ODk2NSwiaWF0IjoxNzc1NDEyOTY1LCJqdGkiOiIxNjM4ZDQyNzE2YzI0MWQzYmEwMTRhMWYzNWJlMDY1MiIsInVzZXJfaWQiOiIzIn0.YIjzFZXwuOOt3tc06ZD1h36NISdd7N2DycZ_1e6suCk	2026-04-05 15:16:05.964341-03	2027-04-05 15:16:05-03	3	1638d42716c241d3ba014a1f35be0652
23	eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NzMyNTcxOSwiaWF0IjoxNzc2NzIwOTE5LCJqdGkiOiI3Zjk1OGM3NGZkZmM0Y2U4ODM0NGYzMzMwMWI4MWNhZCIsInVzZXJfaWQiOiIzIn0.NlyKv0jilzl0AFlpcrLY81vtXPg4w6WYZkKWAkWiZ-U	2026-04-20 18:35:19.141721-03	2026-04-27 18:35:19-03	3	7f958c74fdfc4ce88344f33301b81cad
\.


--
-- Name: account_emailaddress_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('"public"."account_emailaddress_id_seq"', 1, false);


--
-- Name: account_emailconfirmation_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('"public"."account_emailconfirmation_id_seq"', 1, false);


--
-- Name: auth_group_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('"public"."auth_group_id_seq"', 1, false);


--
-- Name: auth_group_permissions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('"public"."auth_group_permissions_id_seq"', 1, false);


--
-- Name: auth_permission_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('"public"."auth_permission_id_seq"', 172, true);


--
-- Name: auth_user_groups_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('"public"."auth_user_groups_id_seq"', 1, false);


--
-- Name: auth_user_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('"public"."auth_user_id_seq"', 16, true);


--
-- Name: auth_user_user_permissions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('"public"."auth_user_user_permissions_id_seq"', 1, false);


--
-- Name: core_apartment_furnitures_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('"public"."core_apartment_furnitures_id_seq"', 448, true);


--
-- Name: core_apartment_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('"public"."core_apartment_id_seq"', 46, true);


--
-- Name: core_building_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('"public"."core_building_id_seq"', 5, true);


--
-- Name: core_contractrule_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('"public"."core_contractrule_id_seq"', 7, true);


--
-- Name: core_creditcard_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('"public"."core_creditcard_id_seq"', 9, true);


--
-- Name: core_dependent_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('"public"."core_dependent_id_seq"', 3, true);


--
-- Name: core_devicetoken_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('"public"."core_devicetoken_id_seq"', 1, false);


--
-- Name: core_employeepayment_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('"public"."core_employeepayment_id_seq"', 3, true);


--
-- Name: core_expense_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('"public"."core_expense_id_seq"', 336, true);


--
-- Name: core_expensecategory_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('"public"."core_expensecategory_id_seq"', 18, true);


--
-- Name: core_expenseinstallment_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('"public"."core_expenseinstallment_id_seq"', 3223, true);


--
-- Name: core_expensemonthskip_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('"public"."core_expensemonthskip_id_seq"', 1, false);


--
-- Name: core_financialsettings_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('"public"."core_financialsettings_id_seq"', 1, false);


--
-- Name: core_furniture_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('"public"."core_furniture_id_seq"', 41, true);


--
-- Name: core_income_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('"public"."core_income_id_seq"', 2, true);


--
-- Name: core_ipcaindex_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('"public"."core_ipcaindex_id_seq"', 25, true);


--
-- Name: core_landlord_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('"public"."core_landlord_id_seq"', 1, true);


--
-- Name: core_lease_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('"public"."core_lease_id_seq"', 53, true);


--
-- Name: core_lease_tenants_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('"public"."core_lease_tenants_id_seq"', 78, true);


--
-- Name: core_monthsnapshot_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('"public"."core_monthsnapshot_id_seq"', 1, false);


--
-- Name: core_notification_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('"public"."core_notification_id_seq"', 1, false);


--
-- Name: core_oauth_exchange_code_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('"public"."core_oauth_exchange_code_id_seq"', 1, false);


--
-- Name: core_paymentproof_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('"public"."core_paymentproof_id_seq"', 1, false);


--
-- Name: core_person_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('"public"."core_person_id_seq"', 7, true);


--
-- Name: core_personincome_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('"public"."core_personincome_id_seq"', 6, true);


--
-- Name: core_personpayment_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('"public"."core_personpayment_id_seq"', 7, true);


--
-- Name: core_personpaymentschedule_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('"public"."core_personpaymentschedule_id_seq"', 1, false);


--
-- Name: core_rentadjustment_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('"public"."core_rentadjustment_id_seq"', 10, true);


--
-- Name: core_rentpayment_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('"public"."core_rentpayment_id_seq"', 30, true);


--
-- Name: core_tenant_furnitures_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('"public"."core_tenant_furnitures_id_seq"', 6, true);


--
-- Name: core_tenant_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('"public"."core_tenant_id_seq"', 65, true);


--
-- Name: core_whatsappverification_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('"public"."core_whatsappverification_id_seq"', 1, false);


--
-- Name: django_admin_log_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('"public"."django_admin_log_id_seq"', 274, true);


--
-- Name: django_content_type_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('"public"."django_content_type_id_seq"', 43, true);


--
-- Name: django_migrations_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('"public"."django_migrations_id_seq"', 96, true);


--
-- Name: django_site_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('"public"."django_site_id_seq"', 1, true);


--
-- Name: socialaccount_socialaccount_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('"public"."socialaccount_socialaccount_id_seq"', 1, false);


--
-- Name: socialaccount_socialapp_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('"public"."socialaccount_socialapp_id_seq"', 1, false);


--
-- Name: socialaccount_socialapp_sites_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('"public"."socialaccount_socialapp_sites_id_seq"', 1, false);


--
-- Name: socialaccount_socialtoken_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('"public"."socialaccount_socialtoken_id_seq"', 1, false);


--
-- Name: token_blacklist_blacklistedtoken_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('"public"."token_blacklist_blacklistedtoken_id_seq"', 4, true);


--
-- Name: token_blacklist_outstandingtoken_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('"public"."token_blacklist_outstandingtoken_id_seq"', 23, true);


--
-- Name: account_emailaddress account_emailaddress_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."account_emailaddress"
    ADD CONSTRAINT "account_emailaddress_pkey" PRIMARY KEY ("id");


--
-- Name: account_emailaddress account_emailaddress_user_id_email_987c8728_uniq; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."account_emailaddress"
    ADD CONSTRAINT "account_emailaddress_user_id_email_987c8728_uniq" UNIQUE ("user_id", "email");


--
-- Name: account_emailconfirmation account_emailconfirmation_key_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."account_emailconfirmation"
    ADD CONSTRAINT "account_emailconfirmation_key_key" UNIQUE ("key");


--
-- Name: account_emailconfirmation account_emailconfirmation_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."account_emailconfirmation"
    ADD CONSTRAINT "account_emailconfirmation_pkey" PRIMARY KEY ("id");


--
-- Name: auth_group auth_group_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."auth_group"
    ADD CONSTRAINT "auth_group_name_key" UNIQUE ("name");


--
-- Name: auth_group_permissions auth_group_permissions_group_id_permission_id_0cd325b0_uniq; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."auth_group_permissions"
    ADD CONSTRAINT "auth_group_permissions_group_id_permission_id_0cd325b0_uniq" UNIQUE ("group_id", "permission_id");


--
-- Name: auth_group_permissions auth_group_permissions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."auth_group_permissions"
    ADD CONSTRAINT "auth_group_permissions_pkey" PRIMARY KEY ("id");


--
-- Name: auth_group auth_group_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."auth_group"
    ADD CONSTRAINT "auth_group_pkey" PRIMARY KEY ("id");


--
-- Name: auth_permission auth_permission_content_type_id_codename_01ab375a_uniq; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."auth_permission"
    ADD CONSTRAINT "auth_permission_content_type_id_codename_01ab375a_uniq" UNIQUE ("content_type_id", "codename");


--
-- Name: auth_permission auth_permission_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."auth_permission"
    ADD CONSTRAINT "auth_permission_pkey" PRIMARY KEY ("id");


--
-- Name: auth_user_groups auth_user_groups_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."auth_user_groups"
    ADD CONSTRAINT "auth_user_groups_pkey" PRIMARY KEY ("id");


--
-- Name: auth_user_groups auth_user_groups_user_id_group_id_94350c0c_uniq; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."auth_user_groups"
    ADD CONSTRAINT "auth_user_groups_user_id_group_id_94350c0c_uniq" UNIQUE ("user_id", "group_id");


--
-- Name: auth_user auth_user_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."auth_user"
    ADD CONSTRAINT "auth_user_pkey" PRIMARY KEY ("id");


--
-- Name: auth_user_user_permissions auth_user_user_permissions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."auth_user_user_permissions"
    ADD CONSTRAINT "auth_user_user_permissions_pkey" PRIMARY KEY ("id");


--
-- Name: auth_user_user_permissions auth_user_user_permissions_user_id_permission_id_14a6b632_uniq; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."auth_user_user_permissions"
    ADD CONSTRAINT "auth_user_user_permissions_user_id_permission_id_14a6b632_uniq" UNIQUE ("user_id", "permission_id");


--
-- Name: auth_user auth_user_username_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."auth_user"
    ADD CONSTRAINT "auth_user_username_key" UNIQUE ("username");


--
-- Name: core_apartment core_apartment_building_id_number_eb0e26fe_uniq; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_apartment"
    ADD CONSTRAINT "core_apartment_building_id_number_eb0e26fe_uniq" UNIQUE ("building_id", "number");


--
-- Name: core_apartment_furnitures core_apartment_furniture_apartment_id_furniture_i_89520678_uniq; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_apartment_furnitures"
    ADD CONSTRAINT "core_apartment_furniture_apartment_id_furniture_i_89520678_uniq" UNIQUE ("apartment_id", "furniture_id");


--
-- Name: core_apartment_furnitures core_apartment_furnitures_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_apartment_furnitures"
    ADD CONSTRAINT "core_apartment_furnitures_pkey" PRIMARY KEY ("id");


--
-- Name: core_apartment core_apartment_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_apartment"
    ADD CONSTRAINT "core_apartment_pkey" PRIMARY KEY ("id");


--
-- Name: core_building core_building_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_building"
    ADD CONSTRAINT "core_building_pkey" PRIMARY KEY ("id");


--
-- Name: core_building core_building_street_number_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_building"
    ADD CONSTRAINT "core_building_street_number_key" UNIQUE ("street_number");


--
-- Name: core_contractrule core_contractrule_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_contractrule"
    ADD CONSTRAINT "core_contractrule_pkey" PRIMARY KEY ("id");


--
-- Name: core_creditcard core_creditcard_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_creditcard"
    ADD CONSTRAINT "core_creditcard_pkey" PRIMARY KEY ("id");


--
-- Name: core_dependent core_dependent_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_dependent"
    ADD CONSTRAINT "core_dependent_pkey" PRIMARY KEY ("id");


--
-- Name: core_devicetoken core_devicetoken_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_devicetoken"
    ADD CONSTRAINT "core_devicetoken_pkey" PRIMARY KEY ("id");


--
-- Name: core_devicetoken core_devicetoken_token_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_devicetoken"
    ADD CONSTRAINT "core_devicetoken_token_key" UNIQUE ("token");


--
-- Name: core_employeepayment core_employeepayment_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_employeepayment"
    ADD CONSTRAINT "core_employeepayment_pkey" PRIMARY KEY ("id");


--
-- Name: core_expense core_expense_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_expense"
    ADD CONSTRAINT "core_expense_pkey" PRIMARY KEY ("id");


--
-- Name: core_expensecategory core_expensecategory_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_expensecategory"
    ADD CONSTRAINT "core_expensecategory_name_key" UNIQUE ("name");


--
-- Name: core_expensecategory core_expensecategory_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_expensecategory"
    ADD CONSTRAINT "core_expensecategory_pkey" PRIMARY KEY ("id");


--
-- Name: core_expenseinstallment core_expenseinstallment_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_expenseinstallment"
    ADD CONSTRAINT "core_expenseinstallment_pkey" PRIMARY KEY ("id");


--
-- Name: core_expensemonthskip core_expensemonthskip_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_expensemonthskip"
    ADD CONSTRAINT "core_expensemonthskip_pkey" PRIMARY KEY ("id");


--
-- Name: core_financialsettings core_financialsettings_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_financialsettings"
    ADD CONSTRAINT "core_financialsettings_pkey" PRIMARY KEY ("id");


--
-- Name: core_furniture core_furniture_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_furniture"
    ADD CONSTRAINT "core_furniture_name_key" UNIQUE ("name");


--
-- Name: core_furniture core_furniture_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_furniture"
    ADD CONSTRAINT "core_furniture_pkey" PRIMARY KEY ("id");


--
-- Name: core_income core_income_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_income"
    ADD CONSTRAINT "core_income_pkey" PRIMARY KEY ("id");


--
-- Name: core_ipcaindex core_ipcaindex_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_ipcaindex"
    ADD CONSTRAINT "core_ipcaindex_pkey" PRIMARY KEY ("id");


--
-- Name: core_ipcaindex core_ipcaindex_reference_month_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_ipcaindex"
    ADD CONSTRAINT "core_ipcaindex_reference_month_key" UNIQUE ("reference_month");


--
-- Name: core_landlord core_landlord_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_landlord"
    ADD CONSTRAINT "core_landlord_pkey" PRIMARY KEY ("id");


--
-- Name: core_lease core_lease_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_lease"
    ADD CONSTRAINT "core_lease_pkey" PRIMARY KEY ("id");


--
-- Name: core_lease_tenants core_lease_tenants_lease_id_tenant_id_b6dc2ad7_uniq; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_lease_tenants"
    ADD CONSTRAINT "core_lease_tenants_lease_id_tenant_id_b6dc2ad7_uniq" UNIQUE ("lease_id", "tenant_id");


--
-- Name: core_lease_tenants core_lease_tenants_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_lease_tenants"
    ADD CONSTRAINT "core_lease_tenants_pkey" PRIMARY KEY ("id");


--
-- Name: core_monthsnapshot core_monthsnapshot_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_monthsnapshot"
    ADD CONSTRAINT "core_monthsnapshot_pkey" PRIMARY KEY ("id");


--
-- Name: core_notification core_notification_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_notification"
    ADD CONSTRAINT "core_notification_pkey" PRIMARY KEY ("id");


--
-- Name: core_oauth_exchange_code core_oauth_exchange_code_code_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_oauth_exchange_code"
    ADD CONSTRAINT "core_oauth_exchange_code_code_key" UNIQUE ("code");


--
-- Name: core_oauth_exchange_code core_oauth_exchange_code_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_oauth_exchange_code"
    ADD CONSTRAINT "core_oauth_exchange_code_pkey" PRIMARY KEY ("id");


--
-- Name: core_paymentproof core_paymentproof_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_paymentproof"
    ADD CONSTRAINT "core_paymentproof_pkey" PRIMARY KEY ("id");


--
-- Name: core_person core_person_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_person"
    ADD CONSTRAINT "core_person_pkey" PRIMARY KEY ("id");


--
-- Name: core_person core_person_user_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_person"
    ADD CONSTRAINT "core_person_user_id_key" UNIQUE ("user_id");


--
-- Name: core_personincome core_personincome_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_personincome"
    ADD CONSTRAINT "core_personincome_pkey" PRIMARY KEY ("id");


--
-- Name: core_personpayment core_personpayment_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_personpayment"
    ADD CONSTRAINT "core_personpayment_pkey" PRIMARY KEY ("id");


--
-- Name: core_personpaymentschedule core_personpaymentschedule_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_personpaymentschedule"
    ADD CONSTRAINT "core_personpaymentschedule_pkey" PRIMARY KEY ("id");


--
-- Name: core_rentadjustment core_rentadjustment_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_rentadjustment"
    ADD CONSTRAINT "core_rentadjustment_pkey" PRIMARY KEY ("id");


--
-- Name: core_rentpayment core_rentpayment_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_rentpayment"
    ADD CONSTRAINT "core_rentpayment_pkey" PRIMARY KEY ("id");


--
-- Name: core_tenant core_tenant_cpf_cnpj_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_tenant"
    ADD CONSTRAINT "core_tenant_cpf_cnpj_key" UNIQUE ("cpf_cnpj");


--
-- Name: core_tenant_furnitures core_tenant_furnitures_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_tenant_furnitures"
    ADD CONSTRAINT "core_tenant_furnitures_pkey" PRIMARY KEY ("id");


--
-- Name: core_tenant_furnitures core_tenant_furnitures_tenant_id_furniture_id_2ca08b30_uniq; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_tenant_furnitures"
    ADD CONSTRAINT "core_tenant_furnitures_tenant_id_furniture_id_2ca08b30_uniq" UNIQUE ("tenant_id", "furniture_id");


--
-- Name: core_tenant core_tenant_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_tenant"
    ADD CONSTRAINT "core_tenant_pkey" PRIMARY KEY ("id");


--
-- Name: core_tenant core_tenant_user_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_tenant"
    ADD CONSTRAINT "core_tenant_user_id_key" UNIQUE ("user_id");


--
-- Name: core_whatsappverification core_whatsappverification_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_whatsappverification"
    ADD CONSTRAINT "core_whatsappverification_pkey" PRIMARY KEY ("id");


--
-- Name: django_admin_log django_admin_log_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."django_admin_log"
    ADD CONSTRAINT "django_admin_log_pkey" PRIMARY KEY ("id");


--
-- Name: django_content_type django_content_type_app_label_model_76bd3d3b_uniq; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."django_content_type"
    ADD CONSTRAINT "django_content_type_app_label_model_76bd3d3b_uniq" UNIQUE ("app_label", "model");


--
-- Name: django_content_type django_content_type_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."django_content_type"
    ADD CONSTRAINT "django_content_type_pkey" PRIMARY KEY ("id");


--
-- Name: django_migrations django_migrations_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."django_migrations"
    ADD CONSTRAINT "django_migrations_pkey" PRIMARY KEY ("id");


--
-- Name: django_session django_session_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."django_session"
    ADD CONSTRAINT "django_session_pkey" PRIMARY KEY ("session_key");


--
-- Name: django_site django_site_domain_a2e37b91_uniq; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."django_site"
    ADD CONSTRAINT "django_site_domain_a2e37b91_uniq" UNIQUE ("domain");


--
-- Name: django_site django_site_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."django_site"
    ADD CONSTRAINT "django_site_pkey" PRIMARY KEY ("id");


--
-- Name: socialaccount_socialaccount socialaccount_socialaccount_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."socialaccount_socialaccount"
    ADD CONSTRAINT "socialaccount_socialaccount_pkey" PRIMARY KEY ("id");


--
-- Name: socialaccount_socialaccount socialaccount_socialaccount_provider_uid_fc810c6e_uniq; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."socialaccount_socialaccount"
    ADD CONSTRAINT "socialaccount_socialaccount_provider_uid_fc810c6e_uniq" UNIQUE ("provider", "uid");


--
-- Name: socialaccount_socialapp_sites socialaccount_socialapp__socialapp_id_site_id_71a9a768_uniq; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."socialaccount_socialapp_sites"
    ADD CONSTRAINT "socialaccount_socialapp__socialapp_id_site_id_71a9a768_uniq" UNIQUE ("socialapp_id", "site_id");


--
-- Name: socialaccount_socialapp socialaccount_socialapp_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."socialaccount_socialapp"
    ADD CONSTRAINT "socialaccount_socialapp_pkey" PRIMARY KEY ("id");


--
-- Name: socialaccount_socialapp_sites socialaccount_socialapp_sites_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."socialaccount_socialapp_sites"
    ADD CONSTRAINT "socialaccount_socialapp_sites_pkey" PRIMARY KEY ("id");


--
-- Name: socialaccount_socialtoken socialaccount_socialtoken_app_id_account_id_fca4e0ac_uniq; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."socialaccount_socialtoken"
    ADD CONSTRAINT "socialaccount_socialtoken_app_id_account_id_fca4e0ac_uniq" UNIQUE ("app_id", "account_id");


--
-- Name: socialaccount_socialtoken socialaccount_socialtoken_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."socialaccount_socialtoken"
    ADD CONSTRAINT "socialaccount_socialtoken_pkey" PRIMARY KEY ("id");


--
-- Name: token_blacklist_blacklistedtoken token_blacklist_blacklistedtoken_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."token_blacklist_blacklistedtoken"
    ADD CONSTRAINT "token_blacklist_blacklistedtoken_pkey" PRIMARY KEY ("id");


--
-- Name: token_blacklist_blacklistedtoken token_blacklist_blacklistedtoken_token_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."token_blacklist_blacklistedtoken"
    ADD CONSTRAINT "token_blacklist_blacklistedtoken_token_id_key" UNIQUE ("token_id");


--
-- Name: token_blacklist_outstandingtoken token_blacklist_outstandingtoken_jti_hex_d9bdf6f7_uniq; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."token_blacklist_outstandingtoken"
    ADD CONSTRAINT "token_blacklist_outstandingtoken_jti_hex_d9bdf6f7_uniq" UNIQUE ("jti");


--
-- Name: token_blacklist_outstandingtoken token_blacklist_outstandingtoken_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."token_blacklist_outstandingtoken"
    ADD CONSTRAINT "token_blacklist_outstandingtoken_pkey" PRIMARY KEY ("id");


--
-- Name: core_expensemonthskip unique_expense_skip_per_month; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_expensemonthskip"
    ADD CONSTRAINT "unique_expense_skip_per_month" UNIQUE ("expense_id", "reference_month");


--
-- Name: core_monthsnapshot unique_month_snapshot; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_monthsnapshot"
    ADD CONSTRAINT "unique_month_snapshot" UNIQUE ("reference_month");


--
-- Name: account_emailaddress_email_03be32b2; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "account_emailaddress_email_03be32b2" ON "public"."account_emailaddress" USING "btree" ("email");


--
-- Name: account_emailaddress_email_03be32b2_like; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "account_emailaddress_email_03be32b2_like" ON "public"."account_emailaddress" USING "btree" ("email" "varchar_pattern_ops");


--
-- Name: account_emailaddress_user_id_2c513194; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "account_emailaddress_user_id_2c513194" ON "public"."account_emailaddress" USING "btree" ("user_id");


--
-- Name: account_emailconfirmation_email_address_id_5b7f8c58; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "account_emailconfirmation_email_address_id_5b7f8c58" ON "public"."account_emailconfirmation" USING "btree" ("email_address_id");


--
-- Name: account_emailconfirmation_key_f43612bd_like; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "account_emailconfirmation_key_f43612bd_like" ON "public"."account_emailconfirmation" USING "btree" ("key" "varchar_pattern_ops");


--
-- Name: apt_building_number_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "apt_building_number_idx" ON "public"."core_apartment" USING "btree" ("building_id", "number");


--
-- Name: apt_building_rented_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "apt_building_rented_idx" ON "public"."core_apartment" USING "btree" ("building_id", "is_rented");


--
-- Name: apt_is_rented_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "apt_is_rented_idx" ON "public"."core_apartment" USING "btree" ("is_rented");


--
-- Name: apt_rented_value_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "apt_rented_value_idx" ON "public"."core_apartment" USING "btree" ("is_rented", "rental_value");


--
-- Name: auth_group_name_a6ea08ec_like; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "auth_group_name_a6ea08ec_like" ON "public"."auth_group" USING "btree" ("name" "varchar_pattern_ops");


--
-- Name: auth_group_permissions_group_id_b120cbf9; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "auth_group_permissions_group_id_b120cbf9" ON "public"."auth_group_permissions" USING "btree" ("group_id");


--
-- Name: auth_group_permissions_permission_id_84c5c92e; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "auth_group_permissions_permission_id_84c5c92e" ON "public"."auth_group_permissions" USING "btree" ("permission_id");


--
-- Name: auth_permission_content_type_id_2f476e4b; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "auth_permission_content_type_id_2f476e4b" ON "public"."auth_permission" USING "btree" ("content_type_id");


--
-- Name: auth_user_groups_group_id_97559544; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "auth_user_groups_group_id_97559544" ON "public"."auth_user_groups" USING "btree" ("group_id");


--
-- Name: auth_user_groups_user_id_6a12ed8b; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "auth_user_groups_user_id_6a12ed8b" ON "public"."auth_user_groups" USING "btree" ("user_id");


--
-- Name: auth_user_user_permissions_permission_id_1fbb5f2c; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "auth_user_user_permissions_permission_id_1fbb5f2c" ON "public"."auth_user_user_permissions" USING "btree" ("permission_id");


--
-- Name: auth_user_user_permissions_user_id_a95ead1b; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "auth_user_user_permissions_user_id_a95ead1b" ON "public"."auth_user_user_permissions" USING "btree" ("user_id");


--
-- Name: auth_user_username_6821ab7c_like; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "auth_user_username_6821ab7c_like" ON "public"."auth_user" USING "btree" ("username" "varchar_pattern_ops");


--
-- Name: core_apartment_building_id_016e1f62; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_apartment_building_id_016e1f62" ON "public"."core_apartment" USING "btree" ("building_id");


--
-- Name: core_apartment_created_by_id_63233eca; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_apartment_created_by_id_63233eca" ON "public"."core_apartment" USING "btree" ("created_by_id");


--
-- Name: core_apartment_deleted_by_id_aee90fef; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_apartment_deleted_by_id_aee90fef" ON "public"."core_apartment" USING "btree" ("deleted_by_id");


--
-- Name: core_apartment_furnitures_apartment_id_fbc40478; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_apartment_furnitures_apartment_id_fbc40478" ON "public"."core_apartment_furnitures" USING "btree" ("apartment_id");


--
-- Name: core_apartment_furnitures_furniture_id_a48c384f; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_apartment_furnitures_furniture_id_a48c384f" ON "public"."core_apartment_furnitures" USING "btree" ("furniture_id");


--
-- Name: core_apartment_is_deleted_5e88d077; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_apartment_is_deleted_5e88d077" ON "public"."core_apartment" USING "btree" ("is_deleted");


--
-- Name: core_apartment_owner_id_2eed0a5c; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_apartment_owner_id_2eed0a5c" ON "public"."core_apartment" USING "btree" ("owner_id");


--
-- Name: core_apartment_updated_by_id_951fb395; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_apartment_updated_by_id_951fb395" ON "public"."core_apartment" USING "btree" ("updated_by_id");


--
-- Name: core_building_created_by_id_880b4e2d; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_building_created_by_id_880b4e2d" ON "public"."core_building" USING "btree" ("created_by_id");


--
-- Name: core_building_deleted_by_id_46b06a95; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_building_deleted_by_id_46b06a95" ON "public"."core_building" USING "btree" ("deleted_by_id");


--
-- Name: core_building_is_deleted_c61a5410; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_building_is_deleted_c61a5410" ON "public"."core_building" USING "btree" ("is_deleted");


--
-- Name: core_building_updated_by_id_b9061915; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_building_updated_by_id_b9061915" ON "public"."core_building" USING "btree" ("updated_by_id");


--
-- Name: core_contractrule_created_by_id_5fc91e81; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_contractrule_created_by_id_5fc91e81" ON "public"."core_contractrule" USING "btree" ("created_by_id");


--
-- Name: core_contractrule_deleted_by_id_10cc20cc; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_contractrule_deleted_by_id_10cc20cc" ON "public"."core_contractrule" USING "btree" ("deleted_by_id");


--
-- Name: core_contractrule_is_active_53171522; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_contractrule_is_active_53171522" ON "public"."core_contractrule" USING "btree" ("is_active");


--
-- Name: core_contractrule_is_deleted_060b997a; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_contractrule_is_deleted_060b997a" ON "public"."core_contractrule" USING "btree" ("is_deleted");


--
-- Name: core_contractrule_order_2385e299; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_contractrule_order_2385e299" ON "public"."core_contractrule" USING "btree" ("order");


--
-- Name: core_contractrule_updated_by_id_de44cbd6; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_contractrule_updated_by_id_de44cbd6" ON "public"."core_contractrule" USING "btree" ("updated_by_id");


--
-- Name: core_creditcard_created_by_id_f58028fd; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_creditcard_created_by_id_f58028fd" ON "public"."core_creditcard" USING "btree" ("created_by_id");


--
-- Name: core_creditcard_deleted_by_id_c491ac7c; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_creditcard_deleted_by_id_c491ac7c" ON "public"."core_creditcard" USING "btree" ("deleted_by_id");


--
-- Name: core_creditcard_is_deleted_676e834b; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_creditcard_is_deleted_676e834b" ON "public"."core_creditcard" USING "btree" ("is_deleted");


--
-- Name: core_creditcard_person_id_ee13c25f; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_creditcard_person_id_ee13c25f" ON "public"."core_creditcard" USING "btree" ("person_id");


--
-- Name: core_creditcard_updated_by_id_64af5879; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_creditcard_updated_by_id_64af5879" ON "public"."core_creditcard" USING "btree" ("updated_by_id");


--
-- Name: core_dependent_created_by_id_1f75409f; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_dependent_created_by_id_1f75409f" ON "public"."core_dependent" USING "btree" ("created_by_id");


--
-- Name: core_dependent_deleted_by_id_ce75a7cb; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_dependent_deleted_by_id_ce75a7cb" ON "public"."core_dependent" USING "btree" ("deleted_by_id");


--
-- Name: core_dependent_is_deleted_d9f585ac; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_dependent_is_deleted_d9f585ac" ON "public"."core_dependent" USING "btree" ("is_deleted");


--
-- Name: core_dependent_tenant_id_ebc48edd; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_dependent_tenant_id_ebc48edd" ON "public"."core_dependent" USING "btree" ("tenant_id");


--
-- Name: core_dependent_updated_by_id_c4c6f044; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_dependent_updated_by_id_c4c6f044" ON "public"."core_dependent" USING "btree" ("updated_by_id");


--
-- Name: core_devicetoken_created_by_id_ddc63831; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_devicetoken_created_by_id_ddc63831" ON "public"."core_devicetoken" USING "btree" ("created_by_id");


--
-- Name: core_devicetoken_token_d6aba46e_like; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_devicetoken_token_d6aba46e_like" ON "public"."core_devicetoken" USING "btree" ("token" "varchar_pattern_ops");


--
-- Name: core_devicetoken_updated_by_id_d97de1f7; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_devicetoken_updated_by_id_d97de1f7" ON "public"."core_devicetoken" USING "btree" ("updated_by_id");


--
-- Name: core_devicetoken_user_id_479d4f09; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_devicetoken_user_id_479d4f09" ON "public"."core_devicetoken" USING "btree" ("user_id");


--
-- Name: core_employeepayment_created_by_id_e6b42255; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_employeepayment_created_by_id_e6b42255" ON "public"."core_employeepayment" USING "btree" ("created_by_id");


--
-- Name: core_employeepayment_deleted_by_id_a07b41ff; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_employeepayment_deleted_by_id_a07b41ff" ON "public"."core_employeepayment" USING "btree" ("deleted_by_id");


--
-- Name: core_employeepayment_is_deleted_d7f82bfb; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_employeepayment_is_deleted_d7f82bfb" ON "public"."core_employeepayment" USING "btree" ("is_deleted");


--
-- Name: core_employeepayment_person_id_6404dbbf; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_employeepayment_person_id_6404dbbf" ON "public"."core_employeepayment" USING "btree" ("person_id");


--
-- Name: core_employeepayment_updated_by_id_c6203d80; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_employeepayment_updated_by_id_c6203d80" ON "public"."core_employeepayment" USING "btree" ("updated_by_id");


--
-- Name: core_expense_building_id_bf94522e; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_expense_building_id_bf94522e" ON "public"."core_expense" USING "btree" ("building_id");


--
-- Name: core_expense_category_id_dcdb74b3; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_expense_category_id_dcdb74b3" ON "public"."core_expense" USING "btree" ("category_id");


--
-- Name: core_expense_created_by_id_f387daf3; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_expense_created_by_id_f387daf3" ON "public"."core_expense" USING "btree" ("created_by_id");


--
-- Name: core_expense_credit_card_id_49386120; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_expense_credit_card_id_49386120" ON "public"."core_expense" USING "btree" ("credit_card_id");


--
-- Name: core_expense_deleted_by_id_f2737b0a; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_expense_deleted_by_id_f2737b0a" ON "public"."core_expense" USING "btree" ("deleted_by_id");


--
-- Name: core_expense_is_deleted_a19e6eb0; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_expense_is_deleted_a19e6eb0" ON "public"."core_expense" USING "btree" ("is_deleted");


--
-- Name: core_expense_person_id_494927aa; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_expense_person_id_494927aa" ON "public"."core_expense" USING "btree" ("person_id");


--
-- Name: core_expense_updated_by_id_6316c802; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_expense_updated_by_id_6316c802" ON "public"."core_expense" USING "btree" ("updated_by_id");


--
-- Name: core_expensecategory_created_by_id_147adbcf; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_expensecategory_created_by_id_147adbcf" ON "public"."core_expensecategory" USING "btree" ("created_by_id");


--
-- Name: core_expensecategory_deleted_by_id_bb1ba135; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_expensecategory_deleted_by_id_bb1ba135" ON "public"."core_expensecategory" USING "btree" ("deleted_by_id");


--
-- Name: core_expensecategory_is_deleted_61ebaa13; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_expensecategory_is_deleted_61ebaa13" ON "public"."core_expensecategory" USING "btree" ("is_deleted");


--
-- Name: core_expensecategory_name_aaa0c3d3_like; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_expensecategory_name_aaa0c3d3_like" ON "public"."core_expensecategory" USING "btree" ("name" "varchar_pattern_ops");


--
-- Name: core_expensecategory_parent_id_823b7351; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_expensecategory_parent_id_823b7351" ON "public"."core_expensecategory" USING "btree" ("parent_id");


--
-- Name: core_expensecategory_updated_by_id_631d2c1b; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_expensecategory_updated_by_id_631d2c1b" ON "public"."core_expensecategory" USING "btree" ("updated_by_id");


--
-- Name: core_expenseinstallment_created_by_id_7fed7a7d; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_expenseinstallment_created_by_id_7fed7a7d" ON "public"."core_expenseinstallment" USING "btree" ("created_by_id");


--
-- Name: core_expenseinstallment_deleted_by_id_95b9cae6; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_expenseinstallment_deleted_by_id_95b9cae6" ON "public"."core_expenseinstallment" USING "btree" ("deleted_by_id");


--
-- Name: core_expenseinstallment_expense_id_2bdeacda; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_expenseinstallment_expense_id_2bdeacda" ON "public"."core_expenseinstallment" USING "btree" ("expense_id");


--
-- Name: core_expenseinstallment_is_deleted_214e26e4; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_expenseinstallment_is_deleted_214e26e4" ON "public"."core_expenseinstallment" USING "btree" ("is_deleted");


--
-- Name: core_expenseinstallment_updated_by_id_b3ccb642; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_expenseinstallment_updated_by_id_b3ccb642" ON "public"."core_expenseinstallment" USING "btree" ("updated_by_id");


--
-- Name: core_expensemonthskip_created_by_id_29f4e78c; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_expensemonthskip_created_by_id_29f4e78c" ON "public"."core_expensemonthskip" USING "btree" ("created_by_id");


--
-- Name: core_expensemonthskip_expense_id_ac188bd0; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_expensemonthskip_expense_id_ac188bd0" ON "public"."core_expensemonthskip" USING "btree" ("expense_id");


--
-- Name: core_expensemonthskip_updated_by_id_6715bdf6; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_expensemonthskip_updated_by_id_6715bdf6" ON "public"."core_expensemonthskip" USING "btree" ("updated_by_id");


--
-- Name: core_financialsettings_updated_by_id_d1242b26; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_financialsettings_updated_by_id_d1242b26" ON "public"."core_financialsettings" USING "btree" ("updated_by_id");


--
-- Name: core_furniture_created_by_id_ac6fa2c3; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_furniture_created_by_id_ac6fa2c3" ON "public"."core_furniture" USING "btree" ("created_by_id");


--
-- Name: core_furniture_deleted_by_id_48e626b9; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_furniture_deleted_by_id_48e626b9" ON "public"."core_furniture" USING "btree" ("deleted_by_id");


--
-- Name: core_furniture_is_deleted_6ea2d58b; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_furniture_is_deleted_6ea2d58b" ON "public"."core_furniture" USING "btree" ("is_deleted");


--
-- Name: core_furniture_name_3a0fcd18_like; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_furniture_name_3a0fcd18_like" ON "public"."core_furniture" USING "btree" ("name" "varchar_pattern_ops");


--
-- Name: core_furniture_updated_by_id_05fc60d9; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_furniture_updated_by_id_05fc60d9" ON "public"."core_furniture" USING "btree" ("updated_by_id");


--
-- Name: core_income_building_id_76ef9a87; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_income_building_id_76ef9a87" ON "public"."core_income" USING "btree" ("building_id");


--
-- Name: core_income_category_id_03e3d7bb; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_income_category_id_03e3d7bb" ON "public"."core_income" USING "btree" ("category_id");


--
-- Name: core_income_created_by_id_10268b93; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_income_created_by_id_10268b93" ON "public"."core_income" USING "btree" ("created_by_id");


--
-- Name: core_income_deleted_by_id_eabcd72d; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_income_deleted_by_id_eabcd72d" ON "public"."core_income" USING "btree" ("deleted_by_id");


--
-- Name: core_income_is_deleted_f41c8420; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_income_is_deleted_f41c8420" ON "public"."core_income" USING "btree" ("is_deleted");


--
-- Name: core_income_person_id_4b0c8077; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_income_person_id_4b0c8077" ON "public"."core_income" USING "btree" ("person_id");


--
-- Name: core_income_updated_by_id_71cc281c; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_income_updated_by_id_71cc281c" ON "public"."core_income" USING "btree" ("updated_by_id");


--
-- Name: core_landlord_created_by_id_26771936; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_landlord_created_by_id_26771936" ON "public"."core_landlord" USING "btree" ("created_by_id");


--
-- Name: core_landlord_deleted_by_id_7daf3704; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_landlord_deleted_by_id_7daf3704" ON "public"."core_landlord" USING "btree" ("deleted_by_id");


--
-- Name: core_landlord_is_deleted_9aac14d7; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_landlord_is_deleted_9aac14d7" ON "public"."core_landlord" USING "btree" ("is_deleted");


--
-- Name: core_landlord_updated_by_id_a96c2f8a; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_landlord_updated_by_id_a96c2f8a" ON "public"."core_landlord" USING "btree" ("updated_by_id");


--
-- Name: core_lease_apartment_id_f3c48467; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_lease_apartment_id_f3c48467" ON "public"."core_lease" USING "btree" ("apartment_id");


--
-- Name: core_lease_created_by_id_10d4e47a; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_lease_created_by_id_10d4e47a" ON "public"."core_lease" USING "btree" ("created_by_id");


--
-- Name: core_lease_deleted_by_id_a349bea4; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_lease_deleted_by_id_a349bea4" ON "public"."core_lease" USING "btree" ("deleted_by_id");


--
-- Name: core_lease_is_deleted_3b73b647; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_lease_is_deleted_3b73b647" ON "public"."core_lease" USING "btree" ("is_deleted");


--
-- Name: core_lease_resident_dependent_id_999b3373; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_lease_resident_dependent_id_999b3373" ON "public"."core_lease" USING "btree" ("resident_dependent_id");


--
-- Name: core_lease_responsible_tenant_id_7048940f; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_lease_responsible_tenant_id_7048940f" ON "public"."core_lease" USING "btree" ("responsible_tenant_id");


--
-- Name: core_lease_start_date_0ca440cd; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_lease_start_date_0ca440cd" ON "public"."core_lease" USING "btree" ("start_date");


--
-- Name: core_lease_tenants_lease_id_4e718198; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_lease_tenants_lease_id_4e718198" ON "public"."core_lease_tenants" USING "btree" ("lease_id");


--
-- Name: core_lease_tenants_tenant_id_1fe477aa; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_lease_tenants_tenant_id_1fe477aa" ON "public"."core_lease_tenants" USING "btree" ("tenant_id");


--
-- Name: core_lease_updated_by_id_837ebc4b; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_lease_updated_by_id_837ebc4b" ON "public"."core_lease" USING "btree" ("updated_by_id");


--
-- Name: core_monthsnapshot_created_by_id_3e18926e; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_monthsnapshot_created_by_id_3e18926e" ON "public"."core_monthsnapshot" USING "btree" ("created_by_id");


--
-- Name: core_monthsnapshot_updated_by_id_ff44bdc4; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_monthsnapshot_updated_by_id_ff44bdc4" ON "public"."core_monthsnapshot" USING "btree" ("updated_by_id");


--
-- Name: core_notifi_recipie_37a373_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_notifi_recipie_37a373_idx" ON "public"."core_notification" USING "btree" ("recipient_id", "sent_at" DESC);


--
-- Name: core_notifi_recipie_aeffaf_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_notifi_recipie_aeffaf_idx" ON "public"."core_notification" USING "btree" ("recipient_id", "is_read");


--
-- Name: core_notifi_type_312e1c_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_notifi_type_312e1c_idx" ON "public"."core_notification" USING "btree" ("type", "recipient_id", "sent_at");


--
-- Name: core_notification_created_by_id_b954034c; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_notification_created_by_id_b954034c" ON "public"."core_notification" USING "btree" ("created_by_id");


--
-- Name: core_notification_recipient_id_24a3d95c; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_notification_recipient_id_24a3d95c" ON "public"."core_notification" USING "btree" ("recipient_id");


--
-- Name: core_notification_updated_by_id_10dfda28; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_notification_updated_by_id_10dfda28" ON "public"."core_notification" USING "btree" ("updated_by_id");


--
-- Name: core_oauth_exchange_code_user_id_806380b2; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_oauth_exchange_code_user_id_806380b2" ON "public"."core_oauth_exchange_code" USING "btree" ("user_id");


--
-- Name: core_paymen_lease_i_d9c27f_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_paymen_lease_i_d9c27f_idx" ON "public"."core_paymentproof" USING "btree" ("lease_id", "reference_month");


--
-- Name: core_paymen_status_2d7c73_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_paymen_status_2d7c73_idx" ON "public"."core_paymentproof" USING "btree" ("status", "created_at" DESC);


--
-- Name: core_paymentproof_created_by_id_1cfed265; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_paymentproof_created_by_id_1cfed265" ON "public"."core_paymentproof" USING "btree" ("created_by_id");


--
-- Name: core_paymentproof_deleted_by_id_6023d639; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_paymentproof_deleted_by_id_6023d639" ON "public"."core_paymentproof" USING "btree" ("deleted_by_id");


--
-- Name: core_paymentproof_is_deleted_89873b63; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_paymentproof_is_deleted_89873b63" ON "public"."core_paymentproof" USING "btree" ("is_deleted");


--
-- Name: core_paymentproof_lease_id_b7a8844e; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_paymentproof_lease_id_b7a8844e" ON "public"."core_paymentproof" USING "btree" ("lease_id");


--
-- Name: core_paymentproof_reviewed_by_id_1e426c23; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_paymentproof_reviewed_by_id_1e426c23" ON "public"."core_paymentproof" USING "btree" ("reviewed_by_id");


--
-- Name: core_paymentproof_updated_by_id_aa748fc5; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_paymentproof_updated_by_id_aa748fc5" ON "public"."core_paymentproof" USING "btree" ("updated_by_id");


--
-- Name: core_person_created_by_id_47e54549; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_person_created_by_id_47e54549" ON "public"."core_person" USING "btree" ("created_by_id");


--
-- Name: core_person_deleted_by_id_cc8215b4; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_person_deleted_by_id_cc8215b4" ON "public"."core_person" USING "btree" ("deleted_by_id");


--
-- Name: core_person_is_deleted_6e3a9413; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_person_is_deleted_6e3a9413" ON "public"."core_person" USING "btree" ("is_deleted");


--
-- Name: core_person_updated_by_id_2c0e591e; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_person_updated_by_id_2c0e591e" ON "public"."core_person" USING "btree" ("updated_by_id");


--
-- Name: core_personincome_apartment_id_6d13107c; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_personincome_apartment_id_6d13107c" ON "public"."core_personincome" USING "btree" ("apartment_id");


--
-- Name: core_personincome_created_by_id_b232accf; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_personincome_created_by_id_b232accf" ON "public"."core_personincome" USING "btree" ("created_by_id");


--
-- Name: core_personincome_deleted_by_id_f348ffbb; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_personincome_deleted_by_id_f348ffbb" ON "public"."core_personincome" USING "btree" ("deleted_by_id");


--
-- Name: core_personincome_is_deleted_30a25355; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_personincome_is_deleted_30a25355" ON "public"."core_personincome" USING "btree" ("is_deleted");


--
-- Name: core_personincome_person_id_bff5a221; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_personincome_person_id_bff5a221" ON "public"."core_personincome" USING "btree" ("person_id");


--
-- Name: core_personincome_updated_by_id_704816d7; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_personincome_updated_by_id_704816d7" ON "public"."core_personincome" USING "btree" ("updated_by_id");


--
-- Name: core_personpayment_created_by_id_719a825a; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_personpayment_created_by_id_719a825a" ON "public"."core_personpayment" USING "btree" ("created_by_id");


--
-- Name: core_personpayment_deleted_by_id_99ec06ff; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_personpayment_deleted_by_id_99ec06ff" ON "public"."core_personpayment" USING "btree" ("deleted_by_id");


--
-- Name: core_personpayment_is_deleted_21b48c3a; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_personpayment_is_deleted_21b48c3a" ON "public"."core_personpayment" USING "btree" ("is_deleted");


--
-- Name: core_personpayment_person_id_510d65a7; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_personpayment_person_id_510d65a7" ON "public"."core_personpayment" USING "btree" ("person_id");


--
-- Name: core_personpayment_updated_by_id_1d230c37; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_personpayment_updated_by_id_1d230c37" ON "public"."core_personpayment" USING "btree" ("updated_by_id");


--
-- Name: core_personpaymentschedule_created_by_id_5524466f; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_personpaymentschedule_created_by_id_5524466f" ON "public"."core_personpaymentschedule" USING "btree" ("created_by_id");


--
-- Name: core_personpaymentschedule_deleted_by_id_6b831031; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_personpaymentschedule_deleted_by_id_6b831031" ON "public"."core_personpaymentschedule" USING "btree" ("deleted_by_id");


--
-- Name: core_personpaymentschedule_is_deleted_48c18b58; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_personpaymentschedule_is_deleted_48c18b58" ON "public"."core_personpaymentschedule" USING "btree" ("is_deleted");


--
-- Name: core_personpaymentschedule_person_id_364d7616; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_personpaymentschedule_person_id_364d7616" ON "public"."core_personpaymentschedule" USING "btree" ("person_id");


--
-- Name: core_personpaymentschedule_updated_by_id_a6fcae64; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_personpaymentschedule_updated_by_id_a6fcae64" ON "public"."core_personpaymentschedule" USING "btree" ("updated_by_id");


--
-- Name: core_rentadjustment_created_by_id_70b404e3; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_rentadjustment_created_by_id_70b404e3" ON "public"."core_rentadjustment" USING "btree" ("created_by_id");


--
-- Name: core_rentadjustment_deleted_by_id_4b51a341; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_rentadjustment_deleted_by_id_4b51a341" ON "public"."core_rentadjustment" USING "btree" ("deleted_by_id");


--
-- Name: core_rentadjustment_is_deleted_79558ba6; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_rentadjustment_is_deleted_79558ba6" ON "public"."core_rentadjustment" USING "btree" ("is_deleted");


--
-- Name: core_rentadjustment_lease_id_49b5f5c0; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_rentadjustment_lease_id_49b5f5c0" ON "public"."core_rentadjustment" USING "btree" ("lease_id");


--
-- Name: core_rentadjustment_updated_by_id_d57f9608; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_rentadjustment_updated_by_id_d57f9608" ON "public"."core_rentadjustment" USING "btree" ("updated_by_id");


--
-- Name: core_rentpayment_created_by_id_78b62bf5; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_rentpayment_created_by_id_78b62bf5" ON "public"."core_rentpayment" USING "btree" ("created_by_id");


--
-- Name: core_rentpayment_deleted_by_id_c6bc4999; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_rentpayment_deleted_by_id_c6bc4999" ON "public"."core_rentpayment" USING "btree" ("deleted_by_id");


--
-- Name: core_rentpayment_is_deleted_d07101fc; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_rentpayment_is_deleted_d07101fc" ON "public"."core_rentpayment" USING "btree" ("is_deleted");


--
-- Name: core_rentpayment_lease_id_a1c2bf37; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_rentpayment_lease_id_a1c2bf37" ON "public"."core_rentpayment" USING "btree" ("lease_id");


--
-- Name: core_rentpayment_updated_by_id_bef14fbe; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_rentpayment_updated_by_id_bef14fbe" ON "public"."core_rentpayment" USING "btree" ("updated_by_id");


--
-- Name: core_tenant_cpf_cnpj_1c2c482d_like; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_tenant_cpf_cnpj_1c2c482d_like" ON "public"."core_tenant" USING "btree" ("cpf_cnpj" "varchar_pattern_ops");


--
-- Name: core_tenant_created_by_id_c9f39c01; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_tenant_created_by_id_c9f39c01" ON "public"."core_tenant" USING "btree" ("created_by_id");


--
-- Name: core_tenant_deleted_by_id_3ff8f8bb; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_tenant_deleted_by_id_3ff8f8bb" ON "public"."core_tenant" USING "btree" ("deleted_by_id");


--
-- Name: core_tenant_furnitures_furniture_id_b38a2b66; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_tenant_furnitures_furniture_id_b38a2b66" ON "public"."core_tenant_furnitures" USING "btree" ("furniture_id");


--
-- Name: core_tenant_furnitures_tenant_id_a5273f50; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_tenant_furnitures_tenant_id_a5273f50" ON "public"."core_tenant_furnitures" USING "btree" ("tenant_id");


--
-- Name: core_tenant_is_deleted_a0b4f60a; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_tenant_is_deleted_a0b4f60a" ON "public"."core_tenant" USING "btree" ("is_deleted");


--
-- Name: core_tenant_updated_by_id_a39a25ef; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_tenant_updated_by_id_a39a25ef" ON "public"."core_tenant" USING "btree" ("updated_by_id");


--
-- Name: core_whatsa_cpf_cnp_c8c80e_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "core_whatsa_cpf_cnp_c8c80e_idx" ON "public"."core_whatsappverification" USING "btree" ("cpf_cnpj", "is_used", "expires_at");


--
-- Name: django_admin_log_content_type_id_c4bce8eb; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "django_admin_log_content_type_id_c4bce8eb" ON "public"."django_admin_log" USING "btree" ("content_type_id");


--
-- Name: django_admin_log_user_id_c564eba6; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "django_admin_log_user_id_c564eba6" ON "public"."django_admin_log" USING "btree" ("user_id");


--
-- Name: django_session_expire_date_a5c62663; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "django_session_expire_date_a5c62663" ON "public"."django_session" USING "btree" ("expire_date");


--
-- Name: django_session_session_key_c0390e0f_like; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "django_session_session_key_c0390e0f_like" ON "public"."django_session" USING "btree" ("session_key" "varchar_pattern_ops");


--
-- Name: django_site_domain_a2e37b91_like; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "django_site_domain_a2e37b91_like" ON "public"."django_site" USING "btree" ("domain" "varchar_pattern_ops");


--
-- Name: exp_person_date_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "exp_person_date_idx" ON "public"."core_expense" USING "btree" ("person_id", "expense_date");


--
-- Name: exp_person_type_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "exp_person_type_idx" ON "public"."core_expense" USING "btree" ("person_id", "expense_type");


--
-- Name: expense_date_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "expense_date_idx" ON "public"."core_expense" USING "btree" ("expense_date" DESC);


--
-- Name: expense_paid_date_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "expense_paid_date_idx" ON "public"."core_expense" USING "btree" ("is_paid", "expense_date" DESC);


--
-- Name: expense_type_date_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "expense_type_date_idx" ON "public"."core_expense" USING "btree" ("expense_type", "expense_date" DESC);


--
-- Name: idx_expense_category_date; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "idx_expense_category_date" ON "public"."core_expense" USING "btree" ("category_id", "expense_date");


--
-- Name: idx_expense_person_paid_date; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "idx_expense_person_paid_date" ON "public"."core_expense" USING "btree" ("person_id", "is_paid", "expense_date");


--
-- Name: idx_expense_recurring_date; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "idx_expense_recurring_date" ON "public"."core_expense" USING "btree" ("is_recurring", "expense_date");


--
-- Name: inst_exp_date_paid_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "inst_exp_date_paid_idx" ON "public"."core_expenseinstallment" USING "btree" ("expense_id", "due_date", "is_paid");


--
-- Name: installment_due_date_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "installment_due_date_idx" ON "public"."core_expenseinstallment" USING "btree" ("due_date");


--
-- Name: installment_paid_due_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "installment_paid_due_idx" ON "public"."core_expenseinstallment" USING "btree" ("is_paid", "due_date");


--
-- Name: ipca_index_month_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "ipca_index_month_idx" ON "public"."core_ipcaindex" USING "btree" ("reference_month");


--
-- Name: lease_apt_date_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "lease_apt_date_idx" ON "public"."core_lease" USING "btree" ("apartment_id", "start_date");


--
-- Name: lease_contract_gen_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "lease_contract_gen_idx" ON "public"."core_lease" USING "btree" ("contract_generated");


--
-- Name: lease_start_date_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "lease_start_date_idx" ON "public"."core_lease" USING "btree" ("start_date");


--
-- Name: lease_status_date_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "lease_status_date_idx" ON "public"."core_lease" USING "btree" ("contract_generated", "start_date");


--
-- Name: lease_tenant_date_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "lease_tenant_date_idx" ON "public"."core_lease" USING "btree" ("responsible_tenant_id", "start_date");


--
-- Name: person_payment_month_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "person_payment_month_idx" ON "public"."core_personpayment" USING "btree" ("person_id", "reference_month");


--
-- Name: rent_payment_lease_month_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "rent_payment_lease_month_idx" ON "public"."core_rentpayment" USING "btree" ("lease_id", "reference_month" DESC);


--
-- Name: rent_payment_month_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "rent_payment_month_idx" ON "public"."core_rentpayment" USING "btree" ("reference_month" DESC);


--
-- Name: rule_active_order_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "rule_active_order_idx" ON "public"."core_contractrule" USING "btree" ("is_active", "order");


--
-- Name: socialaccount_socialaccount_user_id_8146e70c; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "socialaccount_socialaccount_user_id_8146e70c" ON "public"."socialaccount_socialaccount" USING "btree" ("user_id");


--
-- Name: socialaccount_socialapp_sites_site_id_2579dee5; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "socialaccount_socialapp_sites_site_id_2579dee5" ON "public"."socialaccount_socialapp_sites" USING "btree" ("site_id");


--
-- Name: socialaccount_socialapp_sites_socialapp_id_97fb6e7d; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "socialaccount_socialapp_sites_socialapp_id_97fb6e7d" ON "public"."socialaccount_socialapp_sites" USING "btree" ("socialapp_id");


--
-- Name: socialaccount_socialtoken_account_id_951f210e; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "socialaccount_socialtoken_account_id_951f210e" ON "public"."socialaccount_socialtoken" USING "btree" ("account_id");


--
-- Name: socialaccount_socialtoken_app_id_636a42d7; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "socialaccount_socialtoken_app_id_636a42d7" ON "public"."socialaccount_socialtoken" USING "btree" ("app_id");


--
-- Name: tenant_status_type_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "tenant_status_type_idx" ON "public"."core_tenant" USING "btree" ("marital_status", "is_company");


--
-- Name: tenant_type_name_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "tenant_type_name_idx" ON "public"."core_tenant" USING "btree" ("is_company", "name");


--
-- Name: token_blacklist_outstandingtoken_jti_hex_d9bdf6f7_like; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "token_blacklist_outstandingtoken_jti_hex_d9bdf6f7_like" ON "public"."token_blacklist_outstandingtoken" USING "btree" ("jti" "varchar_pattern_ops");


--
-- Name: token_blacklist_outstandingtoken_user_id_83bc629a; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX "token_blacklist_outstandingtoken_user_id_83bc629a" ON "public"."token_blacklist_outstandingtoken" USING "btree" ("user_id");


--
-- Name: unique_active_credit_card; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX "unique_active_credit_card" ON "public"."core_creditcard" USING "btree" ("person_id", "nickname") WHERE (NOT "is_deleted");


--
-- Name: unique_active_employee_payment; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX "unique_active_employee_payment" ON "public"."core_employeepayment" USING "btree" ("person_id", "reference_month") WHERE (NOT "is_deleted");


--
-- Name: unique_active_expense_installment; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX "unique_active_expense_installment" ON "public"."core_expenseinstallment" USING "btree" ("expense_id", "installment_number") WHERE (NOT "is_deleted");


--
-- Name: unique_active_lease_per_apartment; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX "unique_active_lease_per_apartment" ON "public"."core_lease" USING "btree" ("apartment_id") WHERE (NOT "is_deleted");


--
-- Name: unique_active_rent_payment; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX "unique_active_rent_payment" ON "public"."core_rentpayment" USING "btree" ("lease_id", "reference_month") WHERE (NOT "is_deleted");


--
-- Name: unique_person_schedule_per_day; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX "unique_person_schedule_per_day" ON "public"."core_personpaymentschedule" USING "btree" ("person_id", "reference_month", "due_day") WHERE (NOT "is_deleted");


--
-- Name: unique_primary_email; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX "unique_primary_email" ON "public"."account_emailaddress" USING "btree" ("user_id", "primary") WHERE "primary";


--
-- Name: unique_verified_email; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX "unique_verified_email" ON "public"."account_emailaddress" USING "btree" ("email") WHERE "verified";


--
-- Name: account_emailaddress account_emailaddress_user_id_2c513194_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."account_emailaddress"
    ADD CONSTRAINT "account_emailaddress_user_id_2c513194_fk_auth_user_id" FOREIGN KEY ("user_id") REFERENCES "public"."auth_user"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: account_emailconfirmation account_emailconfirm_email_address_id_5b7f8c58_fk_account_e; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."account_emailconfirmation"
    ADD CONSTRAINT "account_emailconfirm_email_address_id_5b7f8c58_fk_account_e" FOREIGN KEY ("email_address_id") REFERENCES "public"."account_emailaddress"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: auth_group_permissions auth_group_permissio_permission_id_84c5c92e_fk_auth_perm; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."auth_group_permissions"
    ADD CONSTRAINT "auth_group_permissio_permission_id_84c5c92e_fk_auth_perm" FOREIGN KEY ("permission_id") REFERENCES "public"."auth_permission"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: auth_group_permissions auth_group_permissions_group_id_b120cbf9_fk_auth_group_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."auth_group_permissions"
    ADD CONSTRAINT "auth_group_permissions_group_id_b120cbf9_fk_auth_group_id" FOREIGN KEY ("group_id") REFERENCES "public"."auth_group"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: auth_permission auth_permission_content_type_id_2f476e4b_fk_django_co; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."auth_permission"
    ADD CONSTRAINT "auth_permission_content_type_id_2f476e4b_fk_django_co" FOREIGN KEY ("content_type_id") REFERENCES "public"."django_content_type"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: auth_user_groups auth_user_groups_group_id_97559544_fk_auth_group_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."auth_user_groups"
    ADD CONSTRAINT "auth_user_groups_group_id_97559544_fk_auth_group_id" FOREIGN KEY ("group_id") REFERENCES "public"."auth_group"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: auth_user_groups auth_user_groups_user_id_6a12ed8b_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."auth_user_groups"
    ADD CONSTRAINT "auth_user_groups_user_id_6a12ed8b_fk_auth_user_id" FOREIGN KEY ("user_id") REFERENCES "public"."auth_user"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: auth_user_user_permissions auth_user_user_permi_permission_id_1fbb5f2c_fk_auth_perm; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."auth_user_user_permissions"
    ADD CONSTRAINT "auth_user_user_permi_permission_id_1fbb5f2c_fk_auth_perm" FOREIGN KEY ("permission_id") REFERENCES "public"."auth_permission"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: auth_user_user_permissions auth_user_user_permissions_user_id_a95ead1b_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."auth_user_user_permissions"
    ADD CONSTRAINT "auth_user_user_permissions_user_id_a95ead1b_fk_auth_user_id" FOREIGN KEY ("user_id") REFERENCES "public"."auth_user"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_apartment core_apartment_building_id_016e1f62_fk_core_building_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_apartment"
    ADD CONSTRAINT "core_apartment_building_id_016e1f62_fk_core_building_id" FOREIGN KEY ("building_id") REFERENCES "public"."core_building"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_apartment core_apartment_created_by_id_63233eca_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_apartment"
    ADD CONSTRAINT "core_apartment_created_by_id_63233eca_fk_auth_user_id" FOREIGN KEY ("created_by_id") REFERENCES "public"."auth_user"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_apartment core_apartment_deleted_by_id_aee90fef_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_apartment"
    ADD CONSTRAINT "core_apartment_deleted_by_id_aee90fef_fk_auth_user_id" FOREIGN KEY ("deleted_by_id") REFERENCES "public"."auth_user"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_apartment_furnitures core_apartment_furni_apartment_id_fbc40478_fk_core_apar; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_apartment_furnitures"
    ADD CONSTRAINT "core_apartment_furni_apartment_id_fbc40478_fk_core_apar" FOREIGN KEY ("apartment_id") REFERENCES "public"."core_apartment"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_apartment_furnitures core_apartment_furni_furniture_id_a48c384f_fk_core_furn; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_apartment_furnitures"
    ADD CONSTRAINT "core_apartment_furni_furniture_id_a48c384f_fk_core_furn" FOREIGN KEY ("furniture_id") REFERENCES "public"."core_furniture"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_apartment core_apartment_owner_id_2eed0a5c_fk_core_person_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_apartment"
    ADD CONSTRAINT "core_apartment_owner_id_2eed0a5c_fk_core_person_id" FOREIGN KEY ("owner_id") REFERENCES "public"."core_person"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_apartment core_apartment_updated_by_id_951fb395_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_apartment"
    ADD CONSTRAINT "core_apartment_updated_by_id_951fb395_fk_auth_user_id" FOREIGN KEY ("updated_by_id") REFERENCES "public"."auth_user"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_building core_building_created_by_id_880b4e2d_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_building"
    ADD CONSTRAINT "core_building_created_by_id_880b4e2d_fk_auth_user_id" FOREIGN KEY ("created_by_id") REFERENCES "public"."auth_user"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_building core_building_deleted_by_id_46b06a95_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_building"
    ADD CONSTRAINT "core_building_deleted_by_id_46b06a95_fk_auth_user_id" FOREIGN KEY ("deleted_by_id") REFERENCES "public"."auth_user"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_building core_building_updated_by_id_b9061915_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_building"
    ADD CONSTRAINT "core_building_updated_by_id_b9061915_fk_auth_user_id" FOREIGN KEY ("updated_by_id") REFERENCES "public"."auth_user"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_contractrule core_contractrule_created_by_id_5fc91e81_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_contractrule"
    ADD CONSTRAINT "core_contractrule_created_by_id_5fc91e81_fk_auth_user_id" FOREIGN KEY ("created_by_id") REFERENCES "public"."auth_user"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_contractrule core_contractrule_deleted_by_id_10cc20cc_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_contractrule"
    ADD CONSTRAINT "core_contractrule_deleted_by_id_10cc20cc_fk_auth_user_id" FOREIGN KEY ("deleted_by_id") REFERENCES "public"."auth_user"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_contractrule core_contractrule_updated_by_id_de44cbd6_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_contractrule"
    ADD CONSTRAINT "core_contractrule_updated_by_id_de44cbd6_fk_auth_user_id" FOREIGN KEY ("updated_by_id") REFERENCES "public"."auth_user"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_creditcard core_creditcard_created_by_id_f58028fd_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_creditcard"
    ADD CONSTRAINT "core_creditcard_created_by_id_f58028fd_fk_auth_user_id" FOREIGN KEY ("created_by_id") REFERENCES "public"."auth_user"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_creditcard core_creditcard_deleted_by_id_c491ac7c_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_creditcard"
    ADD CONSTRAINT "core_creditcard_deleted_by_id_c491ac7c_fk_auth_user_id" FOREIGN KEY ("deleted_by_id") REFERENCES "public"."auth_user"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_creditcard core_creditcard_person_id_ee13c25f_fk_core_person_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_creditcard"
    ADD CONSTRAINT "core_creditcard_person_id_ee13c25f_fk_core_person_id" FOREIGN KEY ("person_id") REFERENCES "public"."core_person"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_creditcard core_creditcard_updated_by_id_64af5879_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_creditcard"
    ADD CONSTRAINT "core_creditcard_updated_by_id_64af5879_fk_auth_user_id" FOREIGN KEY ("updated_by_id") REFERENCES "public"."auth_user"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_dependent core_dependent_created_by_id_1f75409f_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_dependent"
    ADD CONSTRAINT "core_dependent_created_by_id_1f75409f_fk_auth_user_id" FOREIGN KEY ("created_by_id") REFERENCES "public"."auth_user"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_dependent core_dependent_deleted_by_id_ce75a7cb_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_dependent"
    ADD CONSTRAINT "core_dependent_deleted_by_id_ce75a7cb_fk_auth_user_id" FOREIGN KEY ("deleted_by_id") REFERENCES "public"."auth_user"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_dependent core_dependent_tenant_id_ebc48edd_fk_core_tenant_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_dependent"
    ADD CONSTRAINT "core_dependent_tenant_id_ebc48edd_fk_core_tenant_id" FOREIGN KEY ("tenant_id") REFERENCES "public"."core_tenant"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_dependent core_dependent_updated_by_id_c4c6f044_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_dependent"
    ADD CONSTRAINT "core_dependent_updated_by_id_c4c6f044_fk_auth_user_id" FOREIGN KEY ("updated_by_id") REFERENCES "public"."auth_user"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_devicetoken core_devicetoken_created_by_id_ddc63831_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_devicetoken"
    ADD CONSTRAINT "core_devicetoken_created_by_id_ddc63831_fk_auth_user_id" FOREIGN KEY ("created_by_id") REFERENCES "public"."auth_user"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_devicetoken core_devicetoken_updated_by_id_d97de1f7_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_devicetoken"
    ADD CONSTRAINT "core_devicetoken_updated_by_id_d97de1f7_fk_auth_user_id" FOREIGN KEY ("updated_by_id") REFERENCES "public"."auth_user"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_devicetoken core_devicetoken_user_id_479d4f09_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_devicetoken"
    ADD CONSTRAINT "core_devicetoken_user_id_479d4f09_fk_auth_user_id" FOREIGN KEY ("user_id") REFERENCES "public"."auth_user"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_employeepayment core_employeepayment_created_by_id_e6b42255_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_employeepayment"
    ADD CONSTRAINT "core_employeepayment_created_by_id_e6b42255_fk_auth_user_id" FOREIGN KEY ("created_by_id") REFERENCES "public"."auth_user"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_employeepayment core_employeepayment_deleted_by_id_a07b41ff_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_employeepayment"
    ADD CONSTRAINT "core_employeepayment_deleted_by_id_a07b41ff_fk_auth_user_id" FOREIGN KEY ("deleted_by_id") REFERENCES "public"."auth_user"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_employeepayment core_employeepayment_person_id_6404dbbf_fk_core_person_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_employeepayment"
    ADD CONSTRAINT "core_employeepayment_person_id_6404dbbf_fk_core_person_id" FOREIGN KEY ("person_id") REFERENCES "public"."core_person"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_employeepayment core_employeepayment_updated_by_id_c6203d80_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_employeepayment"
    ADD CONSTRAINT "core_employeepayment_updated_by_id_c6203d80_fk_auth_user_id" FOREIGN KEY ("updated_by_id") REFERENCES "public"."auth_user"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_expense core_expense_building_id_bf94522e_fk_core_building_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_expense"
    ADD CONSTRAINT "core_expense_building_id_bf94522e_fk_core_building_id" FOREIGN KEY ("building_id") REFERENCES "public"."core_building"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_expense core_expense_category_id_dcdb74b3_fk_core_expensecategory_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_expense"
    ADD CONSTRAINT "core_expense_category_id_dcdb74b3_fk_core_expensecategory_id" FOREIGN KEY ("category_id") REFERENCES "public"."core_expensecategory"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_expense core_expense_created_by_id_f387daf3_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_expense"
    ADD CONSTRAINT "core_expense_created_by_id_f387daf3_fk_auth_user_id" FOREIGN KEY ("created_by_id") REFERENCES "public"."auth_user"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_expense core_expense_credit_card_id_49386120_fk_core_creditcard_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_expense"
    ADD CONSTRAINT "core_expense_credit_card_id_49386120_fk_core_creditcard_id" FOREIGN KEY ("credit_card_id") REFERENCES "public"."core_creditcard"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_expense core_expense_deleted_by_id_f2737b0a_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_expense"
    ADD CONSTRAINT "core_expense_deleted_by_id_f2737b0a_fk_auth_user_id" FOREIGN KEY ("deleted_by_id") REFERENCES "public"."auth_user"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_expense core_expense_person_id_494927aa_fk_core_person_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_expense"
    ADD CONSTRAINT "core_expense_person_id_494927aa_fk_core_person_id" FOREIGN KEY ("person_id") REFERENCES "public"."core_person"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_expense core_expense_updated_by_id_6316c802_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_expense"
    ADD CONSTRAINT "core_expense_updated_by_id_6316c802_fk_auth_user_id" FOREIGN KEY ("updated_by_id") REFERENCES "public"."auth_user"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_expensecategory core_expensecategory_created_by_id_147adbcf_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_expensecategory"
    ADD CONSTRAINT "core_expensecategory_created_by_id_147adbcf_fk_auth_user_id" FOREIGN KEY ("created_by_id") REFERENCES "public"."auth_user"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_expensecategory core_expensecategory_deleted_by_id_bb1ba135_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_expensecategory"
    ADD CONSTRAINT "core_expensecategory_deleted_by_id_bb1ba135_fk_auth_user_id" FOREIGN KEY ("deleted_by_id") REFERENCES "public"."auth_user"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_expensecategory core_expensecategory_parent_id_823b7351_fk_core_expe; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_expensecategory"
    ADD CONSTRAINT "core_expensecategory_parent_id_823b7351_fk_core_expe" FOREIGN KEY ("parent_id") REFERENCES "public"."core_expensecategory"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_expensecategory core_expensecategory_updated_by_id_631d2c1b_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_expensecategory"
    ADD CONSTRAINT "core_expensecategory_updated_by_id_631d2c1b_fk_auth_user_id" FOREIGN KEY ("updated_by_id") REFERENCES "public"."auth_user"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_expenseinstallment core_expenseinstallment_created_by_id_7fed7a7d_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_expenseinstallment"
    ADD CONSTRAINT "core_expenseinstallment_created_by_id_7fed7a7d_fk_auth_user_id" FOREIGN KEY ("created_by_id") REFERENCES "public"."auth_user"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_expenseinstallment core_expenseinstallment_deleted_by_id_95b9cae6_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_expenseinstallment"
    ADD CONSTRAINT "core_expenseinstallment_deleted_by_id_95b9cae6_fk_auth_user_id" FOREIGN KEY ("deleted_by_id") REFERENCES "public"."auth_user"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_expenseinstallment core_expenseinstallment_expense_id_2bdeacda_fk_core_expense_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_expenseinstallment"
    ADD CONSTRAINT "core_expenseinstallment_expense_id_2bdeacda_fk_core_expense_id" FOREIGN KEY ("expense_id") REFERENCES "public"."core_expense"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_expenseinstallment core_expenseinstallment_updated_by_id_b3ccb642_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_expenseinstallment"
    ADD CONSTRAINT "core_expenseinstallment_updated_by_id_b3ccb642_fk_auth_user_id" FOREIGN KEY ("updated_by_id") REFERENCES "public"."auth_user"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_expensemonthskip core_expensemonthskip_created_by_id_29f4e78c_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_expensemonthskip"
    ADD CONSTRAINT "core_expensemonthskip_created_by_id_29f4e78c_fk_auth_user_id" FOREIGN KEY ("created_by_id") REFERENCES "public"."auth_user"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_expensemonthskip core_expensemonthskip_expense_id_ac188bd0_fk_core_expense_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_expensemonthskip"
    ADD CONSTRAINT "core_expensemonthskip_expense_id_ac188bd0_fk_core_expense_id" FOREIGN KEY ("expense_id") REFERENCES "public"."core_expense"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_expensemonthskip core_expensemonthskip_updated_by_id_6715bdf6_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_expensemonthskip"
    ADD CONSTRAINT "core_expensemonthskip_updated_by_id_6715bdf6_fk_auth_user_id" FOREIGN KEY ("updated_by_id") REFERENCES "public"."auth_user"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_financialsettings core_financialsettings_updated_by_id_d1242b26_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_financialsettings"
    ADD CONSTRAINT "core_financialsettings_updated_by_id_d1242b26_fk_auth_user_id" FOREIGN KEY ("updated_by_id") REFERENCES "public"."auth_user"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_furniture core_furniture_created_by_id_ac6fa2c3_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_furniture"
    ADD CONSTRAINT "core_furniture_created_by_id_ac6fa2c3_fk_auth_user_id" FOREIGN KEY ("created_by_id") REFERENCES "public"."auth_user"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_furniture core_furniture_deleted_by_id_48e626b9_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_furniture"
    ADD CONSTRAINT "core_furniture_deleted_by_id_48e626b9_fk_auth_user_id" FOREIGN KEY ("deleted_by_id") REFERENCES "public"."auth_user"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_furniture core_furniture_updated_by_id_05fc60d9_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_furniture"
    ADD CONSTRAINT "core_furniture_updated_by_id_05fc60d9_fk_auth_user_id" FOREIGN KEY ("updated_by_id") REFERENCES "public"."auth_user"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_income core_income_building_id_76ef9a87_fk_core_building_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_income"
    ADD CONSTRAINT "core_income_building_id_76ef9a87_fk_core_building_id" FOREIGN KEY ("building_id") REFERENCES "public"."core_building"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_income core_income_category_id_03e3d7bb_fk_core_expensecategory_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_income"
    ADD CONSTRAINT "core_income_category_id_03e3d7bb_fk_core_expensecategory_id" FOREIGN KEY ("category_id") REFERENCES "public"."core_expensecategory"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_income core_income_created_by_id_10268b93_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_income"
    ADD CONSTRAINT "core_income_created_by_id_10268b93_fk_auth_user_id" FOREIGN KEY ("created_by_id") REFERENCES "public"."auth_user"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_income core_income_deleted_by_id_eabcd72d_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_income"
    ADD CONSTRAINT "core_income_deleted_by_id_eabcd72d_fk_auth_user_id" FOREIGN KEY ("deleted_by_id") REFERENCES "public"."auth_user"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_income core_income_person_id_4b0c8077_fk_core_person_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_income"
    ADD CONSTRAINT "core_income_person_id_4b0c8077_fk_core_person_id" FOREIGN KEY ("person_id") REFERENCES "public"."core_person"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_income core_income_updated_by_id_71cc281c_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_income"
    ADD CONSTRAINT "core_income_updated_by_id_71cc281c_fk_auth_user_id" FOREIGN KEY ("updated_by_id") REFERENCES "public"."auth_user"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_landlord core_landlord_created_by_id_26771936_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_landlord"
    ADD CONSTRAINT "core_landlord_created_by_id_26771936_fk_auth_user_id" FOREIGN KEY ("created_by_id") REFERENCES "public"."auth_user"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_landlord core_landlord_deleted_by_id_7daf3704_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_landlord"
    ADD CONSTRAINT "core_landlord_deleted_by_id_7daf3704_fk_auth_user_id" FOREIGN KEY ("deleted_by_id") REFERENCES "public"."auth_user"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_landlord core_landlord_updated_by_id_a96c2f8a_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_landlord"
    ADD CONSTRAINT "core_landlord_updated_by_id_a96c2f8a_fk_auth_user_id" FOREIGN KEY ("updated_by_id") REFERENCES "public"."auth_user"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_lease core_lease_apartment_id_f3c48467_fk_core_apartment_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_lease"
    ADD CONSTRAINT "core_lease_apartment_id_f3c48467_fk_core_apartment_id" FOREIGN KEY ("apartment_id") REFERENCES "public"."core_apartment"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_lease core_lease_created_by_id_10d4e47a_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_lease"
    ADD CONSTRAINT "core_lease_created_by_id_10d4e47a_fk_auth_user_id" FOREIGN KEY ("created_by_id") REFERENCES "public"."auth_user"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_lease core_lease_deleted_by_id_a349bea4_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_lease"
    ADD CONSTRAINT "core_lease_deleted_by_id_a349bea4_fk_auth_user_id" FOREIGN KEY ("deleted_by_id") REFERENCES "public"."auth_user"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_lease core_lease_resident_dependent_id_999b3373_fk_core_dependent_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_lease"
    ADD CONSTRAINT "core_lease_resident_dependent_id_999b3373_fk_core_dependent_id" FOREIGN KEY ("resident_dependent_id") REFERENCES "public"."core_dependent"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_lease core_lease_responsible_tenant_id_7048940f_fk_core_tenant_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_lease"
    ADD CONSTRAINT "core_lease_responsible_tenant_id_7048940f_fk_core_tenant_id" FOREIGN KEY ("responsible_tenant_id") REFERENCES "public"."core_tenant"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_lease_tenants core_lease_tenants_lease_id_4e718198_fk_core_lease_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_lease_tenants"
    ADD CONSTRAINT "core_lease_tenants_lease_id_4e718198_fk_core_lease_id" FOREIGN KEY ("lease_id") REFERENCES "public"."core_lease"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_lease_tenants core_lease_tenants_tenant_id_1fe477aa_fk_core_tenant_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_lease_tenants"
    ADD CONSTRAINT "core_lease_tenants_tenant_id_1fe477aa_fk_core_tenant_id" FOREIGN KEY ("tenant_id") REFERENCES "public"."core_tenant"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_lease core_lease_updated_by_id_837ebc4b_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_lease"
    ADD CONSTRAINT "core_lease_updated_by_id_837ebc4b_fk_auth_user_id" FOREIGN KEY ("updated_by_id") REFERENCES "public"."auth_user"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_monthsnapshot core_monthsnapshot_created_by_id_3e18926e_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_monthsnapshot"
    ADD CONSTRAINT "core_monthsnapshot_created_by_id_3e18926e_fk_auth_user_id" FOREIGN KEY ("created_by_id") REFERENCES "public"."auth_user"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_monthsnapshot core_monthsnapshot_updated_by_id_ff44bdc4_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_monthsnapshot"
    ADD CONSTRAINT "core_monthsnapshot_updated_by_id_ff44bdc4_fk_auth_user_id" FOREIGN KEY ("updated_by_id") REFERENCES "public"."auth_user"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_notification core_notification_created_by_id_b954034c_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_notification"
    ADD CONSTRAINT "core_notification_created_by_id_b954034c_fk_auth_user_id" FOREIGN KEY ("created_by_id") REFERENCES "public"."auth_user"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_notification core_notification_recipient_id_24a3d95c_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_notification"
    ADD CONSTRAINT "core_notification_recipient_id_24a3d95c_fk_auth_user_id" FOREIGN KEY ("recipient_id") REFERENCES "public"."auth_user"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_notification core_notification_updated_by_id_10dfda28_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_notification"
    ADD CONSTRAINT "core_notification_updated_by_id_10dfda28_fk_auth_user_id" FOREIGN KEY ("updated_by_id") REFERENCES "public"."auth_user"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_oauth_exchange_code core_oauth_exchange_code_user_id_806380b2_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_oauth_exchange_code"
    ADD CONSTRAINT "core_oauth_exchange_code_user_id_806380b2_fk_auth_user_id" FOREIGN KEY ("user_id") REFERENCES "public"."auth_user"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_paymentproof core_paymentproof_created_by_id_1cfed265_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_paymentproof"
    ADD CONSTRAINT "core_paymentproof_created_by_id_1cfed265_fk_auth_user_id" FOREIGN KEY ("created_by_id") REFERENCES "public"."auth_user"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_paymentproof core_paymentproof_deleted_by_id_6023d639_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_paymentproof"
    ADD CONSTRAINT "core_paymentproof_deleted_by_id_6023d639_fk_auth_user_id" FOREIGN KEY ("deleted_by_id") REFERENCES "public"."auth_user"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_paymentproof core_paymentproof_lease_id_b7a8844e_fk_core_lease_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_paymentproof"
    ADD CONSTRAINT "core_paymentproof_lease_id_b7a8844e_fk_core_lease_id" FOREIGN KEY ("lease_id") REFERENCES "public"."core_lease"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_paymentproof core_paymentproof_reviewed_by_id_1e426c23_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_paymentproof"
    ADD CONSTRAINT "core_paymentproof_reviewed_by_id_1e426c23_fk_auth_user_id" FOREIGN KEY ("reviewed_by_id") REFERENCES "public"."auth_user"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_paymentproof core_paymentproof_updated_by_id_aa748fc5_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_paymentproof"
    ADD CONSTRAINT "core_paymentproof_updated_by_id_aa748fc5_fk_auth_user_id" FOREIGN KEY ("updated_by_id") REFERENCES "public"."auth_user"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_person core_person_created_by_id_47e54549_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_person"
    ADD CONSTRAINT "core_person_created_by_id_47e54549_fk_auth_user_id" FOREIGN KEY ("created_by_id") REFERENCES "public"."auth_user"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_person core_person_deleted_by_id_cc8215b4_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_person"
    ADD CONSTRAINT "core_person_deleted_by_id_cc8215b4_fk_auth_user_id" FOREIGN KEY ("deleted_by_id") REFERENCES "public"."auth_user"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_person core_person_updated_by_id_2c0e591e_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_person"
    ADD CONSTRAINT "core_person_updated_by_id_2c0e591e_fk_auth_user_id" FOREIGN KEY ("updated_by_id") REFERENCES "public"."auth_user"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_person core_person_user_id_3dfe5fcf_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_person"
    ADD CONSTRAINT "core_person_user_id_3dfe5fcf_fk_auth_user_id" FOREIGN KEY ("user_id") REFERENCES "public"."auth_user"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_personincome core_personincome_apartment_id_6d13107c_fk_core_apartment_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_personincome"
    ADD CONSTRAINT "core_personincome_apartment_id_6d13107c_fk_core_apartment_id" FOREIGN KEY ("apartment_id") REFERENCES "public"."core_apartment"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_personincome core_personincome_created_by_id_b232accf_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_personincome"
    ADD CONSTRAINT "core_personincome_created_by_id_b232accf_fk_auth_user_id" FOREIGN KEY ("created_by_id") REFERENCES "public"."auth_user"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_personincome core_personincome_deleted_by_id_f348ffbb_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_personincome"
    ADD CONSTRAINT "core_personincome_deleted_by_id_f348ffbb_fk_auth_user_id" FOREIGN KEY ("deleted_by_id") REFERENCES "public"."auth_user"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_personincome core_personincome_person_id_bff5a221_fk_core_person_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_personincome"
    ADD CONSTRAINT "core_personincome_person_id_bff5a221_fk_core_person_id" FOREIGN KEY ("person_id") REFERENCES "public"."core_person"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_personincome core_personincome_updated_by_id_704816d7_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_personincome"
    ADD CONSTRAINT "core_personincome_updated_by_id_704816d7_fk_auth_user_id" FOREIGN KEY ("updated_by_id") REFERENCES "public"."auth_user"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_personpayment core_personpayment_created_by_id_719a825a_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_personpayment"
    ADD CONSTRAINT "core_personpayment_created_by_id_719a825a_fk_auth_user_id" FOREIGN KEY ("created_by_id") REFERENCES "public"."auth_user"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_personpayment core_personpayment_deleted_by_id_99ec06ff_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_personpayment"
    ADD CONSTRAINT "core_personpayment_deleted_by_id_99ec06ff_fk_auth_user_id" FOREIGN KEY ("deleted_by_id") REFERENCES "public"."auth_user"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_personpayment core_personpayment_person_id_510d65a7_fk_core_person_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_personpayment"
    ADD CONSTRAINT "core_personpayment_person_id_510d65a7_fk_core_person_id" FOREIGN KEY ("person_id") REFERENCES "public"."core_person"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_personpayment core_personpayment_updated_by_id_1d230c37_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_personpayment"
    ADD CONSTRAINT "core_personpayment_updated_by_id_1d230c37_fk_auth_user_id" FOREIGN KEY ("updated_by_id") REFERENCES "public"."auth_user"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_personpaymentschedule core_personpaymentsc_created_by_id_5524466f_fk_auth_user; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_personpaymentschedule"
    ADD CONSTRAINT "core_personpaymentsc_created_by_id_5524466f_fk_auth_user" FOREIGN KEY ("created_by_id") REFERENCES "public"."auth_user"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_personpaymentschedule core_personpaymentsc_deleted_by_id_6b831031_fk_auth_user; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_personpaymentschedule"
    ADD CONSTRAINT "core_personpaymentsc_deleted_by_id_6b831031_fk_auth_user" FOREIGN KEY ("deleted_by_id") REFERENCES "public"."auth_user"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_personpaymentschedule core_personpaymentsc_updated_by_id_a6fcae64_fk_auth_user; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_personpaymentschedule"
    ADD CONSTRAINT "core_personpaymentsc_updated_by_id_a6fcae64_fk_auth_user" FOREIGN KEY ("updated_by_id") REFERENCES "public"."auth_user"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_personpaymentschedule core_personpaymentschedule_person_id_364d7616_fk_core_person_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_personpaymentschedule"
    ADD CONSTRAINT "core_personpaymentschedule_person_id_364d7616_fk_core_person_id" FOREIGN KEY ("person_id") REFERENCES "public"."core_person"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_rentadjustment core_rentadjustment_created_by_id_70b404e3_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_rentadjustment"
    ADD CONSTRAINT "core_rentadjustment_created_by_id_70b404e3_fk_auth_user_id" FOREIGN KEY ("created_by_id") REFERENCES "public"."auth_user"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_rentadjustment core_rentadjustment_deleted_by_id_4b51a341_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_rentadjustment"
    ADD CONSTRAINT "core_rentadjustment_deleted_by_id_4b51a341_fk_auth_user_id" FOREIGN KEY ("deleted_by_id") REFERENCES "public"."auth_user"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_rentadjustment core_rentadjustment_lease_id_49b5f5c0_fk_core_lease_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_rentadjustment"
    ADD CONSTRAINT "core_rentadjustment_lease_id_49b5f5c0_fk_core_lease_id" FOREIGN KEY ("lease_id") REFERENCES "public"."core_lease"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_rentadjustment core_rentadjustment_updated_by_id_d57f9608_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_rentadjustment"
    ADD CONSTRAINT "core_rentadjustment_updated_by_id_d57f9608_fk_auth_user_id" FOREIGN KEY ("updated_by_id") REFERENCES "public"."auth_user"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_rentpayment core_rentpayment_created_by_id_78b62bf5_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_rentpayment"
    ADD CONSTRAINT "core_rentpayment_created_by_id_78b62bf5_fk_auth_user_id" FOREIGN KEY ("created_by_id") REFERENCES "public"."auth_user"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_rentpayment core_rentpayment_deleted_by_id_c6bc4999_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_rentpayment"
    ADD CONSTRAINT "core_rentpayment_deleted_by_id_c6bc4999_fk_auth_user_id" FOREIGN KEY ("deleted_by_id") REFERENCES "public"."auth_user"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_rentpayment core_rentpayment_lease_id_a1c2bf37_fk_core_lease_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_rentpayment"
    ADD CONSTRAINT "core_rentpayment_lease_id_a1c2bf37_fk_core_lease_id" FOREIGN KEY ("lease_id") REFERENCES "public"."core_lease"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_rentpayment core_rentpayment_updated_by_id_bef14fbe_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_rentpayment"
    ADD CONSTRAINT "core_rentpayment_updated_by_id_bef14fbe_fk_auth_user_id" FOREIGN KEY ("updated_by_id") REFERENCES "public"."auth_user"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_tenant core_tenant_created_by_id_c9f39c01_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_tenant"
    ADD CONSTRAINT "core_tenant_created_by_id_c9f39c01_fk_auth_user_id" FOREIGN KEY ("created_by_id") REFERENCES "public"."auth_user"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_tenant core_tenant_deleted_by_id_3ff8f8bb_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_tenant"
    ADD CONSTRAINT "core_tenant_deleted_by_id_3ff8f8bb_fk_auth_user_id" FOREIGN KEY ("deleted_by_id") REFERENCES "public"."auth_user"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_tenant_furnitures core_tenant_furnitur_furniture_id_b38a2b66_fk_core_furn; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_tenant_furnitures"
    ADD CONSTRAINT "core_tenant_furnitur_furniture_id_b38a2b66_fk_core_furn" FOREIGN KEY ("furniture_id") REFERENCES "public"."core_furniture"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_tenant_furnitures core_tenant_furnitures_tenant_id_a5273f50_fk_core_tenant_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_tenant_furnitures"
    ADD CONSTRAINT "core_tenant_furnitures_tenant_id_a5273f50_fk_core_tenant_id" FOREIGN KEY ("tenant_id") REFERENCES "public"."core_tenant"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_tenant core_tenant_updated_by_id_a39a25ef_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_tenant"
    ADD CONSTRAINT "core_tenant_updated_by_id_a39a25ef_fk_auth_user_id" FOREIGN KEY ("updated_by_id") REFERENCES "public"."auth_user"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: core_tenant core_tenant_user_id_6a06dd7c_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."core_tenant"
    ADD CONSTRAINT "core_tenant_user_id_6a06dd7c_fk_auth_user_id" FOREIGN KEY ("user_id") REFERENCES "public"."auth_user"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: django_admin_log django_admin_log_content_type_id_c4bce8eb_fk_django_co; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."django_admin_log"
    ADD CONSTRAINT "django_admin_log_content_type_id_c4bce8eb_fk_django_co" FOREIGN KEY ("content_type_id") REFERENCES "public"."django_content_type"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: django_admin_log django_admin_log_user_id_c564eba6_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."django_admin_log"
    ADD CONSTRAINT "django_admin_log_user_id_c564eba6_fk_auth_user_id" FOREIGN KEY ("user_id") REFERENCES "public"."auth_user"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: socialaccount_socialtoken socialaccount_social_account_id_951f210e_fk_socialacc; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."socialaccount_socialtoken"
    ADD CONSTRAINT "socialaccount_social_account_id_951f210e_fk_socialacc" FOREIGN KEY ("account_id") REFERENCES "public"."socialaccount_socialaccount"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: socialaccount_socialtoken socialaccount_social_app_id_636a42d7_fk_socialacc; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."socialaccount_socialtoken"
    ADD CONSTRAINT "socialaccount_social_app_id_636a42d7_fk_socialacc" FOREIGN KEY ("app_id") REFERENCES "public"."socialaccount_socialapp"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: socialaccount_socialapp_sites socialaccount_social_site_id_2579dee5_fk_django_si; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."socialaccount_socialapp_sites"
    ADD CONSTRAINT "socialaccount_social_site_id_2579dee5_fk_django_si" FOREIGN KEY ("site_id") REFERENCES "public"."django_site"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: socialaccount_socialapp_sites socialaccount_social_socialapp_id_97fb6e7d_fk_socialacc; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."socialaccount_socialapp_sites"
    ADD CONSTRAINT "socialaccount_social_socialapp_id_97fb6e7d_fk_socialacc" FOREIGN KEY ("socialapp_id") REFERENCES "public"."socialaccount_socialapp"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: socialaccount_socialaccount socialaccount_socialaccount_user_id_8146e70c_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."socialaccount_socialaccount"
    ADD CONSTRAINT "socialaccount_socialaccount_user_id_8146e70c_fk_auth_user_id" FOREIGN KEY ("user_id") REFERENCES "public"."auth_user"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: token_blacklist_blacklistedtoken token_blacklist_blacklistedtoken_token_id_3cc7fe56_fk; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."token_blacklist_blacklistedtoken"
    ADD CONSTRAINT "token_blacklist_blacklistedtoken_token_id_3cc7fe56_fk" FOREIGN KEY ("token_id") REFERENCES "public"."token_blacklist_outstandingtoken"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- Name: token_blacklist_outstandingtoken token_blacklist_outs_user_id_83bc629a_fk_auth_user; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY "public"."token_blacklist_outstandingtoken"
    ADD CONSTRAINT "token_blacklist_outs_user_id_83bc629a_fk_auth_user" FOREIGN KEY ("user_id") REFERENCES "public"."auth_user"("id") DEFERRABLE INITIALLY DEFERRED;


--
-- PostgreSQL database dump complete
--

\unrestrict ORJe4op3AfVBI50oMjD6Rq7AVdfVsNqbvN3GKyehZRd3UPM4hdIpNi4MKFP743l

