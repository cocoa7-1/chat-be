"""Regression coverage using temporary SQLite and fake AI streams only."""
import asyncio
import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, func, select
from sqlalchemy.exc import OperationalError

from app.api.v1 import chat
from app.core import abuse
from app.core.database import get_db
from app.main import app
from app.models.chat import ChatMessage, ChatSession
from app.services import gemini_service as gm


class FakeStream:
    def __init__(self, steps, close_delay=0):
        self.steps = iter(steps)
        self.close_delay = close_delay
        self.read_started = asyncio.Event()
        self.closed = False
        self.close_cancelled = False

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            delay, text = next(self.steps)
        except StopIteration:
            raise StopAsyncIteration
        self.read_started.set()
        if delay is None:
            await asyncio.Event().wait()
        else:
            await asyncio.sleep(delay)
        return SimpleNamespace(text=text)

    async def aclose(self):
        self.closed = True
        try:
            await asyncio.sleep(self.close_delay)
        except asyncio.CancelledError:
            self.close_cancelled = True
            raise


def fake_service(monkeypatch, stream, connection_delay=0, timeout=0.12):
    monkeypatch.setattr(gm.settings, "GEMINI_API_KEY", "")
    service = gm.GeminiService()
    service.api_key = "fake-sdk-only"
    service.timeout_seconds = timeout

    async def connect(**kwargs):
        await asyncio.sleep(connection_delay)
        return stream

    service._client = SimpleNamespace(
        aio=SimpleNamespace(models=SimpleNamespace(generate_content_stream=connect))
    )
    return service


async def collect(service):
    return [chunk async for chunk in service.stream_chat_response(1, "timeout-test", [], "test")]


@pytest.mark.asyncio
@pytest.mark.parametrize("connection_delay,steps,partial", [
    (0.5, [(0, "first")], ""),
    (0, [(None, "first")], ""),
    (0, [(0, "first"), (None, "second")], "first"),
    (0, [(0.03, "token")] * 20, "token"),
    (0.08, [(0.08, "first")], ""),
])
async def test_shared_timeout_covers_connection_and_all_reads(
    monkeypatch, caplog, connection_delay, steps, partial
):
    stream = FakeStream(steps)
    service = fake_service(monkeypatch, stream, connection_delay)
    chunks = await asyncio.wait_for(collect(service), timeout=0.8)
    final = chunks[-1]
    assert final["done"] and final["error"] == "AI_TIMEOUT"
    assert "AI_TIMEOUT" in final["full_text"]
    assert final["full_text"].startswith(partial)
    if connection_delay == 0:
        assert stream.closed
    assert "ai_call_failed" in caplog.text and "error=\"AI_TIMEOUT\"" in caplog.text
    assert "ai_call_success" not in caplog.text


@pytest.mark.asyncio
async def test_normal_stream_completes_and_closes(monkeypatch, caplog):
    stream = FakeStream([(0.01, "one"), (0.01, "two")])
    chunks = await collect(fake_service(monkeypatch, stream))
    assert [chunk["text"] for chunk in chunks[:-1]] == ["one", "two"]
    assert chunks[-1]["full_text"] == "onetwo" and chunks[-1]["error"] is None
    assert stream.closed
    assert "ai_call_success" in caplog.text and "ai_call_failed" not in caplog.text


@pytest.mark.asyncio
async def test_timeout_does_not_cancel_consumer_between_chunks(monkeypatch):
    stream = FakeStream([(0, "first"), (0, "second")])
    service = fake_service(monkeypatch, stream, timeout=0.04)
    response = service.stream_chat_response(1, "consumer-delay", [], "test")
    assert (await anext(response))["text"] == "first"
    await asyncio.sleep(0.08)
    rest = [chunk async for chunk in response]
    assert rest[-1]["error"] == "AI_TIMEOUT"
    assert not any(chunk["text"] == "second" for chunk in rest)
    assert stream.closed


@pytest.mark.asyncio
async def test_caller_cancellation_propagates_and_closes(monkeypatch, caplog):
    stream = FakeStream([(None, "first")])
    service = fake_service(monkeypatch, stream, timeout=5)
    task = asyncio.create_task(collect(service))
    await asyncio.wait_for(stream.read_started.wait(), timeout=0.8)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert stream.closed
    assert "ai_call_failed" not in caplog.text and "ai_call_success" not in caplog.text


@pytest.mark.asyncio
async def test_slow_cleanup_is_bounded_and_keeps_timeout_result(monkeypatch, caplog):
    stream = FakeStream([(None, "first")], close_delay=5)
    service = fake_service(monkeypatch, stream, timeout=0.04)
    chunks = await asyncio.wait_for(collect(service), timeout=1.8)
    assert chunks[-1]["error"] == "AI_TIMEOUT"
    assert stream.closed and stream.close_cancelled
    assert "ai_stream_close_failed" in caplog.text


@pytest.mark.parametrize("failure,existing_session,endpoint", [
    ("session_insert", False, "/api/v1/chat/stream"),
    ("question_insert", False, "/api/v1/chat/stream"),
    ("commit", False, "/api/v1/chat/stream"),
    ("question_insert", True, "/api/v1/chat/stream"),
    ("commit", True, "/api/v1/chat/stream"),
    ("session_insert", False, "/api/v1/chat/sessions"),
    ("commit", False, "/api/v1/chat/sessions"),
])
def test_initial_db_failure_rolls_back_and_returns_json(
    isolated_chat, monkeypatch, caplog, failure, existing_session, endpoint
):
    client, factory, engine = isolated_chat
    payload = {"message": "private question"} if endpoint.endswith("stream") else {"title": "private title"}
    if existing_session:
        payload["session_id"] = client.post("/api/v1/chat/sessions", json={"title": "existing"}).json()["id"]
    with factory() as check:
        baseline_sessions = check.scalar(select(func.count(ChatSession.id)))
        original_updated = check.scalar(select(ChatSession.updated_at))

    db = factory()
    rollback = Mock(wraps=db.rollback)
    monkeypatch.setattr(db, "rollback", rollback)
    ai = Mock(side_effect=AssertionError("AI must not run after initial DB failure"))
    monkeypatch.setattr(chat.gemini_service, "stream_chat_response", ai)

    def fail_insert(conn, cursor, statement, parameters, context, executemany):
        table = "chat_sessions" if failure == "session_insert" else "chat_messages"
        if statement.startswith("INSERT INTO " + table):
            raise OperationalError("private SQL", {"question": "private question"}, RuntimeError("injected"))

    if failure == "commit":
        monkeypatch.setattr(db, "commit", Mock(side_effect=OperationalError("private SQL", None, RuntimeError("injected"))))
    else:
        event.listen(engine, "before_cursor_execute", fail_insert)

    def db_dependency():
        yield db

    app.dependency_overrides[get_db] = db_dependency
    caplog.clear()
    try:
        response = client.post(endpoint, json=payload, headers={"X-Request-ID": "db-failure-test"})
        assert response.status_code == 500
        assert response.headers["content-type"].startswith("application/json")
        assert response.json() == {"detail": chat.DB_SAVE_ERROR_DETAIL}
        assert response.headers["X-Request-ID"] == "db-failure-test"
        assert rollback.called and not ai.called
        assert abuse.guard.active_total == 0
        assert "db_save_failed" in caplog.text and "request_id=db-failure-test" in caplog.text
        assert "db_save_success" not in caplog.text
        assert "private SQL" not in caplog.text and "private question" not in caplog.text
        with factory() as check:
            assert check.scalar(select(func.count(ChatSession.id))) == baseline_sessions
            assert check.scalar(select(func.count(ChatMessage.id))) == 0
            assert check.scalar(select(ChatSession.updated_at)) == original_updated
        # Rollback leaves the same connection usable.
        assert db.scalar(select(func.count(ChatMessage.id))) == 0
    finally:
        if failure != "commit":
            event.remove(engine, "before_cursor_execute", fail_insert)
        db.close()


@pytest.mark.parametrize("timeout", [False, True])
def test_sse_result_and_save_events_survive_transaction_changes(
    isolated_chat, monkeypatch, caplog, timeout
):
    client, factory, _ = isolated_chat
    stream = FakeStream([(0, "first"), (None, "second")] if timeout else [(0, "answer")])
    service = fake_service(monkeypatch, stream, timeout=0.05 if timeout else 0.5)
    monkeypatch.setattr(chat, "gemini_service", service)
    caplog.clear()
    response = client.post(
        "/api/v1/chat/stream", json={"message": "question"},
        headers={"X-Request-ID": "sse-save-test"}
    )
    assert response.status_code == 200
    assert "event: meta" in response.text and "event: done" in response.text
    data = [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")]
    assert data[-1]["error"] == ("AI_TIMEOUT" if timeout else None)
    assert data[-1]["status"] == ("error" if timeout else "success")
    with factory() as db:
        messages = db.scalars(select(ChatMessage).order_by(ChatMessage.id)).all()
        assert len(messages) == 2 and [m.role for m in messages] == ["user", "assistant"]
        assert messages[1].status == data[-1]["status"]
        assert messages[1].error_message == data[-1]["error"]
        assert messages[1].id == data[-1]["message_id"]
        assert messages[0].id == data[0]["user_message_id"]
        assert messages[0].session_id == data[0]["session_id"]
        assert messages[1].content.startswith("first" if timeout else "answer")
        assert messages[1].latency_ms is not None
    events = [record.getMessage() for record in caplog.records if "db_save_success" in record.getMessage()]
    assert len(events) == 3
    assert all("request_id=sse-save-test" in entry for entry in events)
    assert any("entity=session" in entry for entry in events)
    assert any("entity=user_message" in entry for entry in events)
    assert any("entity=assistant_message" in entry for entry in events)
    assert stream.closed
    assert abuse.guard.active_total == 0


def test_explicit_session_success_event(isolated_chat, caplog):
    client, _, _ = isolated_chat
    caplog.clear()
    response = client.post("/api/v1/chat/sessions", json={"title": "new"}, headers={"X-Request-ID": "session-save-test"})
    assert response.status_code == 201 and response.json()["title"] == "new"
    assert response.json()["messages"] == []
    assert "db_save_success" in caplog.text
    assert "entity=session" in caplog.text and "request_id=session-save-test" in caplog.text


def test_followup_context_and_foreign_session_stay_isolated(isolated_chat, monkeypatch):
    client, _, _ = isolated_chat
    service = fake_service(monkeypatch, FakeStream([]), timeout=0.5)
    calls = []

    async def connect(**kwargs):
        calls.append(kwargs["contents"])
        return FakeStream([(0, "answer" + str(len(calls)))])

    service._client.aio.models.generate_content_stream = connect
    monkeypatch.setattr(chat, "gemini_service", service)

    def metadata(response):
        assert response.status_code == 200 and "event: done" in response.text
        return json.loads(next(line[6:] for line in response.text.splitlines() if line.startswith("data: ")))

    first = metadata(client.post("/api/v1/chat/stream", json={"message": "first question"}))
    session_id = first["session_id"]
    second = metadata(client.post("/api/v1/chat/stream", json={"message": "followup", "session_id": session_id}))
    assert second["session_id"] == session_id and second["session_title"] == "first question"
    assert [(m["role"], m["parts"][0]["text"]) for m in calls[1]] == [
        ("user", "first question"), ("model", "answer1"), ("user", "followup")
    ]

    with TestClient(app) as other:
        assert other.post("/api/v1/auth/register", json={
            "username": "other_user", "nickname": "Other", "password": "auditPassword123"
        }).status_code == 201
        assert other.post("/api/v1/auth/login", json={
            "username": "other_user", "password": "auditPassword123"
        }).status_code == 200
        assert other.get(f"/api/v1/chat/sessions/{session_id}/messages").status_code == 404
        assert other.delete(f"/api/v1/chat/sessions/{session_id}").status_code == 404
        third = metadata(other.post("/api/v1/chat/stream", json={"message": "other question", "session_id": session_id}))
        # Existing API behavior creates a separate owned session for an unknown
        # or foreign ID; it never reuses that session's messages as context.
        assert third["session_id"] != session_id
        assert calls[2] == [{"role": "user", "parts": [{"text": "other question"}]}]
        assert other.get(f"/api/v1/logs?session_id={session_id}").json()["total"] == 0
        assert other.get("/api/v1/logs").json()["total"] == 2
    assert client.get(f"/api/v1/chat/sessions/{session_id}/messages").status_code == 200
    assert len(client.get(f"/api/v1/chat/sessions/{session_id}/messages").json()) == 4
