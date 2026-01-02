"""
Compatibility shim.

ORM models were consolidated into app.models.
This module remains only to avoid breaking older imports.
"""
from .models import *  # noqa: F401,F403

