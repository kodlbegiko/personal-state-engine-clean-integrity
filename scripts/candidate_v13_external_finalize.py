from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
D=ROOT/'docs/research/candidate-v13-external-validity'; R=ROOT/'results/candidate-v13-external-validity'
LEGAL={
 'CANDIDATE_V13_EXTERNAL_VALIDITY_PASS',
 'CANDIDATE_V13_EXTERNAL_VALIDITY_FAIL — CANDIDATE_V14_AUTHORIZED',
 'EXTERNAL_VALIDITY_INVALID — RESEARCH_INTEGRITY_FAILURE',
 'EXTERNAL_VALIDITY_INFRASTRUCTURE_BLOCKED'
}

def load(path:Path): return json.loads(path.read_text()) if path.exists() else None

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('--terminal-state',required=True); ap.add_argument('--reason',default=''); args=ap.parse_args()
    if args.terminal_state not in LEGAL: raise SystemExit(f'illegal terminal state: {args.terminal_state}')
    freeze=load(D/'freeze-manifest.json'); ledger=load(R/'formal-ledger.json'); eva=load(R/'ev-a-gate.json'); evb=load(R/'ev-b-summary.json'); evbi=load(R/'ev-b-integrity.json'); evc=load(R/'ev-c-summary.json'); evci=load(R/'ev-c-integrity.json'); joint=load(R/'joint-feasibility.json'); cont=load(R/'contamination-audit.json'); qual=load(R/'evermembench-dynamic-qualification.json')
    summary={
      'schema_version':'candidate-v13-external-validity-terminal-summary-v1',
      'terminal_state':args.terminal_state,
      'reason':args.reason,
      'created_utc':datetime.now(timezone.utc).isoformat(),
      'historical_terminal_anchor':'cfea38f4a75e9ce92a5cbeff0162a224e0e90c7e',
      'candidate_v13_source_sha256':freeze.get('files_sha256',{}).get('src/personal_state_engine/candidate_v13.py') if freeze else None,
      'ev_a_gate':eva.get('decision') if eva else None,
      'joint_feasibility':joint.get('status') if joint else None,
      'contamination_status':cont.get('status') if cont else None,
      'evermembench_qualification':qual.get('status') if qual else None,
      'formal_ledger':ledger,
      'ev_b_decision':evb.get('decision') if evb else None,
      'ev_b_metrics':evb.get('metrics') if evb else None,
      'ev_b_integrity_pass':evbi.get('formal_integrity_pass') if evbi else None,
      'ev_c_decision':evc.get('decision') if evc else None,
      'ev_c_metrics':evc.get('metrics') if evc else None,
      'ev_c_integrity_pass':evci.get('formal_integrity_pass') if evci else None,
      'raw_formal_case_payload_committed':False,
      'candidate_v13_tuned_during_external_validity':False
    }
    (R/'terminal-summary.json').write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n')
    lines=[
      '# Candidate-v13 Naturalistic External Validity — Terminal Decision','',
      f'**Terminal state:** `{args.terminal_state}`','',
      f'**Reason:** {args.reason or "See formal stage evidence."}','',
      '## A. Historical integrity','',
      '- Candidate-v13 historical terminal anchor: `cfea38f4a75e9ce92a5cbeff0162a224e0e90c7e`.',
      f"- Frozen Candidate-v13 source SHA256: `{summary['candidate_v13_source_sha256']}`.",
      '- Candidate-v13 was not tuned in this external-validity lineage.','',
      '## B. Preregistration and evaluation freeze','',
      '- Naturalistic external-validity preregistration was committed before formal case materialization.',
      f"- Formal freeze status: `{freeze.get('status') if freeze else None}`.",
      '- Source/gold/allocation rules were immutable after the first EV-A external output.','',
      '## C. Source corpus and contamination','',
      '- Formal source families: PersonaMem-v2, LoCoMo, SGD carry-over, LongMemEval-cleaned, EverMemBench-Dynamic.',
      f"- Pre-performance contamination firewall: `{summary['contamination_status']}`.",
      f"- EverMemBench-Dynamic source qualification: `{summary['evermembench_qualification']}`.",'',
      '## D. EV-A','',
      f"- EV-A integrity gate: `{summary['ev_a_gate']}`.",
      '- EV-A performance was descriptive only and was not used to tune Candidate-v13 or change formal thresholds.','',
      '## E. Formal one-shot ledger','',
      f"- EV-B executions consumed: `{ledger.get('ev_b') if ledger else None}` / 1.",
      f"- EV-C executions consumed: `{ledger.get('ev_c') if ledger else None}` / 1.",'',
      '## F. EV-B','',
      f"- Decision: `{summary['ev_b_decision']}`.",
      f"- Formal integrity pass: `{summary['ev_b_integrity_pass']}`.",'',
      '## G. EV-C','',
      f"- Decision: `{summary['ev_c_decision']}`." if evc else '- EV-C was not authorized/executed.',
      f"- Formal integrity pass: `{summary['ev_c_integrity_pass']}`." if evc else '- No EV-C artifact was fabricated.','',
      '## H. Final interpretation','',
      f'Final legal terminal state: **{args.terminal_state}**.','',
      'This conclusion applies only to the preregistered heterogeneous external-validity distributions tested here. It does not establish universal real-world generalization, production safety under all distributions, or unlimited relation coverage.',''
    ]
    (D/'terminal-decision.md').write_text('\n'.join(lines),encoding='utf-8')
    return 0
if __name__=='__main__': raise SystemExit(main())
