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
