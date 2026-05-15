# Current Plan

이 문서는 현재 진행 중인 작업의 Plan을 기록한다. 구현 전에 작성하고, 작업 중 계획이 바뀌면 함께 수정한다.
하나의 feature가 끝나면 체크 처리하고, 모든 feature가 끝나면 새 세션에서 다음 Plan을 작성한다.

> **상태: 제안 초안.** 설계 문서(`docs/rag-pipeline-design.md`, `docs/chunking-strategy.md`)를 기반으로
> 작성한 feature 분해 초안이다. 본격 착수 시 Claude Code Plan Mode로 feature별 상세 Plan을
> 다시 확정한다(`docs/ai/workflow.md` §2). 아래 순서·범위는 팀 리뷰 후 조정한다.

---

## 작업 개요

- **작업 목표**: RAG Pipeline 기본 골격 구축 — Ingestion·Query 양 파이프라인의 동작 가능한 MVP
- **담당 영역**: RAG Pipeline (`app/`, `tests/`)
- **브랜치 규칙**: feature별로 `feat/#<이슈번호>/<기능-이름>`
- **수정 가능 파일**: `app/`, `tests/`, 관련 `docs/`
- **수정 금지 파일**: 루트 `CLAUDE.md`, `docs/ai/workflow.md`·`prompt-templates.md`, 다른 팀원 담당 영역
- **참고 문서**: 루트 `CLAUDE.md`, `app/CLAUDE.md`, `docs/rag-pipeline-design.md`, `docs/chunking-strategy.md`, `docs/db-schema.md`, `docs/api-spec.md`, `docs/atlassian-api.md`, `docs/conventions.md`

## 선행 확인 / 의존성

- [x] **기획서 `PLAN-CONF-RAG-2026-002 v2.1.6`** — 확보 완료. 설계서와 정합성 확인됨
- [x] **첨부 파일 원본 4건** — 확보 완료, `samples/attachments/`에 위치 (feature4 픽스처)
- [x] **샘플 데이터** — `samples/`에 confluence(57p)·datadog(35p) JSON 배치 완료
- [x] **Atlassian API 명세** — 확보. `docs/atlassian-api.md`로 정리. 데이터 수집은 ML 파이프라인(본 저장소) 책임
- [x] **ACL 필드 모델 결정** — `allowed_groups`/`allowed_users` 청크 Payload 모델 채택(기획서 §6.6·설계서 원안). `app/query/acl.py`의 필터 생성 로직은 추후 교체 가능하도록 분리. → 결정 완료

### 미정 (TBD) — 기록 후 후속 단계에서 해소

- [~] **PoC 샘플 데이터의 ACL 출처** — `JsonFixtureSourceAdapter`는 PoC 임시 방편으로 `space_key` 기반 ACL을 합성한다(`allowed_groups = ["space:{space_key}"]`, `_synthesize_acl`). 실제 ACL 연동(Confluence content restrictions 또는 별도 mock 주입) 방식은 여전히 미정 — `AtlassianSourceAdapter` 구현 시 또는 백엔드 협의 후 `_synthesize_acl`만 교체
- [ ] **`access_token`/`cloudid` 전달 경로** — Authorization Server(Spring) → ML 파이프라인 전달 방식(요청 헤더 / 내부 호출) 미정. `AtlassianSourceAdapter` 착수 전 백엔드와 확정. RAG 코어 코드(feature1·2 일부·3·4 등)는 이 결정과 무관하게 선행 진행
- [ ] **PageObject 계약 동결** — `attachments[]` 등 스펙 동결 (`docs/rag-pipeline-design.md` §7.1)

---

## Milestone A — 공통 기반

### feature1: schemas + config  ✅ 완료 (2026-05-15, 35 tests passed)

- **작업 목표**: 파이프라인 전 단계가 공유하는 Pydantic 데이터 계약과 환경 설정 정의
- **브랜치**: `feat/#1/rag-pipeline-skeleton` (골격과 동일 change-set 연장 — 기반 작업)
- **수정 대상 파일**:
  - `app/schemas/enums.py` — DocType(6) / AttachmentType(4) / SourceType / ExtractedFormat / Intent(4) / VerificationStatus / IngestionStage / IngestionStatus / LlmModel
  - `app/schemas/page_object.py` — `PageObject`, `Attachment` (Ingestion 입력, 설계서 §7.1)
  - `app/schemas/chunk.py` — `Chunk`, `ChunkMetadata` (19종, chunking-strategy §6) + `make_chunk_id()` 결정론 헬퍼
  - `app/schemas/rag_state.py` — `RagState`(Query 그래프 상태), `IngestionState`(Ingestion 그래프 상태)
  - `app/schemas/response.py` — `QueryResponse`, `Source`, `Verification` (api-spec.md)
  - `app/schemas/__init__.py` — 주요 모델 re-export
  - `app/config.py` — `Settings` (pydantic-settings): source.type, Qdrant/Mongo/MySQL/OpenAI, 모델명
  - `tests/schemas/*`, `tests/test_config.py`
- **수정하지 않을 파일**: `app/` 그 외, 다른 팀원 담당 영역
- **구현 단계** (테스트 우선): ① 테스트 케이스 작성 → ② `app/schemas` 구현 → ③ `app/config.py` 구현 → ④ `./scripts/verify.sh`
- **테스트 계획**:
  - enums 값이 설계 문서와 정합 (DocType=incident/operation/faq/meeting/adr/troubleshoot 등)
  - `PageObject` 필수 필드 검증, `is_acl_missing` 식별(둘 다 빈 배열 → True), `Attachment` 검증
  - `ChunkMetadata` 19종 필드, `make_chunk_id` 멱등성(동일 입력 → 동일 id, UUID 미사용)
  - `QueryResponse` round-trip(직렬화/역직렬화), 첨부 전용 필드 Optional 동작
  - `Settings` 환경 변수 없이 기본값 인스턴스화 + env override 동작
- **문서 수정 필요 여부**: 없음 (스키마는 `docs/db-schema.md`·`docs/api-spec.md`·`docs/rag-pipeline-design.md` §7과 정합 확인만)
- **위험 요소**: PageObject 계약 미동결 시 재작업 가능 — 변경 시 영향은 어댑터(feature2)·청커(feature3·4)에 국한
- **완료 기준**: 모든 스키마 모델이 설계 문서와 정합 / 단위 테스트 전체 통과 / `Settings()` 무인자 인스턴스화 가능 / `verify` 통과 / `working-log.md` 갱신

작업 항목:

- [x] enums / PageObject·Attachment / Chunk·ChunkMetadata·make_chunk_id / RagState·IngestionState / 응답 스키마 정의
- [x] `app/config.py` — pydantic-settings 환경 설정
- [x] feature1 단위 테스트 통과 (35 passed)

### feature2: Document Source Adapter  ⏳ 진행 중 (데이터 계층 완료, Atlassian 어댑터 보류)

- 요구사항: 데이터 공급원 추상화. JSON 픽스처 어댑터 + Atlassian 직접 호출 어댑터
- 수정 대상: `app/adapters/{base,json_fixture,atlassian}.py`
- 테스트: `samples/*.json`으로 `JsonFixtureSourceAdapter` 계약 검증, mock HTTP로 `AtlassianSourceAdapter`의 `fetch_pages`/`list_active_ids`/`watch_changes` 검증
- 위험: `access_token`/`cloudid` 전달 방식 미확정 (선행 의존성 참조)

작업 항목:

- [x] `DocumentSourceAdapter` 인터페이스 + `ActiveIds`/`ChangeEvent` (`app/adapters/base.py`)
- [x] `JsonFixtureSourceAdapter` — `samples/*.json` → PageObject 변환 (92p 로드 검증, PoC ACL 합성)
- [ ] `AtlassianSourceAdapter` — `atlassian-python-api`로 `DATA-01`(Full Crawl) / `DATA-02`(CQL Delta Sync) / `DATA-03`(Space 목록) 호출 (`docs/atlassian-api.md`). **`access_token`/`cloudid` 전달 경로 확정 후 착수**

## Milestone B — Ingestion 파이프라인

### feature3: Adaptive Chunker (본문 6유형)  ✅ 완료 (2026-05-15)

- **작업 목표**: `samples/`의 92개 PageObject 본문(`body_html`)을 doc_type별 논리 단위로
  분할하여 `Chunk` 목록을 산출. 데이터 → 청크 단계 검증.
- **브랜치**: `feat/#1/rag-pipeline-skeleton` (기반 작업 연장)
- **규모상 2개 마일스톤으로 분할**:

  **feature3-A: 청킹 기반 (foundation)**
  - `app/ingestion/chunker/tokenizer.py` — `count_tokens()` 토큰 카운터.
    PoC 임시 구현(공백+CJK 휴리스틱, 의존성 없음). 실제 임베딩 모델 SentencePiece는
    품질 튜닝 단계에서 교체 — `docs/chunking-strategy.md` §7 정합
  - `app/ingestion/chunker/storage_format.py` — Confluence Storage Format(HTML) 공통 전처리
    (BeautifulSoup/lxml): 매크로 정규화, 코드블록 ``` 펜스 보존, `<table>` → 마크다운,
    이미지 alt/caption만 보존, 스마트 따옴표 정규화. 파싱 실패 시 plain text fallback
  - `app/ingestion/chunker/base.py` — 2단계 하이브리드 분할 공통 로직:
    2차 재분할(800토큰 초과 → 100토큰 오버랩), 하한선 병합(200토큰 미만),
    원자성 유지 유형 제외 처리, `make_chunk_id` 연동
  - 테스트: 토큰 카운터, HTML 전처리(매크로/코드블록/표/이미지), 2차 분할·하한선·원자성

  **feature3-B: 본문 6유형 분할기**
  - `app/ingestion/chunker/body.py` — doc_type별 1차 논리 단위 파서
    (incident 4블록 / operation H2 / faq Q&A쌍 / meeting 안건 / adr 전체1청크 / troubleshoot 케이스)
  - `app/ingestion/chunker/metadata.py` — 청크 메타데이터 19종 부착 + 무결성 규칙
  - `app/ingestion/chunker/__init__.py` — `chunk_page(page, doc_type) -> list[Chunk]` 엔트리
  - 테스트: 유형별 1차 분할, 원자성(FAQ·ADR·회의록), `samples/` 실제 본문 청킹 통합 테스트
- **doc_type 입력**: feature3은 `doc_type`을 입력으로 받는다(문서 분석기 Agent는 feature6).
  테스트·데모에서는 doc_type을 명시 주입하거나 라벨/제목 휴리스틱으로 임시 부여
- **문서 수정**: 청킹 규칙이 설계서와 달라지면 `docs/chunking-strategy.md` 함께 수정
- **완료 기준**: 6유형 분할·2단계 분할·원자성·메타데이터 무결성 단위 테스트 통과 /
  `samples/` 본문이 청크로 분할되는 통합 테스트 통과 / `verify` 통과

작업 항목:

- [x] feature3-A: tokenizer + storage_format(HTML 전처리) + chunker base(2단계 분할/하한선) — 24 tests, samples 92개 본문 전처리 오류 0건
- [x] feature3-B: 본문 6유형 분할기 + 메타데이터 부착 + chunk_page — 18 tests, samples 92p → 289 청크 오류 0건

### feature4: Adaptive Chunker (첨부 3유형)

- **작업 목표**: `samples/attachments/`의 첨부 파일을 `attachment_type`별 청킹 전략으로
  분할하여 `Chunk` 목록을 산출. 첨부 → 청크 단계 검증 (chunking-strategy.md §5).
- **브랜치**: `feat/#1/rag-pipeline-skeleton` (기반 작업 연장)
- **픽스처 가용성 기준 2개 마일스톤으로 분할**:

  **feature4-A: docx / xlsx 첨부 분할기**  ✅ 완료 (2026-05-15)
  - `app/ingestion/chunker/attachment.py` — 첨부 청킹
    - `infer_attachment_type(attachment)` — mime/확장자 기반 PoC 추정기
      (실제 분류는 첨부 분석기 [Pipeline]=feature6 책임)
    - docx: python-docx로 본문 블록(문단·표)을 문서 순서로 순회 → Heading 1/2/3
      경계 1차 분할(없으면 단락 fallback), 표는 마크다운 변환, 첫 헤딩 이전 preamble은
      첫 섹션에 부착. 원자성 없음 → `apply_size_rules`(2차 재분할·하한선 병합) 적용.
      `extracted_format=raw_text`, section_header=Heading 텍스트
    - xlsx: openpyxl로 시트 단위 1차 분할 → 시트 내 N행 그룹(기본 50행, 직렬화 결과
      800토큰 초과 시 25→10행 축소). 각 행을 `[<시트명>] <컬럼>: <값> | ...` 자연어
      직렬화, 컬럼명 헤더 매 청크 반복 부착, 빈 셀 생략, 헤더 누락 시 `col_1,col_2,...`
      부여. `extracted_format=sheet_serialized`, section_header=`[시트명] 행 N~M`
    - `build_attachment_metadata` — 첨부 청크 메타데이터 19종(`source_type=attachment`,
      `attachment_*`/`extracted_format` 채움, `doc_type`=attachment_type 값,
      `chunk_id`=make_chunk_id(parent_page_id, chunk_index, attachment_id), ACL·
      space_key·labels·webui_link·last_modified는 부모 페이지 상속)
    - `chunk_attachment(attachment, page, attachment_type=None) -> list[Chunk]` 엔트리
  - 재사용(feature3 자산): `ChunkDraft`/`apply_size_rules`/`count_tokens`/`make_chunk_id`
  - **버그 수정(`app/ingestion/chunker/base.py`)**: `merge_undersized`가 하한선을 채운
    직전 청크를 '봉인'하지 않아 작은 청크가 무한 누적 → 문서 전체가 한 청크로 붕괴하던
    버그를 수정. docx 첨부(Heading 섹션 다수가 200토큰 미만)에서 발견. 재현 테스트 선작성
    후 수정 — 본문 청킹도 함께 개선됨(`working-log.md` 참조)
  - 테스트: `infer_attachment_type`, docx Heading 계층 분할·표 마크다운·preamble 부착·
    헤딩 없는 fallback, xlsx 시트 분할·행 직렬화 형식·컬럼명 동봉·빈 셀 생략·50행 그룹
    분할·헤더 누락 fallback, 첨부 메타데이터 19종·결정론 chunk_id·ACL 상속,
    `samples/attachments/` 4건 통합 청킹, `merge_undersized` 봉인 회귀 테스트

  **feature4-B: PDF / CSV 첨부 분할기**  ⏳ 보류 (픽스처·의존성 대기)
  - PDF: PyMuPDF(fitz) → pdfplumber fallback, 섹션 휴리스틱(폰트 크기·굵기·짧은 행),
    미검출 시 800토큰 슬라이딩 윈도우. **PDF 픽스처 미확보 + `pymupdf` 미설치** → 보류
  - CSV: pandas(인코딩 자동감지), xlsx와 직렬화 로직 공유. 별도 픽스처 없음 → 보류
  - 착수 조건: PDF 픽스처 확보 + `pymupdf`/`pdfplumber` 설치 후 별도 세션
- **수정하지 않을 파일**: `app/schemas/*`(ChunkMetadata 19종은 첨부 5종 이미 포함),
  `app/ingestion/chunker/{body,metadata,storage_format,tokenizer}.py`(feature3 완료분 — 재사용만),
  `app/adapters/*`, 다른 팀원 담당 영역
  (`base.py`는 당초 재사용만 예정이었으나 `merge_undersized` 붕괴 버그 발견으로 수정 — 위 참조)
- **문서 수정**: DB 스키마·청킹 규칙 변경 없음(db-schema.md §1.2·chunking-strategy.md §5 정합).
  구현 해석(docx 섹션 비원자성, xlsx 자체 oversize 처리)은 `working-log.md`에 기록
- **완료 기준**: docx Heading 분할·xlsx 행 직렬화·헤더 fallback·메타데이터 무결성 단위
  테스트 통과 / `samples/attachments/` 4건 통합 청킹 오류 0건 / `verify` 통과

작업 항목:

- [x] feature4-A: docx / xlsx 첨부 분할기 + 첨부 메타데이터 + chunk_attachment
- [ ] feature4-B: PDF / CSV 첨부 분할기 (픽스처·`pymupdf` 확보 후 별도 세션)

### feature5: Dual Embedding + Multi-Pool Vector Store

- 수정 대상: `app/ingestion/embedding.py`, `app/ingestion/vector_store.py`
- 테스트: fake Qdrant로 3 Pool upsert, ACL Payload 부착, `embedding_cache` 멱등성
- 문서 수정: Pool/스키마 변경 시 `docs/db-schema.md`

작업 항목:

- [ ] Dense(e5-large) + Sparse(BM25) 임베딩, Qdrant title/content/label pool upsert

### feature6: 문서 분석기 + 첨부 분석기 + Ingestion 그래프

- 수정 대상: `app/ingestion/{document_analyzer,attachment_analyzer,sync,jobs}.py`, `app/pipeline/ingestion_graph.py`, `app/llm/*`
- 테스트: mock LLM으로 doc_type 판별·캐싱·Fallback, Reconciliation 고스트 삭제, 그래프 흐름
- 위험: 문서 분석기는 Agent — LLM 응답 mock 필수

작업 항목:

- [ ] 문서 분석기 [Agent] + 첨부 분석기 [Pipeline] + 삭제 동기화 + Ingestion LangGraph 조립

## Milestone C — Query 파이프라인

> **진행 메모 (2026-05-15)**: RAG 담당자의 기획서 범위는 Query 파이프라인이므로, Ingestion
> (Milestone B)은 feature4-A까지 완료한 상태에서 Query(Milestone C)로 전환한다. Ingestion
> 잔여(feature4-B-2 PDF, feature5·6)는 별도 담당/세션 몫. feature1·2(공통 기반)는 양 파이프라인
> 공용이라 그대로 활용한다.

### feature7: ACL Pre-filtering + @enforce_acl  ✅ 완료 (2026-05-15)

- **작업 목표**: 사용자 단위 검색의 권한 경계를 시스템 단에서 강제. JWT에서 사용자 식별을
  추출하고, Qdrant 검색에 항상 주입되는 ACL 필터를 생성하며, ACL 없는 검색 호출을
  데코레이터로 거부한다 (rag-pipeline-design.md §6 4.2, app/CLAUDE.md §3, db-schema.md §1.4).
- **브랜치**: `feat/#1/rag-pipeline-skeleton` (기반 작업 연장)
- **수정 대상 파일**:
  - `app/query/acl.py` (신규)
    - `extract_principal(jwt) -> Principal` — JWT payload를 stdlib base64+json으로 디코드해
      `sub`(user_id)·`groups`만 추출. **서명은 검증하지 않는다** — 인증/JWT 발급은 BFF 책임
      (api-spec.md). 형식 오류·`sub` 누락 시 `PrincipalExtractionError`(API의 `UNAUTHORIZED` 대응)
    - `build_acl_filter(user_id, groups) -> dict` — `allowed_groups`가 사용자 그룹 중 하나와
      매칭 **OR** `allowed_users`가 user_id 포함, 하는 Qdrant `should` 필터 dict 생성
      (`RagState.acl_filter`가 `dict[str, Any]` 계약). ACL 필드 모델은 `allowed_groups`/
      `allowed_users` 채택 결정됨 — 이 함수만 교체하면 다른 모델로 전환 가능 (app/CLAUDE.md §3)
    - `ACLViolationError` + `@enforce_acl` — 검색 함수에 유효한 `acl_filter` 인자가 없으면
      거부. 데코레이션 시점에 `acl_filter` 파라미터 존재를 강제하고, 호출 시점에 필터
      누락·무효를 `ACLViolationError`로 거부. ACL 검사는 호출 전이라 sync/async 함수 모두 지원
  - `app/query/__init__.py` — re-export 갱신 (adapters/·chunker/와 동일 패턴)
  - `tests/query/__init__.py`, `tests/query/test_acl.py` (신규)
- **수정하지 않을 파일**: `app/schemas/*`(RagState가 이미 `user_id`/`groups`/`acl_filter` 보유 —
  변경 불필요), `app/` 그 외, 다른 팀원 담당 영역
- **구현 단계** (테스트 우선): ① 테스트 작성 → ② `acl.py` 구현 → ③ `__init__.py` re-export →
  ④ `./scripts/verify.sh`
- **테스트 계획**:
  - `extract_principal`: 정상 JWT → Principal, groups 누락 시 `[]` 기본값, 형식 오류·payload
    디코드 실패·`sub` 누락 시 `PrincipalExtractionError`
  - `build_acl_filter`: `should` OR 구조(allowed_groups any / allowed_users any), 빈 groups 처리
  - `@enforce_acl`: 유효 필터 시 정상 호출, 필터 누락/None/무효 시 `ACLViolationError`,
    `acl_filter` 파라미터 없는 함수 데코레이션 시 `TypeError`
- **문서 수정 필요 여부**: 없음 (acl.py는 db-schema.md §1.4·api-spec.md와 정합 확인만)
- **위험 요소**: 보안 핵심 — ACL 우회 불가 구조 검증 필수. 필터 생성 로직은 단일 함수로
  격리해 ACL 모델 변경 시 교체 지점을 한정
- **완료 기준**: 단위 테스트 전체 통과 / `@enforce_acl` 우회 시도가 `ACLViolationError`로
  거부됨을 테스트로 확인 / `verify` 통과 / `working-log.md` 갱신

작업 항목:

- [x] ACL 필터 생성 + `@enforce_acl` 데코레이터 + JWT 클레임 추출

### feature8: 질의 라우터 + 멀티턴 히스토리 [Agent]

- 수정 대상: `app/query/router.py`, `app/query/history.py`, `app/llm/structured_output.py`
- 테스트: mock LLM으로 4종 의도 분류·쿼리 확장·필터/가중치, 히스토리 보존·검색스킵, 타임아웃 Fallback

작업 항목:

- [ ] 질의 라우터(Intent+Rewrite+Filter 단일 호출) + 멀티턴 히스토리 관리자

### feature9: Multi-Pool Hybrid Search + Cross-Encoder 재순위화

- 수정 대상: `app/query/search.py`, `app/query/rerank.py`
- 테스트: RRF 결합, Pool 가중 합산, Top-20→Top-5, 0건/저신뢰 분기

작업 항목:

- [ ] Hybrid Search(RRF + Score Fusion) + Cross-Encoder 재순위화

### feature10: 답변 생성기 + 답변 검증

- 수정 대상: `app/query/generator.py`, `app/query/verifier.py`
- 테스트: 의도별 프롬프트 조립, citation 매핑, 1단계 규칙 매칭, 2단계 LLM 평가자 게이팅

작업 항목:

- [ ] 답변 생성기 [Agent] + 2단계 답변 검증 [Pipeline + Agent]

### feature11: 응답 포맷터 + Query 그래프 + API

- 수정 대상: `app/query/formatter.py`, `app/pipeline/query_graph.py`, `app/api/*`
- 테스트: 응답 JSON 스키마, SSE 이벤트 순서, end-to-end(전 단계 mock), 에러 응답 코드
- 문서 수정: API 변경 시 `docs/api-spec.md`

작업 항목:

- [ ] 응답 포맷터 + Query LangGraph 조립 + FastAPI 라우트(SSE)

---

## 진행 규칙 (요약)

1. feature 단위로만 작업한다. 다음 feature는 새 세션 또는 `/clear` 후 시작한다.
2. 테스트 케이스 정리 → 실패 테스트 작성 → 최소 구현 → 테스트 통과 순서를 지킨다.
3. 완료 후 `./scripts/verify.sh`(format → lint → test)를 실행한다.
4. `git diff`로 변경 범위를 확인하고 `docs/ai/working-log.md`를 업데이트한 뒤 커밋한다.
5. Agent 컴포넌트는 LLM 응답을 mock/fake로 대체해 테스트한다. 외부 의존성(Qdrant/Mongo/MySQL)도 동일.
