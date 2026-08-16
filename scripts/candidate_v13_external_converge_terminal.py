from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
D=ROOT/'docs/research/candidate-v13-external-validity'; R=ROOT/'results/candidate-v13-external-validity'
BRANCH='research/candidate-v13-naturalistic-external-validity'

def run(*args:str,check:bool=True)->subprocess.CompletedProcess[str]:
    return subprocess.run(list(args),cwd=ROOT,text=True,check=check,capture_output=True)

def git_sync()->None:
    run('git','fetch','origin',BRANCH)
    run('git','reset','--hard',f'origin/{BRANCH}')

def load(p:Path): return json.loads(p.read_text())

def commit_push(message:str,paths:list[str])->None:
    run('git','config','user.name','github-actions[bot]'); run('git','config','user.email','41898282+github-actions[bot]@users.noreply.github.com')
    run('git','add',*paths)
    cp=run('git','diff','--cached','--quiet',check=False)
    if cp.returncode==0: return
    run('git','commit','-m',message); run('git','push','origin',f'HEAD:{BRANCH}')

def verify_freeze()->dict:
    f=load(D/'freeze-manifest.json')
    for rel,expected in f['files_sha256'].items():
        p=ROOT/rel
        if not p.exists() or hashlib.sha256(p.read_bytes()).hexdigest()!=expected: raise RuntimeError(f'frozen hash mismatch: {rel}')
    return f

def wait_for_b(max_seconds:int=600)->str:
    deadline=time.time()+max_seconds
    while True:
        git_sync()
        ledger=load(R/'formal-ledger.json')
        if ledger.get('terminal_state') is not None: return 'TERMINAL'
        b=R/'ev-b-summary.json'
        if ledger.get('ev_b')==1 and b.exists():
            decision=load(b).get('decision')
            if decision=='EV_B_PASS — EV_C_AUTHORIZED' and ledger.get('ev_c')==0: return 'EV_C_AUTHORIZED'
            if decision in {'CANDIDATE_V13_EXTERNAL_VALIDITY_FAIL — CANDIDATE_V14_AUTHORIZED','EXTERNAL_VALIDITY_INVALID — RESEARCH_INTEGRITY_FAILURE'}: return 'TERMINAL_PENDING_FINALIZER'
        if ledger.get('ev_c')==1: return 'EV_C_ALREADY_CONSUMED'
        if time.time()>=deadline: return 'NOT_READY'
        time.sleep(10)

def write_status(mode:str)->None:
    (R/'convergence-status.json').write_text(json.dumps({'schema_version':'candidate-v13-external-convergence-status-v1','mode':mode,'ledger':load(R/'formal-ledger.json')},indent=2,sort_keys=True)+'\n')
    commit_push('candidate-v13 external validity: record terminal convergence status',['results/candidate-v13-external-validity/convergence-status.json'])

def main()->int:
    mode=wait_for_b()
    if mode in {'TERMINAL','EV_C_ALREADY_CONSUMED','NOT_READY'}:
        write_status(mode); return 0
    if mode=='TERMINAL_PENDING_FINALIZER':
        ledger=load(R/'formal-ledger.json'); b=load(R/'ev-b-summary.json'); decision=b['decision']; ledger['terminal_state']=decision; (R/'formal-ledger.json').write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')
        run(sys.executable,'scripts/candidate_v13_external_finalize.py','--terminal-state',decision,'--reason','EV-B completed exactly once under the frozen evaluator and did not authorize EV-C.')
        commit_push('candidate-v13 external validity: finalize EV-B terminal state',['results/candidate-v13-external-validity/formal-ledger.json','results/candidate-v13-external-validity/terminal-summary.json','docs/research/candidate-v13-external-validity/terminal-decision.md'])
        return 0
    assert mode=='EV_C_AUTHORIZED'
    freeze=verify_freeze(); ledger=load(R/'formal-ledger.json'); assert ledger=={'ev_b':1,'ev_c':0,'terminal_state':None},ledger
    # Frozen materialization only; no Candidate call yet.
    run(sys.executable,'scripts/candidate_v13_external_runtime_eval.py','--stage','ev_c','--materialize-only')
    runtime=load(R/'ev-c-runtime.json')
    assert runtime['status']=='MATERIALIZATION_VALIDATED_NO_EXECUTION' and runtime['selection_digest']==freeze['ev_c_selection_digest']
    assert runtime['case_counts']['total']==1920 and runtime['case_counts']['answerable']==1152 and runtime['case_counts']['no_evidence']==768
    # Consume the bullet and persist it BEFORE the first EV-C Candidate call.
    ledger['ev_c']=1; (R/'formal-ledger.json').write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')
    (R/'ev-c-execution-start.json').write_text(json.dumps({'schema_version':'candidate-v13-external-ev-c-execution-start-v1','status':'EV_C_FORMAL_BULLET_CONSUMED_BEFORE_ALGORITHM_CALL','ev_c_ledger_count':1},indent=2,sort_keys=True)+'\n')
    commit_push('candidate-v13 external validity: consume EV-C formal bullet before algorithm call',['results/candidate-v13-external-validity/formal-ledger.json','results/candidate-v13-external-validity/ev-c-execution-start.json','results/candidate-v13-external-validity/ev-c-runtime.json'])
    cp=run(sys.executable,'scripts/candidate_v13_external_formal_execute.py','--stage','ev_c',check=False)
    summary=R/'ev-c-summary.json'; ledger=load(R/'formal-ledger.json')
    if summary.exists():
        decision=load(summary)['decision']
        if decision not in {'CANDIDATE_V13_EXTERNAL_VALIDITY_PASS','CANDIDATE_V13_EXTERNAL_VALIDITY_FAIL — CANDIDATE_V14_AUTHORIZED','EXTERNAL_VALIDITY_INVALID — RESEARCH_INTEGRITY_FAILURE'}: raise RuntimeError(f'illegal EV-C decision: {decision}')
        reason='EV-C completed exactly once under the frozen evaluator; terminal state follows preregistered formal gates.'
    else:
        decision='EXTERNAL_VALIDITY_INFRASTRUCTURE_BLOCKED'; reason='EV-C formal bullet was consumed but the frozen formal runner produced no valid stage summary; no rerun is permitted.'
    ledger['terminal_state']=decision; (R/'formal-ledger.json').write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')
    run(sys.executable,'scripts/candidate_v13_external_finalize.py','--terminal-state',decision,'--reason',reason)
    paths=['results/candidate-v13-external-validity/formal-ledger.json','results/candidate-v13-external-validity/terminal-summary.json','docs/research/candidate-v13-external-validity/terminal-decision.md']
    for name in ['ev-c-summary.json','ev-c-structural.json','ev-c-domain.json','ev-c-integrity.json','ev-c-freshness-audit.json']:
        if (R/name).exists(): paths.append(f'results/candidate-v13-external-validity/{name}')
    commit_push('candidate-v13 external validity: converge to terminal state after EV-C',paths)
    return 0
if __name__=='__main__': raise SystemExit(main())
