from __future__ import annotations

"""Authorized v3 formal sequence entry point. No static Candidate import."""

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/candidate_v13_external_validity_v3_formal_runner.py"


def main() -> int:
    if "personal_state_engine.candidate_v13" in sys.modules:
        raise RuntimeError("CANDIDATE_FIREWALL_FAIL: Candidate already imported before formal runner")
    spec = importlib.util.spec_from_file_location("pse_v3_authorized_formal_runner", RUNNER)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load v3 formal runner")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["pse_v3_authorized_formal_runner"] = mod
    spec.loader.exec_module(mod)
    return int(mod.execute())


if __name__ == "__main__":
    raise SystemExit(main())
