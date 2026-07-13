"""Unit tests for core/pagination.py.

A3: page_size was capped at 500 while 28+ frontend hooks intentionally request
page_size=10000 (the project's "show all" convention for a small-scale system) — silently
truncating any list past 500 rows. max_page_size is now 10000, and the redundant
LargePageNumberPagination (identical once the caps matched) was removed.
"""

import pytest
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

import core.pagination
from core.pagination import CustomPageNumberPagination

pytestmark = pytest.mark.unit


class TestCustomPageNumberPagination:
    def test_max_page_size_is_10000(self):
        assert CustomPageNumberPagination.max_page_size == 10000

    def test_default_page_size_unchanged(self):
        assert CustomPageNumberPagination.page_size == 20

    def test_page_size_query_param_unchanged(self):
        assert CustomPageNumberPagination.page_size_query_param == "page_size"

    def test_page_size_10000_returns_more_than_500_items_no_truncation(self):
        """Regression: page_size=10000 (the project convention, 28+ hooks) used to be silently
        clamped to 500 by the old max_page_size — this proves a page of 501+ items now comes
        back whole. No DB needed: PageNumberPagination.paginate_queryset works on any sliceable
        (a plain list stands in for a real queryset)."""
        items = list(range(600))
        request = Request(APIRequestFactory().get("/fake/", {"page_size": "10000"}))

        page = CustomPageNumberPagination().paginate_queryset(items, request)

        assert page is not None
        assert len(page) == 600


class TestLargePageNumberPaginationRemoved:
    def test_large_page_number_pagination_no_longer_exists(self):
        # A3: LargePageNumberPagination became byte-for-byte identical to
        # CustomPageNumberPagination once max_page_size was raised to 10000 — dead code removed
        # (no re-exports, no deprecated alias) rather than kept redundantly.
        assert not hasattr(core.pagination, "LargePageNumberPagination")
