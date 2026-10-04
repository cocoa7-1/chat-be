import asyncio
import json
import os
from pathlib import Path
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from unittest.mock import Mock

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.api.v1 import auth, chat
from app.core import abuse, config
from app.main import app
from app.models.chat import ChatMessage, ChatSession
from app.models.user import User


@pytest.mark.parametrize("environment", ["production", "prod"])
@pytest.mark.parametrize("key", [config.DEVELOPMENT_SECRET_KEY, "", "audit-short"])
def test_production_rejects_default_empty_or_short_key(environment, key):
    settings = config.Settings(_env_file=None, APP_ENV=environment, SECRET_KEY=key)
    with pytest.raises(RuntimeError) as error:
        settings.validate_production_security()
    assert str(error.value) == "Production SECRET_KEY must be a unique random key of at least 32 bytes."


def test_get_settings_enforces_security_without_echoing_key(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", "audit-private-short-sentinel")
    config.get_settings.cache_clear()
    try:
        with pytest.raises(RuntimeError) as error:
            config.get_settings()
        assert "audit-private-short-sentinel" not in str(error.value)
    finally:
        config.get_settings.cache_clear()


def test_random_length_key_and_development_settings_still_work():
    config.Settings(_env_file=None, APP_ENV="production", SECRET_KEY="audit-only-long-key-for-isolated-settings-check").validate_production_security()
    config.Settings(_env_file=None, APP_ENV="development").validate_production_security()


@pytest.mark.parametrize("key,passed", [
    ("audit-only-long-key-for-isolated-settings-check", True),
    (config.DEVELOPMENT_SECRET_KEY, False),
    ("audit-private-short-sentinel", False),
])
def test_security_check_script_reports_booleans_without_secret_or_db(tmp_path, key, passed):
    repo = Path(__file__).resolve().parents[1]
    environment = dict(os.environ, APP_ENV="production", SECRET_KEY=key,
                       GEMINI_API_KEY="audit-only-private-ai-sentinel",
                       DATABASE_URL="sqlite:///" + (tmp_path / "must-not-exist.db").as_posix())
    result = subprocess.run([sys.executable, str(repo / "scripts/check_security_config.py")],
                            cwd=tmp_path, env=environment, capture_output=True, text=True)
    assert result.returncode == (0 if passed else 1)
    assert json.loads(result.stdout)["baseline_passed"] is passed
    assert key not in result.stdout + result.stderr
    assert "audit-only-private-ai-sentinel" not in result.stdout + result.stderr
    assert result.stderr == "" and not (tmp_path / "must-not-exist.db").exists()


def limits(**changes):
    values = dict(CHAT_USER_CONCURRENCY=1, CHAT_GLOBAL_CONCURRENCY=3,
                  CHAT_REQUESTS_PER_MINUTE=6, CHAT_GLOBAL_REQUESTS_PER_MINUTE=20)
    values.update(changes)
    return SimpleNamespace(**values)


def test_sliding_window_retry_and_expiration():
    now = [100.0]
    guard = abuse.RequestGuard(clock=lambda: now[0])
    guard.admit_auth("login", "peer", 2)
    now[0] = 101.2
    guard.admit_auth("login", "peer", 2)
    with pytest.raises(abuse.LimitExceeded) as error:
        guard.admit_auth("login", "peer", 2)
    assert error.value.retry_after == 59
    now[0] = 160.0
    guard.admit_auth("login", "peer", 2)
    assert len(guard.windows[("login", "peer")]) == 2


def test_identity_storage_is_bounded_and_expired_peers_are_removed():
    now = [0.0]
    guard = abuse.RequestGuard(clock=lambda: now[0], max_buckets=2)
    guard.admit_auth("login", "a", 1)
    guard.admit_auth("login", "b", 1)
    with pytest.raises(abuse.LimitExceeded) as error:
        guard.admit_auth("login", "c", 1)
    assert error.value.reason == "limiter_capacity" and len(guard.windows) == 2
    now[0] = 60.0
    guard.admit_auth("login", "c", 1)
    assert list(guard.windows) == [("login", "c")]


def test_failed_global_admission_does_not_consume_user_budget_or_slot():
    guard = abuse.RequestGuard()
    settings = limits(CHAT_GLOBAL_REQUESTS_PER_MINUTE=1)
    guard.admit_chat(1, settings).release()
    with pytest.raises(abuse.LimitExceeded):
        guard.admit_chat(2, settings)
    assert ("chat_user", 2) not in guard.windows
    assert guard.active_total == 0 and guard.active_users == {}


def test_parallel_admission_obeys_global_capacity_and_idempotent_release():
    guard = abuse.RequestGuard()
    def acquire(user_id):
        try:
            return guard.admit_chat(user_id, limits())
        except abuse.LimitExceeded:
            return None
    with ThreadPoolExecutor(max_workers=8) as pool:
        leases = [lease for lease in pool.map(acquire, range(8)) if lease is not None]
    assert len(leases) == guard.active_total == 3
    for lease in leases:
        lease.release()
        lease.release()
    assert guard.active_total == 0 and guard.active_users == {}


def successful_ai(monkeypatch):
    calls = []
    async def respond(**kwargs):
        calls.append(kwargs)
        yield {"text": "", "done": True, "full_text": "audit answer", "latency_ms": 1, "error": None}
    monkeypatch.setattr(chat.gemini_service, "stream_chat_response", respond)
    return calls


def test_register_rate_limit_precedes_password_hash_and_user_insert(isolated_chat, monkeypatch):
    client, factory, _ = isolated_chat
    monkeypatch.setattr(config.get_settings(), "REGISTER_REQUESTS_PER_MINUTE", 1)
    abuse.guard = abuse.RequestGuard()
    hashing = Mock(wraps=auth.get_password_hash)
    monkeypatch.setattr(auth, "get_password_hash", hashing)
    first = client.post("/api/v1/auth/register", json={"username": "new_a", "nickname": "A", "password": "auditPassword123"})
    second = client.post("/api/v1/auth/register", json={"username": "new_b", "nickname": "B", "password": "auditPassword123"})
    assert first.status_code == 201 and second.status_code == 429
    assert int(second.headers["Retry-After"]) >= 1 and hashing.call_count == 1
    with factory() as db:
        assert db.scalar(select(func.count(User.id))) == 2


def test_login_failures_count_and_forwarded_header_cannot_reset_budget(isolated_chat, monkeypatch):
    client, _, _ = isolated_chat
    monkeypatch.setattr(config.get_settings(), "LOGIN_REQUESTS_PER_MINUTE", 1)
    abuse.guard = abuse.RequestGuard()
    verifying = Mock(wraps=auth.verify_password)
    monkeypatch.setattr(auth, "verify_password", verifying)
    first = client.post("/api/v1/auth/login", json={"username": "reliability_user", "password": "wrong-audit-password"}, headers={"X-Forwarded-For": "192.0.2.1"})
    second = client.post("/api/v1/auth/login", json={"username": "reliability_user", "password": "auditPassword123"}, headers={"X-Forwarded-For": "192.0.2.2"})
    assert first.status_code == 401 and second.status_code == 429
    assert verifying.call_count == 1
    # Password changes share the same expensive authentication budget.
    assert client.put("/api/v1/auth/password", json={"current_password": "auditPassword123", "new_password": "auditPassword456"}).status_code == 429


def test_chat_rate_rejection_does_not_save_question_or_call_ai(isolated_chat, monkeypatch, caplog):
    client, factory, _ = isolated_chat
    monkeypatch.setattr(config.get_settings(), "CHAT_REQUESTS_PER_MINUTE", 1)
    calls = successful_ai(monkeypatch)
    assert client.post("/api/v1/chat/stream", json={"message": "first"}).status_code == 200
    caplog.clear()
    denied = client.post("/api/v1/chat/stream", json={"message": "denied"}, headers={"Origin": "https://b7-1-chat-fe.vercel.app", "X-Request-ID": "rate-denied"})
    assert denied.status_code == 429 and "요청이 너무 많습니다" in denied.json()["detail"]
    assert int(denied.headers["Retry-After"]) >= 1
    assert "Retry-After" in denied.headers["Access-Control-Expose-Headers"]
    assert len(calls) == 1 and abuse.guard.active_total == 0
    assert "request_rejected" in caplog.text and "request_id=rate-denied" in caplog.text
    assert "db_save_success" not in caplog.text
    with factory() as db:
        assert db.scalar(select(func.count(ChatMessage.id))) == 2
        assert db.scalar(select(func.count(ChatSession.id))) == 1


def test_global_chat_rate_applies_across_users(isolated_chat, monkeypatch):
    client, factory, _ = isolated_chat
    monkeypatch.setattr(config.get_settings(), "CHAT_GLOBAL_REQUESTS_PER_MINUTE", 1)
    calls = successful_ai(monkeypatch)
    assert client.post("/api/v1/chat/stream", json={"message": "first"}).status_code == 200
    with TestClient(app) as other:
        assert other.post("/api/v1/auth/register", json={"username": "other_audit", "nickname": "B", "password": "auditPassword123"}).status_code == 201
        assert other.post("/api/v1/auth/login", json={"username": "other_audit", "password": "auditPassword123"}).status_code == 200
        assert other.post("/api/v1/chat/stream", json={"message": "denied"}).status_code == 429
    with factory() as db:
        assert db.scalar(select(func.count(ChatMessage.id))) == 2
    assert len(calls) == 1 and abuse.guard.active_total == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("cancel", [False, True])
async def test_active_stream_blocks_same_user_and_releases_after_completion_or_cancel(
    isolated_chat, monkeypatch, cancel
):
    client, factory, _ = isolated_chat
    started, finish = asyncio.Event(), asyncio.Event()
    async def slow_ai(**kwargs):
        started.set()
        await finish.wait()
        yield {"text": "", "done": True, "full_text": "audit answer", "latency_ms": 1, "error": None}
    monkeypatch.setattr(chat.gemini_service, "stream_chat_response", slow_ai)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver", cookies=client.cookies) as browser:
        first = asyncio.create_task(browser.post("/api/v1/chat/stream", json={"message": "first"}))
        try:
            await asyncio.wait_for(started.wait(), timeout=2)
            assert abuse.guard.active_total == 1
            denied = await browser.post("/api/v1/chat/stream", json={"message": "denied"})
            assert denied.status_code == 429 and denied.headers["Retry-After"] == "1"
            with factory() as db:
                assert db.scalar(select(func.count(ChatMessage.id))) == 1
            if cancel:
                first.cancel()
                with pytest.raises(asyncio.CancelledError):
                    await first
            else:
                finish.set()
                assert (await first).status_code == 200
            assert abuse.guard.active_total == 0
            finish.set()
            assert (await browser.post("/api/v1/chat/stream", json={"message": "after"})).status_code == 200
            assert abuse.guard.active_total == 0
        finally:
            finish.set()
            if not first.done():
                first.cancel()
            await asyncio.gather(first, return_exceptions=True)


@pytest.mark.asyncio
async def test_capacity_is_held_until_asgi_send_finishes_or_is_cancelled():
    guard = abuse.RequestGuard()
    started = asyncio.Event()
    async def send_blocked(scope, receive, send):
        scope["state"]["chat_lease"] = guard.admit_chat(1, limits())
        await send({"type": "http.response.start", "status": 200, "headers": []})
        started.set()
        await asyncio.Event().wait()
    async def send(message):
        pass
    task = asyncio.create_task(abuse.ChatLeaseMiddleware(send_blocked)({"type": "http", "state": {}}, None, send))
    await asyncio.wait_for(started.wait(), timeout=1)
    assert guard.active_total == 1
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert guard.active_total == 0
