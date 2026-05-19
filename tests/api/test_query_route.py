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


# --- feature14: SSE token streaming (stream=True) 분기 ---


@pytest.mark.asyncio
async def test_query_route_stream_true_falls_back_when_no_generator_provider(
    populated_graph: Any,
) -> None:
    """PoC 안전 fallback — stream=True 라도 deps.generator_provider 없으면 비-streaming.

    `_should_fallback_to_non_streaming` 회귀 — app.state.deps 가 미설정 / generator
    _provider None / settings.openai_api_key 빈 SecretStr 중 하나라도 해당하면
    stream=True 가 무시되고 기존 run_query 흐름으로 5 이벤트 송신.
    """
    body = {"query": "alpha", "jwt": _make_jwt(), "stream": True}
    async with _client(populated_graph) as client:
        resp = await client.post("/api/v1/rag/query", json=body)
    assert resp.status_code == 200
    events = _parse_sse(resp.text)
    # fallback 흐름은 기존 5 이벤트 시퀀스 그대로 — token 1회 + 후행 4종.
    event_names = [name for name, _ in events]
    assert event_names == ["token", "sources", "verification", "meta", "done"]


def _streaming_client(
    populated_graph: Any,
    *,
    monkeypatch: pytest.MonkeyPatch,
    streaming_tokens: list[str],
) -> httpx.AsyncClient:
    """운영 streaming 분기 회귀용 클라이언트.

    app.state 에 streaming_graph / deps / settings 를 수동 채워 lifespan 우회하면서
    stream=True 분기로 진입할 수 있게 한다. ``stream_openai_answer`` 는 monkeypatch
    로 fake token generator 로 대체.
    """
    from types import SimpleNamespace

    from app.api import routes as routes_module
    from app.pipeline.query_graph import build_query_graph_for_streaming

    # populated_graph 자체에는 streaming_graph 가 없으므로 동일 인메모리 deps 로
    # streaming graph 도 컴파일한다. 본 테스트는 token chunk 송신·검증 호출 흐름을
    # 검증하므로 deps 의 generator_provider/config 는 sentinel 로 채워 분기만 활성화.
    settings = Settings(_env_file=None)  # type: ignore[arg-type]
    dense = FakeDenseEmbedder(dimension=8)
    sparse = FakeSparseEmbedder()
    store = QdrantPoolStore.in_memory(settings, dense_dimension=8)
    store.bootstrap_collections()
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
        # generator_provider 가 None 이 아니어야 streaming 분기 활성. 본 fake 는
        # 실제로는 호출되지 않으며 stream_openai_answer monkeypatch 만 사용된다.
        generator_provider=object(),
        generator_config=SimpleNamespace(model="gpt-4o", temperature=0.2, timeout_seconds=45),
    )
    streaming_graph = build_query_graph_for_streaming(deps)

    # streaming OpenAI 호출은 monkeypatch — fake token chunk 를 순차 yield.
    from app.query.openai_streaming import StreamingTokenChunk

    def _fake_stream_openai_answer(**_kwargs: Any) -> Any:
        for token in streaming_tokens:
            yield StreamingTokenChunk(text=token)

    monkeypatch.setattr(routes_module, "stream_openai_answer", _fake_stream_openai_answer)

    # settings.openai_api_key 가 빈 SecretStr 이면 fallback. 채워 둔다.
    from pydantic import SecretStr

    settings_with_key = settings.model_copy(update={"openai_api_key": SecretStr("sk-test")})

    app = create_app()
    # lifespan 우회한 채 app.state 를 수동 채움 — ASGITransport 가 lifespan 을 자동
    # 켜기 때문에 state 가 초기화될 가능성이 있어 dependency_overrides 와 함께 둔다.
    app.state.deps = deps
    app.state.settings = settings_with_key
    app.state.streaming_graph = streaming_graph
    app.state.graph = populated_graph  # stream=False 케이스 호환을 위해.
    app.dependency_overrides[get_graph] = lambda: populated_graph
    transport = ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://testserver")


def _streaming_client_with_stream_callable(
    populated_graph: Any,
    *,
    monkeypatch: pytest.MonkeyPatch,
    stream_callable: Any,
) -> httpx.AsyncClient:
    """feature15 streaming fallback 회귀용 — stream_openai_answer 를 임의 callable 로
    monkeypatch 한 라우트 클라이언트. _streaming_client 와 동일 패턴이지만 호출 측에서
    더 복잡한 분기를 검증할 수 있도록 monkeypatch 값을 외부에서 주입한다.
    """
    from types import SimpleNamespace

    from app.api import routes as routes_module
    from app.pipeline.query_graph import build_query_graph_for_streaming

    settings = Settings(_env_file=None)  # type: ignore[arg-type]
    dense = FakeDenseEmbedder(dimension=8)
    sparse = FakeSparseEmbedder()
    store = QdrantPoolStore.in_memory(settings, dense_dimension=8)
    store.bootstrap_collections()
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
        generator_provider=object(),
        generator_config=SimpleNamespace(
            model="gpt-4o",
            fallback_model="gpt-4o-mini",
            temperature=0.2,
            timeout_seconds=45,
        ),
    )
    streaming_graph = build_query_graph_for_streaming(deps)

    monkeypatch.setattr(routes_module, "stream_openai_answer", stream_callable)

    from pydantic import SecretStr

    settings_with_key = settings.model_copy(update={"openai_api_key": SecretStr("sk-test")})

    app = create_app()
    app.state.deps = deps
    app.state.settings = settings_with_key
    app.state.streaming_graph = streaming_graph
    app.state.graph = populated_graph
    app.dependency_overrides[get_graph] = lambda: populated_graph
    transport = ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://testserver")


@pytest.mark.asyncio
async def test_query_route_stream_true_rate_limit_falls_back_to_fallback_model(
    populated_graph: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """feature15 streaming Rate Limit fallback — 1차 RateLimitError → fallback_model 재시도.

    stream_openai_answer 첫 호출 (primary_model=gpt-4o) 에서 RateLimitError raise,
    두 번째 호출 (fallback_model=gpt-4o-mini) 에서 정상 token chunk yield → 라우트가
    정상 SSE 응답 송신 + meta.used_llm = gpt-4o-mini 노출.
    """
    # openai.RateLimitError 생성 — sentinel response/body 만 채우고 status_code=429.
    from openai import RateLimitError

    from app.query.openai_streaming import StreamingTokenChunk

    # RateLimitError 시그니처 — message + response (httpx.Response) + body. 본 테스트는
    # 메시지·status_code 만 검증하므로 minimal Response 객체로 인스턴스화.
    fake_response = httpx.Response(429, request=httpx.Request("POST", "https://api.openai.com"))
    rate_limit_error = RateLimitError(
        message="rate limit exceeded", response=fake_response, body=None
    )

    call_count = {"n": 0}

    def _stream_with_rate_limit_then_success(**kwargs: Any) -> Any:
        call_count["n"] += 1
        if call_count["n"] == 1:
            assert kwargs["model"] == "gpt-4o"

            # primary_model 호출 — 토큰 1개 yield 후 raise (UI 가 부분 답변 송신을
            # 받았다가 빈 token 으로 clear 되는 흐름까지 검증).
            def _gen() -> Any:
                yield StreamingTokenChunk(text="(부분)")
                raise rate_limit_error

            return _gen()
        # fallback_model 호출 — 정상 token yield.
        assert kwargs["model"] == "gpt-4o-mini"

        def _gen_fb() -> Any:
            yield StreamingTokenChunk(text="정상")
            yield StreamingTokenChunk(text="[#1]")

        return _gen_fb()

    client = _streaming_client_with_stream_callable(
        populated_graph,
        monkeypatch=monkeypatch,
        stream_callable=_stream_with_rate_limit_then_success,
    )
    body = {"query": "alpha", "jwt": _make_jwt(), "stream": True}
    async with client as c:
        resp = await c.post("/api/v1/rag/query", json=body)
    assert resp.status_code == 200

    events = _parse_sse(resp.text)
    # stream_openai_answer 가 정확히 2회 호출됐다 — primary 1회 + fallback 1회.
    assert call_count["n"] == 2
    token_payloads = [data for name, data in events if name == "token"]
    # (부분) + (빈 clear) + 정상 + [#1] = 4 회 token (또는 차단 분기 추가 1회). 최소 3회.
    assert len(token_payloads) >= 3
    # 빈 clear token 이 송신됐다 — UI 가 부분 답변을 덮어쓸 수 있도록.
    assert "" in token_payloads
    # meta.used_llm 이 fallback_model (gpt-4o-mini) 로 노출 — 다운그레이드 인지.
    meta = json.loads(dict(events)["meta"])
    assert meta["used_llm"] == "gpt-4o-mini"


@pytest.mark.asyncio
async def test_query_route_stream_true_emits_multiple_token_chunks(
    populated_graph: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """운영 streaming — token chunk 가 다중 송신되고 후행 4 이벤트 시퀀스 정합.

    NOTE: ``_parse_sse`` 가 ``data:`` 라인을 ``.strip()`` 으로 정규화하므로 본 회귀
    에서는 trailing/leading 공백 없는 토큰을 사용해 단언 정합화한다 (SSE 공백 보존
    여부는 본 회귀 범위 외).
    """
    streaming_tokens = ["답변", "시작", "[#1]"]
    client = _streaming_client(
        populated_graph,
        monkeypatch=monkeypatch,
        streaming_tokens=streaming_tokens,
    )
    body = {"query": "alpha", "jwt": _make_jwt(), "stream": True}
    async with client as c:
        resp = await c.post("/api/v1/rag/query", json=body)
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")

    events = _parse_sse(resp.text)
    # token 이벤트는 streaming_tokens 갯수 이상 (검증 차단 분기에서 1회 더 송신 가능).
    token_count = sum(1 for name, _ in events if name == "token")
    assert token_count >= len(streaming_tokens)
    # token 데이터 누적은 streaming_tokens 의 순서를 보존한다.
    token_payloads = [data for name, data in events if name == "token"]
    assert token_payloads[: len(streaming_tokens)] == streaming_tokens
    # 후행 이벤트 시퀀스 정합 — sources / verification / meta / done.
    trailing_names = [name for name, _ in events if name != "token"]
    assert trailing_names == ["sources", "verification", "meta", "done"]
    # meta payload — used_llm 이 generator_config.model 정합 (gpt-4o → GPT_4O).
    meta = json.loads(dict(events)["meta"])
    assert meta["used_llm"] == "gpt-4o"
