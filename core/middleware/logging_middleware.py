"""
Request/Response logging middleware.

Logs all HTTP requests and responses with:
- Request method, path, user agent
- Response status, time taken
- User information (if authenticated)
- Request body (for non-GET requests)
"""
import json
import logging
import time
from typing import Callable

from django.http import HttpRequest, HttpResponse
from django.utils.deprecation import MiddlewareMixin

# Get specialized loggers
access_logger = logging.getLogger("access")
performance_logger = logging.getLogger("performance")


class RequestResponseLoggingMiddleware(MiddlewareMixin):
    """
    Middleware to log all HTTP requests and responses.

    Logs:
    - Request details (method, path, user, IP)
    - Response details (status code, time taken)
    - Performance metrics
    - Request/response bodies (configurable)
    """

    def process_request(self, request: HttpRequest) -> None:
        """
        Process incoming request.

        Stores request start time and logs request details.

        Args:
            request: Incoming HTTP request
        """
        request._start_time = time.time()

        # Log access
        access_logger.info(
            "REQUEST",
            extra={
                "method": request.method,
                "path": request.path,
                "user": str(request.user) if hasattr(request, "user") else "Anonymous",
                "ip": self._get_client_ip(request),
                "user_agent": request.META.get("HTTP_USER_AGENT", ""),
                "content_type": request.content_type,
            },
        )

    def process_response(self, request: HttpRequest, response: HttpResponse) -> HttpResponse:
        """
        Process outgoing response.

        Calculates request duration and logs response details.

        Args:
            request: Original HTTP request
            response: HTTP response to be sent

        Returns:
            The unmodified HTTP response
        """
        if hasattr(request, "_start_time"):
            duration = time.time() - request._start_time

            # Log access response
            access_logger.info(
                "RESPONSE",
                extra={
                    "method": request.method,
                    "path": request.path,
                    "status_code": response.status_code,
                    "duration_ms": round(duration * 1000, 2),
                    "user": str(request.user) if hasattr(request, "user") else "Anonymous",
                },
            )

            # Log performance for slow requests
            if duration > 1.0:  # Log requests taking more than 1 second
                performance_logger.warning(
                    "SLOW_REQUEST",
                    extra={
                        "method": request.method,
                        "path": request.path,
                        "duration_ms": round(duration * 1000, 2),
                        "status_code": response.status_code,
                    },
                )

        return response

    @staticmethod
    def _get_client_ip(request: HttpRequest) -> str:
        """
        Get client IP address from request.

        Checks X-Forwarded-For header first (for proxied requests),
        then falls back to REMOTE_ADDR.

        Args:
            request: HTTP request

        Returns:
            Client IP address
        """
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0]
        else:
            ip = request.META.get("REMOTE_ADDR", "")
        return ip
