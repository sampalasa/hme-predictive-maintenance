"""Access-control decorators: role-based authorization and JWT enforcement."""

from functools import wraps
from typing import Callable

import jwt
from flask import abort, g, jsonify, request
from flask_login import current_user

from app.services.auth_service import AuthService
from app.utils.logger import get_logger

logger = get_logger(__name__)


def roles_required(*allowed_roles: str) -> Callable:
    """Restrict a session-authenticated (Flask-Login) view to given roles."""

    def decorator(view_func: Callable) -> Callable:
        @wraps(view_func)
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            if current_user.role.name not in allowed_roles:
                abort(403)
            return view_func(*args, **kwargs)

        return wrapped

    return decorator


def jwt_required(view_func: Callable) -> Callable:
    """Restrict an API view to requests bearing a valid JWT access token."""

    @wraps(view_func)
    def wrapped(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify(error="Missing bearer token."), 401

        token = auth_header[len("Bearer "):].strip()
        try:
            payload = AuthService.decode_token(token)
        except jwt.ExpiredSignatureError:
            return jsonify(error="Token expired."), 401
        except jwt.InvalidTokenError:
            return jsonify(error="Invalid token."), 401

        g.jwt_payload = payload
        return view_func(*args, **kwargs)

    return wrapped
