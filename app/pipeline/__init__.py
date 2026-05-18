"""app.pipeline — LangGraph 그래프 조립.

app.ingestion / app.query 의 단계별 노드를 LangGraph StateGraph로 연결한다.
각 노드는 단일 책임을 갖고, 노드 입출력 상태는 app.schemas 의 IngestionState / RagState로 통일한다.

모듈:
- query_graph.py  Query 그래프 (ACL → 히스토리 → 라우터 → 검색·재순위화 → 생성 → 검증 → 포맷)
                  히스토리 관리자의 needs_search=false 시 검색 단계 스킵 분기 포함
- nodes.py        Pipeline 노드 래퍼 (empty_retrieval / verify_pipeline / after_search_branch)
- stubs.py        Agent stub 3종 (router / generator / verify_llm_evaluator) — 교체 지점

구현 상태:
- query_graph.py  QueryGraphDeps / build_query_graph / run_query — feature11 통합 (Phase 1).
                  FastAPI SSE 라우트(Phase 2)는 별도 세션. Agent 노드는 stubs.py로 교체 가능.
- nodes.py        empty_retrieval_node / verify_pipeline_node / after_search_branch
                  [feature11 통합]
- stubs.py        router_stub / generator_stub / verify_llm_evaluator_stub
                  [feature11 통합] (Agent 코드 전달 시 교체)

계획 모듈 (미구현):
- ingestion_graph.py  Ingestion 그래프 (문서 분석 → 첨부 분석 → 청킹 → 임베딩 → 적재)
"""

from app.pipeline.nodes import (
    RETRIEVAL_EMPTY_ANSWER,
    after_search_branch,
    empty_retrieval_node,
    verify_pipeline_node,
)
from app.pipeline.query_graph import QueryGraphDeps, build_query_graph, run_query
from app.pipeline.stubs import (
    generator_stub,
    router_stub,
    verify_llm_evaluator_stub,
)

__all__ = [
    "RETRIEVAL_EMPTY_ANSWER",
    "QueryGraphDeps",
    "after_search_branch",
    "build_query_graph",
    "empty_retrieval_node",
    "generator_stub",
    "router_stub",
    "run_query",
    "verify_llm_evaluator_stub",
    "verify_pipeline_node",
]
