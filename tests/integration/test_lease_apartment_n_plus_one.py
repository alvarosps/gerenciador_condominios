"""P5.1: the leases + apartments list endpoints resolve apartment.owner and active_lease
without N+1, after removing the dead tenants__dependents/tenants__furnitures prefetches.

Gold-standard assertion: query count must be IDENTICAL for a small and a larger set.
"""

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from tests.factories import make_apartment, make_building, make_lease, make_person

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

LEASES_URL = "/api/leases/"
APARTMENTS_URL = "/api/apartments/"


def _make_lease_with_owned_apartment(index: int):
    building = make_building(street_number=8200 + index)
    apartment = make_apartment(
        building=building, number=500 + index, owner=make_person(name=f"Owner {index}")
    )
    return make_lease(apartment=apartment)


def _count_queries(client, url: str) -> int:
    with CaptureQueriesContext(connection) as ctx:
        response = client.get(url)
    assert response.status_code == 200
    return len(ctx)


def test_lease_list_no_n_plus_one(authenticated_api_client):
    for i in range(2):
        _make_lease_with_owned_apartment(i)
    small = _count_queries(authenticated_api_client, LEASES_URL)

    for i in range(2, 6):
        _make_lease_with_owned_apartment(i)
    large = _count_queries(authenticated_api_client, LEASES_URL)

    assert small == large, (
        f"lease list scales with N: {small} -> {large} (apartment owner/active_lease N+1)"
    )


def test_apartment_list_no_n_plus_one(authenticated_api_client):
    for i in range(2):
        _make_lease_with_owned_apartment(i)
    small = _count_queries(authenticated_api_client, APARTMENTS_URL)

    for i in range(2, 6):
        _make_lease_with_owned_apartment(i)
    large = _count_queries(authenticated_api_client, APARTMENTS_URL)

    assert small == large, (
        f"apartment list scales with N: {small} -> {large} (owner/active_lease N+1)"
    )
