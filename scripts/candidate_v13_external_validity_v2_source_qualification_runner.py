from __future__ import annotations

"""Rate-limit-safe runner for Candidate-v13 External Validity v2 source qualification."""

import fnmatch
import importlib.util
import json
import re
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any

from huggingface_hub import HfApi, snapshot_download

ROOT = Path(__file__).resolve().parents[1]
QUALIFIER = ROOT / "scripts/candidate_v13_external_validity_v2_source_qualification.py"


def load_qualifier():
    spec = importlib.util.spec_from_file_location("pse_v2_source_qualifier", QUALIFIER)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load v2 source qualifier")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def strict_evermem_text(msg: dict[str, Any]) -> str:
    """Use the schema-manifest-verified EverMemBench dialogues field only."""
    value = msg.get("dialogue")
    if not isinstance(value, str) or not value.strip():
        raise RuntimeError("EverMem verified 'dialogue' field missing or empty")
    return value.strip()


class NonEmptyDialogueDatasetView:
    """Normalize only schema-native missing group values.

    HF Arrow represents absent struct members as ``None`` and some source rows
    contain explicit empty lists. Both mean "this group is absent". Any other
    non-list value is preserved so the strict downstream parser fails loudly.
    """

    def __init__(self, dataset: Any):
        self._dataset = dataset
        self.column_names = dataset.column_names
        self.features = dataset.features

    def __len__(self) -> int:
        return len(self._dataset)

    def __iter__(self):
        for row in self._dataset:
            out = dict(row)
            groups = out.get("dialogues")
            if isinstance(groups, dict):
                out["dialogues"] = {
                    key: value
                    for key, value in groups.items()
                    if value is not None and not (isinstance(value, list) and len(value) == 0)
                }
            yield out


def bind_schema_verified_evermem(mod: Any) -> None:
    original_load_dataset = mod.load_dataset

    def load_dataset_verified(*args: Any, **kwargs: Any):
        dataset = original_load_dataset(*args, **kwargs)
        config = args[1] if len(args) > 1 else kwargs.get("name")
        if config == "dialogues":
            return NonEmptyDialogueDatasetView(dataset)
        return dataset

    mod.load_dataset = load_dataset_verified
    mod.extract_message_text = strict_evermem_text


def fast_rhelm(mod, legacy, bases: list[dict[str, Any]], schema_manifest: dict[str, Any]) -> dict[str, Any]:
    api = HfApi()
    repo = mod.SOURCE_CONTRACT["reserve_sources"]["rhelm"]["dataset"]
    info = api.dataset_info(repo)
    rev = info.sha
    if not rev:
        raise RuntimeError("RHELM revision missing")
    card = info.card_data or {}
    license_value = str(card.get("license") or "").casefold()

    with tempfile.TemporaryDirectory(prefix="pse-rhelm-qa-") as td:
        snap = Path(snapshot_download(
            repo_id=repo,
            repo_type="dataset",
            revision=rev,
            local_dir=td,
            allow_patterns=["QA_final/*.jsonl"],
            max_workers=1,
        ))
        qa_files = sorted((snap / "QA_final").glob("*.jsonl"))
        if not qa_files:
            raise RuntimeError("RHELM QA files missing")

        first_row = None
        for line in qa_files[0].read_text(encoding="utf-8").splitlines():
            if line.strip():
                first_row = json.loads(line)
                break
        if not isinstance(first_row, dict):
            raise RuntimeError("RHELM first QA row must be object")
        required = {
            "id", "question", "answer", "question_date", "question_type",
            "supporting_evidence", "characteristics",
        }
        missing = required - set(first_row)
        if missing:
            raise RuntimeError(f"RHELM QA schema missing fields: {sorted(missing)}")

        repo_files = list(api.list_repo_files(repo_id=repo, repo_type="dataset", revision=rev))
        schema_manifest["rhelm:qa-jsonl"] = {
            "top_level_type": "JSONL",
            "record_type": "dict",
            "record_keys": sorted(first_row.keys()),
            "qa_file_count": len(qa_files),
            "repository_file_count": len(repo_files),
            "source_resolution_mode": "immutable-repository-file-index",
        }

        eligible = Counter()
        unresolved = Counter()
        total = 0
        seen_queries: set[str] = set()

        for qafile in qa_files:
            persona = re.sub(r"_all_validated$", "", re.sub(r"^low_score_qa_", "", qafile.stem))
            source_paths = [
                p for p in repo_files
                if p.startswith(f"conversations/{persona}/")
                or p.startswith(f"emails/{persona}/")
                or p.startswith(f"attachments/{persona}/")
            ]
            if not source_paths:
                unresolved["persona_source_directory_missing"] += 1
                continue

            for line in qafile.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                total += 1
                row = json.loads(line)
                q = str(row.get("question") or "").strip()
                a = str(row.get("answer") or "").strip()
                refs = row.get("supporting_evidence")
                if isinstance(refs, str):
                    refs = [refs] if refs.strip() else []
                if not q or not a or not isinstance(refs, list) or not refs:
                    unresolved["missing_q_a_or_evidence"] += 1
                    continue
                nq = mod.norm(q)
                if nq in seen_queries:
                    unresolved["normalized_query_duplicate_within_source"] += 1
                    continue
                domain = mod.classify_rhelm_domain(q, a, refs)
                if domain not in {"D6", "D7"}:
                    unresolved["not_d6_d7"] += 1
                    continue

                resolved_refs: list[str] = []
                ok = True
                for rawref in refs:
                    ref = str(rawref).strip()
                    if not ref:
                        unresolved["empty_reference"] += 1
                        ok = False
                        break
                    matches: list[str] = []
                    token = ref.split(":", 1)[0]
                    if any(ext in token.casefold() for ext in (".md", ".html", ".txt", ".json")):
                        matches = [
                            p for p in source_paths
                            if fnmatch.fnmatch(Path(p).name, token) or fnmatch.fnmatch(p, token)
                        ]
                    if not matches:
                        dm = mod.DATE_REF_RE.search(ref)
                        if dm:
                            date = dm.group("date")
                            matches = [
                                p for p in source_paths
                                if p.startswith(f"conversations/{persona}/") and date in p
                            ]
                    matches = sorted(set(matches))
                    if len(matches) != 1:
                        unresolved["unresolved_or_ambiguous_reference"] += 1
                        ok = False
                        break
                    resolved_refs.append(f"source-ref:{matches[0]}::{ref}")

                if not ok or not resolved_refs:
                    continue
                seen_queries.add(nq)
                legacy.add(
                    bases,
                    "rhelm",
                    f"rhelm:{persona}:{row.get('id', total)}",
                    q,
                    persona,
                    str(row.get("question_type") or "memory"),
                    resolved_refs,
                    domain,
                    temporal=str(row.get("question_type") or "").casefold() == "temporal",
                )
                eligible[domain] += 1

        return {
            "dataset": repo,
            "revision": rev,
            "license": license_value,
            "qa_rows": total,
            "eligible_by_domain_pre_global_dedup": dict(sorted(eligible.items())),
            "unresolved": dict(sorted(unresolved.items())),
            "gold_rule": "supporting_evidence must map to exactly one pinned repository path; source payload fetched only at materialization",
            "source_payload_mass_downloaded": False,
            "candidate_blind": True,
        }


def main() -> int:
    mod = load_qualifier()
    bind_schema_verified_evermem(mod)
    mod.rhelm = lambda legacy, bases, schema_manifest: fast_rhelm(mod, legacy, bases, schema_manifest)
    return int(mod.main())


if __name__ == "__main__":
    raise SystemExit(main())
