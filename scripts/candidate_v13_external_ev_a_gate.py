from __future__ import annotations

import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
R=ROOT/'results/candidate-v13-external-validity'
OUT=R/'ev-a-gate.json'

def main()->int:
    integrity=json.loads((R/'ev-a-integrity.json').read_text())
    summary=json.loads((R/'ev-a-summary.json').read_text())
    violations={
      'candidate_source_violations':int(integrity.get('candidate_source_violations',-1)),
      'determinism_violations':int(integrity.get('determinism_violations',-1)),
      'metadata_firewall_violations':int(integrity.get('metadata_firewall_violations',-1)),
    }
    pass_integrity=(
      integrity.get('candidate_v13_external_performance_observed') is True
      and integrity.get('all_integrity_pass') is True
      and all(v==0 for v in violations.values())
      and int(summary.get('case_counts',{}).get('total',-1))==384
      and summary.get('algorithmic_performance_used_for_source_or_rule_change') is False
    )
    out={
      'schema_version':'candidate-v13-external-ev-a-gate-v1',
      'candidate_v13_external_performance_observed':bool(integrity.get('candidate_v13_external_performance_observed')),
      'case_count':int(summary.get('case_counts',{}).get('total',-1)),
      'integrity_violations':violations,
      'all_integrity_pass':bool(integrity.get('all_integrity_pass')),
      'performance_used_for_source_or_rule_change':bool(summary.get('algorithmic_performance_used_for_source_or_rule_change')),
      'descriptive_metrics':summary.get('metrics',{}),
      'decision':'EV_A_INTEGRITY_PASS_READY_FOR_FORMAL_FREEZE' if pass_integrity else 'EV_A_INTEGRITY_FAIL_BLOCK_FORMAL',
      'formal_freeze_authorized':pass_integrity,
      'candidate_v13_tuning_authorized':False,
      'source_gold_allocation_change_authorized':False,
    }
    OUT.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    return 0 if pass_integrity else 2

if __name__=='__main__': raise SystemExit(main())
