# SSE 이벤트 계약 — 프론트엔드 핸드오프

`POST /api/v1/rag/query` 의 SSE 응답 계약을 프론트엔드 관점에서 정리한 문서다.
근거 코드: `app/api/routes.py`, `app/schemas/response.py`, `app/schemas/enums.py`,
`app/query/formatter.py`, `app/api/errors.py`. 정본 계약은 `docs/api-spec.md`.

---

## 1. 엔드포인트

- **Method / Path**: `POST /api/v1/rag/query`
- **응답 Content-Type**: `text/event-stream` (SSE)
- **인증**: BFF가 전달한 JWT 필요

### Request Body

| 필드 | 타입 | 필수 | 기본값 | 설명 |
|---|---|---|---|---|
| `query` | string | Y | — | 사용자 자연어 질문 (최소 1자) |
| `jwt` | string | Y | — | `sub`(user_id) + `groups[]` 포함 |
| `conversation_id` | string | N | null | 멀티턴 대화 컨텍스트 ID |
| `stream` | boolean | N | `false` | true면 토큰 단위 스트리밍. PoC 환경(OpenAI 키 없음)에서는 true여도 자동으로 비스트리밍 fallback |

---

## 2. SSE 이벤트 순서 (총 5종)

항상 아래 순서로 전송된다.

| # | event | 횟수 | data 형식 | 비고 |
|---|---|---|---|---|
| 1 | `token` | n회 | 평문 string (Markdown) | 비스트리밍: 1회(전체 답변) / 스트리밍: 토큰 단위 다회 |
| 2 | `sources` | 1회 | **JSON 문자열** (배열) | `JSON.parse` 필요 |
| 3 | `verification` | 1회 | **JSON 문자열** (배열) | `JSON.parse` 필요 |
| 4 | `meta` | 1회 | **JSON 문자열** (객체) | `JSON.parse` 필요 |
| 5 | `done` | 1회 | 빈 문자열 `""` | 종료 마커 |

> `token`, `done` 의 `data`는 평문. `sources` / `verification` / `meta` 의 `data`는
> JSON이 문자열로 인코딩되어 있으므로 프론트에서 한 번 더 파싱해야 한다.

---

## 3. 각 이벤트 페이로드

### 3.1 `token`

답변 텍스트. 누적해서 화면에 렌더링한다.

```
event: token
data: 장애 발생 시 먼저 #infra-alert 채널을 확인하세요. [#1]
```

- 답변 문장에는 `[#n]` 형식의 근거 청크 번호가 포함될 수 있다.
- **빈 token (`data: ""`) = 버퍼 클리어 신호** (스트리밍 모드 한정). 아래 6번 참고.

### 3.2 `sources` — 출처 카드 배열

```jsonc
[
  {
    "title": "페이지제목 > 섹션헤더",
    "score": 87,                       // Cross-Encoder 관련도 0~100 (정수)
    "path": "섹션 계층 경로",
    "space_key": "INFRA",
    "source_type": "page",             // "page" | "attachment"
    "confluence_url": "https://confluence.../pages/12345#anchor",
    "last_modified": "2026-05-20T08:30:00Z",  // ISO 8601
    "text_preview": "청크 본문 미리보기",
    "attachment_filename": null,       // source_type=attachment 일 때만 값
    "attachment_mime": null,           // source_type=attachment 일 때만 값
    "download_url": null               // source_type=attachment 일 때만 값
  }
]
```

### 3.3 `verification` — 문장별 검증 결과

```jsonc
[
  {
    "sentence_id": 1,
    "status": "PASS",                  // "PASS" | "SUPPORTED" | "NOT_SUPPORTED"
    "cited_chunks": [1, 3]             // 해당 문장이 인용한 청크 번호
  }
]
```

### 3.4 `meta`

```jsonc
{
  "intent": "장애대응",                // 4종 (아래 enum 참고)
  "used_llm": "gpt-4o",                // "gpt-4o" | "gpt-4o-mini"
  "feedback_enabled": true,            // false면 저신뢰 응답 (경고 배지 권장)
  "latency_ms": 4120
}
```

### 3.5 `done`

```
event: done
data:
```

스트림 종료. 이후 추가 이벤트 없음.

---

## 4. Enum 값 (프론트 분기용)

| 대상 | 가능한 값 |
|---|---|
| `intent` | `장애대응`, `운영가이드`, `정책절차`, `이력조회` |
| `used_llm` | `gpt-4o`, `gpt-4o-mini` |
| `source_type` | `page`, `attachment` |
| `verification[].status` | `PASS`, `SUPPORTED`, `NOT_SUPPORTED` |

---

## 5. 저신뢰 / 차단 분기 (200 SSE 내부에서 처리)

오류가 아니라 정상 200 SSE 안에서 처리된다. 프론트는 `meta.feedback_enabled` 와
답변 내용으로 판단한다.

| 상황 | 동작 | 프론트 처리 |
|---|---|---|
| 검색 결과 0건 | "권한 범위 내 문서를 찾지 못했습니다" 표준 답변, LLM 미호출 | 일반 답변처럼 렌더 |
| Cross-Encoder 최고 점수 < 55 | 저신뢰 분기, `feedback_enabled=false` | 출처를 '참고용' + 경고 배지 |
| `NOT_SUPPORTED` 비율 > 50% | 답변 차단, 안내문으로 대체, `feedback_enabled=false` | 차단 안내문 렌더, 출처 직접 확인 유도 |

차단 안내문 원문:
> "검증 결과 답변의 상당 부분이 출처로 뒷받침되지 않아 답변 제공을 보류합니다. 아래 참고 출처를 직접 확인해 주세요."

---

## 6. 스트리밍 모드(`stream=true`) 특수 동작 ⚠️

프론트가 반드시 처리해야 하는 두 케이스.

1. **빈 `token` 이벤트 = 누적 버퍼 클리어**
   OpenAI Rate Limit 발생 시 fallback 모델로 재시도하며, 이미 보낸 부분 답변을
   덮어쓰도록 `{"event":"token","data":""}` 를 1회 보낸다. 프론트는 빈 token을 받으면
   지금까지 누적한 답변 텍스트를 비우고 이후 token부터 다시 누적해야 한다.

2. **차단 시 token 재전송(overwrite)**
   토큰 스트리밍이 끝난 뒤 답변이 차단 분기로 판정되면, 차단 안내문 전체를 담은
   `token` 이벤트가 1회 더 온다. 프론트는 이 token으로 기존 답변을 교체해야 한다.
   그 다음 `sources` / `verification` / `meta` / `done` 순으로 이어진다.

---

## 7. 에러 응답 (SSE 아님 — HTTP status + JSON)

오류는 SSE 스트림이 아니라 HTTP 상태 코드와 JSON 바디로 반환된다.

```jsonc
{ "success": false, "error": { "code": "UNAUTHORIZED", "message": "..." } }
```

| code | HTTP | 상황 |
|---|---|---|
| `UNAUTHORIZED` | 401 | JWT에서 user_id/groups 추출 실패 |
| `UPSTREAM_LLM_ERROR` | 502 | LLM 호출 실패 / 타임아웃 / ACL 시스템 오류 |

> `RETRIEVAL_EMPTY`, `LOW_CONFIDENCE`, `VERIFICATION_BLOCKED` 코드는 정의돼 있으나
> 현재 구현에서는 **에러가 아니라 200 SSE 내부 분기**로 처리된다 (5번 표 참고).

---

## 8. 참고 — 현재 없는 것

- **진행 상태(progress) `status` 이벤트는 없다.** "검색 중 / 생성 중" 같은 단계 표시용
  이벤트를 원한다면 신규 추가가 필요하다 (현재 미구현).
- 상태성 정보는 `verification[].status`, `meta.feedback_enabled`, 에러 `code` 세 군데로
  나뉘어 있다.
