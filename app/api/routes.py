"""POST /ml/query — SSE 라우트 핸들러 [Pipeline].

--------------------------------------------------
작성자 : 최태성
작성목적 : feature11 통합 Phase 2 — Query 그래프(`app/pipeline/query_graph.py`)
          위에 얇은 HTTP 계층을 얹어 BFF가 호출하는 SSE 엔드포인트를 제공한다.
          BFF가 전달한 userId/groups 로 ACL 필터를 만들고 RagState 를 구성한 뒤
          run_query → SSE 송신까지 한 흐름으로 처리한다. api-spec.md "POST /ml/query"
          정합으로 token / sources / verification / done 이벤트(+ feature19 status)를
          송신한다.
작성일 : 2026-05-18
변경사항 내역 (날짜, 변경목적, 변경내용 순)
  - 2026-05-18, 최초 작성, feature11 통합 Phase 2 — query_route + SSE
    이벤트 생성기 + JWT/ACL 시스템 단 강제
  - 2026-05-19, feature14 SSE token streaming — ``QueryRequest.stream`` 분기.
  - 2026-05-19, feature15 streaming Rate Limit fallback — 설계서 §4.6.5.
  - 2026-05-19, feature17a — Rate Limit fallback Prometheus 카운터.
  - 2026-05-22, feature19 — SSE 진행 표시용 ``status`` 이벤트 *추가*. streaming
    경로에만 적용. phase 7종(connecting → acl_filtering → searching → answering
    → streaming → verifying → formatting).
  - 2026-05-26, feature13 코드 마이그레이션 — BE 통합 스펙(/ml/query) 정합:
    (1) 엔드포인트 ``/api/v1/rag/query`` → ``/ml/query`` 완전 전환.
    (2) 요청 본문 재정의 — ``question``/``userId``/``groups``/``spaceKey``/
        ``conversationId``/``history``/``stream``. JWT 미수신 → ``extract_principal``
        호출 제거, userId/groups 직접 사용. ``spaceKey`` 는 RagState 에 passthrough
        (검색 필터 반영은 후속). ``accessToken``/``cloudId`` 는 api-spec v2.2.0 에서
        ``/ml/query`` 가 아닌 수집 단계(``/ml/ingest``)로 이관됨 — 본 경로 미수신.
    (3) SSE 이벤트 형식 변경 — ``token``=``{"content": ...}``, ``sources``=
        ``{"sources": [...]}`` 래핑(relevanceScore 0~1 / sourceUpdatedAt KST / pageId·
        spaceId·spaceName), ``verification``=집계 ``{"confidenceScore",
        "verificationResult"}``, ``done``=``{}``. ``meta`` 이벤트는 api-spec v2.2.0
        정합으로 유지(intent/used_llm/feedback_enabled/latency_ms, title 은 ML 미생성
        으로 생략). 추후 BE 통합 목표 계약에서 제거 예정.
    (4) 오류는 HTTP 에러 JSON 대신 SSE ``error`` 이벤트로 전달하고 스트림 종료.
        RETRIEVAL_EMPTY/LOW_CONFIDENCE/VERIFICATION_BLOCKED 는 종전대로 200 SSE
        내부 분기로 처리한다.
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
from pydantic import BaseModel, ConfigDict, Field
from sse_starlette.sse import EventSourceResponse

from app.api.errors import ErrorCode
from app.metrics import llm_fallback_total
from app.pipeline.nodes import verify_pipeline_node
from app.pipeline.query_graph import run_query
from app.query.acl import ACLViolationError, build_acl_filter
from app.query.formatter import format_response
from app.query.openai_streaming import stream_openai_answer
from app.schemas.enums import Intent, LlmModel
from app.schemas.rag_state import HistoryTurn, RagState
from app.schemas.response import QueryResponse, VerificationSummary

_LOGGER = logging.getLogger(__name__)

router = APIRouter()


class QueryRequest(BaseModel):
    """``POST /ml/query`` 요청 본문 (docs/api-spec.md, BE 통합 스펙 §2-1).

    BFF 는 camelCase JSON 을 보낸다(``userId``/``spaceKey``/``conversationId`` 등).
    ``populate_by_name=True`` 로 snake_case 필드명 입력도 허용한다(테스트 편의).
    """

    model_config = ConfigDict(populate_by_name=True)

    question: str = Field(..., min_length=1, description="사용자 자연어 질문")
    user_id: str = Field(
        ..., min_length=1, alias="userId", description="ACL Pre-filtering 사용자 식별자"
    )
    groups: list[str] = Field(default_factory=list, description="사용자 그룹 — ACL should-OR 필터")
    space_key: str = Field(
        default="", alias="spaceKey", description="검색 대상 Confluence 스페이스(2단계 고정값)"
    )
    conversation_id: str | None = Field(
        default=None, alias="conversationId", description="대화 컨텍스트 ID"
    )
    history: list[HistoryTurn] = Field(
        default_factory=list, description="이전 대화 이력 [{role, content}] (BFF가 DB에서 조회)"
    )
    stream: bool = Field(
        default=False,
        description=(
            "True 면 SSE 토큰 스트리밍 모드. False 면 답변 전체를 1회 token 이벤트로 송신. "
            "PoC 환경(OpenAI 키 없음)에서는 True 라도 자동 비-streaming fallback."
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


def _token_event(text: str) -> dict[str, str]:
    """답변 텍스트 → SSE ``token`` 이벤트. data 는 ``{"content": "<텍스트>"}`` JSON."""
    return {"event": "token", "data": json.dumps({"content": text}, ensure_ascii=False)}


def _error_event(code: ErrorCode, message: str) -> dict[str, str]:
    """SSE ``error`` 이벤트. data 는 ``{"code", "message"}`` JSON (api-spec.md)."""
    payload = {"code": code.value, "message": message}
    return {"event": "error", "data": json.dumps(payload, ensure_ascii=False)}


def _sse_payload(response: QueryResponse) -> list[dict[str, str]]:
    """QueryResponse → SSE 이벤트 시퀀스 (api-spec.md "SSE 이벤트 순서").

    이벤트 5종 (api-spec v2.2.0 §1-1 정합):
        1. ``token`` — 답변 텍스트. data=``{"content": ...}``. 비-streaming은 1회(전체 답변).
        2. ``sources`` — 출처 카드 배열. data=``{"sources": [...]}``.
        3. ``verification`` — 집계 검증 결과. data=``{"confidenceScore", "verificationResult"}``.
        4. ``meta`` — 현재 구현 호환용 메타데이터(intent/used_llm/feedback_enabled/latency_ms).
           ``title`` 은 ML 이 생성하지 않으므로 생략(스펙상 optional). 추후 제거 예정.
        5. ``done`` — 종료 마커. data=``{}`` (messageId는 BFF가 주입).
    """
    sources_payload = {"sources": [source.to_bff_payload() for source in response.sources]}
    verification_payload = VerificationSummary.from_sentences(
        response.verification
    ).to_bff_payload()
    meta_payload = {
        "intent": response.intent.value,
        "used_llm": response.used_llm.value,
        "feedback_enabled": response.feedback_enabled,
        "latency_ms": response.latency_ms,
    }
    return [
        _token_event(response.answer),
        {"event": "sources", "data": json.dumps(sources_payload, ensure_ascii=False)},
        {
            "event": "verification",
            "data": json.dumps(verification_payload, ensure_ascii=False),
        },
        {"event": "meta", "data": json.dumps(meta_payload, ensure_ascii=False)},
        {"event": "done", "data": json.dumps({})},
    ]


async def _non_streaming_event_stream(
    *, state: RagState, graph: Any
) -> AsyncIterator[dict[str, str]]:
    """비-streaming SSE 흐름 — run_query 실행 후 4종 이벤트 송신.

    그래프/상류 예외는 HTTP 에러가 아니라 SSE ``error`` 이벤트로 전달하고 종료한다
    (api-spec.md 오류 처리 정합).
    """
    try:
        response = run_query(state, graph=graph)
    except ACLViolationError as exc:
        # 시스템 단 안전망 — build_acl_filter는 항상 유효 필터를 만들므로 정상 흐름에선
        # 도달하지 않지만, 그래프 내부 버그/우회 시 ACL 위반이 표면화되어야 한다.
        yield _error_event(ErrorCode.UPSTREAM_LLM_ERROR, f"ACL 시스템 오류: {exc}")
        return
    except Exception as exc:  # noqa: BLE001 — 상류 LLM/네트워크 예외 광범위 캐치 (PoC)
        _LOGGER.exception("non-streaming query failed")
        yield _error_event(ErrorCode.UPSTREAM_LLM_ERROR, str(exc))
        return
    for event in _sse_payload(response):
        yield event


def _resolve_used_llm(model: str) -> LlmModel:
    """generator_config.model 문자열을 LlmModel enum 으로 안전 변환.

    enum 에 없는 모델명 (예: ``gpt-4o-2024-05-13``) 이면 GPT_4O 로 fallback. 내부 메트릭
    정합용 — 응답 객체 스키마(``used_llm: LlmModel``)를 강제하기 위한 단순 정합.
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


# feature19 — SSE 진행 표시용 ``status`` 이벤트.
# 핵심 이벤트(token/sources/verification/done)와 별개로, RAG 라이프사이클 단계 진입 시
# 진행 phase 를 1회 push 한다. status 를 무시하는 클라이언트도 그대로 동작한다(추가 전용).
# streaming 경로(``_streaming_event_stream``)에만 적용하며, 비-streaming 경로는 단일
# 블로킹 invoke 후 모든 이벤트를 한꺼번에 flush 해 phase 가 동시에 발사되므로 적용하지 않는다.
# done/error 는 핵심 done 이벤트 + SSE error 이벤트로 표현하며 status 로는 만들지 않는다.
_STATUS_MESSAGES: dict[str, str] = {
    "connecting": "연결 중이에요",
    "acl_filtering": "접근 권한을 확인하고 있어요",
    "searching": "관련 문서를 검색하고 있어요",
    "answering": "답변을 준비하고 있어요",
    "streaming": "답변을 작성하고 있어요",
    "verifying": "답변 근거를 검증하고 있어요",
    "formatting": "답변을 정리하고 있어요",
}


def _status_event(phase: str) -> dict[str, str]:
    """진행 phase → SSE ``status`` 이벤트 dict.

    ``data`` 는 다른 JSON 이벤트와 동일하게 ``json.dumps(..., ensure_ascii=False)`` 로
    직렬화한 ``{"phase": "<phase>", "message": "<한국어 메시지>"}`` 객체다.
    """
    payload = {"phase": phase, "message": _STATUS_MESSAGES[phase]}
    return {"event": "status", "data": json.dumps(payload, ensure_ascii=False)}


async def _streaming_event_stream(
    *,
    request: Request,
    state: RagState,
) -> AsyncIterator[dict[str, str]]:
    """SSE 토큰 스트리밍 흐름 (설계서 §4.6.4) — 상류 예외를 SSE error 이벤트로 흡수."""
    try:
        async for event in _streaming_event_stream_inner(request=request, state=state):
            yield event
    except Exception as exc:  # noqa: BLE001 — 상류 LLM/네트워크 예외 광범위 캐치 (PoC)
        _LOGGER.exception("streaming query failed")
        yield _error_event(ErrorCode.UPSTREAM_LLM_ERROR, str(exc))


async def _streaming_event_stream_inner(
    *,
    request: Request,
    state: RagState,
) -> AsyncIterator[dict[str, str]]:
    """SSE 토큰 스트리밍 본문.

    1. ``app.state.streaming_graph`` 로 history → router → search → (empty | rerank)
       까지 실행 → RagState 갱신 (top_chunks + sources 채워짐).
    2. RETRIEVAL_EMPTY 분기 (top_chunks 비어 있고 answer 가 표준 메시지) → 기존
       _sse_payload 로 token 1회 + sources/verification/done 송신.
    3. rerank 결과 있음 → ``stream_openai_answer`` 호출, token chunk 다중 yield.
    4. 누적 답변에 대해 ``verify_pipeline_node`` (1+2단계) 호출 후 ``format_response``
       로 저신뢰/차단 분기 적용 → sources/verification/done 송신.
    """
    started = time.perf_counter_ns()

    # feature19 status — connecting / acl_filtering.
    yield _status_event("connecting")
    yield _status_event("acl_filtering")

    streaming_graph = request.app.state.streaming_graph
    # feature19 status — searching. 그래프 내부 history/router/search/rerank 4단계를
    # 절충안으로 단일 phase 하나로 통합한다(astream 전환 없이 invoke 직전 1회 송신).
    yield _status_event("searching")
    result_dict = streaming_graph.invoke(state)
    rerank_state = RagState.model_validate(result_dict)

    intent = rerank_state.intent or Intent.OPERATION_GUIDE
    settings = request.app.state.settings
    deps = request.app.state.deps

    # 검색 0건 분기 — empty_retrieval 노드가 answer/used_llm/intent 를 채워준다.
    # answering/streaming/verifying 를 건너뛰고 formatting 으로 직행한다(feature19).
    if not rerank_state.top_chunks:
        used_llm = rerank_state.used_llm or LlmModel.GPT_4O_MINI
        yield _status_event("formatting")
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

    # feature19 status — answering. 프롬프트 구성 / stream_openai_answer 호출 직전.
    yield _status_event("answering")

    accumulated_tokens: list[str] = []
    used_model = primary_model
    # feature19 status — streaming. 첫 token chunk 송신 직전 1회만 송신(fallback 재시도
    # 시에도 중복 송신하지 않도록 플래그로 한 번만 보낸다).
    streaming_status_sent = False
    try:
        for token_chunk in stream_openai_answer(
            api_key=api_key,
            model=primary_model,
            temperature=temperature,
            timeout_seconds=timeout_seconds,
            query=state.query,
            top_chunks=rerank_state.top_chunks,
        ):
            if not streaming_status_sent:
                yield _status_event("streaming")
                streaming_status_sent = True
            accumulated_tokens.append(token_chunk.text)
            yield _token_event(token_chunk.text)
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
            yield _token_event("")
        used_model = fallback_model
        for token_chunk in stream_openai_answer(
            api_key=api_key,
            model=fallback_model,
            temperature=temperature,
            timeout_seconds=timeout_seconds,
            query=state.query,
            top_chunks=rerank_state.top_chunks,
        ):
            if not streaming_status_sent:
                yield _status_event("streaming")
                streaming_status_sent = True
            accumulated_tokens.append(token_chunk.text)
            yield _token_event(token_chunk.text)

    answer = "".join(accumulated_tokens)
    rerank_state.answer = answer
    rerank_state.used_llm = _resolve_used_llm(used_model)

    # feature19 status — verifying. verify_pipeline_node(1+2단계) 호출 직전.
    yield _status_event("verifying")
    # 검증 1+2단계 — verify_pipeline_node 에 deps 의 verify_llm_evaluator 주입.
    verify_pipeline_node(rerank_state, llm_evaluator=deps.verify_llm_evaluator)

    elapsed_ms = (time.perf_counter_ns() - started) // 1_000_000
    # feature19 status — formatting. format_response → sources/verification 송신 직전.
    yield _status_event("formatting")
    response = format_response(
        answer=rerank_state.answer,
        sources=rerank_state.sources,
        verification=rerank_state.verification,
        intent=intent,
        used_llm=rerank_state.used_llm,
        latency_ms=int(elapsed_ms),
    )
    # token 이벤트는 이미 송신했으므로 sources / verification / done 만 송신.
    # 답변이 차단 분기(BLOCKED_ANSWER_MESSAGE) 인 경우 본 라우트는 이미 원본 토큰을
    # 전송한 뒤이므로, 차단 안내를 별도 'token' 이벤트로 1회 더 송신해 UI 가 답변을
    # 차단 메시지로 덮어쓰도록 한다.
    if response.answer != answer:
        yield _token_event(response.answer)
    for event in _sse_payload(response)[1:]:
        yield event


@router.post("/ml/query")
async def query_route(payload: QueryRequest, request: Request, graph: GraphDep) -> Any:
    """사용자 질의를 받아 ACL 기반 검색·답변·검증을 수행하고 SSE로 응답한다.

    docs/api-spec.md "POST /ml/query" 정합:
      1. BFF가 전달한 ``userId``/``groups`` 로 ``build_acl_filter`` (Qdrant should-OR).
      2. ``RagState`` 구성(question/userId/groups/spaceKey/conversationId/history) 후
         stream 분기:
         - stream=False 또는 PoC fallback: ``run_query`` → token/sources/verification/done.
         - stream=True (운영): ``_streaming_event_stream`` 으로 token 다중 송신.
      3. 오류는 SSE ``error`` 이벤트로 전달하고 스트림을 종료한다.
    """
    state = RagState(
        query=payload.question,
        user_id=payload.user_id,
        groups=payload.groups,
        conversation_id=payload.conversation_id,
        space_key=payload.space_key,
        history=payload.history,
        acl_filter=build_acl_filter(payload.user_id, payload.groups),
    )

    # stream=True 라도 PoC 환경 (OpenAI 키 / generator_provider 없음) 이면
    # 비-streaming 흐름으로 자동 fallback — BFF/테스트 호환성 유지.
    if payload.stream and not _should_fallback_to_non_streaming(request):
        return EventSourceResponse(_streaming_event_stream(request=request, state=state))

    return EventSourceResponse(_non_streaming_event_stream(state=state, graph=graph))
