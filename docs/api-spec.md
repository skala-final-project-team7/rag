# API Spec

이 문서는 RAG 파이프라인이 API Gateway / BFF에 노출하는 API 계약을 정의한다.
RAG 파이프라인 설계서 v0.2.2(`docs/rag-pipeline-design.md`) §4.8과 정합한다.
API 변경 시 이 문서를 함께 수정한다(루트 `CLAUDE.md` 규칙).

> 인증/인가 플로우, JWT 발급, Gateway 라우팅은 백엔드/BFF 담당 영역이다. 본 파이프라인은
> BFF가 전달한 JWT에서 `user_id`/`groups`를 추출해 ACL 필터에 사용한다.
> 엔드포인트 경로·버전은 BFF 설계서와 동결 전까지 잠정값이다.

---

## POST /api/v1/rag/query

사용자 질의를 받아 ACL 기반 검색 → 답변 생성 → 출처 검증을 수행하고 답변·출처를 SSE로 스트리밍한다.

- 인증 필요: 예 (BFF가 JWT 전달)
- 응답 방식: `text/event-stream` (SSE). 답변 토큰을 순차 전송하고, 출처 카드·검증 결과는 답변 완료 직후 일괄 push

### Request Body

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `query` | string | Y | 사용자 자연어 질문 |
| `conversation_id` | string | N | 대화 컨텍스트 ID (멀티턴 히스토리 관리자가 사용) |
| `jwt` | string | Y | 인증 토큰. `sub`(user_id) + `groups[]` 포함 |

### SSE 이벤트 순서

1. `token` 이벤트 (n회) — 답변 텍스트 토큰 (Markdown)
2. `sources` 이벤트 (1회) — 출처 카드 배열
3. `verification` 이벤트 (1회) — 문장별 검증 결과
4. `meta` 이벤트 (1회) — `intent`, `used_llm`, `feedback_enabled`, `latency_ms`
5. `done` 이벤트

> **PoC 제약** — 답변 토큰 스트리밍은 답변 생성기 Agent 통합 후 활성화된다.
> feature11 통합 Phase 2 구현(`app/api/routes.py`)은 `token` 이벤트를 1회만 송신해
> 전체 답변을 한 번에 전달하며, 나머지 이벤트(sources / verification / meta / done)
> 시퀀스·계약은 동일하게 유지한다. Agent 코드 전달 시 `token` 다중 송신만 확장하면
> BFF/프론트 호환성 유지.

### 응답 객체 스키마 (완성형)

```jsonc
{
  "answer": "string (Markdown). 각 문장에 [#n] 형식 근거 청크 번호 명시",
  "sources": [
    {
      "title": "page_title > section_header",
      "score": 87,                    // Cross-Encoder 관련도 0~100
      "path": "section_path (계층 경로)",
      "space_key": "INFRA",            // 사용자 단위 검색 시 다중 스페이스 혼재 가능
      "source_type": "page",           // page | attachment
      "attachment_filename": "...",    // source_type=attachment 일 때만
      "attachment_mime": "...",        // source_type=attachment 일 때만
      "download_url": "...",           // source_type=attachment 일 때만
      "confluence_url": "https://confluence.../pages/12345#anchor",
      "last_modified": "ISO 8601",
      "text_preview": "청크 본문 첫 200자"
    }
  ],
  "verification": [
    {
      "sentence_id": 1,
      "status": "PASS",               // PASS | SUPPORTED | NOT_SUPPORTED
      "cited_chunks": [1, 3]
    }
  ],
  "intent": "장애대응",                // 장애대응 | 운영가이드 | 정책절차 | 이력조회
  "used_llm": "gpt-4o",                // gpt-4o | gpt-4o-mini
  "feedback_enabled": true,            // 저신뢰 응답이면 false 가능
  "latency_ms": 4120
}
```

### 표준 분기 응답

| 상황 | 처리 |
|---|---|
| ACL 결과 후보 0건 | "권한 범위 내에서 참고할 수 있는 문서를 찾지 못했습니다" 표준 응답, LLM 미호출 |
| Cross-Encoder Top-5 최고 점수 < 0.20 | 저신뢰 분기 — 출처를 '참고용'으로 제시 + 경고 배지, `feedback_enabled=false` |
| `verification` 중 `NOT_SUPPORTED` 비율 > 50% | 답변 차단, 저신뢰 응답으로 대체, 운영 긴급 알림 |

### Error Response

```jsonc
{ "success": false, "error": { "code": "RETRIEVAL_EMPTY", "message": "..." } }
```

| code | 상황 |
|---|---|
| `UNAUTHORIZED` | JWT에서 `user_id`/`groups` 추출 실패 (401) |
| `RETRIEVAL_EMPTY` | 권한 내 검색 결과 0건 |
| `LOW_CONFIDENCE` | 재순위화 최고 점수 < 0.20 (저신뢰) |
| `UPSTREAM_LLM_ERROR` | LLM 호출 실패 / 타임아웃 |
| `VERIFICATION_BLOCKED` | `NOT_SUPPORTED` 비율 > 50%로 답변 차단 |

---

## 내부 인터페이스 (참고)

다음은 외부 API는 아니지만 파이프라인 경계에서 동결되는 계약이다.

- **PageObject** — Document Source Adapter → Ingestion 파이프라인 입력. `docs/rag-pipeline-design.md` §7.1
- **DocumentSourceAdapter** — `fetch_pages()` / `list_active_ids()` / `watch_changes()`. 구현은 백엔드 책임

---

## 변경 규칙

- 엔드포인트·요청/응답 필드 변경 시 이 문서를 함께 수정한다.
- 응답에서 출처(`sources`)·검증(`verification`)은 제거하지 않는다 (출처 기반·검증 가능성 원칙).
- SSE 이벤트 순서·이름 변경은 BFF/프론트 영향이 있으므로 Plan에 영향 범위를 명시하고 사전 협의한다.
