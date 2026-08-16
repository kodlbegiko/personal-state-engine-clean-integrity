from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path
from typing import Any

import generate_candidate_v11_benchmark as base
import generate_candidate_v11_benchmark_v2 as gen2


# Keep the iteration-2 corrected negative construction immutable by reuse.
base.negative_case = gen2.negative_case


def answerable_case(stage: str, family: str, index: int, rng: random.Random) -> dict[str, Any]:
    domain = base.DOMAINS[(index * 5 + rng.randrange(len(base.DOMAINS))) % len(base.DOMAINS)]
    domain_index = base.DOMAINS.index(domain)
    wrong_domain = base.DOMAINS[(domain_index + 1 + (index % (len(base.DOMAINS) - 1))) % len(base.DOMAINS)]
    assert wrong_domain["relation"] != domain["relation"]

    name = base.person(stage, index)
    wrong_name = base.other_person(stage, index)
    value, competing_value, uncertain_value = base.choose_values(domain, index)
    query = base.QUERY_TEMPLATES[family].format(name=name, field=domain["label"])
    relevant = base.RELEVANT_TEMPLATES[family].format(name=name, field=domain["label"], value=value)

    # This competitor is deliberately constructed to expose Candidate-v2's
    # legitimate lexical/recency preference without becoming a hard-blocked
    # adversarial echo. It is still valid Candidate-v10 evidence: exact subject,
    # exact relation, open value, and an assignment. Its weakness is proof
    # directness, not eligibility.
    eligible_competitor = (
        f"Current profile record for {name}; {domain['label']}: {competing_value}."
    )

    wrong_relation_value = wrong_domain["values"][(index + 2) % len(wrong_domain["values"])]
    memories = [
        {
            "id": f"CV11-{stage[:3].upper()}-A-{index:03d}-rel",
            "speaker": "user",
            "text": relevant,
            "timestamp": base.timestamp(1),
        },
        {
            "id": f"CV11-{stage[:3].upper()}-A-{index:03d}-eligible-lexical-competitor",
            "speaker": "user",
            "text": eligible_competitor,
            "timestamp": base.timestamp(9),
        },
        {
            "id": f"CV11-{stage[:3].upper()}-A-{index:03d}-uncertain",
            "speaker": "user",
            "text": f"{name}'s {domain['label']} is perhaps {uncertain_value}.",
            "timestamp": base.timestamp(10),
        },
        {
            "id": f"CV11-{stage[:3].upper()}-A-{index:03d}-wrong-subject",
            "speaker": "user",
            "text": f"{wrong_name}'s {domain['label']} is {competing_value}.",
            "timestamp": base.timestamp(10),
        },
        {
            "id": f"CV11-{stage[:3].upper()}-A-{index:03d}-wrong-relation",
            "speaker": "user",
            "text": f"{name}'s {wrong_domain['label']} is {wrong_relation_value}.",
            "timestamp": base.timestamp(10),
        },
    ]
    rng.shuffle(memories)
    relevant_id = next(m["id"] for m in memories if m["text"] == relevant)
    return {
        "id": f"CV11-{stage.upper()}-A-{index:03d}",
        "designation": stage.upper(),
        "query": query,
        "memories": memories,
        "relevant_memory_ids": [relevant_id],
        "generator_metadata": {
            "query_grammar_family": family,
            "evidence_grammar_family": family,
            "structural_mechanism": base.STRUCTURAL_MECHANISM[family],
            "semantic_domain": domain["relation"],
            "template_provenance": f"candidate-v11:{stage}:{family}:answerable-lexical-rank-stress:v4",
            "polarity": "answerable_eligible_lexical_recency_competition",
        },
        "provenance": f"candidate-v11-fresh-generator-v4:{stage}:answerable:{index}",
    }


base.answerable_case = answerable_case


def generate(stage: str) -> dict[str, Any]:
    payload = base.generate(stage)
    payload["schema_version"] = "candidate-v11-benchmark-v4"
    payload["name"] = f"candidate-v11-{stage}-v4"
    payload["generator_design"] = (
        "stage-separated structural grammar mechanisms with lexically and recency-"
        "favored certification-compatible rank competition, corrected disjoint negatives, "
        "and adversarial blockers"
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
        "generator_revision": 4,
        "rank_stress": "eligible competitor with lexical and recency advantage",
    }, indent=2))


if __name__ == "__main__":
    main()
