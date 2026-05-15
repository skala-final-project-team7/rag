"""app.query — Query 파이프라인.

사용자 질문 + JWT를 받아 검증된 답변과 출처를 반환한다.
모든 검색 호출에 ACL 필터가 시스템 단에서 강제 적용된다.

단계 및 분류 (docs/rag-pipeline-design.md §6):
- acl.py        ACL Pre-filtering [Pipeline]  JWT → Qdrant 필터 생성 + @enforce_acl 데코레이터
- history.py    멀티턴 히스토리 관리자 [Agent]  보존/삭제/검색스킵 판단 (GPT-4o-mini, 최근 5턴)
- router.py     질의 라우터 [Agent]  단일 LLM 호출 = Intent + Query Rewrite + Filter Builder
- search.py     Multi-Pool Hybrid Search [Pipeline]  3 Pool 병렬 + RRF + 가중 합산 → Top-20
- rerank.py     Cross-Encoder 재순위화 [Pipeline]  ms-marco-MiniLM-L-12, Top-20 → Top-5
- generator.py  답변 생성기 [Agent]  의도별 프롬프트 + GPT-4o + SSE 스트리밍 + Function Calling
- verifier.py   답변 검증 [Pipeline + Agent]  1단계 규칙 매칭 → FLAG → 2단계 LLM 평가자
- formatter.py  응답 포맷터 [Pipeline]  검증된 답변·출처·검증 결과 → UI JSON (docs/api-spec.md)

구현 상태:
- acl.py        extract_principal / build_acl_filter / @enforce_acl [feature7]
"""

from app.query.acl import (
    ACLViolationError,
    Principal,
    PrincipalExtractionError,
    build_acl_filter,
    enforce_acl,
    extract_principal,
)

__all__ = [
    "ACLViolationError",
    "Principal",
    "PrincipalExtractionError",
    "build_acl_filter",
    "enforce_acl",
    "extract_principal",
]
