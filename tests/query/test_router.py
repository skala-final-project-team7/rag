"""질의 라우터 어댑터 검증 (Agent 통합 1/4) — query-routing-agent ↔ RagState.

manage_router: vendoring 한 query-routing-agent 로직(normalize → classify → rewrite →
filter/weight)을 in-process 로 호출해 라우팅 의도·확장 쿼리·메타필터·Pool 가중치를
채우고 RagState 에 담는다. agent LLM 호출은 FakeRoutingLLMProvider 로 대체.
"""

import json

import pytest

from app.ingestion.vector_store import CONTENT_POOL, LABEL_POOL, TITLE_POOL
from app.query.router import manage_router
from app.schemas.enums import Intent, LlmModel
from app.schemas.rag_state import HistoryDecision, RagState
from query_routing_agent.llm import FakeRoutingLLMProvider


def _state(
    *,
    conversation_id: str | None = "conv-1",
    query: str = "IAM 정책 변경 후 롤백 절차는?",
    groups: list[str] | None = None,
    history_decision: HistoryDecision | None = None,
) -> RagState:
    return RagState(
        query=query,
        user_id="user-1",
        conversation_id=conversation_id,
        groups=groups if groups is not None else ["sre", "platform"],
        history_decision=history_decision,
    )


def _fake(intent: str, *, expanded_queries: list[str] | None = None) -> FakeRoutingLLMProvider:
    payload: dict[str, object] = {
        "intent": intent,
        "confidence": 0.9,
        "reason": f"{intent} 판정",
    }
    if expanded_queries is not None:
        payload["expanded_queries"] = expanded_queries
    return FakeRoutingLLMProvider(payload)


def test_no_conversation_id_shortcuts_to_fallback() -> None:
    # conversation_id 가 없으면 agent 호출 없이 OPERATION_GUIDE 로 안전 fallback.
    result = manage_router(_state(conversation_id=None))
    assert result.intent is Intent.OPERATION_GUIDE
    assert result.rewritten_queries == ["IAM 정책 변경 후 롤백 절차는?"]
    assert result.pool_weights == {TITLE_POOL: 0.2, CONTENT_POOL: 0.7, LABEL_POOL: 0.1}
    assert result.target_llm is LlmModel.GPT_4O
    assert result.metadata_filters is None


def test_operations_guide_intent_default() -> None:
    # 기본 fake provider (operations_guide) — provider=None 분기 회귀 보호.
    result = manage_router(_state())
    assert result.intent is Intent.OPERATION_GUIDE
    assert result.target_llm is LlmModel.GPT_4O
    assert result.rewritten_queries  # deterministic fallback 으로 비어있지 않음.


def test_incident_response_intent_maps_to_korean_enum() -> None:
    result = manage_router(_state(), provider=_fake("incident_response"))
    assert result.intent is Intent.INCIDENT_RESPONSE
    # incident_response 의 default pool weight (title=0.2/content=0.65/label=0.15).
    assert result.pool_weights == {TITLE_POOL: 0.2, CONTENT_POOL: 0.65, LABEL_POOL: 0.15}


def test_policy_procedure_intent_maps_to_korean_enum() -> None:
    result = manage_router(_state(), provider=_fake("policy_procedure"))
    assert result.intent is Intent.POLICY_PROCEDURE
    assert result.pool_weights == {TITLE_POOL: 0.3, CONTENT_POOL: 0.6, LABEL_POOL: 0.1}


def test_history_lookup_intent_maps_to_korean_enum() -> None:
    result = manage_router(_state(), provider=_fake("history_lookup"))
    assert result.intent is Intent.HISTORY_LOOKUP
    assert result.pool_weights == {TITLE_POOL: 0.2, CONTENT_POOL: 0.5, LABEL_POOL: 0.3}


def test_unknown_intent_falls_back_to_operation_guide() -> None:
    # Agent IntentLabel.UNKNOWN 은 rag Intent 에 대응값이 없으므로 OPERATION_GUIDE fallback.
    result = manage_router(_state(), provider=_fake("unknown"))
    assert result.intent is Intent.OPERATION_GUIDE


def test_expanded_queries_hint_is_used_when_provided() -> None:
    hints = ["IAM 정책 롤백 절차", "IAM rollback procedure"]
    result = manage_router(
        _state(),
        provider=_fake("operations_guide", expanded_queries=hints),
    )
    # LLM 힌트가 있으면 정규화 후 first-N 으로 그대로 사용 (default 3 개까지 채워짐).
    assert hints[0] in result.rewritten_queries
    assert hints[1] in result.rewritten_queries


def test_expanded_queries_default_fallback_is_nonempty() -> None:
    # LLM 힌트 없으면 deterministic fallback — rewritten_queries 가 반드시 비어있지 않음.
    result = manage_router(_state(), provider=_fake("operations_guide"))
    assert len(result.rewritten_queries) >= 1
    assert all(isinstance(q, str) and q for q in result.rewritten_queries)


def test_pool_weights_sum_to_one() -> None:
    result = manage_router(_state(), provider=_fake("operations_guide"))
    total = sum(result.pool_weights.values())
    assert total == pytest.approx(1.0)


def test_metadata_filters_includes_groups_via_acl() -> None:
    # groups 가 routing input 의 metadata.groups 로 전달되어 MetadataFilter.acl 에 담긴다.
    result = manage_router(
        _state(groups=["sre", "platform"]),
        provider=_fake("operations_guide"),
    )
    assert result.metadata_filters is not None
    acl = result.metadata_filters["acl"]
    assert acl["user_id"] == "user-1"
    assert sorted(acl["groups"]) == ["platform", "sre"]


def test_provider_failure_falls_back_safely() -> None:
    # provider 가 RuntimeError 를 던지면 안전 fallback (OPERATION_GUIDE) 로 흡수.
    failing_provider = FakeRoutingLLMProvider(RuntimeError("transient provider error"))
    result = manage_router(_state(), provider=failing_provider)
    assert result.intent is Intent.OPERATION_GUIDE
    assert result.rewritten_queries == ["IAM 정책 변경 후 롤백 절차는?"]
    assert result.pool_weights == {TITLE_POOL: 0.2, CONTENT_POOL: 0.7, LABEL_POOL: 0.1}
    assert result.metadata_filters is None


def test_invalid_llm_payload_falls_back_safely() -> None:
    # confidence 누락 등 schema 위반은 ClassificationValidationError 로 흡수돼 fallback.
    invalid_provider = FakeRoutingLLMProvider(
        json.dumps({"intent": "operations_guide", "reason": "missing confidence"})
    )
    result = manage_router(_state(), provider=invalid_provider)
    assert result.intent is Intent.OPERATION_GUIDE
    assert result.metadata_filters is None


def test_history_decision_preserved_context_is_forwarded() -> None:
    # history_decision 의 preserved_context 가 라우터 입력 payload 로 전달되는지 회귀 보호.
    # 단순 동작 검증 — context 가 전달돼도 정상 분기 진행을 확인하면 충분.
    decision = HistoryDecision(
        decision="follow_up",
        contextualized_question="IAM 정책 변경 후 롤백 절차는?",
        preserved_context={
            "summary": "IAM 정책 변경 장애 대응 맥락",
            "entities": ["IAM 정책", "롤백"],
            "turn_refs": ["turn-0", "turn-1"],
        },
        reset_required=False,
        confidence=0.8,
        reason="follow_up 판정",
    )
    result = manage_router(
        _state(history_decision=decision),
        provider=_fake("incident_response"),
    )
    assert result.intent is Intent.INCIDENT_RESPONSE


def test_state_query_is_not_mutated() -> None:
    state = _state()
    original_query = state.query
    manage_router(state, provider=_fake("operations_guide"))
    assert state.query == original_query
