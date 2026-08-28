from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict, field_validator


class ChatStreamRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000, description="사용자 질문 (1~2000자)")
    session_id: Optional[int] = Field(None, description="대화 세션 ID (없을 경우 새 세션 자동 생성)")

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("질문 내용을 입력해주세요.")
        if len(cleaned) > 2000:
            raise ValueError("질문은 최대 2,000자까지 입력 가능합니다.")
        return cleaned


class ChatSessionCreate(BaseModel):
    title: Optional[str] = Field("새 대화", max_length=100)


class ChatMessageResponse(BaseModel):
    id: int
    session_id: int
    user_id: int
    role: str
    content: str
    latency_ms: Optional[int] = 0
    status: str
    error_message: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatSessionResponse(BaseModel):
    id: int
    user_id: int
    title: str
    created_at: datetime
    updated_at: datetime
    messages: Optional[List[ChatMessageResponse]] = []

    model_config = ConfigDict(from_attributes=True)


class ChatLogItem(BaseModel):
    id: int
    user_id: int
    username: str
    session_id: int
    role: str
    content: str
    latency_ms: Optional[int] = 0
    status: str
    error_message: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatLogsResponse(BaseModel):
    total: int
    items: List[ChatLogItem]
