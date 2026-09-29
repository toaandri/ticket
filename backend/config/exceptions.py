"""Custom DRF exception handler with consistent error schema.

Every error response follows:
    {
        "code": "string",
        "message": "string",
        "details": {...} | null,
        "request_id": "string" | null
    }
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from django.core.exceptions import PermissionDenied
from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


def custom_exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    """Wrap DRF exception responses in a consistent envelope."""
    response = exception_handler(exc, context)

    request = context.get("request")
    request_id = getattr(request, "id", None) or str(uuid.uuid4())

    if response is not None:
        code = _get_code(exc, response)
        message = _get_message(exc, response)
        details = _get_details(response)

        response.data = {
            "code": code,
            "message": message,
            "details": details,
            "request_id": request_id,
        }
        return response

    # Unhandled server error — log and return 500
    logger.exception("Unhandled exception: %s", exc, extra={"request_id": request_id})
    return Response(
        {
            "code": "server_error",
            "message": "An unexpected error occurred.",
            "details": None,
            "request_id": request_id,
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


def _get_code(exc: Exception, response: Response) -> str:
    if isinstance(exc, Http404):
        return "not_found"
    if isinstance(exc, PermissionDenied):
        return "permission_denied"
    if isinstance(exc, APIException):
        return getattr(exc, "default_code", "error") or "error"
    return "error"


def _get_message(exc: Exception, response: Response) -> str:
    if isinstance(exc, Http404):
        return "Not found."
    if isinstance(exc, PermissionDenied):
        return "Permission denied."
    if isinstance(exc, APIException):
        detail = exc.detail
        if isinstance(detail, list) and detail:
            first = detail[0]
            return str(first) if not hasattr(first, "items") else "Validation error."
        if isinstance(detail, dict):
            return "Validation error."
        return str(detail)
    return "An error occurred."


def _get_details(response: Response) -> dict | None:
    data = response.data
    if isinstance(data, dict) and any(k not in ("code", "message", "details", "request_id") for k in data):
        return data
    if isinstance(data, list):
        return {"non_field_errors": data}
    return None
