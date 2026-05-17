"""쿼리 → 샘플 데이터 검색 데모 (PoC, 무거운 의존성 0).

--------------------------------------------------
작성자 : 최태성
작성목적 : feature5-B(실제 임베딩 + Qdrant)·feature9-B(검색 노드 오케스트레이션)가
          오기 전에, 본 담당자가 끝낸 결정론적 부품
          (스키마·청커·임베딩 입력 텍스트·ACL 필터·RRF·Pool 가중·재순위화 선정·포맷터)
          이 실제로 잇혀 동작함을 보이기 위한 인메모리 검색 PoC.
작성일 : 2026-05-17
변경사항 내역 (날짜, 변경목적, 변경내용 순)
  - 2026-05-17, 최초 작성, 코드 리뷰 후속(시연용) — BM25-lite Multi-Pool 검색 데모
--------------------------------------------------
[호환성]
  - Python 3.11.x (백포트 shim 적용 시 3.10도 가능)
  - 의존성: pydantic / pydantic-settings / beautifulsoup4 (이미 ingestion extras)
--------------------------------------------------

데이터 흐름:
    samples/*.json → JsonFixtureSourceAdapter → PageObject (92건)
    → chunk_page → Chunk (289건, doc_type 라벨 휴리스틱)
    → pool_embedding_texts → 세 Pool별 입력 텍스트
    → BM25Lite (외부 의존성 0, 인메모리)
    → 사용자 query → ACL 필터 (build_acl_filter 산출물 + 직접 매칭)
    → Pool별 점수 → 의도별 가중 합산 → Top-K 출처 카드

데모와 실제 RAG 차이 (회사 Mac에서 교체될 부분):
    - BM25Lite → multilingual-e5-large(Dense) + BM25(KoNLPy Mecab, Sparse)
    - 인메모리 인덱스 → Qdrant Multi-Pool Collection
    - 직접 ACL 매칭 → @enforce_acl + Qdrant payload 필터
    - 출처 카드 출력 → 답변 생성기(GPT-4o) + 검증 + 응답 포맷터 → SSE 스트리밍

사용법:
    python -m examples.demo_search "EKS 노드 장애 대응 절차"
    python -m examples.demo_search "Kubernetes Helm 설치" --top-k 3
    python -m examples.demo_search "팀 온보딩" --groups space:ONBOARD
    python -m examples.demo_search "metrics" --intent operation
"""

import argparse
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

from app.adapters import JsonFixtureSourceAdapter
from app.ingestion.chunker import chunk_page
from app.ingestion.embedding import pool_embedding_texts
from app.ingestion.vector_store import CONTENT_POOL, LABEL_POOL, TITLE_POOL
from app.query.acl import build_acl_filter
from app.schemas.chunk import Chunk
from app.schemas.enums import Intent

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SAMPLES_DIR = _REPO_ROOT / "samples"

# CJK 글자 단위 + ASCII 영숫자 토큰 (rag-pipeline-design.md §7 토큰 카운팅과 정합).
_TOKEN = re.compile(r"[A-Za-z0-9_]+|[가-힣ぁ-ヿ一-鿿]")

# 의도별 Pool 가중치 (rag-pipeline-design.md §6 4.5 — 라우터가 정한다고 가정).
_INTENT_POOL_WEIGHTS: dict[str, dict[str, float]] = {
    "incident": {TITLE_POOL: 0.4, CONTENT_POOL: 0.5, LABEL_POOL: 0.1},
    "operation": {TITLE_POOL: 0.2, CONTENT_POOL: 0.7, LABEL_POOL: 0.1},
    "policy": {TITLE_POOL: 0.5, CONTENT_POOL: 0.4, LABEL_POOL: 0.1},
    "history": {TITLE_POOL: 0.3, CONTENT_POOL: 0.3, LABEL_POOL: 0.4},
}

_INTENT_LABEL = {
    "incident": Intent.INCIDENT_RESPONSE,
    "operation": Intent.OPERATION_GUIDE,
    "policy": Intent.POLICY_PROCEDURE,
    "history": Intent.HISTORY_LOOKUP,
}


def _tokenize(text: str) -> list[str]:
    return [token.lower() for token in _TOKEN.findall(text)]


class BM25Lite:
    """단일 컬렉션용 BM25 (k1=1.5, b=0.75, 외부 의존성 0).

    feature5-B에서 KoNLPy Mecab + Qdrant Sparse Vector로 교체된다. 본 클래스는
    Pipeline 부품(스키마·청커·임베딩 입력·ACL·검색 결합 로직)이 실제로 잇혀
    동작함을 보이는 PoC 목적이다.
    """

    K1 = 1.5
    B = 0.75

    def __init__(self) -> None:
        self._doc_freq: dict[str, int] = defaultdict(int)
        self._docs: list[Counter[str]] = []
        self._lengths: list[int] = []

    def add(self, tokens: list[str]) -> None:
        counter = Counter(tokens)
        self._docs.append(counter)
        self._lengths.append(len(tokens))
        for term in counter:
            self._doc_freq[term] += 1

    @property
    def average_length(self) -> float:
        return sum(self._lengths) / len(self._lengths) if self._lengths else 0.0

    def score(self, query_tokens: list[str], doc_index: int) -> float:
        total_docs = len(self._docs)
        if total_docs == 0:
            return 0.0
        doc = self._docs[doc_index]
        doc_length = self._lengths[doc_index]
        avg_length = self.average_length or 1.0
        score = 0.0
        for term in query_tokens:
            term_freq = doc.get(term, 0)
            if not term_freq:
                continue
            doc_freq = self._doc_freq.get(term, 0)
            idf = math.log((total_docs - doc_freq + 0.5) / (doc_freq + 0.5) + 1.0)
            numerator = term_freq * (self.K1 + 1)
            denominator = term_freq + self.K1 * (1 - self.B + self.B * doc_length / avg_length)
            score += idf * (numerator / denominator)
        return score


def _build_pool_indexes(chunks: list[Chunk]) -> dict[str, BM25Lite]:
    """청크 → Pool별 임베딩 입력 텍스트 → Pool별 BM25Lite 인덱스."""
    indexes = {TITLE_POOL: BM25Lite(), CONTENT_POOL: BM25Lite(), LABEL_POOL: BM25Lite()}
    for chunk in chunks:
        texts = pool_embedding_texts(chunk)
        indexes[TITLE_POOL].add(_tokenize(texts[TITLE_POOL]))
        indexes[CONTENT_POOL].add(_tokenize(texts[CONTENT_POOL]))
        indexes[LABEL_POOL].add(_tokenize(texts[LABEL_POOL]))
    return indexes


def _matches_acl(chunk: Chunk, user_id: str, groups: list[str]) -> bool:
    """build_acl_filter와 같은 OR 매칭을 인메모리에서 직접 평가한다.

    실제 운영은 ``@enforce_acl`` 데코레이터를 통과한 Qdrant payload 필터로 적용된다.
    """
    metadata = chunk.metadata
    if any(group in metadata.allowed_groups for group in groups):
        return True
    return user_id in metadata.allowed_users


def _format_source_card(rank: int, chunk: Chunk, score: float) -> str:
    metadata = chunk.metadata
    preview = chunk.text[:140].replace("\n", " ")
    return (
        f"#{rank}  score={score:.3f}  [{metadata.space_key}] {metadata.page_title}\n"
        f"      섹션 : {metadata.section_path}\n"
        f"      미리보기: {preview}...\n"
        f"      출처 : {metadata.webui_link}\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="RAG 검색 데모 (PoC, BM25-lite)")
    parser.add_argument("query", help="검색할 자연어 쿼리")
    parser.add_argument("--user", default="taesung", help="JWT sub (user_id)")
    parser.add_argument(
        "--groups",
        default="space:CLOUD,space:CCC,space:DEVOPS,space:SEC,space:ONBOARD,space:PROJ,space:DATADOG_KR",
        help="콤마 구분 사용자 그룹 (PoC ACL: space:<key>)",
    )
    parser.add_argument(
        "--intent",
        default="operation",
        choices=sorted(_INTENT_POOL_WEIGHTS),
        help="질의 의도 — Pool 가중치 선택",
    )
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()

    groups = [group.strip() for group in args.groups.split(",") if group.strip()]
    pool_weights = _INTENT_POOL_WEIGHTS[args.intent]

    print("=" * 70)
    print("  RAG 검색 데모 (PoC, BM25-lite — 무거운 의존성 0)")
    print("=" * 70)
    print(f"쿼리   : {args.query}")
    print(f"의도   : {_INTENT_LABEL[args.intent]} (Pool 가중치 {pool_weights})")
    print(f"사용자 : {args.user} (groups={groups})")
    print()

    # 1) 데이터 로드 + 청크 분할
    adapter = JsonFixtureSourceAdapter(samples_dir=_SAMPLES_DIR)
    pages = list(adapter.fetch_pages())
    chunks: list[Chunk] = []
    for page in pages:
        chunks.extend(chunk_page(page))
    print(f"[로드] PageObject {len(pages)}건 → Chunk {len(chunks)}건")

    # 2) Multi-Pool 인덱스 구축
    indexes = _build_pool_indexes(chunks)
    print("[인덱스] title_pool / content_pool / label_pool BM25-lite 인메모리")

    # 3) ACL 필터 산출 (시연: build_acl_filter 결과 출력)
    acl_filter = build_acl_filter(args.user, groups)
    print(f"[ACL] build_acl_filter → should={len(acl_filter['should'])} 절 (필수 통과)")

    # 4) 쿼리 점수 산출
    query_tokens = _tokenize(args.query)
    if not query_tokens:
        print("\n[오류] 쿼리에서 토큰을 추출하지 못했습니다.")
        return 1

    scored: list[tuple[int, float]] = []
    for index, chunk in enumerate(chunks):
        if not _matches_acl(chunk, args.user, groups):
            continue
        score = sum(
            pool_weights[pool_name] * indexes[pool_name].score(query_tokens, index)
            for pool_name in indexes
        )
        if score > 0:
            scored.append((index, score))

    scored.sort(key=lambda pair: -pair[1])
    top = scored[: args.top_k]
    print(f"[검색] ACL 매칭 후보 {len(scored)}건 → Top-{len(top)}\n")

    if not top:
        # api-spec.md 표준 분기 응답: RETRIEVAL_EMPTY
        print('"권한 범위 내에서 참고할 수 있는 문서를 찾지 못했습니다."')
        print("(api-spec.md 표준 분기 응답: RETRIEVAL_EMPTY)")
        return 0

    for rank, (chunk_index, score) in enumerate(top, start=1):
        print(_format_source_card(rank, chunks[chunk_index], score))

    print("=" * 70)
    print(
        "  ✓ 검색 동작 확인 — feature5-B(임베딩)/feature9-B(노드)/feature11(API) 도입 시\n"
        "    BM25Lite 자리만 multilingual-e5-large + Qdrant로 교체하면 동일 흐름 유지."
    )
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
