"""QueryResponse / Source / Verification 스키마 검증 (docs/api-spec.md)."""

from app.schemas.enums import Intent, LlmModel, SourceType, VerificationStatus
from app.schemas.response import QueryResponse, Source, Verification

_PAGE_SOURCE = dict(
    title="S3 AccessDenied 트러블슈팅 > 원인",
    score=87,
    path="운영 / AWS / S3 AccessDenied 트러블슈팅 > 원인",
    space_key="INFRA",
    source_type="page",
    confluence_url="https://confluence/pages/12345#원인",
    last_modified="2026-05-01T03:21:00+09:00",
    text_preview="버킷 정책의 Principal 필드가 비어 있을 경우...",
)

_ATTACHMENT_SOURCE = dict(
    title="prod_cost_2026Q1.xlsx > [2026Q1 비용]",
    score=78,
    path="운영 / FinOps / 2026Q1 보고 > 비용 시트",
    space_key="FINOPS",
    source_type="attachment",
    confluence_url="https://confluence/pages/12345#attachments",
    last_modified="2026-05-08T07:11:00+09:00",
    text_preview="[2026Q1 비용] 서비스: EKS | 월: 1월 | 비용(USD): 12340...",
    attachment_filename="prod_cost_2026Q1.xlsx",
    attachment_mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    download_url="https://confluence/download/attachments/99001/prod_cost_2026Q1.xlsx",
)


def test_page_source_optional_attachment_fields_none() -> None:
    src = Source(**_PAGE_SOURCE)
    assert src.source_type is SourceType.PAGE
    assert src.attachment_filename is None
    assert src.download_url is None


def test_attachment_source_carries_attachment_fields() -> None:
    src = Source(**_ATTACHMENT_SOURCE)
    assert src.source_type is SourceType.ATTACHMENT
    assert src.attachment_filename == "prod_cost_2026Q1.xlsx"
    assert src.download_url is not None


def test_verification_model() -> None:
    v = Verification(sentence_id=2, status="SUPPORTED", cited_chunks=[2, 3])
    assert v.status is VerificationStatus.SUPPORTED
    assert v.cited_chunks == [2, 3]


def test_query_response_round_trip() -> None:
    response = QueryResponse(
        answer="S3 AccessDenied는 IAM 정책 누락으로 발생합니다 [#1].",
        sources=[Source(**_PAGE_SOURCE), Source(**_ATTACHMENT_SOURCE)],
        verification=[Verification(sentence_id=1, status="PASS", cited_chunks=[1])],
        intent="장애대응",
        used_llm="gpt-4o",
        latency_ms=4120,
    )
    assert response.intent is Intent.INCIDENT_RESPONSE
    assert response.used_llm is LlmModel.GPT_4O
    assert response.feedback_enabled is True  # 기본값

    dumped = response.model_dump(mode="json")
    restored = QueryResponse.model_validate(dumped)
    assert restored == response
    assert len(restored.sources) == 2
