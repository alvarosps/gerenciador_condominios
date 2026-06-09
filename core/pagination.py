# core/pagination.py
"""Custom pagination classes for the API."""

from rest_framework.pagination import PageNumberPagination


class CustomPageNumberPagination(PageNumberPagination):
    """
    Custom pagination class that allows clients to specify page size.

    Query parameters:
    - page: Page number (default: 1)
    - page_size: Number of items per page (default: 20, max: 500)
    """

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 500


class LargePageNumberPagination(CustomPageNumberPagination):
    """Same paginated ``{results, count}`` envelope, but with a high cap for "show all" list
    endpoints (e.g. Contas, grouped per building) that render every row and rely on the
    ``page_size=10000`` convention. Keeps the response SHAPE — clients still get ``results``."""

    max_page_size = 10000
