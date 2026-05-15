"""Multi-Pool Vector Store payload 구성 검증 (feature5-A) — db-schema.md §1.2.

build_point_payload: Chunk를 Qdrant Point payload dict로 변환한다.
"""

from datetime import datetime

from app.ingestion.vector_store import (
    CONTENT_POOL,
    LABEL_POOL,
    POOL_NAMES,
    TITLE_POOL,
    build_point_payload,
)
from app.schemas.chunk import Chunk, ChunkMetadata
from app.schemas.enums import ExtractedFormat, SourceType

_LAST_MODIFIED = datetime.fromisoformat("2026-04-22T08:15:00+09:00")

_PAGE_METADATA = ChunkMetadata(
    chunk_id="chunk-abc123",
    page_id="CONF-PAGE-1",
    page_title="EKS 운영 가이드",
    section_header="개요",
    section_path="Cloud 운영 문서 > EKS 운영 > 개요",
    chunk_index=2,
    labels=["eks", "운영"],
    doc_type="operation",
    space_key="CLOUD",
    allowed_groups=["space:CLOUD"],
    allowed_users=["user:taesung"],
    webui_link="/display/CLOUD/eks",
    last_modified=_LAST_MODIFIED,
    source_type=SourceType.PAGE,
    token_count=120,
)

_DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def _page_chunk(text: str = "EKS 클러스터 운영 본문") -> Chunk:
    return Chunk(text=text, metadata=_PAGE_METADATA)


def _attachment_chunk(text: str = "[시트1] 행 1~10") -> Chunk:
    metadata = _PAGE_METADATA.model_copy(
        update={
            "source_type": SourceType.ATTACHMENT,
            "attachment_id": "CONF-PAGE-1-att-0",
            "attachment_filename": "EKS_운영_상세_매뉴얼_v2.3.docx",
            "attachment_mime": _DOCX_MIME,
            "extracted_format": ExtractedFormat.RAW_TEXT,
        }
    )
    return Chunk(text=text, metadata=metadata)


def test_pool_names_match_db_schema() -> None:
    assert POOL_NAMES == (TITLE_POOL, CONTENT_POOL, LABEL_POOL)
    assert TITLE_POOL == "title_pool"
    assert CONTENT_POOL == "content_pool"
    assert LABEL_POOL == "label_pool"


def test_build_point_payload_common_fields() -> None:
    payload = build_point_payload(_page_chunk(), version_number=7)
    assert payload["page_id"] == "CONF-PAGE-1"
    assert payload["page_title"] == "EKS 운영 가이드"
    assert payload["section_header"] == "개요"
    assert payload["section_path"] == "Cloud 운영 문서 > EKS 운영 > 개요"
    assert payload["chunk_index"] == 2
    assert payload["labels"] == ["eks", "운영"]
    assert payload["doc_type"] == "operation"
    assert payload["space_key"] == "CLOUD"
    assert payload["allowed_groups"] == ["space:CLOUD"]
    assert payload["allowed_users"] == ["user:taesung"]
    assert payload["webui_link"] == "/display/CLOUD/eks"
    assert payload["last_modified"] == _LAST_MODIFIED.isoformat()


def test_build_point_payload_injects_version_number() -> None:
    # version_number는 ChunkMetadata에 없어 부모 PageObject에서 별도 인자로 주입된다
    assert build_point_payload(_page_chunk(), version_number=7)["version_number"] == 7
    assert build_point_payload(_page_chunk(), version_number=1)["version_number"] == 1


def test_build_point_payload_page_chunk_has_null_attachment_fields() -> None:
    payload = build_point_payload(_page_chunk(), version_number=1)
    assert payload["source_type"] == "page"
    assert payload["attachment_id"] is None
    assert payload["attachment_filename"] is None
    assert payload["attachment_mime"] is None
    assert payload["extracted_format"] is None


def test_build_point_payload_attachment_chunk_fields() -> None:
    payload = build_point_payload(_attachment_chunk(), version_number=1)
    assert payload["source_type"] == "attachment"
    assert payload["attachment_id"] == "CONF-PAGE-1-att-0"
    assert payload["attachment_filename"] == "EKS_운영_상세_매뉴얼_v2.3.docx"
    assert payload["attachment_mime"] == _DOCX_MIME
    assert payload["extracted_format"] == "raw_text"


def test_build_point_payload_text_preview_truncated_to_200() -> None:
    payload = build_point_payload(_page_chunk("가" * 500), version_number=1)
    assert payload["text_preview"] == "가" * 200
    assert len(payload["text_preview"]) == 200


def test_build_point_payload_text_preview_keeps_short_text() -> None:
    payload = build_point_payload(_page_chunk("짧은 본문"), version_number=1)
    assert payload["text_preview"] == "짧은 본문"
