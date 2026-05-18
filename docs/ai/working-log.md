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
