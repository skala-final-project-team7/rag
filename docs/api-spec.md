# API Spec (Draft)

> **상태: 초안.** RAG Pipeline이 BFF에 노출하는 API의 초안이다.
> 실제 엔드포인트·요청/응답 스키마는 해당 기능의 Plan 확정 시 함께 갱신한다.
> API 변경 시 이 문서를 함께 수정한다(루트 `CLAUDE.md` 규칙).

이 문서는 RAG Pipeline 서비스가 제공하는 API 계약을 정의한다.
호출 주체는 API Gateway / BFF이며, 전체 흐름은 `docs/architecture.md` 5.1을 참고한다.

공통 응답 형식은 `docs/conventions.md`의 API Convention을 따른다.

---

## POST /api/v1/rag/query

사용자 질의를 받아 권한 기반 검색 → 답변 생성 → 출처 검증을 수행하고 답변과 출처를 반환한다.

- 인증 필요: 예 (BFF가 사용자 권한 정보를 함께 전달)

### Request Body

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `query` | string | Y | 사용자 자연어 질문 |
| `conversation_id` | string | N | 대화 컨텍스트 ID |
| `user_id` | string | Y | 인증된 사용자 ID |
| `acl` | object | Y | `allowed_groups`, `allowed_users` |

### Success Response

```json
{
  "success": true,
  "data": {
    "answer": "...",
    "citations": [
      { "page_id": "...", "title": "...", "source_url": "...", "snippet": "..." }
    ],
    "verified": true
  },
  "message": null
}
```

### Error Response

```json
{
  "success": false,
  "error": {
    "code": "RETRIEVAL_EMPTY",
    "message": "관련 문서를 찾지 못했습니다."
  }
}
```

| code | 상황 |
|---|---|
| `RETRIEVAL_EMPTY` | 권한 내 검색 결과가 없음 |
| `CITATION_UNVERIFIED` | 출처 검증 실패 |
| `UPSTREAM_LLM_ERROR` | LLM 호출 실패 |

---

## 변경 규칙

- 엔드포인트·요청/응답 필드 변경 시 이 문서를 함께 수정한다.
- 응답에서 출처(`citations`)는 제거하지 않는다(출처 기반 답변 원칙).
- 스트리밍(SSE) 도입 등 응답 방식 변경 시 Plan에 영향 범위를 명시한다.
