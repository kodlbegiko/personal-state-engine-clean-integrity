from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


def normalized_text(text: str) -> str:
    text = text.casefold()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^a-z0-9 ]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def case_exact(case: dict[str, Any]) -> str:
    payload = {
        "query": case["query"],
        "memories": [m["text"] for m in case["memories"]],
        "relevant_count": len(case["relevant_memory_ids"]),
    }
    return json.dumps(payload, sort_keys=True)


def case_normalized(case: dict[str, Any]) -> str:
    payload = {
        "query": normalized_text(case["query"]),
        "memories": sorted(normalized_text(m["text"]) for m in case["memories"]),
        "relevant_count": len(case["relevant_memory_ids"]),
    }
    return json.dumps(payload, sort_keys=True)


def skeleton(text: str) -> str:
    # Diagnostic only: remove synthetic identifiers/numerals and open-class
    # capitalized spans to reveal structural template overlap.
    text = re.sub(r"\b[A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z0-9]+)*\b", "<ENTITY>", text)
    text = re.sub(r"\b\d+\b", "<N>", text)
    text = re.sub(r"[A-Z]D\d{3}|[A-Z]P\d{3}|[A-Z]C\d{3}|[A-Z]F\d{3}", "<ID>", text)
    return normalized_text(text)


def duplicate_count(values: list[str]) -> int:
    counts = Counter(values)
    return sum(count - 1 for count in counts.values() if count > 1)


def summarize(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text())
    cases = payload["cases"]
    exact = [case_exact(c) for c in cases]
    normalized = [case_normalized(c) for c in cases]
    query_skeletons = [skeleton(c["query"]) for c in cases]
    evidence_skeletons = [skeleton(m["text"]) for c in cases for m in c["memories"]]
    families = Counter(c["generator_metadata"]["query_grammar_family"] for c in cases)
    domains = Counter(c["generator_metadata"]["semantic_domain"] for c in cases)
    provenances = Counter(c["generator_metadata"]["template_provenance"] for c in cases)
    mechanisms = Counter(c["generator_metadata"]["structural_mechanism"] for c in cases)
    return {
        "stage": payload["stage"],
        "benchmark_name": payload["name"],
        "benchmark_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "case_count": len(cases),
        "answerable_count": payload["answerable_count"],
        "no_evidence_count": payload["no_evidence_count"],
        "exact_duplicate_count": duplicate_count(exact),
        "normalized_duplicate_count": duplicate_count(normalized),
        "query_skeleton_unique": len(set(query_skeletons)),
        "query_skeleton_top": Counter(query_skeletons).most_common(12),
        "evidence_skeleton_unique": len(set(evidence_skeletons)),
        "evidence_skeleton_top": Counter(evidence_skeletons).most_common(12),
        "semantic_domain_distribution": dict(sorted(domains.items())),
        "grammar_family_distribution": dict(sorted(families.items())),
        "structural_mechanism_distribution": dict(sorted(mechanisms.items())),
        "template_provenance_distribution": dict(sorted(provenances.items())),
        "_exact": set(exact),
        "_normalized": set(normalized),
        "_query_skeletons": set(query_skeletons),
        "_evidence_skeletons": set(evidence_skeletons),
        "_families": set(families),
        "_provenances": set(provenances),
        "_mechanisms": set(mechanisms),
    }


def public_summary(row: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in row.items() if not k.startswith("_")}


def pair_audit(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    exact_overlap = len(a["_exact"] & b["_exact"])
    normalized_overlap = len(a["_normalized"] & b["_normalized"])
    family_overlap = sorted(a["_families"] & b["_families"])
    provenance_overlap = sorted(a["_provenances"] & b["_provenances"])
    mechanism_overlap = sorted(a["_mechanisms"] & b["_mechanisms"])
    query_skeleton_overlap = len(a["_query_skeletons"] & b["_query_skeletons"])
    evidence_skeleton_overlap = len(a["_evidence_skeletons"] & b["_evidence_skeletons"])
    hard_pass = (
        exact_overlap == 0
        and normalized_overlap == 0
        and not family_overlap
        and not provenance_overlap
        and not mechanism_overlap
    )
    return {
        "pair": [a["stage"], b["stage"]],
        "exact_case_overlap": exact_overlap,
        "normalized_case_overlap": normalized_overlap,
        "grammar_family_overlap": family_overlap,
        "template_provenance_overlap": provenance_overlap,
        "structural_mechanism_overlap": mechanism_overlap,
        "query_skeleton_overlap_count": query_skeleton_overlap,
        "evidence_skeleton_overlap_count": evidence_skeleton_overlap,
        "hard_freshness_pass": hard_pass,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("benchmarks", nargs="+", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    rows = [summarize(path) for path in args.benchmarks]
    pairs = [
        pair_audit(rows[i], rows[j])
        for i in range(len(rows))
        for j in range(i + 1, len(rows))
    ]
    per_stage_pass = all(
        row["exact_duplicate_count"] == 0 and row["normalized_duplicate_count"] == 0
        for row in rows
    )
    cross_stage_pass = all(pair["hard_freshness_pass"] for pair in pairs)
    result = {
        "schema_version": "candidate-v11-freshness-audit-v1",
        "per_stage": [public_summary(row) for row in rows],
        "cross_stage": pairs,
        "per_stage_hard_freshness_pass": per_stage_pass,
        "cross_stage_hard_freshness_pass": cross_stage_pass,
        "verdict": "PASS" if per_stage_pass and cross_stage_pass else "FAIL",
        "skeleton_overlap_policy": "reported for methodology review; exact/normalized/family/provenance/mechanism overlap are hard constraints",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "stages": [row["stage"] for row in rows],
        "per_stage_pass": per_stage_pass,
        "cross_stage_pass": cross_stage_pass,
        "cross_stage": pairs,
        "verdict": result["verdict"],
    }, indent=2))
    if result["verdict"] != "PASS":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
