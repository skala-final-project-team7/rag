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
- **참고 문서**: 루트 `CLAUDE.md`, `app/CLAUDE.md`, `docs/rag-pipeline-design.md`, `docs/chunking-strategy.md`, `docs/db-schema.md`, `docs/api-spec.md`, `docs/conventions.md`

## 선행 확인 / 의존성 (착수 전 해소 필요)

- [ ] **기획서 `PLAN-CONF-RAG-2026-002 v2.1.6`** 확보 — 설계서의 Source of Truth. 미확보 상태로 진행 시 정합성 리스크
- [ ] **mock 데이터 ACL 필드** — `confluence_sample_data.json`에 `allowed_groups`/`allowed_users`가 없음. 백엔드 어댑터가 PageObject에 부착하는 책임이나, PoC mock에 ACL이 채워지는 시점·방식을 백엔드(권서현)와 확정 필요
- [ ] **첨부 파일 원본** — 샘플 데이터가 참조하는 첨부 4건(docx 2 / xlsx 2)의 실제 파일 또는 `extracted_text`가 채워진 mock 미확보. 첨부 청킹(feature5) 착수 전 필요
- [ ] **PageObject 계약 동결** — 백엔드 설계서와 `attachments[]` 등 스펙 동결 (`docs/rag-pipeline-design.md` §7.1)

---

## Milestone A — 공통 기반

### feature1: schemas + config

- 요구사항: 파이프라인 전 단계가 공유하는 데이터 계약과 설정 정의
- 수정 대상: `app/schemas/*`(page_object, chunk, rag_state, response, enums), `app/config.py`
- 테스트: Pydantic 모델 검증(필수 필드, ACL 누락 거부), 설정 로딩
- 문서 수정: 없음 (스키마는 `docs/db-schema.md`·`docs/api-spec.md`와 정합 확인만)
- 위험: PageObject 계약 미동결 시 재작업 — 선행 확인 항목 참조

작업 항목:

- [ ] PageObject / Attachment / Chunk / ChunkMetadata / 응답 스키마 / enums 정의
- [ ] `app/config.py` — 환경 변수 설정 (source.type, Qdrant/Mongo/MySQL/OpenAI)

### feature2: Document Source Adapter

- 요구사항: 데이터 공급원 추상화. PoC용 MongoDB mock 어댑터
- 수정 대상: `app/adapters/base.py`, `app/adapters/mongo.py`
- 테스트: fake MongoDB로 `fetch_pages` / `list_active_ids` / `watch_changes` 계약 검증
- 위험: ACL 부착 책임 경계 (선행 확인 항목)

작업 항목:

- [ ] `DocumentSourceAdapter` 인터페이스
- [ ] `MongoSourceAdapter` — `rag_mock.pages` / `rag_mock.attachments` 읽기

## Milestone B — Ingestion 파이프라인

### feature3: Adaptive Chunker (본문 6유형)

- 수정 대상: `app/ingestion/chunker/{base,storage_format,body,metadata,tokenizer}.py`
- 테스트: 유형별 1차 분할 / 2차 재분할(800·100) / 하한선(200) / 원자성 / `chunk_id` 멱등성
- 문서 수정: 청킹 규칙 변경 시 `docs/chunking-strategy.md`

작업 항목:

- [ ] Storage Format 공통 전처리 + 본문 6유형 분할 + 메타데이터 19종 부착

### feature4: Adaptive Chunker (첨부 3유형)

- 수정 대상: `app/ingestion/chunker/attachment.py`
- 테스트: PDF/Word 섹션 분할, Excel/CSV 자연어 직렬화(컬럼명 동봉), 헤더 누락 fallback
- 위험: 첨부 원본 미확보 (선행 확인 항목)

작업 항목:

- [ ] PDF / Word / Excel·CSV 청킹 + Excel 직렬화

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

### feature7: ACL Pre-filtering + @enforce_acl

- 수정 대상: `app/query/acl.py`
- 테스트: JWT → 필터 생성, `@enforce_acl`가 ACL 없는 호출을 `ACLViolationError`로 거부
- 위험: 보안 핵심 — 우회 불가 구조 검증 필수

작업 항목:

- [ ] ACL 필터 생성 + `@enforce_acl` 데코레이터

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
