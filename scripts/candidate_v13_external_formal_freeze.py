from __future__ import annotations

import hashlib
import importlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
D=ROOT/'docs/research/candidate-v13-external-validity'; R=ROOT/'results/candidate-v13-external-validity'
FREEZE=D/'freeze-manifest.json'; LEDGER=R/'formal-ledger.json'; CONTRACT=json.loads((R/'runtime-contract.json').read_text())
FILES=[
 'src/personal_state_engine/candidate_v13.py',
 'docs/research/candidate-v13-external-validity/preregistration.md',
 'docs/research/candidate-v13-external-validity/preregistration-lock.json',
 'docs/research/candidate-v13-external-validity/source-manifest.json',
 'docs/research/candidate-v13-external-validity/source-activation-v3.json',
 'docs/research/candidate-v13-external-validity/adapter-policy-v3.json',
 'docs/research/candidate-v13-external-validity/allocation-policy-v4.json',
 'docs/research/candidate-v13-external-validity/feasibility-algorithm-v1.json',
 'docs/research/candidate-v13-external-validity/stress-policy-v1.json',
 'docs/research/candidate-v13-external-validity/contamination-policy-v1.json',
 'docs/research/candidate-v13-external-validity/formal-thresholds-v1.json',
 'docs/research/candidate-v13-external-validity/anti-collapse-policy-v1.json',
 'docs/research/candidate-v13-external-validity/pre-ev-a-lock-v2.json',
 'results/candidate-v13-external-validity/evermembench-dynamic-qualification.json',
 'results/candidate-v13-external-validity/joint-feasibility.json',
 'results/candidate-v13-external-validity/contamination-audit.json',
 'results/candidate-v13-external-validity/runtime-contract.json',
 'results/candidate-v13-external-validity/ev-a-runtime.json',
 'results/candidate-v13-external-validity/ev-a-summary.json',
 'results/candidate-v13-external-validity/ev-a-integrity.json',
 'results/candidate-v13-external-validity/ev-a-gate.json',
 'scripts/candidate_v13_external_joint_feasibility.py',
 'scripts/candidate_v13_external_runtime_eval.py',
 'scripts/candidate_v13_external_formal_execute.py'
]
def sha(p:Path)->str: return hashlib.sha256(p.read_bytes()).hexdigest()
def main()->int:
    gate=json.loads((R/'ev-a-gate.json').read_text())
    assert gate['decision']=='EV_A_INTEGRITY_PASS_READY_FOR_FORMAL_FREEZE',gate
    assert gate['formal_freeze_authorized'] is True
    assert gate['candidate_v13_tuning_authorized'] is False
    hashes={}
    for rel in FILES:
        p=ROOT/rel; assert p.exists(),rel; hashes[rel]=sha(p)
    v2=importlib.import_module(CONTRACT['v2']['module']); v2path=Path(v2.__file__).resolve(); hashes[str(v2path.relative_to(ROOT))]=sha(v2path)
    assert hashes['src/personal_state_engine/candidate_v13.py']=='b602b55428b365d8e925301a1fc8c4bb2a3a0d73d0590228ea48cc7a62be8838'
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    freeze={
      'schema_version':'candidate-v13-external-validity-freeze-manifest-v1',
      'status':'FORMAL_EVALUATION_FROZEN_AFTER_EV_A_INTEGRITY_PASS',
      'freeze_commit_parent':commit,
      'created_utc':datetime.now(timezone.utc).isoformat(),
      'candidate_v13_external_performance_observed':True,
      'ev_a_integrity_pass':True,
      'candidate_v13_tuning_after_ev_a':False,
      'source_gold_allocation_changes_after_ev_a':False,
      'files_sha256':dict(sorted(hashes.items())),
      'formal_stage_limits':{'ev_b':1,'ev_c':1},
      'formal_execution_semantics':'Formal stage bullet is consumed at execution start, before Candidate-v13 sees the first stage case. No rerun after algorithmic FAIL or successful execution.',
      'ev_b_selection_digest':json.loads((R/'joint-feasibility.json').read_text())['stages']['ev_b']['selected_base_id_digest'],
      'ev_c_selection_digest':json.loads((R/'joint-feasibility.json').read_text())['stages']['ev_c']['selected_base_id_digest']
    }
    FREEZE.write_text(json.dumps(freeze,indent=2,sort_keys=True)+'\n')
    if LEDGER.exists():
        existing=json.loads(LEDGER.read_text()); assert existing=={'ev_b':0,'ev_c':0,'terminal_state':None},existing
    else:
        LEDGER.write_text(json.dumps({'ev_b':0,'ev_c':0,'terminal_state':None},indent=2,sort_keys=True)+'\n')
    return 0
if __name__=='__main__': raise SystemExit(main())
