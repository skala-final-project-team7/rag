# Working Log

RAG Pipeline 작업 이력을 시간순으로 기록한다.
세션 간 인수인계와 팀원 간 작업 공유를 위한 로그이며, 실패한 테스트·해결한 문제·남은 TODO도 함께 남긴다.

기록 형식:

```md
## YYYY-MM-DD — <작업 제목>

- 브랜치: feat/#<이슈번호>/<기능-이름>
- 변경 사항: <무엇을 했는지>
- 수정 파일: <파일 목록>
- 실행 명령: ./scripts/format.sh / lint.sh / test.sh
- 테스트 결과: <통과 / 실패 + 원인>
- 평가 결과: <Precision@k, 응답 지연, 출처 정확도 중 해당 항목>
- 남은 TODO: <다음 세션에서 이어갈 내용>
```

---

## 2026-05-15 — RAG 저장소 골격 구성

- 브랜치: `feat/#1/rag-pipeline-skeleton`
- 변경 사항: 단독 RAG 저장소 초기 골격 구성
  - `app/`(패키지), `tests/`(스모크 테스트), `pyproject.toml`, `.gitignore` 추가
  - `app/CLAUDE.md` (RAG Pipeline 전용 규칙) 추가
  - 누락 문서 추가: `docs/ai/current-plan.md`, `docs/ai/working-log.md`, `docs/db-schema.md`, `docs/api-spec.md`, `docs/adr/`
  - `scripts/{format,lint,test}.sh`가 루트 `pyproject.toml` 기반 단독 저장소 구조를 인식하도록 보정
  - git remote URL을 SSH 형식으로 정정
- 수정 파일: 위 신규 파일 + `scripts/format.sh`, `scripts/lint.sh`, `scripts/test.sh`
- 실행 명령: `./scripts/verify.sh`
- 테스트 결과: 스모크 테스트 통과 (실제 파이프라인 테스트는 feature 단위로 추가 예정)
- 남은 TODO: `docs/ai/current-plan.md`에 RAG Pipeline 기본 골격 Plan 작성 → feature 단위 구현 착수

## 2026-05-15 — 설계 문서 기반 골격 구체화

- 브랜치: `feat/#1/rag-pipeline-skeleton`
- 변경 사항: RAG 파이프라인 설계서 v0.2.2 / Adaptive Chunking 전략 설계서 v0.1 / 샘플 데이터
  (confluence 57p·6스페이스, datadog 35p) 정독 후 골격을 실제 설계에 맞게 구체화
  - `docs/rag-pipeline-design.md`, `docs/chunking-strategy.md` 신설 (설계서 구현 참조 문서)
  - `docs/db-schema.md` 재작성 — Qdrant Multi-Pool(title/content/label) + MongoDB(ingestion_jobs,
    embedding_cache, rag_mock.*) + MySQL(space_doc_type_cache)
  - `docs/api-spec.md` 재작성 — `POST /api/v1/rag/query` SSE 응답 스키마(설계서 §4.8 정합)
  - `docs/architecture.md` §9 갱신 — Ingestion/Query 2갈래 + 컴포넌트 분류 + 설계 문서 링크
  - `app/CLAUDE.md` 구체화 — Agent/Pipeline/Storage 분류, @enforce_acl, 결정론·멱등성, LLM 라우팅 규칙
  - `pyproject.toml` — 실제 의존성 반영 (qdrant-client, pymongo, langgraph, sentence-transformers,
    pymupdf 등 / embedding·ingestion·dev extras 분리)
  - `app/` 패키지 골격 스캐폴딩 — schemas / adapters / llm / ingestion(+chunker) / query / pipeline / api
    (각 `__init__.py` docstring에 단계·분류·계획 모듈 명시, 구현은 미포함)
  - `docs/ai/current-plan.md` — feature 12종 분해 제안 초안 (Milestone A/B/C) + 선행 의존성 정리
- 수정 파일: 위 신규/수정 파일 + `tests/test_smoke.py`(서브패키지 import 검증으로 확장)
- 실행 명령: `ruff format --check` / `ruff check` / `pytest`
- 테스트 결과: 통과 (스모크 — 9개 패키지 import 검증)
- 남은 TODO: 선행 의존성 해소(기획서·mock ACL·첨부 원본 확보) → Plan Mode로 feature1 상세 Plan 확정 → 구현 착수

## 2026-05-15 — 기획서·Atlassian API·첨부 원본 반영 (정합성 보정)

- 브랜치: `feat/#1/rag-pipeline-skeleton`
- 변경 사항: 기획서 v2.1.6(Source of Truth), Atlassian API 명세서, 첨부 원본 4건 정독 후 골격 정합성 보정
  - `samples/` 신설 — confluence(57p)·datadog(35p) JSON + 첨부 원본 4건(`samples/attachments/`) + README.
    PoC 목 데이터이자 테스트 픽스처
  - `docs/atlassian-api.md` 신설 — 데이터 수집은 ML 파이프라인(본 저장소)이 `atlassian-python-api`로
    직접 호출. 인증·토큰은 Authorization Server 책임. 페이지 객체 → PageObject 매핑 정리
  - Document Source Adapter 재정의 — 백엔드 미구축 반영: `JsonFixtureSourceAdapter` +
    `AtlassianSourceAdapter` (기존 `MongoSourceAdapter` 가정 폐기). `docs/rag-pipeline-design.md` §4,
    `app/adapters/__init__.py`, `docs/ai/current-plan.md` feature2 갱신
  - **ACL 불일치 발견·명시** — 설계서는 청크별 `allowed_groups`/`allowed_users`를 정의하나
    Atlassian API 명세는 Space 단위 권한(`DATA-03`)만 제공, 샘플 데이터에 ACL 필드 없음.
    `docs/db-schema.md` §1.4·`docs/rag-pipeline-design.md` §7·`docs/atlassian-api.md`·`app/CLAUDE.md`에
    미해결 사항으로 명시, `current-plan.md` 선행 의존성 최우선 항목으로 등재
  - `docs/rag-pipeline-design.md` §10 KPI를 기획서 §10 기준 최소/목표로 갱신
  - `pyproject.toml` — `atlassian-python-api` 추가 (ingestion extras)
- 수정 파일: `samples/*`, `docs/atlassian-api.md`, `docs/rag-pipeline-design.md`, `docs/db-schema.md`,
  `app/adapters/__init__.py`, `app/CLAUDE.md`, `pyproject.toml`, `docs/ai/current-plan.md`
- 실행 명령: `ruff format --check` / `ruff check` / `pytest`
- 테스트 결과: 통과 (골격 스모크)
- 남은 TODO: **ACL 필드 모델 팀 결정** + `access_token` 전달 방식 확정 → Plan Mode로 feature1 상세 Plan 확정 → 구현 착수

## 2026-05-15 — feature1: schemas + config 구현

- 브랜치: `feat/#1/rag-pipeline-skeleton`
- 결정 사항:
  - ACL 모델 = `allowed_groups`/`allowed_users` 청크 Payload 채택 (기획서 §6.6·설계서 원안)
  - 미정(TBD) 기록: PoC 샘플 데이터의 ACL 출처, `access_token`/`cloudid` 전달 경로
    → `current-plan.md` 선행 의존성에 기록, RAG 코어 코드는 무관하게 선행
- 변경 사항: feature1 상세 Plan 확정 후 테스트 우선(TDD)으로 구현
  - `app/schemas/enums.py` — 열거형 9종 (DocType·AttachmentType·SourceType·ExtractedFormat·
    Intent·VerificationStatus·IngestionStage·IngestionStatus·LlmModel), `enum.StrEnum` 기반
  - `app/schemas/page_object.py` — `PageObject`·`Attachment` + `is_acl_missing` 식별 (설계서 §7.1)
  - `app/schemas/chunk.py` — `Chunk`·`ChunkMetadata`(19종) + `make_chunk_id` 결정론 헬퍼
  - `app/schemas/rag_state.py` — `RagState`·`IngestionState`·`HistoryTurn` (LangGraph 노드 상태)
  - `app/schemas/response.py` — `QueryResponse`·`Source`·`Verification` (api-spec.md 정합)
  - `app/schemas/__init__.py` — 주요 모델 re-export
  - `app/config.py` — pydantic-settings `Settings` (무인자 인스턴스화 가능, 시크릿은 SecretStr+env)
- 수정 파일: 위 신규 파일 + `tests/schemas/*`(4) + `tests/test_config.py` + `docs/ai/current-plan.md`
- 실행 명령: `ruff format --check` / `ruff check` / `pytest`
- 테스트 결과: **35 passed** (스키마·config·스모크). ruff format·check 통과
- 비고: 샌드박스 Python 3.10 한계로 `enum.StrEnum`(3.11+) 직접 실행 불가 → 검증 전용 shim으로
  pytest 통과 확인(코드는 3.11 기준 그대로 유지). mypy는 샌드박스 환경 버그로 미검증
- 남은 TODO: feature2(Document Source Adapter) — 단, `access_token` 전달 경로 확정 선행 권장

## 2026-05-15 — feature2 (일부): 데이터 계층 — Document Source Adapter

- 브랜치: `feat/#1/rag-pipeline-skeleton`
- 목적: 테스트 데이터로 RAG 파이프라인 데이터 계층이 제대로 구축됐는지 검증
- 변경 사항: 테스트 우선(TDD)으로 어댑터 인터페이스 + JSON 픽스처 어댑터 구현
  - `app/adapters/base.py` — `DocumentSourceAdapter` 추상 인터페이스 + `ActiveIds`·`ChangeEvent`
  - `app/adapters/json_fixture.py` — `JsonFixtureSourceAdapter`: `samples/*.json`(Atlassian 응답
    포맷) → 표준 `PageObject` 매핑. `parse_atlassian_datetime`(+0900 오프셋 정규화),
    `infer_extracted_format`(mime → raw_text/sheet_serialized) 헬퍼 포함
  - PoC ACL: 샘플 데이터에 ACL 필드가 없어 `_synthesize_acl`로 `space_key` 기반 합성
    (`allowed_groups=["space:{space_key}"]`). 실제 ACL 연동 시 이 메서드만 교체
  - 첨부: 샘플 JSON은 첨부 메타만 보유 → 누락 필드 합성, `extracted_text=""`(텍스트 추출은
    feature4 책임), `download_url`은 `samples/attachments/` 내 실제 파일 경로
  - `app/adapters/__init__.py` re-export 갱신
- 수정 파일: `app/adapters/{base,json_fixture,__init__}.py` + `tests/adapters/*`(3) +
  `docs/ai/current-plan.md`
- 실행 명령: `ruff format --check` / `ruff check` / `pytest`
- 검증 결과: **53 passed** (feature1 35 + feature2 18). ruff format·check 통과
  - **데이터 계층 검증** — `samples/` 전체 92페이지(confluence 57 + datadog 35)가 PageObject로
    오류 0건 로드. 스페이스 분포 정상(CLOUD 16/CCC 21/DEVOPS 7/SEC 3/ONBOARD 4/PROJ 6/DATADOG_KR 35),
    ACL 누락 0건(PoC 합성), 첨부 4건 매핑 확인, `list_active_ids` pages 92/attachments 4
- 비고: feature1과 동일하게 샌드박스 Python 3.10 한계로 검증은 `StrEnum`/`datetime.UTC` 백포트
  shim 사용. 코드는 3.11 기준 그대로. mypy는 샌드박스 환경 버그로 미검증
- 남은 TODO: `AtlassianSourceAdapter` — `access_token`/`cloudid` 전달 경로 확정 후 착수.
  또는 feature3(Adaptive Chunker 본문)로 진행 — 외부 의존성 없음

## 2026-05-15 — 데이터 계층 로컬 데모 + feature3 Plan 확정

- 브랜치: `feat/#1/rag-pipeline-skeleton`
- `examples/demo_data_layer.py` — 팀원 시연용 데모. `python -m examples.demo_data_layer`로
  samples 92페이지를 PageObject로 로드해 콘솔 요약 출력. 최소 의존성(pydantic만)으로 동작
- `docs/ai/current-plan.md` — feature3 상세 Plan 확정, 규모상 A(기반)/B(6유형 분할기) 마일스톤 분할

## 2026-05-15 — feature3-A: 청킹 기반 (tokenizer / storage_format / base)

- 브랜치: `feat/#1/rag-pipeline-skeleton`
- 변경 사항: 테스트 우선(TDD)으로 청킹 기반 3개 모듈 구현
  - `app/ingestion/chunker/tokenizer.py` — `count_tokens` PoC 휴리스틱(CJK 글자 단위 + 공백
    토큰). 실제 SentencePiece 토크나이저는 품질 튜닝 시 교체
  - `app/ingestion/chunker/storage_format.py` — `clean_storage_format`: Confluence Storage
    Format(HTML) → 정규화 텍스트. code 매크로/인라인 code는 플레이스홀더로 보호 후 ``` 펜스/백틱
    복원(코드 내 `<env>` 등이 태그로 파싱되는 것 방지), 표→markdown, ac:task-list→체크박스,
    헤딩→`##/###/####`, 스마트 따옴표 정규화, 파싱 실패 시 plain text 폴백
  - `app/ingestion/chunker/base.py` — `ChunkDraft` + `split_oversized`(800토큰 초과 시
    100토큰 오버랩 슬라이딩 윈도우) + `merge_undersized`(200토큰 미만 직전 청크 병합) +
    `apply_size_rules`(2차 재분할→하한선 병합, 원자성 유형 제외)
  - `app/ingestion/chunker/__init__.py` — re-export 갱신
- 수정 파일: `app/ingestion/chunker/{tokenizer,storage_format,base,__init__}.py` +
  `tests/ingestion/chunker/*`(3) + `docs/ai/current-plan.md`
- 실행 명령: `ruff format --check` / `ruff check` / `pytest`
- 검증 결과: **77 passed** (feature1·2 53 + feature3-A 24). ruff format·check 통과
  - **실제 데이터 검증** — `samples/` 92개 본문을 `clean_storage_format`으로 전처리: 오류 0건,
    정제 텍스트 총 240K자 / 추정 105K토큰. 가장 긴 본문(19,203자 → 5,014토큰)이
    `split_oversized`로 8개 윈도우 분할 확인
- 비고: `storage_format`은 `beautifulsoup4` 필요(`ingestion` extras). 전체 테스트 실행은
  `pip install -e ".[dev]"` + `beautifulsoup4`(또는 `[ingestion]`) 필요.
  datadog 본문의 Hugo 숏코드(`{{< >}}`) 잔재는 텍스트로 통과 — 무해, 추후 정리 검토
- 남은 TODO: feature3-B — 본문 6유형 1차 분할기 + 메타데이터 부착 + samples 통합 테스트

## 2026-05-15 — feature3-B: 본문 6유형 분할기 + chunk_page (feature3 완료)

- 브랜치: `feat/#1/rag-pipeline-skeleton`
- 변경 사항: 테스트 우선(TDD)으로 본문 청킹 완성
  - `app/ingestion/chunker/body.py` — 본문 6유형 1차 분할기(operation/incident/troubleshoot/
    adr/faq/meeting), `split_body`(1차 분할), `chunk_page`(1차 분할 → 크기 규칙 → 메타데이터),
    `infer_doc_type`(라벨 기반 doc_type 추정 — PoC 휴리스틱, 실제는 문서 분석기 Agent=feature6)
  - `app/ingestion/chunker/metadata.py` — `build_metadata`: 청크 메타데이터 19종 부착 +
    무결성 규칙(section_header 빈 문자열 금지, chunk_id 결정론, source_type=page)
  - `app/ingestion/chunker/__init__.py` — re-export 갱신
- 원자성: incident/troubleshoot/adr/faq/meeting 블록은 is_atomic=True로 2차 분할·하한선 병합 제외
- 수정 파일: `app/ingestion/chunker/{body,metadata,__init__}.py` + `tests/ingestion/chunker/`
  `{test_body,test_metadata,test_chunk_page}.py` + `docs/ai/current-plan.md`
- 실행 명령: `ruff format --check` / `ruff check` / `pytest`
- 검증 결과: **95 passed** (feature1·2·3-A 77 + feature3-B 18). ruff 통과
  - **실제 데이터 검증** — `samples/` 92페이지 → `chunk_page` → **289개 청크, 오류 0건**.
    페이지당 평균 3.1개(1~12), 청크 토큰 평균 379(4~964), 200~800 구간 70%.
    doc_type 추정 분포: operation 73 / incident 10 / troubleshoot 4 / adr 3 / faq 1 / meeting 1
  - 메모: 하한선 병합이 직전 큰 청크에 작은 청크를 붙이며 일부(최대 964) 800 초과 — 설계상
    하한선 처리는 2차 재분할 이후라 허용 범위. 품질 튜닝(PoC 6주차) 시 조정 대상
- 남은 TODO: feature4(첨부 3유형 청킹 — `samples/attachments/` 픽스처 활용) 또는
  feature5(Dual Embedding + Multi-Pool Vector Store)
