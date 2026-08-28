import json
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import select, desc
from app.core.database import get_db, SessionLocal
from app.core.logging import (
    log_request_received,
    log_db_save_success,
    log_db_save_failed,
    logger
)
from app.models.user import User
from app.models.chat import ChatSession, ChatMessage
from app.schemas.chat import (
    ChatStreamRequest,
    ChatSessionCreate,
    ChatSessionResponse,
    ChatMessageResponse
)
from app.api.deps import get_current_user
from app.services.gemini_service import gemini_service

router = APIRouter(prefix="/chat", tags=["Chat & Sessions"])


@router.get("/sessions", response_model=List[ChatSessionResponse])
def get_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieves all chat sessions for the authenticated user."""
    sessions = db.scalars(
        select(ChatSession)
        .where(ChatSession.user_id == current_user.id)
        .order_by(desc(ChatSession.updated_at))
    ).all()
    return sessions


@router.post("/sessions", response_model=ChatSessionResponse, status_code=status.HTTP_201_CREATED)
def create_session(
    session_in: ChatSessionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Creates a new chat session."""
    session = ChatSession(
        user_id=current_user.id,
        title=session_in.title or "새 대화"
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.delete("/sessions/{session_id}", status_code=status.HTTP_200_OK)
def delete_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Deletes a chat session and all its messages."""
    session = db.scalar(
        select(ChatSession)
        .where(ChatSession.id == session_id, ChatSession.user_id == current_user.id)
    )
    if not session:
        raise HTTPException(status_code=404, detail="대화 세션을 찾을 수 없습니다.")

    db.delete(session)
    db.commit()
    return {"message": "대화 세션이 삭제되었습니다.", "session_id": session_id}


@router.get("/sessions/{session_id}/messages", response_model=List[ChatMessageResponse])
def get_session_messages(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieves message history for a specific session."""
    session = db.scalar(
        select(ChatSession)
        .where(ChatSession.id == session_id, ChatSession.user_id == current_user.id)
    )
    if not session:
        raise HTTPException(status_code=404, detail="대화 세션을 찾을 수 없습니다.")

    messages = db.scalars(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at)
    ).all()
    return messages


@router.post("/stream")
async def stream_chat(
    request: Request,
    payload: ChatStreamRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Main SSE Streaming Chat Endpoint.
    Receives user message, builds context, streams AI tokens, and persists logs in SQLite.
    """
    request_id = getattr(request.state, "request_id", "req-unknown")
    user_id = current_user.id
    log_request_received(user_id=user_id, path="/api/v1/chat/stream", request_id=request_id)

    # 1. Get or create session
    session_id = payload.session_id
    if session_id:
        session = db.scalar(
            select(ChatSession).where(ChatSession.id == session_id, ChatSession.user_id == user_id)
        )
        if not session:
            session = ChatSession(user_id=user_id, title=payload.message[:30])
            db.add(session)
            db.commit()
            db.refresh(session)
            session_id = session.id
    else:
        # Create a new session with title from first question
        session = ChatSession(user_id=user_id, title=payload.message[:30])
        db.add(session)
        db.commit()
        db.refresh(session)
        session_id = session.id

    # 2. Save user message to DB
    user_msg = ChatMessage(
        session_id=session_id,
        user_id=user_id,
        role="user",
        content=payload.message,
        status="success"
    )
    db.add(user_msg)
    
    # Update session updated_at
    session.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user_msg)

    # 3. Retrieve conversation history for context (last N messages)
    past_messages = db.scalars(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at)
    ).all()

    history_context = [
        {"role": m.role, "content": m.content}
        for m in past_messages[:-1]  # Exclude the current message that was just added
    ]

    # 4. Define SSE Generator
    async def sse_event_stream():
        # Open an independent DB session inside generator for thread safety
        gen_db = SessionLocal()
        full_assistant_reply = ""
        latency_ms = 0
        error_type = None

        try:
            # Yield initial metadata event
            init_event = {
                "session_id": session_id,
                "session_title": session.title,
                "user_message_id": user_msg.id,
                "request_id": request_id
            }
            yield f"event: meta\ndata: {json.dumps(init_event, ensure_ascii=False)}\n\n"

            # Stream chunks from AI Service
            async for chunk in gemini_service.stream_chat_response(
                user_id=user_id,
                request_id=request_id,
                history=history_context,
                current_question=payload.message
            ):
                if not chunk["done"]:
                    yield f"data: {json.dumps({'text': chunk['text']}, ensure_ascii=False)}\n\n"
                else:
                    full_assistant_reply = chunk.get("full_text", "")
                    latency_ms = chunk.get("latency_ms", 0)
                    error_type = chunk.get("error")

            # 5. Persist assistant message & logs in DB
            msg_status = "error" if error_type else "success"
            assistant_msg = ChatMessage(
                session_id=session_id,
                user_id=user_id,
                role="assistant",
                content=full_assistant_reply or ("Error: " + (error_type or "Unknown")),
                latency_ms=latency_ms,
                status=msg_status,
                error_message=error_type
            )
            gen_db.add(assistant_msg)
            gen_db.commit()
            gen_db.refresh(assistant_msg)

            log_db_save_success(user_id=user_id, chat_id=assistant_msg.id, session_id=session_id)

            # Yield final completion event
            final_data = {
                "done": True,
                "message_id": assistant_msg.id,
                "latency_ms": latency_ms,
                "status": msg_status,
                "error": error_type
            }
            yield f"event: done\ndata: {json.dumps(final_data, ensure_ascii=False)}\n\n"

        except Exception as e:
            gen_db.rollback()
            log_db_save_failed(user_id=user_id, error=str(e))
            logger.error(f"Error in SSE stream loop: {e}", exc_info=True)
            err_data = {
                "done": True,
                "error": "SERVER_ERROR",
                "message": "서버 처리 중 오류가 발생했습니다."
            }
            yield f"event: error\ndata: {json.dumps(err_data, ensure_ascii=False)}\n\n"
        finally:
            gen_db.close()

    return StreamingResponse(
        sse_event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
