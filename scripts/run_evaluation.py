"""Evaluation Set 실행 + 결과 측정 CLI [Pipeline 평가 도구].

--------------------------------------------------
작성자 : 최태성
작성목적 : feature17a — 설계서 §6.2 Evaluation Set 50건을 그래프에 통과시키고
          (1) Precision@k (정답 page_id 기준), (2) 의도 분류 정확도, (3) 평균
          latency / NOT_SUPPORTED 비율 / Top-1 Cross-Encoder 점수 분포를 산출
          하는 자동 평가 CLI. 본 세션 (feature17a) 은 골격 + 시드 10건 실행
          까지, 50건 라벨링 + ROUGE-L / BERTScore 평가는 feature17b 이관.
작성일 : 2026-05-19
변경사항 내역 (날짜, 변경목적, 변경내용 순)
  - 2026-05-19, 최초 작성, feature17a — Evaluation Set 실행 + 4종 지표 산출.
  - 2026-05-19, feature17b 인프라 — ``--rouge-l`` / ``--bert-score`` 옵션 추가
    (설계서 §7.2.3 Golden Set 기반 자동 평가). Precision@k 매칭은 expected
    _chunk_ids 가 채워져 있으면 chunk_id 직접 비교 (정밀), 빈 배열이면 기존
    sources 비어 있지 않음 약식 매칭 (feature17a 동작 유지). chunk_id 추출은
    Source 의 confluence_url / text_preview 와 chunk_lookup 으로는 어려우므로,
    backfill 시점에 ``expected_chunk_ids`` 를 그대로 Qdrant scroll 로 채워두면
    eval 단계에서는 chunk_id 가 Source schema 에 없어도 page_id 우회 매칭이
    가능하다.
  - 2026-05-20, feature17b 정밀 매칭 — Source 스키마에 chunk_id/page_id 직접
    필드가 없고 confluence_url 패턴 (``/display/<SPACE>/<title>``) 에도 page_id
    가 없어, samples 의 page_id → webui_link 매핑을 1회 로드해 expected_page
    _ids 가 가리키는 webui_link set 과 Source.confluence_url 의 동일성으로
    page-level 정밀 매칭한다 (chunk-level 은 여전히 불가). samples 데이터가
    없으면 약식 매칭으로 자동 fallback. summary.precision_at_k.match_method 로
    매칭 방식을 명시한다.
--------------------------------------------------
[호환성]
  - Python 3.11.x
  - 사용법:
        # PoC 그래프로 시드 10건 실행 (외부 키/모델 없이)
        python scripts/run_evaluation.py --eval-set samples/evaluation_set.json

        # 운영 그래프 (실 GPT-4o + 운영 Qdrant) 로 실행
        python scripts/run_evaluation.py --use-real-adapters

        # 단일 질문 라우터 디버깅 (feature16 발견 #2 분석)
        python scripts/run_evaluation.py --debug-route "EKS 노드 장애 대응 절차는?"
  - NOTE: 본 스크립트는 routing/generation/verification 의 운영 적합성을 회귀
          가능한 형태로 측정한다. 라이브 평가가 아니므로 결과 JSON 은 시점에
          따라 다를 수 있다 (LLM 비결정론).
--------------------------------------------------
"""

from __future__ import annotations

import argparse
import json
import time
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Evaluation Set 을 그래프에 통과시키고 4종 지표를 측정한다.",
    )
    parser.add_argument(
        "--eval-set",
        type=Path,
        default=Path("samples/evaluation_set.json"),
        help="Evaluation Set JSON 경로 (기본: samples/evaluation_set.json).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="결과 JSON 저장 경로 (기본: reports/evaluation_<timestamp>.json).",
    )
    parser.add_argument(
        "--use-real-adapters",
        action="store_true",
        help="운영 그래프 (E5/BM25/Qdrant.from_settings + 실 OpenAI) 사용. 외부 의존성 필요.",
    )
    parser.add_argument(
        "--debug-route",
        type=str,
        default=None,
        help="단일 질문 라우터 디버깅 모드 — 의도/pool_weights/rewritten_queries 만 출력.",
    )
    parser.add_argument(
        "--debug-rerank",
        type=str,
        default=None,
        help=(
            "단일 질문의 검색 후보 raw Cross-Encoder logit 분포 출력 — temperature "
            "결정용 (feature17c-1). 운영 reranker(predict_logits) 필요 → --use-real-adapters 권장."
        ),
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=3,
        help="Precision@k 계산용 k (기본 3, 설계서 §6.4 KPI Precision@3).",
    )
    parser.add_argument(
        "--pool-weights",
        type=str,
        default=None,
        help=(
            "Pool 가중치 그리드 서치 — 모든 질의의 라우터 pool_weights 를 강제 오버라이드한다 "
            "(feature17c-9). 형식: 'title:0.25,content:0.6,label:0.15'. 라우터 출력을 덮어쓰므로 "
            "의도별 가중치 비교 실험에 사용. 미지정 시 라우터 값 그대로."
        ),
    )
    parser.add_argument(
        "--rouge-l",
        action="store_true",
        help="ROUGE-L F1 (rouge-score 라이브러리) 으로 answer vs expected_answer_excerpt 평가.",
    )
    parser.add_argument(
        "--bert-score",
        action="store_true",
        help=(
            "BERTScore F1 (bert-score 라이브러리) 으로 answer vs expected_answer_excerpt 평가."
            " transformers/torch 모델 다운로드 (~500MB) 필요."
        ),
    )
    args = parser.parse_args()

    if args.debug_route:
        return _run_debug_route(args.debug_route, use_real=args.use_real_adapters)

    if args.debug_rerank:
        return _run_debug_rerank(args.debug_rerank, use_real=args.use_real_adapters)

    if not args.eval_set.exists():
        print(f"[err] eval-set not found: {args.eval_set}")
        return 1

    pool_weights_override = _parse_pool_weights(args.pool_weights) if args.pool_weights else None

    return _run_evaluation(
        eval_set_path=args.eval_set,
        output_path=args.output,
        use_real=args.use_real_adapters,
        top_k=args.top_k,
        compute_rouge_l=args.rouge_l,
        compute_bert_score=args.bert_score,
        pool_weights_override=pool_weights_override,
    )


def _parse_pool_weights(spec: str) -> dict[str, float]:
    """'title:0.25,content:0.6,label:0.15' → {title_pool/content_pool/label_pool: float}.

    Pool 가중치 그리드 서치(feature17c-9)용. 짧은 키(title/content/label)를 Qdrant Pool
    이름(`title_pool`/`content_pool`/`label_pool`)으로 매핑한다. 3 Pool 모두 명시해야 한다.

    Raises:
        ValueError: 형식 오류 / 미지의 Pool 키 / 3 Pool 누락.
    """
    alias = {"title": "title_pool", "content": "content_pool", "label": "label_pool"}
    weights: dict[str, float] = {}
    for part in spec.split(","):
        if ":" not in part:
            raise ValueError(f"잘못된 pool-weights 항목: {part!r} (형식 'title:0.25')")
        key, _, value = part.partition(":")
        key = key.strip().lower()
        if key not in alias:
            raise ValueError(f"미지의 Pool 키: {key!r} (title/content/label 중 하나)")
        weights[alias[key]] = float(value.strip())
    if set(weights) != set(alias.values()):
        raise ValueError("pool-weights 는 title/content/label 3 Pool 을 모두 명시해야 한다")
    return weights


def _run_debug_route(query: str, *, use_real: bool) -> int:
    """단일 질문 라우터 디버깅 — feature16 smoke 발견 #2 (모두 운영가이드 분류) 분석."""
    from app.api.deps import build_poc_deps, build_real_deps
    from app.config import get_settings
    from app.query.acl import build_acl_filter
    from app.query.history import manage_history
    from app.query.router import manage_router
    from app.schemas.rag_state import RagState

    settings = get_settings()
    deps = build_real_deps(settings) if use_real else build_poc_deps(settings)

    # debug-route 는 라우터만 호출하므로 ACL 의 영향은 없으나 _run_evaluation 과
    # 일관되게 모든 space 포함.
    eval_groups = [
        "space:CLOUD",
        "space:CCC",
        "space:DEVOPS",
        "space:SEC",
        "space:ONBOARD",
        "space:PROJ",
        "space:DATADOG_KR",
    ]
    state = RagState(
        query=query,
        user_id="eval-user",
        groups=eval_groups,
        conversation_id="eval-conv-debug",
        acl_filter=build_acl_filter("eval-user", eval_groups),
    )
    # 라우터는 history_decision 을 읽으므로 manage_history 먼저 통과.
    manage_history(state, provider=deps.history_provider)
    manage_router(
        state,
        provider=deps.routing_provider,
        routing_config=deps.routing_config,
    )
    print(
        json.dumps(
            {
                "query": query,
                "intent": state.intent.value if state.intent else None,
                "rewritten_queries": state.rewritten_queries,
                "pool_weights": state.pool_weights,
                "metadata_filters": state.metadata_filters,
                "target_llm": state.target_llm.value if state.target_llm else None,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def _run_debug_rerank(query: str, *, use_real: bool) -> int:
    """단일 질문의 검색 후보 raw Cross-Encoder logit 분포 출력 — temperature 결정용.

    feature17c-1 — ms-marco logit 이 sigmoid 를 saturate 시켜 Source.score 가 모두
    100 으로 변별력을 잃던 문제의 적정 temperature(T) 를 데이터 기반으로 정하기 위해,
    실제 검색 후보(Top-20)의 raw logit 분포와 T별 sigmoid 점수 미리보기를 출력한다.
    """
    import math

    from app.api.deps import build_poc_deps, build_real_deps
    from app.config import get_settings
    from app.query.acl import build_acl_filter
    from app.query.history import manage_history
    from app.query.router import manage_router
    from app.query.search_node import hybrid_search
    from app.schemas.rag_state import RagState

    settings = get_settings()
    deps = build_real_deps(settings) if use_real else build_poc_deps(settings)

    reranker = deps.reranker
    if not hasattr(reranker, "predict_logits"):
        print(
            "[err] 주입된 reranker 에 predict_logits 가 없다 (Fake reranker). "
            "--use-real-adapters 로 실 CrossEncoderRerankerImpl 을 사용하라."
        )
        return 1

    eval_groups = [
        "space:CLOUD",
        "space:CCC",
        "space:DEVOPS",
        "space:SEC",
        "space:ONBOARD",
        "space:PROJ",
        "space:DATADOG_KR",
    ]
    state = RagState(
        query=query,
        user_id="eval-user",
        groups=eval_groups,
        conversation_id="eval-conv-debug-rerank",
        acl_filter=build_acl_filter("eval-user", eval_groups),
    )
    manage_history(state, provider=deps.history_provider)
    manage_router(state, provider=deps.routing_provider, routing_config=deps.routing_config)
    hybrid_search(
        state,
        dense_embedder=deps.dense_embedder,
        sparse_embedder=deps.sparse_embedder,
        store=deps.store,
    )

    candidates = state.candidates
    if not candidates:
        print(f"[debug-rerank] 검색 후보 0건 — query={query!r}")
        return 0

    query_text = (
        state.history_decision.contextualized_question
        if state.history_decision and state.history_decision.contextualized_question
        else state.query
    )
    passages = [c.text for c in candidates]
    logits = reranker.predict_logits(query_text, passages)
    ordered = sorted(logits, reverse=True)

    def _sigmoid(x: float) -> float:
        return 1.0 / (1.0 + math.exp(-x)) if x >= 0 else math.exp(x) / (1.0 + math.exp(x))

    n = len(ordered)
    print(f"[debug-rerank] query={query!r}")
    print(
        f"[debug-rerank] intent={state.intent.value if state.intent else None} "
        f"pool_weights={state.pool_weights} metadata_filters={state.metadata_filters}"
    )

    # 후보별 page 분포 — 정답 페이지가 후보에 있는지/몇 위에 reranking 되는지 진단용
    # (잔여 recall 실패 분석). logit 내림차순으로 page_id/title/section 출력.
    ranked = sorted(zip(candidates, logits, strict=True), key=lambda pair: pair[1], reverse=True)
    print(f"[debug-rerank] 후보 {n}건 (rerank logit 내림차순 — Top-5 가 답변 컨텍스트로 전달):")
    print("  rank | T4score | logit  | src  | page_id | section / title")
    for rank, (chunk, lg) in enumerate(ranked, start=1):
        meta = chunk.metadata
        src = "ATT" if meta.source_type.value == "attachment" else "page"
        label = (meta.attachment_filename or meta.page_title)[:32]
        section = (meta.section_header or "")[:24]
        marker = " <Top5" if rank <= 5 else ""
        print(
            f"  #{rank:>2} | {round(_sigmoid(lg / 4) * 100):>3} | {lg:>7.3f} | {src:>4} | "
            f"{meta.page_id:>7} | {label} / {section}{marker}"
        )
    print()
    print("[debug-rerank] raw logit 분포:")
    print(f"  max={ordered[0]:.3f} / min={ordered[-1]:.3f} / mean={sum(ordered) / n:.3f}")
    print(f"  Top-1 logit = {ordered[0]:.3f}")
    print()
    print("  T별 Top-1 sigmoid 점수 (round*100):")
    for t in (1.0, 2.0, 3.0, 4.0, 5.0, 8.0):
        s = _sigmoid(ordered[0] / t)
        print(f"    T={t:>4}: {s:.4f} → score {round(s * 100)}")
    print()
    print("  상위 5개 logit → T=1 vs T=4 vs T=8 score:")
    for i, lg in enumerate(ordered[:5]):
        s1, s4, s8 = _sigmoid(lg), _sigmoid(lg / 4), _sigmoid(lg / 8)
        print(
            f"    #{i + 1} logit={lg:>7.3f} → T1 {round(s1 * 100):>3} / "
            f"T4 {round(s4 * 100):>3} / T8 {round(s8 * 100):>3}"
        )
    return 0


def _run_evaluation(
    *,
    eval_set_path: Path,
    output_path: Path | None,
    use_real: bool,
    top_k: int,
    compute_rouge_l: bool = False,
    compute_bert_score: bool = False,
    pool_weights_override: dict[str, float] | None = None,
) -> int:
    """Evaluation Set 전체 실행 + 지표 산출."""
    from app.api.deps import build_poc_deps, build_real_deps
    from app.config import get_settings
    from app.pipeline.query_graph import build_query_graph, run_query
    from app.query.acl import build_acl_filter
    from app.query.router import manage_router
    from app.schemas.rag_state import RagState

    with eval_set_path.open() as fp:
        eval_data = json.load(fp)
    items: list[dict[str, Any]] = eval_data["items"]

    # feature17b 정밀 매칭 — samples 의 page_id → webui_link 매핑 1회 로드.
    # 운영 그래프는 chunk metadata 의 webui_link 를 Source.confluence_url 에
    # 그대로 채우므로, expected_page_ids 가 가리키는 webui_link set 과 Source
    # .confluence_url 동일성으로 page-level 정밀 매칭이 가능하다. samples 미
    # 존재 시 약식 매칭으로 자동 fallback.
    page_id_to_webui = _load_page_id_to_webui_link()
    match_method = "webui_link_strict" if page_id_to_webui else "loose_has_sources"

    settings = get_settings()
    deps = build_real_deps(settings) if use_real else build_poc_deps(settings)

    # feature17c-9 — Pool 가중치 그리드 서치: 라우터 노드를 래핑해 실 라우터 실행 후
    # state.pool_weights 를 강제 오버라이드한다. build_query_graph 는 router_node 가
    # manage_router 일 때만 provider/config 를 주입하므로, 래퍼가 직접 provider/config 를
    # captured 해 manage_router 를 호출한다(라우팅 정확도는 그대로, 가중치만 교체).
    if pool_weights_override is not None:
        routing_provider = deps.routing_provider
        routing_config = deps.routing_config

        # NOTE: 노드 annotation 은 ``Any`` 로 둔다 — LangGraph add_node 가 노드 콜러블에
        # get_type_hints 를 호출하는데, 그 평가는 run_evaluation 모듈 globals 에서 일어난다.
        # RagState 는 본 함수 내부 lazy import 라 모듈 globals 에 없어 NameError 가 난다.
        # Any 는 모듈 상단에 import 되어 있어 안전하다(그래프 state schema 는 StateGraph(RagState)).
        def _router_with_pool_override(state: Any) -> Any:
            manage_router(state, provider=routing_provider, routing_config=routing_config)
            state.pool_weights = dict(pool_weights_override)
            return state

        deps.router_node = _router_with_pool_override

    graph = build_query_graph(deps)

    results: list[dict[str, Any]] = []
    intent_correct = 0
    intent_total = 0
    precision_at_k_hits = 0
    precision_at_k_total = 0
    not_supported_count = 0
    verification_total = 0
    latency_ms_list: list[int] = []
    top1_score_list: list[int] = []
    # feature17b — ROUGE-L / BERTScore 누적 (라이브러리 lazy import, summary 에 평균 출력).
    predictions_for_metric: list[str] = []
    references_for_metric: list[str] = []

    for item in items:
        eval_id = item["id"]
        query = item["query"]
        expected_intent = item.get("intent")
        expected_page_ids: set[str] = set(item.get("expected_page_ids", []))

        # 평가용 사용자는 samples 의 모든 space 에 접근 가능해야 한다. ACL filter
        # 의 groups 인자가 state.groups 와 일치하지 않으면 검색이 차단되어
        # precision_at_k / verification 이 일관되게 0 으로 떨어진다 (2026-05-20 발견).
        # samples space: CLOUD / CCC / DEVOPS / SEC / ONBOARD / PROJ / DATADOG_KR.
        eval_groups = [
            "space:CLOUD",
            "space:CCC",
            "space:DEVOPS",
            "space:SEC",
            "space:ONBOARD",
            "space:PROJ",
            "space:DATADOG_KR",
        ]
        state = RagState(
            query=query,
            user_id="eval-user",
            groups=eval_groups,
            conversation_id=f"eval-conv-{eval_id}",
            acl_filter=build_acl_filter("eval-user", eval_groups),
        )
        started = time.perf_counter()
        response = run_query(state, graph=graph)
        elapsed_ms = int((time.perf_counter() - started) * 1000)

        # Precision@k — 응답 sources Top-k 중 expected_page_ids 와 매칭되는지.
        top_k_sources = response.sources[:top_k]
        match = _precision_match(
            top_k_sources,
            expected_page_ids,
            page_id_to_webui,
        )
        if expected_page_ids:
            precision_at_k_total += 1
            if match:
                precision_at_k_hits += 1

        # 의도 분류 정확도.
        if expected_intent and response.intent:
            intent_total += 1
            if response.intent.value == expected_intent:
                intent_correct += 1

        # 환각 비율.
        for v in response.verification:
            verification_total += 1
            if v.status.value == "NOT_SUPPORTED":
                not_supported_count += 1

        latency_ms_list.append(elapsed_ms)
        if response.sources:
            top1_score_list.append(response.sources[0].score)

        # feature17b — ROUGE-L/BERTScore 용 예측·정답 쌍 수집. expected_answer_excerpt
        # 가 있는 항목만 평가 대상에 포함.
        expected_excerpt = item.get("expected_answer_excerpt")
        if expected_excerpt and response.answer:
            predictions_for_metric.append(response.answer)
            references_for_metric.append(expected_excerpt)

        results.append(
            {
                "id": eval_id,
                "query": query,
                "expected_intent": expected_intent,
                "actual_intent": response.intent.value if response.intent else None,
                "intent_match": (
                    response.intent.value == expected_intent
                    if response.intent and expected_intent
                    else None
                ),
                "expected_page_ids": list(expected_page_ids),
                "actual_top_k_source_titles": [s.title for s in top_k_sources],
                "n_sources": len(response.sources),
                "top1_score": response.sources[0].score if response.sources else None,
                "verification": [
                    {"sentence_id": v.sentence_id, "status": v.status.value}
                    for v in response.verification
                ],
                "answer_excerpt": (response.answer or "")[:200],
                "feedback_enabled": response.feedback_enabled,
                "latency_ms": elapsed_ms,
            }
        )

    # --- ROUGE-L / BERTScore 산출 (feature17b 인프라) ---
    rouge_l_f1_avg: float | None = None
    bert_score_f1_avg: float | None = None
    if compute_rouge_l and predictions_for_metric:
        rouge_l_f1_avg = _compute_rouge_l_f1_avg(predictions_for_metric, references_for_metric)
    if compute_bert_score and predictions_for_metric:
        bert_score_f1_avg = _compute_bert_score_f1_avg(
            predictions_for_metric, references_for_metric
        )

    # --- 집계 ---
    summary = {
        "n_items": len(items),
        "intent_accuracy": (intent_correct / intent_total) if intent_total else None,
        "precision_at_k": {
            "k": top_k,
            "hit_ratio": (
                precision_at_k_hits / precision_at_k_total if precision_at_k_total else None
            ),
            "hits": precision_at_k_hits,
            "denom": precision_at_k_total,
            "match_method": match_method,
        },
        "not_supported_ratio": (
            not_supported_count / verification_total if verification_total else None
        ),
        "verification_total": verification_total,
        "not_supported_count": not_supported_count,
        "latency_ms_avg": (
            sum(latency_ms_list) / len(latency_ms_list) if latency_ms_list else None
        ),
        "latency_ms_max": max(latency_ms_list) if latency_ms_list else None,
        "latency_ms_p95": (
            sorted(latency_ms_list)[int(0.95 * (len(latency_ms_list) - 1))]
            if latency_ms_list
            else None
        ),
        "intent_distribution": dict(
            Counter(r["actual_intent"] for r in results if r["actual_intent"])
        ),
        "top1_score_avg": (
            sum(top1_score_list) / len(top1_score_list) if top1_score_list else None
        ),
        "rouge_l_f1_avg": rouge_l_f1_avg,
        "bert_score_f1_avg": bert_score_f1_avg,
        "answer_quality_n_items": len(predictions_for_metric),
        # feature17c-9 — Pool 가중치 그리드 서치 시 어떤 가중치로 측정했는지 기록(없으면 라우터 값).
        "pool_weights_override": pool_weights_override,
    }

    # --- 출력 ---
    report = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "eval_set": str(eval_set_path),
        "use_real_adapters": use_real,
        "summary": summary,
        "results": results,
    }
    if output_path is None:
        output_path = Path("reports") / f"evaluation_{datetime.utcnow():%Y%m%d_%H%M%S}.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2))

    print(f"[eval] {len(items)} items 실행 완료")
    print(f"[eval] report = {output_path}")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


def _load_page_id_to_webui_link(
    samples_dir: Path | None = None,
) -> dict[str, str]:
    """samples 의 페이지 데이터에서 ``{page_id: webui_link}`` 매핑을 로드한다.

    Source 스키마에 chunk_id/page_id 직접 필드가 없고 confluence_url 패턴
    (``/display/<SPACE>/<title>``) 에도 page_id 가 없어, samples 의 webui_link
    를 통해 page-level 정밀 매칭을 수행한다. 운영 그래프는 chunk metadata 의
    webui_link 를 Source.confluence_url 에 그대로 채우므로 일치 비교가 가능.

    samples_dir 미지정 시 ``samples/`` 를 기본 경로로 한다. 파일 미존재 또는
    스키마 불일치 시 빈 dict 반환 (호출 측이 약식 매칭으로 fallback).
    """
    samples_dir = samples_dir or Path("samples")
    candidates = [
        samples_dir / "confluence_sample_data.json",
        samples_dir / "datadog_docs.json",
    ]
    mapping: dict[str, str] = {}
    for path in candidates:
        if not path.exists():
            continue
        try:
            with path.open() as fp:
                data = json.load(fp)
        except (OSError, json.JSONDecodeError):
            continue
        for entry in data.get("single_page_responses", []) or []:
            if not isinstance(entry, dict):
                continue
            page_id = entry.get("id")
            webui = entry.get("_links", {}).get("webui")
            if page_id is not None and webui is not None:
                mapping[str(page_id)] = str(webui)
    return mapping


def _precision_match(
    top_k_sources: list[Any],
    expected_page_ids: set[str],
    page_id_to_webui: dict[str, str],
) -> bool:
    """Precision@k 단건 매칭 — webui_link 정밀 / sources 약식 fallback.

    page_id_to_webui 매핑이 있고 expected_page_ids 중 매핑 가능한 항목이 1건
    이상이면 webui_link 동일성 정밀 매칭. 매핑이 없거나 비어 있으면 sources
    가 비어 있지 않은지 만 검사하는 약식 매칭으로 fallback (feature17a 동작
    유지).
    """
    if not expected_page_ids:
        return False
    if page_id_to_webui:
        expected_webui_links: set[str] = {
            page_id_to_webui[pid] for pid in expected_page_ids if pid in page_id_to_webui
        }
        if expected_webui_links:
            return any(
                getattr(src, "confluence_url", None) in expected_webui_links
                for src in top_k_sources
            )
    # samples lookup 부재 또는 expected page_id 가 lookup 에 없음 → 약식.
    return len(top_k_sources) > 0


def _compute_rouge_l_f1_avg(predictions: list[str], references: list[str]) -> float:
    """ROUGE-L F1 평균 — 설계서 §7.2.3 자동 평가 정합 (rouge-score 라이브러리).

    rouge-score 는 경량 (pure Python) 이라 평가 시점 lazy import. evaluation extras
    미설치 환경에서는 ImportError 즉시 발생 — ``pip install -e ".[evaluation]"`` 안내.
    """
    try:
        from rouge_score import rouge_scorer
    except ImportError as exc:
        raise ImportError(
            'rouge-score 미설치 — `pip install -e ".[evaluation]"` 후 재실행.'
        ) from exc
    scorer = rouge_scorer.RougeScorer(["rougeL"], use_stemmer=False)
    f1_scores = [
        scorer.score(ref, pred)["rougeL"].fmeasure
        for pred, ref in zip(predictions, references, strict=True)
    ]
    return sum(f1_scores) / len(f1_scores) if f1_scores else 0.0


def _compute_bert_score_f1_avg(predictions: list[str], references: list[str]) -> float:
    """BERTScore F1 평균 — 설계서 §7.2.3 자동 평가 정합 (bert-score 라이브러리).

    bert-score 는 transformers/torch 모델 다운로드 (~500MB, multilingual). 한국어
    질의 정합으로 ``lang="ko"`` 사용. evaluation extras 미설치 시 ImportError.
    """
    try:
        from bert_score import score
    except ImportError as exc:
        raise ImportError(
            'bert-score 미설치 — `pip install -e ".[evaluation]"` 후 재실행.'
        ) from exc
    _, _, f1_tensor = score(predictions, references, lang="ko", verbose=False)
    f1_list = f1_tensor.tolist() if hasattr(f1_tensor, "tolist") else list(f1_tensor)
    return sum(f1_list) / len(f1_list) if f1_list else 0.0


if __name__ == "__main__":
    raise SystemExit(main())
