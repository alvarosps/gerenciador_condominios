"""Session 80 — third-party API: settlements CRUD, purchases, statement, extended pay.

Everything goes over HTTP against the real ORM (no internal mocking). Money figures are
computed by hand in the test, never re-derived from the service's own formula.

Condominium: every test uses ``Condominium.get_default()`` — the migration-created row. A
factory-made condominium is never the default, so ``third-party/statement`` (which defaults
to the singleton) would come back empty and the assertions would silently test nothing.
"""

from datetime import date
from decimal import Decimal

import pytest
from freezegun import freeze_time
from rest_framework import status

from core.models import Condominium, Person
from finances.models import (
    Bill,
    BillLifecycleState,
    FundedFrom,
    Payment,
    PaymentAllocation,
    ThirdPartySettlement,
)
from finances.services.condo_balance_service import CondoBalanceService
from tests.factories import (
    make_bill,
    make_bill_line_item,
    make_condo_month_close,
    make_installment,
    make_installment_plan,
    make_person,
)

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

FROZEN = "2026-07-15 12:00:00"
JUNE = "2026-06-01"
JULY = "2026-07-01"

SETTLEMENTS_URL = "/api/finances/third-party-settlements/"
PEOPLE_URL = "/api/finances/third-party/people/"
STATEMENT_URL = "/api/finances/third-party/statement/"
CREATE_PURCHASE_URL = "/api/finances/bills/create_purchase/"


@pytest.fixture
def condominium() -> Condominium:
    default = Condominium.get_default()
    assert default is not None
    return default


@pytest.fixture
def person() -> Person:
    return make_person(name="Alvaro Terceiro")


@pytest.fixture
def other_person() -> Person:
    return make_person(name="Celia Terceira")


def _purchase_payload(person: Person, **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "person_id": person.pk,
        "description": "Material de obra",
        "amount": "300.00",
        "competence_month": JUNE,
        "due_date": "2026-06-20",
    }
    payload.update(overrides)
    return payload


def _plain_bill(condominium: Condominium, amount: str = "500.00") -> Bill:
    bill = make_bill(condominium=condominium, competence_month=date(2026, 6, 1))
    make_bill_line_item(bill=bill, amount=Decimal(amount))
    return bill


def _close_month(condominium: Condominium, reference_month: date) -> None:
    make_condo_month_close(
        condominium=condominium, reference_month=reference_month, status="closed"
    )


# --------------------------------------------------------------------------------------
# 1. ThirdPartySettlement CRUD
# --------------------------------------------------------------------------------------


@freeze_time(FROZEN)
def test_settlement_crud_roundtrip(authenticated_api_client, condominium, person):
    created = authenticated_api_client.post(
        SETTLEMENTS_URL,
        {
            "person_id": person.pk,
            "settlement_date": "2026-07-05",
            "amount": "250.00",
            "method": "PIX",
        },
        format="json",
    )
    assert created.status_code == status.HTTP_201_CREATED
    assert created.data["person"]["id"] == person.pk
    assert created.data["amount"] == "250.00"
    settlement_id = created.data["id"]

    listed = authenticated_api_client.get(SETTLEMENTS_URL)
    assert listed.status_code == status.HTTP_200_OK
    assert [row["id"] for row in listed.data["results"]] == [settlement_id]

    retrieved = authenticated_api_client.get(f"{SETTLEMENTS_URL}{settlement_id}/")
    assert retrieved.status_code == status.HTTP_200_OK
    assert retrieved.data["method"] == "PIX"

    updated = authenticated_api_client.patch(
        f"{SETTLEMENTS_URL}{settlement_id}/", {"amount": "300.00"}, format="json"
    )
    assert updated.status_code == status.HTTP_200_OK
    assert updated.data["amount"] == "300.00"

    deleted = authenticated_api_client.delete(f"{SETTLEMENTS_URL}{settlement_id}/")
    assert deleted.status_code == status.HTTP_204_NO_CONTENT
    assert ThirdPartySettlement.objects.count() == 0
    assert ThirdPartySettlement.all_objects.get(pk=settlement_id).is_deleted is True


@freeze_time(FROZEN)
def test_settlement_rejects_non_positive_amount(authenticated_api_client, person):
    response = authenticated_api_client.post(
        SETTLEMENTS_URL,
        {"person_id": person.pk, "settlement_date": "2026-07-05", "amount": "0.00"},
        format="json",
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "amount" in response.data
    assert ThirdPartySettlement.objects.count() == 0


@freeze_time(FROZEN)
def test_settlement_requires_person(authenticated_api_client):
    response = authenticated_api_client.post(
        SETTLEMENTS_URL, {"settlement_date": "2026-07-05", "amount": "10.00"}, format="json"
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "person_id" in response.data


@freeze_time(FROZEN)
def test_settlement_closed_month_rejected_on_create_update_and_delete(
    authenticated_api_client, condominium, person, admin_user
):
    _close_month(condominium, date(2026, 5, 1))

    blocked = authenticated_api_client.post(
        SETTLEMENTS_URL,
        {"person_id": person.pk, "settlement_date": "2026-05-10", "amount": "100.00"},
        format="json",
    )
    assert blocked.status_code == status.HTTP_400_BAD_REQUEST
    assert "fechado" in str(blocked.data)
    assert ThirdPartySettlement.objects.count() == 0

    live = ThirdPartySettlement.objects.create(
        condominium=condominium,
        person=person,
        settlement_date=date(2026, 5, 20),
        amount=Decimal("80.00"),
        created_by=admin_user,
        updated_by=admin_user,
    )
    patched = authenticated_api_client.patch(
        f"{SETTLEMENTS_URL}{live.pk}/", {"amount": "90.00"}, format="json"
    )
    assert patched.status_code == status.HTTP_400_BAD_REQUEST
    live.refresh_from_db()
    assert live.amount == Decimal("80.00")

    removed = authenticated_api_client.delete(f"{SETTLEMENTS_URL}{live.pk}/")
    assert removed.status_code == status.HTTP_400_BAD_REQUEST
    live.refresh_from_db()
    assert live.is_deleted is False


@freeze_time(FROZEN)
def test_settlement_moving_out_of_open_into_closed_month_rejected(
    authenticated_api_client, condominium, person, admin_user
):
    _close_month(condominium, date(2026, 5, 1))
    live = ThirdPartySettlement.objects.create(
        condominium=condominium,
        person=person,
        settlement_date=date(2026, 7, 5),
        amount=Decimal("80.00"),
        created_by=admin_user,
        updated_by=admin_user,
    )
    response = authenticated_api_client.patch(
        f"{SETTLEMENTS_URL}{live.pk}/", {"settlement_date": "2026-05-05"}, format="json"
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    live.refresh_from_db()
    assert live.settlement_date == date(2026, 7, 5)


# --------------------------------------------------------------------------------------
# 2. Permissions
# --------------------------------------------------------------------------------------


NEW_WRITE_ENDPOINTS = [
    ("post", SETTLEMENTS_URL),
    ("post", CREATE_PURCHASE_URL),
    ("post", "/api/finances/bills/1/reassign_payer/"),
    ("delete", "/api/finances/bills/1/delete_purchase/"),
    ("delete", f"{SETTLEMENTS_URL}1/"),
]

NEW_READ_ENDPOINTS = [SETTLEMENTS_URL, PEOPLE_URL, STATEMENT_URL]


@pytest.mark.parametrize(("method", "url"), NEW_WRITE_ENDPOINTS)
def test_non_admin_cannot_write_third_party(regular_authenticated_api_client, method, url):
    response = getattr(regular_authenticated_api_client, method)(url, {}, format="json")
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.parametrize("url", NEW_READ_ENDPOINTS)
def test_non_admin_cannot_read_third_party(regular_authenticated_api_client, url):
    assert regular_authenticated_api_client.get(url).status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.parametrize("url", NEW_READ_ENDPOINTS)
def test_unauthenticated_cannot_read_third_party(api_client, url):
    assert api_client.get(url).status_code == status.HTTP_401_UNAUTHORIZED


# --------------------------------------------------------------------------------------
# 3. pay / bulk_pay extended with paid_by_person_id
# --------------------------------------------------------------------------------------


@freeze_time(FROZEN)
def test_pay_third_party_without_person_rejected(authenticated_api_client, condominium):
    bill = _plain_bill(condominium)
    response = authenticated_api_client.post(
        f"/api/finances/bills/{bill.pk}/pay/",
        {"payment_date": "2026-07-05", "funded_from": "third_party"},
        format="json",
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "error" in response.data
    assert "pessoa" in response.data["error"].lower()
    assert Payment.objects.count() == 0


@freeze_time(FROZEN)
def test_pay_third_party_with_unknown_person_is_400_not_500(authenticated_api_client, condominium):
    bill = _plain_bill(condominium)
    response = authenticated_api_client.post(
        f"/api/finances/bills/{bill.pk}/pay/",
        {"payment_date": "2026-07-05", "funded_from": "third_party", "paid_by_person_id": 999999},
        format="json",
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert Payment.objects.count() == 0


@freeze_time(FROZEN)
def test_pay_third_party_succeeds_and_leaves_cash_untouched(
    authenticated_api_client, condominium, person
):
    bill = _plain_bill(condominium, "500.00")
    cash_before = CondoBalanceService.cash_balance()

    response = authenticated_api_client.post(
        f"/api/finances/bills/{bill.pk}/pay/",
        {
            "payment_date": "2026-07-05",
            "funded_from": "third_party",
            "paid_by_person_id": person.pk,
        },
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.data["payment_status"] == "paid"

    payment = Payment.objects.get()
    assert payment.funded_from == FundedFrom.THIRD_PARTY
    assert payment.paid_by_id == person.pk
    assert CondoBalanceService.cash_balance() == cash_before


@freeze_time(FROZEN)
def test_pay_caixa_with_person_rejected(authenticated_api_client, condominium, person):
    bill = _plain_bill(condominium)
    response = authenticated_api_client.post(
        f"/api/finances/bills/{bill.pk}/pay/",
        {"payment_date": "2026-07-05", "funded_from": "caixa", "paid_by_person_id": person.pk},
        format="json",
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert Payment.objects.count() == 0


@freeze_time(FROZEN)
def test_bulk_pay_third_party_without_person_rejected(authenticated_api_client, condominium):
    bill = _plain_bill(condominium)
    response = authenticated_api_client.post(
        "/api/finances/bills/bulk_pay/",
        {"bill_ids": [bill.pk], "payment_date": "2026-07-05", "funded_from": "third_party"},
        format="json",
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "pessoa" in response.data["error"].lower()
    assert Payment.objects.count() == 0


@freeze_time(FROZEN)
def test_bulk_pay_third_party_assigns_every_bill_to_the_same_person(
    authenticated_api_client, condominium, person
):
    first = _plain_bill(condominium, "100.00")
    second = _plain_bill(condominium, "200.00")
    response = authenticated_api_client.post(
        "/api/finances/bills/bulk_pay/",
        {
            "bill_ids": [first.pk, second.pk],
            "payment_date": "2026-07-05",
            "funded_from": "third_party",
            "paid_by_person_id": person.pk,
        },
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK
    assert Payment.objects.count() == 2
    assert {payment.paid_by_id for payment in Payment.objects.all()} == {person.pk}


# --------------------------------------------------------------------------------------
# 4. create_purchase
# --------------------------------------------------------------------------------------


@freeze_time(FROZEN)
def test_create_purchase_births_paid_and_leaves_cash_untouched(
    authenticated_api_client, condominium, person
):
    cash_before = CondoBalanceService.cash_balance()
    response = authenticated_api_client.post(
        CREATE_PURCHASE_URL, _purchase_payload(person), format="json"
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert response.data[0]["payment_status"] == "paid"
    assert response.data[0]["amount_total"] == "300.00"
    assert response.data[0]["paid_by_person"]["id"] == person.pk

    bill = Bill.objects.get()
    assert bill.paid_by_person_id == person.pk
    assert bill.competence_month == date(2026, 6, 1)
    payment = Payment.objects.get()
    assert payment.funded_from == FundedFrom.THIRD_PARTY
    assert payment.paid_by_id == person.pk
    assert payment.amount == Decimal("300.00")
    assert CondoBalanceService.cash_balance() == cash_before


@freeze_time(FROZEN)
def test_create_purchase_rolls_back_completely_on_failure(
    authenticated_api_client, condominium, person
):
    # amount 0 makes the Payment step fail (a payment must be positive) AFTER the Bill was
    # created inside the same transaction — nothing may survive.
    response = authenticated_api_client.post(
        CREATE_PURCHASE_URL, _purchase_payload(person, amount="0.00"), format="json"
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert Bill.objects.count() == 0
    assert Bill.all_objects.count() == 0
    assert Payment.objects.count() == 0


@freeze_time(FROZEN)
def test_create_purchase_closed_competence_month_names_the_month(
    authenticated_api_client, condominium, person
):
    _close_month(condominium, date(2026, 6, 1))
    response = authenticated_api_client.post(
        CREATE_PURCHASE_URL,
        _purchase_payload(person, competence_month=JUNE, due_date="2026-07-20"),
        format="json",
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "06/2026" in response.data["error"]
    assert Bill.objects.count() == 0


@freeze_time(FROZEN)
def test_create_purchase_open_competence_but_closed_cash_month_names_the_cash_month(
    authenticated_api_client, condominium, person
):
    _close_month(condominium, date(2026, 5, 1))
    response = authenticated_api_client.post(
        CREATE_PURCHASE_URL,
        _purchase_payload(person, competence_month=JUNE, due_date="2026-05-20"),
        format="json",
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "05/2026" in response.data["error"]
    assert Bill.objects.count() == 0


@freeze_time(FROZEN)
def test_create_purchase_unknown_person_is_400(authenticated_api_client, condominium):
    response = authenticated_api_client.post(
        CREATE_PURCHASE_URL,
        {
            "person_id": 999999,
            "description": "Compra",
            "amount": "100.00",
            "competence_month": JUNE,
            "due_date": "2026-06-20",
        },
        format="json",
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert Bill.objects.count() == 0


@freeze_time(FROZEN)
def test_create_purchase_in_three_installments_sums_to_the_exact_total(
    authenticated_api_client, condominium, person
):
    response = authenticated_api_client.post(
        CREATE_PURCHASE_URL,
        _purchase_payload(person, amount="100.00", installment_count=3),
        format="json",
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert len(response.data) == 3

    bills = list(Bill.objects.order_by("competence_month"))
    assert [bill.competence_month for bill in bills] == [
        date(2026, 6, 1),
        date(2026, 7, 1),
        date(2026, 8, 1),
    ]
    assert [bill.description for bill in bills] == [
        "Material de obra (1/3)",
        "Material de obra (2/3)",
        "Material de obra (3/3)",
    ]
    # 100.00 / 3 = 33.33 with a 0.01 remainder on the FIRST parcela.
    amounts = sorted(payment.amount for payment in Payment.objects.all())
    assert amounts == [Decimal("33.33"), Decimal("33.33"), Decimal("33.34")]
    assert sum(amounts) == Decimal("100.00")
    assert all(bill.installment_id is None for bill in bills)
    assert all(bill.paid_by_person_id == person.pk for bill in bills)
    # every parcela is born fully paid
    assert Payment.objects.count() == 3
    assert PaymentAllocation.objects.count() == 3


@freeze_time(FROZEN)
def test_create_purchase_installments_reject_everything_when_one_month_is_closed(
    authenticated_api_client, condominium, person
):
    _close_month(condominium, date(2026, 8, 1))
    response = authenticated_api_client.post(
        CREATE_PURCHASE_URL,
        _purchase_payload(person, amount="100.00", installment_count=3),
        format="json",
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "08/2026" in response.data["error"]
    assert Bill.objects.count() == 0
    assert Payment.objects.count() == 0


@freeze_time(FROZEN)
def test_create_purchase_rejects_invalid_installment_count(
    authenticated_api_client, condominium, person
):
    response = authenticated_api_client.post(
        CREATE_PURCHASE_URL,
        _purchase_payload(person, installment_count=0),
        format="json",
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert Bill.objects.count() == 0


# --------------------------------------------------------------------------------------
# 5. Lifecycle: unpay / delete_purchase / reassign_payer (§4b)
# --------------------------------------------------------------------------------------


def _create_purchase(client, person, **overrides: object) -> int:
    response = client.post(
        CREATE_PURCHASE_URL, _purchase_payload(person, **overrides), format="json"
    )
    assert response.status_code == status.HTTP_201_CREATED
    return int(response.data[0]["id"])


@freeze_time(FROZEN)
def test_unpay_of_a_purchase_payment_is_rejected(authenticated_api_client, condominium, person):
    bill_id = _create_purchase(authenticated_api_client, person)
    payment = Payment.objects.get()

    response = authenticated_api_client.delete(f"/api/finances/payments/{payment.pk}/")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "compra de terceiro" in response.data["error"].lower()

    payment.refresh_from_db()
    assert payment.is_deleted is False
    assert PaymentAllocation.objects.filter(bill_id=bill_id).count() == 1
    listed = authenticated_api_client.get(f"/api/finances/bills/{bill_id}/")
    assert listed.data["payment_status"] == "paid"


@freeze_time(FROZEN)
def test_delete_purchase_removes_bill_and_payment_atomically(
    authenticated_api_client, condominium, person
):
    bill_id = _create_purchase(authenticated_api_client, person)

    response = authenticated_api_client.delete(f"/api/finances/bills/{bill_id}/delete_purchase/")
    assert response.status_code == status.HTTP_204_NO_CONTENT

    assert Bill.objects.filter(pk=bill_id).count() == 0
    assert Bill.all_objects.get(pk=bill_id).is_deleted is True
    assert Payment.objects.count() == 0
    assert PaymentAllocation.objects.count() == 0

    statement = authenticated_api_client.get(f"{STATEMENT_URL}?person_id={person.pk}")
    assert statement.data["totals"]["total_em_aberto"] == "0.00"


@freeze_time(FROZEN)
def test_delete_purchase_rejects_a_bill_that_is_not_a_purchase(
    authenticated_api_client, condominium
):
    bill = _plain_bill(condominium)
    response = authenticated_api_client.delete(f"/api/finances/bills/{bill.pk}/delete_purchase/")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert Bill.objects.filter(pk=bill.pk).exists()


@freeze_time(FROZEN)
def test_delete_purchase_rejected_in_a_closed_month(authenticated_api_client, condominium, person):
    bill_id = _create_purchase(authenticated_api_client, person)
    _close_month(condominium, date(2026, 6, 1))

    response = authenticated_api_client.delete(f"/api/finances/bills/{bill_id}/delete_purchase/")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert Bill.objects.filter(pk=bill_id).exists()
    assert Payment.objects.count() == 1


@freeze_time(FROZEN)
def test_reassign_payer_moves_both_sides(
    authenticated_api_client, condominium, person, other_person
):
    bill_id = _create_purchase(authenticated_api_client, person)

    response = authenticated_api_client.post(
        f"/api/finances/bills/{bill_id}/reassign_payer/",
        {"paid_by_person_id": other_person.pk},
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.data["paid_by_person"]["id"] == other_person.pk

    assert Bill.objects.get(pk=bill_id).paid_by_person_id == other_person.pk
    assert Payment.objects.get().paid_by_id == other_person.pk

    old = authenticated_api_client.get(f"{STATEMENT_URL}?person_id={person.pk}")
    assert old.data["totals"]["total_devido"] == "0.00"
    new = authenticated_api_client.get(f"{STATEMENT_URL}?person_id={other_person.pk}")
    assert new.data["totals"]["total_devido"] == "300.00"


@freeze_time(FROZEN)
def test_reassign_payer_rejects_a_bill_that_is_not_a_purchase(
    authenticated_api_client, condominium, person
):
    bill = _plain_bill(condominium)
    response = authenticated_api_client.post(
        f"/api/finances/bills/{bill.pk}/reassign_payer/",
        {"paid_by_person_id": person.pk},
        format="json",
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@freeze_time(FROZEN)
def test_reassign_payer_rejects_unknown_person(authenticated_api_client, condominium, person):
    bill_id = _create_purchase(authenticated_api_client, person)
    response = authenticated_api_client.post(
        f"/api/finances/bills/{bill_id}/reassign_payer/",
        {"paid_by_person_id": 999999},
        format="json",
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert Bill.objects.get(pk=bill_id).paid_by_person_id == person.pk


# --------------------------------------------------------------------------------------
# 6. Read actions: people / statement
# --------------------------------------------------------------------------------------


@freeze_time(FROZEN)
def test_statement_requires_a_valid_person_id(authenticated_api_client):
    missing = authenticated_api_client.get(STATEMENT_URL)
    assert missing.status_code == status.HTTP_400_BAD_REQUEST
    assert "error" in missing.data

    unknown = authenticated_api_client.get(f"{STATEMENT_URL}?person_id=999999")
    assert unknown.status_code == status.HTTP_400_BAD_REQUEST

    not_a_number = authenticated_api_client.get(f"{STATEMENT_URL}?person_id=abc")
    assert not_a_number.status_code == status.HTTP_400_BAD_REQUEST


@freeze_time(FROZEN)
def test_statement_reflects_a_settlement_immediately(authenticated_api_client, condominium, person):
    _create_purchase(authenticated_api_client, person)
    before = authenticated_api_client.get(f"{STATEMENT_URL}?person_id={person.pk}")
    assert before.data["totals"]["total_em_aberto"] == "300.00"

    authenticated_api_client.post(
        SETTLEMENTS_URL,
        {"person_id": person.pk, "settlement_date": "2026-07-05", "amount": "120.00"},
        format="json",
    )
    after = authenticated_api_client.get(f"{STATEMENT_URL}?person_id={person.pk}")
    assert after.data["totals"]["total_em_aberto"] == "180.00"
    assert after.data["person_name"] == "Alvaro Terceiro"


@freeze_time(FROZEN)
def test_people_orders_by_open_debt_desc_and_omits_whoever_owes_nothing(
    authenticated_api_client, condominium, person, other_person
):
    make_person(name="Sem Divida")
    _create_purchase(authenticated_api_client, person, amount="100.00")
    _create_purchase(authenticated_api_client, other_person, amount="500.00")
    authenticated_api_client.post(
        SETTLEMENTS_URL,
        {"person_id": other_person.pk, "settlement_date": "2026-07-05", "amount": "50.00"},
        format="json",
    )

    response = authenticated_api_client.get(PEOPLE_URL)
    assert response.status_code == status.HTTP_200_OK
    rows = response.data
    assert [row["person_id"] for row in rows] == [other_person.pk, person.pk]
    assert rows[0]["total_em_aberto"] == "450.00"
    # A compra é de JUNHO e o acerto de 05/07 já foi feito (hoje 15/07), então ele abate junho
    # (design §6.2, rev. 3) e o que sobra dele — 450 — está atrasado por inteiro. Antes da rev. 3
    # o acerto não alcançava junho e ficava pendurado em saldo_credor.
    assert rows[0]["total_atrasado"] == "450.00"
    assert rows[0]["last_settlement_date"] == date(2026, 7, 5)
    assert rows[1]["total_em_aberto"] == "100.00"
    assert rows[1]["last_settlement_date"] is None
    assert all(row["person_name"] != "Sem Divida" for row in rows)


@freeze_time(FROZEN)
def test_people_omits_a_fully_settled_person(authenticated_api_client, condominium, person):
    _create_purchase(authenticated_api_client, person, amount="100.00")
    authenticated_api_client.post(
        SETTLEMENTS_URL,
        {"person_id": person.pk, "settlement_date": "2026-06-05", "amount": "100.00"},
        format="json",
    )
    response = authenticated_api_client.get(PEOPLE_URL)
    assert response.data == []


# --------------------------------------------------------------------------------------
# 7. BillSerializer.paid_by_person (§3b)
# --------------------------------------------------------------------------------------


@freeze_time(FROZEN)
def test_month_board_exposes_paid_by_person_without_n_plus_one(
    authenticated_api_client, condominium, person, django_assert_num_queries
):
    _plain_bill(condominium)
    _create_purchase(authenticated_api_client, person, competence_month=JUNE)

    response = authenticated_api_client.get(
        "/api/finances/finance-dashboard/month_board/?year=2026&month=6"
    )
    assert response.status_code == status.HTTP_200_OK
    bills = [bill for group in response.data["groups"] for bill in group["bills"]]
    by_person = [bill["paid_by_person"] for bill in bills]
    assert any(value is not None and value["id"] == person.pk for value in by_person)
    assert any(value is None for value in by_person)


@freeze_time(FROZEN)
def test_bill_list_query_count_does_not_grow_with_purchases(
    authenticated_api_client, condominium, person, django_assert_max_num_queries
):
    _create_purchase(authenticated_api_client, person, competence_month=JUNE)
    with django_assert_max_num_queries(30) as captured:
        authenticated_api_client.get("/api/finances/bills/")
    baseline = len(captured.captured_queries)

    for _ in range(4):
        _create_purchase(authenticated_api_client, make_person(), competence_month=JUNE)
    with django_assert_max_num_queries(baseline) as second:
        authenticated_api_client.get("/api/finances/bills/")
    assert len(second.captured_queries) <= baseline


# --------------------------------------------------------------------------------------
# 8. §3c — editing billing_account on an installment bill
# --------------------------------------------------------------------------------------


@freeze_time(FROZEN)
def test_update_with_lines_rejects_changing_billing_account_of_an_installment_bill(
    authenticated_api_client, condominium
):
    plan = make_installment_plan(condominium=condominium)
    installment = make_installment(plan=plan)
    bill = make_bill(
        condominium=condominium,
        installment=installment,
        competence_month=date(2026, 6, 1),
        behavior="installment",
    )
    make_bill_line_item(bill=bill, amount=Decimal("100.00"))
    from tests.factories import make_billing_account

    account = make_billing_account(condominium=condominium)

    response = authenticated_api_client.post(
        f"/api/finances/bills/{bill.pk}/update_with_lines/",
        {
            "bill": {
                "competence_month": "2026-06-01",
                "due_date": "2026-06-10",
                "description": "Parcela",
                "behavior": "installment",
                "billing_account_id": account.pk,
            },
            "line_items": [{"description": "Linha", "amount": "100.00"}],
        },
        format="json",
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "parcela" in response.data["error"].lower()
    bill.refresh_from_db()
    assert bill.billing_account_id is None


@freeze_time(FROZEN)
def test_purchase_bill_cannot_be_canceled_but_can_be_deleted_as_purchase(
    authenticated_api_client, condominium, person
):
    """assert_not_paid still guards the ordinary lifecycle — delete_purchase is the only path."""
    bill_id = _create_purchase(authenticated_api_client, person)
    canceled = authenticated_api_client.post(f"/api/finances/bills/{bill_id}/cancel/")
    assert canceled.status_code == status.HTTP_400_BAD_REQUEST
    assert Bill.objects.get(pk=bill_id).lifecycle_state == BillLifecycleState.ACTIVE

    deleted = authenticated_api_client.delete(f"/api/finances/bills/{bill_id}/delete_purchase/")
    assert deleted.status_code == status.HTTP_204_NO_CONTENT
