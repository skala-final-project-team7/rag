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
