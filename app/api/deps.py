"""FastAPI 의존성 부트스트랩 — Query 그래프 의존성 구성 헬퍼 [Pipeline].

--------------------------------------------------
작성자 : 최태성
작성목적 : FastAPI 앱이 시작할 때 한 번 호출되어 Query 그래프 의존성
          (``QueryGraphDeps``)을 부트스트랩한다. PoC 기본(``build_poc_deps``)은
          :memory: Qdrant + Fake embedder/reranker + samples 자동 인덱싱으로 외부
          컨테이너·모델 없이 서버가 즉시 응답 가능하도록 한다. 운영 모드
          (``build_real_deps``)는 E5DenseEmbedder + BM25SparseEmbedder + Qdrant
          from_settings + CrossEncoderRerankerImpl로 실 어댑터를 부트스트랩한다.
          분기는 ``Settings.use_real_adapters`` 토글(``RAG_USE_REAL_ADAPTERS=true``)
          이 결정한다.
작성일 : 2026-05-18
변경사항 내역 (날짜, 변경목적, 변경내용 순)
  - 2026-05-18, 최초 작성, feature11 통합 Phase 2 — build_poc_deps + samples
    자동 인덱싱
  - 2026-05-18, build_real_deps 후속 — 운영 어댑터 부트스트랩 함수 추가
    (E5 / BM25 / Qdrant from_settings / CrossEncoderRerankerImpl). 실 모델
    import는 함수 본문 내 lazy로 처리해 embedding extra 미설치 환경에서도
    PoC 경로(build_poc_deps)와 모듈 import는 동작하도록 한다.
  - 2026-05-18, 풀 텍스트 lookup 후속 — chunk_lookup 어댑터 wiring 추가. PoC는
    빈 FakeChunkTextLookup(QueryGraphDeps 기본값), 운영은 MongoChunkTextLookup
    .from_settings로 chunk_lookup 컬렉션(db-schema §2.5)을 가리키도록 한다.
  - 2026-05-18, 풀 텍스트 lookup Phase 2 — build_poc_deps 가 FakeChunkTextLookup
    1 인스턴스를 _ingest_samples 와 QueryGraphDeps 양쪽에 공유 주입. samples
    인덱싱 시점에 attachment_download_urls 매핑을 page.attachments 에서 합성해
    indexer 에 전달, 첨부 청크의 Source.download_url 이 검색 시점에 채워지도록 한다.
--------------------------------------------------
[호환성]
  - Python 3.11.x, FastAPI 0.111+
  - NOTE: 본 모듈 최상단 import는 외부 의존성(qdrant-client `:memory:`)만 사용한다.
          sentence-transformers / fastembed는 build_real_deps 호출 시점에 lazy
          import되며, embedding extra 미설치 환경에서는 build_real_deps 호출 시
          ImportError로 빨리 실패한다.
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
from app.storage.chunk_lookup import FakeChunkTextLookup
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
    # chunk_lookup은 _ingest_samples 와 QueryGraphDeps 양쪽에 1 인스턴스 공유 — 인덱싱
    # 시 적재한 풀 텍스트·첨부 download_url 을 검색 시 rerank 노드가 그대로 조회한다.
    chunk_lookup = FakeChunkTextLookup()
    _ingest_samples(
        store=store,
        dense=dense,
        sparse=sparse,
        samples_dir=Path(settings.samples_dir),
        chunk_lookup=chunk_lookup,
    )

    return QueryGraphDeps(
        dense_embedder=dense,
        sparse_embedder=sparse,
        store=store,
        reranker=FakeCrossEncoderReranker(),
        chunk_lookup=chunk_lookup,
    )


def build_real_deps(settings: Settings | None = None) -> QueryGraphDeps:
    """운영 어댑터 부트스트랩 — E5 + BM25 + Qdrant from_settings + CrossEncoder.

    PoC 부트스트랩(``build_poc_deps``)과 동일한 ``QueryGraphDeps`` 시그니처를 반환
    한다. 실 모델 import는 함수 본문 내 lazy — embedding extra 미설치 환경에서도
    PoC 경로와 모듈 import는 영향 받지 않는다. 운영 모드는 모델 다운로드(약
    2.4 GB: e5-large 2.24 GB + cross-encoder 130 MB) + Qdrant 서버 접속을 요구
    하므로 ``RAG_USE_REAL_ADAPTERS=true`` 환경 변수로 명시 활성화 후 사용한다.

    samples 자동 인덱싱은 수행하지 않는다 — 운영 환경은 별도 ingestion 파이프라인이
    Qdrant에 적재했다고 가정한다. 컬렉션이 비어 있으면 검색 0건으로 떨어져 그래프
    의 ``empty_retrieval_node`` 가 표준 RETRIEVAL_EMPTY 응답을 반환한다.

    Args:
        settings: 환경 설정. None이면 ``get_settings()`` 로 lazy 로드.

    Returns:
        실 어댑터 4종이 wiring된 ``QueryGraphDeps``.

    Raises:
        ImportError: sentence-transformers / fastembed 미설치 시 (embedding extra
            누락). 운영 모드 활성화 전 ``pip install -e .[embedding]`` 필요.
    """
    settings = settings or get_settings()

    # 실 어댑터 import는 lazy — embedding extra 미설치 환경에서도 build_poc_deps와
    # 본 모듈 import는 동작해야 한다. import 실패 시 호출자에게 ImportError 전파.
    from app.ingestion.embedder.dense import E5DenseEmbedder
    from app.ingestion.embedder.sparse import BM25SparseEmbedder
    from app.query.reranker.cross_encoder import CrossEncoderRerankerImpl
    from app.storage.chunk_lookup import MongoChunkTextLookup

    dense = E5DenseEmbedder(settings.dense_embedding_model)
    sparse = BM25SparseEmbedder()
    # dense_dimension은 어댑터가 모델 로드 후 보고한 값을 사용 (E5-large = 1024).
    store = QdrantPoolStore.from_settings(settings, dense_dimension=dense.dimension)
    store.bootstrap_collections()
    reranker = CrossEncoderRerankerImpl(settings.cross_encoder_model)
    # chunk_lookup은 운영 모드에서 MongoDB `chunk_lookup` 컬렉션을 가리킨다 (db-schema §2.5).
    # 컬렉션이 비어 있어도 fetch가 None을 반환하므로 download_url=None으로 안전 fallback.
    chunk_lookup = MongoChunkTextLookup.from_settings(settings)

    return QueryGraphDeps(
        dense_embedder=dense,
        sparse_embedder=sparse,
        store=store,
        reranker=reranker,
        chunk_lookup=chunk_lookup,
    )


def _ingest_samples(
    *,
    store: QdrantPoolStore,
    dense: FakeDenseEmbedder,
    sparse: FakeSparseEmbedder,
    samples_dir: Path,
    chunk_lookup: FakeChunkTextLookup,
) -> None:
    """``samples/*.json`` 을 PageObject → Chunk → Qdrant + chunk_lookup 에 적재한다 (멱등).

    PoC 픽스처(`JsonFixtureSourceAdapter`)는 page.attachments[*].download_url 을 file://
    URI로 채워둔다. 이 매핑을 indexer 에 전달해 첨부 청크의 chunk_lookup 적재 시점에
    Source.download_url 이 함께 채워지도록 한다.
    """
    adapter = JsonFixtureSourceAdapter(samples_dir=samples_dir)
    chunks: list[Chunk] = []
    version_by_page_id: dict[str, int] = {}
    attachment_download_urls: dict[str, str] = {}
    for page in adapter.fetch_pages():
        version_by_page_id[page.page_id] = page.version_number
        for attachment in page.attachments:
            attachment_download_urls[attachment.attachment_id] = attachment.download_url
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
        chunk_lookup=chunk_lookup,
        attachment_download_urls=attachment_download_urls,
    )
