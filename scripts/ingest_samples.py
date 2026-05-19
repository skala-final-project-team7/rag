"""samples/*.json → 운영 Qdrant 1회 적재 CLI [Pipeline 데모 도구].

--------------------------------------------------
작성자 : 최태성
작성목적 : Mode B 시연을 위한 1회용 CLI. ``build_real_deps`` 는 query path 만
          wiring 하고 samples 자동 인덱싱은 수행하지 않으므로 (운영은 별도 ingestion
          파이프라인이 적재 가정), 시연 환경에서는 본 스크립트로 samples 데이터를
          운영 Qdrant 에 한 번 적재한다. PoC ``_ingest_samples`` 와 동일 흐름을
          운영 E5 / BM25 / Qdrant.from_settings 어댑터에 적용한다.
작성일 : 2026-05-19
변경사항 내역 (날짜, 변경목적, 변경내용 순)
  - 2026-05-19, 최초 작성, Mode B 시연용 1회 적재 CLI.
--------------------------------------------------
[호환성]
  - Python 3.11.x, embedding extras 필수 (sentence-transformers + fastembed).
  - 사용법:
        cd ~/skala-final/rag
        source .venv/bin/activate
        docker compose up -d qdrant        # Qdrant 컨테이너 (docker-compose.yml)
        python scripts/ingest_samples.py   # samples → 운영 Qdrant 적재
        # 그 후 RAG_USE_REAL_ADAPTERS=true uvicorn app.api.main:app --port 8000
  - NOTE: 본 스크립트는 운영 ingestion 파이프라인 대체가 아니다. 시연/평가용
          1회 적재만 수행하며, 실 운영은 RabbitMQ Worker / data-ingestion-agent
          별도 진입점이 담당한다 (설계서 §6).
--------------------------------------------------
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="samples/*.json 을 운영 Qdrant 에 적재한다 (Mode B 시연용).",
    )
    parser.add_argument(
        "--samples-dir",
        type=Path,
        default=None,
        help="samples 디렉토리. 기본값은 settings.samples_dir (보통 'samples').",
    )
    parser.add_argument(
        "--use-mongo-cache",
        action="store_true",
        help="MongoEmbeddingCache / MongoChunkTextLookup 사용 (docker compose 의 mongo 필요).",
    )
    args = parser.parse_args()

    # lazy import — embedding extras 미설치 환경에서 도움말 출력은 가능하게.
    from app.adapters.json_fixture import JsonFixtureSourceAdapter
    from app.config import get_settings
    from app.ingestion.chunker import chunk_page
    from app.ingestion.embedder.dense import E5DenseEmbedder
    from app.ingestion.embedder.sparse import BM25SparseEmbedder
    from app.ingestion.indexer import index_chunks
    from app.schemas.chunk import Chunk
    from app.storage.chunk_lookup import FakeChunkTextLookup
    from app.storage.mongo_cache import FakeEmbeddingCache
    from app.storage.qdrant_client import QdrantPoolStore

    settings = get_settings()
    samples_dir = args.samples_dir or Path(settings.samples_dir)

    print(f"[ingest] samples_dir = {samples_dir.resolve()}")
    print(f"[ingest] qdrant = {settings.qdrant_host}:{settings.qdrant_port}")
    print(f"[ingest] dense model = {settings.dense_embedding_model}")
    print("[ingest] 모델 다운로드 (최초 1회) 및 Qdrant 컬렉션 부트스트랩 중...")

    dense = E5DenseEmbedder(settings.dense_embedding_model)
    sparse = BM25SparseEmbedder()
    store = QdrantPoolStore.from_settings(settings, dense_dimension=dense.dimension)
    store.bootstrap_collections()
    print(f"[ingest] dense_dimension = {dense.dimension}")

    if args.use_mongo_cache:
        from app.storage.chunk_lookup import MongoChunkTextLookup
        from app.storage.mongo_cache import MongoEmbeddingCache

        cache = MongoEmbeddingCache.from_settings(settings)
        chunk_lookup = MongoChunkTextLookup.from_settings(settings)
        print("[ingest] MongoDB cache + chunk_lookup 사용 (docker compose mongo 필요)")
    else:
        cache = FakeEmbeddingCache()
        chunk_lookup = FakeChunkTextLookup()
        print("[ingest] Fake cache + chunk_lookup 사용 (Qdrant 외 의존성 0)")

    adapter = JsonFixtureSourceAdapter(samples_dir=samples_dir)
    chunks: list[Chunk] = []
    version_by_page_id: dict[str, int] = {}
    attachment_download_urls: dict[str, str] = {}
    page_count = 0
    for page in adapter.fetch_pages():
        page_count += 1
        version_by_page_id[page.page_id] = page.version_number
        for attachment in page.attachments:
            attachment_download_urls[attachment.attachment_id] = attachment.download_url
        chunks.extend(chunk_page(page))

    print(f"[ingest] PageObject {page_count}건 → Chunk {len(chunks)}건 생성")

    if not chunks:
        print("[ingest] 적재할 청크가 없습니다. samples_dir 확인 필요.")
        return 1

    print("[ingest] Dense + Sparse 임베딩 + Qdrant upsert 진행 중... (수십 초 소요)")
    index_chunks(
        chunks,
        version_by_page_id=version_by_page_id,
        dense_embedder=dense,
        sparse_embedder=sparse,
        store=store,
        cache=cache,
        chunk_lookup=chunk_lookup,
        attachment_download_urls=attachment_download_urls,
    )
    print(f"[ingest] 완료 — Qdrant 3 Pool 에 {len(chunks)}건 적재")
    print("[ingest] 이제 RAG_USE_REAL_ADAPTERS=true uvicorn 으로 시연 가능합니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
