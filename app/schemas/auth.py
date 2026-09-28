from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict, field_validator

ALLOWED_ROLES = ("safety_manager", "site_worker", "field_engineer")


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=30, description="사용자 아이디 (3~30자)")
    nickname: str = Field(..., min_length=1, max_length=30, description="닉네임 (1~30자)")
    password: str = Field(..., min_length=8, max_length=100, description="비밀번호 (8자 이상)")
    role: Optional[str] = Field("site_worker", description="건설 현장 직책 (safety_manager/site_worker/field_engineer)")

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("아이디를 입력해주세요.")
        return v

    @field_validator("nickname")
    @classmethod
    def validate_nickname(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("닉네임을 입력해주세요.")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not v or len(v.strip()) < 8:
            raise ValueError("비밀번호는 최소 8자 이상이어야 합니다.")
        return v

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: Optional[str]) -> str:
        if not v:
            return "site_worker"
        if v not in ALLOWED_ROLES:
            raise ValueError(f"직책은 {', '.join(ALLOWED_ROLES)} 중 하나여야 합니다.")
        return v


class UserLogin(BaseModel):
    username: str = Field(..., description="사용자 아이디")
    password: str = Field(..., description="비밀번호")


class UserResponse(BaseModel):
    id: int
    username: str
    nickname: str
    role: str
    is_active: bool
    is_admin: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class TokenData(BaseModel):
    user_id: Optional[int] = None
    username: Optional[str] = None


class PasswordChange(BaseModel):
    current_password: str = Field(..., description="현재 비밀번호")
    new_password: str = Field(..., min_length=8, max_length=100, description="새 비밀번호 (8자 이상)")

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        if not v or len(v.strip()) < 8:
            raise ValueError("비밀번호는 최소 8자 이상이어야 합니다.")
        return v
