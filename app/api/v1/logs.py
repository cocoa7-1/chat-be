from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, desc
from app.core.database import get_db
from app.models.chat import ChatMessage, ChatSession
from app.models.user import User
from app.schemas.chat import ChatLogsResponse, ChatLogItem
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

    # If not admin, restrict to own logs
    if not current_user.is_admin:
        query = query.where(ChatMessage.user_id == current_user.id)
    elif user_id:
        query = query.where(ChatMessage.user_id == user_id)

    if session_id:
        query = query.where(ChatMessage.session_id == session_id)
    if status:
        query = query.where(ChatMessage.status == status)

    query = query.order_by(desc(ChatMessage.created_at))

    # Execute
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
        total=len(items),
        items=items
    )
