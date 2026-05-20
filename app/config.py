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
  - 2026-05-19, feature12 — cross_encoder_model 기본값에 ``-v2`` 추가.
    Hugging Face / sentence-transformers 의 실 모델명은 ``cross-encoder/ms-marco-
    MiniLM-L-12-v2`` 이며 ``-v2`` 가 없는 변형은 존재하지 않는다 (설계서
    §4.5.3 표기는 ``-v2`` 누락 — 설계서 차기 개정 시 반영 권장). 직전 세션
    까지는 ``.env`` 의 ``RAG_CROSS_ENCODER_MODEL`` 로 우회 중이었으며 본 fix 로
    코드 기본값만으로도 운영 모드(``RAG_USE_REAL_ADAPTERS=true``) 에서 모델
    로드 성공.
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
    # NOTE: 설계서 §4.5.3 은 ``cross-encoder/ms-marco-MiniLM-L-12`` 로 표기되어 있으나
    # Hugging Face / sentence-transformers 의 실 모델명은 ``-v2`` 가 정식이다 (``-v2``
    # 가 없는 변형은 존재하지 않음). 설계서 차기 개정 시 ``-v2`` 반영 권장.
    cross_encoder_model: str = "cross-encoder/ms-marco-MiniLM-L-12-v2"
    # Cross-Encoder Sigmoid temperature scaling (feature17c, 2026-05-20).
    # ms-marco 계열은 관련 passage 에 큰 양수 logit(8~11)을 출력해 sigmoid(logit) 가
    # 1.0 으로 saturate → Source.score 가 모두 100 으로 변별력을 잃는다. score 단계에서
    # ``sigmoid(logit / temperature)`` 로 분포를 펴 변별력을 회복한다.
    #
    # feature17c-2 (2026-05-20): 운영 logit 분포 수집(--debug-rerank) 결과 강관련
    # passage 의 logit 상한이 ~8.5~8.8 로 확인되어 T=4.0 을 기본값으로 채택. T=4 에서
    # 강관련 score 88~90 / 중관련 ~77 / 무관 ~51 로 변별이 회복된다. select_reranked
    # (LOW 0.55 / NARROW 0.65), formatter(LOW_CONFIDENCE_SCORE 55), extract_golden_set
    # (top1-threshold 0.80) 임계값을 T=4 기준으로 함께 재조정. 50건 재평가로 검증 후
    # 미세조정한다. 다른 T 가 필요하면 .env(RAG_CROSS_ENCODER_TEMPERATURE)로 override.
    cross_encoder_temperature: float = 4.0

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
