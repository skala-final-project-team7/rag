"""POST /api/v1/rag/query — SSE 라우트 핸들러 [Pipeline].

--------------------------------------------------
작성자 : 최태성
작성목적 : feature11 통합 Phase 2 — Query 그래프(`app/pipeline/query_graph.py`)
          위에 얇은 HTTP 계층을 얹어 BFF가 호출하는 SSE 엔드포인트를 제공한다.
          JWT 추출 → ACL 필터 생성 → RagState 구성 → run_query → SSE 송신까지
          한 흐름으로 처리한다. api-spec.md "SSE 이벤트 순서" 정합으로 token /
          sources / verification / meta / done 5개 이벤트를 송신한다.

          PoC 제약: 답변 토큰 스트리밍은 답변 생성기 Agent 통합 후 별도 세션에서
          추가한다. 본 라우트는 token 이벤트를 1회만 송신(전체 답변)하여 SSE
          시퀀스·계약은 유지하되, Agent 통합 시 token 다중 송신으로 확장 가능한
          구조를 둔다.
작성일 : 2026-05-18
변경사항 내역 (날짜, 변경목적, 변경내용 순)
  - 2026-05-18, 최초 작성, feature11 통합 Phase 2 — query_route + SSE
    이벤트 생성기 + JWT/ACL 시스템 단 강제
--------------------------------------------------
[호환성]
  - Python 3.11.x, FastAPI 0.111+, sse-starlette 2.1+
--------------------------------------------------
"""

import json
from collections.abc import AsyncIterator
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from app.api.errors import HTTP_STATUS_BY_CODE, ErrorCode, error_response
from app.pipeline.query_graph import run_query
from app.query.acl import (
    ACLViolationError,
    PrincipalExtractionError,
    build_acl_filter,
    extract_principal,
)
from app.schemas.rag_state import RagState
from app.schemas.response import QueryResponse

router = APIRouter()


class QueryRequest(BaseModel):
    """``POST /api/v1/rag/query`` 요청 본문 (docs/api-spec.md)."""

    query: str = Field(..., min_length=1, description="사용자 자연어 질문")
    conversation_id: str | None = Field(
        default=None, description="대화 컨텍스트 ID (멀티턴 히스토리 관리자가 사용)"
    )
    jwt: str = Field(..., min_length=1, description="BFF가 전달한 JWT. sub + groups[] 포함")


def get_graph(request: Request) -> Any:
    """FastAPI Depends — lifespan에서 만든 컴파일된 그래프를 반환한다.

    테스트에서는 ``app.dependency_overrides[get_graph] = lambda: test_graph`` 로
    교체할 수 있다.
    """
    return request.app.state.graph


# FastAPI Annotated 패턴 — Depends를 함수 인자 기본값으로 쓰는 B008 회피.
GraphDep = Annotated[Any, Depends(get_graph)]


def _error_json(code: ErrorCode, message: str) -> JSONResponse:
    """ErrorResponse를 HTTP 상태와 함께 JSON으로 반환한다 (SSE 아님)."""
    body = error_response(code, message).model_dump(mode="json")
    return JSONResponse(status_code=HTTP_STATUS_BY_CODE[code], content=body)


def _sse_payload(response: QueryResponse) -> list[dict[str, str]]:
    """QueryResponse → SSE 이벤트 시퀀스 (api-spec.md "SSE 이벤트 순서").

    이벤트 5종:
        1. ``token`` — 답변 텍스트(Markdown). PoC는 1회 송신(전체 답변).
        2. ``sources`` — 출처 카드 배열.
        3. ``verification`` — 문장별 검증 결과.
        4. ``meta`` — intent / used_llm / feedback_enabled / latency_ms.
        5. ``done`` — 종료 마커.
    """
    sources_payload = [source.model_dump(mode="json") for source in response.sources]
    verification_payload = [item.model_dump(mode="json") for item in response.verification]
    meta_payload = {
        "intent": response.intent.value,
        "used_llm": response.used_llm.value,
        "feedback_enabled": response.feedback_enabled,
        "latency_ms": response.latency_ms,
    }
    return [
        {"event": "token", "data": response.answer},
        {"event": "sources", "data": json.dumps(sources_payload, ensure_ascii=False)},
        {
            "event": "verification",
            "data": json.dumps(verification_payload, ensure_ascii=False),
        },
        {"event": "meta", "data": json.dumps(meta_payload, ensure_ascii=False)},
        {"event": "done", "data": ""},
    ]


async def _event_stream(response: QueryResponse) -> AsyncIterator[dict[str, str]]:
    """SSE 이벤트 비동기 생성기 — sse-starlette EventSourceResponse 입력."""
    for event in _sse_payload(response):
        yield event


@router.post("/api/v1/rag/query")
async def query_route(payload: QueryRequest, graph: GraphDep) -> Any:
    """사용자 질의를 받아 ACL 기반 검색·답변·검증을 수행하고 SSE로 응답한다.

    docs/api-spec.md "POST /api/v1/rag/query" 정합:
      1. JWT 클레임 추출 — 실패 시 401 ``UNAUTHORIZED``.
      2. ``build_acl_filter`` 로 Qdrant should-OR 필터 생성.
      3. ``RagState`` 구성 후 ``run_query`` 로 그래프 실행.
      4. ``QueryResponse`` 를 SSE 이벤트 5종으로 송신.
    예외 처리는 보수적으로 — 그래프 내부 예외(ACL 미주입 등)는 502 ``UPSTREAM_
    LLM_ERROR`` 로 매핑.
    """
    try:
        principal = extract_principal(payload.jwt)
    except PrincipalExtractionError as exc:
        return _error_json(ErrorCode.UNAUTHORIZED, str(exc))

    acl_filter = build_acl_filter(principal.user_id, principal.groups)
    state = RagState(
        query=payload.query,
        user_id=principal.user_id,
        groups=principal.groups,
        conversation_id=payload.conversation_id,
        acl_filter=acl_filter,
    )

    try:
        response = run_query(state, graph=graph)
    except ACLViolationError as exc:
        # 시스템 단 안전망 — build_acl_filter는 항상 유효 필터를 만들므로 정상 흐름에선
        # 도달하지 않지만, 그래프 내부 버그/우회 시 ACL 위반이 표면화되어야 한다.
        return _error_json(ErrorCode.UPSTREAM_LLM_ERROR, f"ACL 시스템 오류: {exc}")
    except Exception as exc:  # noqa: BLE001 — 상류 LLM/네트워크 예외 광범위 캐치 (PoC)
        return _error_json(ErrorCode.UPSTREAM_LLM_ERROR, str(exc))

    return EventSourceResponse(_event_stream(response))
