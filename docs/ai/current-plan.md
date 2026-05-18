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

### feature5: Dual Embedding + Multi-Pool Vector Store [Pipeline + Storage]

- **작업 목표**: 청크를 Pool별 임베딩 입력으로 변환하고, Qdrant Multi-Pool에 적재할 Point
  payload를 구성하며, embedding_cache 기반 멱등성을 확보한다 (rag-pipeline-design.md §5,
  db-schema.md §1·§2.4). 청커 산출물(`Chunk`)을 실제 검색 가능한 색인으로 잇는 "다리".
- **브랜치**: `feat/#1/rag-pipeline-skeleton` (기반 작업 연장)
- **외부 의존성(e5-large 모델·Qdrant·MongoDB) 분리 위해 2개 마일스톤으로 분할**:

  **feature5-A: 임베딩 입력·payload·멱등성 순수 로직**  ✅ 완료 (2026-05-15)
  - `app/ingestion/vector_store.py` [Storage] — Pool 이름 상수(`TITLE_POOL`/`CONTENT_POOL`/
    `LABEL_POOL`, config.py 기본값과 정합) + `build_point_payload(chunk, version_number)`:
    `Chunk` → Qdrant Point payload dict(db-schema.md §1.2의 19필드). `version_number`는
    ChunkMetadata에 없으므로(페이지 단위 값) 부모 PageObject에서 별도 인자로 주입.
    Point id는 chunk_id(feature1 `make_chunk_id`)
  - `app/ingestion/embedding.py` [Pipeline] — `pool_embedding_texts(chunk)`: Pool별 임베딩
    입력 텍스트 구성(title=page_title+section_header / 첨부는 attachment_filename+
    section_header, content=청크 본문, label=labels+space_key+doc_type) +
    `should_skip_embedding(version_number, cached_version)`: 멱등성 판정(app/CLAUDE.md §4)
  - 외부 의존성 0 — e5-large·Qdrant·MongoDB 없이 완전히 단위테스트 가능
  - 테스트: payload 19필드 매핑·page/attachment 분기·text_preview 200자·version_number
    주입, pool별 텍스트 구성, 멱등성 판정(동일 버전 skip / 캐시 없음 / 버전 불일치)

  **feature5-B: 실제 임베딩·Qdrant·MongoDB 클라이언트 연동**  ⏳ 보류 (무거운 의존성)
  - Dense(`intfloat/multilingual-e5-large`, 1024d)·Sparse(BM25) 실제 임베딩, Qdrant 3 Pool
    Collection 생성·Named Vector upsert, MongoDB `embedding_cache` I/O. e5의 `passage:`
    프리픽스 등 모델별 처리도 여기서.
  - 착수 조건: 무거운 의존성(`sentence-transformers`/torch·`qdrant-client`·`pymongo`) 방향
    확정 후 — PoC 단계는 가짜/경량 임베더 + Qdrant `:memory:` 또는 fake로 진행 검토.
    임베딩·Qdrant·Mongo는 어댑터/클라이언트 계층으로 분리(app/CLAUDE.md §8)
- **수정하지 않을 파일**: `app/schemas/*`(ChunkMetadata에 version_number 부재 — payload
  빌더가 별도 인자로 받아 해소, 스키마 변경 안 함), `app/llm/*`, 다른 팀원 담당 영역
- **문서 수정**: feature5-A는 db-schema.md §1.2 payload 스키마를 구현만 — 변경 없음(정합 확인).
  Pool/스키마를 바꾸게 되면 `docs/db-schema.md` 함께 수정
- **완료 기준(5-A)**: 단위 테스트 전체 통과 / `verify` 통과 / `working-log.md` 갱신

작업 항목:

- [x] feature5-A: 임베딩 입력·payload·멱등성 순수 로직
- [ ] feature5-B: 실제 임베딩·Qdrant·MongoDB 클라이언트 연동 (무거운 의존성 방향 확정 후)

### feature6: 문서 분석기 + 첨부 분석기 + Ingestion 그래프 — ⚠ 담당 분리

- **본 담당자 몫(Pipeline + Storage)**: 첨부 파일 분석기(`app/ingestion/attachment_analyzer.py`),
  삭제 동기화(`app/ingestion/sync.py`), `ingestion_jobs` 기록 헬퍼(`app/storage/jobs.py` —
  외부 저장소 어댑터는 `app/storage/` 패키지 일관성 정합, `app/CLAUDE.md` §8).
- **Agent 담당자 몫**: 문서 분석기(`app/ingestion/document_analyzer.py` [Agent]).
- **통합 지점**: Ingestion 그래프 조립(`app/pipeline/ingestion_graph.py`) — Agent 노드 stub →
  전달 후 교체.
- 테스트: 첨부 분석·Reconciliation 고스트 삭제·그래프 흐름(본 담당자, mock/stub),
  mock LLM으로 doc_type 판별·캐싱·Fallback(Agent 담당자)

작업 항목:

- [x] (본 담당자) 첨부 분석기 [Pipeline] — Phase 1 완료 (2026-05-18, `4c6c2dc`)
- [x] (본 담당자) `ingestion_jobs` 기록 헬퍼 [Storage] — Phase 2 완료 (2026-05-18, `152d2e9`)
- [x] (본 담당자) 삭제 동기화 [Pipeline] — Phase 3 완료 (2026-05-18)
- [ ] (본 담당자) Ingestion 그래프 조립 — Phase 4 (Phase 1~3 + Agent 노드 stub 종합)
- [ ] (Agent 담당자) 문서 분석기 [Agent]

## Milestone C — Query 파이프라인

> **진행 메모 (2026-05-15 갱신)**: RAG 담당자의 기획서 범위는 Query 파이프라인이며,
> **Agent 컴포넌트는 별도 담당자 몫**이다 — Agent 코드·파일은 추후 전달받아 병합한다.
> 따라서 본 담당자는 각 feature의 **[Pipeline]/[Storage] 부분만** 진행하고 **[Agent] 부분은
> 건너뛴다.** Ingestion(Milestone B)은 feature4-A까지 완료, 이후 Query(Milestone C)로 전환.
>
> **Agent / Pipeline 경계와 병합 방식:**
> - Agent 담당자 전달분: 질의 라우터·멀티턴 히스토리(feature8 전체), 답변 생성기·검증 2단계
>   LLM 평가자(feature10 일부), 문서 분석기(feature6 일부), 그리고 `app/llm/`(Agent 인프라).
> - Agent 노드와 Pipeline 노드는 **서로 직접 호출하지 않는다.** 공유 seam은 (1) `RagState`
>   — feature1에서 동결된 상태 계약, 각 노드가 필드를 읽고 쓴다, (2) LangGraph 그래프(feature11)
>   — 노드를 순서대로 배선, (3) 합의된 모듈 경로·노드 시그니처(각 feature에 명시).
> - 본 담당자의 Pipeline 노드는 RagState 필드 계약만 지키면 Agent 코드와 독립적으로 구현·
>   단위테스트된다. 그래프 조립 시 Agent 노드는 stub/fake로 대체했다가 실제 코드 전달 시
>   교체한다 (app/CLAUDE.md §6).
>
> **진행 순서**: feature7(완료) → feature9-A → feature10[Pipeline] → feature11[Pipeline:
> 포맷터] → feature5(다리) → feature9-B → feature11(그래프·API 조립) → feature6[Pipeline]
> → feature4-B. feature1·2(공통 기반)는 양 파이프라인 공용이라 그대로 활용한다.

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

### feature8: 질의 라우터 + 멀티턴 히스토리 [Agent] — ⚙ 통합 진행 중

- 질의 라우터·멀티턴 히스토리 관리자는 **둘 다 Agent 컴포넌트**이며 Agent 담당자가 구현해
  전달한다. 본 담당자(Pipeline/통합)는 전달받은 Agent 코드를 vendoring하고 RagState 어댑터
  노드로 통합한다.
- **병합 계약**: 노드 시그니처 `(state: RagState) -> RagState`. 라우터는 RagState의
  `intent`/`rewritten_queries`/`metadata_filters`/`pool_weights`/`target_llm`를 채운다.

  **feature8-멀티턴 히스토리: history-manager-agent 통합**  ⚙ vendoring 완료, 어댑터 진행 예정
  - **전달분**: `ai-agent` 저장소의 `history-manager-agent` — 자체 pyproject·`src/` 레이아웃·
    스키마(dataclass)·테스트를 가진 독립 패키지. 작성자 Codex.
  - **vendoring (완료, 2026-05-15)**: `src/history_manager_agent/**` → 저장소 루트
    `history_manager_agent/`(무수정), `tests/**` → `tests/history_manager_agent/**`(무수정 +
    pytest 패키지 마커 `__init__.py`만 추가), `history-manager-agent.md` → `docs/`.
    `pyproject.toml` — `packages.find`에 `history_manager_agent*` 추가, `[tool.ruff]
    extend-exclude`로 벤더 코드를 RAG lint/format 대상에서 제외(원본 무수정 보존). 벤더
    테스트 76개는 RAG `pytest`로 함께 실행되어 통과
  - **어댑터 노드 (완료, 2026-05-15)**: `app/query/history.py` — `manage_history(state:
    RagState, *, provider=None) -> RagState`. 파일 기반 워크플로 대신 agent의 조립 가능한
    로직 함수(`normalize_history_input_payload`/`classify_history`/`apply_context_policy`/
    `build_question_result`)를 in-process로 호출. 기본 provider는 `FakeHistoryLLMProvider`
    (PoC·테스트), 실제 `OpenAIHistoryLLMProvider` 주입 가능
  - **RagState 확장 (완료)**: agent 출력(`history_decision`/`contextualized_question`/
    `preserved_context`/`reset_required`/`confidence`/`reason`/`warnings`)은 RagState의
    `history`/`needs_search`에 1:1로 안 맞음. → `app/schemas/rag_state.py`에 `HistoryDecision`
    Pydantic 모델 추가하고 `RagState.history_decision: HistoryDecision | None` 필드 신설.
    매핑: `RagState.query`는 원문 유지(비파괴), `contextualized_question`은
    `history_decision`에 담아 다운스트림이 선택 사용. `needs_search`는 agent MVP가 검색스킵
    신호를 내지 않으므로 기본 `True` 유지. `conversation_id` 없으면 어댑터가 new_topic으로
    단축 처리
  - **테스트**: `tests/query/test_history.py` — RagState→agent 입력 변환(HistoryTurn→
    ConversationTurn, turn_id/created_at 합성), 분류 결과별 RagState 매핑, conversation_id
    없는 경우 단축, FakeHistoryLLMProvider 주입

작업 항목:

- [x] history-manager-agent vendoring (패키지·테스트·스펙 문서, pyproject 갱신)
- [x] `app/query/history.py` 어댑터 노드 + `RagState.history_decision` 확장 + 테스트
- [ ] (Agent 담당자) 질의 라우터 — 전달 후 동일 방식으로 통합

### feature9: Multi-Pool Hybrid Search + Cross-Encoder 재순위화 [Pipeline]

- **작업 목표**: 3개 Pool 검색 결과를 RRF로 융합·가중 합산해 Top-20을 뽑고, Cross-Encoder
  재순위화로 Top-5를 선정한다 (rag-pipeline-design.md §6 4.5, §8). 전부 [Pipeline] — 본 담당자 몫.
- **브랜치**: `feat/#1/rag-pipeline-skeleton` (기반 작업 연장)
- **외부 의존성(임베딩 모델·Qdrant·Cross-Encoder 모델) 분리 위해 2개 마일스톤으로 분할**:

  **feature9-A: 검색·재순위화 핵심 로직 (순수 함수)**  ✅ 완료 (2026-05-15)
  - `app/query/search.py` — 순수 함수: `reciprocal_rank_fusion`(RRF k=60, Pool 내부
    dense+sparse 융합), `merge_pools`(Pool 가중 합산), `select_top_candidates`(Top-20 선정,
    동점 결정론 정렬), `fuse_and_rank`(세 단계 결합 엔트리)
  - `app/query/rerank.py` — 순수 함수: `select_reranked`(Cross-Encoder 점수 → Top-5,
    5위 < 0.30이면 Top-3 축소, 최고 < 0.20이면 저신뢰 플래그) + `RerankResult` 데이터클래스
  - `app/query/__init__.py` — re-export 갱신
  - 외부 의존성 0 — 임베딩·Qdrant·Cross-Encoder 모델 없이 완전히 단위테스트 가능. feature9의
    회귀 보호 핵심 로직. RagState 통합·I/O 배선은 9-B 책임
  - 테스트: RRF 점수·순위, Pool 가중 합산, Top-N 선정·동점 정렬, Top-5/Top-3 축소,
    저신뢰 임계, 빈 입력(0건) 처리

  **feature9-B: 검색·재순위화 노드 오케스트레이션**  ⏳ 보류 (feature5·모델 의존)
  - 쿼리 임베딩 + Qdrant 3-pool 검색 + Cross-Encoder 추론을 9-A 로직에 연결하는 LangGraph
    노드(`hybrid_search`/`cross_encoder_rerank`, `(state: RagState) -> RagState`).
    `candidates`(Top-20)·`top_chunks`(Top-5)를 RagState에 채운다
  - 착수 조건: feature5(Dual Embedding + Multi-Pool Vector Store)와 Cross-Encoder 모델
    확보 후. 임베딩·Qdrant·Cross-Encoder는 어댑터/클라이언트 계층으로 분리(app/CLAUDE.md §8),
    9-B 착수 시 그 계층 위치를 feature5와 함께 확정
- **수정하지 않을 파일**: `app/schemas/*`(RagState가 이미 candidates·top_chunks 보유),
  `app/llm/*`(Agent 인프라), `app/ingestion/*`, 다른 팀원 담당 영역
- **완료 기준(9-A)**: 순수 함수 단위 테스트 전체 통과 / `verify` 통과 / `working-log.md` 갱신

작업 항목:

- [x] feature9-A: 검색·재순위화 핵심 로직 (RRF / Pool 가중 합산 / Top-K 선정 / 저신뢰 분기)
- [ ] feature9-B: 검색·재순위화 노드 오케스트레이션 (feature5·Cross-Encoder 모델 확보 후)

### feature10: 답변 생성기 + 답변 검증 — ⚠ 담당 분리

- **본 담당자 몫(Pipeline)**: 답변 검증 **1단계 규칙 매칭** — `app/query/verifier.py`.
  - **작업 목표**: 생성된 답변을 문장 단위로 분해해, 각 문장의 검증 토큰(수치·구조적 식별자)이
    인용한 청크 텍스트에 나타나는지 규칙으로 대조한다. 확인되지 않은 토큰이 있는 문장은
    의심(suspicious)으로 FLAG해 2단계 LLM 평가자로 넘기고, 그 외는 PASS로 확정한다
    (rag-pipeline-design.md §6 4.7, conventions.md §5.5).
  - **수정 대상**: `app/query/verifier.py`(신규, 1단계 부분), `app/query/__init__.py`,
    `tests/query/test_verifier.py`(신규)
  - **구현**: `verify_answer_rules(answer, top_chunks) -> RuleVerificationResult`.
    헬퍼 — 문장 분리(PoC 휴리스틱), `[#n]` 인용 추출, 인용 청크 텍스트 수집, 검증 토큰
    추출(수치·구조적 식별자 — Mecab 미사용 PoC 휴리스틱), 토큰 근거 대조.
    `SentenceCheck`(문장별 결과) + `RuleVerificationResult`(`suspicious_sentences`/
    `has_suspicious_sentences`/`passed_verifications` 접근자).
  - **병합 계약**: `RuleVerificationResult.passed_verifications()`는 PASS 문장의 최종
    `Verification`(status=PASS)을 준다. `suspicious_sentences`는 2단계 평가자(Agent)가
    받아 `SUPPORTED`/`NOT_SUPPORTED`를 판정하고, 두 결과를 병합해 RagState.verification을
    만든다(병합·`NOT_SUPPORTED` 비율 차단은 feature11 통합 지점).
  - **수정하지 않을 파일**: `app/schemas/*`(Verification 스키마 기존 활용), `app/llm/*`,
    `app/query/generator.py`(Agent), 다른 팀원 담당 영역
  - **테스트**: 문장 분리, 인용 추출, 검증 토큰 근거 대조, 근거 있는 문장 PASS / 미검증
    토큰·미인용 claim 문장 suspicious, 필러 문장(검증 토큰 없음) PASS, 빈 답변,
    `passed_verifications`/`suspicious_sentences` 접근자
  - **완료 기준**: 단위 테스트 전체 통과 / `verify` 통과 / `working-log.md` 갱신
- **Agent 담당자 몫**: 답변 생성기(`app/query/generator.py` [Agent]), 답변 검증 **2단계
  LLM 평가자**(`SUPPORTED`/`NOT_SUPPORTED`, `app/query/verifier.py`에 2단계 섹션 추가).

작업 항목:

- [x] (본 담당자) 답변 검증 1단계 규칙 매칭 [Pipeline]
- [ ] (Agent 담당자) 답변 생성기 [Agent] + 검증 2단계 LLM 평가자 [Agent]

### feature11: 응답 포맷터 + Query 그래프 + API — ⚠ 일부 통합 지점

- **본 담당자 몫(Pipeline)**: 응답 포맷터 — `app/query/formatter.py`.
  - **작업 목표**: 생성·검증을 거친 답변을 `QueryResponse`(UI JSON)로 변환하고,
    api-spec.md "표준 분기 응답" 규칙을 적용한다 — Cross-Encoder 최고 점수가 낮으면
    저신뢰 분기(`feedback_enabled=false`), NOT_SUPPORTED 비율 > 50%면 답변 차단·대체
    (rag-pipeline-design.md §6 4.8, api-spec.md).
  - **수정 대상**: `app/query/formatter.py`(신규), `app/query/__init__.py`,
    `tests/query/test_formatter.py`(신규)
  - **구현**: `format_response(answer, sources, verification, intent, used_llm,
    latency_ms) -> QueryResponse` 순수 함수 + 헬퍼(`_is_low_confidence`·
    `_not_supported_ratio`) + 상수(`LOW_CONFIDENCE_SCORE`=20·`VERIFICATION_BLOCK_RATIO`=
    0.5·`BLOCKED_ANSWER_MESSAGE`). feature9-A처럼 순수 로직 우선 — RagState→인자 추출
    노드 래퍼는 그래프 조립 단계에서.
  - **scoping**: `Source` 객체 생성(Chunk+Cross-Encoder 점수 → Source)은 feature9-B
    책임(점수를 가진 단계). 포맷터는 완성된 `Source`를 입력으로 받는다(`RagState.sources`가
    이미 `list[Source]`). 검색 0건 early-exit는 그래프(아래 통합 지점) 몫 — 포맷터는
    "생성된 답변을 응답으로 변환"만 한다.
  - **수정하지 않을 파일**: `app/schemas/*`(QueryResponse·Source 기존 활용), `app/llm/*`,
    `app/pipeline/*`·`app/api/*`(통합 지점 — 아래), 다른 팀원 담당 영역
  - **테스트**: 정상 응답(feedback_enabled=True), 저신뢰 분기(최고 Source 점수 < 20),
    검증 차단(NOT_SUPPORTED 비율 > 50% → 답변 대체), 경계값, 차단 우선순위,
    sources/verification 통과
  - **완료 기준**: 단위 테스트 전체 통과 / `verify` 통과 / `working-log.md` 갱신
- **통합 지점**: Query 그래프 조립(`app/pipeline/query_graph.py`)·FastAPI 라우트(`app/api/*`)는
  Agent 노드 + Pipeline 노드를 배선한다. Agent 노드는 stub/fake로 두고 구현·end-to-end
  테스트한 뒤, Agent 코드 전달 시 교체. 그래프 조립은 feature5·9-B 이후가 적절.
- 문서 수정: API 변경 시 `docs/api-spec.md`

작업 항목:

- [x] (본 담당자) 응답 포맷터 [Pipeline]
- [x] Query LangGraph 조립 + Agent stub 3종 — Phase 1 완료 (2026-05-18,
  `app/pipeline/{stubs,nodes,query_graph}.py`. Agent 코드 전달 시 `QueryGraphDeps`
  3개 필드만 교체)
- [x] FastAPI 라우트(SSE) — Phase 2 완료 (2026-05-18,
  `app/api/{main,routes,errors,deps}.py`. PoC: `:memory:` Qdrant + Fake +
  samples 자동 인덱싱. token 1회 송신, Agent 통합 시 다중 송신으로 확장)

---

## 진행 규칙 (요약)

1. feature 단위로만 작업한다. 다음 feature는 새 세션 또는 `/clear` 후 시작한다.
2. 테스트 케이스 정리 → 실패 테스트 작성 → 최소 구현 → 테스트 통과 순서를 지킨다.
3. 완료 후 `./scripts/verify.sh`(format → lint → test)를 실행한다.
4. `git diff`로 변경 범위를 확인하고 `docs/ai/working-log.md`를 업데이트한 뒤 커밋한다.
5. Agent 컴포넌트는 LLM 응답을 mock/fake로 대체해 테스트한다. 외부 의존성(Qdrant/Mongo/MySQL)도 동일.
