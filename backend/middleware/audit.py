"""
Audit log middleware for InvoiceForge.
Records write operations (POST, PUT, PATCH, DELETE) on API endpoints
for compliance and troubleshooting purposes.
"""

import json
import logging

from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger("invoiceforge.audit")

# HTTP methods that modify data
WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


class AuditLogMiddleware(MiddlewareMixin):
    """
    Logs all write operations on API endpoints.
    Captures user, action, resource path, and timestamp.
    """

    def process_request(self, request):
        # Only track write methods on API endpoints
        if request.method not in WRITE_METHODS:
            return None
        if not request.path.startswith("/api/"):
            return None

        # Store the body before it's consumed by DRF parsers
        try:
            if request.content_type and "json" in request.content_type:
                body = request.body.decode("utf-8", errors="replace")
                # Truncate very large bodies
                if len(body) > 2000:
                    body = body[:2000] + "...[truncated]"
                request._audit_body = body
            else:
                request._audit_body = f"<{request.content_type or 'no content-type'}>"
        except Exception:
            request._audit_body = "<unable to read body>"

        return None

    def process_response(self, request, response):
        if request.method not in WRITE_METHODS:
            return response
        if not request.path.startswith("/api/"):
            return response

        user_email = "anonymous"
        user_id = None
        if hasattr(request, "user") and request.user.is_authenticated:
            user_email = request.user.email
            user_id = str(request.user.id)

        audit_entry = {
            "timestamp": timezone.now().isoformat(),
            "user_id": user_id,
            "user_email": user_email,
            "method": request.method,
            "path": request.path,
            "status_code": response.status_code,
            "ip_address": self._get_client_ip(request),
        }

        # Log at appropriate level based on status code
        if response.status_code < 400:
            logger.info(
                "AUDIT: %(method)s %(path)s by %(user_email)s -> %(status_code)s",
                audit_entry,
            )
        else:
            logger.warning(
                "AUDIT: %(method)s %(path)s by %(user_email)s -> %(status_code)s",
                audit_entry,
            )

        return response

    @staticmethod
    def _get_client_ip(request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "unknown")
