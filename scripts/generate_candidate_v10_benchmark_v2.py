from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

import generate_candidate_v10_benchmark as base


def normalize(text: str) -> str:
    """Conventional normalized-overlap representation.

    Lowercase and normalize whitespace/typographic apostrophes only. Entity and
    value abstraction are deliberately NOT performed here; those are measured
    separately by skeleton and declared latent grammar-family audits.
    """
    text = text.replace("’", "'").casefold()
    text = re.sub(r"\s+", " ", text).strip()
    return text


def skeleton(text: str) -> str:
    text = normalize(text)
    first = "|".join(x.casefold() for x in base.FIRST)
    last = "|".join(x.casefold() for x in base.LAST)
    text = re.sub(rf"\b(?:{first})\b", "<person>", text)
    text = re.sub(rf"\b(?:{last})\d*\b", "<surname>", text)
    text = re.sub(r"\b\d+(?:[.:]\d+)?\b", "<num>", text)
    # The final open-class answer phrase is abstracted for evidence skeletons;
    # slot words and constructional syntax remain visible.
    text = re.sub(r"\b[a-z][a-z-]*(?:\s+[a-z][a-z-]*){0,3}\b(?=[.?!])", "<tail>", text)
    return text


def audit_payload(payload: dict) -> dict:
    cases = payload["cases"]
    exact = [json.dumps({"q": c["query"], "m": [m["text"] for m in c["memories"]]}, sort_keys=True) for c in cases]
    normalized = [json.dumps({"q": normalize(c["query"]), "m": sorted(normalize(m["text"]) for m in c["memories"])}, sort_keys=True) for c in cases]
    qsk = [skeleton(c["query"]) for c in cases]
    esk = [
        skeleton(next(m["text"] for m in c["memories"] if m["id"] in c["relevant_memory_ids"]))
        for c in cases if c["relevant_memory_ids"]
    ]
    families = Counter(c["generator_metadata"]["query_grammar_family"] for c in cases)
    domains = Counter(c["generator_metadata"]["semantic_domain"] for c in cases)
    return {
        "schema_version": "candidate-v10-freshness-audit-v2",
        "stage": payload["designation"].casefold(),
        "case_count": len(cases),
        "exact_surface_duplicate_count": len(exact) - len(set(exact)),
        "normalized_surface_duplicate_count": len(normalized) - len(set(normalized)),
        "question_skeleton_unique": len(set(qsk)),
        "evidence_skeleton_unique": len(set(esk)),
        "grammar_family_distribution": dict(sorted(families.items())),
        "semantic_domain_distribution": dict(sorted(domains.items())),
        "declared_family_partition": payload["grammar_family_partition"],
        "template_provenance": sorted({c["generator_metadata"]["template_provenance"] for c in cases}),
        "normalization_policy": "casefold + apostrophe + whitespace; entity/value abstraction reserved for skeleton audit",
        "inference_metadata_visibility": False,
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--stage", choices=base.STAGE_SPECS, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--audit", type=Path, required=True)
    args = p.parse_args()
    payload = base.generate(args.stage)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n")
    audit = audit_payload(payload)
    args.audit.parent.mkdir(parents=True, exist_ok=True)
    args.audit.write_text(json.dumps(audit, indent=2) + "\n")
    digest = hashlib.sha256(args.output.read_bytes()).hexdigest()
    print(json.dumps({"stage": args.stage, "cases": payload["case_count"], "sha256": digest, "audit": audit}, indent=2))
    if audit["exact_surface_duplicate_count"] or audit["normalized_surface_duplicate_count"]:
        raise SystemExit("freshness duplicate detected")


if __name__ == "__main__":
    main()
