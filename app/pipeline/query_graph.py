"""Query LangGraph 그래프 조립 + 그래프 호출 래퍼 [Pipeline].

--------------------------------------------------
작성자 : 최태성
작성목적 : feature11 통합 — Query 파이프라인의 Pipeline 노드(완료)와 Agent stub(`app/
          pipeline/stubs.py`)을 LangGraph StateGraph로 잇는다. ACL Pre-filtering →
          멀티턴 히스토리 → 라우터 → Multi-Pool Hybrid Search → (검색 0건 분기) →
          Cross-Encoder 재순위화 → 답변 생성 → 답변 검증(1+2단계) → 응답 포맷터 흐름을
          한 위치에서 wiring한다 (`docs/architecture.md` §5.1, `docs/rag-pipeline-design.md`
          §6, `docs/api-spec.md`).
작성일 : 2026-05-18
변경사항 내역 (날짜, 변경목적, 변경내용 순)
  - 2026-05-18, 최초 작성, feature11 통합 — QueryGraphDeps + build_query_graph +
    run_query (Phase 1: 그래프 조립). FastAPI SSE 라우트는 별도 세션(Phase 2).
--------------------------------------------------
[호환성]
  - Python 3.11.x, LangGraph 0.2.x
  - 외부 의존성: dense/sparse 임베더·QdrantPoolStore·Cross-Encoder Reranker는 모두
    호출자가 주입한다 (`functools.partial` 패턴 — `app/CLAUDE.md` §8).
  - NOTE: 본 모듈은 Agent 노드(라우터·답변 생성기·검증 2단계)를 stub로 둔 채 end-to-end
          흐름을 검증한다. Agent 코드 전달 시 `QueryGraphDeps.router_node` /
          `.generator_node` / `.verify_llm_evaluator` 3곳의 기본값만 교체한다.
--------------------------------------------------
"""

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from functools import partial
from typing import Any

from langgraph.graph import END, StateGraph

from app.ingestion.embedder.base import DenseEmbedder, SparseEmbedder
from app.pipeline.nodes import (
    after_search_branch,
    empty_retrieval_node,
    verify_pipeline_node,
)
from app.pipeline.stubs import (
    generator_stub,
    router_stub,
    verify_llm_evaluator_stub,
)
from app.query.formatter import format_response
from app.query.history import manage_history
from app.query.rerank_node import cross_encoder_rerank
from app.query.reranker.base import CrossEncoderReranker
from app.query.search_node import hybrid_search
from app.schemas.enums import Intent, LlmModel
from app.schemas.rag_state import RagState
from app.schemas.response import QueryResponse
from app.storage.qdrant_client import QdrantPoolStore

# history-manager-agent의 LLM provider — runtime 인터페이스 의존성 회피를 위해 Any.
HistoryProvider = Any

# 노드 시그니처 (모두 (RagState) -> RagState)
QueryNode = Callable[[RagState], RagState]

# 검증 2단계 LLM 평가자 시그니처 — keyword args (`answer`, `top_chunks`,
# `suspicious_sentences`). `app/pipeline/nodes.VerifyLLMEvaluator` 와 정합.
VerifyEvaluator = Callable[..., list]


@dataclass(slots=True)
class QueryGraphDeps:
    """Query 그래프 의존성 묶음 — 그래프 빌더가 노드에 wiring한다.

    Pipeline 컴포넌트(검색·재순위화·검증 1단계·포맷터)는 본 담당자 영역에서 이미 완료
    되었으며, Agent 컴포넌트 3종(라우터·답변 생성기·검증 2단계)은 stub 기본값을 둔다.
    Agent 코드 전달 시 본 dataclass 인자만 교체하면 그래프는 변경 없이 동작한다.
    """

    # --- Pipeline / Storage 의존성 ---
    dense_embedder: DenseEmbedder
    sparse_embedder: SparseEmbedder
    store: QdrantPoolStore
    reranker: CrossEncoderReranker
    # 멀티턴 히스토리 관리자 LLM provider — None이면 manage_history가
    # FakeHistoryLLMProvider 기본을 사용한다.
    history_provider: HistoryProvider | None = None

    # --- Agent 노드 — 기본값은 stub. 실 Agent 코드 전달 시 교체. ---
    router_node: QueryNode = field(default=router_stub)
    generator_node: QueryNode = field(default=generator_stub)
    verify_llm_evaluator: VerifyEvaluator = field(default=verify_llm_evaluator_stub)


def build_query_graph(deps: QueryGraphDeps) -> Any:
    """Query LangGraph StateGraph를 조립해 컴파일된 그래프를 반환한다.

    그래프 구조 (rag-pipeline-design.md §6, api-spec.md 표준 분기):
        manage_history → router → hybrid_search
                                     ├─(candidates 0건)─► empty_retrieval ─► END
                                     └─(후보 있음)─► rerank → generate → verify ─► END

    Args:
        deps: 그래프 노드 wiring에 필요한 의존성 묶음.

    Returns:
        LangGraph CompiledGraph (`graph.invoke(state)` 로 실행).
    """
    builder = StateGraph(RagState)

    # 노드 등록 — 외부 의존성은 functools.partial 로 wiring.
    # NOTE: 노드명은 RagState 필드명과 네임스페이스를 공유한다 (LangGraph 1.x 제약).
    # 히스토리 관리자 노드는 RagState.history 필드와 충돌하므로 'manage_history'로 둔다.
    builder.add_node("manage_history", partial(manage_history, provider=deps.history_provider))
    builder.add_node("router", deps.router_node)
    builder.add_node(
        "hybrid_search",
        partial(
            hybrid_search,
            dense_embedder=deps.dense_embedder,
            sparse_embedder=deps.sparse_embedder,
            store=deps.store,
        ),
    )
    builder.add_node("empty_retrieval", empty_retrieval_node)
    builder.add_node("rerank", partial(cross_encoder_rerank, reranker=deps.reranker))
    builder.add_node("generate", deps.generator_node)
    builder.add_node(
        "verify",
        partial(verify_pipeline_node, llm_evaluator=deps.verify_llm_evaluator),
    )

    # 엣지 — 단일 경로 + 검색 0건 분기.
    builder.set_entry_point("manage_history")
    builder.add_edge("manage_history", "router")
    builder.add_edge("router", "hybrid_search")
    builder.add_conditional_edges(
        "hybrid_search",
        after_search_branch,
        {"empty": "empty_retrieval", "rerank": "rerank"},
    )
    builder.add_edge("empty_retrieval", END)
    builder.add_edge("rerank", "generate")
    builder.add_edge("generate", "verify")
    builder.add_edge("verify", END)

    return builder.compile()


def run_query(
    state: RagState,
    *,
    graph: Any,
    formatter: Callable[..., QueryResponse] = format_response,
) -> QueryResponse:
    """그래프를 invoke해 RagState를 채운 뒤 포맷터로 QueryResponse를 산출한다.

    latency 측정은 본 wrapper가 책임진다 — 그래프 진입 직전부터 invoke 종료 시점까지의
    monotonic 시간을 ms로 환산한다. 그래프 자체는 비결정적 외부 호출(임베딩 / Qdrant /
    Cross-Encoder)을 포함하므로 wall-clock 대신 ``time.perf_counter_ns`` 를 사용한다.

    LangGraph 0.2.x는 Pydantic state를 dict로 직렬화해 반환하므로
    ``RagState.model_validate`` 로 재구성한 뒤 포맷터에 전달한다.

    Args:
        state: 초기 RagState. ``query`` / ``user_id`` / ``groups`` / ``acl_filter``
            (호출자가 build_acl_filter로 산출) 채워 진입.
        graph: ``build_query_graph`` 로 컴파일된 그래프.
        formatter: 포맷터 함수 — 기본값 `app.query.formatter.format_response`. 테스트
            에서 분기 검증을 위해 주입 가능.

    Returns:
        UI 렌더링용 QueryResponse (api-spec.md 정합).
    """
    started = time.perf_counter_ns()
    result_dict = graph.invoke(state)
    elapsed_ms = (time.perf_counter_ns() - started) // 1_000_000

    final = RagState.model_validate(result_dict)
    # latency_ms 는 그래프 외부에서 측정한 값만 신뢰한다.
    intent = final.intent or Intent.OPERATION_GUIDE
    used_llm = final.used_llm or LlmModel.GPT_4O_MINI
    answer = final.answer or ""

    return formatter(
        answer=answer,
        sources=final.sources,
        verification=final.verification,
        intent=intent,
        used_llm=used_llm,
        latency_ms=int(elapsed_ms),
    )
