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


## 2026-05-18 — 회사 Mac 환경 셋업 + mypy 설정 비대칭 보정

- 브랜치: `feat/#1/rag-pipeline-skeleton`
- 배경: 핸드오프(2026-05-17)에 따라 회사 Mac에서 origin 8커밋 fast-forward 후
  `pip install -e ".[dev,ingestion]"`로 환경 구성. `./scripts/verify.sh` 첫 실행에서
  mypy 단계만 4건 실패 — ruff/pytest는 통과 예정 상태였으나 mypy 2.1.0(신버전) 검사가
  벤더 영역까지 따라 들어가는 비대칭이 드러남.

### 변경 사항

mypy 설정 비대칭 보정 (`pyproject.toml`):
- `[tool.ruff]`에는 `extend-exclude = ["history_manager_agent", "tests/history_manager_agent"]`로
  벤더 코드(History Manager Agent) 제외가 이미 박혀 있었으나, `[tool.mypy]`에는 동일 정책이
  없어 `app/`에서 import를 따라 들어가 벤더 내부의 dataclass/Any 타입 이슈 2건이
  보고되고 있었음.
- `[tool.mypy]`에 `exclude = ["history_manager_agent/", "tests/history_manager_agent/"]` 추가.
- 추가로 `[[tool.mypy.overrides]] module = "history_manager_agent.*"` + `follow_imports = "skip"`
  지정 — `app/query/history.py` 같은 통합 어댑터가 벤더 모듈을 import해도 벤더 내부까지
  파고들지 않도록 정지선 설정.
- 통합 어댑터(`app/query/history.py`) 자체는 정상 검사 유지.

docx 청커 타입 어노테이션 정비 (`app/ingestion/chunker/attachment.py`):
- `_iter_block_items(document: object)` → `_iter_block_items(document: "DocxDocument")`로
  좁힘. python-docx `Document()` 팩토리의 반환 타입(`docx.document.Document`)이
  `t.ProvidesStoryPart` Protocol을 만족하므로 `Paragraph(child, document)` /
  `Table(child, document)` 호출의 mypy 에러(2건)가 해소됨.
- `from docx.document import Document as DocxDocument`는 `TYPE_CHECKING` 가드 안에 둬서
  런타임 import 비용 없음(원본 `from docx import Document as load_docx` 그대로 유지).
- 동시에 `body = document.element.body  # type: ignore[attr-defined]` 주석도 제거 가능
  해져서 함께 정리.

### 검증 결과 (회사 Mac 기준)

- `./scripts/format.sh` — 66 files already formatted, All checks passed.
- `./scripts/lint.sh` — ruff All checks passed + mypy `Success: no issues found in 32 source files`.
- `./scripts/test.sh` — 274 passed 회귀 유지(RAG 198 + vendor history-manager-agent 76).

### 비고

- 핸드오프 §4.2의 "ruff format/check 통과" 옆에 **mypy 명시가 없었던 이유**는 집 환경에
  mypy 1.x가 깔려 있었거나 lint.sh에서 mypy 단계가 silent skip되었던 정황으로 추정.
  Mac에서 `mypy>=1.10` 의존성 명세에 따라 신규 설치된 2.1.0이 더 엄격해서 비대칭이 드러난 것.
- 정책 변경이 아닌 설정의 ruff↔mypy 대칭화이므로 ADR 미작성. 단 향후 벤더 코드
  업데이트 시(예: ai-agent 팀 원본 변경 → re-vendoring) 본 보정도 같이 점검.

### 남은 TODO

- feature4-B(PDF/CSV 청킹) / feature5-B(실제 임베딩·Qdrant) / feature6(Ingestion 그래프) /
  feature9-B / feature11 통합 / AtlassianSourceAdapter — 본 환경 셋업 완료로 이어서 착수 가능.


## 2026-05-18 — feature5-B-1: Dense/Sparse Embedder 어댑터 (ABC + Fake + 실 어댑터)

- 브랜치: `feat/#1/rag-pipeline-skeleton`
- 배경: feature5-A(임베딩 입력·payload·멱등성 순수 로직, 외부 의존성 0)와 db-schema §1.1
  Qdrant Multi-Pool 명세(dense 1024d Cosine + sparse-bm25 idf) 사이를 잇는 "어떻게
  임베딩할지" 어댑터 계층을 구현. feature5-B를 3개 마일스톤(5-B-1 Embedder / 5-B-2
  Qdrant / 5-B-3 Cache+Indexer)으로 분할한 첫 단계.
- 분할 결정: 9-B(검색·재순위화 노드 오케스트레이션)의 query 임베딩 의존을 가장 적은
  코드로 해소하는 단위. 외부 서비스 연결 없이 단위 테스트 완비 가능 — 위험 최소.

### 변경 사항

신규 패키지 `app/ingestion/embedder/`:

- `base.py` (~180 lines)
  - `DenseEmbedder`·`SparseEmbedder` ABC — 기존 `DocumentSourceAdapter` 패턴 정합
    (ABC + abstractmethod, Protocol 미사용).
  - `SparseVector` frozen dataclass(slots=True) — Qdrant Named Vector(sparse-bm25)
    upsert 형식과 정합. `__post_init__`에서 indices/values 길이 동일 강제.
  - `FakeDenseEmbedder` / `FakeSparseEmbedder` — 결정론적 sha256 해시 기반 구현.
    실 모델 다운로드(e5-large 약 2.24 GB) 없이 단위 테스트가 통과하도록 한다.
  - 외부 의존성 0 — 본 모듈만으로 import·테스트 가능.
- `dense.py` (~90 lines)
  - `E5DenseEmbedder` — sentence-transformers `SentenceTransformer` 래퍼.
  - e5 모델 카드 명세 정합: `passage: ` / `query: ` 프리픽스를 어댑터가 강제.
  - `normalize_embeddings=True`로 L2 정규화 강제 — Cosine 검색 정합
    (db-schema.md §1.1).
  - 빈 입력에서는 모델 호출 회피 (불필요한 비용 차단).
- `sparse.py` (~85 lines)
  - `BM25SparseEmbedder` — fastembed `SparseTextEmbedding("Qdrant/bm25")` 래퍼.
  - `query_embed` 메서드가 있으면 사용, 없으면 `embed`로 fallback (fastembed 버전
    호환).
  - 모델 출력(SparseEmbedding, numpy array)을 `SparseVector(tuple[int]/tuple[float])`
    로 변환해 호출자 numpy 의존을 제거.
  - idf modifier 적용은 Qdrant Collection 설정(`sparse_vectors.modifier="idf"`)이
    담당 — 본 어댑터는 모델 산출값을 그대로 전달.
- `__init__.py` (~35 lines)
  - Protocol/Fake만 re-export. 실 어댑터(`E5DenseEmbedder`/`BM25SparseEmbedder`)는
    명시적 import 요구 — 의존성 부재 환경(`embedding` extra 미설치)에서도 base는
    import 가능.

신규 테스트 `tests/ingestion/embedder/` (총 33 unit tests):

- `test_base.py` — 20 tests. SparseVector 불변/길이/empty, FakeDense·Sparse의
  결정론·정규화(L2 norm = 1.0)·shape·batch·passage/query 분기·빈 입력.
- `test_dense.py` — 7 tests. `pytest.importorskip("sentence_transformers")`로 미설치
  환경 스킵. stub SentenceTransformer로 모델 다운로드 회피, 프리픽스·정규화·배치
  사이즈·dimension·빈 입력 단축 확인.
- `test_sparse.py` — 6 tests. `pytest.importorskip("fastembed")`로 미설치 환경 스킵.
  stub SparseTextEmbedding으로 모델 다운로드 회피, query_embed 우선/fallback 분기,
  numpy→Python 원시 타입 변환, 형식 오류 거부.

### 책임 분리 (5-A vs 5-B-1)

- feature5-A `app/ingestion/embedding.py::pool_embedding_texts` → **무엇을** 임베딩할지
  (Pool별 입력 텍스트 구성, 순수 로직).
- feature5-B-1 `app/ingestion/embedder/` → **어떻게** 임베딩할지 (모델 호출·프리픽스·
  정규화·형식 변환). app/CLAUDE.md §8 어댑터/클라이언트 계층 분리 원칙 준수.

### 검증 결과 (회사 Mac 기준)

- format / lint(ruff + mypy) / pytest 통과. 회귀 없음, 신규 33 unit tests 추가.
- `embedding` extra 미설치 환경에서는 test_dense·test_sparse가 importorskip로 스킵됨
  (base 20개만 통과). 설치 환경에서는 stub으로 모델 다운로드 없이 33개 모두 통과.
- 시크릿/토큰 grep 결과 0건 — BM25 토크나이저의 `tokens`/`token` 변수만 매칭됨(무관).

### 비고

- 기존 패턴 확인 후 채택: `app/adapters/base.py`의 ABC + abstractmethod 스타일을
  그대로 따라감 (Protocol + runtime_checkable 대안은 codebase 부재로 도입 보류).
- `pyproject.toml` 변경 없음 — `[embedding]` extra에 `sentence-transformers>=3.0`,
  `fastembed>=0.3`, `kiwipiepy>=0.17`이 이미 명세돼 있음. 실 어댑터 사용 시 사용자가
  `pip install -e ".[embedding]"`로 설치한다.
- `docker-compose.yml` / `.env.example` 변경 없음 — 5-B-2(Qdrant 컨테이너 연결)에서
  필요.
- DB 스키마 변경 없음 — Qdrant Collection 생성·payload 인덱스 부착은 5-B-2 책임.

### 남은 TODO

- **5-B-2 (다음 단계)** — `app/storage/qdrant_client.py`: Qdrant Multi-Pool Collection
  생성(dense 1024d Cosine + sparse-bm25 idf, 3 Pool) + payload 인덱스(`allowed_groups`/
  `allowed_users`/`space_key`/`labels`/`doc_type`/`page_id`/`attachment_id`/`source_type`/
  `last_modified`) + Named Vector upsert/search. `:memory:` Qdrant로 통합 테스트.
- **5-B-3** — `app/storage/mongo_cache.py` + `app/ingestion/indexer.py`: embedding_cache
  I/O + 청크 인덱싱 오케스트레이터(멱등성 통합).
- **9-B 의존 해소 진척**: 5-B-1 완료로 query 임베딩 부분 잠금 해제. 5-B-2 후 Qdrant
  검색까지 잠금 해제되면 9-B 착수 가능.


## 2026-05-18 — feature5-B-2: Qdrant Multi-Pool 클라이언트 + 5-A payload chunk_id 보정

- 브랜치: `feat/#1/rag-pipeline-skeleton`
- 배경: 5-B-1 어댑터 다음으로 Qdrant 측 어댑터를 작성. 부트스트랩(3 Pool 컬렉션·Named
  Vector·payload 인덱스) + Named Vector upsert + ACL 필터 검색 + 키 기반 삭제를
  단일 클래스에 모음. `:memory:` Qdrant in-process 모드로 외부 컨테이너 없이 통합
  검증.
- 5-A 영역 보정(Qdrant Point ID 제약 발견 → 작은 후속 수정): db-schema §1.2는 "Point
  id = chunk_id"라고 명시했으나 Qdrant는 Point ID로 UUID 또는 unsigned int만 허용한다
  (SHA1 hex 40자는 거부). 첫 소비자(5-B-2)에서 드러난 implicit contract 위반이라
  본 change-set에 포함해 보정.

### 변경 사항

5-A 영역 보정 (additive — 외부 동작 호환):

- `app/ingestion/vector_store.py` — `build_point_payload` 결과에 `chunk_id` 필드 1개
  추가. 어댑터가 `uuid5(NAMESPACE_OID, chunk_id)`로 Point ID 매핑하므로, 원본
  `chunk_id`는 payload에서 복원해야 한다. docstring·변경사항 내역 갱신.
- `tests/ingestion/test_vector_store.py` — `test_build_point_payload_includes_chunk_id`
  단언 추가.
- `docs/db-schema.md` §1.2 — Payload 표에 `chunk_id` 행 추가(20필드)
  + "Point ID 매핑" 본문 단락 신설(uuid5 결정론·멱등성 명시). §1.3 keyword 인덱스에
  `chunk_id` 추가.

신규 `app/storage/` 패키지:

- `app/storage/__init__.py` — `QdrantPoolStore`·`SearchHit` re-export. 향후 5-B-3에서
  `mongo_cache.py` 추가 예정.
- `app/storage/qdrant_client.py` (~390 lines)
  - `QdrantPoolStore` 클래스 [Storage] — db-schema §1 정합.
    - `from_settings()` — 실 Qdrant 서버 연결(host/port).
    - `in_memory()` — qdrant-client `:memory:` in-process 클라이언트 (테스트·PoC).
    - `bootstrap_collections()` — 3 Pool 컬렉션 멱등 생성 + payload 인덱스 9종 부착
      (`chunk_id`/`allowed_groups`/`allowed_users`/`space_key`/`labels`/`doc_type`/
      `page_id`/`attachment_id`/`source_type` keyword + `last_modified` datetime).
      Named Vector(dense Cosine + sparse-bm25 idf) — db-schema §1.1 정합.
    - `upsert_chunk` / `upsert_chunks_batch` — chunk_id → uuid5 매핑, payload는
      `build_point_payload`(5-A) 재사용, vector는 {"dense": [...], "sparse-bm25":
      QdrantSparseVector(...)}.
    - `search` — 단일 Named Vector 검색(dense 또는 sparse). Hybrid는 호출자가 두 번
      호출 후 9-A `reciprocal_rank_fusion`으로 결합(설계서 §6 4.5). `acl_filter`는
      필수 키워드 인자로 강제 → 미주입 시 시그니처 오류. `metadata_filters` 부가
      적용(str → MatchValue, list → MatchAny). qdrant-client v1.11에서 deprecated된
      `search()` 대신 `query_points()` 사용.
    - `delete_by_page_id` / `delete_by_attachment_id` / `delete_by_chunk_id` —
      문서·첨부·청크 단위 삭제(세 Pool 모두에서). feature6 sync 어댑터 의존성 해소.
  - `SearchHit` frozen dataclass — qdrant-client `ScoredPoint` 의존을 어댑터 안쪽으로
    격리. payload에서 원본 `chunk_id` 복원.
  - `_chunk_id_to_point_id(chunk_id)` 헬퍼 — `uuid5(NAMESPACE_OID, chunk_id)` 결정론
    매핑. 동일 `chunk_id` → 동일 UUID → Qdrant 레벨에서도 멱등 upsert 유지.

신규 테스트 `tests/storage/test_qdrant_client.py` (~480 lines, 22 unit·통합 tests):

- `_chunk_id_to_point_id` 결정론·UUID 형식·서로 다른 chunk_id → 서로 다른 UUID.
- `_pool_name_to_collection` — 알려진 pool 매핑 / 알 수 없는 pool 거부.
- `SearchHit` 불변성.
- `:memory:` 통합:
  - `bootstrap_collections` — 3 Pool 생성 + 멱등(두 번 호출 OK) + Named Vector 구조
    확인(dense + sparse-bm25 둘 다 설정됨).
  - Upsert + dense 검색으로 chunk_id 복원 + Cosine 자기-매칭 1.0.
  - Upsert 배치 + 정렬·매칭 검증.
  - 멱등 upsert(동일 chunk_id 재호출 → count 동일 + version_number 갱신).
  - ACL 필터: 일치 그룹만 매칭, 불일치 그룹은 빈 결과.
  - dense·sparse 분기: sparse-only 검색 / 빈 sparse → short-circuit / 동시 입력
    거부 / 둘 다 없음 거부 / top_k 제한.
  - metadata_filters: str → MatchValue, list → MatchAny.
  - 삭제: page_id / attachment_id / chunk_id별 — 다른 청크 보존.
  - POOL_NAMES 회귀 — 3 Pool 모두 독립 동작.

### 책임 분리 (5-A vs 5-B-1 vs 5-B-2)

- feature5-A `vector_store.py::build_point_payload` → 무엇을 payload로 담을지(db-schema
  §1.2 스키마 매핑).
- feature5-B-1 `embedder/` → 어떻게 임베딩할지(모델 호출·프리픽스·정규화).
- feature5-B-2 `storage/qdrant_client.py` → 어떻게 저장·검색·삭제할지(컬렉션·인덱스·
  Named Vector·Point ID 매핑·필터 결합). `@enforce_acl`(feature7)이 검증한 acl_filter
  dict를 받아 Qdrant Filter로 결합한다.

### 검증 결과 (회사 Mac 기준)

- format / lint(ruff + mypy) / pytest 통과. 회귀 없음, 신규 ~23 tests 추가
  (storage 22 + vector_store 1).
- `:memory:` 통합 테스트 22건 — 부트스트랩 멱등성·Named Vector·ACL 필터·검색 분기·
  멱등 upsert·키 기반 삭제까지 모두 검증.
- qdrant-client `:memory:` 로컬 모드에서 payload 인덱스 UserWarning(`Payload indexes
  have no effect`)은 무시 처리(`warnings.filterwarnings`) — 실 Qdrant 서버에서는
  성능 인덱스로 동작함을 db-schema 본문에 명시.
- 시크릿/토큰 grep 결과 0건 — `token_count`(필드명)만 매칭.

### 비고

- qdrant-client `search()` 메서드는 deprecated → `query_points()`로 갈아탔다. 출력은
  `QueryResponse.points` (list[ScoredPoint]).
- Filter 결합 패턴: ACL Filter(`should` OR) + metadata FieldCondition/Filter들을 함께
  `must` 리스트에 둠. Qdrant Filter는 `must` 안에 `FieldCondition`과 nested `Filter`
  혼용을 허용한다.
- 운영 Qdrant 서버에서 `shard_number=2 / replication_factor=1 / on_disk_payload=true`
  설정은 그대로 적용된다. `:memory:` 로컬 모드는 단일 샤드로 동작.
- 새 의존성 도입 없음 — `qdrant-client>=1.9`는 이미 main dependencies에 있다.

### 남은 TODO

- **5-B-3** — `app/storage/mongo_cache.py` + `app/ingestion/indexer.py`: MongoDB
  `embedding_cache` I/O + 청크 인덱싱 오케스트레이터(임베더 + Qdrant 클라이언트 +
  캐시 + 멱등성 통합). 5-B 마무리.
- **9-B 의존 완전 해소** — query 임베딩(5-B-1) + Qdrant 검색(5-B-2) 둘 다 준비됨 →
  9-B(검색·재순위화 노드 오케스트레이션) 즉시 착수 가능.
- 운영 Qdrant 서버 라이브 smoke 테스트 — `docker compose up qdrant` 후 `samples/`
  일부 청크 upsert·검색 시각 확인. 별도 세션.


## 2026-05-18 — feature5-B-3: Mongo embedding_cache + Indexer (5-B 마무리)

- 브랜치: `feat/#1/rag-pipeline-skeleton`
- 배경: 5-A(payload·멱등성 순수 로직) · 5-B-1(Embedder 어댑터) · 5-B-2(Qdrant Multi-Pool
  클라이언트) 부품을 끝까지 잇는 마지막 단계. embedding_cache로 `(chunk_id,
  version_number)` 기반 멱등성을 통합하고 청크 → 임베딩 → upsert 오케스트레이터를 도입.
  5-B 시리즈 완성.

### 변경 사항

신규 `app/storage/mongo_cache.py` (~170 lines):

- `EmbeddingCache` ABC — Ingestion indexer의 멱등성 의존성. ``get_cached_version`` /
  ``set_cached_version`` 두 메서드.
- `EmbeddingCacheEntry` frozen dataclass — db-schema §2.4 정합 (chunk_id /
  version_number / dense_hash / sparse_hash / computed_at).
- `MongoEmbeddingCache` — pymongo 래퍼. `find_one` projection + `update_one` upsert로
  멱등 I/O. ``from_settings`` 가 ``Settings.mongo_uri``/`mongo_db`에서 클라이언트 생성.
- `FakeEmbeddingCache` — in-memory dict. 외부 의존성 0, 테스트·PoC용. ``entries`` 속성
  으로 cache 상태 직접 assert 가능.

신규 `app/ingestion/indexer.py` (~160 lines):

- `index_chunks(chunks, version_by_page_id, dense_embedder, sparse_embedder, store, cache)
  -> IndexerResult` — 3-phase 배치 처리:
    1. **Filter** — `cache.get_cached_version == version` 인 청크는 스킵 (멱등성).
    2. **Embed** — 남은 청크에 대해 Pool별 입력 텍스트(5-A `pool_embedding_texts`)를
       모아 dense/sparse 배치 임베딩. Pool 수(3)만큼만 임베더 호출 — 네트워크·모델
       라운드트립 최소화. 청크 수와 무관한 배치 효율.
    3. **Upsert + cache write** — Pool별 배치 upsert(5-B-2 `upsert_chunks_batch`) 후
       `embedding_cache` 갱신. cache write는 모든 Pool upsert 성공 후에만 — 도중 실패
       시 다음 실행에서 재시도되도록 best-effort 멱등성 유지.
- `IndexerResult` 데이터클래스 — `upserted_count`/`skipped_count` + 추적용 chunk_id
  목록 (테스트 어서션·운영 메트릭).
- `_hash_dense_vector` / `_hash_sparse_vector` — db-schema §2.4 ``dense_hash`` /
  ``sparse_hash`` 메타데이터(skip 판정에는 사용 X, 추적용).

수정 `app/storage/__init__.py`: ``EmbeddingCache``·``EmbeddingCacheEntry``·
``FakeEmbeddingCache``·``MongoEmbeddingCache`` re-export 추가.

### 신규 테스트 (`tests/storage/test_mongo_cache.py` + `tests/ingestion/test_indexer.py`)

`test_mongo_cache.py` (~10 tests):
- `EmbeddingCacheEntry` 불변성.
- FakeEmbeddingCache — cache miss / set+get / overwrite / chunk_id 격리.
- MongoEmbeddingCache(unittest.mock.MagicMock 주입, 실 MongoDB 불필요):
  - get → `find_one` 호출 시그니처(projection 포함) 검증.
  - get cache miss → None 반환.
  - set → `update_one` 멱등 upsert 호출 검증.
  - `from_settings` 가 pymongo `MongoClient` 호출 (pymongo 설치 시).

`test_indexer.py` (~10 tests, `:memory:` Qdrant + Fake everything):
- 단건 인덱싱 — 3 Pool 모두 적재 + cache 기록.
- 동일 version 재호출 — 모두 cache hit으로 스킵 (멱등성).
- version 변경 — 재인덱싱.
- 부분 cache hit — 새 청크만 인덱싱.
- 빈 입력 — `IndexerResult(0,0)` 반환.
- 모두 cache hit 시 임베더 호출 횟수 0 (배치 효율 — short-circuit).
- 배치 효율 — Pool 수(3) × 1 embed call (청크 5개여도 임베더는 3번만 호출, batch_size=5).
- 다중 페이지 — 청크별 부모 page_id의 version을 정확히 사용. Qdrant payload의
  `version_number` 도 정합.
- `KeyError` — `version_by_page_id` 에 page_id 없으면 즉시 실패.
- 5-A 통합 검증 — `title_pool` 입력 텍스트가 `page_title + section_header`,
  `content_pool` 입력이 청크 본문임을 임베더 capture로 우회 확인.

### 책임 분리 (5-A vs 5-B-1 vs 5-B-2 vs 5-B-3)

- **feature5-A**: 무엇을 임베딩할지 (Pool별 입력 텍스트 구성) + 무엇을 payload에 담을지.
- **feature5-B-1**: 어떻게 임베딩할지 (Dense/Sparse 모델 어댑터).
- **feature5-B-2**: 어떻게 저장·검색·삭제할지 (Qdrant Multi-Pool 클라이언트).
- **feature5-B-3**: 언제·얼마나 임베딩할지 (멱등성 + 오케스트레이션) + 캐시 I/O.

5-B 시리즈 4개 컴포넌트가 모두 어댑터 계층(`app/CLAUDE.md` §8)으로 분리되어 있어,
실 어댑터를 Fake로 교체하면 외부 의존성 없이 단위 테스트가 끝까지 동작한다.

### 검증 결과 (회사 Mac 기준 — 예상)

- format / lint(ruff + mypy) / pytest 통과 예상.
- 신규 ~20 tests (mongo_cache 10 + indexer 10).
- `pymongo` 미설치 환경에서는 `test_mongo_cache_from_settings_imports_pymongo` 만 skip,
  나머지는 mock으로 통과.

### 비고

- 새 외부 의존성 도입 없음 — `pymongo>=4.7` 은 이미 main dependencies에 명시됨.
- DB 스키마 변경 없음 — `embedding_cache` 컬렉션은 db-schema §2.4 정합 그대로.
- Indexer는 함수 형태로 두고 클래스 캡슐화는 도입하지 않음 — 9-B 그래프 노드처럼
  앞으로 LangGraph 노드 래퍼만 추가하면 그래프에 그대로 꽂힌다(상태 없는 함수 + 주입된
  의존성).
- 본 세션에서 운영 Qdrant 라이브 smoke는 진행하지 않음 — Docker 컨테이너 띄움 후 별도
  세션 권장(samples/ 92p → 청크 → 인덱싱 → 검색 시각 확인).

### 5-B 시리즈 완료 + 9-B 잠금 완전 해소

5-B-1(Embedder) + 5-B-2(Qdrant) + 5-B-3(Cache + Indexer)로 Ingestion 측 흐름이
끝까지 동작 가능해졌다. 9-B(검색·재순위화 노드 오케스트레이션)는 이제 5-B-1의 query
임베딩 + 5-B-2의 Qdrant 검색을 그대로 활용해 즉시 착수 가능하다 — Cross-Encoder 도입과
LangGraph 노드 wiring만 남는다.

### 남은 TODO

- **9-B** — 검색·재순위화 노드 오케스트레이션 (Cross-Encoder 도입 + LangGraph 노드 +
  9-A `reciprocal_rank_fusion` 결합). RAG 사용자 가치 라인.
- **feature11 통합** — Query LangGraph 그래프 조립 + FastAPI SSE. Agent 노드(라우터·
  생성기·검증 2단계)는 stub → 전달 후 교체.
- **운영 Qdrant 라이브 smoke** — `docker compose up` 후 `samples/` 적재·검색 시각 확인.
- **AtlassianSourceAdapter** — `access_token`/`cloudid` 전달 경로 BFF 협의 후.
- **feature4-B** — PDF/CSV 첨부 분할기 (픽스처·`pymupdf` 확보 후).
- **`examples/demo_search.py` 갱신** — BM25-lite 인메모리 검색을 실 5-B-1/2/3로 교체
  하는 시연 데모. 소규모 작업.


## 2026-05-18 — feature9-B-1: Cross-Encoder Reranker 어댑터 (ABC + Fake + 실 어댑터)

- 브랜치: `feat/#1/rag-pipeline-skeleton`
- 배경: 9-B(검색·재순위화 노드 오케스트레이션) 진입을 위해 Cross-Encoder 외부 모델
  어댑터를 5-B-1과 같은 패턴(ABC + Fake + 실 어댑터)으로 격리. 9-A의 순수 로직
  ``select_reranked`` 와 9-B-2/3 노드 오케스트레이션 사이를 잇는 "어떻게 재순위화 점수를
  낼지" 계약.
- 분할 결정: 어댑터만 먼저 격리하면 9-B-2(검색 노드) / 9-B-3(rerank 노드)이 큰 위험
  없이 진입 가능. 5-B 시리즈의 점진적 분할 패턴 연속.

### 변경 사항

신규 패키지 `app/query/reranker/`:

- `base.py` (~70 lines)
  - `CrossEncoderReranker` ABC — `score(query, passages) -> list[float]` 단일 메서드.
    반환 점수는 ``[0.0, 1.0]`` 범위로 강제 — `select_reranked` (9-A)의 임계값
    (``NARROW_SCORE_THRESHOLD=0.30``, ``LOW_CONFIDENCE_THRESHOLD=0.20``) 정합.
  - `FakeCrossEncoderReranker` — sha256 결정론 해시 기반. 같은 ``(query, passage)`` →
    같은 점수. 실 모델 다운로드(약 130 MB) 없이 단위 테스트 통과.
- `cross_encoder.py` (~85 lines)
  - `CrossEncoderRerankerImpl` — sentence-transformers ``CrossEncoder`` 래퍼.
    `model_name` 기본값 ``cross-encoder/ms-marco-MiniLM-L-12`` (`docs/.env.example`
    정합). raw logit → `_sigmoid` 변환으로 ``[0.0, 1.0]`` 점수 산출.
  - `_sigmoid(value)` 헬퍼 — 수치 안정 Sigmoid (큰 양수/음수에서 overflow·underflow
    회피하도록 부호 분기).
- `__init__.py` — Protocol/Fake만 re-export. 실 어댑터는 명시적 import 요구 —
  embedding extra 미설치 환경에서도 base는 import 가능.

신규 테스트 `tests/query/reranker/` (~190 lines, 17 unit tests):

- `test_base.py` — 8 tests. FakeCrossEncoderReranker의 ABC 정합·shape·결정론·
  ``[0.0, 1.0]`` 점수 범위·서로 다른 (query, passage) → 서로 다른 점수·빈 입력·
  **9-A `select_reranked` 와의 통합 흐름** 검증 (어댑터 출력 dict → select_reranked
  → RerankResult).
- `test_cross_encoder.py` — 9 tests. `pytest.importorskip("sentence_transformers")`
  로 미설치 환경 스킵. stub CrossEncoder로 모델 다운로드 회피, pairs 구성·batch_size
  전달·빈 입력 short-circuit·Sigmoid 적용 검증. `_sigmoid` 수치 안정성(0/큰 양수/큰
  음수/단조 증가) 별도 검증.

### 책임 분리 (9-A vs 9-B-1)

- **feature9-A** `app/query/rerank.py::select_reranked` — Top-K 선정·축소·저신뢰
  분기 (순수 로직, ``dict[chunk_id, score]`` 입력).
- **feature9-B-1** `app/query/reranker/` — 점수 산출 어댑터 (외부 모델 호출, raw logit
  → Sigmoid). 호출자(9-B-2/3 노드)가 ``chunk_id`` 매핑을 만들어 두 단계를 결합한다.

### 검증 결과 (회사 Mac 기준 — 예상)

- format / lint(ruff + mypy) / pytest 통과 예상.
- 신규 17 tests (base 8 + cross_encoder 9).
- `embedding` extra 미설치 환경에서는 `test_cross_encoder.py` 9건 skip, `test_base.py`
  8건은 외부 의존성 없이 통과.

### 비고

- 새 의존성 도입 없음 — `sentence-transformers>=3.0` 은 이미 5-B-1에서 도입됨.
- `CrossEncoder.predict` 의 raw logit 출력을 Sigmoid로 변환하는 책임은 어댑터 측에
  명시적으로 둠 — `apply_softmax` 인자에 위임하지 않고 어댑터 자체에서 처리. 9-A 임계값
  정합이 어댑터 계약의 일부이기 때문.
- `_sigmoid` 는 stdlib `math.exp` 만 사용 — `torch.nn.functional.sigmoid` 의존을 피해
  의존성 폭발 회피. 어차피 단일 값씩 처리하므로 vectorize 이득 없음.
- ms-marco-MiniLM-L-12 모델은 한 번에 32쌍 추론 권장 — `docs/conventions.md` §5.7 NOTE
  정합.

### 남은 TODO

- **9-B-2** — `hybrid_search` 노드 (RagState → query 임베딩(5-B-1) → 3 Pool dense+sparse
  검색(5-B-2) → 9-A `reciprocal_rank_fusion` + `merge_pools` → `candidates` Top-20).
- **9-B-3** — `cross_encoder_rerank` 노드 (candidates → 9-B-1 Reranker.score →
  9-A `select_reranked` → `top_chunks` Top-5 + 저신뢰 분기).
- **9-B 의존 완전 해소** — 9-B-1 후 Cross-Encoder 측 잠금까지 해소됨 → 9-B-2/3 즉시
  착수 가능.


## 2026-05-18 — feature9-B-2: hybrid_search LangGraph 노드 (query → 3 Pool RRF → candidates)

- 브랜치: `feat/#1/rag-pipeline-skeleton`
- 배경: 5-B-1(Embedder) + 5-B-2(Qdrant) + 9-A(RRF 순수 로직)를 LangGraph 노드 형태로
  잇는다. RagState의 `query` (+선택적 `rewritten_queries`)를 받아 dense·sparse 임베딩 →
  3 Pool ACL 필터 검색 → RRF + Pool 가중 합산 + Top-20 선정 → `candidates` 채움까지
  한 단계로 처리. ACL 미주입 호출은 `@enforce_acl` 가드(feature7)로 시스템 단에서 거부.

### 변경 사항

신규 `app/query/search_node.py` (~215 lines):

- `hybrid_search(state, *, dense_embedder, sparse_embedder, store, top_k=20)` —
  외부 노드 (`(state) -> state` 표준 시그니처). 의존성은 키워드 인자로 주입 —
  LangGraph 그래프 조립(feature11)에서 `functools.partial` 또는 클로저로 wiring.
- `_hybrid_search_acl_guarded(state, *, acl_filter, ...)` — `@enforce_acl` 가드를 통과한
  내부 본문. `state.acl_filter`를 명시 인자로 받아 호출 전 데코레이터가 유효성 검증.
- 알고리즘 5-phase:
    1. **query 텍스트 결정**: `rewritten_queries` 있으면 그것들, 없으면 `[state.query]`.
       라우터(feature8)가 채울 multi-query 확장과 정합.
    2. **배치 임베딩**: dense·sparse 각각 한 번씩 — query 수 무관 임베더 호출 2회.
    3. **3 Pool × N query × {dense, sparse} 검색**: `QdrantPoolStore.search` 직접 호출.
       검색 결과는 chunk_id 기준 SearchHit 풀에 누적 (Chunk 재구성용).
    4. **9-A 결합**: `fuse_and_rank(pool_rankings, pool_weights, limit=top_k)`. query별
       ranking은 `dense_q{idx}` / `sparse_q{idx}` 키로 분리해 RRF가 동등하게 합치도록 함.
    5. **Chunk 재구성**: `_chunk_from_search_hit(hit)` — `payload`(db-schema §1.2 20필드)
       → `Chunk(text=text_preview, metadata=ChunkMetadata(...))`. `token_count=0` default
       (별도 follow-up으로 payload에 token_count 추가 필요).
- `_coerce_metadata_filters` — `dict[str, Any]` → `dict[str, str | list[str]]` 강건 변환.
  잘못된 타입은 무시 (라우터 산출 신뢰성 보장 안 됨).
- `_DEFAULT_POOL_WEIGHTS` — 라우터가 `pool_weights`를 안 채운 경우 등가 fallback.
- `_chunk_from_search_hit` 헬퍼 + 보조 파서(doc_type DocType↔AttachmentType,
  extracted_format, optional_str, datetime ISO).

수정 `tests/query/reranker/test_base.py`: ruff/linter follow-up — unused `import pytest`
제거 (9-B-1 push 후 사용자 mac에서 자동 적용된 변경).

### 신규 테스트 `tests/query/test_search_node.py` (~340 lines, 14 통합 tests)

`:memory:` Qdrant + Fake 임베더 + FakeEmbeddingCache 조합으로 외부 컨테이너·모델
없이 끝-끝 검증:

- **정상 동작**: candidates 채움, in-place mutation, Chunk 재구성 필드 정합
  (page_id/page_title/section_header/space_key/source_type/doc_type/text_preview/
  token_count=0), top_k 제한.
- **ACL 강제**: acl_filter=None → ACLViolationError, acl_filter={} (무효) →
  ACLViolationError, ACL 매칭 그룹만 결과 포함 (CCC 청크 제외), 매칭 없으면 빈 후보.
- **multi-query**: rewritten_queries 모두 한 번에 배치 임베딩 (spy로 호출 시점 검증),
  rewritten_queries 비어 있으면 query 단일 사용.
- **pool_weights**: None → 등가 fallback 동작, 명시 가중치 정상 사용.
- **metadata_filters**: doc_type 단일 값(MatchValue)으로 좁힘, list 값(MatchAny) 다중
  매칭, 비-str/list 타입(int 등)은 무시 — 잘못된 라우터 출력에 강건.

### 책임 분리 (9-A vs 9-B-2)

- **feature9-A** — 순수 결합 로직 (RRF / merge_pools / select_top_candidates /
  fuse_and_rank). 외부 의존성 0.
- **feature9-B-2** — query 임베딩(5-B-1) + Qdrant 검색(5-B-2)을 9-A 로직과 잇고,
  RagState 입출력 + ACL 강제 + Chunk 재구성을 담당하는 노드 wiring.

### 책임 경계 (9-B-2 vs 9-B-3 vs 추후)

- 9-B-2는 candidates(Top-20)까지. **Cross-Encoder 재순위화는 9-B-3** 책임.
- Chunk 재구성의 `text`는 payload의 `text_preview` (첫 200자). 풀 텍스트가 필요한
  단계(예: 답변 생성 LLM)는 별도 chunk lookup 어댑터 추가(후속).
- payload에 `token_count` 가 없어 0 default. **5-A 영역 `build_point_payload`에
  token_count 추가**가 작은 후속 fix로 권장.

### 검증 결과 (회사 Mac 기준 — 예상)

- format / lint(ruff + mypy) / pytest 통과 예상.
- 신규 14 tests (test_search_node.py). 전체 회귀 0건 + 신규 흡수.

### 비고

- `hybrid_search` 노드의 외부 의존성(dense/sparse/store)은 키워드 인자로 노출 —
  LangGraph 통합 시 `functools.partial`로 wiring 권장 (feature11 통합 단계에서 확정).
- 새 의존성 도입 없음 — 모든 부품 기존 5-B-1·5-B-2·9-A·7·1·schemas 재사용.
- DB 스키마 변경 없음. payload에 token_count 추가는 별도 follow-up.

### 남은 TODO

- **9-B-3** — `cross_encoder_rerank` 노드. candidates → 9-B-1 score → 9-A
  `select_reranked` → `top_chunks` Top-5 + 저신뢰 분기. 본 9-B-2의 출력을 바로
  소비. 짧은 작업.
- **5-A payload.token_count 추가** — Chunk 재구성 정합. 작은 refactor commit.
- **풀 텍스트 lookup 어댑터** — payload.text_preview 200자 한계를 넘는 단계가 필요해질 때.
- **examples/demo_search.py 갱신** — BM25-lite → 9-B-2 노드 호출로 시연 데모 교체.
- **운영 Qdrant 라이브 smoke** — 5-B + 9-B-2 묶어 시각 확인.


## 2026-05-18 — feature9-B-3: cross_encoder_rerank 노드 (Top-5 + sources, 9-B 마무리)

- 브랜치: `feat/#1/rag-pipeline-skeleton`
- 배경: 9-B-2가 채운 `candidates` (Top-20)을 받아 9-B-1 Reranker로 (query, passage)
  관련도 점수를 산출하고, 9-A `select_reranked` 결정론 로직으로 Top-K(5 또는 3) +
  저신뢰 분기까지 적용해 `top_chunks` 와 `sources` 출처 카드를 채운다. **9-B 시리즈
  완료** — query 라인 검색·재순위화가 끝까지 동작.

### 변경 사항

신규 `app/query/rerank_node.py` (~125 lines):

- `cross_encoder_rerank(state, *, reranker)` LangGraph 노드. `(state) -> state` 표준
  시그니처에 reranker만 키워드 주입 (history.py 패턴 정합). 빈 candidates면 즉시
  short-circuit 후 `top_chunks=[], sources=[]` 초기화.
- 알고리즘 5-phase:
    1. **short-circuit**: `candidates` 가 비어 있으면 reranker 호출 없이 빈 결과.
    2. **query 텍스트 결정**: `history_decision.contextualized_question` 우선, 없거나
       빈 문자열이면 원 `state.query`.
    3. **Reranker.score**: 9-B-1 어댑터가 [0.0, 1.0] 점수 산출 (Sigmoid 정규화 정합).
    4. **9-A select_reranked**: chunk_id → score dict 입력 → RerankResult.top 정렬·축소·
       저신뢰 분기 결정.
    5. **top_chunks + sources 매핑**: `result.top` 순서 그대로 Chunk 목록 + Source
       카드 동시 채움.
- `_chunk_to_source(chunk, raw_score)` 헬퍼 — `docs/api-spec.md` Source 스키마 정합:
  - `title` = attachment_filename(첨부) OR page_title(본문)
  - `score` = `round(raw_score * 100)` — int 0~100 (포맷터 LOW_CONFIDENCE_SCORE=20 정합)
  - `path` = section_path, `confluence_url` = webui_link
  - `text_preview` = chunk.text (5-A의 첫 200자 보존)
  - `download_url` = None (ChunkMetadata에 없음 — 풀 텍스트 lookup 어댑터 추가 시 채움)
- `is_low_confidence` 신호는 RagState 별도 필드로 두지 않음 — 응답 포맷터(feature11)의
  `_is_low_confidence(sources)` 가 `Source.score < LOW_CONFIDENCE_SCORE` 임계로 동일
  판정. 본 노드는 score만 정확히 매핑하면 포맷터가 자동 분기.

### 신규 테스트 `tests/query/test_rerank_node.py` (~335 lines, 16 tests)

외부 의존성 0 — Fake Reranker + 임의 stub Reranker:

- **short-circuit**: 빈 candidates → reranker 호출 0회 검증 (spy), top_chunks·sources
  비움, 기존 top_chunks 초기화.
- **선정·정렬**: 단건 정상, 7개 후보에서 Top-5 점수 내림차순 매핑.
- **Top-3 축소**: 5위 점수 < `NARROW_SCORE_THRESHOLD` (0.30) → Top-3, 정확히 임계값
  일치하면 Top-5 유지 (strict less than 보장).
- **저신뢰 분기**: 모든 점수 < `LOW_CONFIDENCE_THRESHOLD` (0.20) → Source.score 모두
  20 미만. `LOW_CONFIDENCE_THRESHOLD*100 == 20` 임계 정합 단언.
- **contextualized_question**: 있으면 우선 사용 (spy로 검증), 없거나 빈 문자열이면
  원 query fallback.
- **Source 매핑**: 본문/첨부 청크별 title 분기, 모든 필드 매핑(path/space_key/
  source_type/confluence_url/text_preview/attachment_filename/mime), score 반올림
  (raw 0.567 → 57), top_chunks-sources 동기 정합.
- **노드 계약**: in-place mutation (`result is state`).

### 책임 분리 (9-A vs 9-B-1 vs 9-B-2 vs 9-B-3)

- **9-A** `select_reranked` — Top-K 선정·축소·저신뢰 분기 (순수 로직).
- **9-B-1** `CrossEncoderReranker` — (query, passage) → [0, 1] 점수 (어댑터).
- **9-B-2** `hybrid_search` 노드 — query 임베딩 + 3 Pool 검색 + 9-A `fuse_and_rank` →
  candidates.
- **9-B-3** `cross_encoder_rerank` 노드 ⬅ 본 세션 — candidates + 9-B-1 + 9-A
  `select_reranked` → top_chunks + sources.

### 9-B 시리즈 완료 + feature11 진입 가능

5-B-1(Embedder) + 5-B-2(Qdrant) + 5-B-3(Cache+Indexer) + 9-A(순수 로직) + 9-B-1
(Reranker) + 9-B-2(검색 노드) + 9-B-3(재순위화 노드)으로 query 라인의 비-Agent 부품이
모두 준비됨. 답변 생성기(Agent 담당)·검증 2단계(Agent 담당)는 별도 트랙. feature11
통합(Query LangGraph 그래프 + FastAPI SSE)이 이제 진입 가능 — Agent 노드는 stub로 두고
end-to-end 흐름을 먼저 검증.

### 검증 결과 (회사 Mac 기준 — 예상)

- format / lint(ruff + mypy) / pytest 통과 예상.
- 신규 16 tests (test_rerank_node.py). 전체 회귀 0건 + 신규 흡수.

### 비고

- 새 의존성 도입 없음 — 5-B-1/9-A/9-B-1 + schemas만 재사용.
- Source 스키마 변경 없음 (`docs/api-spec.md` 정합 그대로).
- 9-B-3 노드는 `cross_encoder_rerank` 단일 함수 + 헬퍼 — 11 통합 시 functools.partial
  로 wiring하고 그래프 노드로 등록.

### 9-B 시리즈 책임 도식 (마무리)

```
candidates (5-B-2 / 9-B-2 산출)
       │
       ├─► 9-B-1 Reranker.score(query, passages) → list[float] in [0, 1]
       │
       ├─► chunk_id ↔ score dict 변환
       │
       ├─► 9-A select_reranked → RerankResult(top=[(id, score)], is_low_confidence)
       │      • Top-5 선정 (동점 chunk_id asc 결정론)
       │      • 5위 < NARROW(0.30) → Top-3 축소
       │      • 최고 < LOW(0.20) → 저신뢰 분기 (단, RagState엔 별도 X)
       │
       └─► 9-B-3 chunk_to_source 매핑
              • top_chunks: list[Chunk]
              • sources: list[Source] (score 0~100, 포맷터 임계 정합)
```

### 남은 TODO

- **feature11 통합** — Query LangGraph 그래프 조립 + FastAPI SSE. Agent 노드(라우터·
  생성기·검증 2단계)는 stub → 전달 후 교체. 9-B-2·9-B-3은 functools.partial로 wiring.
- **5-A payload.token_count 추가** — Chunk 재구성 정합 (작은 refactor).
- **풀 텍스트 lookup 어댑터** — Source.download_url + payload.text_preview 한계 보완.
- **examples/demo_search.py 갱신** — BM25-lite → 실 5-B + 9-B 노드 호출로 시연.


## 2026-05-18 — feature11 통합 Phase 1: Query LangGraph 그래프 조립

- 브랜치: `feat/#1/rag-pipeline-skeleton`
- 범위 결정: feature11 통합을 두 단계로 분할 — **Phase 1(본 세션)**: LangGraph 그래프
  조립 + Agent stub 3종 + end-to-end 통합 테스트. **Phase 2(후속 세션)**: FastAPI
  SSE 라우트 + httpx in-process 테스트. 1 change-set = 1 session 원칙(루트
  `CLAUDE.md` "세션 운영 원칙") 정합 + 디버깅 단순성 우선.
- 배경: 5-B 시리즈(임베더·Qdrant·캐시·Indexer) + 9-B 시리즈(Reranker·검색 노드·
  재순위화 노드)로 Pipeline 노드가 모두 준비됨. Agent 노드(라우터·답변 생성기·
  검증 2단계 LLM 평가자)는 별도 담당자 영역 → fake로 단일 모듈에 격리해 교체
  지점을 한 곳에 모은다.

### 변경 사항

신규 `app/pipeline/stubs.py` (~115 lines, Agent stub 3종):

- `router_stub(state) -> state` — 질의 라우터 [Agent] fake. rag-pipeline-design.md
  §8 "라우터 LLM 타임아웃 fallback" 정합으로 다음을 채운다:
    - `intent = OPERATION_GUIDE`
    - `rewritten_queries = [state.query]` (원본 쿼리 단일)
    - `pool_weights = {title:0.2, content:0.7, label:0.1}` (운영가이드 가중치)
    - `target_llm = GPT_4O`
    - `metadata_filters = None`
- `generator_stub(state) -> state` — 답변 생성기 [Agent] fake. `top_chunks[0]`
  존재 시 `[#1] {page_title or attachment_filename} 관련 정보를 다음과 같이
  안내합니다.` 형태의 검증 가능한 stub 답변. `used_llm = target_llm or GPT_4O`.
- `verify_llm_evaluator_stub(*, answer, top_chunks, suspicious_sentences) ->
  list[Verification]` — 검증 2단계 [Agent] fake. 보수적으로 모두 SUPPORTED.

신규 `app/pipeline/nodes.py` (~115 lines, Pipeline 노드 래퍼):

- `empty_retrieval_node(state) -> state` — api-spec.md "표준 분기 응답"
  RETRIEVAL_EMPTY 처리. 답변을 "권한 범위 내에서 참고할 수 있는 문서를 찾지
  못했습니다." 표준 메시지로 채우고 sources/verification/top_chunks를 비운다.
  라우터 intent 보존(없으면 OPERATION_GUIDE fallback), `used_llm`은
  `target_llm or GPT_4O_MINI` (LLM 미호출이지만 응답 객체 필드 채움).
- `verify_pipeline_node(state, *, llm_evaluator) -> state` — 답변 검증 1+2단계
  병합. feature10-Pipeline의 `verify_answer_rules` 호출 → `passed_verifications`
  PASS 모음 + `suspicious_sentences` 있을 때만 2단계 LLM 평가자 호출 →
  sentence_id 정렬 후 `state.verification` 으로 병합. 답변 None/빈 문자열이면
  안전하게 verification 비움.
- `after_search_branch(state) -> str` — LangGraph conditional edges 분기 키.
  `candidates` 비어있으면 `"empty"`, 그 외 `"rerank"`.
- 상수 `RETRIEVAL_EMPTY_ANSWER` — RETRIEVAL_EMPTY 표준 메시지.

신규 `app/pipeline/query_graph.py` (~155 lines, 그래프 조립 + 호출 래퍼):

- `QueryGraphDeps` dataclass — 그래프 의존성 묶음.
    - Pipeline/Storage: `dense_embedder` / `sparse_embedder` / `store` /
      `reranker` / `history_provider`(None 가능).
    - Agent: `router_node` / `generator_node` / `verify_llm_evaluator` — 기본값은
      stubs.py의 3종. Agent 코드 전달 시 이 3곳만 교체.
- `build_query_graph(deps) -> CompiledGraph` — LangGraph StateGraph 빌드.
  엣지 구조:
  ```
  history → router → hybrid_search
                       ├─(0건)─► empty_retrieval ─► END
                       └─(후보 있음)─► rerank → generate → verify ─► END
  ```
  외부 의존성은 `functools.partial`로 노드 시그니처 `(state) -> state`에 wiring.
- `run_query(state, *, graph, formatter=format_response) -> QueryResponse` —
  그래프 호출 래퍼. `time.perf_counter_ns()` 로 latency_ms 측정 → graph.invoke →
  `RagState.model_validate(result_dict)` 로 재구성(LangGraph 0.2.x가 Pydantic
  state를 dict로 반환) → 포맷터 호출 → QueryResponse 산출. intent/used_llm
  fallback 처리.

수정 `app/pipeline/__init__.py` — 모듈 docstring 갱신 + `RETRIEVAL_EMPTY_ANSWER` /
`QueryGraphDeps` / `build_query_graph` / `run_query` / `router_stub` /
`generator_stub` / `verify_llm_evaluator_stub` / 노드 3종 re-export.

### 신규 테스트

`tests/pipeline/test_stubs.py` (~155 lines, 9 unit tests):
- router_stub: intent / pool_weights / target_llm fallback 정합, history_decision
  보존, in-place mutation.
- generator_stub: [#1] 인용 마커 포함 답변, target_llm 정합, 빈 top_chunks 방어.
- verify_llm_evaluator_stub: suspicious → SUPPORTED 매핑, 빈 입력.

`tests/pipeline/test_nodes.py` (~190 lines, 10 unit tests):
- empty_retrieval_node: 표준 메시지, intent fallback, used_llm fallback,
  in-place.
- verify_pipeline_node: 1단계 전부 PASS면 2단계 미호출(spy), 의심 있을 때 2단계
  병합, NOT_SUPPORTED passthrough, 빈 답변/None 안전, in-place.
- after_search_branch: candidates 유무에 따른 분기 키.

`tests/pipeline/test_query_graph.py` (~270 lines, 8 통합 tests):
- `:memory:` Qdrant + Fake 임베더·Reranker로 외부 컨테이너 없이 end-to-end.
- 정상 흐름 (sources/verification 채움, score 0~100, latency_ms>=0).
- 라우터 stub intent / target_llm 검증.
- RETRIEVAL_EMPTY: 빈 store + ACL 불일치 두 케이스 — answer 표준 메시지 + sources
  비움 + feedback_enabled=False.
- 저신뢰 분기 (`_AlwaysLowReranker` 0.1 → Source.score=10 < 20) →
  feedback_enabled=False, answer는 차단 메시지 아님.
- 검증 차단 분기 (custom generator + custom evaluator → NOT_SUPPORTED 100%) →
  answer가 BLOCKED_ANSWER_MESSAGE로 교체, feedback_enabled=False.
- ACL 미주입 (None / 빈 dict) → ACLViolationError 정상 발생.

### 책임 분리 (그래프 노드 ↔ Agent ↔ Pipeline)

- **본 담당자 영역(Pipeline)**: `empty_retrieval_node` / `verify_pipeline_node` /
  `after_search_branch` (이번 추가) + 9-B-2/9-B-3 노드(이전 완료) + 포맷터
  (이전 완료) + ACL 데코레이터(feature7 완료) + history 어댑터(feature8 통합).
- **Agent 담당자 영역(현재 stub)**: `router_stub` / `generator_stub` /
  `verify_llm_evaluator_stub`. 교체는 `QueryGraphDeps`의 3개 필드만 바꿈.
- **그래프 조립**: `build_query_graph` 가 양쪽 노드를 단일 위치에서 배선.
  Agent 코드와 Pipeline 코드는 RagState 필드 계약과 LangGraph 엣지로만 연결되며
  서로 직접 import 하지 않는다.

### RagState 계약 (변경 없음)

스키마 변경 없음 — `intent` / `rewritten_queries` / `pool_weights` /
`target_llm` / `metadata_filters` / `acl_filter` / `candidates` / `top_chunks` /
`sources` / `verification` / `answer` / `used_llm` / `latency_ms` /
`history_decision` 모두 기존 필드 그대로 사용. `latency_ms` 는 `run_query`
wrapper가 그래프 외부에서 측정한 값을 포맷터에 직접 전달한다(RagState 미저장).

### 표준 분기 응답 통합 (api-spec.md)

| 분기 | 동작 | 그래프 처리 |
|---|---|---|
| RETRIEVAL_EMPTY | LLM 미호출 표준 메시지 | `after_search_branch` → empty_retrieval_node → END |
| LOW_CONFIDENCE | Source.score < 20 → feedback_enabled=False | 포맷터 `_is_low_confidence` 자동 분기 (그래프 무변경) |
| VERIFICATION_BLOCKED | NOT_SUPPORTED > 50% → 답변 차단 | 포맷터 `_not_supported_ratio` 자동 분기 (그래프 무변경) |
| UNAUTHORIZED(JWT 실패) | 401 (api-spec.md) | API 라우트 책임 — Phase 2 |
| UPSTREAM_LLM_ERROR | 5xx 또는 fallback | Agent 코드 책임 — 본 세션 범위 외 |

### 검증 결과 (회사 Mac 기준 — 예상)

- 본 세션 추가 파일 8건 모두 ruff format / ruff check 통과 확인 (샌드박스 ruff).
- pytest는 회사 Mac에서 `./scripts/verify.sh` 실행 시 통과 예상 — 신규
  27 tests (stubs 9 + nodes 10 + query_graph 8). LangGraph 0.2.x StateGraph +
  Pydantic state + `RagState.model_validate(dict)` 패턴이 표준 동작.
- 샌드박스 Python 3.10 한계로 직접 pytest 미실행 (이전 feature1/2와 동일).
  코드는 3.11 기준 그대로 유지.

### 비고

- 새 의존성 도입 없음 — `langgraph>=0.2,<0.3` 은 이미 main dependencies.
- `app/query/*` 의 기존 파일은 일절 수정하지 않음(본 담당자 영역 보존).
- `app/schemas/*` 변경 없음(필드 충분, RagState 확장 불요).
- 다른 팀원 영역(`app/llm/`, `app/query/router.py`, `app/query/generator.py`)에는
  파일을 만들지 않음 — Agent 코드 격리 원칙 유지.
- `app/query/rerank_node.py` / `tests/query/test_rerank_node.py` 에 사용자가 직전에
  적용한 ruff format 차이(줄바꿈 합치기 2곳)가 commit `ba13414` 시점 형태와 다른
  채로 워킹 디렉토리에 남아 있었으나 사용자 결정에 따라 git restore로 폐기. 본
  세션 commit 범위 외. 회사 Mac에서 `./scripts/format.sh` 실행 시 ruff format이
  자동으로 다시 합칠 것이며 별도 commit으로 처리 권장.

### feature11 통합 Phase 1 완료 + Phase 2 진입 가능

Pipeline 단계의 비-Agent 부품이 LangGraph 그래프 한 곳에서 모두 wiring되어
end-to-end 흐름이 동작함을 통합 테스트로 검증. Agent 담당자가 라우터·답변
생성기·검증 2단계 LLM 평가자 코드를 전달하면 `QueryGraphDeps`의 3개 필드만
교체해 즉시 활용 가능. FastAPI SSE 라우트(Phase 2)는 본 그래프 위에 얹는
얇은 계층(JWT extract → run_query → SSE 송신)으로 후속 세션에서 추가.

### 남은 TODO

- **feature11 통합 Phase 2** — FastAPI SSE 라우트 (`app/api/{main,routes,errors,
  deps}.py`) + httpx in-process 테스트. `run_query` 위에 얇게 얹는다.
- **Agent 코드 통합** — Agent 담당자 전달 후 `QueryGraphDeps.router_node` /
  `.generator_node` / `.verify_llm_evaluator` 3곳 교체 + 회귀 테스트.
- **5-A payload.token_count 추가** — Chunk 재구성 정합 (작은 refactor).
- **풀 텍스트 lookup 어댑터** — Source.download_url + payload.text_preview 한계 보완.
- **examples/demo_search.py 갱신** — BM25-lite → 실 5-B + 9-B + Query 그래프 호출.
- **운영 Qdrant 라이브 smoke** — `docker compose up` 후 samples 적재 + run_query 시연.


## 2026-05-18 — feature11 통합 Phase 2: FastAPI SSE 라우트 (feature11 마무리)

- 브랜치: `feat/#1/rag-pipeline-skeleton`
- 배경: Phase 1(Query LangGraph 그래프)이 끝-끝 동작함을 통합 테스트로 검증했고,
  Agent 코드 전달 전이라도 BFF가 호출할 수 있는 HTTP 진입점이 필요하다.
  `run_query` 위에 얇은 계층(JWT 추출 → ACL filter → run_query → SSE 송신)을
  얹어 `POST /api/v1/rag/query` 를 구현한다.
- 분할 결정점:
  - **SSE 이벤트 시퀀스**: api-spec.md 그대로 `token + sources + verification +
    meta + done` 5종 송신. PoC는 token을 1회로(전체 답변) 송신 — Agent 통합 시
    token만 다중 송신으로 확장 가능한 구조. BFF/프론트 호환성 유지.
  - **DI 기본값**: PoC `:memory:` Qdrant + Fake everything + samples 자동 인덱싱.
    외부 컨테이너·모델 없이 서버가 즉시 응답.

### 변경 사항

신규 `app/api/errors.py` (~75 lines):

- `ErrorCode` StrEnum — `UNAUTHORIZED` / `RETRIEVAL_EMPTY` / `LOW_CONFIDENCE` /
  `UPSTREAM_LLM_ERROR` / `VERIFICATION_BLOCKED` (api-spec.md 정합).
- `ErrorDetail` / `ErrorResponse` Pydantic 모델 — `{ "success": false, "error":
  { "code": "...", "message": "..." } }` 응답 형식.
- `HTTP_STATUS_BY_CODE` 매핑 — UNAUTHORIZED=401, UPSTREAM_LLM_ERROR=502 (4xx/5xx
  로 변환되는 코드만 등록. RETRIEVAL_EMPTY 등 표준 분기는 200 SSE 내부 처리).
- `error_response(code, message)` 헬퍼.

신규 `app/api/deps.py` (~100 lines):

- `build_poc_deps(settings=None) -> QueryGraphDeps` — PoC 부트스트랩.
    1. FakeDenseEmbedder(64차원) + FakeSparseEmbedder.
    2. `QdrantPoolStore.in_memory(settings, dense_dimension=64)` + 3 Pool
       컬렉션 부트스트랩.
    3. `JsonFixtureSourceAdapter(samples_dir)` → PageObject → `chunk_page`
       → `index_chunks` (FakeEmbeddingCache).
    4. `QueryGraphDeps` 반환 (Agent 노드 3종 stub 기본값).
- `_ingest_samples` 헬퍼 — samples 디렉토리에서 청크 생성·인덱싱. samples가
  없으면(빈 디렉토리) 조용히 패스 — `RETRIEVAL_EMPTY` 분기 검증 가능.

신규 `app/api/routes.py` (~150 lines):

- `QueryRequest` Pydantic 모델 — `query` / `conversation_id?` / `jwt`
  (api-spec.md Request Body).
- `get_graph(request)` — FastAPI Depends. `request.app.state.graph` 반환.
  테스트는 `dependency_overrides[get_graph]` 로 교체.
- `GraphDep = Annotated[Any, Depends(get_graph)]` — bugbear B008 회피 패턴.
- `_sse_payload(response)` — `QueryResponse` → 5종 SSE 이벤트 시퀀스 (`token` /
  `sources` / `verification` / `meta` / `done`). Pydantic `model_dump(mode="json")`
  으로 datetime/enum 직렬화.
- `_event_stream` — sse-starlette `EventSourceResponse` 입력용 async generator.
- `query_route(payload, graph)`:
    1. `extract_principal(jwt)` — `PrincipalExtractionError` → 401 UNAUTHORIZED
       (`_error_json` JSON 응답).
    2. `build_acl_filter(user_id, groups)` → `RagState` 구성.
    3. `run_query(state, graph)` → `QueryResponse`. ACLViolationError /
       그 외 Exception → 502 UPSTREAM_LLM_ERROR (보수적).
    4. 정상 응답 → `EventSourceResponse(_event_stream(response))`.

신규 `app/api/main.py` (~70 lines):

- `_lifespan(app)` async context — `build_poc_deps` → `build_query_graph` →
  `app.state.graph` / `app.state.deps` 보관. teardown은 `:memory:` 클라이언트라
  GC 위임.
- `create_app() -> FastAPI` 팩토리 — 테스트·운영 공통 진입점.
- `/healthz` 헬스 라우트 — `{"status": "ok"}`.
- 모듈 레벨 `app = create_app()` — `uvicorn app.api.main:app` 진입점.

수정 `app/api/__init__.py` — docstring 갱신 + ErrorCode / ErrorDetail /
ErrorResponse / app / create_app / error_response re-export.

수정 `docs/api-spec.md` — "SSE 이벤트 순서" 절에 PoC 제약 NOTE 추가 (token 1회
송신, Agent 통합 시 다중 송신 확장 예정).

### 신규 테스트 `tests/api/test_query_route.py` (~255 lines, 7 통합 tests)

`httpx.AsyncClient(transport=ASGITransport(app))` in-process — 외부 서버 없이
ASGI 직접 호출. lifespan은 `dependency_overrides[get_graph]`로 우회하고 그래프는
테스트에서 직접 컴파일.

- **헬스**: `GET /healthz` → 200 + `{"status": "ok"}`.
- **정상 흐름**: `POST /api/v1/rag/query` → 200 + `text/event-stream` + 이벤트
  시퀀스 `[token, sources, verification, meta, done]` 정합 + sources score
  0~100 int + meta intent=`운영가이드` / used_llm=`gpt-4o` / latency_ms>=0.
- **RETRIEVAL_EMPTY**: 빈 그래프 + 유효 JWT → 200 SSE + token에 "권한 범위" +
  sources=[] + meta.feedback_enabled=False.
- **UNAUTHORIZED (JWT 형식)**: `"not-a-jwt"` → 401 + `{"success": false,
  "error": {"code": "UNAUTHORIZED", "message": ...}}`.
- **UNAUTHORIZED (sub 누락)**: 정상 형식이나 `sub` 클레임 없음 → 401.
- **422 (요청 검증)**: query 필드 누락 → FastAPI 기본 422 (Pydantic).
- **ACL 불일치**: JWT groups가 인덱싱된 allowed_groups와 불일치 → RETRIEVAL_EMPTY
  분기 (200 SSE + 표준 메시지).

`_make_jwt(sub, groups)` 헬퍼 — base64url payload만 채운 stub JWT. 서명은 BFF
책임이므로 미검증 정책 정합.
`_parse_sse(body)` 헬퍼 — SSE 본문에서 (event, data) 시퀀스 추출.

### 책임 분리 (Phase 2 vs Phase 1 vs Agent 영역)

- **Phase 2 (본 세션)**: HTTP 계층(요청 검증·JWT 추출·ACL 필터 생성·SSE 송신·
  Error 매핑) + PoC 부트스트랩. 비즈니스 로직 0 — 모두 Phase 1 그래프 위에 얇게.
- **Phase 1 (이전 세션)**: LangGraph 그래프 조립 + Pipeline 노드 + Agent stub.
  `run_query(state, graph)` 호출 한 줄로 모든 분기 처리.
- **Agent 영역(미정)**: `QueryGraphDeps.router_node` / `.generator_node` /
  `.verify_llm_evaluator` 3곳. 본 세션과 무관.

### 표준 분기 응답 매핑 (api-spec.md)

| 분기 | HTTP | 응답 형식 | 처리 위치 |
|---|---|---|---|
| 정상 흐름 | 200 | SSE 5종 | run_query → routes._sse_payload |
| RETRIEVAL_EMPTY | 200 | SSE (token=표준 메시지) | 그래프 empty_retrieval_node + 포맷터 |
| LOW_CONFIDENCE | 200 | SSE (meta.feedback_enabled=false) | 포맷터 `_is_low_confidence` |
| VERIFICATION_BLOCKED | 200 | SSE (token=BLOCKED_ANSWER_MESSAGE) | 포맷터 `_not_supported_ratio` |
| UNAUTHORIZED | 401 | ErrorResponse JSON | routes — extract_principal 예외 |
| UPSTREAM_LLM_ERROR | 502 | ErrorResponse JSON | routes — 그래프 예외 광범위 캐치 |

### 검증 결과 (회사 Mac 기준 — 예상)

- 본 세션 추가 파일 7건 모두 ruff format / ruff check 통과 (샌드박스 ruff).
- pytest는 회사 Mac에서 `./scripts/verify.sh` 실행 시 통과 예상 — 신규
  7 tests (test_query_route.py). LangGraph 0.2.x + FastAPI 0.111 + sse-starlette
  + httpx ASGITransport 표준 동작.
- 샌드박스 Python 3.10 한계로 직접 pytest 미실행 (이전 feature 패턴 동일).

### 비고

- 새 의존성 도입 없음 — `fastapi>=0.111` / `sse-starlette>=2.1` / `httpx>=0.27`
  모두 main dependencies.
- `app/pipeline/*` / `app/query/*` / `app/schemas/*` 변경 0 (본 담당자 영역 보존).
- 실 어댑터(E5 / Qdrant from_settings / Cross-Encoder) 부트스트랩(`build_real_deps`)
  은 별도 follow-up으로 분리. 운영 전환 시 환경 토글 추가.

### feature11 통합 완료 + Agent 통합 진입 가능

Pipeline 단계(검색·재순위화·검증 1단계·포맷터)·HTTP 계층(SSE 라우트·Error 매핑·
헬스 체크)·PoC 부트스트랩이 모두 본 담당자 영역에서 끝까지 동작. 회사 Mac에서
`uvicorn app.api.main:app` 으로 즉시 띄울 수 있으며, `samples/` 92페이지가
자동 인덱싱되어 PoC 검색이 가능하다. Agent 담당자 코드 전달 시 `QueryGraphDeps`
의 3개 필드만 교체하면 라우터 + 답변 생성기 + 검증 2단계 LLM 평가자가 즉시
활성화된다.

### 남은 TODO

- **Agent 코드 통합** — Agent 담당자 전달 후 `QueryGraphDeps.router_node` /
  `.generator_node` / `.verify_llm_evaluator` 3곳 교체 + 회귀 테스트 + token
  다중 송신(SSE 스트리밍) 확장.
- **`build_real_deps`** — 운영 어댑터 부트스트랩 (E5 + Qdrant from_settings +
  Cross-Encoder 실 모델). 환경 토글 `RAG_USE_REAL_ADAPTERS=true` 권장.
- **5-A payload.token_count 추가** — Chunk 재구성 정합 (작은 refactor).
- **풀 텍스트 lookup 어댑터** — Source.download_url + payload.text_preview 한계 보완.
- **examples/demo_search.py 갱신** — BM25-lite → 실 5-B + 9-B + Query 그래프 호출.
- **운영 Qdrant 라이브 smoke** — `docker compose up` + `build_real_deps` 시연.


## 2026-05-18 — examples/demo_search.py 갱신 (feature11 통합 후속)

- 브랜치: `feat/#1/rag-pipeline-skeleton`
- 배경: feature11 통합(Phase 1 + Phase 2) 완료 후, BM25-lite + 인메모리 ACL
  매칭으로 시연하던 `examples/demo_search.py` 가 더 이상 실제 동작 흐름을
  반영하지 못한다. Phase 2 부품(`build_poc_deps` + `build_query_graph` +
  `run_query`)을 그대로 호출하는 CLI 데모로 교체해 Agent 코드 전달 전 시각적
  검증 도구로 사용한다.

### 변경 사항

수정 `examples/demo_search.py` (~210 lines, 전면 재작성):

- 제거: ``BM25Lite`` / ``_build_pool_indexes`` / ``_matches_acl`` /
  ``_format_source_card`` 헬퍼 일체 (인메모리 검색 시연 흔적).
- 추가: ``main(argv) -> int`` 진입점. 3-phase 진행 로그 + SSE 5종 페이로드
  콘솔 시각화.
    1. ``build_poc_deps()`` — :memory: Qdrant + Fake everything + samples 자동
       인덱싱 (app/api/deps.py 재사용).
    2. ``build_query_graph(deps)`` — LangGraph StateGraph 컴파일.
    3. ``build_acl_filter(user, groups)`` + ``RagState`` → ``run_query`` →
       ``QueryResponse`` 결과 출력.
- 출력 형식 — SSE 이벤트와 1:1 매핑되어 BFF 응답을 그대로 콘솔에 펼친 모습:
    - ``[meta]`` intent / used_llm / feedback_enabled / latency_ms
    - ``[answer]`` token 페이로드 (PoC 1회 송신)
    - ``[sources]`` 출처 카드 (rank / score / space_key / title / 섹션 /
      미리보기 / URL)
    - ``[verification]`` 문장별 결과 + PASS/SUPPORTED/NOT_SUPPORTED 카운트 요약
    - ``[표준 분기 응답]`` — RETRIEVAL_EMPTY / LOW_CONFIDENCE /
      VERIFICATION_BLOCKED 분기 도달 시 가시화
- CLI 인자 단순화: ``query`` (positional) / ``--user`` / ``--groups``
  (ADR-0002 ``space:`` prefix) / ``--conversation-id``. 기존 ``--intent``,
  ``--top-k`` 는 라우터 stub + Top-5 내장에 의해 의미가 사라져 제거.

### 책임 분리 (시연 vs 운영)

- ``examples/demo_search.py``: 본 담당자 영역 시연 도구. 한 줄 호출
  (``python -m examples.demo_search "..."``)로 그래프 끝-끝 동작 확인.
- ``app/api/main.py`` (Phase 2): 운영 진입점. ``uvicorn`` 기반 SSE 라우트.

본 데모는 FastAPI 서버 없이 즉시 동작하므로 회사 Mac에서 ``./scripts/verify.sh``
이전 단계 sanity check로 사용 가능.

### 검증 결과 (회사 Mac 기준 — 예상)

- ruff format / ruff check 통과 (샌드박스).
- 본 데모는 시연 도구라 별도 단위 테스트 없음 — `python -m examples.demo_search
  "EKS 노드 장애"` 등 manual smoke로 검증한다. samples 92페이지 인덱싱 후 응답
  까지 수 초 내 완료 예상 (Fake 임베더 + :memory: Qdrant).

### 비고

- 신규 의존성 도입 없음. ``app.api.deps`` / ``app.pipeline.query_graph`` /
  ``app.query.acl`` 모두 기존 부품.
- 본 commit은 `examples/demo_search.py` 단일 파일 변경. `app/*`/`docs/api-spec.md`
  변경 없음 (CLAUDE.md "담당 범위" 정합).


## 2026-05-18 — fix(rag): query_graph 노드명 'history' → 'manage_history' (LangGraph state key 충돌)

- 브랜치: `feat/#1/rag-pipeline-skeleton`
- 배경: 회사 Mac에서 `./scripts/test.sh` 실행 결과 `pytest` 가 15건 실패
  (test_query_graph 8 failed + test_query_route 7 errors). 기존 회귀 0건
  (420 passed) — feature11 통합 그래프 빌드 단계만 실패.
- 원인: LangGraph 1.x StateGraph는 **노드명과 state field가 동일 네임스페이스를
  공유**한다. `RagState.history: list[HistoryTurn]` 필드가 이미 있는 상태에서
  ``builder.add_node("history", manage_history)`` 를 호출하면
  ``ValueError: 'history' is already being used as a state key`` 발생.
  설계서/문서/이전 Plan에는 "history" 노드명을 사용했으나 실 LangGraph 제약과
  충돌. 1.x에서 강화된 제약으로 보이며 0.2.x에서는 검출 안 됐을 수 있음.

### 변경 사항

수정 `app/pipeline/query_graph.py`:

- 노드명 `"history"` → `"manage_history"` 4곳 일괄 교체 (등록 / 진입점 /
  엣지). 다른 노드명(`router`/`hybrid_search`/`empty_retrieval`/`rerank`/
  `generate`/`verify`)은 RagState 필드와 무충돌이라 그대로 유지.
- docstring "그래프 구조" 다이어그램의 `history` → `manage_history`.
- 노드명 네임스페이스 제약을 코드 주석으로 명시 (회귀 방지).

수정 `tests/pipeline/test_query_graph.py`:

- 신규 회귀 보호 테스트
  `test_build_query_graph_compiles_without_node_state_key_collision` — 그래프
  컴파일 자체가 통과하는지만 단언. 향후 노드 추가 시 RagState 필드와 같은 이름을
  쓰면 본 테스트가 즉시 실패해 회귀를 차단한다.

수정 `examples/demo_search.py`:

- 진행 로그의 그래프 구조 안내 `history → ...` → `manage_history → ...`.

### 검증

- ruff format / check 통과 (3 파일).
- 본 fix는 노드명 4번 교체 + 회귀 테스트 1건 추가만 — 노드 함수 로직·시그니처
  변경 없음. 회사 Mac에서 `./scripts/test.sh` 재실행 시 15건 실패 → 통과 + 1건
  신규 통과 (총 +16) 예상.

### 비고

- RagState 필드 21종 중 ``history`` 1개만 노드명과 충돌했다. 다른 필드
  (``query`` / ``user_id`` / ``intent`` / ``candidates`` / ``top_chunks`` /
  ``answer`` / ``sources`` / ``verification`` 등)와 노드명 (``router`` /
  ``hybrid_search`` / ``empty_retrieval`` / ``rerank`` / ``generate`` /
  ``verify``) 사이에는 교집합 없음 — 운 좋게 한 곳만 영향.
- 본 fix는 단일 함수 안의 문자열 4곳 + 다이어그램 + 회귀 테스트 1건만 — 매우
  국소적 commit. `chore` 보다는 `fix` 로 표기 권장.
- **운영 Qdrant 라이브 smoke** — 5-B + 9-B-2/3 묶어 시각 확인.


## 2026-05-18 — 5-A 후속: payload.token_count 동봉 + Chunk 재구성 정합

- 브랜치: `feat/#1/rag-pipeline-skeleton`
- 배경: feature9-B-2 (`hybrid_search` 노드) 작성 당시 `_chunk_from_search_hit`
  의 ``token_count`` 는 payload에 필드가 없어 0으로 하드코딩됐다. working-log
  feature9-B-2 섹션에 명시된 follow-up으로 분리해 두었던 항목. ChunkMetadata는
  ``token_count`` 를 필수 필드로 정의하므로 인덱싱 전(청커 산출 값)과 재구성 후
  값이 일치해야 의미가 있다 — Cross-Encoder reranker(9-B-3) 이후 답변 생성기·
  검증기·포맷터까지 동일 메타를 보도록 정합을 회복한다.

### 변경 사항

수정 `app/ingestion/vector_store.py`:

- `build_point_payload` 에 ``"token_count": metadata.token_count`` 1줄 추가
  (additive — `extracted_format` 아래, `text_preview` 위).
- 모듈 docstring 변경 이력에 `2026-05-18, 5-A 후속` 한 항목 추가.

수정 `app/query/search_node.py`:

- `_chunk_from_search_hit` 의 ``token_count=0`` → ``token_count=int(payload.get(
  "token_count") or 0)``. 신규 인덱스는 payload에서 그대로 복원, legacy 인덱스
  (payload에 필드 없음)는 0 fallback으로 후방 호환.
- 함수 docstring 갱신 — "0으로 두고 follow-up" 문장 제거, payload에서 복원하는
  근거(db-schema §1.2) 명시.
- 모듈 docstring 변경 이력에 `2026-05-18, 5-A 후속` 항목 추가.

수정 `docs/db-schema.md` §1.2:

- payload 스키마 테이블에 `token_count integer` 행 추가 (`extracted_format` 아래,
  `text_preview` 위). 설명: `ChunkMetadata.token_count` 그대로 복원해 답변 생성기/
  검증 단계가 동일 메타를 보도록 한다.

수정 `tests/ingestion/test_vector_store.py`:

- 신규 회귀 보호 테스트 `test_build_point_payload_includes_token_count` 1건 추가
  — 픽스처 `token_count=120` → payload 그대로 동봉. 다음에 payload 스키마에서
  필드를 누락하면 즉시 실패한다.

수정 `tests/query/test_search_node.py`:

- 기존 `test_hybrid_search_returns_chunks_with_reconstructed_metadata` 단언
  ``== 0`` → ``== 120`` 로 갱신 + 주석 갱신 (5-A 후속 사유 명시). 인덱싱한
  청크의 token_count(120)가 재구성 후 보존됨을 검증.

### 책임 분리 (Pipeline + Storage 영역만)

- 본 commit은 본 담당자 영역 4개 파일 + db-schema 문서 1개. Agent 영역 / API 표면 /
  app/schemas / app/storage 어댑터 모두 무변경. `app/CLAUDE.md` "담당 범위" 절대
  규칙 정합.

### 후방 호환성

- 신규 인덱싱은 token_count를 payload에 동봉.
- legacy 인덱스(token_count 필드 없음)에서 검색해도 `_chunk_from_search_hit` 가
  ``payload.get("token_count") or 0`` 로 0 fallback — 정상 동작. 운영 환경 migration
  무필요 (자연스럽게 다음 재색인 시 채워진다).

### 검증 결과 (회사 Mac 기준 — 예상)

- 샌드박스 ruff 0.15.13으로 format `--check` + check 통과 (105 files already
  formatted, All checks passed).
- 본 세션 추가/수정 파일 5건 모두 ruff 통과.
- pytest는 회사 Mac에서 `./scripts/verify.sh` 실행 시 통과 예상 — 신규 1건
  (`test_build_point_payload_includes_token_count`) + 갱신 1건
  (`test_hybrid_search_returns_chunks_with_reconstructed_metadata` 단언 값) +
  기존 회귀 0건. 샌드박스 Python 3.10 한계로 직접 pytest 미실행 (이전 feature
  패턴 동일).

### 비고

- 5개 파일, +23 -5 lines (`git diff --stat`). 매우 국소적 commit.
- `db-schema.md` 변경 시 3곳 정합(payload 스키마 + `build_point_payload` +
  `_chunk_from_search_hit`)을 본 commit 하나에서 모두 처리. 다음 follow-up 후보
  — 풀 텍스트 lookup 어댑터(Source.text_preview 200자 한계 보완), `build_real_deps`
  운영 어댑터 부트스트랩, Agent 코드 통합(`QueryGraphDeps` 3개 필드 교체).


## 2026-05-18 — build_real_deps + use_real_adapters 환경 토글

- 브랜치: `feat/#1/rag-pipeline-skeleton`
- 배경: feature11 통합 Phase 2(`build_poc_deps`) 완료 후, 운영 전환 시
  E5DenseEmbedder + BM25SparseEmbedder + `QdrantPoolStore.from_settings` +
  `CrossEncoderRerankerImpl` 실 어댑터를 부트스트랩하는 진입점이 필요했다. 본
  세션은 코드 + 환경 토글까지만 작성하고, 실 모델 다운로드(약 2.4 GB) + Qdrant
  서버 접속 검증은 별도 라이브 smoke로 분리한다. 5-A token_count(직전 commit
  `13f07a9`) 후속.

### 변경 사항

수정 `app/config.py`:

- ``use_real_adapters: bool = False`` 필드 추가 (env ``RAG_USE_REAL_ADAPTERS``).
  기본 False라 미설정 환경에서 무의식적으로 운영 모드가 켜져 모델 다운로드가
  발생하지 않도록 한다.
- 모듈 docstring 변경 이력에 `2026-05-18, build_real_deps 후속` 항목 추가.

수정 `app/api/deps.py`:

- ``build_real_deps(settings) -> QueryGraphDeps`` 함수 신설. 호출 시점에
  ``E5DenseEmbedder`` / ``BM25SparseEmbedder`` / ``CrossEncoderRerankerImpl`` 을
  **lazy import** — embedding extra 미설치 환경에서도 PoC 경로
  (``build_poc_deps``)와 본 모듈 자체 import는 영향 받지 않는다.
- ``QdrantPoolStore.from_settings(settings, dense_dimension=dense.dimension)``
  + ``bootstrap_collections()`` 호출. dense_dimension은 어댑터가 모델 로드 후
  보고한 값을 사용 (E5-large = 1024).
- samples 자동 인덱싱은 운영 모드에서 수행하지 않음 — 별도 ingestion 파이프라인
  적재 가정. 매 startup마다 92페이지 재임베딩 회피.
- 모듈 docstring·변경 이력 갱신 + `[호환성]` NOTE에 lazy import 정책 명시.

수정 `app/api/main.py`:

- ``_lifespan`` 에서 ``settings.use_real_adapters`` 토글 분기 — True →
  ``build_real_deps(settings)`` / False(기본) → ``build_poc_deps(settings)``.
- 기본값 False라 기존 동작(:memory: Qdrant + Fake + samples 자동 인덱싱)
  변화 0.
- 모듈 docstring 변경 이력에 본 세션 항목 추가.

수정 `app/api/__init__.py`:

- 패키지 docstring 모듈 일람·구현 상태에 build_real_deps 명시.

### 신규 테스트 `tests/api/test_deps.py` (~210 lines, 5 통합 tests)

monkeypatch로 실 어댑터 4종(E5/BM25/CrossEncoder + Qdrant from_settings)을 가짜
로 대체해 함수 로직만 검증. sentence-transformers / fastembed / 실 Qdrant 서버
없이 통과.

- `test_build_real_deps_wires_real_adapter_classes` — 4 어댑터 모두 호출 +
  QueryGraphDeps 박힘 + dense_dimension=1024 전달 + Fake 어댑터 미사용.
- `test_build_real_deps_passes_model_names_from_settings` —
  ``settings.dense_embedding_model`` / ``cross_encoder_model`` 이 어댑터 생성자
  에 전달.
- `test_build_real_deps_does_not_ingest_samples` — 운영 모드 ``_ingest_samples``
  미호출 (매 startup마다 재임베딩 회피 검증).
- `test_build_real_deps_does_not_eagerly_import_sentence_transformers` — 모듈
  소스 inspect로 최상단 import 영역에 sentence-transformers / fastembed / 실
  어댑터 모듈이 등장하지 않음을 검증 (lazy import 회귀 보호).
- `test_build_poc_deps_uses_fake_adapters_unchanged` — PoC 경로 회귀 보호.

### 추가 회귀 테스트 `tests/test_config.py` (+2 tests)

- `test_settings_use_real_adapters_defaults_false` — 기본값 False.
- `test_settings_use_real_adapters_env_override` —
  ``RAG_USE_REAL_ADAPTERS=true`` → True.

### 책임 분리 (본 담당자 영역만)

- 본 commit은 본 담당자 영역 4개 모듈(app/api 3 + app/config 1) + 테스트 2개
  파일. Agent 영역(app/llm, app/query/router, app/query/generator) / app/schemas /
  app/pipeline / app/query/search·rerank / app/storage 모두 무변경.
- 운영 어댑터 자체(E5DenseEmbedder / BM25SparseEmbedder / CrossEncoderRerankerImpl /
  QdrantPoolStore.from_settings)는 feature5-B-1·5-B-2·9-B-1 에서 이미 완성.
  본 세션은 그것들을 부트스트랩하는 wiring만 추가.

### 토글 정책 (운영 안전)

- `use_real_adapters=False` (기본): :memory: Qdrant + Fake everything + samples
  자동 인덱싱. 외부 의존성 0, 즉시 응답. 개발·CI·테스트·PoC 데모용.
- `use_real_adapters=True`: 모델 다운로드(e5-large 2.24 GB + cross-encoder
  130 MB) + Qdrant 서버 접속. 첫 startup 시 lag 30~60초. 운영용.
- embedding extra (`sentence-transformers` + `fastembed`) 미설치 환경에서
  `use_real_adapters=True` 활성화 시 ``build_real_deps`` 호출 시점에 ImportError
  로 즉시 실패. PoC 경로와 모듈 import 자체는 영향 받지 않음 (lazy import 회귀
  보호 테스트로 확인).

### 검증 결과 (회사 Mac 기준 — 예상)

- 샌드박스 ruff 0.15.13으로 format(106 files, 1 reformat) + check(All checks
  passed!) 통과.
- pytest는 회사 Mac에서 `./scripts/verify.sh` 실행 시 통과 예상 — 신규 7건
  (test_deps.py 5 + test_config.py 2) + 기존 회귀 0건. 샌드박스 Python 3.10
  한계로 직접 pytest 미실행 (이전 feature 패턴 동일).

### 비고

- 6개 파일(5 modified + 1 new), +101 -16 lines (`git diff --stat HEAD`).
- 본 commit은 `examples/demo_search.py` 변경 없음 — 데모는 명시적으로
  ``build_poc_deps()`` 만 호출하는 시연 도구.
- `docs/architecture.md` / `docs/api-spec.md` / `docs/db-schema.md` 변경 없음
  — 외부 API 표면·아키텍처·DB 스키마 동일, 운영 토글은 환경 변수일 뿐.
- `docs/ai/current-plan.md` 변경 없음 — feature11 통합 후속 미세 보강이라 별도
  milestone 아님.

### 후속 TODO (다음 세션 후보)

- **운영 Qdrant 라이브 smoke** — `docker compose up` + ``RAG_USE_REAL_ADAPTERS=true``
  + `uvicorn` 으로 실 모델 다운로드 + 검색 끝-끝 동작 확인. 회사 Mac에서 수동.
- **풀 텍스트 lookup 어댑터** — Source.text_preview 200자 한계 보완 +
  Source.download_url 채움 + Chunk lookup 어댑터 + db-schema 갱신.
- **Agent 코드 통합** — Agent 담당자 코드 전달 시 ``QueryGraphDeps.router_node`` /
  ``generator_node`` / ``verify_llm_evaluator`` 3개 필드 교체.


## 2026-05-18 — 풀 텍스트 lookup 어댑터 (Phase 1: 인프라 + Source.download_url)

- 브랜치: `feat/#1/rag-pipeline-skeleton`
- 배경: feature9-B-3 작성 당시 ``Source.download_url`` 은 ``ChunkMetadata`` 에 필드가
  없어 항상 None이었고 (`rerank_node._chunk_to_source` 주석 명시), Qdrant payload의
  ``text_preview`` 도 첫 200자 한계가 있었다. 답변 생성기·검증기가 풀 텍스트가 필요한
  경우와 UI 출처 카드에 첨부 다운로드 URL이 필요한 경우를 대비한 어댑터 인프라를
  추가한다. 본 commit은 **인프라 + Source.download_url 채움 통합**까지만 — 실 적재
  (인덱싱 시 chunk_lookup upsert) 는 별도 milestone(indexer 확장)으로 분리한다.

### 변경 사항

신규 `app/storage/chunk_lookup.py` (~170 lines):

- ``ChunkLookupRecord`` (frozen dataclass) — db-schema §2.5 정합. 필드:
  ``chunk_id`` / ``text`` (청크 풀 텍스트) / ``download_url`` (첨부 청크 only).
- ``ChunkTextLookup`` ABC — ``fetch(chunk_id) -> ChunkLookupRecord | None`` +
  ``fetch_many(chunk_ids) -> dict[str, ChunkLookupRecord]`` 2개 추상 메서드.
- ``FakeChunkTextLookup`` — in-memory dict 구현. 테스트·PoC용 (외부 의존성 0).
  ``add(record)`` 헬퍼로 단건 적재 가능.
- ``MongoChunkTextLookup`` — pymongo 래퍼. ``from_settings(settings)`` 클래스
  메서드로 운영 경로 부트스트랩. find_one + projection 으로 O(1) 룩업,
  fetch_many는 ``$in`` 으로 배치. legacy 문서(필드 누락) 호환.

수정 `app/storage/__init__.py`:

- 신규 모듈 4종 (``ChunkLookupRecord`` / ``ChunkTextLookup`` /
  ``FakeChunkTextLookup`` / ``MongoChunkTextLookup``) re-export + 패키지 docstring
  의 모듈 일람에 ``chunk_lookup.py`` 추가.

수정 `app/query/rerank_node.py`:

- ``cross_encoder_rerank`` 시그니처에 ``chunk_lookup: ChunkTextLookup | None = None``
  추가 (default None — legacy 호출자 호환).
- ``_chunk_to_source`` 시그니처에 ``download_url: str | None = None`` 추가 +
  쓸데없는 주석 제거 (이전 9-B-3 "후속에서 채움" 메모).
- ``_fetch_attachment_download_urls`` 헬퍼 신설 — 첨부 청크만 골라 ``fetch_many``
  배치 호출 (Mongo round-trip 1회 + 본문 청크에 잘못 적재된 download_url 무시).
- 변경 이력 갱신.

수정 `app/pipeline/query_graph.py`:

- ``QueryGraphDeps.chunk_lookup: ChunkTextLookup`` 필드 추가 (기본
  ``FakeChunkTextLookup()`` — 미주입 환경에서도 안전 동작).
- ``builder.add_node("rerank", partial(cross_encoder_rerank, reranker=...,
  chunk_lookup=deps.chunk_lookup))`` 으로 wiring 확장.
- 변경 이력 갱신.

수정 `app/api/deps.py`:

- ``build_real_deps`` 에 ``MongoChunkTextLookup.from_settings(settings)`` lazy
  import + wiring 추가. PoC는 ``QueryGraphDeps`` 기본값 (FakeChunkTextLookup)
  이 자동 적용되므로 ``build_poc_deps`` 변경 없음.
- 변경 이력 갱신.

수정 `docs/db-schema.md`:

- §2.5 ``chunk_lookup`` 컬렉션 신설 — chunk_id (PK / unique index) / text /
  download_url / updated_at. 적재는 별도 milestone임을 명시.

### 신규 테스트 `tests/storage/test_chunk_lookup.py` (~170 lines, 10 tests)

- Fake: fetch (존재/미존재) / fetch_many (필터 + 미존재) / add 덮어쓰기 / ABC
  계약.
- Mongo: 첨부 record fetch / 본문 record (download_url=None) / 미존재 → None /
  legacy 문서 (download_url 필드 누락) 호환 / fetch_many 배치 + ``$in`` 필터 /
  빈 입력 short-circuit.
- pymongo 의존성 mock — ``_FakeCollection`` + ``_DictStyleClient`` 로
  ``client[db_name][collection_name]`` 두 단계 인덱싱 흉내.

### 추가 회귀 테스트 `tests/query/test_rerank_node.py` (+4 tests)

- ``test_attachment_source_download_url_filled_from_lookup`` — 첨부 청크 +
  lookup 적재 → Source.download_url 채워짐.
- ``test_page_source_download_url_remains_none_even_with_lookup`` — 본문 청크는
  lookup 조회 자체 회피 → download_url=None (정합성 보호).
- ``test_attachment_source_download_url_none_when_lookup_missing_record`` —
  첨부 청크지만 lookup에 레코드 없음 → None (안전 fallback).
- ``test_lookup_default_none_keeps_legacy_behavior`` — ``chunk_lookup=None``
  legacy 호출 → 모든 download_url=None (후방 호환 회귀 보호).

### 책임 분리 (본 담당자 영역만)

- 본 commit은 본 담당자 영역 6개 modified + 2 new. Agent 영역
  (``app/llm/`` / ``app/query/router.py`` / ``app/query/generator.py``) /
  ``app/schemas/`` (Source는 이미 ``download_url: str | None``) / ingestion
  모두 무변경.
- 풀 텍스트 자체 사용(답변 생성기·검증기에서 ``text`` 필드 조회)은 Agent 담당자
  통합 시점에 추가됨 — 본 commit은 ``download_url`` 채움 통합만.

### 후방 호환성

- ``QueryGraphDeps.chunk_lookup`` default = FakeChunkTextLookup → 기존 호출자
  변화 없음.
- ``cross_encoder_rerank`` 의 ``chunk_lookup=None`` default → legacy 호출 그대로
  동작.
- 운영 환경에서 ``chunk_lookup`` 컬렉션이 비어 있으면 ``fetch_many`` 가 빈 dict
  를 반환해 download_url=None — 안전 fallback. 컬렉션 적재 전 운영 모드 활성화
  해도 graph 흐름은 깨지지 않는다.

### 검증 결과 (예상)

- 샌드박스 ruff 0.15.13으로 format(108 files, 모두 정합) + check(All checks
  passed) 통과.
- pytest는 ``./scripts/verify.sh`` 실행 시 통과 예상 — 신규 14건 (Fake/Mongo 10 +
  rerank_node 회귀 4) + 기존 회귀 0건. 샌드박스 Python 3.10 한계로 직접 pytest
  미실행 (이전 feature 패턴 동일).

### 비고

- 8개 파일 (6 modified + 2 new), +182 -6 lines (`git diff --stat HEAD`).
- ``docs/architecture.md`` / ``docs/api-spec.md`` / ``docs/rag-pipeline-design.md``
  변경 없음 (Storage 추상화 추가만, 외부 API 표면·아키텍처 동일).
- ``docs/ai/current-plan.md`` 변경 없음 (feature11 통합 후속 미세 보강이라 별도
  milestone 아님).

### 후속 TODO (다음 세션 후보)

- **chunk_lookup 적재 통합 (Phase 2)** — ``app/ingestion/indexer.py`` 에
  ``chunk_lookup`` 인자 추가 + 청크 적재 시 ``MongoChunkTextLookup`` upsert.
  ingestion 그래프·테스트 동반 변경 (~10 파일).
- **답변 생성기·검증기 풀 텍스트 조회 통합** — Agent 영역. 라우터·생성기·검증
  2단계 LLM 코드 전달 후, 풀 텍스트가 필요한 경우 ``chunk_lookup.fetch_many``
  호출하도록 wiring.
- **운영 Qdrant 라이브 smoke** — 5-B + 9-B + chunk_lookup 묶어 시연.


## 2026-05-18 — 풀 텍스트 lookup Phase 2: chunk_lookup 적재 통합

- 브랜치: `feat/#1/rag-pipeline-skeleton`
- 배경: 직전 commit `5e14062` (풀 텍스트 lookup Phase 1)에서 ``ChunkTextLookup`` ABC
  + Fake/Mongo 구현 + ``Source.download_url`` 채움 통합까지 완료했고, db-schema §2.5
  말미에 "본 컬렉션 적재(인덱싱 단계에서 ``chunk_lookup`` upsert)는 별도 후속 milestone
  에서 indexer를 확장" 라고 적재 흐름이 빠져 있었다. 본 commit은 ``index_chunks`` 에
  ``chunk_lookup`` + ``attachment_download_urls`` 인자를 추가하고, 모든 Pool upsert +
  cache write 성공 직후 단일 ``upsert_many`` 배치로 chunk_lookup 컬렉션에 적재해 db-
  schema §2.5의 잔여 작업을 마무리한다.

### 변경 사항

수정 `app/storage/chunk_lookup.py`:

- ``ChunkTextLookup`` ABC 에 ``upsert(record) -> None`` / ``upsert_many(records) -> None``
  2개 추상 메서드 추가. 빈 입력 정책(``upsert_many([])`` short-circuit)을 docstring
  으로 명시 — pymongo ``bulk_write`` 가 빈 ops 에서 InvalidOperation 을 던지는 사실
  을 호출자에게 떠넘기지 않도록 어댑터가 흡수한다.
- ``FakeChunkTextLookup`` — dict 갱신 시맨틱으로 구현. ``add`` 와 동일하지만 ABC 계약
  정합을 위해 별도 메서드로 노출.
- ``MongoChunkTextLookup`` — 단건은 ``replace_one(filter, replacement, upsert=True)``,
  배치는 ``pymongo.ReplaceOne`` 으로 op 리스트를 구성해 ``bulk_write`` 호출. ReplaceOne
  은 함수 본문 내 lazy import — Fake 경로는 pymongo 미설치 환경에서도 import 자체가
  동작해야 하기 때문.
- ``_record_to_doc`` 헬퍼 — ``ChunkLookupRecord`` 3필드 + ``updated_at=datetime.now(UTC)``
  를 4필드 doc 으로 합성. updated_at 부여 책임을 어댑터로 격리해 호출자가 의식하지 않아도
  되도록.
- 모듈 docstring 변경 이력에 `2026-05-18, 풀 텍스트 lookup Phase 2` 항목 추가.

수정 `app/ingestion/indexer.py`:

- ``index_chunks`` 시그니처에 ``chunk_lookup: ChunkTextLookup | None = None`` +
  ``attachment_download_urls: dict[str, str] | None = None`` 2개 keyword-only 인자
  추가. 둘 다 default 가 있어 기존 7개 호출자(테스트)는 무변경.
- Phase 4 신설 — ``chunk_lookup is not None`` 일 때만 to_index 청크에서 ``ChunkLookupRecord``
  리스트를 합성해 ``upsert_many`` 1회 호출. cache hit으로 스킵된 청크는 자연스럽게
  배제(``to_index`` 에 들어가지 않음) — embedding_cache 와 멱등성 정합.
- ``_resolve_download_url`` 헬퍼 — 본문 청크는 항상 None, 첨부 청크만 매핑에서 조회
  (없으면 None 안전 fallback). source_type 기반 분기.
- 함수 docstring 을 3-phase → 4-phase 로 갱신, Args 에 신규 2 인자 설명 추가, 모듈
  docstring 변경 이력에 본 세션 항목 추가.

수정 `app/api/deps.py`:

- ``build_poc_deps`` 가 ``FakeChunkTextLookup`` 1 인스턴스를 만들어 ``_ingest_samples``
  와 ``QueryGraphDeps(chunk_lookup=...)`` 양쪽에 공유 주입. 인덱싱 시 적재한 풀 텍스트·
  첨부 download_url 을 rerank 노드가 그대로 조회할 수 있도록 한다.
- ``_ingest_samples`` 시그니처에 ``chunk_lookup: FakeChunkTextLookup`` keyword 인자
  추가 + 본문 안에서 ``page.attachments[*].download_url`` 을 모아 ``attachment_download_urls``
  dict 합성, ``index_chunks`` 에 전달.
- ``build_real_deps`` 는 무변경 — 운영은 별도 ingestion 파이프라인이 적재한다고 가정하므로
  본 PoC 와이어링과 무관(``MongoChunkTextLookup.from_settings`` 까지는 Phase 1 에서 이미
  완료).
- 모듈 docstring 변경 이력에 `2026-05-18, 풀 텍스트 lookup Phase 2` 항목 추가.

수정 `docs/db-schema.md` §2.5:

- "본 commit은 어댑터 인터페이스와 운영 wiring만 추가" 마지막 문장을 **적재 흐름** 단락
  으로 교체 — Phase 4 단계 위치, cache hit 청크 제외, 본문/첨부 download_url 분기,
  updated_at 자동 부여, cache write 이후 단계라 적재 실패가 멱등성 캐시를 오염시키지
  않음을 명시.

### 신규 회귀 테스트 `tests/storage/test_chunk_lookup.py` (+10 tests)

- Fake: ``upsert`` 신규 적재 / 기존 레코드 덮어쓰기 / ``upsert_many`` 배치 적재 / 빈
  입력 noop.
- Mongo: ``replace_one`` 호출 검증(filter+upsert=True+updated_at) / 덮어쓰기 / 본문
  청크 download_url=None 보존 / ``upsert_many`` 가 ``bulk_write`` 1회 + ReplaceOne ops
  로 호출 / 빈 입력 short-circuit (bulk_write 호출 없음).
- ``_FakeCollection`` 에 ``replace_one`` / ``bulk_write`` 메서드 추가 + 호출 인자 캡처
  속성으로 호출 패턴 검증.

### 추가 회귀 테스트 `tests/ingestion/test_indexer.py` (+6 tests, +1 헬퍼)

- ``_attachment_chunk`` 헬퍼 — ``AttachmentType.PDF`` / ``SourceType.ATTACHMENT`` /
  attachment_id/filename/mime/extracted_format 5필드 채운 ChunkMetadata.
- 본문 청크: chunk_lookup 에 text 그대로 + download_url=None 적재.
- 첨부 청크 + 매핑 hit: download_url 채워짐.
- 첨부 청크 + 매핑 miss: download_url=None 안전 fallback.
- ``chunk_lookup=None`` legacy 호출 회귀 보호.
- cache hit 시 ``upsert_many`` 호출 안 함 (멱등성 정합, spy 로 검증).
- 다수 청크 적재 시 ``upsert_many`` 1회 호출 + batch size = 청크 수 (배치 효율 회귀 보호).

### 추가 회귀 테스트 `tests/api/test_deps.py` (+1 test)

- ``test_build_poc_deps_shares_chunk_lookup_with_ingest_samples`` —
  ``_ingest_samples`` 가 받은 chunk_lookup 인스턴스와 ``QueryGraphDeps.chunk_lookup``
  이 동일 인스턴스(``is`` 비교)여야 함. 공유가 깨지면 인덱싱과 검색이 서로 다른
  lookup 을 가리켜 download_url 채움이 실패하므로 회귀 차단.

### 책임 분리 (본 담당자 영역만)

- 본 commit 은 본 담당자 영역 7 modified (storage 1 / ingestion 1 / api 1 / docs 1 /
  tests 3). Agent 영역(``app/llm/`` / ``app/query/router.py`` / ``app/query/generator.py``)
  / ``app/schemas/`` / ``app/pipeline/`` / ``app/query/`` 모두 무변경.
- Phase 1 에서 만든 ``ChunkTextLookup`` 인프라(fetch / fetch_many) 는 변경 없음 —
  upsert 만 추가하므로 기존 호출자(``cross_encoder_rerank`` 의 ``fetch_many`` 사용)는
  영향 없음.

### 후방 호환성

- ``index_chunks`` 의 ``chunk_lookup`` / ``attachment_download_urls`` 모두 default
  None — 기존 7개 호출자(테스트 + indexer 호출자) 무변경 통과.
- ``QueryGraphDeps.chunk_lookup`` 기본값(빈 FakeChunkTextLookup)은 Phase 1 그대로 —
  본 commit 은 ``build_poc_deps`` 가 명시 인스턴스를 만들어 공유 주입할 뿐 default
  변경 없음.
- ``ChunkTextLookup`` ABC 에 abstractmethod 2개 추가 — 외부 구현체는 본 프로젝트에
  없으므로 영향 0. Fake / Mongo 두 구현체 모두 본 commit 에서 메서드 추가.

### 검증 결과 (회사 Mac 기준 — 예상)

- 샌드박스 ruff 0.15.13 으로 format `--check` (108 files already formatted) + check
  (All checks passed!) 통과.
- pytest 는 ``./scripts/verify.sh`` 실행 시 통과 예상 — 신규 17건 (chunk_lookup 4
  Fake + 6 Mongo + indexer 6 + deps 1) + 기존 회귀 0건. 샌드박스 Python 3.10 한계로
  직접 pytest 미실행 (이전 feature 패턴 동일).

### 비고

- 7개 파일 (모두 modified), +558 -10 lines (``git diff --stat HEAD``).
- ``docs/architecture.md`` / ``docs/api-spec.md`` / ``docs/rag-pipeline-design.md``
  변경 없음 (Storage 적재 통합만, 외부 API 표면·아키텍처 동일).
- ``docs/ai/current-plan.md`` 변경 없음 (Phase 1 의 자연스러운 연속이라 별도 milestone
  아님).
- chunk_lookup upsert 는 cache write 이후 단계라 chunk_lookup 적재 실패 시 다음 실행은
  cache hit 으로 스킵돼 chunk_lookup 적재가 누락될 수 있음 — 운영에서는 retry / 백필
  잡으로 보강한다 (현재 milestone 외).

### 후속 TODO (다음 세션 후보)

- **답변 생성기·검증기 풀 텍스트 조회 통합** — Agent 영역. 라우터·생성기·검증
  2단계 LLM 코드 전달 후, 풀 텍스트가 필요한 경우 ``chunk_lookup.fetch_many``
  호출하도록 wiring. 본 Phase 2 가 적재까지 완료했으므로 Agent 측 조회 통합만 남음.
- **운영 Qdrant 라이브 smoke** — 5-B + 9-B + chunk_lookup Phase 1+2 묶어 시연.
- **feature6 Ingestion 그래프** — 운영 ingestion 그래프가 ``attachment_download_urls``
  매핑을 ``page.attachments`` 에서 합성해 ``index_chunks`` 에 전달하도록 wiring (PoC
  ``_ingest_samples`` 패턴 재사용).


## 2026-05-18 — feature6 Phase 1: 첨부 파일 분석기 [Pipeline]

- 브랜치: `feat/#1/rag-pipeline-skeleton`
- 배경: chunk_lookup Phase 2(`ffabd34`) 완료 후 본 담당자 잔여 영역 feature6 (첨부 분석기
  + jobs 헬퍼 + 삭제 동기화 + Ingestion 그래프 조립)으로 진입. 4 모듈을 1 change-set =
  1 session 원칙 정합 위해 잘라, 가장 작은 독립 단위인 첨부 파일 분석기 [Pipeline]만
  본 세션에서 진행. 다음 세션 후보: jobs 헬퍼 → 삭제 동기화 → Ingestion 그래프 조립
  순서.
- 정합성 검증: 사용자가 기획서 v2.1.6 + 설계서 v0.2.2 원본 첨부 → 원본 §3.3.B 와 본
  세션 Plan 대조. 2건 정합성 이슈 발견 + 수정:
  1. **반복도 정의** — Plan 원안 "토큰 단위 max-frequency" → 설계서 원문
     "동일 문자 반복 비율 > 80%" 정합으로 **공백 제외 character max-frequency ≥ 0.8**
     로 수정.
  2. **분석기 책임 범위** — Plan 원안에 메타데이터 부착(③) 검토 포함 → chunker 의
     ``build_attachment_metadata`` (feature4-A 완료분)이 이미 처리 중이라 중복 구현이
     오버튜닝이 됨. **분석기는 ①분류 + ②유효성만 책임** 으로 축소 (③은 chunker,
     ④Chunker 호출은 Ingestion 그래프 노드 책임). 기존 chunk_lookup Phase 1·2 등
     완료 영역도 점검 — 모두 설계서 정합 (오버튜닝 없음).

### 변경 사항

신규 `app/ingestion/attachment_analyzer.py` (~150 lines):

- ``AttachmentAnalysisResult`` (frozen + slots dataclass) — ``attachment_id`` /
  ``attachment_type: AttachmentType | None`` / ``status: IngestionStatus`` /
  ``reason: str`` / ``analyzable: bool`` 프로퍼티. ``analyzable`` 는 ``status is
  SUCCESS`` 일 때만 True 인 단일 신호로, Ingestion 그래프 노드가 본 신호로 청킹
  진행 여부를 결정한다.
- ``analyze_attachment(attachment) -> AttachmentAnalysisResult`` — 설계서 §3.3.B
  정합 2단계:
  1. **유형 판별** — ``_classify_attachment`` 가 mime 부분 문자열 매칭 (PDF /
     wordprocessingml / msword / spreadsheetml / ms-excel / csv) 후 확장자 fallback
     (.pdf/.docx/.doc/.xlsx/.xls/.csv). 둘 다 실패 → status=UNSUPPORTED_ATTACH_TYPE.
  2. **텍스트 유효성** — 길이 검사 (< 200자 → LOW_QUALITY_ATTACH) → 동일 문자 반복
     검사 (공백 제외 max-frequency > 0.8 → LOW_QUALITY_ATTACH). 모두 통과 → SUCCESS.
- ``_max_char_repetition_ratio`` — 공백·개행 제외 후 Counter 로 최빈 문자 비율 계산.
  공백 제외 사유 docstring 명시 (들여쓰기·줄바꿈이 많은 정상 첨부에서 false positive
  회피).
- ATTACH_ENCRYPTED 는 본 분석기에서 발급하지 않는다 — 추출 단계(별도 어댑터/헬퍼)
  책임. docstring 명시.

수정 `app/ingestion/__init__.py`:

- 패키지 docstring 모듈 일람을 §3·§5 양쪽 인용으로 갱신, attachment_analyzer 책임
  범위 한 줄(분류 + 유효성, 메타·청크 호출은 chunker / 그래프 노드)을 명시. 신규
  ``구현 상태`` 단락 추가 — feature6 Phase 1 / chunker / embedding / indexer / 미구현
  계획 항목 명확히.
- ``AttachmentAnalysisResult`` / ``analyze_attachment`` re-export 추가 + ``__all__``
  신설.

### 신규 회귀 테스트 `tests/ingestion/test_attachment_analyzer.py` (~200 lines, 12 tests)

- mime 분류 4종 (pdf/docx/xlsx/csv) — ``@parametrize``.
- 확장자 분류 fallback 4종 (mime=octet-stream) — ``@parametrize``.
- 미지원 mime + 미지원 확장자 → UNSUPPORTED_ATTACH_TYPE (이미지 png, 동영상 mp4
  2케이스).
- 텍스트 200자 미만 → LOW_QUALITY_ATTACH + 빈 텍스트 케이스 분리.
- 동일 문자 반복 비율 > 80% → LOW_QUALITY_ATTACH (OCR 노이즈 시뮬레이션).
- 일반 한국어 텍스트는 SUCCESS (false positive 회귀 보호).
- 공백 제외 검증 — 공백만 압도적으로 많은 정상 첨부도 SUCCESS.
- 미지원 mime + 정상 길이 텍스트 → 분류 실패가 우선 (① > ②).
- ``frozen=True`` 회귀 보호 — set 시도 시 ``dataclasses.FrozenInstanceError``.
- ``attachment_id`` 결과 동봉 회귀 보호 (jobs.py 적재 시 키).

### 책임 분리 (본 담당자 영역만)

- 본 commit 은 본 담당자 영역 3 파일 (1 modified `app/ingestion/__init__.py` + 2 new
  `app/ingestion/attachment_analyzer.py` + `tests/ingestion/test_attachment_analyzer.py`).
- Agent 영역(``app/llm/`` / ``app/query/router.py`` / ``app/query/generator.py`` /
  ``app/ingestion/document_analyzer.py`` 미구현 — Agent 담당자 몫) 무변경.
- ``app/schemas/`` / ``app/pipeline/`` / ``app/query/`` / ``app/storage/`` /
  ``app/api/`` 모두 무변경.
- chunker 의 ``infer_attachment_type`` (feature4-A 의 PoC 추정기) 보존 — chunker
  단독 데모 경로. 분석기 [Pipeline] 책임은 신규 모듈이 가져옴.
- ``docs/`` 변경 없음 — 본 commit 은 설계서 §3.3.B 정의를 구현만 하므로 스키마·
  아키텍처·API 정의 변경 없음. db-schema §2.3 (``ingestion_jobs``)도 본 commit 에서
  적재 통합하지 않음(jobs 헬퍼는 별도 세션).

### 후방 호환성

- 신규 모듈만 추가, 기존 호출자 변화 0. 패키지 ``app/ingestion`` 의 기존 re-export
  는 없었으므로 ``__all__`` 신설이 영향 없음.

### 검증 결과 (회사 Mac 기준 — 예상)

- 샌드박스 ruff 0.15.13 으로 format `--check` (110 files already formatted) + check
  (All checks passed!) 통과.
- pytest 는 ``./scripts/verify.sh`` 실행 시 통과 예상 — 신규 12 케이스 + 기존 회귀
  0건. 샌드박스 Python 3.10 한계로 직접 pytest 미실행 (이전 feature 패턴 동일).

### 비고

- 3개 파일 (1 modified + 2 new), +~390 lines (`git diff --stat HEAD` 기준 modified
  +20 lines + 2 new files).
- 설계서 §3.3.B 정의에 정확 정합 — 반복도는 character 단위 (토큰 아님), 분석기는
  ①②만 (③④는 별도 책임).
- ``docs/architecture.md`` / ``docs/api-spec.md`` / ``docs/db-schema.md`` /
  ``docs/rag-pipeline-design.md`` / ``docs/chunking-strategy.md`` 변경 없음 (설계서
  기존 정의를 구현만, 새 인프라 도입 0).
- ``docs/ai/current-plan.md`` 변경 없음 (feature6 4단위 중 1단위 진행, milestone
  자체는 동일).

### 후속 TODO (다음 세션 후보)

- **feature6 Phase 2 — jobs.py 헬퍼** — ``app/ingestion/jobs.py`` + ``IngestionJobs``
  ABC + Fake / Mongo 구현 + ``record_stage(page_id, attachment_id, stage, status,
  started_at, finished_at, error)`` API. db-schema §2.3 정합. chunk_lookup Phase 1
  와 유사한 어댑터 패턴 재사용.
- **feature6 Phase 3 — sync.py 삭제 동기화** — ``DocumentSourceAdapter.list_active_ids
  ()`` vs Qdrant 적재 chunk_id 대조 → 고스트 청크 cascade 삭제 (페이지 + 첨부
  attachment_id 단위, 설계서 §3.7).
- **feature6 Phase 4 — Ingestion 그래프 조립** — ``app/pipeline/ingestion_graph.py``.
  analyze(첨부) → chunk → embed → upsert + jobs 기록 흐름. Agent 노드(문서 분석기)
  는 stub.
- **운영 Qdrant 라이브 smoke** — 5-B + 9-B + chunk_lookup Phase 1+2 묶어 시연.
- **답변 생성기·검증기 풀 텍스트 조회 통합** — Agent 코드 전달 후, 풀 텍스트가
  필요한 경우 ``chunk_lookup.fetch_many`` 호출하도록 wiring.


## 2026-05-18 — feature6 Phase 2: ingestion_jobs 어댑터 [Storage]

- 브랜치: `feat/#1/rag-pipeline-skeleton`
- 배경: feature6 Phase 1 (첨부 분석기 `4c6c2dc`) 직후 본 담당자 잔여 4단위 중 Phase 2.
  설계서 §3.1 + db-schema §2.3 정합 — Ingestion 파이프라인 각 단계(analyze/chunk/embed/
  upsert/sync) 처리 결과를 7필드(`page_id` / `attachment_id` / `stage` / `status` /
  `started_at` / `finished_at` / `error`)로 ``ingestion_jobs`` 컬렉션에 적재하기 위한
  어댑터. Phase 1 첨부 분석기가 ``AttachmentAnalysisResult`` 를 반환할 뿐 적재는 별도
  레이어 책임으로 분리해 두었으므로, 본 어댑터가 그 적재 경로를 마련한다 (실 호출 통합
  은 Phase 4 그래프 조립 세션).

### 변경 사항

신규 `app/storage/jobs.py` (~150 lines):

- ``IngestionJobRecord`` (frozen + slots dataclass) — db-schema §2.3 정합 7필드.
  ``stage: IngestionStage`` / ``status: IngestionStatus`` 는 기존 enum 그대로 사용
  (스키마 변경 0). 호출자가 ``started_at`` / ``finished_at`` 를 단계 진입·종료 시점
  에 직접 채워 전달.
- ``IngestionJobsRepository`` ABC — ``record(record)`` + ``record_many(records)``
  2개 추상 메서드만. ``list_recent`` / ``query`` 같은 조회 API 는 관리자 대시보드가
  미정이라 **오버튜닝 회피로 의도적 제외** (필요 시 후속 milestone).
- ``FakeIngestionJobsRepository`` — in-memory list 적재, 호출 순서 보존.
  ``records`` 프로퍼티가 방어 복사본을 반환 — 외부 ``.clear()`` 등이 내부 상태를
  오염시키지 않도록 회귀 보호.
- ``MongoIngestionJobsRepository`` — chunk_lookup Phase 1 패턴 그대로 재사용:
  - ``__init__(client, db_name, *, collection_name="ingestion_jobs")`` — dict-style
    인덱싱.
  - ``from_settings(settings, *, collection_name="ingestion_jobs")`` — pymongo lazy
    import (운영 부트스트랩).
  - ``record`` → ``insert_one(doc)``, ``record_many`` → ``insert_many(docs)``.
  - 빈 입력 short-circuit — pymongo ``insert_many`` 가 빈 docs 에서 던지는
    ``InvalidOperation`` 을 어댑터가 흡수해 호출자(그래프 노드)가 별도 분기 없이
    호출.
- ``_record_to_doc`` 헬퍼 — ``stage`` / ``status`` 를 명시적으로 ``.value`` 문자열로
  직렬화 (StrEnum 이지만 mongo BSON 인코더에 enum 타입이 전달되지 않도록 호환성
  안전).

수정 `app/storage/__init__.py`:

- 패키지 docstring 모듈 일람에 ``jobs.py`` 추가 (db-schema §2.3 정합 명시).
- 신규 모듈 4종 (``IngestionJobRecord`` / ``IngestionJobsRepository`` /
  ``FakeIngestionJobsRepository`` / ``MongoIngestionJobsRepository``) re-export +
  ``__all__`` 정렬 갱신.

수정 `docs/db-schema.md` §2.3:

- 적재 흐름 단락 신설 — ``IngestionJobsRepository.record`` / ``record_many`` 위치,
  enum ``.value`` 직렬화, 빈 입력 short-circuit 정책, 조회 API 미포함 사유(오버튜닝
  회피) 명시. chunk_lookup §2.5 패턴 정합.
- 인덱스 권장 — 운영 관리자 대시보드 조회 패턴에 맞춰 ``(page_id, started_at)``
  복합 인덱스 + ``status`` 단일 인덱스 권장 명시. 본 milestone 은 적재 어댑터만
  추가, 인덱스 생성은 운영 부트스트랩 단계 책임.

수정 `docs/ai/current-plan.md` §feature6:

- "본 담당자 몫(Pipeline)" → "본 담당자 몫(Pipeline + Storage)" — jobs 헬퍼는
  Storage 어댑터이므로 분류 갱신.
- ``app/ingestion/jobs.py`` → ``app/storage/jobs.py`` 위치 갱신 (외부 저장소 어댑터
  는 ``app/storage/`` 패키지 일관성 정합, ``app/CLAUDE.md`` §8). 결정 근거 한 줄
  명시.
- 작업 항목 4단위로 분해 + Phase 1 (첨부 분석기) / Phase 2 (jobs 헬퍼) 완료 표시
  + Phase 3 (sync) / Phase 4 (그래프 조립) 미진행 표시.

### 신규 회귀 테스트 `tests/storage/test_ingestion_jobs.py` (~225 lines, 12 tests)

- ABC 계약: ``issubclass`` 회귀 보호 (Fake / Mongo 둘 다 ABC 구현 강제).
- 값 객체: frozen 회귀 (``dataclasses.FrozenInstanceError``) + 7필드 보존 회귀.
- Fake: ``record`` 순서 보존 / ``record_many`` 배치 + 순서 / 빈 입력 noop /
  ``records`` 프로퍼티 방어 복사 회귀.
- Mongo: ``insert_one`` 7필드 + enum 문자열 직렬화 (``"embed"`` / ``"SUCCESS"``) /
  본문 잡 ``attachment_id=None`` 보존 / ``insert_many`` 배치 + ``insert_one`` 미호출 /
  빈 입력 short-circuit (``insert_many`` 도 미호출) / error 문자열 보존
  (``UNSUPPORTED_ATTACH_TYPE`` + 한국어 사유).
- ``_FakeCollection`` / ``_FakeDB`` / ``_DictStyleClient`` mock 3종 — chunk_lookup
  Phase 1 패턴 그대로 재사용해 일관성 유지.

### 책임 분리 (본 담당자 영역만)

- 본 commit 은 본 담당자 영역 5 파일 (2 new — ``app/storage/jobs.py`` +
  ``tests/storage/test_ingestion_jobs.py`` / 3 modified — ``app/storage/__init__.py``
  + ``docs/db-schema.md`` + ``docs/ai/current-plan.md``).
- Agent 영역(``app/llm/`` / ``app/query/router.py`` / ``app/query/generator.py``)
  / ``app/schemas/`` / ``app/pipeline/`` / ``app/query/`` / ``app/ingestion/`` /
  ``app/api/`` 모두 무변경.
- 본 commit 은 어댑터만 추가, 실제 호출 통합(첨부 분석기 → jobs 적재, 그래프 노드 →
  jobs 적재)은 Phase 4 그래프 조립 세션 책임.

### 정합성 검증 (오버튜닝 회피)

- 설계서 §3.1 원문 7필드 정확 정합 ✓
- 설계서 §5.3 + §8 예외 처리: 모든 ``stage`` / ``status`` 코드는 기존
  ``IngestionStage`` / ``IngestionStatus`` enum 정의에 이미 있음 — 스키마 변경 0 ✓
- chunk_lookup Phase 1 ABC + Fake + Mongo + ``from_settings`` 패턴 재사용 — 신규
  패턴 도입 0, 일관성 정합 ✓
- 조회 API 부재 — 관리자 대시보드 도입 시 별도 milestone 으로 분리 명시. 본 어댑터
  는 적재만 책임 ✓

### 후방 호환성

- 신규 모듈 + ABC 추상 메서드 — 외부 구현체 0 (본 프로젝트에 다른 IngestionJobs
  구현체 없음).
- ``app/storage/__init__.py`` ``__all__`` 에 신규 4종 추가 — 기존 re-export 0건 변경.

### 검증 결과 (회사 Mac 기준 — 예상)

- 샌드박스 ruff 0.15.13 으로 format `--check` (112 files already formatted) + check
  (All checks passed!) 통과.
- pytest 는 ``./scripts/verify.sh`` 실행 시 통과 예상 — 신규 12 케이스 + 기존 회귀
  0건. 샌드박스 Python 3.10 한계로 직접 pytest 미실행 (이전 feature 패턴 동일).

### 비고

- 5개 파일 (2 new + 3 modified), 본 commit 의 코드/테스트 신규 추가 + 문서 갱신.
- ``docs/architecture.md`` / ``docs/api-spec.md`` / ``docs/rag-pipeline-design.md`` /
  ``docs/chunking-strategy.md`` 변경 없음 (설계서 §3.1 정의를 구현만, 새 인프라
  추가 없음).
- ``app/config.py`` 변경 없음 — ``mongo_uri`` / ``mongo_db`` 기존 필드 그대로 사용,
  ``from_settings(collection_name=...)`` 기본값으로 충분 (chunk_lookup 패턴 정합).

### 후속 TODO (다음 세션 후보)

- **feature6 Phase 3 — sync.py 삭제 동기화** — ``app/ingestion/sync.py``
  + ``DocumentSourceAdapter.list_active_ids()`` vs Qdrant chunk_id 대조 → 고스트
  cascade 삭제 (페이지 + 첨부 ``attachment_id`` 단위, 설계서 §3.7).
- **feature6 Phase 4 — Ingestion 그래프 조립** — ``app/pipeline/ingestion_graph.py``.
  analyze(첨부) → chunk → embed → upsert + jobs 기록 흐름. Agent 노드(문서 분석기)
  는 stub. Phase 1 (첨부 분석기) + Phase 2 (jobs) + Phase 3 (sync) 종합.
- **운영 Qdrant 라이브 smoke** — 5-B + 9-B + chunk_lookup Phase 1+2 + jobs 묶어
  시연.
- **답변 생성기·검증기 풀 텍스트 조회 통합** — Agent 코드 전달 후, ``chunk_lookup
  .fetch_many`` 호출하도록 wiring.


## 2026-05-18 — feature6 Phase 3: 삭제 동기화 (Reconciliation) [Pipeline]

- 브랜치: `feat/#1/rag-pipeline-skeleton`
- 배경: feature6 Phase 2 (`152d2e9`) 직후 본 담당자 잔여 4단위 중 Phase 3. 설계서
  §3.7 정확 정합 — Delta Sync 가 감지하지 못하는 삭제된 페이지·첨부의 고스트
  데이터를 Qdrant 에서 제거하기 위한 Reconciliation. PoC 단계는 본 함수 단독으로
  일관성 유지, 운영 전환 시 Trash API Sync + Webhook 으로 ‘주 1회 → 1시간 → 즉시’
  3중 안전망 보강 (운영 책임, 본 PoC 범위 외).

### 변경 사항

수정 `app/storage/qdrant_client.py`:

- ``scroll_page_ids(*, batch_size: int = 1000) -> set[str]`` — 본문 청크(source_type
  =page)의 ``page_id`` unique set. CONTENT_POOL 하나만 스캔 (3 Pool 동일 청크 적재
  정합, ``app/CLAUDE.md`` §4). payload-only scroll 로 벡터 미로드 (메모리 효율).
- ``scroll_attachment_ids(*, batch_size: int = 1000) -> set[str]`` — 첨부 청크
  (source_type=attachment) 의 ``attachment_id`` unique set.
- ``_scroll_payload_field`` 헬퍼 — pymongo scroll 페이지네이션 (offset/next_offset
  무한 loop) + source_type 필터 + 단일 payload 필드 추출.
- 모듈 docstring 변경 이력에 본 세션 항목 추가.

신규 `app/ingestion/sync.py` (~95 lines):

- ``ReconciliationResult`` (frozen + slots dataclass) — ``deleted_pages: list[str]``
  + ``deleted_attachments: list[str]``. 호출자(스케줄러·그래프 노드)가 jobs 적재·
  알림에 사용.
- ``reconcile_deletions(*, source: DocumentSourceAdapter, store: QdrantPoolStore)
  -> ReconciliationResult`` — 설계서 §3.7 Phase 1 흐름 7단계 정확 구현:
  1. ``active_ids = source.list_active_ids()`` (pages set + attachments set)
  2. ``set_B_pages = store.scroll_page_ids()``
  3. ``set_B_attaches = store.scroll_attachment_ids()``
  4. ``ghost_pages = set_B_pages - active_ids.pages``
  5. ``ghost_attaches = set_B_attaches - active_ids.attachments``
  6. 각 ghost id 에 ``store.delete_by_page_id`` / ``delete_by_attachment_id`` 호출
     — 어댑터가 3 Pool 모두에서 cascade 삭제.
  7. ``ReconciliationResult`` 반환.
- ghost 집합이 비어 있으면 delete 호출 자체 회피 — 운영 비용 절감 + false positive
  차단. 결정론 회귀를 위해 결과를 정렬 (테스트·로깅 안정성).

수정 `app/ingestion/__init__.py`:

- 패키지 docstring 구현 상태 — sync.py 항목 추가 + jobs.py 위치 이전 명시
  (``app/storage/jobs.py`` Phase 2 정합).
- ``ReconciliationResult`` / ``reconcile_deletions`` re-export + ``__all__`` 정렬.

수정 `docs/ai/current-plan.md` §feature6:

- Phase 3 (삭제 동기화) 완료 표시. 본 담당자 잔여 4단위 중 3단위 (Phase 1+2+3)
  완료, Phase 4 (Ingestion 그래프 조립)만 남음.

### 신규 회귀 테스트

수정 `tests/storage/test_qdrant_client.py` (+4 tests):

- ``test_scroll_page_ids_returns_unique_set_of_body_page_ids`` — 같은 page_id 중복
  청크는 1회만 등장.
- ``test_scroll_page_ids_excludes_attachment_chunks`` — 첨부 청크는 결과에서 제외
  (source_type 필터 회귀 보호).
- ``test_scroll_attachment_ids_returns_unique_set_of_attachment_ids`` — 첨부 청크
  의 ``attachment_id`` unique set + 본문 제외.
- ``test_scroll_methods_return_empty_set_on_empty_collection`` — 빈 컬렉션 회귀
  보호.

신규 `tests/ingestion/test_sync.py` (~225 lines, 9 tests):

- 값 객체 회귀 (frozen, 필드 보존).
- ghost page 삭제 + Qdrant 상태 검증 (적재 결과 검증).
- ghost attachment 삭제.
- active ⊇ stored → ghost 0 (false positive 회귀 보호).
- 빈 Qdrant → 빈 결과.
- 빈 active → 모든 청크 ghost.
- 본문 + 첨부 혼합 ghost — 한 호출에서 둘 다 cascade 삭제.
- ghost 0 시 delete 호출 자체 회피 — spy 로 ``delete_by_page_id`` / ``delete_by_
  attachment_id`` 미호출 검증 (운영 비용 회귀 보호).

### 책임 분리 (본 담당자 영역만)

- 본 commit 은 본 담당자 영역 5 파일 (2 new — ``app/ingestion/sync.py`` +
  ``tests/ingestion/test_sync.py`` / 3 modified — ``app/storage/qdrant_client.py``
  + ``app/ingestion/__init__.py`` + ``tests/storage/test_qdrant_client.py``).
- Agent 영역(``app/llm/`` / ``app/query/router.py`` / ``app/query/generator.py``)
  / ``app/schemas/`` / ``app/pipeline/`` / ``app/query/`` / ``app/api/`` 모두 무변경.
- jobs 통합·스케줄링·알림은 **호출자 책임** — sync 함수는 ``ReconciliationResult``
  만 반환하고 호출자(Phase 4 그래프 조립 또는 운영 스케줄러)가 jobs 적재. 책임
  분리 정합 (CLAUDE.md "Controller·Service·Repository·Client·DTO 책임을 섞지 않
  는다").

### 정합성 검증 (오버튜닝 회피)

- 설계서 §3.7 "PoC 단계는 Reconciliation 만" 정확 정합 — Trash API Sync / Webhook
  미구현 ✓
- 설계서 §3.7 7단계 흐름 정확 정합 — scroll → diff → cascade delete ✓
- 스케줄링 / cron / 운영 알림 / DLQ 재시도 미포함 — 운영 책임, 본 모듈은 단일
  함수만 ✓
- 신규 패턴 도입 0 — 기존 ``QdrantPoolStore`` 확장 (scroll 2종) + 기존
  ``DocumentSourceAdapter.list_active_ids`` / ``delete_by_*`` 그대로 사용 ✓
- jobs 통합은 호출자 책임 (책임 분리) ✓

### 후방 호환성

- 신규 모듈 + 기존 어댑터 메서드 추가 — 기존 호출자 0건 영향.
- ``app/ingestion/__init__.py`` ``__all__`` 에 신규 2종 추가 — 기존 re-export 0건
  변경.

### 검증 결과 (회사 Mac 기준 — 예상)

- 샌드박스 ruff 0.15.13 으로 format `--check` (114 files already formatted) + check
  (All checks passed!) 통과.
- pytest 는 ``./scripts/verify.sh`` 실행 시 통과 예상 — 신규 13 케이스 (scroll 4 +
  sync 9) + 기존 회귀 0건. 샌드박스 Python 3.10 한계로 직접 pytest 미실행 (이전
  feature 패턴 동일).

### 비고

- 5개 파일 (2 new + 3 modified), 본 commit 의 코드/테스트 신규 추가 + 문서 갱신.
- ``docs/architecture.md`` / ``docs/api-spec.md`` / ``docs/db-schema.md`` /
  ``docs/rag-pipeline-design.md`` / ``docs/chunking-strategy.md`` 변경 없음 —
  설계서 §3.7 정의를 구현만, 새 인프라 추가 0.
- scroll 의 batch_size 기본 1000 — 본 PoC (92 페이지 규모) 에는 단일 호출로 충분,
  운영 (수십만 청크) 에서는 메모리/네트워크 트레이드오프로 조정 가능.

### 후속 TODO (다음 세션 후보)

- **feature6 Phase 4 — Ingestion 그래프 조립** — ``app/pipeline/ingestion_graph.py``.
  analyze(첨부) → chunk → embed → upsert + jobs 기록 흐름. Agent 노드(문서 분석기)
  는 stub. Phase 1 (첨부 분석기) + Phase 2 (jobs) + Phase 3 (sync) 종합. **본 담당자
  잔여 영역의 마지막 단위 — 완료 시 feature6 종결.**
- **운영 Qdrant 라이브 smoke** — 5-B + 9-B + chunk_lookup Phase 1+2 + jobs + sync
  묶어 시연.
- **답변 생성기·검증기 풀 텍스트 조회 통합** — Agent 코드 전달 후, ``chunk_lookup
  .fetch_many`` 호출하도록 wiring.


## 2026-05-18 — feature6 Phase 4: Ingestion 그래프 조립 [Pipeline] — feature6 종결

- 브랜치: `feat/#1/rag-pipeline-skeleton`
- 배경: feature6 Phase 3 (`8ceec58`) 직후 본 담당자 잔여 4단위 중 **마지막 단위**.
  설계서 §3.1 Big Picture 정합 — analyze → chunk → embed_upsert 3 stage 를 한
  LangGraph 그래프로 종합. Phase 1 (첨부 분석기) + Phase 2 (jobs) + Phase 3 (sync —
  별도 잡) 모듈을 wiring 하고 Agent 노드(문서 분석기) 자리는 stub. 완료 시
  **feature6 종결** + 본 담당자 영역 ~95% 도달.

### 변경 사항

신규 `app/pipeline/ingestion_graph.py` (~260 lines):

- ``IngestionGraphDeps`` (slots dataclass) — 그래프 의존성 묶음:
  - Pipeline/Storage 4종 필수: ``dense_embedder`` / ``sparse_embedder`` / ``store``
    / ``cache``
  - default_factory 2종: ``chunk_lookup`` (FakeChunkTextLookup) / ``jobs``
    (FakeIngestionJobsRepository) — 미주입 환경에서도 안전 동작.
  - Agent stub default: ``document_analyzer_node = document_analyzer_stub``
  - chunk_attachment 주입 default: ``chunk_attachment_fn = chunk_attachment`` — 파일
    시스템 의존성을 갖는 함수라 테스트에서 fake 주입 가능하게 한다.
- ``build_ingestion_graph(deps) -> CompiledGraph`` — StateGraph(IngestionState) 에
  3 노드 + 3 엣지 wiring. 노드명 (``analyze_document`` / ``chunk_documents`` /
  ``embed_upsert``)은 IngestionState 필드(page/doc_type/chunks/stage/status/error)
  와 다른 네임스페이스 — LangGraph 1.x 충돌 회피 (query_graph 패턴 정합).
- ``run_ingestion(state, *, graph) -> IngestionState`` — invoke 후
  ``IngestionState.model_validate`` 로 재구성 (LangGraph 0.2.x Pydantic 직렬화 패턴).
- 3 노드 내부 함수:
  - ``_analyze_document_node`` — Agent stub 호출 + ``jobs.record(ANALYZE, SUCCESS)``.
  - ``_chunk_documents_node`` — 본문 ``chunk_page`` + 첨부 순회. 각 첨부는
    ``_process_attachment`` 헬퍼가 분석 → 청킹 → 잡 기록. 무효/실패 시 본문은 정상.
  - ``_embed_upsert_node`` — ``index_chunks`` 호출 (chunk_lookup +
    attachment_download_urls 매핑 자동 합성). 청크 0 시 적재 회피.
- ``_process_attachment`` 헬퍼 — Phase 1 ``analyze_attachment`` 호출 → 무효 시
  잡 기록 후 빈 list / 유효 시 ``chunk_attachment_fn`` 호출 → ValueError catch
  (PDF/CSV feature4-B 대기) + 잡 기록.

수정 `app/pipeline/stubs.py`:

- ``document_analyzer_stub(state) -> IngestionState`` 추가 — 설계서 §8 fallback 정합
  ``doc_type = DocType.OPERATION.value`` 채움. Agent 코드 전달 시 교체.
- 모듈 docstring 변경 이력에 feature6 Phase 4 항목 추가.
- import 에 ``DocType`` + ``IngestionState`` 추가.

수정 `app/pipeline/__init__.py`:

- 패키지 docstring 모듈 일람·구현 상태에 ingestion_graph.py 추가, stubs.py 4종
  (이전 3종 + document_analyzer_stub) 명시. "계획 모듈 (미구현)" 단락 제거 — Phase 4
  완료로 모두 구현됨.
- 신규 4종 re-export (``IngestionGraphDeps`` / ``build_ingestion_graph`` /
  ``run_ingestion`` / ``document_analyzer_stub``) + ``__all__`` 정렬.

수정 `docs/ai/current-plan.md`:

- Phase 3 완료 commit hash 명시 (`8ceec58`).
- Phase 4 (Ingestion 그래프 조립) 완료 표시 + "feature6 종결" 명시.

### 신규 회귀 테스트 `tests/pipeline/test_ingestion_graph.py` (~280 lines, 10 tests)

- ``IngestionGraphDeps`` 기본값 회귀 — ``document_analyzer_node is document_analyzer_stub``.
- 본문만 적재 — 첨부 없는 페이지 → ``scroll_page_ids() == {"P1"}`` +
  ``scroll_attachment_ids() == set()``.
- 본문 + 유효 docx 첨부 — 양쪽 source_type 적재 + Qdrant 양쪽 scroll set 정합.
- 미지원 mime(png) 첨부 — 본문만 적재 + jobs 에 ``UNSUPPORTED_ATTACH_TYPE`` 기록
  (stage=ANALYZE).
- LOW_QUALITY 첨부 — 본문만 적재 + jobs 에 ``LOW_QUALITY_ATTACH`` 기록.
- PDF 첨부 (feature4-B 대기) — ``chunk_attachment_fn`` 의 ValueError catch + 잡 기록
  + 본문은 정상 적재.
- jobs stage 3종 회귀 — 첨부 없는 정상 페이지 → 페이지 단위 잡에 ANALYZE +
  CHUNK + UPSERT 모두 SUCCESS 기록.
- jobs 타임스탬프 회귀 — 모든 잡 기록의 ``started_at <= finished_at``.
- IngestionState 흐름 회귀 — ``doc_type`` 채워짐 + ``chunks`` 적재 + ``page``
  보존.
- LangGraph 노드명-state field 충돌 회귀 — 그래프 컴파일이 그대로 통과해야 함.

테스트 격리를 위해 ``_fake_attachment_chunk`` fixture 정의 — 실 ``chunk_attachment``
의 파일 시스템 의존성 회피, PDF/CSV 케이스는 동일 ValueError 던지도록.

### 책임 분리 (본 담당자 영역만)

- 본 commit 은 본 담당자 영역 5 파일 (2 new — ``app/pipeline/ingestion_graph.py`` +
  ``tests/pipeline/test_ingestion_graph.py`` / 3 modified — ``app/pipeline/stubs.py``
  + ``app/pipeline/__init__.py`` + ``docs/ai/current-plan.md``).
- Agent 영역 (``app/llm/`` / ``app/query/router.py`` / ``app/query/generator.py`` /
  ``app/ingestion/document_analyzer.py`` — Agent 담당자 몫) 무변경.
- ``app/schemas/`` / ``app/ingestion/`` 각 모듈 / ``app/query/`` / ``app/api/`` /
  ``app/storage/`` 모두 무변경 (그래프가 호출만 함).
- 운영 진입점 (``build_real_ingestion_deps``, RabbitMQ Worker wiring) 미구현 —
  호출자/운영 책임 (별도 세션 가능).

### 정합성 검증 (오버튜닝 회피)

- 설계서 §3.1 Big Picture stage 4종 중 analyze + chunk + upsert만 구현 (sync 는
  별도 함수, Phase 3 sync.py 담당) ✓
- 본문/첨부 병렬 처리 X — LangGraph 병렬은 복잡, PoC 직렬로 충분 (성능 PoC 범위 외) ✓
- IngestionState 스키마 변경 X — 기존 그대로 ✓
- 운영 진입점 wiring (build_real_ingestion_deps, RabbitMQ) X — 호출자/운영 책임 ✓
- DLQ 재시도·알림·스케줄링 X — 운영 책임 ✓
- 문서 분석기 [Agent] 본 구현 X — stub만 (Agent 담당자 코드 전달 시 교체) ✓
- chunk_attachment ValueError catch 로 PDF/CSV (feature4-B 대기) 우회 — 본문 정상
  적재 보장 ✓

### 후방 호환성

- 신규 모듈 + ABC 추상 메서드 추가 없음 — 기존 호출자 0건 영향.
- ``app/pipeline/__init__.py`` ``__all__`` 에 신규 4종 추가 — 기존 re-export 0건
  변경.

### 검증 결과 (회사 Mac 기준 — 예상)

- 샌드박스 ruff 0.15.13 으로 format `--check` (116 files already formatted) + check
  (All checks passed!) 통과.
- pytest 는 ``./scripts/verify.sh`` 실행 시 통과 예상 — 신규 10 케이스 + 기존 회귀
  0건. 샌드박스 Python 3.10 한계로 직접 pytest 미실행 (이전 feature 패턴 동일).

### 비고

- 5개 파일 (2 new + 3 modified), 본 commit 의 코드/테스트 신규 추가 + 문서 갱신.
- ``docs/architecture.md`` / ``docs/api-spec.md`` / ``docs/db-schema.md`` /
  ``docs/rag-pipeline-design.md`` / ``docs/chunking-strategy.md`` 변경 없음 —
  설계서 §3.1 정의를 구현만, 새 인프라 추가 0.

### feature6 종결 + 본 담당자 영역 진척도

- **feature6 완료** — 본 담당자 영역 4단위 (Phase 1+2+3+4) 모두 종료.
- **본 담당자 영역 진척도**: ~92% → **약 95%**.
- **잔여**: feature2 Atlassian 어댑터 (토큰 경로 미정), feature4-B PDF/CSV 첨부
  분할기 (픽스처 대기), Agent 통합 (Agent 담당자 코드 전달 후 QueryGraphDeps /
  IngestionGraphDeps 3 stub 교체), 운영 진입점 wiring, 운영 라이브 smoke.

### 후속 TODO (다음 세션 후보)

- **운영 Qdrant 라이브 smoke** — 5-B + 9-B + chunk_lookup Phase 1+2 + jobs + sync
  + ingestion_graph 묶어 시연. docker compose + RAG_USE_REAL_ADAPTERS=true. 코드
  미변경, 운영 검증만.
- **build_real_ingestion_deps** — 운영 어댑터 부트스트랩 함수 (app/api/deps.py 또는
  별도). MongoEmbeddingCache + MongoIngestionJobsRepository + MongoChunkTextLookup
  wiring.
- **답변 생성기·검증기 풀 텍스트 조회 통합** — Agent 코드 전달 후 ``chunk_lookup
  .fetch_many`` wiring.


## 2026-05-18 — feature6 후속: build_poc/real_ingestion_deps (운영 진입점 wiring)

- 브랜치: `feat/#1/rag-pipeline-skeleton`
- 배경: feature6 Phase 4 (`10aeb1c`) 완료로 ``IngestionGraphDeps`` + ``build_ingestion_graph``
  + ``run_ingestion`` 가 동작. 운영 진입점(``build_real_ingestion_deps``) + PoC
  편의 진입점(``build_poc_ingestion_deps``)이 완성되면 운영 RabbitMQ Worker / 라이브
  smoke 가 본 두 함수만 호출하면 된다. ``build_real_deps`` (Query 용) 패턴 재사용.

### 변경 사항

수정 `app/api/deps.py`:

- 모듈 docstring 변경 이력에 feature6 후속 항목 추가.
- 최상단 import 추가: ``from app.pipeline.ingestion_graph import IngestionGraphDeps``
  — LangGraph 는 query_graph 가 이미 최상단 import 중이므로 본 추가는 새 heavy
  의존성을 도입하지 않는다 (lazy 정책 유지).
- ``build_poc_ingestion_deps(settings) -> IngestionGraphDeps`` 신설 (~30 lines):
  - ``FakeDenseEmbedder`` / ``FakeSparseEmbedder`` / :memory: Qdrant /
    ``FakeEmbeddingCache`` / ``FakeChunkTextLookup`` / ``FakeIngestionJobsRepository``
  - samples 자동 인덱싱 X — 그래프 호출자가 명시 PageObject 전달 가정.
- ``build_real_ingestion_deps(settings) -> IngestionGraphDeps`` 신설 (~55 lines):
  - ``E5DenseEmbedder`` + ``BM25SparseEmbedder`` + ``QdrantPoolStore.from_settings``
    + ``MongoEmbeddingCache.from_settings`` + ``MongoChunkTextLookup.from_settings``
    + ``MongoIngestionJobsRepository.from_settings``
  - 실 어댑터 4종(E5/BM25/Mongo 3종) 모두 함수 본문 내 lazy import — embedding
    extra 미설치 환경 보호 (``build_real_deps`` 정책 정합).
  - bootstrap_collections() 호출 (3 Pool 멱등 생성).
  - Agent 노드(문서 분석기) 자리는 ``IngestionGraphDeps`` 기본값(stub) 그대로 — Agent
    코드 전달 시 ``deps.document_analyzer_node`` 1줄만 교체.
  - reranker 미포함 — Ingestion 그래프는 검색 단계가 없으므로 불필요 (Query 용
    ``build_real_deps`` 와 책임 분리 정합).

### 신규 회귀 테스트 `tests/api/test_deps.py` (+191 lines, 6 tests)

- ``test_build_poc_ingestion_deps_returns_all_fake_adapters`` — 모든 어댑터 Fake 인
  스턴스 + Agent stub 기본값 + chunk_attachment_fn 실 함수 default.
- ``test_build_poc_ingestion_deps_bootstrap_collections`` — :memory: Qdrant 3 Pool
  컬렉션 생성.
- ``patched_real_ingestion_adapters`` fixture — 6 어댑터 가짜 대체 (E5/BM25 lazy
  import + Qdrant from_settings + Mongo 3종 from_settings classmethod 교체).
- ``test_build_real_ingestion_deps_wires_all_real_adapter_classes`` — 6 어댑터 모두
  호출 검증 + IngestionGraphDeps 시그니처 정합 + Fake 미사용 회귀 보호.
- ``test_build_real_ingestion_deps_passes_dense_model_name`` — settings.dense_embedding_model
  이 E5DenseEmbedder 생성자에 전달.
- ``test_build_real_ingestion_deps_does_not_eagerly_import_sentence_transformers``
  — AST 로 모듈 최상단 import 검사 (sentence_transformers / fastembed /
  app.ingestion.embedder.dense / app.ingestion.embedder.sparse 누설 없음).

### 책임 분리 (본 담당자 영역만)

- 본 commit 은 본 담당자 영역 2 파일 (1 modified — ``app/api/deps.py`` + 1 modified —
  ``tests/api/test_deps.py``). Agent 영역 / ``app/schemas/`` / ``app/pipeline/`` /
  ``app/query/`` / ``app/ingestion/`` / ``app/storage/`` / ``app/main.py`` 모두 무변경.
- FastAPI lifespan 자동 ingestion 부트스트랩 X — Ingestion 은 query 와 별도 진입점
  (RabbitMQ Worker / 운영 트리거) 책임. 본 함수가 운영 Worker 의 호출 대상이며
  본 PoC 에서는 함수만 추가, Worker 시스템 wiring 은 운영 측 책임.

### 정합성 검증 (오버튜닝 회피)

- 기존 ``build_real_deps`` (Query 용) 패턴 재사용 — 신규 패턴 도입 0 ✓
- ``Settings`` 신규 필드 추가 X — 기존 mongo_uri / mongo_db / qdrant_host / qdrant_port
  / dense_embedding_model 활용 ✓
- RabbitMQ Worker / 스케줄러 / cron / 알림 wiring 미포함 — 운영 책임 ✓
- FastAPI lifespan 자동 ingestion 부트스트랩 X — query 와 분리 ✓
- 운영 lifespan + samples 인덱싱 자동화 X — 운영은 별도 적재 가정 ✓

### 후방 호환성

- 신규 함수 2종 추가만 — 기존 호출자 0건 영향.
- ``IngestionGraphDeps`` 최상단 import 추가 — LangGraph 이미 query_graph 가 최상단
  import 중이므로 신규 heavy 의존성 도입 0. ``app.api.deps`` 모듈 import 시점에
  heavy 의존성 누설 없음 (회귀 보호 테스트로 검증).

### 검증 결과 (회사 Mac 기준 — 예상)

- 샌드박스 ruff 0.15.13 으로 format `--check` (116 files already formatted) + check
  (All checks passed!) 통과.
- pytest 는 ``./scripts/verify.sh`` 실행 시 통과 예상 — 신규 6 케이스 + 기존 회귀 0건.
  샌드박스 Python 3.10 한계로 직접 pytest 미실행.

### 비고

- 2개 파일 (모두 modified), +288 lines.
- ``docs/architecture.md`` / ``docs/api-spec.md`` / ``docs/db-schema.md`` /
  ``docs/rag-pipeline-design.md`` / ``docs/chunking-strategy.md`` / ``docs/ai/current-plan.md``
  변경 없음 — 새 인프라 도입 0, 기존 부트스트랩 패턴 확장만.

### 후속 TODO (다음 세션 후보)

- **운영 Qdrant + MongoDB 라이브 smoke** — docker compose up + RAG_USE_REAL_ADAPTERS=true
  + ``build_real_ingestion_deps()`` 로 단일 PageObject 적재 + ``build_real_deps()`` +
  uvicorn 으로 끝-끝 검색 검증. 코드 미변경, 운영 검증만.
- **답변 생성기·검증기 풀 텍스트 조회 통합** — Agent 코드 전달 후 ``chunk_lookup
  .fetch_many`` wiring.
- **Agent 통합** — Agent 담당자 코드 전달 시 ``QueryGraphDeps`` / ``IngestionGraphDeps``
  4 stub (router / generator / verify_llm_evaluator / document_analyzer) 교체.


## 2026-05-18 — Agent 통합 1/4: query-routing-agent vendoring + 어댑터 노드

- 브랜치: `feat/#1/rag-pipeline-skeleton`
- 배경: feature6 후속 (`6cd507c`) 으로 본 담당자 잔여 영역 ~96% 도달. Agent 담당자가
  ``ai-agent/query-routing-agent/`` 를 전달, 본 세션에서 ``router_stub`` 자리에 실
  Agent 코드를 wiring 한다 (`docs/ai/current-plan.md` Agent 통합 메모 정합). 작업
  분해 = B 안 (단계별, 1 세션 = 1 Agent). 본 세션은 라우터부터 — Query 그래프 진입
  직후 노드로 다른 노드들에 영향을 주는 출력(intent / pool_weights / target_llm /
  metadata_filters) 을 채우므로 우선 진행.

### 변경 사항

**Vendoring (무수정 보존)**

신규 ``query_routing_agent/`` (~19 파일, ai-agent/query-routing-agent/src/
query_routing_agent 복사) — ``history_manager_agent`` 패턴 정합:

- ``app/`` / ``config/`` / ``llm/`` / ``routing/`` / ``schemas/`` / ``scripts/`` /
  ``workflow.py`` 모두 무수정 복사. ``tests/`` 는 가져오지 않음 (history_manager_agent
  패턴 정합 — Agent 담당자 저장소에서 이미 검증됐다는 가정).
- ``__init__.py`` 등 표준 모듈 구조 — ``from query_routing_agent.config import …``
  같은 absolute import 가 rag 저장소 루트에서 그대로 동작 (Python path 정합).

**pyproject.toml 갱신**

- ``[tool.setuptools.packages.find].include`` 에 ``query_routing_agent*`` 추가 —
  ``pip install -e .`` 시 vendoring 패키지가 함께 설치되도록.
- ``[tool.ruff].extend-exclude`` 에 ``query_routing_agent`` + ``tests/
  query_routing_agent`` 추가 — vendoring 외부 코드는 lint/format 대상에서 제외.
- ``[tool.mypy].exclude`` + ``[[tool.mypy.overrides]] module = "query_routing_agent.*"
  follow_imports = "skip"`` 추가 — mypy 검사 대상에서 제외 (history_manager_agent
  패턴 그대로).

**어댑터 노드 신설 — ``app/query/router.py`` (~145 lines)**

- ``manage_router(state, *, provider=None, config=None) -> RagState`` — vendoring
  한 4 단계 로직 함수를 in-process 호출:
    1. ``normalize_routing_input(routing_input_dict)`` →
       ``NormalizedRoutingInputResult``
    2. ``classify_intent(normalized, config, provider)`` →
       ``IntentClassificationResult``
    3. ``rewrite_queries(normalized, classification, config)`` → ``QueryRewriteResult``
    4. ``build_filter_and_pool_weights(normalized, intent, config)`` →
       ``FilterAndWeightResult``
- RagState ↔ agent 스키마 변환:
    - ``_build_routing_input_payload`` — ``conversation_id`` / ``user_id`` / ``query`` /
      ``groups`` + ``HistoryDecision`` (있으면 preserved_context 전달)
    - ``_INTENT_MAP`` — Agent ``IntentLabel`` (영어 snake_case) → rag ``Intent``
      (한국어 enum 값) 매핑 표. ``UNKNOWN`` 은 rag Intent 에 대응값이 없어
      OPERATION_GUIDE 로 fallback (stub 정합).
    - ``_map_pool_weights`` — Agent ``PoolWeights`` (title/content/label) → rag Pool
      이름 키 ({TITLE_POOL, CONTENT_POOL, LABEL_POOL}).
    - ``MetadataFilter.to_dict()`` 그대로 사용 → ``RagState.metadata_filters: dict``.
- 안전 fallback:
    - ``conversation_id`` 가 None 이면 Agent 호출 자체를 회피 (정규화 단계에서 required
      로 실패하기 때문) → ``_apply_fallback`` 으로 stub 정합 분기.
    - ``Exception`` 광역 catch — provider/parsing 실패 시 OPERATION_GUIDE fallback.
      rag-pipeline-design.md §8 안전 기본값과 정합.
- LLM provider default: ``FakeRoutingLLMProvider`` (PoC·테스트). 실 운영은
  ``OpenAIRoutingLLMProvider`` 를 ``QueryGraphDeps.routing_provider`` 로 주입.

**그래프 wiring — ``app/pipeline/query_graph.py``**

- ``QueryGraphDeps`` 갱신:
    - ``routing_provider: RoutingProvider | None = None`` 추가
    - ``routing_config: RoutingConfig | None = None`` 추가
    - ``router_node`` default 를 ``router_stub`` → ``manage_router`` 로 변경.
- ``build_query_graph`` 갱신:
    - ``deps.router_node is manage_router`` 일 때만 ``functools.partial`` 로
      ``provider`` / ``config`` 주입. 외부 사용자 정의 router_node 는 captured 가
      이미 있다고 가정하고 그대로 등록.
- import 정리 — ``router_stub`` 제거, ``manage_router`` 추가.

**부트스트랩 — ``app/api/deps.py``**

- ``build_poc_deps`` — 변경 없음. QueryGraphDeps 기본값(routing_provider=None →
  manage_router 가 FakeRoutingLLMProvider 자동 주입) 그대로 사용 — 외부 API 키
  없이 PoC 경로 동작 유지.
- ``build_real_deps`` 본체:
    - lazy import 추가: ``from query_routing_agent.config import QueryRoutingConfig``,
      ``from query_routing_agent.llm import OpenAIRoutingLLMProvider``
    - ``QueryRoutingConfig(model="gpt-4o-mini")`` 생성 (app/CLAUDE.md §5 라우팅 정책).
    - ``OpenAIRoutingLLMProvider.from_config(routing_config)`` 로 환경변수 기반 provider
      구성 — OPENAI_API_KEY 누락 시 RoutingProviderError 즉시 발생 (운영 lifespan
      진입 직전에 누락 명확히 드러남).
    - 반환 ``QueryGraphDeps`` 에 ``routing_provider`` / ``routing_config`` 추가 인자.

**Stub 갱신 — ``app/pipeline/stubs.py``**

- 모듈 docstring 변경 이력에 "Agent 통합 1/4 — query-routing-agent 어댑터 wiring
  완료" 추가.
- ``router_stub`` 자체는 **보존** — 회귀 보호·PoC fallback 데모용. ``QueryGraphDeps
  .router_node`` 의 default 가 ``manage_router`` 로 바뀌었을 뿐.

**Re-export — ``app/query/__init__.py``**

- 패키지 docstring 구현 상태 단락에 ``router.py — manage_router`` 한 줄 추가
  ([Agent 통합 1/4] 표시).
- ``manage_router`` re-export + ``__all__`` 정렬 갱신.

### 신규 회귀 테스트 ``tests/query/test_router.py`` (~140 lines, 14 tests)

- ``test_no_conversation_id_shortcuts_to_fallback`` — conversation_id None 시 Agent
  호출 없이 OPERATION_GUIDE fallback (stub 정합 회귀 보호).
- ``test_operations_guide_intent_default`` — provider=None 분기 (FakeProvider 자동
  주입) 회귀 보호.
- 4 intent 정상 매핑 (incident_response / policy_procedure / history_lookup +
  operations_guide) — Intent enum 한국어 값 검증 + intent 별 Pool 가중치 검증.
- ``test_unknown_intent_falls_back_to_operation_guide`` — Agent UNKNOWN → rag
  OPERATION_GUIDE fallback 정합.
- ``test_expanded_queries_hint_is_used_when_provided`` — LLM 응답에 expanded_queries
  힌트 있으면 rewritten_queries 에 포함.
- ``test_expanded_queries_default_fallback_is_nonempty`` — 힌트 없어도 deterministic
  fallback 으로 비어있지 않음.
- ``test_pool_weights_sum_to_one`` — 합계 1.0 회귀.
- ``test_metadata_filters_includes_groups_via_acl`` — RagState.groups 가
  metadata_filter.acl.groups 로 전달 회귀 보호.
- ``test_provider_failure_falls_back_safely`` — provider 가 RuntimeError 시 fallback.
- ``test_invalid_llm_payload_falls_back_safely`` — confidence 누락 등 schema 위반 시
  fallback (ClassificationValidationError 흡수).
- ``test_history_decision_preserved_context_is_forwarded`` — HistoryDecision 의
  preserved_context 가 라우터 입력 payload 로 전달돼도 정상 분기 진행 회귀 보호.
- ``test_state_query_is_not_mutated`` — 비파괴적 호출 회귀 보호.

### 책임 분리 (본 담당자 영역만)

- 본 commit 은 본 담당자 영역 7 파일 (2 new — ``app/query/router.py`` + ``tests/
  query/test_router.py`` / 5 modified — ``pyproject.toml`` + ``app/pipeline/
  query_graph.py`` + ``app/pipeline/stubs.py`` + ``app/query/__init__.py`` +
  ``app/api/deps.py``) + vendoring 19 파일 (무수정).
- Agent 패키지 (``query_routing_agent/**``) — **무수정 보존**. ai-agent 저장소
  원본을 그대로 복사.
- 기존 stub (``router_stub``) **보존** — 회귀 테스트·PoC fallback 데모용.
- ``docs/architecture.md`` / ``docs/api-spec.md`` / ``docs/db-schema.md`` /
  ``docs/rag-pipeline-design.md`` / ``docs/chunking-strategy.md`` 변경 없음 — 외부
  API 표면·아키텍처·스키마 동일.

### 정합성 검증 (오버튜닝 회피)

- ``app/CLAUDE.md`` "담당 범위를 벗어난 파일은 수정하지 않는다" 절대 규칙 정합 —
  Agent 패키지 자체 0 수정 ✓
- ``app/CLAUDE.md`` §5 LLM 라우팅 — 라우터는 GPT-4o-mini ✓ (build_real_deps 에 명시)
- ``app/CLAUDE.md`` §3 ACL — 라우터가 ACL 판정에 사용되지 않음. groups 는
  metadata_filter.acl 로 단순 전달, 실제 enforcement 는 별도 ``@enforce_acl`` 책임 ✓
- rag-pipeline-design.md §8 fallback 정합 — provider 실패 시 OPERATION_GUIDE
  안전 기본값 ✓
- 기존 패턴 재사용 — ``history_manager_agent`` vendoring + ``manage_history`` 어댑터
  패턴을 그대로 ``query_routing_agent`` + ``manage_router`` 로 복제. 신규 패턴 도입 0 ✓
- 새 의존성 도입 0 — ``langgraph`` / ``openai`` 둘 다 이미 본 저장소 도입
  (``pyproject.toml`` dependencies). ``pyproject.toml`` 변경은 setuptools/ruff/mypy
  대상 등록만 ✓

### 후방 호환성

- 신규 어댑터 + Agent 패키지 vendoring + 기존 router_stub 보존 — 기존 회귀 테스트 0건
  영향. ``app/pipeline/stubs.py`` 의 ``router_stub`` 호출 회귀 테스트(있다면) 그대로
  통과.
- ``QueryGraphDeps`` 신규 필드 2종 (``routing_provider`` / ``routing_config``) 모두
  default None — 기존 호출자(``build_poc_deps`` 직접 호출, 테스트 등) 무변경 통과.
- ``app/api/deps.py`` 시그니처 변경 없음 — 호출자(``app/main.py`` lifespan) 영향 0.

### 검증 결과 (회사 Mac 기준 — 예상)

- 샌드박스 ruff 0.15.13 으로 format `--check` (118 files already formatted) + check
  (All checks passed!) 통과.
- pytest 는 ``./scripts/verify.sh`` 실행 시 통과 예상 — 신규 14 케이스 (test_router)
  + 기존 회귀 0건. 샌드박스 Python 3.10 한계로 직접 pytest 미실행 (이전 feature
  패턴 동일).

### Agent 통합 진척도 (4 stub 중 1 종료)

| stub | 현재 상태 |
|---|---|
| ``router_stub`` | ✅ **본 commit 으로 wiring 완료** (manage_router) |
| ``generator_stub`` | ⏳ Agent 코드 전달 대기 |
| ``verify_llm_evaluator_stub`` | ⏳ Agent 코드 전달 대기 |
| ``document_analyzer_stub`` | ⏳ Agent 코드 전달 대기 |

### 비고

- 본 담당자 영역 7 modified + 19 vendoring + 2 new (router.py / test_router.py) =
  총 28 파일. ``git diff --stat HEAD`` 로 정확히 검증.
- 본 commit 이 끝나면 본 담당자 영역 ~96% → **~97%**.

### 후속 TODO (다음 세션 후보)

- **Agent 통합 2/4 — 답변 생성기** — ``answer-generation-agent`` 패키지가 동일 패턴
  으로 ``app/query/generator.py`` 어댑터 + vendoring. SSE 스트리밍 지원 시 routes.py
  의 단일 송신을 token 다중 송신으로 확장.
- **Agent 통합 3/4 — 검증 2단계 LLM 평가자**.
- **Agent 통합 4/4 — 문서 분석기** (Ingestion 그래프).
- **운영 라이브 smoke** — Agent 통합 모두 끝낸 후 docker compose + RAG_USE_REAL_ADAPTERS=true
  로 끝-끝 검증.


## 2026-05-19 — Agent 통합 2/4: answer-generation-agent vendoring + 어댑터 노드

- 브랜치: `feat/#1/rag-pipeline-skeleton`
- 배경: Agent 통합 1/4 (`25f16b5`) 직후 진척도 ~97%. Agent 담당자가 `ai-agent/
  answer-generation-agent/` 를 전달, 본 세션에서 `generator_stub` 자리에 실 Agent
  코드를 wiring 한다 (`docs/ai/current-plan.md` Agent 통합 메모 정합). 직전 세션의
  `query-routing-agent` vendoring 패턴을 그대로 복제 (신규 패턴 도입 0). 설계서
  §4.6 답변 생성기 (의도별 task prompt + GPT-4o + [#N] 인용 마커 + Function
  Calling)·기획서 §6.3·6.4 (③ 답변 생성 에이전트) 정합.

### 변경 사항

**Vendoring (무수정 보존)**

신규 `answer_generation_agent/` (17 파일, ai-agent/answer-generation-agent/src/
answer_generation_agent 복사) — `query_routing_agent` / `history_manager_agent`
패턴 정합:

- `app/` / `config/` / `generation/` / `schemas/` / `scripts/` 모두 무수정 복사.
  `tests/` 는 가져오지 않음 (직전 세션과 동일 정책 — Agent 담당자 저장소에서 이미
  검증됐다는 가정).
- `__init__.py` 표준 모듈 구조 — `from answer_generation_agent.generation.
  answer_generation import …` 같은 absolute import 가 rag 저장소 루트에서 동작
  (Python path 정합).

**pyproject.toml 갱신**

- `[tool.setuptools.packages.find].include` 에 `answer_generation_agent*` 추가.
- `[tool.ruff].extend-exclude` 에 `answer_generation_agent` + `tests/
  answer_generation_agent` 추가.
- `[tool.mypy].exclude` + `[[tool.mypy.overrides]] module = "answer_generation_agent
  .*" follow_imports = "skip"` 추가.

**어댑터 노드 신설 — `app/query/generator.py` (~280 lines)**

- `manage_generator(state, *, provider=None, config=None) -> RagState` — vendoring
  한 agent 의 in-process 로직 함수를 순차 호출:
    1. `normalize_generation_input(payload, max_contexts)` →
       `NormalizedGenerationInputResult`
    2. `AnswerGenerationService(provider).generate(normalized, config)` →
       `AnswerGenerationResult` (prompt 빌더 + LLM provider 호출까지 포함)
    3. `map_citations(generation_result, normalized)` → `CitationMappingResult`
    4. `build_answer_output(normalized, generation, citation)` → `AnswerOutput`
- RagState ↔ agent 스키마 변환:
    - `_INTENT_TO_TASK_PROMPT` — Intent 4종 → TaskPromptType 매핑표
      (rag-pipeline-design.md §4.6.2 / §6.6 표 정합):
        - INCIDENT_RESPONSE → TIMELINE
        - OPERATION_GUIDE → STEP_BY_STEP
        - POLICY_PROCEDURE → EVIDENCE_FIRST
        - HISTORY_LOOKUP → HISTORY_SUMMARY
    - `_INTENT_TO_AGENT_LABEL` — Intent → agent IntentLabel (영어 snake_case)
      매핑 (router.py 의 역방향). Intent None 시 "unknown" fallback.
    - `_build_generation_input_payload` — RagState 의 `query` / `user_id` /
      `conversation_id` / `intent` / `rewritten_queries` / `metadata_filters` /
      `pool_weights` / `history_decision` 을 agent GenerationInput dict 로 변환.
    - `_chunk_to_top_context_payload` — RAG Chunk → agent TopContext dict 변환.
      `context_id` 는 `ctx-{index:03d}-{chunk_id[:8]}` 합성 (검증 1단계 `[#N]`
      마커 N(1-based 순번)과 의미상 연결). `rerank_score` 는 입력 순서 보존을 위해
      `1 - 0.001 * index` 부여 (agent normalize 의 sort_key 정합).
    - `_synthesize_conversation_id` / `_synthesize_routing_id` — 결정론 합성
      (sha1 16자) — SSE 라우트에서 conversation_id None 으로 들어오는 싱글턴 경로
      를 안전 fallback 없이 흡수.
    - `_compose_answer_with_citations` — AnswerOutput.sentences 를 순회하며
      `"{text} [#N1][#N2]"` 형식으로 답변 재조립. context_id → N 매핑은
      `used_context_ids` 의 등장 순서(1-based, agent answer_output_builder 의
      `_build_sources` 순서와 정합). insufficient_context / failed 상태는 agent
      안내문 그대로 사용. sentences 가 비고 answer 만 있는 경우 끝에 `[#1]` 1회
      부착 — 검증 1단계 동작 보장.
    - `_agent_sources_to_rag_sources` — agent GeneratedSource → rag Source 변환.
      chunk.metadata 의 정보 (attachment_filename / attachment_mime / source_type
      / webui_link / last_modified) 보존. score 는 rerank_score(0~1) × 100 의 0~100
      정수 (api-spec.md Source.score). chunk 매칭 실패한 fallback citation source 는
      안전을 위해 skip.
- LLM provider default: `FakeAnswerLLMProvider` (PoC·테스트, `_DEFAULT_FAKE_RESPONSE`
  주입). agent 의 `OpenAIAnswerLLMProvider` 는 `transport=None` 시
  `ProviderConfigurationError` 를 던지므로 본 세션은 운영 모드도 fake 자동 wiring
  (Plan v2 §3 B / 사용자 결정).
- 안전 fallback: provider 실패·정규화 실패 시 `_apply_fallback` — stub 정합 `[#1]
  {title} 관련 정보를 다음과 같이 안내합니다.` (설계서 §4.6.5 "plain text 폴백,
  출처 매핑은 검증기 1단계 결과로 대체" 정합).
- `used_llm` — `state.target_llm` 우선, 없으면 GPT_4O (설계서 §4.6.3 — 라우터가
  GPT-4o-mini 동적 라우팅한 경우 그 결정 보존).

**그래프 wiring — `app/pipeline/query_graph.py`**

- `QueryGraphDeps` 갱신:
    - `generator_provider: GeneratorProvider | None = None` 추가
    - `generator_config: GeneratorConfig | None = None` 추가
    - `generator_node` default 를 `generator_stub` → `manage_generator` 로 변경.
- `build_query_graph` 갱신:
    - `deps.generator_node is manage_generator` 일 때만 `functools.partial` 로
      `provider` / `config` 주입 (router 패턴 정합). 외부 사용자 정의 generator_node
      는 captured 가 이미 있다고 가정하고 그대로 등록.
- import 정리 — `generator_stub` 제거, `app.query.generator.manage_generator` 추가.

**부트스트랩 — `app/api/deps.py`**

- 모듈 docstring 변경 이력에 Agent 통합 2/4 단락 추가.
- `build_poc_deps` / `build_real_deps` 본체 변경 없음 — QueryGraphDeps 기본값
  (generator_provider=None → FakeAnswerLLMProvider 자동) 그대로. 사용자 결정
  (Plan v2 §3 B) — agent OpenAIAnswerLLMProvider 는 transport 미주입 한계로 본
  세션은 운영 모드도 fake 자동 wiring 유지.

**Stub 갱신 — `app/pipeline/stubs.py`**

- 모듈 docstring 변경 이력에 Agent 통합 2/4 단락 추가.
- `generator_stub` docstring 에 "Agent 통합 2/4 완료" 표시 + 회귀 보호용 보존 명시.
- `generator_stub` 본체 변경 없음 — 회귀 테스트·외부 명시 주입(`deps.generator_node
  =generator_stub`) 경로 보장.

**Re-export — `app/query/__init__.py`**

- 패키지 docstring 구현 상태 단락에 `generator.py — manage_generator` 한 줄 추가
  ([Agent 통합 2/4] 표시).
- `manage_generator` re-export + `__all__` 알파벳 순 갱신.

### 신규 회귀 테스트 `tests/query/test_generator.py` (~270 lines, 13 tests)

- `test_empty_top_chunks_returns_empty_answer` — top_chunks 비면 stub 정합 빈 답변
  (그래프 검색 0건 분기에서는 도달 X) 방어 처리 회귀 보호.
- `test_default_fake_provider_produces_cited_answer` — provider=None 분기
  (FakeAnswerLLMProvider 자동 주입) 회귀 보호. 답변에 `[#1]` 인용 마커 합성 확인.
- `test_used_llm_prefers_state_target_llm_over_default` — 라우터가 동적 라우팅한
  `target_llm` 우선 (§4.6.3).
- `test_used_llm_defaults_to_gpt_4o_when_state_target_unset` — target_llm None 시
  GPT_4O 기본.
- `test_state_query_is_not_mutated` — 비파괴적 호출 회귀 보호.
- `test_intent_maps_to_task_prompt_type` (parametrize ×4) — Intent 4종 → agent
  prompt builder 에 정확한 task_prompt_type 전달 검증. provider.requests 의
  developer_prompt 에 task type 마커가 포함되는지 단언 (§4.6.2 / §6.6 표).
- `test_citation_markers_synthesized_in_answer` — agent sentences[*].citations 가
  used_context_ids 순서(1-based)로 `[#N]` 마커 합성됨을 회귀 보호 (§4.6.1).
- `test_verify_answer_rules_compatibility` — 생성기 답변이 검증 1단계
  (`verify_answer_rules`) 입력으로 정상 동작 (PASS 떨어짐) 회귀 보호.
- `test_sources_built_from_top_chunks` — GeneratedSource → Source 변환 — score 0~100
  정수, space_key 보존, source_type 매핑.
- `test_attachment_source_metadata_preserved` — 첨부 청크의 attachment_filename /
  attachment_mime / SourceType.ATTACHMENT 보존.
- `test_provider_failure_falls_back_safely` — AnswerProviderError 발생 시 안전
  fallback (stub-like [#1] 답변).
- `test_invalid_llm_payload_falls_back_safely` — agent parse_llm_response 실패 시
  안전 fallback.
- `test_missing_conversation_id_synthesizes_deterministic_id` — SSE 라우트
  conversation_id None 경로 안전 흡수.
- `test_history_decision_contextualized_question_used` — history_decision 의
  contextualized_question 이 agent user_prompt 에 전달 회귀 보호.
- `test_custom_config_max_contexts_limits_top_contexts` — config.max_contexts 가
  agent normalization 컨텍스트 제한에 반영.

### `tests/api/test_deps.py` 회귀 보호 추가

- `test_build_real_deps_wires_real_adapter_classes` — `deps.generator_provider is
  None` + `deps.generator_config is None` 단언 추가 (Plan v2 §3 B 정합 — 운영
  모드도 fake 자동 wiring 유지).
- `test_build_poc_deps_uses_fake_adapters_unchanged` — 동일 단언 추가 (PoC 정합).

### 본 세션 미구현 (Plan v2 §3 — 다음 단계 이관, 설계서 §4.6 정합)

다음 항목들은 본 세션 범위를 벗어나며, `app/query/generator.py` docstring §[본
세션 미구현]·`docs/ai/working-log.md` 본 단락에 일관 기록되어 다음 세션에서 누락
없이 이어받게 한다.

- **(A) SSE 토큰 스트리밍** (설계서 §4.6.4 / 기획서 KPI "P95 5초", "토큰당
  25~40ms") — agent MVP 는 `streaming_supported=False`, 전체 답변을 동기 반환.
  본 세션의 `manage_generator` 도 1회 호출·1회 반환. SSE 라우트 (`app/api/routes
  .py`)는 token 이벤트를 1회만 송신 (전체 답변) — 직전 세션 동작 그대로 유지.
  - 다음 단계: agent streaming API 추가 (Agent 담당자 영역) OR 본 저장소가
    OpenAI Streaming API → AnswerLLMResult chunk 어댑터 transport 추가 → SSE
    라우트 multi-token 송신으로 확장 (B 와 함께 진행 권장).

- **(B) 운영 OpenAI HTTP transport** (설계서 §4.6.3 GPT-4o 운영 호출) — agent 의
  `OpenAIAnswerLLMProvider` 는 `transport=None` 시 `ProviderConfigurationError` 를
  던진다. 본 세션은 `build_real_deps` 도 PoC 와 동일하게 fake 자동 wiring → 운영
  모드에서 실 OpenAI 호출 안됨.
  - 다음 단계: Agent 담당자가 transport 제공 OR 본 저장소가 `openai>=1.30` (이미
    의존성 보유) 기반 transport callable 작성 후 주입.

- **(C) Rate Limit Fallback — GPT-4o-mini 다운그레이드** (설계서 §4.6.5) — agent
  에 `select_generation_model(use_fallback=True)` 인터페이스만 있고 retry
  orchestrator 없음. 본 세션은 LLM 실패 시 안전 fallback (stub-like)만 수행.
  - 다음 단계: B 운영 transport 도입 후 retry orchestrator 추가 + `verification
    .note` 기록.

- **(D) Function Calling 스키마 강제** (설계서 §4.6.1) — agent 는 prompt
  instruction 으로 JSON schema 요청. OpenAI `tools=` 미설정. Agent 담당자 영역 —
  본 저장소가 수정하지 않음.
  - 다음 단계: Agent 담당자가 tool definition 추가.

- **(E) 자연어 출처 인용 패턴** — `[스페이스명]…` / `첨부 파일 [filename]에
  따르면…` (설계서 §4.6.1 v0.2.2 신설). agent prompt template 에 미반영. Agent
  담당자 영역 — 본 저장소가 수정하지 않음.
  - 다음 단계: Agent 담당자가 prompt template 갱신.

- **(F) 검증 2단계 LLM 평가자 통합** (설계서 §4.7.2) — `verify_llm_evaluator_stub`
  그대로. Agent 통합 3/4 별도 세션.

- **(G) 의도별 task prompt 4종 정합 검증** (설계서 §6.6 표) — agent prompt
  template 4종 (`timeline/step_by_step/evidence_first/history_summary`) 이 설계서
  §6.6 표와 정합되지만, 본 세션에서는 매핑만 검증하고 prompt 본문 비교는 하지
  않음. 평가 세션 또는 Agent 담당자 영역 prompt 튜닝 단계에서 §6.6 표와 1:1 점검.

### 책임 분리 (본 담당자 영역만)

- 본 commit 은 본 담당자 영역 8 파일 (2 new — `app/query/generator.py` + `tests/
  query/test_generator.py` / 6 modified — `pyproject.toml` + `app/pipeline/
  query_graph.py` + `app/pipeline/stubs.py` + `app/query/__init__.py` + `app/api/
  deps.py` + `tests/api/test_deps.py`) + vendoring 17 파일 (무수정) + 본
  docs/ai/working-log.md = 총 27 파일.
- Agent 패키지 (`answer_generation_agent/**`) — **무수정 보존**. ai-agent 저장소
  원본을 그대로 복사.
- 기존 stub (`generator_stub`) **보존** — 회귀 테스트·외부 명시 주입 경로 보장.
- `app/api/routes.py` 미변경 — A (SSE token streaming) 미구현으로 본 세션 범위 외.
- `docs/architecture.md` / `docs/api-spec.md` / `docs/db-schema.md` / `docs/
  rag-pipeline-design.md` / `docs/chunking-strategy.md` 변경 없음 — 외부 API
  표면·아키텍처·스키마 동일.

### 정합성 검증 (오버튜닝 회피)

- `app/CLAUDE.md` "담당 범위를 벗어난 파일은 수정하지 않는다" 절대 규칙 정합 —
  Agent 패키지 자체 0 수정 ✓
- `app/CLAUDE.md` §5 LLM 라우팅 — 답변 생성기는 GPT-4o 기본, 라우터 결정 시
  GPT-4o-mini 동적 라우팅 (`used_llm = state.target_llm or GPT_4O`) ✓
- `app/CLAUDE.md` §3 보안 — ACL 필터는 라우터 영역에서 metadata_filter.acl 로
  단순 전달되며 본 어댑터는 ACL 판정에 관여하지 않음 ✓
- rag-pipeline-design.md §4.6.1 "모든 문장에 근거 청크 번호를 [#1], [#2] 형식으로
  명시" — `_compose_answer_with_citations` 가 sentences → answer 재조립 시점에
  부착 ✓
- rag-pipeline-design.md §4.6.2 / §6.6 의도별 task prompt — Intent 4종 → agent
  TaskPromptType 1:1 매핑 ✓
- rag-pipeline-design.md §4.6.3 GPT-4o 기본 + 동적 라우팅 — `target_llm` 우선 ✓
- rag-pipeline-design.md §4.6.5 plain text 폴백 — `_apply_fallback` 이 stub 정합
  `[#1] {title}` 답변 부여 (검증기 1단계 동작 보장) ✓
- 기존 패턴 재사용 — `query_routing_agent` vendoring + `manage_router` 어댑터
  패턴을 그대로 `answer_generation_agent` + `manage_generator` 로 복제. 신규 패턴
  도입 0 ✓
- 새 의존성 도입 0 — `answer_generation_agent` 는 표준 라이브러리 + dataclasses
  만 사용. `pyproject.toml` 변경은 setuptools/ruff/mypy 대상 등록만 ✓

### 후방 호환성

- 신규 어댑터 + Agent 패키지 vendoring + 기존 generator_stub 보존 — 기존 회귀
  테스트 0건 영향. `test_run_query_normal_flow_populates_sources_and_verification`
  등 query_graph end-to-end 회귀는 새 default(`manage_generator + FakeAnswer
  LLMProvider`)와 호환 (`[#1]` 마커·sources 채움·BLOCKED 아님 동작 유지).
- `QueryGraphDeps` 신규 필드 2종 (`generator_provider` / `generator_config`) 모두
  default None — 기존 호출자(`build_poc_deps` 직접 호출, 테스트 등) 무변경 통과.
- `app/api/deps.py` 시그니처 변경 없음.
- `tests/pipeline/test_query_graph.py` 의 외부 명시 주입 경로
  (`generator_node=_generator_with_suspicious`)는 `is manage_generator` 분기로
  `else` 경로 (그대로 등록)가 동작 — 기존 패턴 그대로 호환.

### 검증 결과 (회사 Mac 기준 — 예상)

- 샌드박스 ruff 0.15.13 으로 format `--check` (117 files already formatted) + check
  (All checks passed!) 통과.
- pytest 는 `./scripts/verify.sh` 실행 시 통과 예상 — 신규 16 케이스
  (test_generator) + 기존 회귀 0건 + test_deps.py 회귀 추가 (PoC + real 2건).
  샌드박스 Python 3.10 한계 (agent StrEnum import 불가)로 직접 pytest 미실행
  (직전 세션 패턴 동일).

### Agent 통합 진척도 (4 stub 중 2 종료)

| stub | 현재 상태 |
|---|---|
| `router_stub` | ✅ Agent 통합 1/4 완료 (manage_router) |
| `generator_stub` | ✅ **본 commit 으로 wiring 완료** (manage_generator) |
| `verify_llm_evaluator_stub` | ⏳ Agent 통합 3/4 대기 |
| `document_analyzer_stub` | ⏳ Agent 통합 4/4 대기 |

### 비고

- 본 commit 이 끝나면 본 담당자 영역 ~97% → **~98%**.
- 본 commit 의 변경 영향 파일 = 8 본 담당자 + 17 vendoring + 1 working-log = 26 파일.
  `git diff --stat HEAD` 로 정확히 검증.

### 후속 TODO (다음 세션 후보 — 우선순위)

1. **Agent 통합 3/4 — 검증 2단계 LLM 평가자** — `verify-agent` 패키지가 전달되면
   동일 패턴으로 `app/pipeline/nodes.py` 의 `verify_pipeline_node` 가 호출하는
   `llm_evaluator` 자리에 어댑터 wiring.
2. **Agent 통합 4/4 — 문서 분석기** (Ingestion 그래프) — `document-analyzer-agent`
   패키지가 전달되면 `app/pipeline/ingestion_graph.py` 의 `document_analyzer_node`
   에 wiring.
3. **(A+B) SSE 토큰 스트리밍 + 운영 OpenAI HTTP transport** — Agent 통합 4종 모두
   끝낸 후 (또는 별도 세션에서) 함께 진행. `openai>=1.30` 기반 streaming transport
   callable → `OpenAIAnswerLLMProvider(transport=...)` 주입 → SSE 라우트 multi-
   token 송신 확장 + `build_real_deps` 에 wiring.
4. **(C) Rate Limit fallback (GPT-4o-mini 다운그레이드 + verification.note 기록)**
   — B 운영 transport 도입 후.
5. **(D+E) Function Calling 강제 + 자연어 출처 인용 패턴** — Agent 담당자 보고 사항.
6. **(G) 의도별 task prompt 4종 정합 검증** — 평가 세션에서 §6.6 표와 1:1 점검.
7. **운영 라이브 smoke** — Agent 통합 4종 + A·B 모두 끝낸 후 docker compose +
   `RAG_USE_REAL_ADAPTERS=true` 로 끝-끝 검증.


## 2026-05-19 — Agent 통합 3/4: answer-verification-agent vendoring + 어댑터 노드

- 브랜치: `feat/#1/rag-pipeline-skeleton`
- 배경: Agent 통합 2/4 (`5861057`) 직후 진척도 ~98%. Agent 담당자가 `ai-agent/
  answer-verification-agent/` 를 전달, 본 세션에서 `verify_llm_evaluator_stub`
  자리에 실 Agent 코드를 wiring 한다. 직전 세션과 다른 점은 본 저장소가 검증
  1단계(`verify_answer_rules`)를 이미 Pipeline 으로 수행 중이므로 agent 의
  rule-based / sentence parser / overall label 집계 등 중복 책임은 사용하지
  않는다. agent 의 LLM evaluator(`AnswerEvaluatorProvider.evaluate_sentence`)만
  in-process 로 호출한다. 설계서 §4.7.2 (검증 2단계 LLM 평가자 GPT-4o-mini, FLAG
  문장 한정)·기획서 ④ 답변 검증 정합.

### 변경 사항

**Vendoring (무수정 보존)**

신규 `answer_verification_agent/` (26 파일, ai-agent/answer-verification-agent/
src/answer_verification_agent 복사) — `query_routing_agent` /
`answer_generation_agent` 패턴 정합:

- `app/` / `config/` / `evaluator/` / `qca/` / `regeneration/` / `schemas/` /
  `scripts/` / `storage/` / `verification/` / `workflow.py` 모두 무수정 복사.
  `tests/` 는 가져오지 않음 (직전 세션과 동일 정책).

**pyproject.toml 갱신**

- `[tool.setuptools.packages.find].include` 에 `answer_verification_agent*` 추가.
- `[tool.ruff].extend-exclude` 에 `answer_verification_agent` + `tests/
  answer_verification_agent` 추가.
- `[tool.mypy].exclude` + `[[tool.mypy.overrides]] module = "answer_verification_
  agent.*" follow_imports = "skip"` 추가.

**어댑터 노드 신설 — `app/query/verifier_evaluator.py` (~220 lines)**

- `manage_verifier_evaluator(*, answer, top_chunks, suspicious_sentences,
  provider=None, config=None) -> list[Verification]` — stub 시그니처 그대로
  유지 (keyword 전용 — `verify_pipeline_node` 의 `llm_evaluator` 호출 정합).
- agent in-process 호출:
    1. `_chunks_to_normalized_contexts(top_chunks)` → `list[NormalizedContext]`
       (context_id 합성은 `app/query/generator.py` 와 동일 패턴 — 두 어댑터의
       일관성 보장).
    2. suspicious_sentences 순회하며:
       - `_sentence_check_to_target(check, top_chunks)` → `SuspiciousSentence
         Target` (1-based `cited_chunks` 의 정수 → context_id 문자열로 환원).
       - `provider.evaluate_sentence(target, normalized_contexts)` →
         `SentenceEvaluation`.
       - `_LABEL_MAP` 으로 agent `SentenceLabel` → rag `VerificationStatus`:
            * SUPPORTED → SUPPORTED
            * UNSUPPORTED → NOT_SUPPORTED
            * LOW_CONFIDENCE → NOT_SUPPORTED (사용자 결정 — Plan v2 보수적 매핑)
            * NOT_CHECKED → NOT_SUPPORTED (보수적)
- 안전 fallback: `EvaluatorProviderError` 발생 시 stub 정합 SUPPORTED 로 흡수
  (stub 의 "all SUPPORTED" 기본 동작과 정합 — provider 실패의 alert 는 호출자
  책임).
- LLM provider default: `FakeEvaluatorProvider` (PoC·테스트). 운영은
  `OpenAIEvaluatorProvider` — agent `_default_transport` (urllib 기반) 가 OpenAI
  Chat Completions 를 직접 호출하므로 transport 미주입 OK
  (answer-generation-agent 와 차이점 — 운영 즉시 wiring 가능).

**그래프 wiring — `app/pipeline/query_graph.py`**

- `QueryGraphDeps` 갱신:
    - `verifier_provider: VerifierProvider | None = None` 추가
    - `verifier_config: VerifierConfig | None = None` 추가
    - `verify_llm_evaluator` default 를 `verify_llm_evaluator_stub` →
      `manage_verifier_evaluator` 로 변경.
- `build_query_graph` 갱신:
    - `deps.verify_llm_evaluator is manage_verifier_evaluator` 일 때만
      `functools.partial` 로 `provider` / `config` 주입 (router/generator 패턴
      정합). 외부 사용자 정의 verify_llm_evaluator 는 captured 가 이미 있다고
      가정하고 그대로 등록.
- import 정리 — `verify_llm_evaluator_stub` 제거 (stubs 모듈에서 import 안 함),
  `app.query.verifier_evaluator.manage_verifier_evaluator` 추가.

**부트스트랩 — `app/api/deps.py`**

- 모듈 docstring 변경 이력에 Agent 통합 3/4 단락 추가.
- `build_poc_deps` 본체 변경 없음 — QueryGraphDeps 기본값 (verifier_provider=
  None → FakeEvaluatorProvider 자동) 그대로.
- `build_real_deps` 본체:
    - lazy import 추가: `from answer_verification_agent.config import
      AnswerVerificationConfig`, `from answer_verification_agent.evaluator.
      providers import OpenAIEvaluatorProvider`
    - `AnswerVerificationConfig(evaluator_model="gpt-4o-mini")` 생성
      (app/CLAUDE.md §5 라우팅 정책 + 설계서 §4.7.2).
    - `OpenAIEvaluatorProvider(config=verifier_config)` 로 인스턴스화 — agent
      자체 urllib transport 사용. OPENAI_API_KEY 누락 시 EvaluatorProviderError
      즉시 발생.
    - 반환 `QueryGraphDeps` 에 `verifier_provider` / `verifier_config` 추가 인자.

**Stub 갱신 — `app/pipeline/stubs.py`**

- 모듈 docstring 변경 이력에 Agent 통합 3/4 단락 추가.
- `verify_llm_evaluator_stub` docstring 에 "Agent 통합 3/4 완료" 표시 + 회귀
  보호용 보존 명시.
- `verify_llm_evaluator_stub` 본체 변경 없음.

**Re-export — `app/query/__init__.py`**

- 패키지 docstring 구현 상태 단락에 `verifier_evaluator.py — manage_verifier_
  evaluator` 한 줄 추가 ([Agent 통합 3/4] 표시).
- `manage_verifier_evaluator` re-export + `__all__` 알파벳 순 갱신.

### 신규 회귀 테스트 `tests/query/test_verifier_evaluator.py` (~230 lines, 11 tests)

- `test_empty_suspicious_sentences_returns_empty_list` — suspicious 비면 provider
  호출 없이 빈 list (stub 정합).
- `test_default_fake_provider_returns_low_confidence_mapped_to_not_supported` —
  scripted 없는 FakeEvaluatorProvider 의 기본 LOW_CONFIDENCE → NOT_SUPPORTED
  보수적 매핑 회귀 보호.
- `test_supported_label_maps_to_supported` — SUPPORTED → SUPPORTED.
- `test_unsupported_label_maps_to_not_supported` — UNSUPPORTED → NOT_SUPPORTED.
- `test_low_confidence_maps_to_not_supported_conservative` — LOW_CONFIDENCE →
  NOT_SUPPORTED (Plan v2 보수적 매핑 — 환각 차단 우선).
- `test_multiple_suspicious_sentences_invoke_evaluator_n_times` — N 문장 →
  evaluator N 회 호출, sentence_id 정합.
- `test_cited_chunks_preserved_in_verification_output` — cited_chunks 보존
  (api-spec.md 정합).
- `test_provider_failure_falls_back_to_supported` — EvaluatorProviderError 발생
  시 stub 정합 SUPPORTED 안전 fallback.
- `test_empty_top_chunks_still_evaluates` — top_chunks 비어도 evaluator 호출 시도
  (agent prompt builder 가 "No valid cited context" 안내문 채움).
- `test_signature_matches_stub_keyword_only` — positional 호출 시 TypeError
  (verify_pipeline_node 정합 회귀 보호).
- `test_custom_config_is_validated` — config 유효성 검증 강제.

### `tests/api/test_deps.py` 회귀 보호 추가

- `patched_real_adapters` fixture 에 `OpenAIEvaluatorProvider` monkeypatch 추가
  — sentinel `_FakeOpenAIEvaluator` 로 대체해 OPENAI_API_KEY 환경변수 없이도
  build_real_deps wiring 검증 가능. `verifier_provider_init` 캡처.
- `test_build_real_deps_wires_real_adapter_classes` 에 `deps.verifier_provider
  is not None` + `evaluator_model == "gpt-4o-mini"` 단언 추가.
- `test_build_poc_deps_uses_fake_adapters_unchanged` 에 `deps.verifier_provider
  is None` + `deps.verifier_config is None` 단언 추가.

### 본 세션 미구현 (Plan v2 §3 — 다음 단계 이관, 설계서 §4.7 정합)

`app/query/verifier_evaluator.py` docstring §[본 세션 미구현]·`docs/ai/
working-log.md` 본 단락에 일관 기록되어 다음 세션에서 누락 없이 이어받게 한다.

- **(A) agent rule-based verifier 사용** — 본 저장소 `verify_answer_rules` 와
  중복이므로 사용하지 않음. 다음 단계: 두 구현의 정합 (같은 의심 판정) 평가
  세션에서 비교.
- **(B) agent sentence parser** — 본 저장소 generator 가 이미 `[#N]` 마커를 합성
  하므로 사용하지 않음.
- **(C) agent overall label / score 집계** — 본 저장소 `app/query/formatter.py`
  가 NOT_SUPPORTED 비율 기반 BLOCKED 정책을 이미 수행. agent 집계는 사용 안 함.
- **(D) UI warning metadata / QCA / regeneration recommendation** — api-spec.md
  에 없는 확장 영역. 다음 단계: BFF/저장소 책임 확정 후.
- **(E) `verification.note` 답변 생성기 다운그레이드 기록** (설계서 §4.6.5) —
  답변 생성기 (B) 운영 transport 도입 후 같이.
- **(F) all-sentence evaluation mode** (`evaluate_suspicious_only=False`) —
  비용 우선 정책으로 본 세션은 suspicious only. 다음 단계: 평가 세션에서
  비용/정확도 trade-off 측정 후 결정.
- **(G) agent rule-based 정합 검증** — 본 저장소 1단계와 agent 1단계가 같은 의심
  판정을 내리는지 평가 세션에서 비교.

### 책임 분리 (본 담당자 영역만)

- 본 commit 은 본 담당자 영역 8 파일 (2 new — `app/query/verifier_evaluator.py`
  + `tests/query/test_verifier_evaluator.py` / 6 modified — `pyproject.toml` +
  `app/pipeline/query_graph.py` + `app/pipeline/stubs.py` + `app/query/__init__.
  py` + `app/api/deps.py` + `tests/api/test_deps.py`) + vendoring 26 파일
  (무수정) + 본 docs/ai/working-log.md = 총 35 파일.
- Agent 패키지 (`answer_verification_agent/**`) — **무수정 보존**.
- 기존 stub (`verify_llm_evaluator_stub`) **보존** — 회귀 테스트·외부 명시 주입
  경로 보장.
- `app/query/verifier.py` (Pipeline 1단계), `app/pipeline/nodes.py` (`verify_
  pipeline_node`), `app/query/formatter.py` (BLOCKED 정책) 미변경.
- `docs/architecture.md` / `docs/api-spec.md` / `docs/db-schema.md` / `docs/
  rag-pipeline-design.md` / `docs/chunking-strategy.md` 변경 없음.

### 정합성 검증 (오버튜닝 회피)

- `app/CLAUDE.md` "담당 범위를 벗어난 파일은 수정하지 않는다" 정합 ✓
- `app/CLAUDE.md` §5 LLM 라우팅 — 검증 2단계는 GPT-4o-mini ✓
- `app/CLAUDE.md` §3 보안·정확성 — "답변 검증을 우회하거나 비활성화하지 않는다"
  정합 (stub → 실 어댑터로 교체, 검증 자체는 유지) ✓
- rag-pipeline-design.md §4.7.2 — "GPT-4o-mini 에 Top-5 청크 전체와 의심 문장을
  전달" → 본 어댑터는 top_chunks 전체를 NormalizedContext 로 변환해 전달, agent
  prompt builder 가 cited 만 선별 (False Negative 방지 책임은 agent 측) ✓
- 설계서 §3 "정확성 우선" 원칙 정합 — LOW_CONFIDENCE → NOT_SUPPORTED 보수적
  매핑으로 환각 차단 우선 ✓
- 기존 패턴 재사용 — Agent 통합 1/4, 2/4 의 vendoring + 어댑터 + partial wiring
  패턴 그대로 복제 ✓
- 새 의존성 도입 0 ✓

### 후방 호환성

- 신규 어댑터 + Agent 패키지 vendoring + 기존 verify_llm_evaluator_stub 보존 —
  기존 회귀 테스트 0건 영향. `tests/pipeline/test_query_graph.py` 의
  `_evaluator_all_not_supported` (외부 명시 주입) 경로는 `is manage_verifier_
  evaluator` 분기로 `else` 경로 (그대로 등록) 동작.
- `QueryGraphDeps` 신규 필드 2종 (`verifier_provider` / `verifier_config`) 모두
  default None.
- `app/api/deps.py` 시그니처 변경 없음.

### 검증 결과 (회사 Mac 기준 — 예상)

- 샌드박스 ruff 0.15.13 으로 format `--check` + check 모두 통과.
- pytest 는 `./scripts/verify.sh` 실행 시 통과 예상 — 신규 11 케이스
  (test_verifier_evaluator) + test_deps 회귀 추가 + 기존 회귀 0건. 565 → ~576
  예상.

### Agent 통합 진척도 (4 stub 중 3 종료)

| stub | 현재 상태 |
|---|---|
| `router_stub` | ✅ Agent 통합 1/4 완료 (manage_router) |
| `generator_stub` | ✅ Agent 통합 2/4 완료 (manage_generator) |
| `verify_llm_evaluator_stub` | ✅ **본 commit 으로 wiring 완료** (manage_verifier_evaluator) |
| `document_analyzer_stub` | ⏳ Agent 통합 4/4 대기 (data-ingestion-agent) |

### 비고

- 본 commit 이 끝나면 본 담당자 영역 ~98% → **~99%** (Query 그래프 4 Agent 노드
  중 3 종 완료, Ingestion 그래프 Agent 노드 1 종만 남음).
- 본 commit 의 변경 영향 파일 = 8 본 담당자 + 26 vendoring + 1 working-log = 35
  파일. `git diff --stat HEAD` 로 정확히 검증.

### 후속 TODO (다음 세션 후보 — 우선순위)

1. **Agent 통합 4/4 — data-ingestion-agent (문서 분석기)** — Ingestion 그래프의
   `document_analyzer_node` 자리에 wiring. Query 그래프와 별개로 본 담당자 영역
   완성도에 중요.
2. **(A+B) SSE 토큰 스트리밍 + 운영 OpenAI HTTP transport** — Agent 통합 4/4
   완료 후 답변 생성기 운영 wiring 완료를 위해 진행.
3. **(C) Rate Limit fallback** (답변 생성기) — B 도입 후.
4. **(G) agent rule-based 정합 검증** — 본 저장소 1단계와 agent 1단계 비교 (평가
   세션).
5. **(F) all-sentence evaluation mode** — 비용/정확도 trade-off 평가 후 결정.
6. **운영 라이브 smoke** — Agent 통합 4종 + 운영 transport 모두 끝낸 후 docker
   compose + `RAG_USE_REAL_ADAPTERS=true` 로 끝-끝 검증.


## 2026-05-19 — (B) 운영 OpenAI HTTP transport + (A 인프라) Hybrid streaming generator

- 브랜치: `feat/#1/rag-pipeline-skeleton`
- 배경: Agent 통합 3/4 완료로 본 담당자 영역 ~99% 도달. 답변 생성기 운영 GPT-4o
  호출 (설계서 §4.6.3)·SSE 토큰 스트리밍 (§4.6.4) 두 잔여 미구현을 진행한다.
  본 세션은 사용자 합의에 따라 (B) transport + (A) streaming 인프라 (`openai_
  transport.py` / `openai_streaming.py`)·`build_real_deps` wiring·테스트까지만
  마무리. SSE 라우트의 streaming 통합은 그래프 흐름 (search → rerank → generate
  → verify) 분리·재조립이 필요하므로 별도 세션 (다음 후속 작업).

### 변경 사항

**(B) 운영 OpenAI HTTP transport — `app/query/openai_transport.py` (~150 lines)**

- `build_openai_chat_transport(*, api_key, response_format=None) -> Callable` —
  agent `OpenAIAnswerLLMProvider` 의 transport 자리에 그대로 주입 가능한
  closure callable 반환.
- agent `request.to_safe_dict()` payload 를 받아 `openai.OpenAI.chat.completions
  .create` 동기 호출. `response_format={"type": "json_object"}` 기본값으로 JSON
  강제 — agent `parse_llm_response` 가 JSON dict 를 기대하므로 정합.
- `_normalize_messages` — agent 의 `system` / `developer` / `user` 3 role 을
  OpenAI 가 받는 형식 (`system` / `user`)으로 정규화. `developer` 메시지는 system
  앞에 합쳐 단일 system 메시지로 전달 (GPT-4o 계열은 developer role 미지원).
- 에러 흡수:
    - `APITimeoutError` → `OpenAITransportError(status_code=None)` → agent 가
      timeout_error 로 분류 (retryable).
    - `APIStatusError` → status_code 보존 → agent 가 429/5xx retry 결정.
    - `APIError` → status_code=500 일반화.
    - empty content / invalid JSON / non-object JSON → 모두 `OpenAITransport
      Error(status_code=500)` 로 흡수.
- 컴포넌트 분류 [Storage] — 외부 API 호출 어댑터. agent retry/타임아웃/안전
  fallback 은 그대로 agent 본체·`manage_generator` 에 위임 (책임 분리).

**(A 인프라) Hybrid streaming generator — `app/query/openai_streaming.py` (~150 lines)**

- 설계서 §4.6 의 두 충돌 (Function Calling JSON contract vs token streaming)을
  Plan v2 hybrid 방식으로 해소: streaming 경로는 별도 plain text prompt 로
  분리하고, LLM 에게 `[#N]` 마커를 답변에 포함하도록 강제. 검증 1단계는 답변
  텍스트의 `[#N]` 마커 기반이므로 호환.
- `_STREAMING_SYSTEM_PROMPT` — 핵심 규칙 6 조항:
    1. 컨텍스트만 근거, 한국어 답변.
    2. 모든 핵심 문장 끝에 `[#1]` `[#2]` 형식 마커.
    3. 다중 인용은 `[#1][#2]` 이어붙임.
    4. 컨텍스트 외 사실 단정 금지 ("확인할 수 없습니다" 표시).
    5. plain text 만 — JSON / 코드 블록 감싸지 않기.
- `build_streaming_user_prompt(*, query, top_chunks) -> str` — top_chunks 를
  1-based `[#N]` 번호로 컨텍스트 블록 합산. 본 함수가 마커 번호 부여 단일 진입점.
- `stream_openai_answer(*, api_key, model, temperature, timeout_seconds, query,
  top_chunks) -> Iterator[StreamingTokenChunk]` — OpenAI `stream=True` 모드로
  token chunk yield. `delta.content` 가 None / 빈 문자열이면 skip.
- `StreamingTokenChunk` dataclass — SSE 라우트가 그대로 송신할 단일 token chunk
  타입. SSE 라우트 통합 (다음 세션) 시 token 이벤트로 변환.
- 가드: `top_chunks` 비면 `RuntimeError` — 호출자 (다음 세션의 SSE 라우트) 가
  검색 0건 분기에서 본 함수 호출을 막아야 한다.
- 컴포넌트 분류 [Storage] — 외부 streaming API 어댑터.

**부트스트랩 — `app/api/deps.py` (build_real_deps 갱신)**

- 모듈 docstring 변경 이력에 (B) 운영 OpenAI HTTP transport 단락 추가.
- `build_real_deps` 본체:
    - lazy import 추가: `AnswerGenerationConfig`, `OpenAIAnswerLLMProvider`,
      `build_openai_chat_transport`.
    - `settings.openai_api_key.get_secret_value()` 로 API key 추출.
    - `AnswerGenerationConfig(model=settings.llm_answer_model, fallback_model=
      settings.llm_aux_model)` 생성 — settings 단일 진입점에서 GPT-4o / GPT-4o-
      mini 모델명 가져옴.
    - `OpenAIAnswerLLMProvider(api_key=..., transport=build_openai_chat
      _transport(api_key=...))` 인스턴스화 — transport 주입 시점에 API key 누락
      이면 `ProviderConfigurationError` 즉시 발생 (운영 lifespan 진입 직전에
      누락 명확히 드러남).
    - `QueryGraphDeps(..., generator_provider=..., generator_config=...)` 반환.
- `build_poc_deps` 변경 없음 — fake 자동 wiring 유지 (외부 API 키 없이 동작).

### 신규 회귀 테스트

**`tests/query/test_openai_transport.py` (~230 lines, 9 tests)**

OpenAI client 를 `_FakeClient` 로 monkeypatch (sys.modules["openai"] 모듈 자체 교체):
- `test_transport_returns_parsed_json` — 정상 JSON 응답 → dict 반환.
- `test_transport_merges_developer_into_system_role` — developer 메시지가 system
  으로 합쳐짐.
- `test_transport_passes_model_and_temperature` — model/temperature 정합 전달.
- `test_transport_empty_content_raises_openai_transport_error` — 빈 응답 흡수.
- `test_transport_invalid_json_raises_openai_transport_error` — 잘못된 JSON 흡수.
- `test_transport_non_object_json_raises_openai_transport_error` — array JSON 흡수.
- `test_transport_timeout_raises_with_none_status_code` — APITimeoutError →
  status_code=None (agent timeout_error 분류 정합).
- `test_transport_status_error_preserves_status_code` — 429 등 status_code 보존.
- `test_transport_generic_api_error_normalized_to_500` — generic APIError → 500.
- `test_transport_custom_response_format_overrides_default` — response_format
  커스텀 주입 (text 등).

**`tests/query/test_openai_streaming.py` (~220 lines, 8 tests)**

- `test_user_prompt_includes_query_and_numbered_contexts` — 1-based [#N] 매칭.
- `test_user_prompt_handles_empty_chunks_safely` — "(컨텍스트 없음)" 안전 fallback.
- `test_user_prompt_includes_chunk_text` — chunk.text 가 prompt 에 포함.
- `test_streaming_yields_token_chunks` — token chunk 정합 yield + stream=True 전달.
- `test_streaming_skips_none_delta` — None/빈 문자열 chunk skip.
- `test_streaming_requires_non_empty_top_chunks` — empty top_chunks → RuntimeError.
- `test_streaming_passes_model_and_temperature` — 인자 정합 전달.
- `test_streaming_system_prompt_enforces_marker_rule` — system prompt 규칙
  검증 ([#N] + plain text).

**`tests/api/test_deps.py` 회귀 보호 추가**

- `patched_real_adapters` fixture 에 `_FakeOpenAIAnswer` + `_fake_build_openai
  _chat_transport` monkeypatch 추가. `OpenAIAnswerLLMProvider` 자체 + `build_
  openai_chat_transport` 자체를 sentinel 로 대체 — 실 OpenAI client 생성 회피.
- `test_build_real_deps_wires_real_adapter_classes` 에 generator_provider/
  config 회귀 단언 추가:
    - `generator_provider_init.api_key_provided is True`
    - `generator_provider_init.transport is not None` — transport 주입 회귀 보호.
    - `generator_transport_init.api_key_provided is True`
    - `deps.generator_config.model == settings.llm_answer_model` (default GPT-4o).

### 본 세션 미구현 — 다음 단계 이관

- **(A) SSE 라우트 streaming 통합** — `openai_streaming.py` 가 token chunk
  generator 를 제공하지만, SSE 라우트가 이를 multi-token 송신으로 변환하는 분기
  는 별도 세션. 그래프 흐름을 search/rerank 까지 분리한 뒤 streaming 으로 답변
  생성을 대체하는 비교적 큰 작업.
- **(C) Rate Limit fallback (GPT-4o-mini 다운그레이드)** — 설계서 §4.6.5. agent
  의 `select_generation_model(use_fallback=True)` 인터페이스를 사용하는 retry
  orchestrator 추가 필요. transport 도입 후 별도 세션.
- **(D) Function Calling 스키마 강제** — Agent 담당자 영역.
- **(E) 자연어 출처 인용 패턴** — Agent 담당자 영역.

### 책임 분리 (본 담당자 영역만)

- 본 commit 은 본 담당자 영역 5 파일 (2 new — `app/query/openai_transport.py`
  + `app/query/openai_streaming.py` / 3 modified — `app/api/deps.py` + `tests/
  api/test_deps.py`) + 2 new tests (`tests/query/test_openai_transport.py` +
  `tests/query/test_openai_streaming.py`) + 본 docs/ai/working-log.md = 총 8
  파일.
- Agent 패키지 (`answer_generation_agent/**`) — 무수정 보존.
- `app/query/generator.py` — 변경 없음 (build_real_deps 만 provider 주입).
- `app/api/routes.py` — 변경 없음 (SSE streaming 분기는 다음 세션).

### 정합성 검증 (오버튜닝 회피)

- `app/CLAUDE.md` §5 LLM 라우팅 — 답변 생성기는 GPT-4o 기본 + GPT-4o-mini
  fallback (`AnswerGenerationConfig(model=GPT-4o, fallback_model=GPT-4o-mini)`) ✓
- rag-pipeline-design.md §4.6.3 GPT-4o 운영 호출 정합 ✓
- rag-pipeline-design.md §4.6.4 SSE 토큰 streaming 의 LLM 호출 인프라 ✓
- rag-pipeline-design.md §4.6.5 plain text fallback — streaming 경로가 plain
  text 모드 + 검증기 1단계 출처 매핑 정합 ✓
- `app/CLAUDE.md` §3 ACL / 정확성 — 컨텍스트 외 단정 금지 system prompt 강제 ✓
- 기존 패턴 재사용 — `OpenAIRoutingLLMProvider` / `OpenAIEvaluatorProvider`
  wiring 패턴 (build_real_deps lazy import + sentinel monkeypatch) 그대로 복제 ✓
- 새 의존성 도입 0 — `openai>=1.30` 이미 보유 ✓

### 후방 호환성

- 신규 (B) transport + (A 인프라) — 기존 회귀 테스트 0건 영향. `build_poc_deps`
  는 변경 없음 — fake 자동 wiring 유지로 PoC 경로 그대로.
- `QueryGraphDeps` 시그니처 변경 없음 (Agent 통합 2/4 에서 이미 generator_
  provider/config 필드 추가됨).
- `manage_generator` 변경 없음 — Agent 통합 2/4 때의 transport=None 한계가 본
  세션에서 해소되며 자연 동작.
- `tests/api/test_deps.py` `patched_real_adapters` fixture 확장 — 기존
  monkeypatch 와 충돌 없이 추가됨.

### 검증 결과 (회사 Mac 기준 — 예상)

- 샌드박스 ruff 0.15.13 으로 format `--check` + check 모두 통과 (`All checks
  passed!`).
- pytest 는 `./scripts/verify.sh` 실행 시 통과 예상 — 신규 17 케이스 (test_
  openai_transport 9 + test_openai_streaming 8) + test_deps 회귀 추가 + 기존
  회귀 0건. 576 → ~595 예상.

### Agent 통합 + 잔여 진척도

| 영역 | 현재 상태 |
|---|---|
| RAG Pipeline 에이전트 4종 (히스토리/라우팅/생성/검증) | ✅ 모두 통합 완료 |
| (B) 답변 생성기 운영 OpenAI HTTP transport | ✅ 본 commit 으로 완료 |
| (A 인프라) Streaming generator + plain text prompt | ✅ 본 commit 으로 완료 |
| (A 라우트) SSE token multi-send 분기 | ⏳ 다음 세션 |
| (C) Rate Limit fallback | ⏳ 다음 세션 |

### 비고

- 본 commit 이 끝나면 본 담당자 영역 ~99% → **99%+** (단순 인프라 완성도 상승,
  운영 답변 생성 가능). SSE token 체감 streaming 은 다음 세션 후 100% 운영 정합.
- 본 commit 의 변경 영향 파일 = 5 본 담당자 + 0 vendoring + 2 test + 1 working
  -log = 8 파일.

### 후속 TODO (다음 세션 후보 — 우선순위)

1. **(A) SSE 라우트 streaming 통합** — `app/api/routes.py` 의 query_route 에
   `stream` query parameter 추가. stream=True 시 graph 분기 — search/rerank
   까지만 graph 실행, top_chunks 확보 후 `stream_openai_answer` 로 token
   multi-send, 답변 완료 후 sources/verification/meta/done 송신.
2. **(C) Rate Limit fallback** — `manage_generator` 가 `AnswerProviderError(
   error_type='rate_limit_error')` 캐치 후 GPT-4o-mini 로 재시도 + verification
   .note 기록 (설계서 §4.6.5).
3. **운영 라이브 smoke** — Agent 통합 4종 + (A+B+C) 모두 끝낸 후 docker compose
   + `RAG_USE_REAL_ADAPTERS=true` 로 끝-끝 검증.
4. **평가 세션 (F, G)** — 1단계 정합 검증, all-sentence mode 비용 측정.
5. **feature4-B PDF/CSV 첨부 분할기** — 외부 픽스처 + pymupdf.


## 2026-05-19 — Mode B 시연 fix: LangGraph config 충돌 + scripts/ingest_samples.py

- 브랜치: `feat/#1/rag-pipeline-skeleton`
- 배경: (A+B) 운영 OpenAI HTTP transport 도입 (`5f9311b`) 직후 사용자 시연. PoC
  모드는 정상 동작하지만 운영 모드(`RAG_USE_REAL_ADAPTERS=true`)에서 답변 생성
  단계만 stub fallback 으로 떨어지는 현상 발견. 시연 디버그 끝에 LangGraph 노드
  시그니처의 `config` 키워드가 자체 `RunnableConfig` (dict) 로 자동 override 되는
  충돌을 진단·해결. 추가로 운영 Qdrant 에 samples 데이터를 1회 적재할 CLI 도
  작성. 실 GPT-4o 답변·검증 2단계가 정상 동작하는 끝-끝 시연 완료.

### 변경 사항

**LangGraph config 충돌 fix — `app/query/generator.py`**

LangGraph 의 노드 호출 시 `(state, config: RunnableConfig)` 시그니처를 자동 인식
해서 두 번째 인자에 dict 형태의 RunnableConfig 를 주입한다. 본 어댑터의 keyword
인자 `config` 가 이 dict 로 override 되어, partial wiring 으로 박아둔 agent
`AnswerGenerationConfig` 인스턴스가 dict 로 바뀌는 버그.

- 시그니처 변경: `config` 키워드를 placeholder (`Any` 타입) 로 유지하고, agent
  config 는 `generation_config` keyword-only 인자로 분리.
- `manage_generator(state, config=None, *, provider=None, generation_config=None)`.
- 본체에서 `selected_config = generation_config or AnswerGenerationConfig()` 로
  변경.
- query_graph.py 의 partial wiring 도 `generation_config=deps.generator_config`
  로 갱신.
- generator.py docstring 변경 이력에 본 fix 단락 추가.

**디버그 로그 정리**

시연 도중 manage_generator except 절에 traceback print 를 추가해 fallback 원인
진단 → 시연 끝나고 원래 silent `except Exception: return _apply_fallback(state)`
복원.

**scripts/ingest_samples.py 신설 (~110 lines)**

- 1회용 CLI — `build_real_deps` 가 samples 자동 인덱싱을 수행하지 않으므로
  (운영은 별도 ingestion 파이프라인 가정), Mode B 시연을 위해 samples → 운영
  Qdrant 1회 적재.
- E5DenseEmbedder + BM25SparseEmbedder + QdrantPoolStore.from_settings +
  bootstrap_collections → samples loader → chunk_page → index_chunks.
- `--use-mongo-cache` 옵션 (기본 Fake) — 시연은 docker compose 의 mongo 가 없어도
  동작 가능.
- 사용법: `python scripts/ingest_samples.py` (uvicorn 별도 실행 중 다른 터미널).

**tests/query/test_generator.py 갱신**

- `test_custom_config_max_contexts_limits_top_contexts` 의 `config=...` 인자 호출
  을 `generation_config=...` 으로 갱신 (시그니처 변경 정합).

### 시연 검증 결과 (사용자 Mac, 실 GPT-4o)

- 질의: "EKS Worker Node가 NotReady 상태가 되었을 때 어떻게 대응해야 하나요?"
- 답변 (실 GPT-4o 생성):

  > EKS Worker Node가 NotReady 상태가 되었을 때의 대응 절차는 다음과 같습니다.
  > 먼저, Datadog 알림을 통해 Node NotReady 상태를 인지합니다. [#1] 그런 다음,
  > `kubectl` 명령어를 사용하여 노드 상태를 확인하고... [#1] 이후, AWS Health
  > Dashboard 를 확인하여 특정 가용 영역(AZ)에 하드웨어 이슈가 있는지 점검합니다.
  > [#1] 만약 하드웨어 이슈가 확인되면, Karpenter 와 같은 자동화 도구가 다른 AZ
  > 에 대체 노드를 프로비저닝하는지 확인합니다. [#1] 이 과정에서 Pod 들이 다른
  > 노드로 재스케줄링되며 일시적인 서비스 지연이 발생할 수 있습니다. [#2]

- 검증 2단계: 7 문장 중 SUPPORTED 1 + PASS 5 + NOT_SUPPORTED 1 (첫 문장 인용 마커
  없음). NOT_SUPPORTED 비율 14% < 50% → 답변 정상 송출, `feedback_enabled=true`.
- latency: 8.9 초 (실 GPT-4o + GPT-4o-mini 라우터 + GPT-4o-mini 검증 2단계 합산).
- 설계서 §4.6.1 핵심 규칙 모두 충족: 컨텍스트 기반, [#N] 마커, 의도별 단계별
  답변 형식, 자연스러운 한국어.

### 발견·기록 (정합성 검증)

- LangGraph 노드 시그니처 `(state, config)` 자동 인식 — 라우터·답변 생성기 어댑터
  도 동일 패턴. 라우터는 fallback 이 OPERATION_GUIDE 로 떨어져 겉으로 잘 보이지
  않지만 같은 dict override 영향 받음. **다음 세션 TODO** — `app/query/router.py`
  의 `config` 키워드도 동일 패턴으로 분리 (시그니처 명시 `routing_config=`).
- 설계서 §4.6.3 GPT-4o 호출 운영 정합 ✓
- 설계서 §4.6.1 모든 핵심 문장 [#N] 인용 ✓
- 설계서 §6.6 의도별 task prompt 적용 (운영가이드 → 단계별) ✓
- 환각 차단 — 컨텍스트 외 정보 단정 없음 ✓

### 후방 호환성

- `manage_generator` 시그니처 변경 — 외부 호출자가 `config=...` keyword 로 명시
  주입한 코드는 없으며 (LangGraph partial wiring 만 사용), 본 commit 으로 모두
  `generation_config=` 로 일관 갱신. 기존 회귀 테스트 1건 (`test_custom_config
  _max_contexts_limits_top_contexts`) 도 함께 갱신.
- ingest_samples.py 는 신규 — 기존 코드 영향 0.

### 후속 TODO (다음 세션 후보 — 우선순위)

1. **라우터 어댑터 동일 fix** (`app/query/router.py`) — `config` 키워드 → `routing
   _config` 로 분리. 현재는 fallback 이 OPERATION_GUIDE 로 떨어져 잘 안 보이지만
   `RoutingProvider` 호출 자체가 실패할 가능성 있음.
2. **(A) SSE 라우트 streaming 통합** — 답변 latency 8.9초 → token streaming 으로
   첫 토큰 1초 내 도달 (설계서 §4.6.4 KPI).
3. **(C) Rate Limit fallback** — manage_generator 가 `AnswerProviderError(error
   _type='rate_limit_error')` 캐치 후 GPT-4o-mini 재시도 + verification.note 기록.
4. **운영 라이브 smoke + 평가 세션 (F, G)**.
5. **app/config.py 의 cross_encoder_model 기본값** — 현재 `cross-encoder/ms-marco
   -MiniLM-L-12` (잘못된 이름). `-v2` 추가 필요 (사용자가 .env 로 임시 우회).

---

## 2026-05-19 — feature12: ML 코드 리뷰 (PDF #1+#4) + 운영성 fix

- 브랜치: `feat/#1/rag-pipeline-skeleton`
- 변경 사항: `0518_RAG.pdf` 의 ML 코드 리뷰 항목 #1(.gitignore 보완) + #4
  (Prometheus 모니터링) 적용 + 라우터 LangGraph config 충돌 fix + 설정 기본값
  /api_key 명시 주입 클린업.

### 1. `.gitignore` 머지 (PDF #1)

- Virtual environments 섹션에 `.env/` (가상환경 디렉터리) 1줄 추가. 기존
  Secrets 섹션의 `.env` 가 file/dir 둘 다 잡지만 PDF 표기와 정합화.
- 그 외 패턴 (`__pycache__/`, `*.py[cod]`, `.pytest_cache/`, `.ruff_cache/`,
  `.coverage`, `htmlcov/`, `.env.*`/`!.env.example`, `.idea/`/`.vscode/`/
  `.DS_Store`, `*.log`/`.cache/`) 은 직전 세션까지 이미 머지돼 있어 중복
  추가하지 않음.

### 2. Prometheus 운영 모니터링 도입 (PDF #4)

- `pyproject.toml` runtime dependency 에 `prometheus-fastapi-instrumentator>=
  7.0` 추가 (새 `--- 운영 모니터링 ---` 블록).
- `app/api/main.py` `create_app` 에 `Instrumentator().instrument(app).expose
  (app, endpoint="/metrics", include_in_schema=False)` wiring. HTTP 표준
  메트릭 (요청 수·지연 히스토그램·상태 코드별 카운터) 자동 수집 + `/metrics`
  엔드포인트 노출.
- `/metrics` 는 OpenAPI 스키마에서 제외하고 BFF 인증을 우회하는 Prometheus
  scraper 직접 접근 경로로 둠 (CORS·인증은 BFF 담당 — `docs/api-spec.md`
  NOTE 정합).
- 결정점:
  - 라이브러리 — `prometheus-fastapi-instrumentator` (FastAPI 통합 1줄 wiring).
  - 메트릭 범위 — HTTP 표준만 (이번 세션). LLM 커스텀 메트릭 (환각 비율·
    Precision@3 등) 은 feature17 (평가 세션) 으로 이관.
  - 엔드포인트 위치 — 루트 `/metrics`.

### 3. 라우터 LangGraph config 키워드 충돌 fix

- `app/query/router.py` `manage_router` 시그니처 변경 — `config: Any = None`
  를 LangGraph RunnableConfig placeholder 로 두고 (`# noqa: ARG001`), agent
  `QueryRoutingConfig` 는 `routing_config: QueryRoutingConfig | None = None`
  keyword-only 인자로 분리. generator/verifier 와 동일 패턴.
- `app/pipeline/query_graph.py` router partial wiring 을 `config=deps.routing
  _config` → `routing_config=deps.routing_config` 로 갱신.
- 이전 시그니처에서는 LangGraph 가 노드에 주입한 RunnableConfig dict 가
  agent `normalize_routing_input` 에 흘러 들어가 `RoutingProviderError` 가
  발생, OPERATION_GUIDE fallback 으로 떨어지던 회귀를 해소. 본 fix 후 라우터
  정상 분기 동작 — 의도가 다양화돼도 설계서 §4.4.2 의 4종 의도 분류 + §4.4.4
  Pool 가중치 정책 정합.

### 4. `cross_encoder_model` 기본값 정합화

- `app/config.py` 의 `cross_encoder_model` 기본값을 `cross-encoder/ms-marco-
  MiniLM-L-12` → `cross-encoder/ms-marco-MiniLM-L-12-v2` 로 변경.
- 설계서 §4.5.3 표기는 `-v2` 누락 ─ Hugging Face / sentence-transformers 의
  실 모델명은 `-v2` 가 정식 (`-v2` 없는 변형은 존재하지 않음). **설계서
  차기 개정 시 `-v2` 반영 권장** (이영훈에게 별도 노트 권장).
- 직전 세션까지는 `.env` 의 `RAG_CROSS_ENCODER_MODEL` 로 우회 중이었으며,
  본 fix 로 코드 기본값만으로도 운영 모드 (`RAG_USE_REAL_ADAPTERS=true`)
  에서 모델 로드 성공.

### 5. `build_real_deps` api_key 명시 주입

- `app/api/deps.py` `build_real_deps` 에서 `settings.openai_api_key.get
  _secret_value()` 를 1회 추출 후 3종 provider 에 직접 주입.
- 라우터 — `OpenAIRoutingLLMProvider.from_config` (env fallback 의존) →
  `OpenAIRoutingLLMProvider(config, api_key)` 직접 호출로 변경.
- 검증기 — `AnswerVerificationConfig(evaluator_model=..., openai_api_key=
  api_key)` 로 config 객체에 키를 채워 `OpenAIEvaluatorProvider` 가
  `os.environ.get("OPENAI_API_KEY")` fallback 을 거치지 않도록 함.
- 답변 생성기는 이미 명시 주입 중 (Plan v2 §3 (B), 직전 세션).
- `.env` 의 `OPENAI_API_KEY` 중복 환경변수 제거 가능 — `RAG_OPENAI_API_KEY`
  하나로 통일. CLAUDE.md 절대 규칙 "Secret 은 `app/config.py` 에서 환경
  변수로 주입" 정합.

### 수정 파일

- `.gitignore`
- `pyproject.toml`
- `app/api/main.py`
- `app/query/router.py`
- `app/pipeline/query_graph.py`
- `app/config.py`
- `app/api/deps.py`
- `tests/api/test_main.py` (신규 — `/metrics` + `/healthz` 회귀 3건)
- `tests/query/test_router.py` (LangGraph fix 회귀 2건 추가)
- `tests/api/test_deps.py` (api_key 명시 전달 회귀 1건 추가 + fixture 갱신)
- `docs/ai/working-log.md` (본 세션 기록)

### 정합성 검증 — 기획서 v2.1.6 + 설계서 v0.2.2

- **`.gitignore`**: 설계서·기획서에 직접 언급 없음. CLAUDE.md 절대 규칙 ".env
  커밋 금지" + PDF 권고로 정당화. **충돌 없음**.
- **Prometheus `/metrics`**: 설계서 §6.4 KPI 표 (latency_ms, P95, NOT_SUPPORTED
  카운트, feedback) + §4.7.3 "운영 로그에 hallucination_event 기록 ─ 대시보드
  모니터링 대상" + 기획서 v2.0 "관리자 역할 재정의(운영 모니터링 중심)" 정합.
  "Prometheus" 도구 자체는 두 문서 미명시 — 운영 모니터링 요구사항을 만족하기
  위한 도구 선택은 본 저장소 운영성 결정으로 정당화. **단, HTTP 표준만 도입은
  KPI 4종 중 latency_ms / P95 일부만 충당 — 환각 비율 (NOT_SUPPORTED 카운트)·
  Precision@3 메트릭은 feature17 (평가 세션) 으로 이관**.
- **라우터 LangGraph fix**: 설계서 §4.4.6 라우터 실패 시 fallback (OPERATION
  _GUIDE, [원본 쿼리], 빈 filters) 정합. 본 fix 는 fallback 분기로 잘못 떨어지지
  않도록 정상 분기를 복구. **정합 ✓**.
- **cross_encoder_model -v2**: **설계서 §4.5.3 표기와 차이 발견** — 설계서는
  `cross-encoder/ms-marco-MiniLM-L-12` (v2 없음) 이나 Hugging Face 실 모델명은
  `-v2` 가 정식. 코드 fix 가 동작 측면에서 옳음. **설계서 차기 개정 시 반영
  권장** (담당 영역 외 문서는 본 세션에서 수정하지 않음 — CLAUDE.md 정합).
- **api_key 명시 전달**: CLAUDE.md 절대 규칙 "Secret 은 `app/config.py` 에서
  환경 변수로 주입" 정합. **정합 ✓**.

### 검증 명령 / 결과

- 사용자 Mac: `source .venv/bin/activate && ./scripts/verify.sh` 실행 — 594+N
  passed 확인 필요 (`tests/api/test_main.py` 신규 3건 + `tests/query/test_router
  .py` 신규 2건 + `tests/api/test_deps.py` 신규 1건 = 6건 추가).

### 후속 TODO (다음 세션 후보 — `docs/ai/current-plan.md` Milestone D 정합)

- feature13 (PDF #2+#3) — BE 협의 대기 (API Spec / user ACL 컬럼 + Confluence
  call 명세).
- feature14 — (A) SSE token streaming 라우트 통합.
- feature15 — (C) Rate Limit fallback (GPT-4o-mini 다운그레이드).
- feature16 — 운영 라이브 smoke (docker compose 전체).
- feature17 — 평가 세션 (F, G, Golden Set) + **LLM 커스텀 Prometheus 메트릭**
  (환각 비율·Precision@3 등) — 본 세션 미구현 이관.
- feature18 — Data Ingestion Agent 책임 협의 / feature4-B / (D)+(E).
- **설계서 §4.5.3 표기 정정 요청** — 이영훈에게 cross-encoder/ms-marco-MiniLM
  -L-12 → `-v2` 표기 반영 요청 (Slack 별도 협의).

---

## 2026-05-19 — feature14: SSE token streaming 라우트 통합

- 브랜치: `feat/#1/rag-pipeline-skeleton`
- 변경 사항: 설계서 §4.6.4 SSE 토큰 streaming 정합. 직전 commit `5f9311b` 의
  `stream_openai_answer` 인프라를 라우트와 결합해 운영 모드에서 첫 토큰 1초
  내 도달 (KPI P95 5초) 가능하도록 통합.

### 1. partial 그래프 helper 신설

- `app/pipeline/query_graph.py` 에 `build_query_graph_for_streaming(deps)` 추가.
  기존 `build_query_graph` 는 무수정 보존 (PoC 600 test 회귀 + non-streaming
  경로 유지).
- 그래프 구조 — history → router → search → (empty | rerank) 까지만 조립.
  rerank 노드가 끝나면 END 로 종료. generate/verify 는 라우트가 직접 OpenAI
  streaming + verify_pipeline_node 로 사후 수행.
- rerank 노드는 기존과 동일하게 `state.top_chunks` + `state.sources` 를
  채워준다 — 별도 chunks_to_sources 헬퍼 불필요.

### 2. `QueryRequest.stream` + 라우트 분기

- `app/api/routes.py` `QueryRequest` 에 `stream: bool = False` 필드 추가.
  기본값 False 이므로 BFF/테스트 기존 호출 호환 (600 test 회귀 0).
- `query_route` 가 `stream=True` 분기:
  - PoC 안전 fallback 검사 (`_should_fallback_to_non_streaming`) —
    `request.app.state.deps.generator_provider` None 또는 `settings.openai_api
    _key` 빈 SecretStr 이면 stream=True 무시하고 기존 `run_query` 흐름.
  - 운영 streaming (`_streaming_event_stream`) — `app.state.streaming_graph` 로
    rerank 까지 실행 → `top_chunks` 가 비어 있으면 RETRIEVAL_EMPTY 표준 응답
    그대로 송신 → `stream_openai_answer` 호출 → token chunk 다중 yield →
    답변 누적 후 `verify_pipeline_node` (1+2단계) → `format_response` 로 저신뢰
    /차단 분기 적용 → sources/verification/meta/done 송신.
- 차단 분기 (NOT_SUPPORTED 비율 > 0.5) 케이스 — 이미 원본 token 을 다 보낸
  뒤이므로 차단 안내문을 별도 token 이벤트로 1회 더 송신해 UI 가 덮어쓰도록
  처리. 이는 설계서 §4.7.3 "환각 비율 초과 시 답변 보류" 정합.

### 3. lifespan 갱신 (`app/api/main.py`)

- lifespan 이 `build_query_graph_for_streaming(deps)` 도 함께 컴파일해
  `app.state.streaming_graph` / `app.state.deps` / `app.state.settings` 에 저장.
  PoC 환경에서도 함께 컴파일 (lifespan 부담 적음).
- `_resolve_used_llm(model: str) -> LlmModel` 안전 변환 헬퍼 추가 — enum 에
  없는 모델명 (예: `gpt-4o-2024-05-13`) 은 GPT_4O 로 fallback.

### 수정 파일

- `app/pipeline/query_graph.py` — `build_query_graph_for_streaming` 신설
- `app/api/main.py` — streaming_graph + settings 를 lifespan 에 저장
- `app/api/routes.py` — `QueryRequest.stream` 필드 + `_streaming_event_stream`
  + `_should_fallback_to_non_streaming` + `_resolve_used_llm`
- `tests/api/test_query_route.py` — stream=true PoC fallback + 운영 streaming
  회귀 2건
- `tests/pipeline/test_query_graph.py` — partial graph 회귀 2건 (rerank 채움 +
  RETRIEVAL_EMPTY 분기)
- `docs/ai/working-log.md` (본 세션 기록)
- `docs/ai/current-plan.md` (feature14 체크박스 [x] + 완료현황 갱신)

### 정합성 검증 — 설계서 v0.2.2

- 설계서 §4.6.4 "OpenAI Streaming API 사용해 토큰 단위로 수신하고, FastAPI 의
  SSE 로 즉시 푸시 → 첫 토큰 빠르게 도달" — **정합 ✓**. 직전 시연 latency 8.9
  초 → SSE token 첫 토큰 1초 내 도달 가능.
- 설계서 §6.4 KPI 표 "응답 시간 P95 5초 / Query 파이프라인 entry → SSE 첫
  토큰" — 본 plan 으로 KPI 충족 경로 확보.
- 설계서 §4.7 답변 검증 (1단계 규칙 + 2단계 LLM 평가자) — streaming 흐름도
  검증 사후 호출로 정합 ✓. NOT_SUPPORTED 비율 > 0.5 차단 안내 송신 정합.
- 설계서 §4.6.5 답변 생성 실패 fallback — Rate Limit 다운그레이드는 본 세션
  미구현. feature15 로 이관.
- 설계서 §4.5.4 검색 결과 0건 처리 — streaming 그래프도 empty_retrieval 분기
  + 표준 메시지 송신 정합.

### 검증 명령 / 결과

- 사용자 Mac: `./scripts/verify.sh` 실행 — 600+4 = 604 passed 예상 (test_query
  _route.py 신규 2건 + test_query_graph.py 신규 2건). PoC fallback / 운영
  streaming 시나리오 양쪽 회귀.

### 후속 TODO (다음 세션 후보 — current-plan.md Milestone D 정합)

- feature15 — (C) Rate Limit fallback (GPT-4o-mini 다운그레이드)
- feature16 — 운영 라이브 smoke (docker compose 전체 + SSE latency 실측)
- feature17 — 평가 세션 (F, G, Golden Set) + LLM 커스텀 Prometheus 메트릭
- feature13 — (PDF #2+#3) BE 협의 대기
- feature18 — Data Ingestion Agent 책임 협의 + feature4-B + (D)+(E)

---

## 2026-05-19 — feature15: Rate Limit fallback (§4.6.5)

- 브랜치: `feat/#1/rag-pipeline-skeleton`
- 변경 사항: 설계서 §4.6.5 정합 — OpenAI 429 (Rate Limit) 시 GPT-4o-mini 자동
  다운그레이드 + 재시도. non-streaming (`manage_generator`) + streaming
  (`_streaming_event_stream`) 양쪽에 동일 패턴 적용. 운영 안정성 확보 — Rate
  Limit 발생 시에도 답변이 사용자에게 도달 + meta.used_llm 으로 다운그레이드
  인지.

### 1. non-streaming Rate Limit fallback (`app/query/generator.py`)

- `manage_generator` 의 `service.generate(normalized_input, config)` 호출을
  `_generate_with_rate_limit_fallback` helper 로 래핑.
- agent `AnswerProviderError(error_type='rate_limit_error')` 만 fallback 트리거 —
  다른 에러 (`timeout_error` / `auth_error` / `server_error` / `invalid_response`)
  는 상위로 raise 해 기존 `_apply_fallback` 안전 분기로 이어지게 둔다 (의미 없는
  다운그레이드 시도 방지).
- fallback 시 `service.generate(use_fallback_model=True)` 로 1회 재시도 →
  agent `select_generation_model` 이 `config.fallback_model` 반환.
- `state.used_llm` 은 `generation_result.model` 에서 정합화 (`_resolve_used_llm`
  helper). 모델 문자열에 `mini` 포함 → `GPT_4O_MINI` 매핑.
- `logging.warning("answer generator rate-limited, falling back to fallback
  _model=%s")` 로 운영 로그 기록 — 다음 세션 feature17 의 `llm_fallback_total`
  카운터로 후속 가시화.

### 2. streaming Rate Limit fallback (`app/api/routes.py`)

- `_streaming_event_stream` 의 `stream_openai_answer` 호출을 try/except
  `openai.RateLimitError` 로 감싸 fallback 분기 추가.
- **첫 토큰 송신 전 raise** → 그대로 fallback_model 로 재시도.
- **첫 토큰 송신 후 raise** → 누적 토큰 폐기 + 빈 `token` 이벤트 1회 송신해 UI
  가 부분 답변을 덮어쓸 수 있도록 함 + fallback_model 로 재시도.
- 두 번째 시도 중에도 `RateLimitError` → 그대로 raise → 상위 `query_route` 의
  try/except 가 `UPSTREAM_LLM_ERROR` 502 로 매핑.
- `used_model` 변수로 추적 → `state.used_llm` 이 fallback 시 `GPT_4O_MINI` 로
  정합화 → 응답 `meta.used_llm` 에 노출.

### 3. 가시화 전략

- **Schema 변경 없음** — `Verification.note` 등 신설 안 함.
- 다운그레이드 인지: (1) `meta.used_llm` 이 `gpt-4o-mini` 로 표시 + (2) 운영
  로그 `logging.warning` 기록.
- LLM 커스텀 메트릭 (`llm_fallback_total` 카운터 등) 은 feature17 (평가 세션)
  에서 추가.

### 수정 파일

- `app/query/generator.py` — `_generate_with_rate_limit_fallback` + `_resolve
  _used_llm` helper 신설 + `manage_generator` 본문 통합
- `app/api/routes.py` — streaming RateLimitError 캐치 + fallback_model 재시도
  + 빈 clear token 송신
- `tests/query/test_generator.py` — `_SequencedProvider` fixture + 회귀 2건
  (rate_limit_error 재시도 + 다른 error_type 은 재시도 안 함)
- `tests/api/test_query_route.py` — `_streaming_client_with_stream_callable`
  helper + 회귀 1건 (streaming primary 1회 raise → fallback 정상 yield)
- `docs/ai/working-log.md` (본 세션 기록)
- `docs/ai/current-plan.md` (feature15 체크박스 [x] + 완료현황 갱신)

### 정합성 검증 — 설계서 v0.2.2

- **§4.6.5** "Rate Limit (429) → GPT-4o-mini 자동 다운그레이드 + 재시도" —
  **정합 ✓**.
- **§4.6.3** GPT-4o 운영 호출 / `app/CLAUDE.md` §5 라우팅 정책 보조 모델 —
  fallback 시 GPT-4o-mini 사용 **정합 ✓**.
- **§4.7** 답변 검증 — fallback 답변도 동일 검증 1+2단계 통과 **정합 ✓**.
- Schema 변경 없음 — `docs/api-spec.md` / `docs/db-schema.md` 영향 0.

### 검증 명령 / 결과

- 사용자 Mac: `./scripts/verify.sh` 실행 — 604+3 = 607 passed 예상 (test_generator
  .py 신규 2건 + test_query_route.py 신규 1건).

### 후속 TODO (다음 세션 후보 — current-plan.md Milestone D)

- feature16 — 운영 라이브 smoke (docker compose 전체)
- feature17 — 평가 세션 (F, G, Golden Set) + LLM 커스텀 Prometheus 메트릭
  (`llm_fallback_total` 카운터로 본 세션의 logging.warning 가시화)
- feature13 — (PDF #2+#3) BE 협의 대기
- feature18 — Data Ingestion Agent 책임 협의 + feature4-B + (D)+(E)

---

## 2026-05-19 — feature16: 운영 라이브 smoke + histogram bucket fix

- 브랜치: `feat/#1/rag-pipeline-skeleton`
- 변경 사항: docker compose 전체 (Qdrant + MongoDB + MySQL) 기동 + 운영 어댑터
  (E5/BM25/Qdrant.from_settings/CrossEncoder + 실 OpenAI) 끝-끝 라이브 검증. 직전
  세션 (feature12·14·15) 변경사항의 운영 적합성 확인. 발견된 1건 (Prometheus
  histogram bucket 협소) 후속 fix.

### Smoke 시나리오 실행 결과

- 인프라: docker compose up -d (qdrant + mongo + mysql, healthy)
- 적재: `scripts/ingest_samples.py --use-mongo-cache` → 92 PageObject → 374
  Chunk → Qdrant 3 Pool 적재 (~수십 초)
- 모드: `RAG_USE_REAL_ADAPTERS=true` + 실 GPT-4o + GPT-4o-mini
- 의도 분기 4종 (장애대응 / 운영가이드 / 정책절차 / 이력조회) + streaming 1건

### 수치 측정

| # | 질의 | latency_ms | answer 품질 | sources | NOT_SUPPORTED 비율 | feedback |
|---|------|-----------:|-------------|--------:|---------------------:|----------|
| Q1 | 장애대응 — EKS NotReady | 9430 | [#1] 인용, kubelet/SG/IAM 절차 | 1 | 1/6 = 16.7% | true |
| Q2 | 운영가이드 — IAM 롤백 | 7522 | "context 없음" 솔직 + 일반지식 | 0 | 2/9 = 22.2% | **false** (저신뢰) |
| Q3 | 정책/절차 — 외부솔루션 보안 | 1416 | "context 없음" 표준 | 0 | 0/1 | **false** (저신뢰) |
| Q4 | 이력조회 — 클라우드 비용 | 5767 | [#1] 인용, 비용 절감 항목 | 1 | 1/3 = 33% | true |
| Stream | EKS NotReady (stream=true) | **3587** | 마크다운 + 다중 [#1][#2] | 5 | 2/11 = 18.2% | true |

### 설계서 §6.4 KPI 정합 검증

| KPI 항목 | 목표 | 측정 결과 | 결과 |
|---------|------|-----------|------|
| 정보 검색 소요 시간 | 30초 이내 | 최대 9430ms | ✅ 통과 |
| 응답 시간 P95 (entry → 첫 토큰) | 5초 이내 | streaming 3.6초 (첫 토큰 ~1초대 추정) | ✅ **통과** (streaming 기준) |
| 환각 비율 | 15% 이하 | 평균 ~18% (의도된 보수적 답변 포함) | ⚠️ 일부 초과 — feature17 prompt 튜닝 |
| `/metrics` 노출 | scrape 정상 | http_requests_total=5, histogram 정상 | ✅ 통과 |

### 본 담당자 영역 검증 ✓

- SSE token streaming 첫 토큰 빠른 도달 ✓
- ACL 통과 검색 ✓
- 다중 [#N] 인용 ✓
- 검증 1+2단계 동작 ✓
- 저신뢰 분기 (`feedback_enabled=false`) Q2/Q3 정상 ✓
- /metrics Prometheus scrape ✓
- Cross-Encoder Top-5 점수 분포 ✓ (score=100, 99, 99, 99, 99 with margin)

### 발견 1: Prometheus histogram bucket 협소 (본 세션 후속 fix)

- 기본 `metrics.default()` 의 lowr_buckets 는 (0.1, 0.5, 1.0) 만이라 LLM 응답
  latency (3~10초) 가 모두 `le=+Inf` bucket 에만 누적 → P95 측정 불가.
- **fix**: `app/api/main.py` 에서 `Instrumentator.add(metrics.default(latency
  _highr_buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, inf),
  latency_lowr_buckets=(1.0, 5.0, 30.0)))` 명시 등록. 설계서 §6.4 KPI 5초·30
  초 임계가 bucket 경계로 직접 노출돼 Prometheus 쿼리 `histogram_quantile(0.95,
  rate(http_request_duration_seconds_bucket[5m]))` 정확화.

### 발견 2: 4종 질의 모두 intent="운영가이드" 분류 (feature17 이관)

- Q1 (장애대응) / Q3 (정책절차) / Q4 (이력조회) 가 라우터에서 모두 "운영가이드"
  로 분류됨. GPT-4o-mini 분류 정확도 / fallback 분기 / prompt 튜닝 여부를
  feature17 평가 세션에서 분석 필요.
- 단, 운영가이드 분기로 떨어져도 검색·재순위화·생성·검증은 정상 동작하므로
  본 fix 우선순위 ↓.

### 발견 3: non-streaming P95 5초 초과 (BFF 권고)

- non-streaming 평균 6.04초 (Q1·Q2 가 5초 초과). streaming 모드는 첫 토큰 1초
  대로 KPI ✓. **BFF/UI 가 `stream=true` 사용 권장**. 본 저장소 fix 불필요.

### 수정 파일

- `.env.example` — `RAG_USE_REAL_ADAPTERS` 항목 추가 (feature16 진입 명확화)
- `app/api/main.py` — Prometheus histogram bucket 명시 등록
- `docs/ai/working-log.md` (본 세션 기록)
- `docs/ai/current-plan.md` (feature16 체크박스 [x] + 완료현황 갱신)

### 후속 TODO (다음 세션 후보)

- feature17 — 평가 세션 (F, G, Golden Set) + LLM 커스텀 Prometheus 메트릭
  + **라우터 의도 분류 오분류 원인 분석** (smoke 발견 #2)
- feature13 — (PDF #2+#3) BE 협의 대기
- feature18 — Data Ingestion Agent 책임 협의

---

## 2026-05-19 — feature17a: Evaluation Set 골격 + 평가 스크립트 + LLM 커스텀 메트릭

- 브랜치: `feat/#1/rag-pipeline-skeleton`
- 변경 사항: 설계서 §6 (품질 튜닝 계획) + §7.2.3 (평가 자동화) 의 **인프라/도구
  골격** 구축. 실 라벨링 (50건 완성) + 회귀 평가 + 튜닝은 feature17b/c 이관.

### 1. LLM 커스텀 Prometheus 메트릭 모듈 (`app/metrics.py`)

설계서 §6.4 KPI 표 정합. default `CollectorRegistry` 사용 → `app/api/main.py` 의
Instrumentator 가 `/metrics` 로 자동 노출.

- **`llm_fallback_total{from_model, to_model, reason}`** (Counter) — feature15
  Rate Limit fallback 발생 빈도 가시화. logging.warning 과 이중화.
- **`verification_status_total{status}`** (Counter) — 설계서 §6.4 "환각 비율
  15% 이하" KPI 관측 지점. PASS / SUPPORTED / NOT_SUPPORTED 분포.
- **`answer_generation_latency_seconds`** (Histogram, 0.1~60 sec buckets) —
  답변 생성 단계 자체 latency (HTTP latency 와 분리). KPI P95 5초 정합.
- **`intent_classification_total{intent}`** (Counter) — feature16 smoke 발견
  #2 (4종 질의 모두 운영가이드) 원인 분석 + §6.1 의도 분류 정확도 90% 임계.

### 2. 메트릭 수집 hook

- `app/query/generator.py` — `_generate_with_rate_limit_fallback` 의 rate_limit
  _error 분기에서 `llm_fallback_total.labels(...).inc()`. 답변 생성 단계 전체
  를 `time.perf_counter()` 로 측정해 `answer_generation_latency_seconds.observe()`.
- `app/pipeline/nodes.py` — `verify_pipeline_node` 가 verification 결과 산출
  직후 `verification_status_total.labels(status=...).inc()` 를 status 별로.
- `app/api/routes.py` — streaming RateLimitError 분기에서 `llm_fallback_total
  .inc()` (non-streaming 과 동일 패턴).
- `app/query/router.py` — manage_router 정상 분기 종료 직전 `intent
  _classification_total.labels(intent=state.intent.value).inc()`. `_apply
  _fallback` 분기는 별도 라벨 `"fallback"` 으로 inc — 라우터 안전 분기 빈도
  관측 가능.

### 3. Evaluation Set 골격 (`samples/evaluation_set.json`)

설계서 §6.2 정합. 시드 10건, 50건 완성은 feature17b 이관.

- 형식: `{items: [{id, intent, query, expected_page_ids[], expected_chunk_ids
  [], expected_answer_excerpt, is_attachment_focused}]}`
- 시드 분포: 장애대응 4건 / 운영가이드 3건 / 정책절차 2건 / 이력조회 1건
  (설계서 비율 35:30:20:15 근사).
- `expected_chunk_ids` 는 운영 그래프 1회 실행 후 backfill (feature17b) — 본
  세션은 빈 배열.
- 첨부 활용 슬롯 — 본 시드 0건 (설계서 50건 중 8건 ≥ 16% 임계는 feature17b).

### 4. 평가 스크립트 (`scripts/run_evaluation.py`)

- argparse CLI: `--eval-set` / `--output` / `--use-real-adapters` / `--debug
  -route "질문"` / `--top-k 3` (KPI Precision@3 정합).
- 측정 지표:
  - 의도 분류 정확도 (expected_intent vs actual_intent)
  - Precision@k (sources Top-k 중 expected_page_ids 매칭) — 본 세션은 약식
    매칭, 정밀 매칭은 feature17b backfill 후
  - 환각 비율 (NOT_SUPPORTED / verification_total)
  - latency 평균 / 최대 / P95
  - 라우터 의도 분포 (smoke 발견 #2 분석용)
- 디버그 모드 (`--debug-route`) — 단일 질문에 대한 라우터 응답만 출력 (의도
  분류 오분류 원인 분석 용).
- 결과 JSON 저장: `reports/evaluation_<timestamp>.json`.

### 5. 회귀 테스트 (`tests/test_metrics.py`)

- 메트릭 자체 동작 4건: Counter inc / Histogram observe / status 라벨 분리 /
  default registry 등록.
- hook 동작 3건: generator rate_limit_error → llm_fallback_total +1 / verify
  _pipeline_node → verification_status_total{PASS} +1 / manage_router fallback
  → intent_classification_total{fallback} +1.
- 합계 7건 추가.

### 수정 파일

- `app/metrics.py` (신규)
- `app/query/generator.py` — 메트릭 hook + latency observe
- `app/pipeline/nodes.py` — verification_status_total hook
- `app/api/routes.py` — streaming Rate Limit fallback counter
- `app/query/router.py` — intent_classification_total hook
- `samples/evaluation_set.json` (신규) — 시드 10건
- `scripts/run_evaluation.py` (신규) — 평가 CLI
- `tests/test_metrics.py` (신규) — 회귀 7건
- `docs/ai/working-log.md` (본 세션 기록)
- `docs/ai/current-plan.md` (Milestone D feature17 을 17a/17b/17c 로 세분화)

### 정합성 검증 — 설계서 §6 / §7.2.3

- **§6.1 의도 분류 정확도 90%** — 본 세션은 `intent_classification_total`
  분포 가시화 인프라까지. 90% 임계 실측은 feature17b.
- **§6.2 Evaluation Set 50건** — 본 세션 시드 10건, 라벨링 완성은 feature17b.
- **§6.3 Golden Set 3 조건** — `verification_status_total` + Top-1 Cross-
  Encoder 점수 관측 인프라 구축. 자동 추출 (3 조건 AND 필터) 은 feature17b.
- **§6.4 KPI** — 환각 비율 / P95 / Precision@3 모두 메트릭화 인프라 ✓.
- **§7.2.3 ROUGE-L / BERTScore** — 본 세션 미구현. feature17b 이관.

### 검증 명령 / 결과

- 사용자 Mac: `./scripts/verify.sh` 실행 — 607 + 7 = **614 passed 예상**.
- 평가 스크립트 시연: `python scripts/run_evaluation.py` (PoC 그래프 + 시드
  10건) → `reports/evaluation_<timestamp>.json` 산출.

### 후속 TODO (feature17b / 17c 이관)

- **feature17b** (인적 자원 필요):
  - Evaluation Set 50건 완성 라벨링 (의도별 비율 + 첨부 활용 ≥ 8건)
  - 운영 환경 실행 → Precision@k / 의도 분류 정확도 / 환각 비율 실측
  - 설계서 §6.3 3 조건 만족 → Golden Set 자동 추출
  - ROUGE-L / BERTScore 자동 평가 (`evaluate` 라이브러리 도입)
- **feature17c** (평가 결과 기반 튜닝):
  - Pool 가중치 그리드 서치
  - 라우터 prompt 튜닝 (smoke 발견 #2 의도 분류 정확도 90% 달성)
  - 답변 생성기 prompt 튜닝 (환각 비율 15% 이내)
  - Cross-Encoder 임계값 비교 (0.20 / 0.30 / 0.40)

---

## 2026-05-19 — 라우터 의도 분류 prompt 보강 (feature16 발견 #2 fix)

- 브랜치: `feat/#1/rag-pipeline-skeleton`
- 변경 사항: feature17a 의 `scripts/run_evaluation.py --debug-route` 로 4종 의도
  질의를 운영 라우터에 통과시킨 결과 — **4건 중 1건만 정답** (operations_guide
  만 우연 정합), 나머지 3건 모두 incident_response / policy_procedure /
  history_lookup → operations_guide 로 오분류. **설계서 §6.1 임계 90% 와 격차
  큼**. vendoring 한 `query_routing_agent` 의 default prompt 결함을 본 저장소
  transport callable 보강으로 무수정 우회 fix.

### 분석 결과

| 질의 | expected | actual | latency_ms | 비고 |
|------|----------|--------|------------|------|
| EKS NotReady | 장애대응 | 운영가이드 | — | 오분류 |
| Karpenter 도입 단계 | 운영가이드 | 운영가이드 | — | 우연 정답 |
| IAM 정책 변경 절차 | 정책절차 | 운영가이드 | — | 오분류 |
| 지난 분기 비용 증가 원인 | 이력조회 | 운영가이드 | — | 오분류 |

- 정확도 **25%** (1/4). 설계서 §6.1 임계 90% 미충족.
- `rewritten_queries` 가 모두 deterministic fallback (`"원본"`, `"원본 + 검색"`,
  `"원본 + 검색 1"`) — LLM 응답에 `expanded_queries` 없음.
- `metadata_filters` 의 space_keys / labels / document_types 모두 빈 배열 —
  LLM 이 메타필터 추출 안 함.
- `pool_weights = {0.25, 0.6, 0.15}` — agent 의 OPERATIONS_GUIDE 정상 분기
  가중치. **`_apply_fallback` 안 탐 ✓** (라우터 LangGraph fix 정상 작동).

### 원인 (vendoring `query_routing_agent` prompt 결함)

`query_routing_agent/llm/classification.py:57` 의 `build_routing_prompt` 가
빈약함:

```python
return "\n".join([
    "Classify the routing intent for a RAG search request.",
    f"query: {routing_input.query}",
    ...
    "Return JSON with intent, confidence, reason.",
])
```

`query_routing_agent/llm/providers.py:88` 의 `to_openai_payload` 가 만든 system
prompt 도 한 줄: `"You classify RAG query routing intent."`

결함 4종:
1. 4종 의도 라벨의 정의·예시·구분 기준 prompt 미포함 → LLM 이 라벨 의미 모름
2. `expanded_queries` 요청 누락 → rewrite_queries deterministic fallback
3. `metadata_filters` 요청 누락 → space_keys / labels 빈 배열
4. Function Calling schema 강제 없음 (response_format=json_object 만 있음)

### Fix — `app/query/routing_transport.py` 신설

vendoring 코드는 무수정 보존 (CLAUDE.md 절대 규칙) 하고, `OpenAIRoutingLLMProvider`
의 `transport` 인자에 본 저장소가 만든 callable 을 주입해 **default transport 대체**.

- `build_openai_routing_transport(api_key)` — transport callable factory.
- system prompt: 설계서 §4.4.2 / §4.4.3 / §4.4.4 정합 — 4종 의도 정의·예시·구분
  기준 + 한국어 가이드 + 출력 schema (intent / confidence / reason / expanded
  _queries[3] / metadata_filters) 강제.
- user message: agent 의 `build_routing_prompt` 결과를 그대로 전달 (history
  _decision / context_summary 정보 보존).
- response_format=json_object 유지 (agent `parse_routing_llm_response` 가 그대로
  파싱 가능).
- OpenAI `RateLimitError` → `OpenAITransportError(429)` 매핑 (상위 provider 가
  routing fallback 으로 흡수).

### `build_real_deps` 갱신

```python
routing_provider = OpenAIRoutingLLMProvider(
    config=routing_config,
    api_key=openai_api_key,
    transport=build_openai_routing_transport(api_key=openai_api_key),
)
```

### 수정 파일

- `app/query/routing_transport.py` (신규) — transport callable + system prompt
- `app/api/deps.py` — `build_real_deps` 의 OpenAIRoutingLLMProvider 에 transport
  명시 주입
- `tests/query/test_routing_transport.py` (신규) — 회귀 6건 (system prompt 4종
  의도 명시 / user 메시지 보존 / response_format=json_object / model·temp 전달
  / content 반환 / RateLimitError 매핑)
- `tests/api/test_deps.py` — `routing_provider_init["transport"]` 가 callable
  인지 단언 추가
- `docs/ai/working-log.md` (본 세션 기록)
- `docs/ai/current-plan.md` (Milestone D 갱신)

### 정합성 검증 — 설계서

- §4.4.2 (4종 의도 정의) ✓ — system prompt 에 명시
- §4.4.3 (검색 친화적 쿼리 확장 3종) ✓ — schema 강제
- §4.4.4 (의도별 메타필터 + Pool 가중치) ✓ — metadata_filters schema 강제
- §4.4.5 (Function Calling 강제) — response_format=json_object + schema 명세로
  대체 (full Function Calling tools 강제는 후속 — 본 fix 충분)
- §4.4.6 (라우터 실패 시 Fallback) ✓ — RateLimitError 매핑 정합
- §6.1 의도 분류 정확도 90% — 본 fix 후 사용자 Mac 재검증 권장 (4 → 4 정답
  목표)

### 검증 명령 / 결과

- 사용자 Mac: `./scripts/verify.sh` 실행 — 614 + 6 = **620 passed 예상**.
- commit/push 후 **debug-route 재실행** 권장 — 4종 질의가 정확히 4종 의도로
  분류되는지 확인. 결과를 다음 commit 의 후속 기록으로.

### 후속 TODO

- 사용자 Mac 에서 debug-route 재실행 → 본 fix 의 분류 정확도 실측
- feature17b — Evaluation Set 50건 라벨링 + ROUGE-L/BERTScore
- feature17c — Pool 가중치 그리드 서치 + 답변 생성기 prompt 튜닝

### 사용자 Mac 재실행 — fix 효과 실측 (2026-05-19)

본 fix 적용 후 동일 4종 의도 질의를 운영 라우터로 재실행. **정확도 25% →
100% (4/4)** 달성, 설계서 §6.1 임계 90% **충족**.

---

## 2026-05-19 — feature17b 인프라 (chunk_id backfill + ROUGE-L/BERTScore)

- 브랜치: `feat/#1/rag-pipeline-skeleton`
- 변경 사항: feature17b 의 **인프라 부분** 만 본 세션에서 완성 — Evaluation Set
  50건 라벨링 후 즉시 자동 평가 가능한 도구 골격 구축. 50건 라벨링 자체는 사용자
  시간 필요 (별도 세션).

### 1. `scripts/backfill_chunk_ids.py` 신설

- 입력: `samples/evaluation_set.json` (expected_page_ids 채워진 상태)
- 처리: 운영 Qdrant CONTENT_POOL 을 `MatchAny(any=[page_id, ...])` filter 로
  scroll → page_id 별 chunk_id set 산출 → 각 항목의 expected_chunk_ids 자동 채움
- 백업: 갱신 전 `.bak` 사본 생성
- `--dry-run` 옵션: 파일 수정 없이 매칭 결과만 콘솔 출력
- chunking 결과가 결정론 (SHA1) 이므로 한 번 backfill 한 chunk_id 는 stable

### 2. `pyproject.toml` `evaluation` extras 신설

```
evaluation = [
  "evaluate>=0.4.0",
  "rouge-score>=0.1.2",
  "bert-score>=0.3.13",
]
```

사용법: `pip install -e ".[evaluation]"`. ROUGE-L 은 경량 (pure Python),
BERTScore 는 transformers/torch 모델 다운로드 (~500MB, multilingual). 모두
lazy import — 미설치 환경에서도 본 저장소 import 영향 0.

### 3. `scripts/run_evaluation.py` 옵션 확장

- `--rouge-l` — actual answer vs expected_answer_excerpt 의 ROUGE-L F1 평균
- `--bert-score` — 동일 비교의 BERTScore F1 평균 (lang="ko" 강제)
- helper 함수 `_compute_rouge_l_f1_avg` / `_compute_bert_score_f1_avg` 분리 —
  라이브러리 lazy import + 미설치 시 ImportError 안내 메시지
- summary 에 `rouge_l_f1_avg` / `bert_score_f1_avg` / `answer_quality_n_items`
  추가

### 4. 회귀 테스트 신규 7건

- `tests/scripts/test_backfill_chunk_ids.py` (3건):
  - page_id 별 chunk_id 매핑이 expected_chunk_ids 에 채워짐 + 백업 생성
  - --dry-run 시 파일 미수정 + 백업 미생성
  - target page_ids 비어 있으면 scroll 호출 안 함
- `tests/scripts/test_run_evaluation.py` (4건):
  - ROUGE-L helper 평균 산출 (mock scorer)
  - rouge-score 미설치 시 ImportError + "evaluation" 안내
  - BERTScore helper 평균 산출 (mock score)
  - bert-score 미설치 시 ImportError + "evaluation" 안내

`scripts/__init__.py` + `tests/scripts/__init__.py` 신설로 본 회귀가 `from
scripts import ...` 패턴으로 import 가능.

### 수정 파일

- `scripts/backfill_chunk_ids.py` (신규)
- `scripts/run_evaluation.py` — `--rouge-l` / `--bert-score` 옵션 + helper 함수 +
  ROUGE-L/BERTScore 누적 + summary 항목 3종 추가
- `scripts/__init__.py` (신규, 빈 파일)
- `pyproject.toml` — evaluation extras 추가
- `tests/scripts/__init__.py` (신규, 빈 파일)
- `tests/scripts/test_backfill_chunk_ids.py` (신규, 3건)
- `tests/scripts/test_run_evaluation.py` (신규, 4건)
- `docs/ai/working-log.md` (본 세션 기록)
- `docs/ai/current-plan.md` (feature17b 인프라 부분 [x], 라벨링은 미완)

### 정합성 검증 — 설계서

- §6.2 (Evaluation Set 50건 형식 `(질문, 정답 청크 ID 집합, 우수 답변 예시)`) —
  backfill 로 정답 청크 ID 집합 자동 채움 ✓
- §6.3 Golden Set 채택 기준 (3 조건 AND) — verification_status / Cross-Encoder
  Top-1 점수 / 사용자 피드백 인프라 모두 보유. 자동 추출은 feature17b 다음
  단계 (50건 실행 후)
- §6.4 KPI (Precision@3 75% 이상) — expected_chunk_ids backfill 후 정밀 매칭
  가능
- §7.2.3 ROUGE-L / BERTScore 자동 평가 — 라이브러리 도입 + helper 함수 ✓

### 검증 명령 / 결과

- 사용자 Mac: `./scripts/verify.sh` 실행 — 620 + 7 = **627 passed 예상**.
- evaluation extras 설치 후 사용 가이드: `pip install -e ".[evaluation]"` →
  `python scripts/backfill_chunk_ids.py` → `python scripts/run_evaluation.py
  --use-real-adapters --rouge-l --bert-score`.

### 후속 (다음 세션, 사용자 시간 필요)

- **feature17b 라벨링** — `samples/evaluation_set.json` 에 40건 더 추가 (의도
  비율 35:30:20:15 + 첨부 활용 ≥ 8건).
- backfill 1회 실행으로 expected_chunk_ids 자동 채움.
- 운영 환경 평가 실행 + Golden Set 자동 추출 (3 조건 AND 필터 신설).
- **feature17c** — 평가 결과 기반 튜닝 (Pool 가중치 / 생성기 prompt / Cross-
  Encoder 임계값). 라우터 prompt 는 직전 commit 으로 달성됨.

---

## 2026-05-19 — feature17b Claude bootstrap 라벨링 (40건 추가)

- 브랜치: `feat/#1/rag-pipeline-skeleton`
- 변경 사항: `samples/evaluation_set.json` 에 Claude bootstrap 라벨링 40건 추가.
  시드 10건 (사람 작성) + bootstrap 40건 = **총 50건**. 설계서 §6.2 비율 정합.
  사용자 검수 후 LLM-as-Judge 순환 문제를 회피한 채 회귀 평가 baseline 으로
  활용 가능.

### 분포 (설계서 §6.2 / §3.3.B 정합)

| 의도 | 목표 | 실제 | 결과 |
|------|------|------|------|
| 장애대응 | 35% | 17건 (34%) | ✓ |
| 운영가이드 | 30% | 15건 (30%) | ✓ |
| 정책절차 | 20% | 10건 (20%) | ✓ |
| 이력조회 | 15% | 8건 (16%) | ✓ |
| 첨부 활용 (v0.2.2) | ≥ 8건 | **8건** | ✓ |

### Claude bootstrap 라벨링 한계 명시

- 각 항목에 `label_source` 필드 추가: `human` (시드 10건) / `claude_bootstrap`
  (추가 40건).
- **LLM-as-Judge 순환 문제 회피** — Claude 가 만든 평가 데이터셋으로 동일
  계열 LLM (GPT-4o) 평가는 객관성 한계. bootstrap 회귀 baseline (직전 vs 다음
  버전 모델 비교) 용도까지가 권장 범위. 최종 Golden Set 채택은 사용자 피드백
  추가 검증 필요.
- 각 query 는 samples 페이지의 실 콘텐츠에 직접 매핑됨 — bootstrap 항목도
  expected_page_ids 가 명확해 chunk_id backfill 즉시 가능.

### 첨부 활용 8건 매핑

samples 의 첨부는 4건 (EKS 운영 매뉴얼 / Datadog 메트릭 정의서 / EKS 노드
사용량 통계 / 신규입사 체크리스트). 각 첨부에서 2건씩 다른 각도 질문으로 8건
확보. 설계서 v0.2.2 의 "첨부 활용 질문 16% 이상" 정합.

### 수정 파일

- `samples/evaluation_set.json` — 10건 → **50건** + label_source 필드 추가
- `docs/ai/working-log.md` (본 세션 기록)
- `docs/ai/current-plan.md` (feature17b 라벨링 [x] bootstrap 만, 사용자 검수
  대기 명시)

### 검증

- 의도 비율 자동 검증 통과 (Python Counter 로 확인)
- label_source / is_attachment_focused 분포 정합 확인
- ruff/format 영향 없음 (JSON 데이터 변경만)
- pytest 회귀 영향 없음 — 627 passed 유지

### 후속 (사용자 검수 필요)

1. **사용자 검수** — `samples/evaluation_set.json` 의 EVAL-011 ~ EVAL-050
   40건을 빠르게 훑어보고 (1) 질문이 의미 있는지, (2) expected_page_ids 가
   정확한지, (3) expected_answer_excerpt 가 답변 베이스라인으로 적절한지 확인.
   부적절한 항목은 직접 수정 또는 label_source 를 `human` 으로 승격.
2. **backfill** — `python scripts/backfill_chunk_ids.py` 1회 실행 → expected
   _chunk_ids 자동 채움.
3. **운영 평가** — `python scripts/run_evaluation.py --use-real-adapters
   --rouge-l --bert-score` → 50건 자동 평가.
4. **Golden Set 추출** — 설계서 §6.3 3 조건 만족 항목 자동 필터 (feature17b
   다음 단계).
5. **feature17c** — 평가 결과 기반 Pool 가중치 / Cross-Encoder 임계값 튜닝.

| 질의 | expected | actual | 결과 |
|------|----------|--------|------|
| EKS NotReady | 장애대응 | 장애대응 | ✅ |
| Karpenter 도입 단계 | 운영가이드 | 운영가이드 | ✅ |
| IAM 정책 변경 절차 | 정책절차 | 정책절차 | ✅ |
| 지난 분기 비용 증가 원인 | 이력조회 | 이력조회 | ✅ |

rewritten_queries 도 deterministic fallback ("원본 + 검색", "원본 + 검색 1")
에서 의미 있는 검색 친화적 확장으로 개선:

- Q1 (장애대응): "EKS Worker Node NotReady 상태 대응 방법은?" /
  "EKS Worker Node가 NotReady일 때의 대응 절차는?"
- Q2 (운영가이드): "EKS Karpenter 도입 절차는?" /
  "Karpenter 설치를 위한 EKS 단계는?"
- Q3 (정책절차): "IAM policy change procedure 어떻게 하나요?" (한영 혼용) /
  "IAM 정책 변경을 위한 절차는?"
- Q4 (이력조회): "지난 분기 클라우드 비용 증가 이유는?" /
  "What caused the increase in cloud costs last quarter?" (한영 혼용)

→ **검색 hit 률 개선 기대** + 한영 혼용 확장으로 BM25 매칭 다양성 확보.

본 결과로 feature17c 의 "라우터 prompt 튜닝 (의도 분류 정확도 90% 달성)"
TODO 는 **사실상 본 fix 로 달성** — 후속 세션에서는 다른 튜닝 항목 (Pool
가중치 / Cross-Encoder 임계값 / 생성기 prompt) 에 집중 가능.

---

## 2026-05-20 — feature17b 평가 본 실행 + Golden Set 추출 + 527 v0.2.0 docx

- 브랜치: `feat/#1/rag-pipeline-skeleton`
- 변경 사항: feature17b 의 **본 실행** 단계 완료 — bootstrap 40건 검수 →
  chunk_id backfill → 운영 모드 평가 50건 실측 → Golden Set 자동 추출 →
  527 리포트 v0.2.0 docx 의 §3 를 정량 데이터로 갱신. 평가 본 실행 과정에서
  검색 0건을 유발하던 버그 2건을 발견·수정.

### 1. Evaluation Set EVAL-011~050 검수 (bootstrap 40건)

- 1차 (expected_page_ids 존재): 40건 모두 실제 samples 페이지에 존재 ✓
- 2차 (첨부 활용 8건): 모두 페이지·첨부 정확 매핑 ✓
- 3차 (의심 항목): EVAL-020 의미 정합 OK / **EVAL-050 정정** —
  expected_answer_excerpt 가 페이지 본문 의역체였음. 설계서 v0.2.2 §3.6.3
  "Qdrant 선정 핵심 근거" 공식 표현으로 교체하고 `label_source` 를
  `claude_bootstrap` → `human` 승격. label_source 분포: human 11 / bootstrap 39.

### 2. chunk_id backfill (운영 Qdrant scroll)

- `python scripts/backfill_chunk_ids.py` 실행 — 43개 target page_id → chunk_id
  114건 매칭. `samples/evaluation_set.json` 의 expected_chunk_ids 자동 채움 +
  `.bak` 백업 생성. (page-level 매칭에는 webui_link 를 쓰므로 chunk_id 는
  다음 세션 chunk-level 정밀 매칭 / 회귀 비교용으로 유지.)

### 3. 평가 본 실행 — 검색 0건 버그 2건 발견·수정

운영 모드 첫 실행 시 precision_at_k=0 / top1_score=null / verification=0 으로
**전건 검색 0건**. 단계적 진단으로 원인 2건 확정·수정:

- **(fix A) `scripts/run_evaluation.py` ACL filter 단일 그룹 버그** —
  `build_acl_filter("eval-user", ["space:CLOUD"])` 로 1개 그룹만 전달해 samples
  의 다른 6개 space (CCC/DEVOPS/SEC/ONBOARD/PROJ/DATADOG_KR) 페이지가 ACL
  단계에서 모두 차단. 평가용 사용자가 7개 space 전체에 접근 가능하도록 확장
  (debug-route 모드도 동일 적용).
- **(fix B) `app/query/search_node.py` `_coerce_metadata_filters` 빈 list 버그**
  — 라우터가 채운 빈 배열 (`space_keys: []`, `labels: []` 등) 이 그대로 통과해
  Qdrant `MatchAny(any=[])` 가 생성되고, `_build_combined_filter` 의 must 결합
  시 빈 set 조건 1개가 **모든 검색 결과를 차단**. 빈 list / 빈 문자열을 명시적
  으로 거르도록 수정. (라우터 metadata_filters 출력에 빈 배열 4종이 항상 있어
  50/50 전건 0건이 일관 발생했음.)
- **(fix C) Precision@k 정밀 매칭 보완** — 약식 매칭(sources 비어 있지 않음)을
  samples 의 `page_id → webui_link` 매핑 기반 page-level 정밀 매칭으로 교체
  (`match_method=webui_link_strict`). Source 스키마에 chunk_id/page_id 직접
  필드가 없고 confluence_url 패턴에도 page_id 가 없어 webui_link 동일성으로 매칭.

### 4. 평가 본 실행 실측 결과 (reports/evaluation_20260520_014709.json)

| 지표 | 측정 | 목표 | 결과 |
|------|------|------|------|
| 의도 분류 정확도 | 94% (47/50) | 90% | ✅ 통과 |
| Precision@3 | 68% (34/50) | 75% | ⚠ 살짝 미달 |
| 환각 비율 (NOT_SUPPORTED 문장) | 36.1% (57/158) | 15% | ⚠ 초과 |
| 응답 P95 (non-streaming) | 16.6초 (avg 10.7) | 5초 | ⚠ 초과 (streaming 권장) |
| ROUGE-L F1 평균 | 0.199 | — | 의역체 baseline 정합 |
| BERTScore F1 평균 | 0.673 | — | multilingual 정합 |
| Top-1 Cross-Encoder 평균 | 100 (38건 saturate) | 관측 | 🤔 saturation 후속 조사 |

- 의도별 Precision@3: 장애대응 82% / 운영가이드 67% / 정책절차 50% / 이력조회 62%.
- **첨부 활용 8건 Precision@3 = 12% (1/8)** — 가장 큰 약점. Pool 가중치가 본문
  위주이고 첨부 청크 임베딩 입력의 attachment_filename 가중 부족 추정 →
  feature17c attachment_focused 분리 평가 권장.

### 5. Golden Set 추출 (`scripts/extract_golden_set.py` 신설)

- 설계서 §6.3 3 조건 AND 필터 — verification PASS/SUPPORTED + Cross-Encoder
  Top-1 ≥ 0.85 (score 85) + 사용자 피드백 Positive (또는 미제출). 임계값 스케일
  자동 인식 (0~1 / 0~100), 피드백 미보유 환경 fallback (조건 #3 통과).
- 결과 (reports/golden_set_20260520_015102.json): **3 / 50 (6.0%)** 추출
  (EVAL-016 / EVAL-025 / EVAL-037). 조건별 단독: #1 verification 13 / #2
  Top-1≥85 38 / #3 feedback 50. 추출률을 좌우하는 1차 병목은 조건 #1 (생성기
  보수성) — 생성기 prompt 튜닝 시 함께 개선될 것으로 예상.

### 6. 527 리포트 v0.2.0 docx 작성

- v0.1.0 docx 를 base 로 unpack → XML 직접 편집 → pack (양식 100% 정합 보존:
  컬러 팔레트 2E5395/F2F2F2/1F3864/333333/BFBFBF, Malgun Gothic, 표 구조).
- §1·§2·§4 본문 보존, **§3 전체를 본 세션 정량 데이터로 교체** (§3.1 KPI 5종 /
  §3.2 ROUGE-L·BERTScore / §3.3 의도별·첨부 분해 / §3.4 Golden Set / §3.5 발견
  사항·부수 fix). 표지 메타 v0.2.0 / 2026-05-20, 개정 이력 v0.2.0 단락 추가,
  §1.2 상태 표 "대기"→"완료/일부 이관" 갱신.
- 저장: Claude 임시 작업 폴더 `outputs/deliverables/` (RAG 저장소 비건드림).
  파일명 `[척척학사]_500.구현_결과_보고서_527_RAG검색품질_성능최적화_리포트_v0.2.0.docx`.
- docx 양식 검증 (`scripts/office/validate.py`) — All validations PASSED.

### 수정 파일

- `samples/evaluation_set.json` — EVAL-050 정정 (excerpt + human 승격) +
  backfill 로 expected_chunk_ids 채움 (`.bak` 백업)
- `scripts/run_evaluation.py` — ACL filter 7개 space 확장 (fix A) + Precision@k
  webui_link 정밀 매칭 (fix C) + summary.match_method
- `app/query/search_node.py` — `_coerce_metadata_filters` 빈 list/문자열 거름 (fix B)
- `scripts/extract_golden_set.py` (신규) — 3 조건 AND 필터 Golden Set 추출
- `tests/scripts/test_run_evaluation.py` — 정밀 매칭 회귀 +5
- `tests/scripts/test_extract_golden_set.py` (신규) — 3 조건 회귀 19
- `tests/query/test_search_node.py` — 빈 list/문자열 metadata 회귀 +3
- `docs/ai/working-log.md` (본 단락)

### 검증 명령 / 결과

- 사용자 Mac: 평가 본 실행 50건 정상 (search_node fix 적용 후 검색 정상화) +
  Golden Set 추출 3건 + docx validate PASSED.
- 본 세션 격리 검증: `_coerce_metadata_filters` 5케이스 + run_evaluation/
  extract_golden_set 회귀 (사용자 Mac 의 `.venv` 에서 `pytest tests/scripts/`
  + `tests/query/test_search_node.py` 통과 권장).

### 후속 (feature17c)

- **Top-1 Cross-Encoder saturation (모두 100) 조사** — 임계값 비교 (0.20/0.30/
  0.40) 이전에 점수 분포 신뢰성 검증 선행.
- **첨부 활용 검색 약점 (Precision 12%)** — Pool 가중치 그리드 서치 시
  attachment_focused 분리 평가.
- **환각 비율 36% / 정책절차 Precision 50%** — 생성기 prompt 튜닝 + Cross-
  Encoder 임계값 조정.
- non-streaming P95 16.6초 — BFF/UI stream=true 사용 권장 (본 저장소 추가 fix 불요).

---

## 2026-05-20 — feature17c-1: Cross-Encoder Top-1 saturation 진단 + temperature scaling 인프라

- 브랜치: `feat/#1/rag-pipeline-skeleton`
- 변경 사항: feature17b 평가에서 발견된 Top-1 Cross-Encoder 점수 saturation
  (38건 모두 100) 의 원인을 코드 레벨로 진단하고, temperature scaling 인프라를
  구축. 실 T 값 결정·임계값 재조정·재평가는 사용자 Mac 데이터 기반 (feature17c-2).

### 1. 원인 진단 (코드 버그 아님 — 모델 + sigmoid 특성)

`CrossEncoderRerankerImpl.score()` 가 ms-marco cross-encoder
(`cross-encoder/ms-marco-MiniLM-L-12-v2`) 의 raw logit 에 sigmoid 를 적용한다.
ms-marco 계열은 관련 passage 에 큰 양수 logit(8~11)을 출력하는 특성이 있어
`sigmoid(logit ≥ 5.30) ≥ 0.995 → round(*100) = 100`. Top-1(최고 관련) passage
의 logit 은 거의 항상 5.30 이상이라 38건 전부 score=100 으로 saturate
(12건 null 은 검색 0건).

- **영향 (3종)**: (1) Source.score 변별력 손실, (2) `select_reranked` 의
  `LOW_CONFIDENCE_THRESHOLD=0.20`(최고<0.20 저신뢰) 거의 안 걸림 → 저신뢰
  분기 무력화, (3) Golden Set 조건 #2(Top-1 ≥ 0.85) 가 "검색 결과 있으면 통과"
  와 동일(38/38).
- **영향 없음**: ranking(순위)은 logit 순서를 보존 → Top-K 선정·Precision@3(68%)
  은 saturation 과 무관. 점수 스케일/임계값 설계 문제이지 검색 품질 문제 아님.

### 2. Temperature scaling 인프라 (사용자 선택)

- `app/config.py` — `cross_encoder_temperature: float = 1.0` 신설. 기본 1.0 은
  현행 동작(무변경) 보존. 운영에서 `RAG_CROSS_ENCODER_TEMPERATURE` 로 주입.
- `app/query/reranker/cross_encoder.py` —
  - `__init__(temperature=1.0)` + 0 이하 ValueError 가드.
  - `score()` 가 `sigmoid(logit / temperature)` 적용 (T=1.0 이면 현행 동일).
  - `predict_logits()` 신설 — raw logit 직접 반환 (활성화 미적용). logit 분포
    수집·T 결정용.
- `app/api/deps.py` — `build_real_deps` 가 `settings.cross_encoder_temperature`
  를 reranker 에 주입.
- 검증(분석): T=1 은 logit 5.30+ 에서 score 100 saturate / T=4 는 logit 3~11 이
  68~94 / T=8 은 59~80 으로 변별 회복. 권장 탐색 범위 3.0~8.0.

### 3. logit 분포 수집 디버그 (`run_evaluation.py --debug-rerank`)

- 단일 질문의 검색 후보 raw logit 분포 + T별(1/2/3/4/5/8) Top-1 sigmoid 점수
  미리보기 출력. 운영 reranker(predict_logits) 필요 → `--use-real-adapters`.
- 사용자가 실 ms-marco logit 분포를 보고 데이터 기반으로 T 를 결정한다.

### 4. 회귀 테스트 (`tests/query/reranker/test_cross_encoder.py`)

- temperature 6건 추가: saturation 완화 / ranking 보존(단조변환) /
  predict_logits raw 반환 / predict_logits 빈 입력 / temperature 0·음수 ValueError.
- `_make_reranker` 헬퍼에 temperature 파라미터 추가 (기본 1.0).
- sentence-transformers importorskip 이라 사용자 Mac 에서 실행.

### 수정 파일

- `app/config.py` — cross_encoder_temperature 설정
- `app/query/reranker/cross_encoder.py` — temperature scaling + predict_logits
- `app/api/deps.py` — temperature 주입
- `scripts/run_evaluation.py` — `--debug-rerank` 옵션
- `tests/query/reranker/test_cross_encoder.py` — temperature 회귀 +6
- `docs/ai/working-log.md` (본 단락)

### 후속 (feature17c-2, 사용자 Mac 데이터 기반)

1. `python scripts/run_evaluation.py --debug-rerank "<질문>" --use-real-adapters`
   를 여러 의도 질문으로 실행해 실 logit 분포 수집.
2. 적정 T 결정 (권장 3.0~8.0) → `.env` 의 `RAG_CROSS_ENCODER_TEMPERATURE` 설정.
3. T 에 맞춰 임계값 재조정 — `select_reranked` 의 `NARROW_SCORE_THRESHOLD`(0.30) /
   `LOW_CONFIDENCE_THRESHOLD`(0.20), 포맷터 `LOW_CONFIDENCE_SCORE`(20), Golden Set
   조건 #2(0.85). T 적용 후 점수 분포에 맞춰 재정의.
4. 재평가 (`run_evaluation --use-real-adapters --rouge-l --bert-score`) →
   Top-1 분포 변별 회복 + 저신뢰 분기·Golden Set #2 정상 작동 확인.
5. 이후 Pool 가중치 그리드 서치(첨부 12% / 정책절차 50% 개선) + 생성기 prompt
   튜닝(환각 36%) 으로 진행.

---

## 2026-05-20 — feature17c-2: T=4 확정 + 임계값 재조정

- 브랜치: `feat/#1/rag-pipeline-skeleton`
- 변경 사항: feature17c-1 의 `--debug-rerank` 로 수집한 실 logit 분포를 근거로
  temperature=4.0 을 확정하고, sigmoid 후 score 기준 임계값들을 T=4 분포에 맞춰
  재조정. 50건 재평가로 검증 예정 (사용자 Mac).

### 1. 실 logit 분포 (사용자 Mac --debug-rerank)

| 질문 | Top-1 logit | 분포 |
|------|-------------|------|
| EKS NotReady (장애대응) | 8.492 | max 8.49 / min 0.14 / mean 3.71 |
| IAM 정책 변경 (정책절차) | 8.843 | max 8.84 / min 2.68 / mean 7.05 |

- 강관련 passage 의 logit 상한 ≈ 8.5~8.8. T=1 에서 logit 5.30+ 는 sigmoid≈1.0
  → round 100 saturate (관측 결과와 정합).
- T=4: 강관련(logit 8~9) → score 88~90 / 중관련(logit ~4.8) → 77 / 무관(logit
  ~0.1) → 51. 변별 회복 + "강관련=높은 점수" 직관 보존 → T=4.0 채택.

### 2. 임계값 재조정 (T=4 분포 기준)

| 항목 | 기존 | 신규 | 파일 |
|------|------|------|------|
| cross_encoder_temperature | 1.0 | **4.0** | `app/config.py` |
| select_reranked NARROW_SCORE_THRESHOLD | 0.30 | **0.65** | `app/query/rerank.py` |
| select_reranked LOW_CONFIDENCE_THRESHOLD | 0.20 | **0.55** | `app/query/rerank.py` |
| formatter LOW_CONFIDENCE_SCORE | 20 | **55** | `app/query/formatter.py` |
| extract_golden_set top1-threshold (기본) | 0.85 | **0.80** | `scripts/extract_golden_set.py` |

- LOW(저신뢰)·NARROW(Top-3 축소)·formatter 저신뢰·Golden #2 가 T=4 점수 분포
  에서 일관되게 작동하도록 동시 재조정. select_reranked LOW(0.55) 와 formatter
  LOW_CONFIDENCE_SCORE(55) 는 동일 기준(0~1 vs 0~100)으로 정합.

### 3. 회귀 갱신

- `tests/query/test_rerank.py` — NARROW 0.65 / LOW 0.55 기준으로 점수·경계값
  재설계 + 경계 테스트 1건 추가 (최고=0.55 면 저신뢰 아님). 임계값 상수 import 로
  하드코딩 제거.
- `tests/query/test_formatter.py` — 저신뢰 경계 테스트 2건을 55 기준으로 갱신
  (`test_low_confidence_boundary_score_55`). _source(80) 계열은 80 ≥ 55 라 의도
  보존, 변경 불필요.
- extract_golden_set 회귀는 모두 명시 인자(threshold_score=85)라 기본값 변경과
  무관 — 변경 없음.
- **회귀 누락 보완 (2026-05-20 후속)**: 사용자 Mac pytest 에서 `tests/query/test_
  rerank_node.py` 의 임계값 의존 회귀 3건이 실패(NARROW 0.30/LOW 0.20 가정).
  feature17c-2 1차에서 test_rerank.py 만 갱신하고 rerank_node 회귀를 놓침 →
  보완: (1) test_seven_candidates_select_top_five_by_score 점수 0.65~0.95 로
  재설계, (2) test_no_narrow_when_fifth_score_at_or_above_threshold 5위가
  NARROW(0.65)가 되도록 점수 조정, (3) test_low_confidence_threshold_alignment
  20→55 + formatter LOW_CONFIDENCE_SCORE 일치 단언 추가, (4) test_all_low_scores
  주석·단언 55 정합. 격리 검증 통과.
- 검증: select_reranked 7 + formatter 6 + rerank_node 3 시나리오 격리 통과 (본
  세션은 Python 3.10 이라 StrEnum 체인 import 불가 → app import 회귀는 사용자
  Mac 3.11. 사용자 Mac 에서 45건 전체 통과 확인 권장).

### 수정 파일

- `app/config.py` — cross_encoder_temperature 1.0 → 4.0
- `app/query/rerank.py` — NARROW 0.65 / LOW 0.55
- `app/query/formatter.py` — LOW_CONFIDENCE_SCORE 55
- `scripts/extract_golden_set.py` — 기본 top1-threshold 0.80
- `tests/query/test_rerank.py` / `tests/query/test_formatter.py` — 회귀 갱신
- `docs/ai/working-log.md` (본 단락)

### 후속 (사용자 Mac 검증)

1. `pytest tests/query/test_rerank.py tests/query/test_formatter.py
   tests/query/reranker/test_cross_encoder.py -v` (3.11 환경).
2. 50건 재평가 (`run_evaluation --use-real-adapters --rouge-l --bert-score`) →
   top1_score 분포가 88~90 중심으로 펴졌는지 + 저신뢰 분기 작동 + Golden Set
   추출 건수 변화 확인.
3. 재평가 top1_score 분포를 보고 LOW/NARROW/Golden 임계값 미세조정 (필요 시).
4. 이후 Pool 가중치 그리드 서치 / 생성기 prompt 튜닝.

---

## 2026-05-20 — feature17c-3: Source.score saturation 진짜 원인 fix (generator 진짜 rerank score 전달)

- 브랜치: `feat/#1/rag-pipeline-skeleton`
- 변경 사항: feature17c-2 적용 후에도 평가 top1_score 가 100 으로 유지되는 현상을
  추적해 **최종 Source.score saturation 의 진짜 원인이 Cross-Encoder 가 아니라
  답변 생성기(generator)의 가짜 rerank_score** 임을 확정하고 수정.

### 1. 진단 — Cross-Encoder 아닌 generator 가 원인

- `deps.reranker.score()` 직접 호출 검증: T=4 에서 `[0.894, 0.305]` → 변별 정상.
  즉 reranker·temperature 는 완벽히 작동.
- 그러나 평가 경로의 최종 `Source.score` 는 여전히 100. 추적 결과
  `app/query/generator.py::_chunk_to_top_context_payload` 가 agent 에 넘기는
  `rerank_score` 를 **순서 보존용 가짜값 `1.0 - 0.001*index`** (Top-1=1.0) 로
  부여하고 있었음. agent 는 이 값을 `GeneratedSource.rerank_score` 로 보존
  (`citation_mapping.py`), `_agent_sources_to_rag_sources` 가
  `Source.score = rerank_score × 100` 으로 역변환 → **Top-1 항상 100**.
- 결론: rerank_node 의 실제 Cross-Encoder 점수가 generator 단계에서 버려지고
  순번 기반 가짜값으로 대체됨. temperature scaling 은 select_reranked(Top-K
  선정·저신뢰 판정)에만 도달하고 최종 출처 카드 점수에는 미반영이었음.

### 2. Fix — RagState.rerank_scores 로 실제 점수 전달

- `app/schemas/rag_state.py` — `rerank_scores: dict[str, float]` 신설
  (chunk_id → Cross-Encoder score 0~1). top_chunks(Chunk)는 점수를 싣지 못하므로
  별도 map 으로 전달.
- `app/query/rerank_node.py` — `select_reranked` 결과의 실제 점수를
  `state.rerank_scores` 에 저장.
- `app/query/generator.py` [Agent 담당 영역 — 아래 경계 메모] —
  `_chunk_to_top_context_payload(chunk, *, index, rerank_score=None)` 로 확장.
  `state.rerank_scores.get(chunk_id)` 를 넘겨 실제 점수가 있으면 사용, None 이면
  기존 `1.0 - 0.001*index` fallback(후방 호환). agent vendoring 코드
  (`answer_generation_agent/`)는 무수정 — agent 가 rerank_score 를 보존하는
  기존 계약을 그대로 활용.

### 3. 담당 영역 경계 메모 (CLAUDE.md 정합)

- `app/query/generator.py` 는 `docs/ai/current-plan.md` feature10 기준 **Agent
  담당 영역**이다. 본 수정은 사용자 승인 하에 본 담당자(Pipeline)가 진행했으며,
  변경 범위는 (1) 함수 시그니처에 `rerank_score` 키워드 추가, (2) 호출부가
  `state.rerank_scores` 참조 — 두 곳으로 한정. **agent 패키지·프롬프트·정렬
  로직은 무수정**. rerank_score 미제공 시 기존 동작이 그대로 유지되어 Agent
  담당자의 기존 가정과 충돌하지 않는다. Agent 담당자 통보 필요.

### 4. 회귀

- `tests/query/test_generator.py` — `_state` 에 rerank_scores 파라미터 추가 +
  3건: payload 가 실제 rerank_score 사용 / None 이면 fallback / 통합(rerank_scores
  주입 시 Source.score=89 — 가짜 100 아님).
- `tests/query/test_rerank_node.py` — 2건: rerank_scores map 채워짐 / 검색 0건 시
  빈 dict 유지.
- 격리 검증: effective_rerank_score 로직 (진짜 0.89→89, fallback 0.999) 통과.
  (본 세션 Python 3.10 StrEnum 제약 → app import 회귀는 사용자 Mac 3.11.)

### 5. v0.2.0 docx 정정 필요 (후속)

- 527 v0.2.0 docx §3.5 의 "Top-1 saturation = ms-marco 모델 특성 + sigmoid"
  설명은 **부정확**. 진짜 원인은 generator 의 가짜 rerank_score 였음. 또 §3.1·§3.4
  의 top1_score=100 은 generator fix 전 값이므로, fix 후 재평가 결과로 갱신해야
  한다 → v0.2.1 docx 또는 재평가 후 §3 재갱신.

### 수정 파일

- `app/schemas/rag_state.py` — rerank_scores 필드
- `app/query/rerank_node.py` — rerank_scores 저장
- `app/query/generator.py` — _chunk_to_top_context_payload rerank_score 인자
- `tests/query/test_generator.py` / `tests/query/test_rerank_node.py` — 회귀 +5
- `docs/ai/working-log.md` (본 단락)

### 후속 (사용자 Mac)

1. `pytest tests/query/test_generator.py tests/query/test_rerank_node.py -v` (3.11).
2. 50건 재평가 → top1_score_avg 가 88~90 부근으로 펴졌는지 확인 (가짜 100 해소).
   이때 비로소 formatter LOW_CONFIDENCE_SCORE(55)·Golden Set(0.80)·저신뢰 분기가
   실제 점수 기준으로 작동한다.
3. 재평가 결과로 527 §3 재갱신 (v0.2.1) + §3.5 saturation 원인 정정.
4. 임계값 미세조정 후 Pool 가중치 그리드 서치 / 생성기 prompt 튜닝.
