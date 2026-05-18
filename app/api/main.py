"""FastAPI 앱 entrypoint — lifespan에서 Query 그래프 컴파일 [Pipeline].

--------------------------------------------------
작성자 : 최태성
작성목적 : feature11 통합 Phase 2 — FastAPI 애플리케이션의 진입점. lifespan에서
          ``build_poc_deps`` (또는 후속 ``build_real_deps``)를 호출해 Query 그래프
          의존성을 부트스트랩하고, ``build_query_graph`` 로 컴파일한 그래프를
          ``app.state.graph`` 에 저장한다. 라우트는 ``app.api.routes`` 의 라우터를
          마운트한다. CORS·인증 미들웨어는 BFF가 담당하므로 본 앱은 추가하지
          않는다 (docs/api-spec.md NOTE).
작성일 : 2026-05-18
변경사항 내역 (날짜, 변경목적, 변경내용 순)
  - 2026-05-18, 최초 작성, feature11 통합 Phase 2 — create_app + lifespan +
    헬스 라우트(/healthz)
--------------------------------------------------
[호환성]
  - Python 3.11.x, FastAPI 0.111+
  - 실행 예시: ``uvicorn app.api.main:app --host 0.0.0.0 --port 8000``
--------------------------------------------------
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.deps import build_poc_deps
from app.api.routes import router as query_router
from app.pipeline.query_graph import QueryGraphDeps, build_query_graph


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    """앱 시작 시 PoC deps + 그래프 컴파일을 한 번 수행해 app.state에 보관한다.

    NOTE: 운영 어댑터(E5 / Qdrant from_settings / Cross-Encoder 실 모델) 부트스트랩은
    별도 follow-up(``build_real_deps``)으로 분리한다. 본 lifespan은 PoC 기본
    (:memory: Qdrant + Fake everything + samples 자동 인덱싱)만 수행해 외부 컨테이너·
    모델 다운로드 없이 서버가 즉시 응답 가능하도록 한다.
    """
    deps: QueryGraphDeps = build_poc_deps()
    app.state.deps = deps
    app.state.graph = build_query_graph(deps)
    try:
        yield
    finally:
        # Qdrant `:memory:` 클라이언트는 GC에 맡긴다 — 명시 close 없음.
        app.state.graph = None
        app.state.deps = None


def create_app() -> FastAPI:
    """FastAPI 앱 인스턴스를 생성한다 — 운영·테스트 공통 팩토리.

    테스트는 ``create_app()`` 후 ``app.dependency_overrides`` 로 그래프 의존성을
    교체하거나, lifespan을 건너뛰고 ``app.state.graph`` 를 수동 설정한다.
    """
    app = FastAPI(
        title="LINA RAG Pipeline",
        version="0.1.0",
        description="척척학사(LINA) Confluence 기반 RAG 챗봇 서비스의 RAG 파이프라인",
        lifespan=_lifespan,
    )
    app.include_router(query_router)

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        """기본 헬스 체크 — Kubernetes readiness probe 대상."""
        return {"status": "ok"}

    return app


# uvicorn 진입점 (``uvicorn app.api.main:app``).
app = create_app()
