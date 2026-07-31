"""Shared Flask extension instances.

Kept in their own module (separate from ``app/__init__.py``) so any module
can import them without triggering a circular import with the application
factory.
"""

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LoginManager
from flask_wtf import CSRFProtect

login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message = "Veuillez vous connecter pour accéder à cette page."
login_manager.login_message_category = "warning"

csrf = CSRFProtect()

limiter = Limiter(key_func=get_remote_address, default_limits=["300 per hour"])
