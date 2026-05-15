# Current Plan

이 문서는 현재 진행 중인 작업의 Plan을 기록한다.
구현 전에 작성하고, 작업 중 계획이 바뀌면 함께 수정한다.
하나의 feature가 끝나면 체크 처리하고, 모든 feature가 끝나면 새 세션에서 다음 Plan을 작성한다.

---

## 작업 개요

- **작업 목표**: <이번 change-set의 목표>
- **담당 영역**: RAG Pipeline
- **브랜치**: `feat/#<이슈번호>/<기능-이름>`
- **수정 가능 파일**: `app/`, `tests/`, 관련 `docs/`
- **수정 금지 파일**: 루트 `CLAUDE.md`, 다른 팀원 담당 영역
- **참고 문서**: 루트 `CLAUDE.md`, `app/CLAUDE.md`, `docs/architecture.md`, `docs/conventions.md`, `docs/db-schema.md`

---

## Feature 목록

각 feature는 `[ ]` 미완료 / `[x]` 완료로 관리한다.

### feature1: <이름>

- 요구사항 요약: <current-plan 기준 구현 범위>
- 테스트 계획: <Unit / Integration / 평가 질문 세트>
- 문서 수정 필요 여부: <api-spec / db-schema / architecture 중 해당 사항>
- 위험 요소: <ACL 우회, 출처 누락 등 주의점>

작업 항목:

- [ ] 기능 1 구현
- [ ] 기능 2 구현

### feature2: <이름>

작업 항목:

- [ ] 기능 1 구현
- [ ] 기능 2 구현

---

## 진행 규칙 (요약)

1. feature 단위로만 작업한다. 다음 feature는 새 세션 또는 `/clear` 후 시작한다.
2. 테스트 케이스 정리 → 실패 테스트 작성 → 최소 구현 → 테스트 통과 순서를 지킨다.
3. 완료 후 `./scripts/format.sh`, `./scripts/lint.sh`, `./scripts/test.sh`(또는 `./scripts/verify.sh`)를 실행한다.
4. `git diff`로 변경 범위를 확인하고 `docs/ai/working-log.md`를 업데이트한 뒤 커밋한다.
