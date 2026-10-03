import os
from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Construction Domain Knowledge Q&A Chatbot"
    APP_ENV: str = "development"
    DEBUG: bool = True
    PORT: int = 8000
    HOST: str = "0.0.0.0"

    # Security & Auth
    SECRET_KEY: str = "feelosophysics-chatbot-super-secret-key-change-in-production"
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


@lru_cache()
def get_settings() -> Settings:
    return Settings()
