"""애플리케이션 환경 설정.

--------------------------------------------------
작성자 : 최태성
작성목적 : 데이터 공급원·Qdrant·MongoDB·MySQL·OpenAI·모델명 등 환경 의존 설정을
          환경 변수(RAG_ 프리픽스) 또는 .env 파일에서 주입받는다. 시크릿은
          코드에 포함하지 않는다 (루트 CLAUDE.md 절대 규칙).
작성일 : 2026-05-15
변경사항 내역 (날짜, 변경목적, 변경내용 순)
  - 2026-05-15, 최초 작성, feature1 — pydantic-settings 기반 Settings 정의
  - 2026-05-17, 코드 리뷰 후속(P1-1) — samples_dir이 어댑터에 흐르도록 정리,
    mysql_uri는 운영 전환 시 SecretStr 승급 후보 NOTE 명시
  - 2026-05-18, build_real_deps 후속 — use_real_adapters 토글 추가
    (RAG_USE_REAL_ADAPTERS). 기본값 False(PoC). True 시 lifespan이 build_real_deps
    분기로 E5 + BM25 + Qdrant from_settings + CrossEncoderRerankerImpl을 부트스트랩
--------------------------------------------------
[호환성]
  - Python 3.11.x, Pydantic 2.7+, pydantic-settings 2.3+
--------------------------------------------------
"""

from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """환경 변수 기반 설정. 모든 항목은 기본값을 가지므로 무인자 인스턴스화가 가능하다."""

    model_config = SettingsConfigDict(
        env_prefix="RAG_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- 데이터 공급원 (docs/atlassian-api.md) ---
    source_type: str = "json_fixture"  # json_fixture | atlassian
    samples_dir: str = "samples"
    # NOTE: access_token / cloudid 전달 경로는 미정(TBD) — docs/ai/current-plan.md 참조
    atlassian_api_base_url: str = "https://api.atlassian.com"

    # --- Qdrant Multi-Pool Vector Store ---
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_title_pool: str = "title_pool"
    qdrant_content_pool: str = "content_pool"
    qdrant_label_pool: str = "label_pool"

    # --- MongoDB (ingestion_jobs / embedding_cache) ---
    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db: str = "lina_rag"

    # --- MySQL (space_doc_type_cache) ---
    # NOTE(P2): 운영 전환 시 비밀번호 포함 DSN이 들어오면 SecretStr로 승급해야 한다.
    # PoC는 localhost·비밀번호 없는 DSN만 사용하므로 평문 문자열을 유지한다.
    mysql_uri: str = "mysql+pymysql://localhost:3306/lina_rag"

    # --- OpenAI ---
    openai_api_key: SecretStr = SecretStr("")
    llm_answer_model: str = "gpt-4o"
    llm_aux_model: str = "gpt-4o-mini"

    # --- 임베딩 / 재순위화 모델 ---
    dense_embedding_model: str = "intfloat/multilingual-e5-large"
    cross_encoder_model: str = "cross-encoder/ms-marco-MiniLM-L-12"

    # --- 운영 어댑터 토글 (build_real_deps 후속, 2026-05-18) ---
    # True면 lifespan이 build_real_deps 분기로 E5 + BM25 + Qdrant from_settings +
    # CrossEncoderRerankerImpl 부트스트랩. False(기본)는 build_poc_deps 분기로
    # :memory: Qdrant + Fake everything + samples 자동 인덱싱. 운영 모드는 모델
    # 다운로드(약 2.4 GB)와 Qdrant 서버 접속을 요구하므로 명시 활성화한다.
    use_real_adapters: bool = False


@lru_cache
def get_settings() -> Settings:
    """프로세스 단일 Settings 인스턴스를 반환한다."""
    return Settings()
