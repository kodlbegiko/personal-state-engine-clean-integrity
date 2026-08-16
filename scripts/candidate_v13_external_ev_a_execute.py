from __future__ import annotations

import json
from pathlib import Path

from candidate_v13_external_runtime_eval import evaluate

ROOT=Path(__file__).resolve().parents[1]
RESULT_DIR=ROOT/'results/candidate-v13-external-validity'

def main()->int:
    result=evaluate('ev_a',execute=True)
    integrity=result['integrity']
    summary={k:v for k,v in result.items() if k not in {'integrity'}}
    summary['ev_a_role']='evaluator/infrastructure calibration audit; Candidate-v13 performance is descriptive and does not authorize tuning or threshold changes'
    summary['algorithmic_performance_used_for_source_or_rule_change']=False
    integ={
      'schema_version':'candidate-v13-external-ev-a-integrity-v1',
      'stage':'ev_a',
      'candidate_v13_external_performance_observed':True,
      'candidate_v13_source_sha256':result['candidate_v13_source_sha256'],
      'selection_digest':result['selection_digest'],
      'case_counts':result['case_counts'],
      **integrity,
      'all_integrity_pass': bool(integrity['candidate_source_invariant_pass'] and integrity['determinism_pass'] and integrity['metadata_firewall_pass']),
      'raw_case_payload_persisted':False,
      'source_or_gold_rules_changed_from_ev_a_performance':False
    }
    (RESULT_DIR/'ev-a-summary.json').write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    (RESULT_DIR/'ev-a-integrity.json').write_text(json.dumps(integ,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    return 0 if integ['all_integrity_pass'] else 2

if __name__=='__main__': raise SystemExit(main())
