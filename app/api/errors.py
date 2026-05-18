"""Error Response 정의 — api-spec.md Error Response 표 정합 [Pipeline].

--------------------------------------------------
작성자 : 최태성
작성목적 : RAG 파이프라인 HTTP 계층의 Error Response 스키마와 표준 코드를 정의한다.
          `RETRIEVAL_EMPTY` / `LOW_CONFIDENCE` / `VERIFICATION_BLOCKED` 같은 "표준
          분기 응답"은 200 SSE 성공 응답 내부에서 처리되므로(`feedback_enabled=False`
          또는 답변 대체) 본 모듈의 Error Response는 `UNAUTHORIZED`(JWT 추출 실패) 와
          `UPSTREAM_LLM_ERROR`(LLM 호출 실패 / 타임아웃) 같은 본격 오류에만 사용된다.
작성일 : 2026-05-18
변경사항 내역 (날짜, 변경목적, 변경내용 순)
  - 2026-05-18, 최초 작성, feature11 통합 Phase 2 — ErrorCode StrEnum +
    ErrorDetail / ErrorResponse Pydantic 모델 + HTTP status 매핑
--------------------------------------------------
[호환성]
  - Python 3.11.x, Pydantic 2.7+, FastAPI 0.111+
--------------------------------------------------
"""

from enum import StrEnum

from fastapi import status
from pydantic import BaseModel, Field


class ErrorCode(StrEnum):
    """api-spec.md Error Response 표의 표준 코드.

    각 코드는 BFF/프론트가 분기 처리하는 식별자다. ``RETRIEVAL_EMPTY`` /
    ``LOW_CONFIDENCE`` / ``VERIFICATION_BLOCKED`` 도 api-spec.md 표에 포함되어
    있으나, 본 구현에서는 그 세 분기를 200 SSE 성공 응답 내부에서 처리한다
    (`feedback_enabled` / 답변 대체). 본 Enum은 4xx/5xx 응답에만 쓰이는 코드를
    명시하지만 호환성을 위해 모두 정의해 둔다.
    """

    UNAUTHORIZED = "UNAUTHORIZED"
    RETRIEVAL_EMPTY = "RETRIEVAL_EMPTY"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    UPSTREAM_LLM_ERROR = "UPSTREAM_LLM_ERROR"
    VERIFICATION_BLOCKED = "VERIFICATION_BLOCKED"


class ErrorDetail(BaseModel):
    """Error Response 의 ``error`` 필드 — code + message."""

    code: ErrorCode
    message: str


class ErrorResponse(BaseModel):
    """api-spec.md Error Response 응답 모델.

    .. code-block:: json

        { "success": false, "error": { "code": "RETRIEVAL_EMPTY", "message": "..." } }
    """

    success: bool = Field(default=False)
    error: ErrorDetail


# 4xx / 5xx 응답에 매핑되는 HTTP status. RETRIEVAL_EMPTY 등의 정상 분기는 200으로
# 처리되므로 본 매핑에 포함하지 않는다 — Error Response로 변환되는 코드만 등록한다.
HTTP_STATUS_BY_CODE: dict[ErrorCode, int] = {
    ErrorCode.UNAUTHORIZED: status.HTTP_401_UNAUTHORIZED,
    ErrorCode.UPSTREAM_LLM_ERROR: status.HTTP_502_BAD_GATEWAY,
}


def error_response(code: ErrorCode, message: str) -> ErrorResponse:
    """Error Response Pydantic 모델을 생성한다 — 라우트 핸들러용 헬퍼."""
    return ErrorResponse(error=ErrorDetail(code=code, message=message))
