import logging
import sys
import os
from datetime import datetime

# Ensure logs directory exists
os.makedirs("logs", exist_ok=True)

# Custom Formatter for standardized log outputs
class CustomLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S")
        log_level = record.levelname
        msg = super().format(record)
        return f"[{timestamp}] {log_level:<5} {record.name}: {msg}"


def setup_logger(name: str = "chatbot") -> logging.Logger:
    """Configures and returns a structured logger."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(CustomLogFormatter())
    logger.addHandler(console_handler)

    # File handler
    file_handler = logging.FileHandler("logs/server.log", encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(CustomLogFormatter())
    logger.addHandler(file_handler)

    logger.propagate = False
    return logger


logger = setup_logger("chatbot.server")


# Structured logging helper functions
def log_request_received(user_id: str | int, path: str, request_id: str = "") -> None:
    logger.info(f"request_received user_id={user_id} path={path} request_id={request_id}")


def log_ai_call_start(user_id: str | int, request_id: str, model: str = "") -> None:
    logger.info(f"ai_call_start user_id={user_id} request_id={request_id} model={model}")


def log_ai_call_success(request_id: str, latency_ms: int) -> None:
    logger.info(f"ai_call_success request_id={request_id} latency_ms={latency_ms}")


def log_ai_call_failed(request_id: str, error: str, latency_ms: int = 0) -> None:
    logger.error(f"ai_call_failed request_id={request_id} error=\"{error}\" latency_ms={latency_ms}")


def log_db_save_success(user_id: str | int, chat_id: str | int, session_id: str | int = "") -> None:
    logger.info(f"db_save_success user_id={user_id} chat_id={chat_id} session_id={session_id}")


def log_db_save_failed(user_id: str | int, error: str) -> None:
    logger.error(f"db_save_failed user_id={user_id} error=\"{error}\"")
