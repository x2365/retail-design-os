"""Shared slowapi Limiter instance.

Lives in its own module (rather than main.py) so routers can import it to
decorate individual endpoints without a circular import on `main`.
"""

from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

from .config import get_settings

limiter = Limiter(
    key_func=get_remote_address, default_limits=[get_settings().default_rate_limit]
)
