"""Ingestion 입력 표준 — PageObject / Attachment.

--------------------------------------------------
작성자 : 최태성
작성목적 : Document Source Adapter가 반환하는 표준 PageObject와 첨부 객체를
          정의한다. 공급원(JSON 픽스처 / Atlassian)과 무관하게 동결되는 계약.
작성일 : 2026-05-15
변경사항 내역 (날짜, 변경목적, 변경내용 순)
  - 2026-05-15, 최초 작성, feature1 schemas — 설계서 §7.1 PageObject 스펙 구현
--------------------------------------------------
[호환성]
  - Python 3.11.x, Pydantic 2.7+
--------------------------------------------------
"""

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.enums import ExtractedFormat


class Attachment(BaseModel):
    """페이지에 부속된 첨부 파일. 텍스트 추출 결과를 포함한다 (설계서 §3.2)."""

    attachment_id: str
    filename: str
    mime_type: str
    extracted_text: str
    extracted_format: ExtractedFormat
    download_url: str
    parent_page_id: str
    last_modified: datetime
    file_size_bytes: int | None = None


class PageObject(BaseModel):
    """RAG 파이프라인이 수신하는 표준 페이지 객체 (설계서 §7.1).

    공급원 전환(JSON 픽스처 ↔ Atlassian)에도 본 스펙은 변경되지 않는다.
    ``allowed_groups``/``allowed_users``는 필수 필드이나 빈 배열이 허용되며,
    둘 다 비어 있으면 ``is_acl_missing``으로 식별하여 Ingestion 단계에서
    ``INVALID_ACL``로 처리한다 (스키마 단에서 거부하지 않음).
    """

    page_id: str
    space_key: str
    title: str
    body_html: str
    version_number: int
    last_modified: datetime
    allowed_groups: list[str]
    allowed_users: list[str]
    webui_link: str
    labels: list[str] = Field(default_factory=list)
    ancestors: list[str] = Field(default_factory=list)
    attachments: list[Attachment] = Field(default_factory=list)

    @property
    def is_acl_missing(self) -> bool:
        """allowed_groups·allowed_users가 모두 비면 ACL 누락(INVALID_ACL 대상)."""
        return not self.allowed_groups and not self.allowed_users
