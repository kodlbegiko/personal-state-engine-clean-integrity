from __future__ import annotations

import hashlib
import importlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
OUT=ROOT/'docs/research/candidate-v13-external-validity/pre-ev-a-lock.json'
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
 'scripts/candidate_v13_external_runtime_contract_probe.py',
 'scripts/candidate_v13_external_runtime_eval.py'
]

def sha(path:Path)->str: return hashlib.sha256(path.read_bytes()).hexdigest()

def main()->int:
    files={}
    for rel in FILES:
        p=ROOT/rel
        if not p.exists(): raise FileNotFoundError(rel)
        files[rel]=sha(p)
    v2mod=importlib.import_module(CONTRACT['v2']['module']); v2path=Path(v2mod.__file__).resolve(); files[str(v2path.relative_to(ROOT))]=sha(v2path)
    result={
      'schema_version':'candidate-v13-external-pre-ev-a-lock-v1',
      'status':'LOCKED_BEFORE_FIRST_EXTERNAL_CANDIDATE_V13_EXECUTION',
      'created_utc':datetime.now(timezone.utc).isoformat(),
      'candidate_v13_external_performance_observed':False,
      'formal_ev_b_or_ev_c_materialized':False,
      'candidate_v13_expected_sha256':'b602b55428b365d8e925301a1fc8c4bb2a3a0d73d0590228ea48cc7a62be8838',
      'files_sha256':dict(sorted(files.items())),
      'source_set':['personamem-v2','locomo','sgd-carryover','longmemeval-cleaned','evermembench-dynamic'],
      'ev_a_selection_digest':json.loads((ROOT/'results/candidate-v13-external-validity/ev-a-runtime.json').read_text())['selection_digest'],
      'joint_feasibility_global_digest':json.loads((ROOT/'results/candidate-v13-external-validity/joint-feasibility.json').read_text())['global_selected_base_id_digest'],
      'immutability_after_first_external_output':'Source set, source/domain mapping, gold mapping, structural-family rules, stage sizes, thresholds and allocation rules may not change after EV-A first external output. Only objective evaluator infrastructure defects may be documented; no performance-responsive tuning is allowed.'
    }
    assert result['files_sha256']['src/personal_state_engine/candidate_v13.py']==result['candidate_v13_expected_sha256']
    OUT.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    return 0

if __name__=='__main__': raise SystemExit(main())
