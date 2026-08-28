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
                "안녕하세요! 저는 **건설 안전 및 시공 관리 전문 AI 튜터**입니다. 👷‍♂️🏗️\n\n"
                "산업안전보건법, 중대재해처벌법, 콘크리트/골조 시공 지침, 위험성 평가(TBM), "
                "현장 안전 수칙 및 FastAPI 기반 시스템 구조에 대해 무엇이든 편하게 물어보세요!"
            )
        elif "추락" in q_lower or "안전" in q_lower or "중대재해" in q_lower or "개구부" in q_lower:
            return (
                "### 🏗️ 건설 현장 추락 재해 예방 및 안전 기준\n\n"
                "**1. 핵심 3대 안전 시설물 설치 기준**\n"
                "- **안전난간**: 상부 난간대(90~120cm), 중간 난간대(중간 높이), 발끝막이판(10cm 이상)\n"
                "- **추락방호망**: 작업면으로부터 10m 이내 설치 (수평 처짐률 12% 이상 확보)\n"
                "- **개구부 덮개**: 임의 개방 방지 조치 및 \"추락위험\" 경고 표지 부착\n\n"
                "**2. 중대재해처벌법 대비 핵심 체크리스트**\n"
                "- 일일 작업 전 **TBM(Tool Box Meeting)**을 통한 위험성 평가 전파\n"
                "- 근로자 개인보호구(안전모, 안전대 2개소 걸이, 안전화) 착용 의무화\n\n"
                "> 💡 *[Demo 모드] 실제 Google AI Studio(Gemma 4) 연동을 원하시면 `.env` 파일에 `GEMINI_API_KEY`를 설정하세요.*"
            )
        elif "콘크리트" in q_lower or "타설" in q_lower or "시공" in q_lower or "양생" in q_lower:
            return (
                "### 📐 콘크리트 타설 및 품질 관리 지침\n\n"
                "**1. 동절기/한중 콘크리트 (일평균 기온 4℃ 이하)**\n"
                "- **초기 동결 방지**: 압축강도 $5\\text{ MPa}$ 발현 시까지 온도를 $5^\\circ\\text{C}$ 이상 유지\n"
                "- **보온 양생**: 열풍기, 방풍막, 갈탄 지양(일산화탄소 질식 위험 $\\rightarrow$ 열풍기 권장)\n\n"
                "**2. 타설 시 주의사항**\n"
                "- 이어치기 시간 한도: 외기온 25℃ 이상 시 2시간, 25℃ 미만 시 2.5시간 이내\n"
                "- 진동기(Vibrator) 사용: 과다 진동 시 재료 분리 발생 $\\rightarrow$ 수직으로 5~15초간 삽입\n\n"
                "> 💡 *[Demo 모드] 실제 Google AI Studio(Gemma 4) 연동을 원하시면 `.env` 파일에 `GEMINI_API_KEY`를 설정하세요.*"
            )
        elif "fastapi" in q_lower or "웹" in q_lower or "서버" in q_lower:
            return (
                "### 🚀 FastAPI의 핵심 특징과 파이프라인\n\n"
                "**FastAPI**는 현대적인 고성능 Python 웹 프레임워크입니다:\n\n"
                "1. **비동기 처리(Async/Await)**: `async def`를 통해 I/O 바운드 작업(AI API 호출, DB 쿼리)을 논블로킹으로 처리합니다.\n"
                "2. **Pydantic 데이터 검증**: 요청/응답 스키마를 타입 힌트 기반으로 자동 검증하고 직렬화합니다.\n"
                "3. **의존성 주입(Dependency Injection)**: `Depends(get_db)`, `Depends(get_current_user)`로 인증 및 DB 세션을 깔끔하게 분리합니다.\n\n"
                "```python\n"
                "@app.post('/api/v1/chat/stream')\n"
                "async def stream_chat(request: ChatMessageCreate, user: User = Depends(get_current_user)):\n"
                "    return StreamingResponse(gemini_service.stream_chat_response(...))\n"
                "```\n\n"
                "> 💡 *[Demo 모드] 실제 Gemini API 연동을 원하시면 `.env` 파일에 `GEMINI_API_KEY`를 설정하세요.*"
            )
        elif "db" in q_lower or "데이터베이스" in q_lower or "sqlite" in q_lower or "로그" in q_lower:
            return (
                "### 🗄️ 대화 로그 영속화 및 데이터 모델링 (Role 2)\n\n"
                "AI 챗봇 서비스에서 대화 로그 저장은 품질 관리와 사용자 경험에 필수적입니다:\n\n"
                "- **User (사용자)**: 계정 식별자 및 암호화된 비밀번호 관리 (`users`)\n"
                "- **ChatSession (대화방)**: 다중 대화 스레드 분리 (`chat_sessions`)\n"
                "- **ChatMessage (메시지/로그)**: 질문, AI 답변, 지연시간(latency_ms), 상태(status), 생성일시 저장 (`chat_messages`)\n\n"
                "상단 네비게이션의 **[대화 로그 확인]** 메뉴에서 현재 DB에 적재된 실시간 로그를 테이블로 직접 검증할 수 있습니다!"
            )
        else:
            return (
                f"질문해주신 **\"{question}\"**에 대한 건설 튜터 답변입니다.\n\n"
                "건설 실무 및 AI/SW 시스템 개발에서는 요청 수신 $\\rightarrow$ 도메인 분석/AI 추론 $\\rightarrow$ 결과 응답 $\\rightarrow$ DB 로깅의 전체 파이프라인이 "
                "안정적으로 유기 결합되어야 합니다.\n\n"
                "- **현장 안전 수칙 준수**: 법적 기준(산업안전보건법) 및 KCS 표준시방서 준수\n"
                "- **타임아웃 방어**: 외부 AI API 지연 시 시스템이 멈추지 않도록 예외 처리 필수\n"
                "- **대화 문맥 유지**: 이전 질의응답 내역을 프롬프트에 주입하여 연속성 있는 답변 생성\n\n"
                "> 💡 *[Demo 모드] 실제 Gemini API 연동을 원하시면 `.env` 파일에 `GEMINI_API_KEY`를 설정하세요.*"
            )

    def _chunk_text(self, text: str, chunk_size: int = 4) -> List[str]:
        """Splits text into small token-like chunks for mock streaming."""
        return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]


# Global service instance
gemini_service = GeminiService()
