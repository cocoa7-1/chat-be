"""Bounded, process-local request windows and streaming admission leases."""
import math
import time
from collections import OrderedDict, deque
from threading import Lock

from fastapi import HTTPException, Request

from app.core.config import get_settings
from app.core.logging import logger


class LimitExceeded(Exception):
    def __init__(self, reason: str, retry_after: int):
        self.reason = reason
        self.retry_after = retry_after


class ChatLease:
    def __init__(self, owner, user_id: int):
        self.owner = owner
        self.user_id = user_id
        self.released = False

    def release(self) -> None:
        self.owner.release(self)


class RequestGuard:
    WINDOW_SECONDS = 60

    def __init__(self, clock=time.monotonic, max_buckets: int = 10000):
        self.clock = clock
        self.max_buckets = max_buckets
        self.lock = Lock()
        self.windows = OrderedDict()
        self.active_users = {}
        self.active_total = 0

    def _record(self, limits, now: float) -> None:
        cutoff = now - self.WINDOW_SECONDS
        # Ordered by last accepted request, so expired identities are removed
        # without scanning every live bucket on every request.
        while self.windows:
            key, window = next(iter(self.windows.items()))
            if window[-1] > cutoff:
                break
            self.windows.pop(key)
        missing = 0
        for key, limit in limits:
            window = self.windows.get(key)
            if window is None:
                missing += 1
                continue
            while window and window[0] <= cutoff:
                window.popleft()
            if len(window) >= limit:
                raise LimitExceeded("rate_limit", max(1, math.ceil(window[0] + self.WINDOW_SECONDS - now)))
        if len(self.windows) + missing > self.max_buckets:
            raise LimitExceeded("limiter_capacity", self.WINDOW_SECONDS)
        # All checks pass before consuming any of the shared budgets.
        for key, _ in limits:
            window = self.windows.setdefault(key, deque())
            window.append(now)
            self.windows.move_to_end(key)

    def admit_auth(self, kind: str, client: str, limit: int) -> None:
        with self.lock:
            self._record([((kind, client), limit)], self.clock())

    def admit_chat(self, user_id: int, settings) -> ChatLease:
        with self.lock:
            if self.active_users.get(user_id, 0) >= settings.CHAT_USER_CONCURRENCY:
                raise LimitExceeded("user_concurrency", 1)
            if self.active_total >= settings.CHAT_GLOBAL_CONCURRENCY:
                raise LimitExceeded("global_concurrency", 1)
            self._record([
                (("chat_user", user_id), settings.CHAT_REQUESTS_PER_MINUTE),
                (("chat_global", "all"), settings.CHAT_GLOBAL_REQUESTS_PER_MINUTE),
            ], self.clock())
            self.active_users[user_id] = self.active_users.get(user_id, 0) + 1
            self.active_total += 1
            return ChatLease(self, user_id)

    def release(self, lease: ChatLease) -> None:
        with self.lock:
            if lease.released:
                return
            lease.released = True
            self.active_total -= 1
            remaining = self.active_users[lease.user_id] - 1
            if remaining:
                self.active_users[lease.user_id] = remaining
            else:
                self.active_users.pop(lease.user_id)


guard = RequestGuard()


def _reject(request: Request, error: LimitExceeded, kind: str) -> None:
    request_id = getattr(request.state, "request_id", "req-unknown")
    logger.warning("request_rejected request_id=%s kind=%s reason=%s", request_id, kind, error.reason)
    message = (
        "답변 처리 중입니다. 잠시 후 다시 시도해 주세요."
        if "concurrency" in error.reason else "요청이 너무 많습니다. 잠시 후 다시 시도해 주세요."
    )
    raise HTTPException(status_code=429, detail=message, headers={"Retry-After": str(error.retry_after)})


async def limit_registration(request: Request) -> None:
    client = request.client.host if request.client else "unknown"
    try:
        guard.admit_auth("register", client, get_settings().REGISTER_REQUESTS_PER_MINUTE)
    except LimitExceeded as error:
        _reject(request, error, "register")


async def limit_login(request: Request) -> None:
    # Use ASGI's client address. Never trust caller-supplied forwarding headers
    # here; Uvicorn must trust only the existing loopback Caddy proxy.
    client = request.client.host if request.client else "unknown"
    try:
        guard.admit_auth("login", client, get_settings().LOGIN_REQUESTS_PER_MINUTE)
    except LimitExceeded as error:
        _reject(request, error, "login")


def admit_chat(request: Request, user_id: int) -> None:
    try:
        request.state.chat_lease = guard.admit_chat(user_id, get_settings())
    except LimitExceeded as error:
        _reject(request, error, "chat")


class ChatLeaseMiddleware:
    """Hold admission until the whole ASGI response ends, including SSE sends."""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        try:
            await self.app(scope, receive, send)
        finally:
            if scope["type"] == "http":
                lease = scope.get("state", {}).pop("chat_lease", None)
                if lease is not None:
                    lease.release()
