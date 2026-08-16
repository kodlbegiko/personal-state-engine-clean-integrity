from __future__ import annotations

import hashlib
import importlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
OUT=ROOT/'docs/research/candidate-v13-external-validity/pre-ev-a-lock-v2.json'
CONTRACT=json.loads((ROOT/'results/candidate-v13-external-validity/runtime-contract.json').read_text())
FILES=[
 'src/personal_state_engine/candidate_v13.py',
 'docs/research/candidate-v13-external-validity/preregistration.md',
 'docs/research/candidate-v13-external-validity/source-activation-v3.json',
 'docs/research/candidate-v13-external-validity/adapter-policy-v3.json',
 'docs/research/candidate-v13-external-validity/allocation-policy-v4.json',
 'docs/research/candidate-v13-external-validity/feasibility-algorithm-v1.json',
 'docs/research/candidate-v13-external-validity/stress-policy-v1.json',
 'docs/research/candidate-v13-external-validity/contamination-policy-v1.json',
 'results/candidate-v13-external-validity/evermembench-dynamic-qualification.json',
 'results/candidate-v13-external-validity/joint-feasibility.json',
 'results/candidate-v13-external-validity/contamination-audit.json',
 'results/candidate-v13-external-validity/runtime-contract.json',
 'results/candidate-v13-external-validity/ev-a-runtime.json',
 'scripts/candidate_v13_external_joint_feasibility.py',
 'scripts/candidate_v13_external_runtime_eval.py',
 'scripts/candidate_v13_external_ev_a_execute.py'
]
def sha(p:Path)->str: return hashlib.sha256(p.read_bytes()).hexdigest()
def main()->int:
    hashes={rel:sha(ROOT/rel) for rel in FILES}
    v2=importlib.import_module(CONTRACT['v2']['module']); v2path=Path(v2.__file__).resolve(); hashes[str(v2path.relative_to(ROOT))]=sha(v2path)
    old=json.loads((ROOT/'docs/research/candidate-v13-external-validity/pre-ev-a-lock.json').read_text())
    out={
      'schema_version':'candidate-v13-external-pre-ev-a-lock-v2',
      'status':'FINAL_LOCK_BEFORE_FIRST_EXTERNAL_CANDIDATE_V13_EXECUTION',
      'supersedes':'pre-ev-a-lock.json only to add the non-overwriting EV-A wrapper; no source/gold/allocation/evaluator rule changed',
      'created_utc':datetime.now(timezone.utc).isoformat(),
      'candidate_v13_external_performance_observed':False,
      'formal_ev_b_or_ev_c_materialized':False,
      'candidate_v13_expected_sha256':'b602b55428b365d8e925301a1fc8c4bb2a3a0d73d0590228ea48cc7a62be8838',
      'files_sha256':dict(sorted(hashes.items())),
      'ev_a_selection_digest':old['ev_a_selection_digest'],
      'joint_feasibility_global_digest':old['joint_feasibility_global_digest'],
      'authorized_first_external_entrypoint':'scripts/candidate_v13_external_ev_a_execute.py',
      'immutability_after_first_external_output':old['immutability_after_first_external_output']
    }
    assert out['files_sha256']['src/personal_state_engine/candidate_v13.py']==out['candidate_v13_expected_sha256']
    OUT.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    return 0
if __name__=='__main__': raise SystemExit(main())
