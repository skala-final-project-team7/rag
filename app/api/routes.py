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
  - 2026-05-19, feature14 SSE token streaming — ``QueryRequest.stream`` (default
    False) 필드 추가 + ``query_route`` 가 stream=True 분기를 처리한다. 분기 흐름:
    (1) PoC 안전 fallback 검사 — ``state.deps.generator_provider`` 가 None 이거나
        ``settings.openai_api_key`` 가 비어 있으면 stream=true 라도 기존 run_query
        흐름으로 자동 fallback (PoC 환경에서도 동작 유지).
    (2) 운영 streaming — ``build_query_graph_for_streaming`` 으로 rerank 까지 실행
        한 RagState 를 받고, top_chunks 가 비어 있으면 (RETRIEVAL_EMPTY) 기존 표준
        응답을 그대로 송신한다. top_chunks 가 있으면 ``stream_openai_answer`` 로
        OpenAI Chat Completions streaming 호출 → token chunk 다중 송신 → 답변
        누적 후 ``verify_pipeline_node`` (1+2단계 검증) → ``format_response`` 로
        저신뢰/차단 분기 적용 → sources/verification/meta/done 송신.
    설계서 §4.6.4 정합으로 첫 토큰부터 사용자에게 즉시 송신해 P95 5초 KPI 달성.
  - 2026-05-19, feature15 streaming Rate Limit fallback — 설계서 §4.6.5 정합.
    ``stream_openai_answer`` 호출 중 OpenAI ``RateLimitError`` 캐치 후 ``fallback
    _model`` (GPT-4o-mini) 로 재시도. 첫 토큰 송신 전 발생 시 그대로 fallback,
    첫 토큰 송신 후 발생 시 누적 토큰을 빈 ``token`` 이벤트로 clear 한 뒤
    fallback 으로 재시작 (UI 가 부분 답변을 덮어쓸 수 있도록). ``logging.warning``
    으로 운영 로그 기록 + meta.used_llm 이 GPT-4o-mini 로 표시되어 사용자가
    다운그레이드를 인지할 수 있다. 두 번째 시도 중에도 RateLimitError → 상위
    UPSTREAM_LLM_ERROR 502 매핑 (라우트 try/except 가 흡수).
  - 2026-05-19, feature17a — streaming Rate Limit fallback 발생 시 ``llm
    _fallback_total`` Prometheus 카운터 inc. ``answer_generation_latency
    _seconds`` 히스토그램은 generator 어댑터에서 이미 측정하므로 본 라우트
    에서는 별도 observe 하지 않는다 (streaming 경로는 generator 노드 미경유
    이므로 streaming 시작 ~ 마지막 토큰 도착 구간 own observe). 설계서 §6.4
    KPI 정합.
--------------------------------------------------
[호환성]
  - Python 3.11.x, FastAPI 0.111+, sse-starlette 2.1+
--------------------------------------------------
"""

import json
import logging
import time
from collections.abc import AsyncIterator
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from app.api.errors import HTTP_STATUS_BY_CODE, ErrorCode, error_response
from app.metrics import llm_fallback_total
from app.pipeline.nodes import verify_pipeline_node
from app.pipeline.query_graph import run_query
from app.query.acl import (
    ACLViolationError,
    PrincipalExtractionError,
    build_acl_filter,
    extract_principal,
)
from app.query.formatter import format_response
from app.query.openai_streaming import stream_openai_answer
from app.schemas.enums import Intent, LlmModel
from app.schemas.rag_state import RagState
from app.schemas.response import QueryResponse

_LOGGER = logging.getLogger(__name__)

router = APIRouter()


class QueryRequest(BaseModel):
    """``POST /api/v1/rag/query`` 요청 본문 (docs/api-spec.md)."""

    query: str = Field(..., min_length=1, description="사용자 자연어 질문")
    conversation_id: str | None = Field(
        default=None, description="대화 컨텍스트 ID (멀티턴 히스토리 관리자가 사용)"
    )
    jwt: str = Field(..., min_length=1, description="BFF가 전달한 JWT. sub + groups[] 포함")
    stream: bool = Field(
        default=False,
        description=(
            "True 면 SSE 토큰 스트리밍 모드 — 답변을 OpenAI Streaming API 로 토큰 chunk "
            "단위 송신. False 면 답변 전체를 1회 token 이벤트로 송신 (기본값, BFF/테스트 "
            "회귀 호환). PoC 환경 (OpenAI 키 없음) 에서는 True 라도 자동 fallback."
        ),
    )


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


def _resolve_used_llm(model: str) -> LlmModel:
    """generator_config.model 문자열을 LlmModel enum 으로 안전 변환.

    enum 에 없는 모델명 (예: ``gpt-4o-2024-05-13``) 이면 GPT_4O 로 fallback. UI 메타
    표시 정합 — 응답 객체 스키마 (``used_llm: LlmModel``) 를 강제하기 위한 단순 정합.
    """
    try:
        return LlmModel(model)
    except ValueError:
        return LlmModel.GPT_4O


def _should_fallback_to_non_streaming(request: Request) -> bool:
    """stream=True 가 들어와도 PoC 환경이면 비-streaming 으로 자동 fallback.

    fallback 조건 (OR):
      - ``app.state.deps.generator_provider`` 가 None — PoC 경로는 fake provider 자동
        주입이라 OpenAI streaming 호출 자체가 불가능.
      - ``app.state.settings.openai_api_key`` 가 빈 SecretStr — 키 없이는 호출 실패.

    Returns:
        True 면 stream=True 무시하고 기존 run_query 흐름으로 처리해야 한다.
    """
    deps = getattr(request.app.state, "deps", None)
    if deps is None or getattr(deps, "generator_provider", None) is None:
        return True
    settings = getattr(request.app.state, "settings", None)
    if settings is None:
        return True
    api_key_value = settings.openai_api_key.get_secret_value()
    return not api_key_value


async def _streaming_event_stream(
    *,
    request: Request,
    state: RagState,
) -> AsyncIterator[dict[str, str]]:
    """SSE 토큰 스트리밍 흐름 (설계서 §4.6.4).

    1. ``app.state.streaming_graph`` 로 history → router → search → (empty | rerank)
       까지 실행 → RagState 갱신 (top_chunks + sources 채워짐).
    2. RETRIEVAL_EMPTY 분기 (top_chunks 비어 있고 answer 가 표준 메시지) → 기존
       _sse_payload 로 token 1회 + sources/verification/meta/done 5종 송신.
    3. rerank 결과 있음 → ``stream_openai_answer`` 호출, token chunk 다중 yield
       (sse-starlette 에 ``event="token"`` 형식으로 즉시 전달).
    4. 누적 답변에 대해 ``verify_pipeline_node`` (1+2단계) 호출 후 ``format_response``
       로 저신뢰/차단 분기 적용 → sources/verification/meta/done 송신.
    """
    started = time.perf_counter_ns()

    streaming_graph = request.app.state.streaming_graph
    result_dict = streaming_graph.invoke(state)
    rerank_state = RagState.model_validate(result_dict)

    intent = rerank_state.intent or Intent.OPERATION_GUIDE
    settings = request.app.state.settings
    deps = request.app.state.deps

    # 검색 0건 분기 — empty_retrieval 노드가 answer/used_llm/intent 를 채워준다.
    if not rerank_state.top_chunks:
        used_llm = rerank_state.used_llm or LlmModel.GPT_4O_MINI
        elapsed_ms = (time.perf_counter_ns() - started) // 1_000_000
        response = format_response(
            answer=rerank_state.answer or "",
            sources=rerank_state.sources,
            verification=rerank_state.verification,
            intent=intent,
            used_llm=used_llm,
            latency_ms=int(elapsed_ms),
        )
        for event in _sse_payload(response):
            yield event
        return

    # rerank 분기 — OpenAI streaming 으로 token chunk 다중 송신.
    api_key = settings.openai_api_key.get_secret_value()
    generator_config = deps.generator_config
    # generator_config 가 None 이면 (외부 사용자 정의 generator_node 만 주입한 경우)
    # _should_fallback_to_non_streaming 단계에서 이미 걸러져야 한다 — 본 분기 도달 시
    # generator_config 는 반드시 존재한다고 가정한다.
    primary_model = generator_config.model
    fallback_model = generator_config.fallback_model
    temperature = generator_config.temperature
    timeout_seconds = generator_config.timeout_seconds

    # lazy import — openai 없는 환경 (PoC) 에서도 모듈 로드 가능. 본 분기는 운영
    # 모드에서만 도달.
    from openai import RateLimitError

    accumulated_tokens: list[str] = []
    used_model = primary_model
    try:
        for token_chunk in stream_openai_answer(
            api_key=api_key,
            model=primary_model,
            temperature=temperature,
            timeout_seconds=timeout_seconds,
            query=state.query,
            top_chunks=rerank_state.top_chunks,
        ):
            accumulated_tokens.append(token_chunk.text)
            yield {"event": "token", "data": token_chunk.text}
    except RateLimitError:
        # 설계서 §4.6.5 — 429 시 fallback_model 로 1회 재시도. 부분 토큰을 이미
        # 송신했다면 UI 가 덮어쓸 수 있도록 빈 token 이벤트로 clear.
        _LOGGER.warning(
            "answer streaming rate-limited, falling back to fallback_model=%s",
            fallback_model,
        )
        # feature17a — Prometheus 카운터로 streaming 경로 Rate Limit fallback 빈도 가시화.
        llm_fallback_total.labels(
            from_model=primary_model,
            to_model=fallback_model,
            reason="rate_limit_error",
        ).inc()
        if accumulated_tokens:
            accumulated_tokens.clear()
            yield {"event": "token", "data": ""}
        used_model = fallback_model
        for token_chunk in stream_openai_answer(
            api_key=api_key,
            model=fallback_model,
            temperature=temperature,
            timeout_seconds=timeout_seconds,
            query=state.query,
            top_chunks=rerank_state.top_chunks,
        ):
            accumulated_tokens.append(token_chunk.text)
            yield {"event": "token", "data": token_chunk.text}

    answer = "".join(accumulated_tokens)
    rerank_state.answer = answer
    rerank_state.used_llm = _resolve_used_llm(used_model)

    # 검증 1+2단계 — verify_pipeline_node 에 deps 의 verify_llm_evaluator 주입.
    verify_pipeline_node(rerank_state, llm_evaluator=deps.verify_llm_evaluator)

    elapsed_ms = (time.perf_counter_ns() - started) // 1_000_000
    response = format_response(
        answer=rerank_state.answer,
        sources=rerank_state.sources,
        verification=rerank_state.verification,
        intent=intent,
        used_llm=rerank_state.used_llm,
        latency_ms=int(elapsed_ms),
    )
    # token 이벤트는 이미 송신했으므로 sources / verification / meta / done 4 종만 송신.
    # 답변이 차단 분기(BLOCKED_ANSWER_MESSAGE) 인 경우 본 라우트는 이미 원본 토큰을
    # 전송한 뒤이므로, 차단 안내를 별도 'token' 이벤트로 1회 더 송신해 UI 가 답변을
    # 차단 메시지로 덮어쓰도록 한다.
    if response.answer != answer:
        yield {"event": "token", "data": response.answer}
    for event in _sse_payload(response)[1:]:
        yield event


@router.post("/api/v1/rag/query")
async def query_route(payload: QueryRequest, request: Request, graph: GraphDep) -> Any:
    """사용자 질의를 받아 ACL 기반 검색·답변·검증을 수행하고 SSE로 응답한다.

    docs/api-spec.md "POST /api/v1/rag/query" 정합:
      1. JWT 클레임 추출 — 실패 시 401 ``UNAUTHORIZED``.
      2. ``build_acl_filter`` 로 Qdrant should-OR 필터 생성.
      3. ``RagState`` 구성 후 stream 분기:
         - stream=False 또는 PoC fallback: ``run_query`` 로 그래프 실행 → 5 이벤트.
         - stream=True (운영): ``_streaming_event_stream`` 으로 token 다중 송신.
      4. ``QueryResponse`` 를 SSE 이벤트로 송신.
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

    # stream=True 라도 PoC 환경 (OpenAI 키 / generator_provider 없음) 이면
    # 비-streaming 흐름으로 자동 fallback — BFF/테스트 호환성 유지.
    if payload.stream and not _should_fallback_to_non_streaming(request):
        return EventSourceResponse(_streaming_event_stream(request=request, state=state))

    try:
        response = run_query(state, graph=graph)
    except ACLViolationError as exc:
        # 시스템 단 안전망 — build_acl_filter는 항상 유효 필터를 만들므로 정상 흐름에선
        # 도달하지 않지만, 그래프 내부 버그/우회 시 ACL 위반이 표면화되어야 한다.
        return _error_json(ErrorCode.UPSTREAM_LLM_ERROR, f"ACL 시스템 오류: {exc}")
    except Exception as exc:  # noqa: BLE001 — 상류 LLM/네트워크 예외 광범위 캐치 (PoC)
        return _error_json(ErrorCode.UPSTREAM_LLM_ERROR, str(exc))

    return EventSourceResponse(_event_stream(response))
