"""LangGraph 노드 상태 — RagState / IngestionState.

--------------------------------------------------
작성자 : 최태성
작성목적 : Query / Ingestion LangGraph 그래프의 노드 간 전달 상태를 정의한다.
          각 노드가 단계별로 필드를 채워 나가는 상태 봉투(envelope) 역할.
작성일 : 2026-05-15
변경사항 내역 (날짜, 변경목적, 변경내용 순)
  - 2026-05-15, 최초 작성, feature1 schemas — Query/Ingestion 상태 정의
--------------------------------------------------
[호환성]
  - Python 3.11.x, Pydantic 2.7+
--------------------------------------------------
"""

from typing import Any

from pydantic import BaseModel, Field

from app.schemas.chunk import Chunk
from app.schemas.enums import IngestionStage, IngestionStatus, Intent, LlmModel
from app.schemas.page_object import PageObject
from app.schemas.response import Source, Verification


class HistoryTurn(BaseModel):
    """멀티턴 대화 1턴."""

    role: str  # "user" | "assistant"
    content: str


class RagState(BaseModel):
    """Query 파이프라인 LangGraph 상태. 단계가 진행되며 필드가 채워진다."""

    # 입력
    query: str
    user_id: str
    conversation_id: str | None = None
    groups: list[str] = Field(default_factory=list)
    # ACL Pre-filtering (§4.2)
    acl_filter: dict[str, Any] | None = None
    # 멀티턴 히스토리 (§4.3)
    history: list[HistoryTurn] = Field(default_factory=list)
    needs_search: bool = True
    # 질의 라우터 (§4.4)
    intent: Intent | None = None
    rewritten_queries: list[str] = Field(default_factory=list)
    metadata_filters: dict[str, Any] | None = None
    pool_weights: dict[str, float] | None = None
    target_llm: LlmModel | None = None
    # 검색·재순위화 (§4.5)
    candidates: list[Chunk] = Field(default_factory=list)  # Hybrid Search Top-20
    top_chunks: list[Chunk] = Field(default_factory=list)  # Cross-Encoder Top-5
    # 답변 생성·검증·포맷 (§4.6~4.8)
    answer: str | None = None
    sources: list[Source] = Field(default_factory=list)
    verification: list[Verification] = Field(default_factory=list)
    used_llm: LlmModel | None = None
    latency_ms: int | None = None


class IngestionState(BaseModel):
    """Ingestion 파이프라인 LangGraph 상태."""

    page: PageObject
    doc_type: str | None = None  # 문서 분석기 결과(본문) / attachment_type(첨부)
    chunks: list[Chunk] = Field(default_factory=list)
    stage: IngestionStage | None = None
    status: IngestionStatus | None = None
    error: str | None = None
