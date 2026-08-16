from __future__ import annotations

"""Candidate-agnostic evaluator wrapper for External Validity v3."""

import importlib.util
import sys
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
V2 = ROOT / "scripts/candidate_v13_external_validity_v2_evaluator.py"


def _load():
    name = "pse_v3_reused_candidate_agnostic_evaluator_core"
    spec = importlib.util.spec_from_file_location(name, V2)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load candidate-agnostic evaluator core")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def evaluate(stage: str, cases: list[dict[str, Any]], ranker: Callable[[dict[str, Any], int], list[str]], policy: dict[str, Any]) -> dict[str, Any]:
    result = _load().evaluate(stage, cases, ranker, policy)
    result["schema_version"] = "candidate-v13-external-validity-v3-stage-summary-v1"
    result["evaluator_lineage"] = "v3 wrapper over frozen candidate-agnostic v2 metric implementation; stage names/thresholds supplied by v3 preregistration"
    return result
