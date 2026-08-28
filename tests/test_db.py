import pytest
from sqlalchemy import select
from app.core.database import SessionLocal, init_db
from app.models.user import User
from app.models.chat import ChatSession, ChatMessage
from app.core.security import get_password_hash


def test_database_models_and_relationships():
    init_db()
    db = SessionLocal()
    try:
        # Create user
        username = f"dbuser_{pytest.importorskip('time').time()}"
        user = User(username=username, password_hash=get_password_hash("pass123"))
        db.add(user)
        db.commit()
        db.refresh(user)
        assert user.id is not None

        # Create session
        session = ChatSession(user_id=user.id, title="DB 테스트 대화방")
        db.add(session)
        db.commit()
        db.refresh(session)
        assert session.id is not None

        # Create user message & assistant message
        msg1 = ChatMessage(session_id=session.id, user_id=user.id, role="user", content="테스트 질문")
        msg2 = ChatMessage(session_id=session.id, user_id=user.id, role="assistant", content="테스트 답변", latency_ms=120)
        db.add_all([msg1, msg2])
        db.commit()

        # Check relationships
        retrieved_session = db.scalar(select(ChatSession).where(ChatSession.id == session.id))
        assert len(retrieved_session.messages) == 2
        assert retrieved_session.user.username == username

        # Cascade delete test
        db.delete(user)
        db.commit()

        deleted_session = db.scalar(select(ChatSession).where(ChatSession.id == session.id))
        assert deleted_session is None
    finally:
        db.close()
