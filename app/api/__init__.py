"""app.api — FastAPI 앱 및 라우트.

RAG 파이프라인을 BFF에 노출하는 HTTP 계층. API 계약은 docs/api-spec.md.

계획 모듈:
- main.py    FastAPI 앱 생성, 미들웨어, 헬스 체크
- routes.py  POST /api/v1/rag/query — Query 그래프 호출 + SSE(EventSourceResponse) 스트리밍
- errors.py  공통 예외 → Error Response 변환 (UNAUTHORIZED / RETRIEVAL_EMPTY / LOW_CONFIDENCE 등)

이 계층은 요청 검증·응답 변환만 담당하고 비즈니스 로직은 app.pipeline / app.query에 둔다.
"""
