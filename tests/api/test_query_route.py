"""POST /api/v1/rag/query — httpx ASGITransport 통합 테스트.

본 테스트는 FastAPI 라우트가 (1) SSE 이벤트 5종 시퀀스를 정확히 송신하고, (2) JWT
추출 실패 / 표준 분기 응답 / 예외 매핑을 api-spec.md 정합으로 처리하는지를 in-process
httpx 클라이언트로 검증한다. 외부 컨테이너·모델 없이 동작 — :memory: Qdrant + Fake
everything + samples 자동 인덱싱 기본값을 활용한다.
"""

import base64
import json
import warnings
from datetime import datetime
from typing import Any

import httpx
import pytest
from httpx import ASGITransport

from app.api.main import create_app
from app.api.routes import get_graph
from app.config import Settings
from app.ingestion.embedder.base import FakeDenseEmbedder, FakeSparseEmbedder
from app.ingestion.indexer import index_chunks
from app.pipeline.query_graph import QueryGraphDeps, build_query_graph
from app.query.reranker.base import FakeCrossEncoderReranker
from app.schemas.chunk import Chunk, ChunkMetadata
from app.schemas.enums import SourceType
from app.storage.mongo_cache import FakeEmbeddingCache
from app.storage.qdrant_client import QdrantPoolStore

warnings.filterwarnings("ignore", message="Payload indexes have no effect.*")


# --- JWT 헬퍼 (서명 미검증 — 본 파이프라인은 클레임 추출만 한다) ---


def _make_jwt(sub: str = "taesung", groups: list[str] | None = None) -> str:
    """base64url JWT 페이로드만 채운 stub. 서명은 BFF 책임이므로 임의 문자열로 둔다."""
    header = base64.urlsafe_b64encode(b'{"alg":"none"}').rstrip(b"=").decode("ascii")
    payload_dict = {"sub": sub, "groups": groups or ["space:CLOUD"]}
    payload = (
        base64.urlsafe_b64encode(json.dumps(payload_dict).encode("utf-8"))
        .rstrip(b"=")
        .decode("ascii")
    )
    return f"{header}.{payload}.signature"


# --- 테스트용 그래프 픽스처 (lifespan 우회 + 작은 인메모리 데이터) ---


def _chunk(*, chunk_id: str, text: str = "alpha bravo charlie") -> Chunk:
    metadata = ChunkMetadata(
        chunk_id=chunk_id,
        page_id="P1",
        page_title="EKS 운영 가이드",
        section_header="개요",
        section_path="Cloud 운영 문서 > 개요",
        chunk_index=0,
        labels=["eks"],
        doc_type="operation",
        space_key="CLOUD",
        allowed_groups=["space:CLOUD"],
        allowed_users=[],
        webui_link="/display/CLOUD/eks",
        last_modified=datetime.fromisoformat("2026-04-22T08:15:00+09:00"),
        source_type=SourceType.PAGE,
        token_count=120,
    )
    return Chunk(text=text, metadata=metadata)


def _build_test_graph(*, indexed: bool = True) -> Any:
    """`:memory:` Qdrant + Fake everything 으로 컴파일된 테스트용 그래프를 만든다."""
    settings = Settings(_env_file=None)
    dense = FakeDenseEmbedder(dimension=8)
    sparse = FakeSparseEmbedder()
    store = QdrantPoolStore.in_memory(settings, dense_dimension=8)
    store.bootstrap_collections()
    if indexed:
        index_chunks(
            [
                _chunk(chunk_id="a" * 40, text="alpha bravo charlie"),
                _chunk(chunk_id="b" * 40, text="bravo delta echo"),
            ],
            version_by_page_id={"P1": 1},
            dense_embedder=dense,
            sparse_embedder=sparse,
            store=store,
            cache=FakeEmbeddingCache(),
        )
    deps = QueryGraphDeps(
        dense_embedder=dense,
        sparse_embedder=sparse,
        store=store,
        reranker=FakeCrossEncoderReranker(),
    )
    return build_query_graph(deps)


@pytest.fixture()
def populated_graph() -> Any:
    return _build_test_graph(indexed=True)


@pytest.fixture()
def empty_graph() -> Any:
    return _build_test_graph(indexed=False)


def _client(graph: Any) -> httpx.AsyncClient:
    """lifespan을 우회한 ASGITransport 클라이언트.

    lifespan을 끄려면 ``transport`` 의 ``lifespan="off"`` 옵션을 활용한다.
    그래프는 dependency override로 직접 주입.
    """
    app = create_app()
    app.dependency_overrides[get_graph] = lambda: graph
    transport = ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://testserver")


# --- 헬스 ---


@pytest.mark.asyncio
async def test_healthz_returns_ok(populated_graph: Any) -> None:
    async with _client(populated_graph) as client:
        resp = await client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


# --- 정상 흐름 ---


def _parse_sse(body: str) -> list[tuple[str, str]]:
    """SSE 본문에서 (event, data) 튜플 시퀀스를 추출한다."""
    events: list[tuple[str, str]] = []
    current_event: str | None = None
    current_data: list[str] = []
    for line in body.splitlines():
        if line.startswith("event:"):
            current_event = line[len("event:") :].strip()
        elif line.startswith("data:"):
            current_data.append(line[len("data:") :].strip())
        elif line.strip() == "" and current_event is not None:
            events.append((current_event, "\n".join(current_data)))
            current_event = None
            current_data = []
    if current_event is not None:
        events.append((current_event, "\n".join(current_data)))
    return events


@pytest.mark.asyncio
async def test_query_route_emits_full_sse_sequence(populated_graph: Any) -> None:
    """정상 흐름: token → sources → verification → meta → done 5개 이벤트 시퀀스."""
    body = {"query": "alpha", "jwt": _make_jwt()}
    async with _client(populated_graph) as client:
        resp = await client.post("/api/v1/rag/query", json=body)
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")

    events = _parse_sse(resp.text)
    event_names = [name for name, _ in events]
    assert event_names == ["token", "sources", "verification", "meta", "done"]

    # sources 페이로드는 JSON 배열 — api-spec.md 정합.
    sources = json.loads(dict(events)["sources"])
    assert isinstance(sources, list)
    assert all(0 <= source["score"] <= 100 for source in sources)

    # meta 페이로드 — intent / used_llm / feedback_enabled / latency_ms.
    meta = json.loads(dict(events)["meta"])
    assert meta["intent"] == "운영가이드"
    assert meta["used_llm"] == "gpt-4o"
    assert isinstance(meta["feedback_enabled"], bool)
    assert meta["latency_ms"] >= 0


# --- RETRIEVAL_EMPTY 표준 분기 ---


@pytest.mark.asyncio
async def test_query_route_retrieval_empty_returns_standard_message(
    empty_graph: Any,
) -> None:
    """청크 0건이면 200 SSE 정상 응답으로 표준 메시지를 송신한다 (api-spec.md 분기)."""
    body = {"query": "anything", "jwt": _make_jwt()}
    async with _client(empty_graph) as client:
        resp = await client.post("/api/v1/rag/query", json=body)
    assert resp.status_code == 200
    events = dict(_parse_sse(resp.text))
    assert "권한 범위" in events["token"]
    assert json.loads(events["sources"]) == []
    meta = json.loads(events["meta"])
    assert meta["feedback_enabled"] is False


# --- UNAUTHORIZED (JWT 추출 실패) ---


@pytest.mark.asyncio
async def test_query_route_invalid_jwt_returns_401(populated_graph: Any) -> None:
    """JWT 형식이 깨지면 401 UNAUTHORIZED Error Response (api-spec.md)."""
    body = {"query": "q", "jwt": "not-a-jwt"}
    async with _client(populated_graph) as client:
        resp = await client.post("/api/v1/rag/query", json=body)
    assert resp.status_code == 401
    payload = resp.json()
    assert payload["success"] is False
    assert payload["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_query_route_missing_sub_returns_401(populated_graph: Any) -> None:
    """sub 클레임이 없으면 401 UNAUTHORIZED."""
    header = base64.urlsafe_b64encode(b'{"alg":"none"}').rstrip(b"=").decode("ascii")
    payload_b = base64.urlsafe_b64encode(b'{"groups":["space:CLOUD"]}').rstrip(b"=").decode("ascii")
    jwt = f"{header}.{payload_b}.sig"
    body = {"query": "q", "jwt": jwt}
    async with _client(populated_graph) as client:
        resp = await client.post("/api/v1/rag/query", json=body)
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "UNAUTHORIZED"


# --- 요청 본문 검증 ---


@pytest.mark.asyncio
async def test_query_route_missing_required_fields_returns_422(
    populated_graph: Any,
) -> None:
    """query 필드 누락 → FastAPI 기본 422 (Pydantic 검증)."""
    async with _client(populated_graph) as client:
        resp = await client.post("/api/v1/rag/query", json={"jwt": _make_jwt()})
    assert resp.status_code == 422


# --- ACL 매칭 0건 → RETRIEVAL_EMPTY ---


@pytest.mark.asyncio
async def test_query_route_acl_mismatch_yields_empty_retrieval(
    populated_graph: Any,
) -> None:
    """JWT groups가 인덱싱된 청크의 allowed_groups와 일치하지 않으면 표준 메시지."""
    body = {"query": "alpha", "jwt": _make_jwt(groups=["space:OTHER"])}
    async with _client(populated_graph) as client:
        resp = await client.post("/api/v1/rag/query", json=body)
    assert resp.status_code == 200
    events = dict(_parse_sse(resp.text))
    assert "권한 범위" in events["token"]
    assert json.loads(events["sources"]) == []
