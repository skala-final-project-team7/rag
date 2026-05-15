"""애플리케이션 환경 설정.

--------------------------------------------------
작성자 : 최태성
작성목적 : 데이터 공급원·Qdrant·MongoDB·MySQL·OpenAI·모델명 등 환경 의존 설정을
          환경 변수(RAG_ 프리픽스) 또는 .env 파일에서 주입받는다. 시크릿은
          코드에 포함하지 않는다 (루트 CLAUDE.md 절대 규칙).
작성일 : 2026-05-15
변경사항 내역 (날짜, 변경목적, 변경내용 순)
  - 2026-05-15, 최초 작성, feature1 — pydantic-settings 기반 Settings 정의
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
    mysql_uri: str = "mysql+pymysql://localhost:3306/lina_rag"

    # --- OpenAI ---
    openai_api_key: SecretStr = SecretStr("")
    llm_answer_model: str = "gpt-4o"
    llm_aux_model: str = "gpt-4o-mini"

    # --- 임베딩 / 재순위화 모델 ---
    dense_embedding_model: str = "intfloat/multilingual-e5-large"
    cross_encoder_model: str = "cross-encoder/ms-marco-MiniLM-L-12"


@lru_cache
def get_settings() -> Settings:
    """프로세스 단일 Settings 인스턴스를 반환한다."""
    return Settings()
