# 0001. Attachment의 사용자 노출 URL과 청커용 로컬 경로 분리

- 상태: 채택
- 날짜: 2026-05-17
- 작성자: 최태성

## 배경

`PageObject.attachments[i]` (`app/schemas/page_object.py`)는 설계서 §7.1에서 `download_url`
단일 필드만 정의했다. PoC의 `JsonFixtureSourceAdapter`는 이 필드에 `samples/attachments/`
하위 로컬 파일 경로를 채워 청커(`app/ingestion/chunker/attachment.py`)가 직접 파일을 열어
텍스트를 추출해 왔다. 그러나 `download_url`은 동시에 `Source.download_url`(API 응답)로 그대로
사용자에게 노출되는 필드이다.

운영 어댑터(`AtlassianSourceAdapter`, current-plan feature2 잔여)가 도착하면 같은 필드에
HTTP URL이 들어올 텐데, 청커가 그 URL을 `python-docx`/`openpyxl`에 직접 전달하면 파일을
열지 못해 실패한다. 반대로 PoC 어댑터의 로컬 경로가 사용자에게 노출되면 백엔드 서버의 디스크
경로가 누출된다. 즉 **하나의 필드에 의미가 다른 두 값이 들어와** 운영 전환 시 보안·기능
양쪽에서 사고가 날 수 있다.

코드 리뷰(`docs/ai/code-review-2026-05-17.md` P1-3)에서 발견.

## 검토한 대안

### A. 단일 필드 유지 (`download_url`만 사용)

- 장점: 스키마 무변경.
- 단점: 의미 이중성. 운영 전환 시 청커가 URL을 파일로 열다 실패하거나, 로컬 경로가 사용자에게
  노출되는 사고 위험.

### B. `Attachment`에 `local_path: str | None` 추가 (채택)

- 장점:
  - `download_url`은 항상 **사용자 노출용 URI/URL**로 의미 동결.
  - `local_path`는 **청커가 파일 시스템에서 직접 열 때만** 사용. PoC 어댑터(JsonFixture)는
    채우고, 운영 어댑터(Atlassian)는 비워둔다.
  - 운영 어댑터 도착 시 별도 다운로드 헬퍼가 임시 경로를 `local_path`에 채우면 청커는
    그대로 동작 — 청커 코드 변경 없음.
  - 기존 `download_url` 사용자(`Source.download_url`)는 무변경 — 비파괴.
- 단점: 어댑터 계약에 한 필드 추가. 운영 어댑터 구현자는 다운로드 단계를 추가해야 한다는
  점이 명확해진다(이건 오히려 장점).

### C. `download_url`을 항상 URL로 두고 청커가 다운로드까지 책임

- 장점: 청커가 단일 책임.
- 단점: PoC 단계에서 불필요한 다운로드 단계 추가. 로컬 픽스처를 위해 file:// 스킴 처리·임시
  경로 관리가 필요. 어댑터/청커 책임 경계가 흐려진다.

## 결정

대안 **B**를 채택한다.

- `Attachment.local_path: str | None = None` 필드를 신설(기본 `None`, 비파괴).
- `Attachment.download_url`은 사용자 노출용 URI/URL로 의미 동결한다.
  - PoC 어댑터는 `file://...` URI를 사용한다.
  - 운영 어댑터는 Confluence의 다운로드 URL을 그대로 사용한다.
- 청커는 `attachment.local_path or <download_url fallback>` 순서로 경로를 결정한다
  (`_resolve_attachment_path` 헬퍼).
- 운영 어댑터 구현 시(feature2 잔여) 다운로드 단계가 `local_path`를 채우는 것을 책임진다.
  본 ADR이 그 책임을 명시한다.

## 영향

- 수정 파일: `app/schemas/page_object.py`, `app/adapters/json_fixture.py`,
  `app/ingestion/chunker/attachment.py`, `docs/db-schema.md`(아래).
- 동결 계약 변경(`PageObject.attachments[].local_path` 추가)이라 BFF·AtlassianSourceAdapter
  담당자에게 알림 필요(`docs/ai/working-log.md`에 기록). 다른 담당자 영역(`app/api/`,
  운영 어댑터 등)의 기존 코드는 영향 없음 — 새 필드는 선택(`None`)이므로 비파괴.
- `Source.download_url`(API 응답)은 변경 없음. 사용자 노출 URL 의미는 그대로 유지.
- 후속 작업: 운영 `AtlassianSourceAdapter` 구현 시 다운로드 헬퍼로 `local_path`를 채우는
  단계를 포함(feature2 잔여, current-plan 참조).

## 함께 수정한 문서

- `docs/db-schema.md` — Attachment 스펙 갱신.
- `docs/ai/working-log.md` — 변경 사항·결정 기록.
- `docs/ai/code-review-2026-05-17.md` — 본 ADR로 P1-3이 해소됨을 반영(working-log 경로로).
