from __future__ import annotations

"""Authoritative v3 qualification entry point.

Binds indexed production materialization and the v3 contamination audit into the
candidate-blind qualification, then enriches only aggregate evidence. Protected
individual assignments are never persisted.
"""

import hashlib
import importlib.util
import json
import sys
import urllib.request
from pathlib import Path
from typing import Any

from huggingface_hub import HfApi

ROOT = Path(__file__).resolve().parents[1]
BASE_QUAL = ROOT / "scripts/candidate_v13_external_validity_v3_infrastructure_qualification.py"
MATERIALIZER = ROOT / "scripts/candidate_v13_external_validity_v3_materializer.py"
CONTAMINATION = ROOT / "scripts/candidate_v13_external_validity_v3_contamination.py"
OUT = ROOT / "results/candidate-v13-external-validity-v3"
DOC = ROOT / "docs/research/candidate-v13-external-validity-v3"
V2_SOURCE_MANIFEST = ROOT / "docs/research/candidate-v13-external-validity-v2/source-manifest-v2.json"
V2_SOURCE_QUAL = ROOT / "results/candidate-v13-external-validity-v2/source-qualification.json"


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def transform_distribution(dist: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in dist.items():
        if key == "count":
            out[key] = value
        elif isinstance(value, (int, float)):
            out[key] = max(5.0, float(value) + 4.0)
        else:
            out[key] = value
    return out


def enrich_gold_audit() -> None:
    path = OUT / "gold-cardinality-audit.json"
    audit = read_json(path)
    distributions = audit.get("distributions", {})
    audit["gold_payload_count_definition"] = "source-native mechanically resolved gold memory units; aggregate gold_payload_count equals aggregate gold_count"
    audit["estimated_runtime_memory_requirement"] = {
        "overall": transform_distribution(distributions.get("overall", {})),
        "by_source": {k: transform_distribution(v) for k, v in distributions.get("by_source", {}).items()},
        "by_domain": {k: transform_distribution(v) for k, v in distributions.get("by_domain", {}).items()},
        "by_eligible_family": {k: transform_distribution(v) for k, v in distributions.get("by_eligible_family", {}).items()},
    }
    max_gold = float(distributions.get("overall", {}).get("max", 0))
    audit["runtime_policy_formula"] = "max(5, gold_count + 4)"
    audit["global_infrastructure_safety_ceiling"] = 100
    audit["cases_known_to_exceed_runtime_ceiling"] = 0 if max_gold <= 96 else "UNRESOLVED"
    audit["candidate_v13_imported"] = False
    audit["candidate_v13_invoked"] = False
    write_json(path, audit)


def hf_license(repo: str, revision: str) -> tuple[str, str]:
    info = HfApi().dataset_info(repo, revision=revision)
    if str(info.sha) != revision:
        raise RuntimeError(f"immutable revision mismatch for {repo}: {info.sha} != {revision}")
    card = info.card_data
    card_dict: dict[str, Any] = {}
    if card is not None and hasattr(card, "to_dict"):
        card_dict = dict(card.to_dict())
    elif isinstance(card, dict):
        card_dict = dict(card)
    license_value = card_dict.get("license") if card_dict else getattr(card, "license", None)
    if isinstance(license_value, list):
        license_value = ",".join(sorted(str(x) for x in license_value))
    license_text = str(license_value or "").strip().casefold()
    if not license_text:
        raise RuntimeError(f"license metadata missing for pinned dataset {repo}@{revision}")
    return license_text, str(info.sha)


def github_license(repo: str, revision: str) -> tuple[str, str, str]:
    data = None
    used_path = None
    last_error: Exception | None = None
    for filename in ("LICENSE", "LICENSE.txt", "LICENSE.md"):
        url = f"https://raw.githubusercontent.com/{repo}/{revision}/{filename}"
        try:
            data = urllib.request.urlopen(url, timeout=30).read()
            used_path = filename
            break
        except Exception as exc:
            last_error = exc
    if data is None or used_path is None:
        raise RuntimeError(f"pinned license file unavailable for {repo}@{revision}: {last_error}")
    text = data.decode("utf-8", errors="replace").casefold()
    if "attribution-noncommercial 4.0 international" in text:
        license_value = "cc-by-nc-4.0"
    elif "attribution-sharealike 4.0 international" in text:
        license_value = "cc-by-sa-4.0"
    elif "apache license" in text and "version 2.0" in text:
        license_value = "apache-2.0"
    elif "mit license" in text or "permission is hereby granted, free of charge" in text:
        license_value = "mit"
    elif "bsd" in text and "redistribution and use" in text:
        license_value = "bsd"
    else:
        raise RuntimeError(f"unable to mechanically classify pinned license for {repo}@{revision}")
    return license_value, hashlib.sha256(data).hexdigest(), used_path


def enrich_source_manifest() -> None:
    materializer = load("pse_v3_manifest_materializer", MATERIALIZER)
    revisions = materializer.SOURCE_REVISIONS
    v2_manifest = read_json(V2_SOURCE_MANIFEST)
    v2_qual = read_json(V2_SOURCE_QUAL)
    by_old = {str(x["source_id"]): x for x in v2_manifest.get("sources", [])}
    baseline_hashes = v2_qual["sources"]["baseline-four-source-pool"].get("source_hashes", {})
    hf_repos = {
        "personamem-v2": "bowen-upenn/PersonaMem-v2",
        "longmemeval-cleaned": "xiaowu0162/longmemeval-cleaned",
        "evermembench-dynamic": "EverMind-AI/EverMemBench-Dynamic",
        "rhelm": "microsoft/RHELM",
    }
    gh_repos = {
        "locomo": "snap-research/locomo",
        "sgd-carryover": "google-research-datasets/dstc8-schema-guided-dialogue",
    }
    source_hash_key = {
        "personamem-v2": "personamem-v2",
        "longmemeval-cleaned": "longmemeval-cleaned",
        "locomo": "locomo",
        "sgd-carryover": "sgd-archive",
    }
    sources = []
    for source_id, revision in revisions.items():
        old = by_old.get(source_id, {})
        if source_id in hf_repos:
            license_value, revision_confirmation = hf_license(hf_repos[source_id], revision)
            identity = {"dataset": hf_repos[source_id]}
            license_evidence = {"pinned_dataset_revision_confirmed": revision_confirmation}
        elif source_id in gh_repos:
            license_value, license_file_sha, license_path = github_license(gh_repos[source_id], revision)
            identity = {"repository": gh_repos[source_id]}
            license_evidence = {"pinned_license_file": license_path, "pinned_license_file_sha256": license_file_sha}
        else:
            raise RuntimeError(f"unknown source license resolver: {source_id}")
        content_hash = baseline_hashes.get(source_hash_key.get(source_id, ""))
        sources.append({
            "source_id": source_id,
            **identity,
            "revision": revision,
            "license": license_value,
            "schema_version": "source-native-schema-requalified-v3",
            "adapter_version": "candidate-v13-external-validity-v3-pinned-adapter-v1",
            "adapter_dependency": old.get("dataset_name") or old.get("source_type") or "pinned-v2-qualified-loader",
            "qualification_status": "PASS",
            "content_sha256": content_hash,
            "content_hash_policy": "exact pinned payload hash retained where v2 qualification produced one; otherwise immutable repository revision plus qualification/runtime digests",
            "role": "preregistered_reserve" if source_id == "rhelm" else "primary",
            "gold_rule": old.get("gold_rule"),
            **license_evidence,
        })
    write_json(DOC / "source-manifest-v3.json", {
        "schema_version": "candidate-v13-external-validity-v3-source-manifest-v2",
        "status": "QUALIFIED_IMMUTABLE_REVISIONS_PINNED_PRE_FREEZE",
        "candidate_v13_imported": False,
        "candidate_v13_invoked": False,
        "runtime_load_policy": "load/download directly from the exact qualified immutable revision",
        "sources": sources,
    })


def main() -> int:
    qual = load("pse_v3_base_infrastructure_qualification", BASE_QUAL)
    qual.CORE_PATH = MATERIALIZER
    qual.STRICT_CONTAM = CONTAMINATION
    code = int(qual.main())
    if code != 0:
        return code
    enrich_gold_audit()
    enrich_source_manifest()
    infra_path = OUT / "infrastructure-qualification.json"
    infra = read_json(infra_path)
    infra["source_manifest_enriched_v3"] = True
    infra["gold_cardinality_runtime_requirement_enriched_v3"] = True
    infra["candidate_v13_imported"] = False
    infra["candidate_v13_invoked"] = False
    write_json(infra_path, infra)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
