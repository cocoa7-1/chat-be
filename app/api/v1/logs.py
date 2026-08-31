from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, desc, func
from app.core.database import get_db
from app.models.chat import ChatMessage, ChatSession
from app.models.user import User
from app.schemas.chat import ChatLogsResponse, ChatLogItem, ChatStatsResponse
from app.api.deps import get_current_user

router = APIRouter(prefix="/logs", tags=["Logs & Evaluation"])


@router.get("", response_model=ChatLogsResponse)
def get_chat_logs(
    user_id: Optional[int] = Query(None, description="특정 사용자 ID로 필터링"),
    session_id: Optional[int] = Query(None, description="특정 세션 ID로 필터링"),
    status: Optional[str] = Query(None, description="상태(success, error, timeout) 필터링"),
    limit: int = Query(50, ge=1, le=200, description="조회할 개수"),
    offset: int = Query(0, ge=0, description="오프셋"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Evaluation & Audit Endpoint: Retrieves flattened conversation logs with user information and latency.
    Non-admin users see their own logs; admin users can filter by any user.
    """
    query = select(ChatMessage, User.username).join(User, ChatMessage.user_id == User.id)
    count_query = select(func.count(ChatMessage.id))

    # If not admin, restrict to own logs
    if not current_user.is_admin:
        query = query.where(ChatMessage.user_id == current_user.id)
        count_query = count_query.where(ChatMessage.user_id == current_user.id)
    elif user_id:
        query = query.where(ChatMessage.user_id == user_id)
        count_query = count_query.where(ChatMessage.user_id == user_id)

    if session_id:
        query = query.where(ChatMessage.session_id == session_id)
        count_query = count_query.where(ChatMessage.session_id == session_id)
    if status:
        query = query.where(ChatMessage.status == status)
        count_query = count_query.where(ChatMessage.status == status)

    total = db.scalar(count_query) or 0
    query = query.order_by(desc(ChatMessage.created_at))

    # Execute pagination
    results = db.execute(query.offset(offset).limit(limit)).all()
    
    items = []
    for msg, username in results:
        items.append(ChatLogItem(
            id=msg.id,
            user_id=msg.user_id,
            username=username,
            session_id=msg.session_id,
            role=msg.role,
            content=msg.content,
            latency_ms=msg.latency_ms or 0,
            status=msg.status,
            error_message=msg.error_message,
            created_at=msg.created_at
        ))

    return ChatLogsResponse(
        total=total,
        items=items
    )


@router.get("/stats", response_model=ChatStatsResponse)
def get_chat_stats(
    user_id: Optional[int] = Query(None, description="특정 사용자 ID 통계 (관리자 전용)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Performance & Operational KPI Endpoint:
    Returns conversation volumes, sessions, average latency, and success rates.
    """
    target_user_id = user_id if (current_user.is_admin and user_id) else (None if (current_user.is_admin and not user_id) else current_user.id)

    # Base message queries
    msg_query = select(ChatMessage)
    sess_query = select(ChatSession)

    if target_user_id:
        msg_query = msg_query.where(ChatMessage.user_id == target_user_id)
        sess_query = sess_query.where(ChatSession.user_id == target_user_id)

    all_messages = db.scalars(msg_query).all()
    total_sessions = len(db.scalars(sess_query).all())

    user_questions = [m for m in all_messages if m.role == "user"]
    ai_answers = [m for m in all_messages if m.role == "assistant"]
    success_answers = [m for m in ai_answers if m.status == "success"]

    latencies = [m.latency_ms for m in success_answers if m.latency_ms]
    avg_latency = int(sum(latencies) / len(latencies)) if latencies else 0

    success_rate = (
        round((len(success_answers) / len(user_questions)) * 100, 1)
        if user_questions
        else 100.0
    )

    return ChatStatsResponse(
        total_messages=len(all_messages),
        total_questions=len(user_questions),
        total_answers=len(ai_answers),
        total_sessions=total_sessions,
        avg_latency_ms=avg_latency,
        success_rate_percent=success_rate
    )

