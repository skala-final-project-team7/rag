"""Query API 응답 스키마 — QueryResponse / Source / Verification.

--------------------------------------------------
작성자 : 최태성
작성목적 : 응답 포맷터가 생성하는 UI 렌더링용 응답 객체를 정의한다.
작성일 : 2026-05-15
변경사항 내역 (날짜, 변경목적, 변경내용 순)
  - 2026-05-15, 최초 작성, feature1 schemas — docs/api-spec.md 응답 객체 스키마 정합
--------------------------------------------------
[호환성]
  - Python 3.11.x, Pydantic 2.7+
--------------------------------------------------
"""

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.enums import Intent, LlmModel, SourceType, VerificationStatus


class Source(BaseModel):
    """인용 출처 카드 1건. 첨부 출처일 때만 attachment_* / download_url이 채워진다."""

    title: str
    score: int  # Cross-Encoder 관련도 0~100
    path: str
    space_key: str
    source_type: SourceType
    confluence_url: str
    last_modified: datetime
    text_preview: str
    attachment_filename: str | None = None
    attachment_mime: str | None = None
    download_url: str | None = None


class Verification(BaseModel):
    """답변 문장 1개의 검증 결과 (설계서 §4.7)."""

    sentence_id: int
    status: VerificationStatus
    cited_chunks: list[int] = Field(default_factory=list)


class QueryResponse(BaseModel):
    """POST /api/v1/rag/query의 완성형 응답 객체 (docs/api-spec.md)."""

    answer: str
    intent: Intent
    used_llm: LlmModel
    latency_ms: int
    sources: list[Source] = Field(default_factory=list)
    verification: list[Verification] = Field(default_factory=list)
    feedback_enabled: bool = True
