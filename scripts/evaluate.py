"""Run synthetic cases against the real application service, never a second evaluator model."""

import argparse
import asyncio
import json
import math
import platform
import statistics
from datetime import UTC, datetime
from pathlib import Path

from app.config import ROOT, Settings
from app.models import Incident
from app.service import InvestigationService


async def evaluate(mode: str, output: Path):
    service = InvestigationService(Settings(mode=mode))
    cases = json.loads((ROOT / "evaluation/incidents.json").read_text())
    rows = []
    try:
        await service.initialize()
        for case in cases:
            try:
                result = await service.analyze(Incident.model_validate(case["incident"]))
                retrieved = {s.runbook for s in result.sources}
                retrieval_hit = (
                    (case["expected_runbook"] in retrieved) if case["expected_runbook"] else None
                )
                decision_match = (
                    result.diagnosis.insufficient_evidence == case["expect_insufficient"]
                )
                term = case["expected_cause_term"]
                cause_match = (
                    term.lower() in " ".join(h.cause for h in result.diagnosis.hypotheses).lower()
                    if term
                    else None
                )
                rows.append(
                    {
                        "id": case["id"],
                        "split": case["split"],
                        "retrieval_hit_at_5": retrieval_hit,
                        "abstention_match": decision_match,
                        "cause_keyword_match": cause_match,
                        "latency_ms": result.latency_ms,
                        "input_tokens": result.input_tokens,
                        "output_tokens": result.output_tokens,
                        "embedding_tokens": result.embedding_tokens,
                        "error": None,
                    }
                )
            except Exception as error:
                rows.append(
                    {"id": case["id"], "split": case["split"], "error": type(error).__name__}
                )
    finally:
        await service.close()
    success = [r for r in rows if not r["error"]]
    expected = [r for r in rows if next(c for c in cases if c["id"] == r["id"])["expected_runbook"]]
    causes = [
        r for r in rows if next(c for c in cases if c["id"] == r["id"])["expected_cause_term"]
    ]

    def rate(items, key):
        return round(sum(bool(r.get(key)) for r in items) / len(items), 4) if items else None

    latencies = sorted(r["latency_ms"] for r in success)
    summary = {
        "total_cases": len(rows),
        "completed_cases": len(success),
        "errors": len(rows) - len(success),
        "retrieval_hit_at_5": rate(expected, "retrieval_hit_at_5"),
        "abstention_match": rate(rows, "abstention_match"),
        "cause_keyword_match": rate(causes, "cause_keyword_match"),
        "latency_median_ms": round(statistics.median(latencies), 2) if latencies else None,
        "latency_p95_ms": latencies[max(0, math.ceil(0.95 * len(latencies)) - 1)]
        if latencies
        else None,
        "input_tokens": sum(r.get("input_tokens", 0) for r in rows),
        "output_tokens": sum(r.get("output_tokens", 0) for r in rows),
        "embedding_query_tokens": sum(r.get("embedding_tokens", 0) for r in rows),
    }
    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "mode": mode,
        "python": platform.python_version(),
        "model": service.settings.model if mode == "live" else None,
        "limitations": "Synthetic smoke/variation fixtures, not an independent benchmark. Demo uses rules, not an LLM. Keyword matching is a coarse check, not factual diagnosis grading. API tests cover citation validation separately. Latency excludes startup/indexing; embedding query tokens exclude indexing. Errors count as failed checks.",
        "summary": summary,
        "cases": rows,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    if summary["errors"]:
        raise SystemExit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["demo", "live"], default="demo")
    parser.add_argument("--output", type=Path, default=ROOT / "evaluation/local-results.json")
    args = parser.parse_args()
    asyncio.run(evaluate(args.mode, args.output))
