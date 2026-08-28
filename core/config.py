import os
from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "AI Learning Tutor Chatbot"
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
        "당신은 친절하고 전문적인 'AI/SW 개발 학습 튜터'입니다. "
        "사용자가 질문하는 프로그래밍, FastAPI 웹 개발, 데이터베이스, 리눅스, AI 기술 등에 대해 "
        "핵심 개념을 명확하고 알기 쉽게 설명하며, 실용적인 예제 코드와 마크다운 서식을 활용해 정성껏 답변하세요."
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


@lru_cache()
def get_settings() -> Settings:
    return Settings()
