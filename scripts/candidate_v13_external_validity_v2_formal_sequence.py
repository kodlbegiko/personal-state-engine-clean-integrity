from __future__ import annotations

"""Authorized entrypoint for the one-process EV-A -> EV-B -> EV-C sequence."""

import importlib
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/candidate_v13_external_validity_v2_formal_runner.py"
CANDIDATE_MODULE = "personal_state_engine.candidate_v13"


def load_runner():
    spec = importlib.util.spec_from_file_location("pse_v2_formal_runner_core", RUNNER)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load formal runner core")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    # The process must enter the formal sequence candidate-blind. After the first
    # one-shot ledger is consumed, later authorized stages may reuse the module
    # already loaded by this same process without constituting a stage rerun.
    if CANDIDATE_MODULE in sys.modules:
        raise RuntimeError("CANDIDATE_FIREWALL_FAIL: Candidate-v13 preloaded before formal sequence")
    runner = load_runner()

    def authorized_ranker():
        module = importlib.import_module(CANDIDATE_MODULE)
        rank = getattr(module, "pse_candidate_v13_rank")
        return lambda runtime, k: list(rank(runtime, k))

    runner.formal_ranker = authorized_ranker
    return int(runner.main())


if __name__ == "__main__":
    raise SystemExit(main())
