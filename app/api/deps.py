"""FastAPI 의존성 부트스트랩 — Query 그래프 의존성 구성 헬퍼 [Pipeline].

--------------------------------------------------
작성자 : 최태성
작성목적 : feature11 통합 Phase 2 — FastAPI 앱이 시작할 때 한 번 호출되어 Query
          그래프 의존성(``QueryGraphDeps``)을 부트스트랩한다. PoC 기본은 :memory:
          Qdrant + Fake embedder/reranker + samples 자동 인덱싱으로 외부 컨테이너·
          모델 없이 서버가 즉시 응답 가능하도록 한다. 실 어댑터(E5 +
          Qdrant from_settings + Cross-Encoder 실 모델) 부트스트랩은 별도 follow-up
          (운영 전환 시 본 모듈에 ``build_real_deps``를 추가하고 환경 토글로 선택).
작성일 : 2026-05-18
변경사항 내역 (날짜, 변경목적, 변경내용 순)
  - 2026-05-18, 최초 작성, feature11 통합 Phase 2 — build_poc_deps + samples
    자동 인덱싱
--------------------------------------------------
[호환성]
  - Python 3.11.x, FastAPI 0.111+
  - NOTE: 본 모듈은 외부 의존성(qdrant-client `:memory:`)을 사용하지만 모델
          다운로드는 없다. FastAPI 의존성 주입 트리는 ``app.state.graph`` /
          ``app.state.deps`` 로 단일 인스턴스를 공유한다 (lifespan).
--------------------------------------------------
"""

from pathlib import Path

from app.adapters.json_fixture import JsonFixtureSourceAdapter
from app.config import Settings, get_settings
from app.ingestion.chunker import chunk_page
from app.ingestion.embedder.base import FakeDenseEmbedder, FakeSparseEmbedder
from app.ingestion.indexer import index_chunks
from app.pipeline.query_graph import QueryGraphDeps
from app.query.reranker.base import FakeCrossEncoderReranker
from app.schemas.chunk import Chunk
from app.storage.mongo_cache import FakeEmbeddingCache
from app.storage.qdrant_client import QdrantPoolStore

# PoC 임베딩 차원 — Fake에서는 코사인 유사도 계산만 정합하면 충분하므로 64로 가볍게.
# 실 어댑터(E5)는 1024차원으로 별도 부트스트랩.
_POC_DENSE_DIMENSION = 64


def build_poc_deps(settings: Settings | None = None) -> QueryGraphDeps:
    """PoC 기본 QueryGraphDeps — :memory: Qdrant + Fake everything + samples 인덱싱.

    1. Fake Dense / Sparse 임베더 인스턴스화 (모델 다운로드 없음).
    2. ``QdrantPoolStore.in_memory`` 로 :memory: 클라이언트 + 3 Pool 컬렉션 부트스트랩.
    3. ``JsonFixtureSourceAdapter`` 로 ``samples/`` PageObject 로드.
    4. ``chunk_page`` 로 본문 청크 생성 (PoC ACL 합성 포함).
    5. ``index_chunks`` 로 3 Pool 모두에 적재 (멱등성 캐시는 Fake).
    6. Agent stub 3종은 ``QueryGraphDeps`` 기본값을 그대로 사용.

    Args:
        settings: 환경 설정. None이면 ``get_settings()`` 로 lazy 로드.

    Returns:
        부트스트랩이 끝난 ``QueryGraphDeps`` — FastAPI lifespan에서 그래프 빌더에 주입.
    """
    settings = settings or get_settings()

    dense = FakeDenseEmbedder(dimension=_POC_DENSE_DIMENSION)
    sparse = FakeSparseEmbedder()
    store = QdrantPoolStore.in_memory(settings, dense_dimension=_POC_DENSE_DIMENSION)
    store.bootstrap_collections()

    # samples 자동 인덱싱 — 외부 데이터·모델 없이 ACL 매칭 검색이 동작하도록.
    _ingest_samples(store=store, dense=dense, sparse=sparse, samples_dir=Path(settings.samples_dir))

    return QueryGraphDeps(
        dense_embedder=dense,
        sparse_embedder=sparse,
        store=store,
        reranker=FakeCrossEncoderReranker(),
    )


def _ingest_samples(
    *,
    store: QdrantPoolStore,
    dense: FakeDenseEmbedder,
    sparse: FakeSparseEmbedder,
    samples_dir: Path,
) -> None:
    """``samples/*.json`` 을 PageObject → Chunk → Qdrant에 적재한다 (멱등)."""
    adapter = JsonFixtureSourceAdapter(samples_dir=samples_dir)
    chunks: list[Chunk] = []
    version_by_page_id: dict[str, int] = {}
    for page in adapter.fetch_pages():
        version_by_page_id[page.page_id] = page.version_number
        chunks.extend(chunk_page(page))

    if not chunks:
        return
    index_chunks(
        chunks,
        version_by_page_id=version_by_page_id,
        dense_embedder=dense,
        sparse_embedder=sparse,
        store=store,
        cache=FakeEmbeddingCache(),
    )
