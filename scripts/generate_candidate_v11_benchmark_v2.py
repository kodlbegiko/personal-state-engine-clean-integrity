from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path
from typing import Any

import generate_candidate_v11_benchmark as base


# Development iteration 1 exposed a generator defect: the negative-case
# wrong-relation offset could equal the domain count, wrapping back to the
# original semantic domain. This corrected constructor guarantees an offset in
# [1, domain_count - 1]. The v1 generator and v1 benchmark remain immutable
# historical Development evidence.
def negative_case(stage: str, family: str, index: int, rng: random.Random) -> dict[str, Any]:
    domain = base.DOMAINS[(index * 7 + rng.randrange(len(base.DOMAINS))) % len(base.DOMAINS)]
    domain_index = base.DOMAINS.index(domain)
    offset = 1 + (index % (len(base.DOMAINS) - 1))
    wrong_domain = base.DOMAINS[(domain_index + offset) % len(base.DOMAINS)]
    assert wrong_domain["relation"] != domain["relation"]

    name = base.person(stage, 5000 + index)
    wrong_name = base.other_person(stage, 5000 + index)
    value, alt_value, _ = base.choose_values(domain, index + 2)
    query = base.QUERY_TEMPLATES[family].format(name=name, field=domain["label"])
    wrong_relation_value = wrong_domain["values"][(index + 1) % len(wrong_domain["values"])]
    memories = [
        {
            "id": f"CV11-{stage[:3].upper()}-N-{index:03d}-novalue",
            "speaker": "user",
            "text": f"No verified value is available for {name}'s {domain['label']}.",
            "timestamp": base.timestamp(4),
        },
        {
            "id": f"CV11-{stage[:3].upper()}-N-{index:03d}-uncertain",
            "speaker": "user",
            "text": f"{name}'s {domain['label']} is perhaps {value}.",
            "timestamp": base.timestamp(4),
        },
        {
            "id": f"CV11-{stage[:3].upper()}-N-{index:03d}-wrong-subject",
            "speaker": "user",
            "text": f"{wrong_name}'s {domain['label']} is {alt_value}.",
            "timestamp": base.timestamp(4),
        },
        {
            "id": f"CV11-{stage[:3].upper()}-N-{index:03d}-agenda",
            "speaker": "user",
            "text": f"Agenda item: discuss {name}'s {domain['label']} at a later meeting.",
            "timestamp": base.timestamp(4),
        },
        {
            "id": f"CV11-{stage[:3].upper()}-N-{index:03d}-wrong-relation",
            "speaker": "user",
            "text": f"{name}'s {wrong_domain['label']} is {wrong_relation_value}.",
            "timestamp": base.timestamp(4),
        },
    ]
    rng.shuffle(memories)
    return {
        "id": f"CV11-{stage.upper()}-N-{index:03d}",
        "designation": stage.upper(),
        "query": query,
        "memories": memories,
        "relevant_memory_ids": [],
        "generator_metadata": {
            "query_grammar_family": family,
            "evidence_grammar_family": family,
            "structural_mechanism": base.STRUCTURAL_MECHANISM[family],
            "semantic_domain": domain["relation"],
            "template_provenance": f"candidate-v11:{stage}:{family}:negative:v2",
            "polarity": "no_evidence_adversarial",
        },
        "provenance": f"candidate-v11-fresh-generator-v2:{stage}:negative:{index}",
    }


# Patch only the corrected constructor into the preregistered stage-separated
# generator. Answerable construction, stage counts, seeds, and grammar-family
# boundaries remain unchanged.
base.negative_case = negative_case


def generate(stage: str) -> dict[str, Any]:
    payload = base.generate(stage)
    payload["schema_version"] = "candidate-v11-benchmark-v2"
    payload["name"] = f"candidate-v11-{stage}-v2"
    payload["generator_design"] = (
        "stage-separated structural grammar mechanisms with corrected disjoint "
        "wrong-relation negatives, semantic competition, and adversarial no-evidence cases"
    )
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=tuple(base.STAGES), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = generate(args.stage)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    args.output.write_text(encoded)
    print(json.dumps({
        "stage": args.stage,
        "seed": payload["seed"],
        "case_count": payload["case_count"],
        "answerable_count": payload["answerable_count"],
        "no_evidence_count": payload["no_evidence_count"],
        "families": payload["grammar_families"],
        "sha256": hashlib.sha256(encoded.encode("utf-8")).hexdigest(),
        "generator_revision": 2,
    }, indent=2))


if __name__ == "__main__":
    main()
