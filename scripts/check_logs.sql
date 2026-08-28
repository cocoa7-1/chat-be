-- ==========================================================
-- AI 챗봇 서비스 SQLite 검증 쿼리 스크립트 (check_logs.sql)
-- 평가자 또는 개발자가 SQLite CLI / DBeaver 등에서 직접 실행 가능
-- ==========================================================

-- 1. 등록된 모든 사용자 조회
SELECT id, username, is_active, created_at FROM users ORDER BY id ASC;

-- 2. 사용자별 대화 세션 목록 조회
SELECT s.id AS session_id, u.username, s.title, s.created_at, s.updated_at
FROM chat_sessions s
JOIN users u ON s.user_id = u.id
ORDER BY s.updated_at DESC;

-- 3. 최근 20개 대화 로그(질문/응답/지연시간/상태) 상세 조회
SELECT 
    m.id AS log_id,
    u.username,
    m.session_id,
    m.role,
    m.latency_ms,
    m.status,
    m.content,
    m.created_at
FROM chat_messages m
JOIN users u ON m.user_id = u.id
ORDER BY m.created_at DESC
LIMIT 20;

-- 4. 사용자별/상태별 통계 요약
SELECT 
    u.username,
    COUNT(m.id) AS total_messages,
    AVG(CASE WHEN m.role = 'assistant' THEN m.latency_ms ELSE NULL END) AS avg_ai_latency_ms
FROM users u
LEFT JOIN chat_messages m ON u.id = m.user_id
GROUP BY u.id, u.username;
