import os
from functools import lru_cache
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

DEVELOPMENT_SECRET_KEY = "feelosophysics-chatbot-super-secret-key-change-in-production"


class Settings(BaseSettings):
    APP_NAME: str = "Construction Domain Knowledge Q&A Chatbot"
    APP_ENV: str = "development"
    DEBUG: bool = True
    PORT: int = 8000
    HOST: str = "0.0.0.0"

    # Security & Auth
    SECRET_KEY: str = DEVELOPMENT_SECRET_KEY
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day
    COOKIE_NAME: str = "access_token"

    # Database
    DATABASE_URL: str = "sqlite:///./chatbot.db"

    # AI / Gemma Model Settings
    GEMINI_API_KEY: Optional[str] = ""
    GEMINI_MODEL_NAME: str = "gemma-4-26b-a4b-it"  # AI Studio의 Gemma 4 26B 정식 식별자
    AI_TIMEOUT_SECONDS: int = 30
    MAX_HISTORY_MESSAGES: int = 10

    # Per-process safeguards for the existing single-worker deployment.
    REGISTER_REQUESTS_PER_MINUTE: int = Field(5, ge=1)
    LOGIN_REQUESTS_PER_MINUTE: int = Field(10, ge=1)
    CHAT_REQUESTS_PER_MINUTE: int = Field(6, ge=1)
    CHAT_GLOBAL_REQUESTS_PER_MINUTE: int = Field(20, ge=1)
    CHAT_USER_CONCURRENCY: int = Field(1, ge=1)
    CHAT_GLOBAL_CONCURRENCY: int = Field(3, ge=1)

    # System Persona
    SYSTEM_INSTRUCTION: str = (
        "당신은 친절하고 전문적인 '건설 도메인 지식 & 상식 Q&A 전문 어시스턴트'입니다. "
        "사용자가 질문하는 시공/공정(골조, 마감, 방수, 조적, RC구조, 가설), "
        "인허가/행정 절차(건축허가, 착공신고, 사용승인, 준공검사), "
        "계약/비용(도급, 하도급, 평당 공사비, 공사대금 분할, 견적서), "
        "참여 주체(발주자, 시공사, 감리자, 건축사, 하도급업체), "
        "자재/구조(철근, 콘크리트, 단열재, 방수재, 구조 방식), "
        "개념 비교(신축 vs 리모델링 vs 재건축, 원도급 vs 하도급, 감리 vs 감독), "
        "플랜트/산업설비 건설(EPC, FEED, 화공/발전 플랜트, 턴키 계약)에 대해 "
        "일반인도 이해하기 쉽고 명확하게 설명하며, 핵심 개념을 친절한 마크다운 서식으로 답변하세요."
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    def validate_production_security(self) -> None:
        if self.APP_ENV.strip().lower() in {"production", "prod"}:
            if self.SECRET_KEY.strip() == DEVELOPMENT_SECRET_KEY or len(self.SECRET_KEY.strip().encode("utf-8")) < 32:
                # A model-validator error can print the whole settings input,
                # including secrets. Raise a fixed message outside validation.
                raise RuntimeError("Production SECRET_KEY must be a unique random key of at least 32 bytes.")


@lru_cache()
def get_settings() -> Settings:
    settings = Settings()
    settings.validate_production_security()
    return settings
