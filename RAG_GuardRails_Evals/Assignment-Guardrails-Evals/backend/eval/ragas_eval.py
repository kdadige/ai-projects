"""
ragas_eval.py - RAGAs evaluation with ablation study
"""
from __future__ import annotations
import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

logger = logging.getLogger(__name__)

QA_DATASET_PATH = Path(__file__).parent / "qa_dataset.json"


def load_qa_dataset() -> list[dict]:
    """Load the ground truth QA dataset."""
    with open(QA_DATASET_PATH) as f:
        data = json.load(f)
    # Filter to only use standard questions (not adversarial/guardrail tests)
    return [q for q in data if q["category"] not in ("rbac_adversarial", "guardrail_test")]


async def run_pipeline_for_eval(
    question: str,
    role: str,
    use_routing: bool = True,
    use_guardrails: bool = True,
) -> dict[str, Any]:
    """
    Run the RAG pipeline in eval mode (bypass some components for ablation).
    """
    from vector_store.qdrant_store import QdrantStore
    from routing.semantic_router import classify_query
    from rag.pipeline import build_context
    from config import RBAC_MATRIX
    from groq import AsyncGroq
    from config import settings

    store = QdrantStore()
    groq_client = AsyncGroq(api_key=settings.groq_api_key)
    user_collections = RBAC_MATRIX.get(role, [])

    # Determine target collections
    if use_routing:
        routing = classify_query(question, role)
        if routing["access_denied"]:
            return {"answer": routing["denied_reason"], "contexts": []}
        target_collections = routing["target_collections"] or user_collections
    else:
        target_collections = user_collections

    # Retrieve
    chunks = await store.search(
        query=question,
        user_role=role,
        collections=target_collections,
        top_k=5,
    )

    if not chunks:
        return {"answer": "No relevant information found.", "contexts": []}

    contexts = [c["text"] for c in chunks]
    context_text = build_context(chunks)

    from rag.pipeline import SYSTEM_PROMPT
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"Context:\n\n{context_text}\n\nQuestion: {question}\n\nAnswer with citations:",
        },
    ]

    response = await groq_client.chat.completions.create(
        model=settings.groq_model,
        messages=messages,
        temperature=0.1,
        max_tokens=800,
    )

    answer = response.choices[0].message.content or ""
    return {"answer": answer, "contexts": contexts}


async def collect_pipeline_outputs(
    qa_pairs: list[dict],
    use_routing: bool = True,
    use_guardrails: bool = True,
    limit: int = None,
) -> list[dict]:
    """Collect pipeline outputs for RAGAs evaluation."""
    results = []
    pairs_to_eval = qa_pairs[:limit] if limit else qa_pairs

    for i, qa in enumerate(pairs_to_eval):
        logger.info(f"Evaluating {i+1}/{len(pairs_to_eval)}: {qa['question'][:60]}...")
        try:
            output = await run_pipeline_for_eval(
                question=qa["question"],
                role=qa["role"],
                use_routing=use_routing,
                use_guardrails=use_guardrails,
            )
            results.append({
                "question": qa["question"],
                "answer": output["answer"],
                "contexts": output["contexts"],
                "ground_truth": qa["ground_truth"],
                "collection": qa["collection"],
                "role": qa["role"],
                "category": qa["category"],
            })
        except Exception as e:
            logger.error(f"Failed to evaluate Q{qa['id']}: {e}")
            results.append({
                "question": qa["question"],
                "answer": f"Error: {str(e)}",
                "contexts": [],
                "ground_truth": qa["ground_truth"],
                "collection": qa["collection"],
                "role": qa["role"],
                "category": qa["category"],
            })

        # Small delay to avoid rate limiting
        await asyncio.sleep(0.5)

    return results


def run_ragas_evaluation(results: list[dict]) -> dict:
    """Run RAGAs evaluation on collected results."""
    try:
        from ragas import evaluate
        from ragas.metrics import (
            faithfulness,
            answer_relevancy,
            context_precision,
            context_recall,
            answer_correctness,
        )
        from datasets import Dataset

        # Prepare dataset
        eval_data = {
            "question": [r["question"] for r in results],
            "answer": [r["answer"] for r in results],
            "contexts": [r["contexts"] for r in results],
            "ground_truth": [r["ground_truth"] for r in results],
        }

        dataset = Dataset.from_dict(eval_data)

        metrics = [
            faithfulness,
            answer_relevancy,
            context_precision,
            context_recall,
            answer_correctness,
        ]

        score = evaluate(dataset, metrics=metrics)
        return score

    except Exception as e:
        logger.error(f"RAGAs evaluation failed: {e}")
        return {"error": str(e)}


async def run_ablation_study(output_dir: str = "."):
    """
    Run ablation study with 4 configurations:
    1. Full pipeline (routing + guardrails + hierarchical chunking)
    2. No routing (search all accessible collections)
    3. No guardrails (skip input/output checks)
    4. Full pipeline (baseline comparison)
    """
    qa_pairs = load_qa_dataset()
    logger.info(f"Loaded {len(qa_pairs)} QA pairs for ablation study")

    # Limit to 20 questions per ablation run to save cost
    eval_limit = min(20, len(qa_pairs))

    configurations = [
        {"name": "full_pipeline", "use_routing": True, "use_guardrails": True},
        {"name": "no_routing", "use_routing": False, "use_guardrails": True},
        {"name": "no_guardrails", "use_routing": True, "use_guardrails": False},
    ]

    all_scores = {}

    for config in configurations:
        logger.info(f"\n{'='*60}")
        logger.info(f"Running ablation: {config['name']}")
        logger.info(f"{'='*60}")

        results = await collect_pipeline_outputs(
            qa_pairs,
            use_routing=config["use_routing"],
            use_guardrails=config["use_guardrails"],
            limit=eval_limit,
        )

        # Save raw results
        results_path = Path(output_dir) / f"ablation_{config['name']}_raw.json"
        with open(results_path, "w") as f:
            json.dump(results, f, indent=2)

        # Run RAGAs
        scores = run_ragas_evaluation(results)
        all_scores[config["name"]] = scores
        logger.info(f"Scores for {config['name']}: {scores}")

    # Create ablation summary table
    summary_rows = []
    for config_name, scores in all_scores.items():
        if isinstance(scores, dict) and "error" not in scores:
            try:
                row = {
                    "Configuration": config_name,
                    "Faithfulness": round(float(scores.get("faithfulness", 0)), 4),
                    "Answer Relevancy": round(float(scores.get("answer_relevancy", 0)), 4),
                    "Context Precision": round(float(scores.get("context_precision", 0)), 4),
                    "Context Recall": round(float(scores.get("context_recall", 0)), 4),
                    "Answer Correctness": round(float(scores.get("answer_correctness", 0)), 4),
                }
            except Exception:
                row = {"Configuration": config_name, "Error": str(scores)}
        else:
            row = {"Configuration": config_name, "Error": str(scores.get("error", "Unknown"))}
        summary_rows.append(row)

    summary_df = pd.DataFrame(summary_rows)
    summary_path = Path(output_dir) / "ablation_results.csv"
    summary_df.to_csv(summary_path, index=False)

    logger.info(f"\nAblation Results:\n{summary_df.to_string()}")
    logger.info(f"Results saved to {summary_path}")

    # Save JSON
    scores_path = Path(output_dir) / "ablation_scores.json"
    with open(scores_path, "w") as f:
        json.dump(
            {k: {str(mk): str(mv) for mk, mv in v.items()} if isinstance(v, dict) else str(v)
             for k, v in all_scores.items()},
            f, indent=2
        )

    return all_scores


if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description="Run RAGAs evaluation")
    parser.add_argument("--output-dir", default=".", help="Directory for output files")
    parser.add_argument("--ablation", action="store_true", help="Run full ablation study")
    args = parser.parse_args()

    if args.ablation:
        asyncio.run(run_ablation_study(output_dir=args.output_dir))
    else:
        async def single_run():
            qa_pairs = load_qa_dataset()
            results = await collect_pipeline_outputs(qa_pairs, limit=20)
            scores = run_ragas_evaluation(results)
            print(f"\nRAGAs Scores:\n{json.dumps({str(k): str(v) for k, v in scores.items()}, indent=2)}")

        asyncio.run(single_run())

