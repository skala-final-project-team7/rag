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

## 2026-05-15 — feature4-A: docx / xlsx 첨부 분할기 + base.py 하한선 병합 버그 수정

- 브랜치: `feat/#1/rag-pipeline-skeleton`
- 범위 결정: feature4를 픽스처 가용성 기준으로 4-A(docx/xlsx — 픽스처 보유)와
  4-B(PDF/CSV — 픽스처·`pymupdf` 미확보, 보류)로 분할. 이번 세션은 4-A만 진행
  (`current-plan.md` feature4 갱신)
- 변경 사항: 테스트 우선(TDD)으로 첨부 docx/xlsx 청킹 구현
  - `app/ingestion/chunker/attachment.py` — 첨부 청킹 (chunking-strategy.md §5)
    - `infer_attachment_type` — mime/확장자 기반 PoC 추정기 (실제 분류는 첨부 분석기
      [Pipeline]=feature6 책임)
    - docx: python-docx로 본문 블록(문단·표)을 문서 순서로 순회(`_iter_block_items`) →
      Heading 1/2/3 경계 1차 분할(없으면 단일 draft fallback, section_header=파일명),
      표는 markdown 변환, 첫 헤딩 이전 preamble은 첫 섹션 도입부에 부착
    - xlsx: openpyxl로 시트 단위 → 시트 내 N행 그룹(기본 50, 직렬화 800토큰 초과 시
      25→10행 축소). 각 행 `[<시트명>] <컬럼>: <값> | ...` 직렬화, 빈 셀 생략,
      첫 행이 수치면 헤더 누락으로 보고 `col_1..` 부여(ATTACH_NO_HEADER)
    - `build_attachment_metadata` — 첨부 메타데이터 19종(`source_type=attachment`,
      `attachment_*`/`extracted_format` 채움, `doc_type`=attachment_type 값,
      `chunk_id`=make_chunk_id(page_id, idx, attachment_id), ACL·메타는 부모 페이지 상속)
    - `chunk_attachment` 엔트리 — 1차 분할 → (docx만)`apply_size_rules` → 메타데이터
  - `app/ingestion/chunker/__init__.py` — re-export·docstring 갱신
- 구현 해석(설계서 충돌 없음, 기록 목적):
  - docx 섹션은 원자성 없음 → `apply_size_rules`(2차 재분할·하한선 병합) 적용.
    xlsx는 행 그룹 분할이 크기 처리를 겸하므로 `apply_size_rules` 미적용
  - `section_path`는 첨부의 경우 `ancestors > 첨부파일명 > section_header`로 구성(맥락 동봉)
  - xlsx `클러스터 메트릭` 시트는 단일 행이 ~163토큰이라 10행 그룹도 800 초과 →
    더 줄일 단계가 없어 수용(설계서 §5 "25→10행 축소" 한계 — 허용 범위)
- **버그 수정 — `app/ingestion/chunker/base.py` `merge_undersized`** (Option A, 사용자 승인):
  - 증상: 하한선 병합이 직전 청크를 '봉인'하지 않아 200토큰 미만 청크가 무한 누적.
    docx 첨부(Heading 섹션 다수가 200토큰 미만)에서 EKS 매뉴얼 44섹션이 한 청크(4091토큰)로
    붕괴, 온보딩 14섹션이 1135토큰 한 청크로 붕괴
  - 원인: `can_merge` 조건이 `result[-1]`의 원자성만 검사하고 누적 크기를 검사하지 않음
  - 수정: `can_merge`에 `count_tokens(result[-1].text) < min_tokens` 조건 추가 — 하한선을
    채운 직전 청크는 봉인. 설계서 §3 "직전/직후 1회 병합" 의도와 정합
  - 재현 테스트 선작성: `test_merge_undersized_seals_chunk_at_min_tokens`(회귀 보호) +
    버그 동작을 인코딩하던 기존 `test_merge_undersized_merges_small_adjacent` 정정
- 수정 파일: `app/ingestion/chunker/{attachment,base,__init__}.py` +
  `tests/ingestion/chunker/{test_attachment,test_base}.py` +
  `docs/ai/{current-plan,working-log}.md`
- 실행 명령: `./scripts/verify.sh` (ruff format → ruff check → pytest)
- 검증 결과: **116 passed** (기존 95 + feature4-A 20 + base.py 회귀 1). ruff format·check 통과
  - **실제 데이터 검증** — `samples/attachments/` 4건 → `chunk_attachment` → **35 청크, 오류 0건**:
    EKS 매뉴얼 15청크(177~373토큰), 모니터링 메트릭 6청크(199~1556), EKS 노드 통계
    10청크(300~768, 전부 200~800), 온보딩 4청크(236~315)
  - **feature3 본문 회귀(개선)** — 버그 수정으로 본문 청킹도 개선: 92페이지 289→**379청크**,
    최대 토큰 964→**800**(이전 메모의 "800 초과" 문제 해소). feature3 테스트는 정확 개수를
    단언하지 않아 전부 통과
- 비고 — Python 3.10 검증 shim:
  - 기존 세션은 `enum.StrEnum`/`datetime.UTC` 백포트를 임시 shim으로 처리. 이번에 저장소 내
    `conftest.py`로 시도했으나 ruff(target-version=py311)와 충돌: `if sys.version_info`
    블록은 UP036, `class(str, Enum)`은 UP042로 거부되고, `ruff check --fix`가
    `datetime.timezone.utc`를 `datetime.UTC`로 재작성해 shim 자체를 깨뜨림
  - 해결: shim을 **저장소 밖** `~/.local/lib/python3.10/site-packages/usercustomize.py`로
    이동(인터프리터 기동 시 자동 로드, ruff 검사 대상 아님). 저장소에는 shim 파일이 없으며
    프로젝트 코드는 3.11 기준 그대로. Python 3.10 샌드박스에서 재검증 시 동일 파일 재생성 필요
- 남은 TODO: feature4-B(PDF/CSV 첨부 분할기 — PDF 픽스처·`pymupdf`/`pdfplumber` 확보 후
  별도 세션) 또는 feature5(Dual Embedding + Multi-Pool Vector Store)

## 2026-05-15 — 담당 범위 재확인 → Query 파이프라인 전환 (Milestone C 착수)

- 결정 사항: RAG 담당자의 기획서 범위는 **Query 파이프라인**이다. current-plan.md의 feature
  분해는 Ingestion(Milestone B)을 앞에 두지만, current-plan.md 자체가 "제안 초안 — 순서·범위는
  팀 리뷰 후 조정"이라 명시하고 rag-pipeline-design.md도 "기획서가 Source of Truth"라 둔다.
  → Ingestion은 feature4-A까지 완료한 상태에서 Query(Milestone C)로 전환
- 진행 메모:
  - 시작하던 feature4-B-1(CSV 첨부 분할기)은 테스트·문서 편집까지만 진행한 뒤 미커밋 상태로
    되돌렸다(`git restore`). Ingestion 잔여(feature4-B-2 PDF, feature5·6)는 별도 담당/세션 몫
  - Ingestion 작업물(feature3·4-A)은 `app/ingestion/` 하위 트리에 격리돼 있어 인계 용이.
    feature1·2(공통 기반: schemas/config·Document Source Adapter)는 양 파이프라인 공용
  - current-plan.md Milestone C 상단에 전환 메모 추가, feature7 상세 Plan 확정

## 2026-05-15 — feature7: ACL Pre-filtering + @enforce_acl (Query 파이프라인 시작)

- 브랜치: `feat/#1/rag-pipeline-skeleton`
- 변경 사항: 테스트 우선(TDD)으로 ACL Pre-filtering 구현 (rag-pipeline-design.md §6 4.2,
  app/CLAUDE.md §3, db-schema.md §1.4)
  - `app/query/acl.py` (신규)
    - `Principal` — JWT에서 추출한 검색 주체(user_id/groups) Pydantic 모델
    - `extract_principal(jwt)` — JWT payload를 stdlib base64+json으로 디코드해 `sub`·`groups`
      추출. **서명은 검증하지 않는다** — 인증·서명 검증·토큰 발급은 BFF 책임(api-spec.md),
      config에도 JWT 키가 없음. 형식 오류·payload 디코드 실패·`sub` 누락 시
      `PrincipalExtractionError`(API의 `UNAUTHORIZED`에 대응)
    - `build_acl_filter(user_id, groups)` — `allowed_groups` any-match OR `allowed_users`
      any-match 의 Qdrant `should` 필터 dict 생성. `RagState.acl_filter`(`dict[str, Any]`)
      계약과 정합. ACL 모델 변경 시 이 함수만 교체하도록 격리(app/CLAUDE.md §3)
    - `ACLViolationError` + `@enforce_acl` — 데코레이션 시점에 대상 함수의 `acl_filter`
      파라미터 존재를 강제(없으면 `TypeError`), 호출 시점에 필터 누락·무효를
      `ACLViolationError`로 거부. ACL 검사가 호출 전이라 sync/async 함수 모두 적용 가능
  - `app/query/__init__.py` — re-export 갱신 (adapters/·chunker/와 동일 패턴)
- 결정 사항: JWT 서명 미검증(클레임 추출만) — 사용자 선택. BFF가 서명 검증을 담당하므로
  RAG 파이프라인은 클레임만 추출하며, `pyjwt` 등 새 의존성을 추가하지 않는다
- 수정 파일: `app/query/{acl,__init__}.py` + `tests/query/{__init__,test_acl}.py` +
  `docs/ai/current-plan.md`
- 실행 명령: `./scripts/verify.sh` (ruff format → ruff check → pytest)
- 검증 결과: **130 passed** (기존 116 + feature7 14). ruff format·check 통과
  - 테스트: `extract_principal`(정상/groups 기본값/형식 오류/payload 디코드 실패/sub 누락),
    `build_acl_filter`(should OR 구조/빈 groups/원본 비-aliasing),
    `@enforce_acl`(유효 필터 허용/누락·무효 거부/위치 인자/파라미터 없는 함수 TypeError),
    JWT→Principal→필터→@enforce_acl 통합
- 남은 TODO: feature8(질의 라우터 + 멀티턴 히스토리 — Agent, mock LLM 필수) →
  feature9(Hybrid Search + 재순위화) → feature10(생성 + 검증) → feature11(포맷터 + 그래프 + API)

## 2026-05-15 — Agent 컴포넌트 담당 분리 반영 + feature9-A 착수

- 결정 사항: **Agent 컴포넌트는 별도 담당자 몫**이다 — Agent 코드·파일은 추후 전달받아 병합한다.
  본 담당자(RAG)는 각 feature의 [Pipeline]/[Storage] 부분만 진행한다.
  - Agent 담당자 전달분: 질의 라우터·멀티턴 히스토리(feature8 전체), 답변 생성기·검증 2단계
    LLM 평가자(feature10 일부), 문서 분석기(feature6 일부), `app/llm/`(Agent 인프라)
  - 병합 seam: (1) `RagState`(feature1 동결 상태 계약) — Agent·Pipeline 노드가 필드를 읽고 쓴다,
    (2) LangGraph 그래프(feature11) — 노드 배선, (3) 합의된 모듈 경로·노드 시그니처
    `(state: RagState) -> RagState`. Agent·Pipeline 노드는 서로 직접 호출하지 않는다.
    그래프 조립 시 Agent 노드는 stub/fake로 대체했다가 실제 코드 전달 시 교체
  - feature8은 전부 Agent(라우터·히스토리)라 본 담당자는 건너뛴다 → 다음 진행은 feature9부터
  - `current-plan.md` Milestone C 메모·feature8/9/10/11/6 담당 분리 주석 갱신
- 진행 순서(본 담당자): feature7(완료) → feature9-A → feature10[Pipeline] → feature11[Pipeline:
  포맷터] → feature5(다리) → feature9-B → feature11(그래프·API 조립) → feature6[Pipeline] → feature4-B

## 2026-05-15 — feature9-A: 검색·재순위화 핵심 로직 (순수 함수)

- 브랜치: `feat/#1/rag-pipeline-skeleton`
- 변경 사항: 테스트 우선(TDD)으로 Multi-Pool Hybrid Search·Cross-Encoder 재순위화의
  결정론적 핵심 로직 구현 (rag-pipeline-design.md §6 4.5, §8)
  - `app/query/search.py` — `reciprocal_rank_fusion`(Pool 내부 dense+sparse RRF, k=60),
    `merge_pools`(Pool 가중 합산), `select_top_candidates`(Top-20 선정, 동점은 item id
    오름차순 결정론 정렬), `fuse_and_rank`(세 단계 결합 엔트리)
  - `app/query/rerank.py` — `select_reranked`(Cross-Encoder 점수 → Top-5, 5위 < 0.30이면
    Top-3 축소, 최고 < 0.20이면 저신뢰 분기) + `RerankResult` 데이터클래스
  - `app/query/__init__.py` — re-export 갱신
- 범위: 외부 의존성 0인 순수 함수만. 쿼리 임베딩·Qdrant 3-pool 검색·Cross-Encoder 추론·
  RagState 배선은 feature9-B(노드 오케스트레이션, feature5·모델 확보 후) 책임
- 수정 파일: `app/query/{search,rerank,__init__}.py` + `tests/query/{test_search,test_rerank}.py`
  + `docs/ai/current-plan.md`
- 실행 명령: `./scripts/verify.sh` (ruff format → ruff check → pytest)
- 검증 결과: **146 passed** (기존 130 + feature9-A 16). ruff format·check 통과
  - 테스트: RRF 점수·순위 누적, Pool 가중 합산·미지정 가중치 0 처리, Top-N 선정·동점
    결정론 정렬, fuse_and_rank 결합, Top-5 유지/Top-3 축소(5위<0.30)/임계 경계,
    저신뢰 분기(최고<0.20)·빈 입력
- 남은 TODO: feature10[Pipeline](답변 검증 1단계 규칙 매칭) → feature11[Pipeline](응답 포맷터)
  → feature5(Dual Embedding + Multi-Pool Vector Store, 다리) → feature9-B(노드 오케스트레이션)

## 2026-05-15 — feature10-Pipeline: 답변 검증 1단계 규칙 매칭

- 브랜치: `feat/#1/rag-pipeline-skeleton`
- 변경 사항: 테스트 우선(TDD)으로 답변 검증 1단계(규칙 기반)를 구현 (rag-pipeline-design.md
  §6 4.7, conventions.md §5.5)
  - `app/query/verifier.py` — `verify_answer_rules(answer, top_chunks)`: 답변을 문장 단위로
    분해해 각 문장의 검증 토큰(수치·구조적 식별자)이 인용한 청크 텍스트에 나타나는지 대조.
    확인 안 된 토큰이 있으면 의심(suspicious) FLAG → 2단계 LLM 평가자로 넘김, 그 외 PASS
    - `SentenceCheck`(문장별 결과·`is_suspicious`) + `RuleVerificationResult`
      (`suspicious_sentences`/`has_suspicious_sentences`/`passed_verifications` 접근자)
    - 헬퍼: `_split_sentences`(PoC 휴리스틱 — 줄바꿈·종결부호+공백), `_extract_citations`
      (`[#n]` → 1-based 청크 번호), `_gather_cited_text`(범위 밖 인용 스킵),
      `_extract_checkable_tokens`(수치·구조적 식별자 — ASCII 클래스만 써서 한글 조사 분리),
      `_token_grounded`(대소문자 무시 부분 문자열)
  - `app/query/__init__.py` — re-export 갱신
- 결정 사항·구현 해석:
  - 검증 토큰은 수치·구조적 식별자만 — 일반 단어는 패러프레이즈 노이즈가 커 제외.
    Mecab 형태소 분석은 쓰지 않음(PoC 휴리스틱) — 정밀 엔티티 추출은 품질 튜닝 단계 교체
  - 인용 없이 검증 토큰이 있는 문장은 대조 근거가 없으므로 suspicious가 된다(출처 없는 주장)
  - **버그 수정(구현 중 발견)**: `_STRUCTURED_TOKEN` 정규식이 `\w`를 써서 한글 조사가
    식별자에 붙던 문제(`prod-main-eks는`) → ASCII 문자 클래스로 교체. 재현 테스트가
    먼저 실패 → 수정 후 통과
  - 병합 계약: `passed_verifications()`가 PASS 문장의 최종 `Verification`을 주고,
    `suspicious_sentences`는 2단계 평가자(Agent)가 받아 SUPPORTED/NOT_SUPPORTED 판정.
    두 결과 병합·NOT_SUPPORTED 비율 차단은 feature11 통합 지점
- 수정 파일: `app/query/{verifier,__init__}.py` + `tests/query/test_verifier.py` +
  `docs/ai/current-plan.md`
- 실행 명령: `./scripts/verify.sh` (ruff format → ruff check → pytest)
- 검증 결과: **157 passed** (기존 146 + feature10-Pipeline 11). ruff format·check 통과
  - 테스트: 근거 있는 문장 PASS, 환각 수치·미인용 claim·범위 밖 인용 suspicious,
    필러 문장 PASS, 다문장 분리·인덱싱, 다중 인용, 버전번호 비분리, 종결부호+공백 분리,
    빈 답변, passed_verifications/suspicious_sentences 접근자
- 남은 TODO: feature11[Pipeline](응답 포맷터) → feature5(Dual Embedding + Multi-Pool
  Vector Store, 다리) → feature9-B(노드 오케스트레이션) → feature11(그래프·API 조립)

## 2026-05-15 — feature11-Pipeline: 응답 포맷터

- 브랜치: `feat/#1/rag-pipeline-skeleton`
- 변경 사항: 테스트 우선(TDD)으로 응답 포맷터를 구현 (rag-pipeline-design.md §6 4.8, api-spec.md)
  - `app/query/formatter.py` — `format_response(answer, sources, verification, intent,
    used_llm, latency_ms) -> QueryResponse`: 생성·검증을 거친 답변을 QueryResponse로
    변환하고 api-spec.md "표준 분기 응답" 규칙을 적용
    - NOT_SUPPORTED 비율 > 0.5 → 답변 차단, `BLOCKED_ANSWER_MESSAGE`로 대체,
      `feedback_enabled=False` (차단이 저신뢰보다 우선)
    - Cross-Encoder 최고 점수 < 20(0~100 척도) 또는 출처 없음 → 저신뢰 분기,
      `feedback_enabled=False` (답변은 '참고용'으로 유지)
    - 출처·검증 결과는 어느 분기에서도 투명성 위해 그대로 응답에 담음
    - 헬퍼: `_is_low_confidence`, `_not_supported_ratio` / 상수: `LOW_CONFIDENCE_SCORE`(20),
      `VERIFICATION_BLOCK_RATIO`(0.5), `BLOCKED_ANSWER_MESSAGE`
  - `app/query/__init__.py` — re-export 갱신
- scoping 결정(코드·current-plan.md에 명시): feature9-A처럼 순수 변환 함수만 구현.
  `Source` 객체 생성(Chunk + Cross-Encoder 점수 → Source)은 점수를 가진 feature9-B 책임 —
  포맷터는 완성된 `Source`를 입력으로 받는다(`RagState.sources`가 이미 `list[Source]`).
  검색 0건 early-exit·RagState→인자 추출 노드 래퍼는 Query 그래프 조립(feature11 통합) 몫
- 수정 파일: `app/query/{formatter,__init__}.py` + `tests/query/test_formatter.py` +
  `docs/ai/current-plan.md`
- 실행 명령: `./scripts/verify.sh` (ruff format → ruff check → pytest)
- 검증 결과: **166 passed** (기존 157 + feature11-Pipeline 9). ruff format·check 통과
  - 테스트: 정상 응답(feedback_enabled=True), 저신뢰 분기·경계값(점수 20)·출처 없음,
    검증 차단·경계값(정확히 50%)·검증 없음, 차단 우선순위, sources/verification 통과
- 남은 TODO: feature5(Dual Embedding + Multi-Pool Vector Store, 다리) → feature9-B(검색·
  재순위화 노드 오케스트레이션) → feature11 통합(Query 그래프 조립 + FastAPI 라우트,
  Agent 노드 stub → 전달 후 교체). 본 담당자의 Query 순수 로직(7·9-A·10-Pipeline·
  11-Pipeline)은 완료 — 이후는 feature5 다리부터

## 2026-05-15 — feature5-A: 임베딩 입력·payload·멱등성 순수 로직

- 브랜치: `feat/#1/rag-pipeline-skeleton`
- 변경 사항: 테스트 우선(TDD)으로 Dual Embedding + Multi-Pool Vector Store의 결정론적
  순수 로직을 구현 (rag-pipeline-design.md §5, db-schema.md §1·§2.4, app/CLAUDE.md §4)
  - `app/ingestion/vector_store.py` [Storage] — Pool 이름 상수(`TITLE_POOL`/`CONTENT_POOL`/
    `LABEL_POOL`/`POOL_NAMES`, config.py 기본값과 정합) + `build_point_payload(chunk,
    version_number)`: `Chunk` → Qdrant Point payload dict(db-schema.md §1.2의 19필드).
    datetime·enum 값은 JSON 직렬화 가능 문자열로 변환, text_preview는 본문 첫 200자
  - `app/ingestion/embedding.py` [Pipeline] — `pool_embedding_texts(chunk)`: Pool별 임베딩
    입력 텍스트 구성(title=page_title+section_header / 첨부는 attachment_filename+
    section_header, content=청크 본문, label=labels+space_key+doc_type) +
    `should_skip_embedding(version_number, cached_version)`: 멱등성 판정
- 결정 사항·구현 해석:
  - feature5를 5-A(순수 로직 — 외부 의존성 0)/5-B(실제 e5-large·Qdrant·MongoDB 클라이언트
    연동, 무거운 의존성)로 분할. 5-A만 이번 진행 — 5-B 착수 시 가짜/경량 임베더 + Qdrant
    `:memory:` 등 방향을 별도로 정한다 (PDF의 pymupdf 상황과 동일 패턴)
  - **ChunkMetadata에 `version_number` 없음** — version_number는 페이지 단위 값이라
    ChunkMetadata(feature1)에 없다. db-schema.md §1.2 payload·embedding_cache는
    version_number를 요구하므로 `build_point_payload`가 부모 PageObject에서 받아 별도
    인자로 주입한다. ChunkMetadata 스키마는 변경하지 않음(feature1 영역·페이지 단위 값)
  - e5의 `passage:` 프리픽스 등 모델별 처리는 feature5-B(실제 임베더) 책임 —
    `pool_embedding_texts`는 모델 비종속 원문 텍스트만 산출
- 수정 파일: `app/ingestion/{embedding,vector_store}.py`(신규) +
  `tests/ingestion/{test_embedding,test_vector_store}.py`(신규) + `docs/ai/current-plan.md`
- 실행 명령: `./scripts/verify.sh` (ruff format → ruff check → pytest)
- 검증 결과: **178 passed** (기존 166 + feature5-A 12). ruff format·check 통과
  - 테스트: payload 19필드 매핑·page/attachment 분기·null 첨부필드·text_preview 200자
    절단·version_number 주입, Pool별 텍스트 구성(page/attachment), 멱등성 판정
    (동일 버전 skip / 버전 불일치 / 캐시 없음)
- 남은 TODO: feature5-B(실제 임베딩·Qdrant·MongoDB 클라이언트 — 무거운 의존성 방향 확정 후)
  → feature9-B(검색·재순위화 노드 오케스트레이션) → feature11 통합(Query 그래프 + API).
  본 담당자의 순수 로직(7·9-A·10-P·11-P·5-A) 완료 — 이후는 실제 클라이언트 연동 단계

## 2026-05-15 — feature8: history-manager-agent vendoring (Agent 코드 통합 1단계)

- 브랜치: `feat/#1/rag-pipeline-skeleton`
- 배경: Agent 담당자가 멀티턴 히스토리 관리자(`history-manager-agent`)를 전달. 단일 파일이
  아니라 자체 pyproject·`src/` 레이아웃·dataclass 스키마·테스트를 가진 독립 패키지
  (`ai-agent` 저장소 소속, 작성자 Codex)였음. 출력 스키마(`history_decision`/
  `contextualized_question`/`preserved_context` 등)가 RagState의 `history`/`needs_search`
  계약과 1:1로 안 맞음 → 통합 방식을 사용자와 확정
- 결정 사항: **vendoring + 어댑터 노드** 방식 (사용자 선택)
  - agent 코드는 무수정 보존, RAG 저장소 어댑터(`app/query/history.py`)로 RagState와 연결
- 변경 사항 (이번 change-set = vendoring):
  - `src/history_manager_agent/**` → 저장소 루트 `history_manager_agent/`(무수정 — 패키지
    내부 절대 임포트 `from history_manager_agent...`를 그대로 살리려면 루트 패키지여야 함)
  - `tests/**` → `tests/history_manager_agent/**`(테스트 파일 무수정. RAG 저장소 pytest가
    패키지 모드라 빈 `__init__.py` 3개만 추가 — 마커 파일이며 agent 테스트 코드는 무수정)
  - `history-manager-agent.md` → `docs/history-manager-agent.md`(스펙 참조용)
  - `pyproject.toml`: `[tool.setuptools.packages.find]`에 `history_manager_agent*` 추가,
    `[tool.ruff] extend-exclude`로 벤더 코드(`history_manager_agent`,
    `tests/history_manager_agent`)를 RAG lint/format 대상에서 제외 — 원본 무수정 보존.
    통합 어댑터(`app/query/history.py`)는 RAG ruff로 정상 검사
  - agent의 자체 `pyproject.toml`·top-level `scripts/`·`data/`·`.env.example`은 미반입
- 수정 파일: `history_manager_agent/**`(신규 20), `tests/history_manager_agent/**`(신규 18) +
  `docs/history-manager-agent.md`(신규) + `pyproject.toml` + `docs/ai/current-plan.md`
- 실행 명령: `./scripts/verify.sh` (ruff format → ruff check → pytest)
- 검증 결과: **254 passed** (RAG 178 + 벤더 history-manager-agent 76). 벤더 패키지 import
  정상, 벤더 테스트가 3.10 샌드박스(usercustomize shim)에서 전부 통과. ruff는 벤더 코드 제외
- 남은 TODO: feature8 어댑터 — `app/query/history.py`(`manage_history` 노드) + `RagState`에
  `HistoryDecision` 모델·`history_decision` 필드 확장(제안 매핑은 current-plan.md feature8).
  사용자에게 RagState 확장 매핑 확인 후 진행

## 2026-05-15 — feature8: 히스토리 어댑터 노드 + RagState 확장 (Agent 코드 통합 2단계)

- 브랜치: `feat/#1/rag-pipeline-skeleton`
- 결정 사항: RagState 확장 매핑을 사용자가 승인("제안대로 진행") — 비파괴 매핑
- 변경 사항: 테스트 우선(TDD)으로 vendoring한 history-manager-agent를 RagState에 연결
  - `app/schemas/rag_state.py` — `HistoryDecision` Pydantic 모델 신설(`decision`/
    `contextualized_question`/`preserved_context`/`reset_required`/`confidence`/`reason`/
    `warnings`) + `RagState.history_decision: HistoryDecision | None` 필드 추가.
    `app/schemas/__init__.py` re-export 갱신
  - `app/query/history.py` — `manage_history(state, *, provider=None) -> RagState` 어댑터 노드.
    파일 기반 워크플로 대신 agent의 조립 가능한 로직 함수(`normalize_history_input_payload`
    → `classify_history` → `apply_context_policy` → `build_question_result`)를 in-process로
    호출하고, `ContextualizedQuestionResult`를 `RagState.history_decision`으로 매핑
  - `app/query/__init__.py` — re-export 갱신
- 매핑 원칙 (current-plan.md feature8 정합):
  - `RagState.query`는 원문 비파괴 — `contextualized_question`은 `history_decision`에 담음
  - `RagState.needs_search`는 기본 `True` 유지 — agent MVP가 검색스킵 신호를 내지 않음
  - `conversation_id` 없으면 agent 호출 없이 new_topic 단축. 빈 history도 LLM 호출 없이
    new_topic (agent 워크플로와 동일)
  - RagState.HistoryTurn에 turn_id·created_at이 없어, turn_id는 순번 합성, created_at은
    agent의 결정론적 fallback(목록 순서=시간 순서)에 위임
- LLM provider: 기본 `FakeHistoryLLMProvider`(PoC·테스트), 실제 `OpenAIHistoryLLMProvider`
  주입 가능. `app/query/history.py`는 [Agent] 컴포넌트이나 어댑터 자체는 결정론적이라
  fake provider로 단위테스트
- 수정 파일: `app/query/history.py`(신규) + `tests/query/test_history.py`(신규) +
  `app/schemas/{rag_state,__init__}.py` + `app/query/__init__.py` +
  `docs/ai/{current-plan,working-log}.md`
- 실행 명령: `./scripts/verify.sh` (ruff format → ruff check → pytest)
- 검증 결과: **262 passed** (기존 254 + 어댑터 8). ruff format·check 통과
  - 테스트: conversation_id 없음 단축, 빈 history new_topic, follow_up/new_topic/ambiguous
    분류별 RagState 매핑, query 비파괴·needs_search 유지, HistoryTurn→ConversationTurn 변환
- 남은 TODO: feature5-B(실제 임베딩·Qdrant·MongoDB) → feature9-B(검색·재순위화 노드
  오케스트레이션) → feature11 통합(Query 그래프 조립 + API — 히스토리 어댑터·검색·검증·
  포맷터·라우터(Agent 전달 후) 배선). 질의 라우터는 Agent 담당자 전달 시 동일 방식으로 통합


## 2026-05-17 — 코드 리뷰 후속: P1·P2 보완

- 브랜치: `feat/#1/rag-pipeline-skeleton`
- 배경: `docs/ai/code-review-2026-05-17.md`의 P1 3건 + 본 담당자 영역 P2 결함을 일괄 보완.
  옵션 "P1 + 본 담당자 영역 P2 (권장)"를 사용자 승인 후 진행.

### 변경 사항

P1-1 (Settings.samples_dir):
- `app/adapters/factory.py` 신설 — `build_source_adapter(settings)`가 `Settings.source_type`
  에 따라 어댑터를 생성하고 `samples_dir`을 주입한다. `UnsupportedSourceTypeError` 추가.
- `app/adapters/__init__.py` re-export 갱신.
- `app/config.py` `mysql_uri`에 운영 전환 시 `SecretStr` 승급 후보 NOTE 추가.

P1-2 (`_is_valid_acl_filter` 강화):
- `app/query/acl.py`에 `_is_valid_acl_clause` 신설. `should` 절 내부 구조(`key`/`match.any`)
  까지 검사하도록 `_is_valid_acl_filter` 강화. 잘못된 호출 조기 감지.
- `enforce_acl` docstring을 coroutine 반환 함수 한정 표현으로 정정.

P1-3 (`Attachment.local_path` 분리):
- `docs/adr/0001-attachment-source-url.md` 신규 — `download_url`은 사용자 노출용 URL/URI,
  `local_path`(선택)는 청커가 파일을 직접 열 때 사용. 운영 어댑터는 다운로드 헬퍼가 채운다.
- `app/schemas/page_object.py` `Attachment.local_path: str | None = None` 추가(비파괴).
- `app/adapters/json_fixture.py` `_map_attachments`가 `download_url`은 file:// URI,
  `local_path`는 실제 경로로 분리 매핑.
- `app/ingestion/chunker/attachment.py` `_resolve_attachment_path` 헬퍼 추가. `_chunk_docx`·
  `_chunk_xlsx`가 그 경로를 사용.
- `docs/db-schema.md` Attachment 스펙·주석 갱신.

본 담당자 영역 P2:
- xlsx 단일 행/축소 한계(10행) 그룹이 800토큰 초과 시 슬라이딩 윈도우 추가 분할
  (`_group_sheet_rows` `emit_single_row`). 클러스터 메트릭 시트가 행 단위로 분해됨.
- `_looks_like_header`를 raw value 기반으로 보강 — datetime 셀이 헤더로 오인되지 않게 함.
- `ChunkMetadata.doc_type`을 `DocType | AttachmentType`으로 정적 강제(StrEnum이라
  직렬화는 동일). 잘못된 doc_type 값 주입을 컴파일 시 차단.
- `metadata.build_metadata`·`attachment.build_attachment_metadata`에서 `str(doc_type)`/
  `str(attachment_type)` 변환 제거 — enum 그대로 전달.
- `vector_store.build_point_payload`·`embedding.pool_embedding_texts`에 `.value` 명시
  (enum 통일).
- `tests/test_config.py` `.env` 자동 로드를 끄는 `_isolate_rag_env` autouse fixture +
  `_settings_without_env_file` 헬퍼 추가 — 개발자 머신 `.env`가 `Settings()` 검증을
  오염시키지 않도록 격리. 모든 `Settings()` 호출이 `_env_file=None`으로 격리됨.

신규 회귀 테스트 (7건 + 1건 갱신):
- `tests/adapters/test_factory.py` (4건): 기본값/Settings.samples_dir 주입/unknown 거부/
  atlassian deferred.
- `tests/query/test_acl.py`: 비-리스트 groups 거부, `_is_valid_acl_filter` 절 구조 검사,
  async 함수 데코레이션 통합 (3건).
- `tests/schemas/test_page_object.py`: Attachment.local_path 기본/명시 (2건 보강).
- `tests/ingestion/chunker/test_attachment.py`: 단일 행 oversize 슬라이딩, datetime 헤더
  오인 방지 (2건 신규), 기존 `[클러스터 메트릭] 행 1~10` 단언을 P2 동작에 맞춰 갱신.

### 검증 결과

- ruff format / ruff check: 통과 (1개 파일 reformat 됨, all checks passed)
- pytest: **272 passed** (이전 baseline 262 + 신규 회귀 10건). RAG 핵심 196 + vendor
  history-manager-agent 76. 1 failed→0 (사용자 `.env` 의존 환경 격리 결함 보완 포함).

### 비고

- 손상된 Edit 도구로 인해 일부 파일이 truncate 됐던 사건은 `git restore` + bash python으로
  안전하게 재패치하여 해결. 모든 변경 파일은 UTF-8 LF로 일관 저장.
- 의도된 미완 영역(`app/api/`, `app/pipeline/`, `app/llm/`, `app/query/generator.py`,
  `app/query/router.py`, `app/ingestion/document_analyzer.py`, AtlassianSourceAdapter,
  feature4-B/5-B/6/9-B/10-Agent/11-통합)은 변경하지 않았다.
- ACL 모델·청크 메타·라우팅/검증 임계값 등 동결 계약은 변경 없음(P1-3은 `Attachment`에
  새 필드 추가만 — 비파괴 확장).

### 남은 TODO

- ADR-0001 반영 — `AtlassianSourceAdapter` 구현 시 다운로드 헬퍼가 `local_path`를 채우는
  단계를 포함한다.
- 코드 리뷰 P2 잔여(품질 튜닝 영역): `verifier._token_grounded` 워드 경계·`count_tokens`
  SentencePiece 도입·ACL prefix 컨벤션 ADR — 별도 세션/스프린트에서.


## 2026-05-17 — 코드 리뷰 후속 2: 시연 데모 + P2 잔여 + ADR-0002

- 브랜치: `feat/#1/rag-pipeline-skeleton`
- 배경: 직전 change-set(P1+P2)이 완료된 뒤, 회사 시연 전에 "쿼리 → 샘플 데이터 검색"이
  실제로 동작함을 보일 수 있도록 가벼운 PoC 데모와 P2 잔여 항목 두 건을 일괄 보완.

### 변경 사항

검색 시연 데모:
- `examples/demo_search.py` 신규 — 외부 의존성 0건. samples 92p → 청크 379건 →
  Multi-Pool BM25-lite 인메모리 인덱스 → ACL 필터(`build_acl_filter` + 직접 OR 매칭)
  → 의도별 Pool 가중 합산 → Top-K 출처 카드. `RETRIEVAL_EMPTY` 표준 분기 응답까지 시연.
- 데이터 흐름: `JsonFixtureSourceAdapter → chunk_page → pool_embedding_texts →
  BM25Lite → build_acl_filter → 가중 합산 → 출처 카드` — 본 담당자가 끝낸 결정론적
  부품이 모두 잇혀 동작함을 보인다.
- 회사 Mac에서 feature5-B/9-B/11 통합 시 `BM25Lite` 자리만 multilingual-e5-large +
  Qdrant + Cross-Encoder로 교체하면 동일한 흐름이 유지된다.

P2 잔여 (working-log 2026-05-17 직전 섹션에서 "별도 세션" 표기):
- `app/query/verifier.py` `_token_grounded`에 ASCII 워드 경계 적용 — 답변의 '32'가
  청크의 '320' 안에서 false positive 매칭되는 것을 차단. 한글 토큰은 워드 경계 개념이
  없어 부분 문자열 매칭 유지(품질 튜닝 단계에서 Mecab 도입 후 교체).
- `app/ingestion/chunker/storage_format.py` `_HUGO_SHORTCODE` 정규식 추가 — datadog
  본문의 `{{< ref "..." >}}` 같은 Hugo 숏코드 잔재를 정제 단계에서 제거. 임베딩 잡음 감소.

ADR-0002 ACL prefix 컨벤션:
- `docs/adr/0002-acl-prefix-convention.md` 신규 — `space:{key}` prefix 채택을 명시 동결.
  `JsonFixtureSourceAdapter._synthesize_acl`과 `examples/demo_search.py`가 이미 그
  컨벤션을 따르고 있으며, BFF가 JWT `groups` 클레임에 같은 형식을 보장해야 함을 명시.

신규 회귀 테스트:
- `tests/ingestion/chunker/test_storage_format.py::test_hugo_shortcode_is_stripped` (1건)
- `tests/query/test_verifier.py::test_number_not_matched_inside_larger_number` (1건)

### 검증 결과 (집 Windows 샌드박스 기준)

- `python -m examples.demo_search "EKS 노드 장애 대응 절차" --top-k 3`
  → CLOUD/EKS 장애 대응 가이드(#1), CCC/장애 대응 프로세스 표준(#2),
    ONBOARD/Cloud Control Center팀 신규 입사자 온보딩 가이드(#3) 정상 매칭.
- `--groups space:ONBOARD` 만 부여 시 후보 14건으로 정확히 격리됨.
- `--groups space:NONEXIST` 시 RETRIEVAL_EMPTY 표준 분기 응답 출력 확인.
- pytest: **274 passed** (이전 272 + Hugo 숏코드 1 + verifier 워드 경계 1).
- ruff format/check: 통과.

### 비고

- 1 change-set 원칙상 직전 change-set과 분리해서 별도 commit 그룹 3개로 묶었다
  (feat: 시연 데모 / refactor + test: P2 잔여 / docs: ADR-0002 + working-log).
- 회사 Mac에서 진행할 다음 단계 — feature5-B(실제 임베딩·Qdrant) / AtlassianSourceAdapter
  / feature6(Ingestion 그래프) / feature11 통합(Query 그래프 + SSE) — 환경적으로 회사
  환경이 적합한 항목들이다.

### 남은 TODO

- feature4-B / feature5-B / feature6 / feature9-B / feature11 통합 / AtlassianSourceAdapter
  (회사 Mac 다음 세션)
- `docs/api-spec.md`의 JWT 클레임 예시를 `groups=["space:..."]`로 갱신할지 BFF 담당자
  협의 후 결정 (별도 PR)
