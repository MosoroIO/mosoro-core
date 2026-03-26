# Copyright 2026 Mosoro Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: Apache-2.0

"""
Mosoro API Authentication & Authorization
==========================================

Provides JWT-based authentication middleware for the FastAPI API layer.
Includes rate limiting per robot_id and role-based access control stubs.

Usage:
    from security.auth import get_current_user, require_admin

    @app.get("/robots")
    async def list_robots(user: dict = Depends(get_current_user)):
        ...
"""

import logging
import os
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

logger = logging.getLogger("mosoro.security.auth")

# JWT configuration from environment
JWT_SECRET = os.environ.get("MOSORO_JWT_SECRET", "mosoro-dev-secret-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_MINUTES = int(os.environ.get("MOSORO_JWT_EXPIRATION_MINUTES", "60"))

# Rate limiting configuration
RATE_LIMIT_REQUESTS = int(os.environ.get("MOSORO_RATE_LIMIT_REQUESTS", "100"))
RATE_LIMIT_WINDOW_SECONDS = int(os.environ.get("MOSORO_RATE_LIMIT_WINDOW", "60"))

# Bearer token scheme
bearer_scheme = HTTPBearer(auto_error=False)


# ---------------------------------------------------------------------------
# Rate limiter (in-memory, per robot_id or IP)
# ---------------------------------------------------------------------------

class RateLimiter:
    """Simple in-memory rate limiter per key (robot_id or IP)."""

    def __init__(self, max_requests: int = RATE_LIMIT_REQUESTS, window_seconds: int = RATE_LIMIT_WINDOW_SECONDS):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: Dict[str, list] = defaultdict(list)

    def is_allowed(self, key: str) -> bool:
        """Check if a request from the given key is allowed."""
        now = time.time()
        cutoff = now - self.window_seconds

        # Clean old entries
        self._requests[key] = [t for t in self._requests[key] if t > cutoff]

        if len(self._requests[key]) >= self.max_requests:
            return False

        self._requests[key].append(now)
        return True

    def get_remaining(self, key: str) -> int:
        """Get remaining requests for the given key."""
        now = time.time()
        cutoff = now - self.window_seconds
        self._requests[key] = [t for t in self._requests[key] if t > cutoff]
        return max(0, self.max_requests - len(self._requests[key]))


# Global rate limiter instance
rate_limiter = RateLimiter()


# ---------------------------------------------------------------------------
# JWT token creation and validation
# ---------------------------------------------------------------------------

def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create a JWT access token.

    Args:
        data: Payload data (e.g., {"sub": "admin", "role": "admin"}).
        expires_delta: Custom expiration time.

    Returns:
        Encoded JWT string.
    """
    try:
        import jwt
    except ImportError:
        raise ImportError("PyJWT is required. Install with: pip install PyJWT")

    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=JWT_EXPIRATION_MINUTES)
    )
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})

    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> Dict[str, Any]:
    """
    Decode and validate a JWT token.

    Args:
        token: The JWT string.

    Returns:
        Decoded payload dict.

    Raises:
        HTTPException: If token is invalid or expired.
    """
    try:
        import jwt
    except ImportError:
        raise ImportError("PyJWT is required. Install with: pip install PyJWT")

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ---------------------------------------------------------------------------
# FastAPI dependencies
# ---------------------------------------------------------------------------

async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> Dict[str, Any]:
    """
    FastAPI dependency: Extract and validate the current user from JWT.

    Also applies rate limiting per client IP.

    Usage:
        @app.get("/robots")
        async def list_robots(user: dict = Depends(get_current_user)):
            ...
    """
    # Rate limiting by client IP
    client_ip = request.client.host if request.client else "unknown"
    if not rate_limiter.is_allowed(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Max {RATE_LIMIT_REQUESTS} requests per {RATE_LIMIT_WINDOW_SECONDS}s.",
        )

    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_token(credentials.credentials)

    # Validate required fields
    if "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing subject",
        )

    return payload


async def require_admin(
    user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    FastAPI dependency: Require admin role.

    Usage:
        @app.post("/admin/rules")
        async def update_rules(user: dict = Depends(require_admin)):
            ...
    """
    if user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user


async def rate_limit_by_robot_id(
    request: Request,
    robot_id: str,
) -> None:
    """
    FastAPI dependency: Rate limit by robot_id.

    Usage:
        @app.get("/robots/{robot_id}")
        async def get_robot(robot_id: str, _=Depends(rate_limit_by_robot_id)):
            ...
    """
    if not rate_limiter.is_allowed(f"robot:{robot_id}"):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded for robot {robot_id}",
        )
