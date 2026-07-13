# core/pagination.py
"""Custom pagination classes for the API."""

from rest_framework.pagination import PageNumberPagination


class CustomPageNumberPagination(PageNumberPagination):
    """
    Custom pagination class that allows clients to specify page size.

    Query parameters:
    - page: Page number (default: 1)
    - page_size: Number of items per page (default: 20, max: 10000)

    The 10000 cap matches the project's "show all" convention (small-scale system; large pages
    are intentional, not a bug) — 28+ frontend hooks request page_size=10000 to render every row
    in one page (e.g. Contas grouped per building).
    """

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 10000
