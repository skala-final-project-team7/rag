# app/CLAUDE.md — RAG Pipeline 전용 규칙

이 문서는 RAG Pipeline 영역(`app/`, `tests/`)에서만 적용되는 규칙을 정의한다.
작업 시 루트 `CLAUDE.md`의 공통 규칙을 먼저 적용하고, 이 문서의 규칙을 추가로 따른다.

> Codex를 사용하는 팀원은 이 파일을 `app/AGENTS.md`로 복사하거나 심볼릭 링크로 연결해 사용한다.

---

## RAG Pipeline Rules

- 파이프라인 단계를 명확히 분리한다: Query Preprocessing → Intent Analysis → Permission Filtering → Hybrid Retrieval → Reranking → Context Building → Answer Generation → Citation Verification → Response Formatting.
- Retrieval, Reranking, Generation, Citation Verification 단계는 서로의 책임을 침범하지 않는다.
- ACL pre-filtering 또는 Citation Verification을 우회하지 않는다.
- 출처 없는 답변을 생성하는 방향으로 수정하지 않는다.
- Retrieval 결과가 비어 있으면 답변을 생성하지 않고 명시적으로 처리한다.
- 프롬프트 변경 시 변경 의도, 기대 효과, 부작용 가능성을 문서화한다.
- chunking, embedding, retrieval 설정 변경 시 평가 쿼리 결과를 함께 기록한다.
- 실험성 코드는 production path에 직접 연결하지 않는다.

## Stack 규칙

- Python 3.11.x 기준으로 작성한다.
- LangGraph 0.2.x / LangChain 0.3.x / `openai>=1.30` 기준으로 작성한다.
- Vector DB는 Qdrant, 문서 저장소는 MongoDB를 사용한다 (`docs/architecture.md`, `docs/db-schema.md` 참고).
- LangGraph 노드는 단일 책임을 갖도록 작성하고, 노드 입출력 상태는 `RagState`로 통일한다.
- 외부 호출(LLM, Qdrant, MongoDB)은 어댑터/클라이언트 계층으로 분리하고 파이프라인 노드에서 직접 호출하지 않는다.
- 주요 단계 함수에는 `docs/conventions.md`의 표준 주석 블록을 작성한다.

## Evaluation Rules

- 변경 후 최소 평가 질문 세트를 실행한다.
- Precision@k, 응답 지연(latency), 출처 정확도 중 변경 영향이 있는 항목을 기록한다.
- 평가 결과는 `docs/ai/working-log.md`에 함께 남긴다.

## Test Rules

- 각 파이프라인 단계 함수는 Unit Test를 작성한다.
- LLM·Qdrant·MongoDB 등 외부 의존성은 mock 또는 fake로 대체해 테스트한다.
- 버그 수정 시 재현 테스트를 먼저 작성한다.
- 구현 전 테스트 케이스를 먼저 정리한다(`docs/ai/workflow.md`의 테스트 우선 절차).
