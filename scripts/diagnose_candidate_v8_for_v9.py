from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from personal_state_engine.candidate_v2 import pse_candidate_v2_rank
from personal_state_engine.candidate_v8 import evidence_support_signature, pse_candidate_v8_rank

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "experiments/benchmarks/candidate-v8-protected-validation-v1.json"
OUT = ROOT / "docs/research/candidate-v9/candidate-v8-protected-failure-taxonomy.md"
ACCESS = ROOT / "results/candidate-v9/historical-diagnostic-access-v1.json"
JSON_OUT = ROOT / "results/candidate-v9/candidate-v8-protected-failure-taxonomy-v1.json"


def classify(cert: dict) -> str:
    clauses = cert.get("clauses", [])
    if not clauses:
        return "CLAUSE_SEGMENTATION_OR_EMPTY"
    blockers = [getattr(c, "blocker", None) for c in clauses if getattr(c, "blocker", None)]
    if blockers:
        return "SAFETY_BLOCKER_SCOPE:" + ",".join(sorted(set(blockers)))
    if not any(getattr(c, "subject_ok", False) for c in clauses):
        return "SUBJECT_OR_COREFERENCE"
    if not any(getattr(c, "relation_ok", False) for c in clauses):
        return "RELATION_REALIZATION"
    if not any(getattr(c, "value_bearing", False) for c in clauses):
        return "OBJECT_VALUE_BINDING"
    if not any(getattr(c, "temporal_ok", False) for c in clauses):
        return "TEMPORAL_COMPATIBILITY"
    return "MULTI_SIGNAL_OR_SEGMENTATION"


def main() -> int:
    data = json.loads(DATASET.read_text())
    failures = []
    for case in data["cases"]:
        rel = list(case.get("relevant_memory_ids", []))
        if not rel:
            continue
        v8 = pse_candidate_v8_rank(case, 5)
        if any(mid in v8 for mid in rel):
            continue
        v2 = pse_candidate_v2_rank(case, max(5, len(case["memories"])))
        sig = evidence_support_signature(case, v2)
        by_id = {m["id"]: m for m in case["memories"]}
        cert_by_id = {row["memory_id"]: row for row in sig["certifications"]}
        rel_rows = []
        cats = []
        for mid in rel:
            cert = cert_by_id.get(mid, {"memory_id": mid, "supported": False, "clauses": []})
            cat = classify(cert)
            cats.append(cat)
            rel_rows.append({
                "memory_id": mid,
                "memory_text": by_id[mid]["text"],
                "certification": {
                    "supported": cert.get("supported", False),
                    "clauses": [
                        {
                            "text": c.text,
                            "subject_ok": c.subject_ok,
                            "relation_ok": c.relation_ok,
                            "value_bearing": c.value_bearing,
                            "direct_assertion": c.direct_assertion,
                            "temporal_ok": c.temporal_ok,
                            "blocker": c.blocker,
                            "support_signals": list(c.support_signals),
                            "score": c.score,
                            "supported": c.supported,
                        }
                        for c in cert.get("clauses", [])
                    ],
                },
            })
        failures.append({
            "case_id": case["id"],
            "query": case["query"],
            "relevant_memories": rel_rows,
            "candidate_v2_ranking": v2,
            "candidate_v8_ranking": v8,
            "root_cause_category": "+".join(sorted(set(cats))),
            "predicted_by_preregistered_hypothesis": any(
                x.startswith(("RELATION_REALIZATION", "SUBJECT_OR_COREFERENCE", "OBJECT_VALUE_BINDING", "TEMPORAL_COMPATIBILITY", "SAFETY_BLOCKER_SCOPE", "MULTI_SIGNAL"))
                for x in cats
            ),
            "generalizable_change_required": True,
        })

    assert len(failures) == 4, f"Expected exactly 4 historical false abstentions; got {len(failures)}"
    now = datetime.now(timezone.utc).isoformat()
    payload = {
        "schema_version": "candidate-v9-v8-historical-failure-taxonomy-v1",
        "classification": "HISTORICAL_DIAGNOSTIC_ONLY",
        "historical_dataset_sha256": "087352b8ccc3a66790cd29953f41418e9fb296df60d10245b576bf41c49d55f8",
        "failure_count": len(failures),
        "failures": failures,
        "case_specific_hardcoding_prohibited": True,
        "opened_at": now,
    }
    JSON_OUT.write_text(json.dumps(payload, indent=2) + "\n")

    md = [
        "# Candidate-v8 Protected Failure Taxonomy (Historical Diagnostic Only)",
        "",
        "This surface is excluded from Candidate-v9 development, protected, confirmatory, and final evaluation. It was opened only after Candidate-v9 preregistration and diagnostic-access authorization.",
        "",
    ]
    for idx, row in enumerate(failures, 1):
        md += [
            f"## Failure {idx}: `{row['case_id']}`",
            "",
            f"- Query: `{row['query']}`",
            f"- Candidate-v2 ranking: `{row['candidate_v2_ranking']}`",
            f"- Candidate-v8 ranking: `{row['candidate_v8_ranking']}`",
            f"- Root cause: **{row['root_cause_category']}**",
            f"- Predicted by preregistered hypothesis: `{row['predicted_by_preregistered_hypothesis']}`",
            "",
        ]
        for mem in row["relevant_memories"]:
            md += [f"Relevant memory `{mem['memory_id']}`: `{mem['memory_text']}`", ""]
            for c in mem["certification"]["clauses"]:
                md += [
                    f"- Clause: `{c['text']}`",
                    f"  - subject_ok={c['subject_ok']}; relation_ok={c['relation_ok']}; value_bearing={c['value_bearing']}; direct_assertion={c['direct_assertion']}; temporal_ok={c['temporal_ok']}; blocker={c['blocker']}; score={c['score']}; supported={c['supported']}",
                ]
        md += ["", "Generalization constraint: fix only the typed mechanism; do not whitelist this case ID, subject, value, answer, or exact phrase.", ""]
    OUT.write_text("\n".join(md) + "\n")

    access = json.loads(ACCESS.read_text())
    access["opened_at"] = now
    access["semantic_payload_accessed"] = True
    access["failure_count_observed"] = len(failures)
    ACCESS.write_text(json.dumps(access, indent=2) + "\n")
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
