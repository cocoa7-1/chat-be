import asyncio
import time
import json
from typing import AsyncGenerator, List, Dict, Any, Optional
from app.core.config import get_settings
from app.core.logging import (
    log_ai_call_start,
    log_ai_call_success,
    log_ai_call_failed
)

settings = get_settings()


class GeminiService:
    """Service wrapper for Google Gemini API with Timeout, Context, and Mock Fallback."""

    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.model_name = settings.GEMINI_MODEL_NAME
        self.timeout_seconds = settings.AI_TIMEOUT_SECONDS
        self.system_instruction = settings.SYSTEM_INSTRUCTION
        self._client = None

        if self.api_key:
            try:
                from google import genai
                from google.genai import types
                self._client = genai.Client(api_key=self.api_key)
                self._types = types
            except Exception as e:
                # If library not yet installed or key issue, fallback gracefully
                self._client = None

    def is_live_api(self) -> bool:
        """Returns True if live Gemini API is configured and available."""
        return bool(self._client and self.api_key)

    def _build_context_messages(self, history: List[Dict[str, str]], current_question: str) -> List[Any]:
        """Formats conversation history into Gemini SDK content objects or dicts."""
        contents = []
        
        # Take the most recent N messages
        recent_history = history[-settings.MAX_HISTORY_MESSAGES:] if history else []
        for msg in recent_history:
            role = "user" if msg["role"] == "user" else "model"
            contents.append({
                "role": role,
                "parts": [{"text": msg["content"]}]
            })
            
        # Append current user prompt
        contents.append({
            "role": "user",
            "parts": [{"text": current_question}]
        })
        return contents

    async def stream_chat_response(
        self,
        user_id: int,
        request_id: str,
        history: List[Dict[str, str]],
        current_question: str
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Streams AI response token-by-token using SSE format with timeout protection.
        Yields dicts with {"text": str, "done": bool, "latency_ms": int, "error": str, "full_text": str}.
        """
        start_time = time.perf_counter()
        log_ai_call_start(user_id=user_id, request_id=request_id, model=self.model_name)
        
        full_response = ""

        # Case 1: Live Gemini API
        if self.is_live_api():
            try:
                contents = self._build_context_messages(history, current_question)
                if hasattr(self, "_types") and self._types:
                    config = self._types.GenerateContentConfig(
                        system_instruction=self.system_instruction,
                        temperature=0.7
                    )
                else:
                    config = {
                        "system_instruction": self.system_instruction,
                        "temperature": 0.7,
                    }

                # Start streaming with timeout protection on initial connection
                response_stream = await asyncio.wait_for(
                    self._client.aio.models.generate_content_stream(
                        model=self.model_name,
                        contents=contents,
                        config=config
                    ),
                    timeout=self.timeout_seconds
                )

                async for chunk in response_stream:
                    if chunk.text:
                        full_response += chunk.text
                        yield {
                            "text": chunk.text,
                            "done": False,
                            "error": None
                        }

                latency_ms = int((time.perf_counter() - start_time) * 1000)
                log_ai_call_success(request_id=request_id, latency_ms=latency_ms)

                yield {
                    "text": "",
                    "done": True,
                    "full_text": full_response,
                    "latency_ms": latency_ms,
                    "error": None
                }
                return

            except asyncio.TimeoutError:
                latency_ms = int((time.perf_counter() - start_time) * 1000)
                error_msg = "AI_TIMEOUT"
                log_ai_call_failed(request_id=request_id, error=error_msg, latency_ms=latency_ms)
                friendly_err = "\n\n⚠️ **현재 응답이 지연되고 있어요. 잠시 후 다시 시도해 주세요. (error: AI_TIMEOUT)**"
                full_response += friendly_err
                yield {
                    "text": friendly_err,
                    "done": False,
                    "error": None
                }
                yield {
                    "text": "",
                    "done": True,
                    "full_text": full_response,
                    "latency_ms": latency_ms,
                    "error": "AI_TIMEOUT"
                }
                return
            except Exception as e:
                latency_ms = int((time.perf_counter() - start_time) * 1000)
                log_ai_call_failed(request_id=request_id, error=str(e), latency_ms=latency_ms)
                err_str = str(e)
                if "404" in err_str or "not found" in err_str.lower():
                    friendly_err = (
                        f"\n\n⚠️ **AI 모델(`{self.model_name}`)을 찾을 수 없습니다. (error: 404 NOT_FOUND)**\n\n"
                        f"> 💡 **해결 방법**: `.env` 파일의 `GEMINI_MODEL_NAME`을 `gemma-4-26b-a4b-it` 또는 `gemini-2.5-flash`로 지정해주세요."
                    )
                else:
                    friendly_err = f"\n\n⚠️ **AI 서비스 오류가 발생했습니다: {err_str[:100]}**"
                
                full_response += friendly_err
                yield {
                    "text": friendly_err,
                    "done": False,
                    "error": None
                }
                yield {
                    "text": "",
                    "done": True,
                    "full_text": full_response,
                    "latency_ms": latency_ms,
                    "error": "AI_SERVICE_ERROR"
                }
                return

        # Case 2: Smart Demo / Mock Fallback Mode
        mock_reply = self._generate_mock_reply(current_question)
        chunks = self._chunk_text(mock_reply)

        for chunk in chunks:
            await asyncio.sleep(0.04)  # Natural typing speed simulation
            full_response += chunk
            yield {
                "text": chunk,
                "done": False,
                "error": None
            }

        latency_ms = int((time.perf_counter() - start_time) * 1000)
        log_ai_call_success(request_id=request_id, latency_ms=latency_ms)

        yield {
            "text": "",
            "done": True,
            "full_text": full_response,
            "latency_ms": latency_ms,
            "error": None
        }

    def _generate_mock_reply(self, question: str) -> str:
        """Generates a rich, educational mock response for AI/SW students."""
        q_lower = question.lower()

        if "안녕" in q_lower or "hi" in q_lower or "hello" in q_lower or "반가" in q_lower:
            return (
                "안녕하세요! 저는 AI/SW 학습 튜터 챗봇입니다. 🤖\n\n"
                "FastAPI 백엔드, 데이터베이스(SQLite/SQLAlchemy), 리눅스 서버 운영, "
                "AI API 연동 및 웹 개발 관련 질문이 있으시면 무엇이든 편하게 물어보세요!"
            )
        elif "fastapi" in q_lower or "웹" in q_lower or "서버" in q_lower:
            return (
                "### 🚀 FastAPI의 핵심 특징과 파이프라인\n\n"
                "**FastAPI**는 현대적인 고성능 Python 웹 프레임워크입니다:\n\n"
                "1. **비동기 처리(Async/Await)**: `async def`를 통해 I/O 바운드 작업(AI API 호출, DB 쿼리)을 논블로킹으로 처리합니다.\n"
                "2. **Pydantic 데이터 검증**: 요청/응답 스키마를 타입 힌트 기반으로 자동 검증하고 직렬화합니다.\n"
                "3. **의존성 주입(Dependency Injection)**: `Depends(get_db)`, `Depends(get_current_user)`로 인증 및 DB 세션을 깔끔하게 분리합니다.\n\n"
                "```python\n"
                "@app.post('/api/chat')\n"
                "async def chat(request: ChatRequest, user: User = Depends(get_current_user)):\n"
                "    response = await ai_service.generate(request.message)\n"
                "    return {'response': response}\n"
                "```\n\n"
                "> 💡 *[Demo 모드] 실제 Gemini API 연동을 원하시면 `.env` 파일에 `GEMINI_API_KEY`를 설정하세요.*"
            )
        elif "db" in q_lower or "데이터베이스" in q_lower or "sqlite" in q_lower or "로그" in q_lower:
            return (
                "### 🗄️ 대화 로그 영속화 및 데이터 모델링\n\n"
                "AI 챗봇 서비스에서 대화 로그 저장은 품질 관리와 사용자 경험에 필수적입니다:\n\n"
                "- **User (사용자)**: 계정 식별자 및 암호화된 비밀번호 관리\n"
                "- **ChatSession (대화방)**: 다중 대화 스레드 분리\n"
                "- **ChatMessage (메시지/로그)**: 질문, AI 응답, 지연시간(latency_ms), 상태(status), 생성일시 저장\n\n"
                "상단 네비게이션의 **[대화 로그 확인]** 메뉴에서 현재 DB에 적재된 실시간 로그를 테이블로 직접 검증할 수 있습니다!"
            )
        else:
            return (
                f"질문해주신 **\"{question}\"**에 대한 답변입니다.\n\n"
                "AI/SW 개발에서는 요청 수신 $\\rightarrow$ 비즈니스 로직(AI 호출) $\\rightarrow$ 결과 응답 $\\rightarrow$ DB 로깅의 전체 파이프라인이 "
                "안정적으로 유기 결합되어야 합니다.\n\n"
                "- **입력 검증**: 유효하지 않은 입력이나 악의적인 요청을 차단합니다.\n"
                "- **타임아웃 방어**: 외부 AI API 지연 시 시스템이 멈추지 않도록 예외 처리가 필수입니다.\n"
                "- **대화 문맥 유지**: 이전 질의응답 내역을 프롬프트에 주입하여 연속성 있는 대화를 구성합니다.\n\n"
                "> 💡 *[Demo 모드] 실제 Gemini API 연동을 원하시면 `.env` 파일에 `GEMINI_API_KEY`를 설정하세요.*"
            )

    def _chunk_text(self, text: str, chunk_size: int = 4) -> List[str]:
        """Splits text into small token-like chunks for mock streaming."""
        return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]


# Global service instance
gemini_service = GeminiService()
