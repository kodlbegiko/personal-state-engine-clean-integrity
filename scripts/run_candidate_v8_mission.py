from __future__ import annotations
import hashlib, json, os, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

R=Path(__file__).resolve().parents[1]; B="research/candidate-v8-fresh-lineage"
V7S="c9bc8a5cf70cca5e2f97240bb427d1ad1cd8d60d14af922a4e634ec9c870bdae"; V7C="7acc9a99938efa0d361791191960a60cf8a88b6a2ec022d60f54da3df29b7e62"; V7F="090e6201e5c5a6701d003cd51b048edc93133b9d"
V8S="09d58cfb5c4b8ecfe8fcdb8cbc96b5fc85363ea155d8901ab54b42b92cd1322a"; GEN="238d78cf73d1726553c42098cd667c96055e20dd7e779d1ab252bd2b67866754"; EVAL="fae90a880803c1f7240a13aa51705ceb0d429e7c7fa1ad9a773c15ecdc83c9da"; DEV="a2a72a6e12efbbbd7adb35b77698c3fa503d2b04f388588d252f88a899e1ab8b"
RID=os.getenv("GITHUB_RUN_ID","LOCAL"); RAT=os.getenv("GITHUB_RUN_ATTEMPT","1")

def now(): return datetime.now(timezone.utc).isoformat()
def sha(p): return hashlib.sha256((R/p).read_bytes()).hexdigest()
def sh(*a, ok=True):
    x=subprocess.run(a,cwd=R,text=True,capture_output=True)
    if ok and x.returncode: raise RuntimeError(f"{a}: {x.stdout}\n{x.stderr}")
    return x
def head(): return sh("git","rev-parse","HEAD").stdout.strip()
def dump(p,x):
    p=R/p; p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(x,indent=2)+"\n")
def commit(paths,msg):
    sh("git","add","--",*paths); sh("git","commit","-m",msg); return head()

def identities():
    t=json.loads((R/"results/candidate-v7/terminal-snapshot.json").read_text())
    c={
      "v7_terminal":t.get("terminal_state")=="CANDIDATE_V7_CONFIRMATORY_FAIL",
      "v7_frozen":t.get("candidate_v7",{}).get("frozen") is True,
      "v7_freeze":t.get("candidate_v7",{}).get("freeze_boundary_commit")==V7F,
      "v7_source":sha("src/personal_state_engine/candidate_v7.py")==V7S,
      "v7_config":sha("experiments/configs/candidate-v7-v1.json")==V7C,
      "v8_source":sha("src/personal_state_engine/candidate_v8.py")==V8S,
      "generator":sha("scripts/generate_candidate_v8_benchmark.py")==GEN,
      "evaluator":sha("scripts/evaluate_candidate_v8.py")==EVAL}
    if not all(c.values()): raise RuntimeError(c)
    return c

def gen(split,path):
    sh(sys.executable,"scripts/generate_candidate_v8_benchmark.py",split,path)
    p=json.loads((R/path).read_text()); return {"sha256":sha(path),"seed":p["seed"],"case_count":p["case_count"],"answerable_count":p["answerable_count"],"no_evidence_count":p["no_evidence_count"],"namespace":p["namespace"]}
def ev(stage,bench,out,seed):
    x=sh(sys.executable,"scripts/evaluate_candidate_v8.py",bench,out,"--bootstrap-seed",str(seed),"--stage",stage,ok=False)
    return x.returncode,json.loads((R/out).read_text())
def terminal(state,stage,res,L):
    snap={"schema_version":"candidate-v8-terminal-snapshot-v1","terminal_state":state,"mission_stopped":True,"repository":"kodlbegiko/personal-state-engine-clean-integrity","branch":B,
      "candidate_v7_historical_immutable":True,"candidate_v7_terminal_state":"CANDIDATE_V7_CONFIRMATORY_FAIL","candidate_v7_source_sha256":V7S,"candidate_v7_config_sha256":V7C,
      "candidate_v8":{"source_sha256":V8S,"generator_sha256":GEN,"evaluator_sha256":EVAL,"architecture":"QUERY_REQUIREMENT_GRAPH_PLUS_CLAUSE_LEVEL_MULTI_SIGNAL_CERTIFIER","candidate_v2_rank_order_preserved":True,"per_memory_filtering":True},
      "formal_execution_count":L["counts"],"formal_rerun":{"protected":False,"confirmatory":False},"last_stage":stage,"last_result":res,
      "development_freeze_commit":L.get("dev_freeze"),"protected_materialization_commit":L.get("p_mat"),"protected_result_commit":L.get("p_res"),"confirmatory_freeze_commit":L.get("c_freeze"),"confirmatory_materialization_commit":L.get("c_mat"),
      "historical_v7_confirmatory_classification":"HISTORICAL_DIAGNOSTIC_ONLY","retired_99_case_semantic_payload_opened":False,"retired_99_case_manifest_only":{"dataset_sha256":"d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442","case_ids_sha256":"1ca053112b634871d24addbb3982d4e417dc8f4acce10609554cc41b6ed8e987","case_count":99},
      "integrity_deviations":["results/candidate-v8/pre-freeze-local-smoke-contamination-v1.json"],"monetary_cost_usd":0,"github_actions":{"workflow_run_id":RID,"attempt":RAT},"next_legal_action":"SEEK_EXPLICIT_FRESH_FINAL_GATE_F_AUTHORIZATION" if state=="READY_FOR_FRESH_FINAL_GATE_F_AUTHORIZATION" else "STOP_CANDIDATE_V8_AND_PRESERVE_FAILURE_EVIDENCE","created_at":now()}
    dump("results/candidate-v8/terminal-snapshot.json",snap)
    (R/"docs/research/candidate-v8/terminal-report.md").write_text(f"# Candidate-v8 Terminal Report\n\n## Terminal state\n`{state}`\n\n## Last formal stage\n`{stage}` — `{res['verdict']}`\n\nCandidate-v7 remained immutable. The retired 99-case semantic payload was never opened. Candidate-v7 confirmatory is historical-diagnostic-only. Formal protected/confirmatory executions were one-shot and cost USD 0.\n\n```json\n{json.dumps(res,indent=2)}\n```\n")
    commit(["results/candidate-v8/terminal-snapshot.json","docs/research/candidate-v8/terminal-report.md"],f"candidate-v8: terminal {state}"); sh("git","push","origin",f"HEAD:{B}")

def main():
    if (R/"results/candidate-v8/terminal-snapshot.json").exists(): return
    sh("git","config","user.name","candidate-v8-research-bot"); sh("git","config","user.email","candidate-v8-research-bot@users.noreply.github.com")
    L={"counts":{"protected":0,"confirmatory":0},"start":head()}; ids=identities()
    d=gen("development","experiments/benchmarks/candidate-v8-development-v1.json")
    if d["sha256"]!=DEV: raise RuntimeError(d)
    pt=sh(sys.executable,"-m","pytest","-q").stdout.strip(); rc,ds=ev("development","experiments/benchmarks/candidate-v8-development-v1.json","results/candidate-v8/development-summary-v1.json",2026081500)
    if rc or ds["verdict"]!="PASS": raise RuntimeError(ds)
    dump("results/candidate-v8/development-ci-execution-v1.json",{"schema_version":"candidate-v8-development-ci-execution-v1","workflow_run_id":RID,"attempt":RAT,"identity_checks":ids,"generator":d,"tests":pt,"result":ds,"historical_confirmatory_used_as_gate":False,"monetary_cost_usd":0,"executed_at":now()})
    de=commit(["experiments/benchmarks/candidate-v8-development-v1.json","results/candidate-v8/development-summary-v1.json","results/candidate-v8/development-ci-execution-v1.json"],"candidate-v8: reproduce development PASS")
    dump("results/candidate-v8/development-freeze-manifest-v1.json",{"schema_version":"candidate-v8-development-freeze-manifest-v1","status":"FROZEN_FOR_PROTECTED_VALIDATION","head_before_freeze":de,"source_sha256":V8S,"generator_sha256":GEN,"evaluator_sha256":EVAL,"config_sha256":sha("experiments/configs/candidate-v8-v1.json"),"development_benchmark_sha256":DEV,"tests":pt,"protected_dataset_seed":2026081511,"protected_bootstrap_seed":2026081501,"historical_v7_confirmatory_excluded":True,"retired_99_case_semantic_payload_opened":False,"workflow_run_id":RID,"created_at":now()})
    L["dev_freeze"]=commit(["results/candidate-v8/development-freeze-manifest-v1.json"],"candidate-v8: freeze development before protected validation")
    identities(); p=gen("protected","experiments/benchmarks/candidate-v8-protected-validation-v1.json")
    if p["seed"]!=2026081511 or p["case_count"]!=160: raise RuntimeError(p)
    dump("experiments/benchmarks/candidate-v8-protected-validation-lock-v1.json",{"schema_version":"candidate-v8-protected-lock-v1","status":"FROZEN_BEFORE_FORMAL_EXECUTION","development_freeze_commit":L["dev_freeze"],"dataset_seed":2026081511,"bootstrap_seed":2026081501,"dataset_sha256":p["sha256"],"source_sha256":V8S,"generator_sha256":GEN,"evaluator_sha256":EVAL,"formal_execution_count":0,"rerun":False,"payload_manually_inspected":False,"created_at":now()})
    L["p_mat"]=commit(["experiments/benchmarks/candidate-v8-protected-validation-v1.json","experiments/benchmarks/candidate-v8-protected-validation-lock-v1.json"],"candidate-v8: materialize and lock fresh protected validation")
    dump("results/candidate-v8/protected-execution-authorization-v1.json",{"schema_version":"candidate-v8-protected-execution-authorization-v1","status":"AUTHORIZED_ONCE","materialization_commit":L["p_mat"],"dataset_sha256":p["sha256"],"formal_execution_limit":1,"workflow_run_id":RID,"created_at":now()})
    pa=commit(["results/candidate-v8/protected-execution-authorization-v1.json"],"candidate-v8: authorize protected validation once")
    L["counts"]["protected"]=1; prc,ps=ev("protected","experiments/benchmarks/candidate-v8-protected-validation-v1.json","results/candidate-v8/protected-validation-summary-v1.json",2026081501)
    dump("results/candidate-v8/protected-execution-record-v1.json",{"schema_version":"candidate-v8-protected-execution-record-v1","formal_execution_count":1,"rerun":False,"authorization_commit":pa,"materialization_commit":L["p_mat"],"dataset_sha256":p["sha256"],"workflow_run_id":RID,"return_code":prc,"verdict":ps["verdict"],"executed_at":now()})
    L["p_res"]=commit(["results/candidate-v8/protected-validation-summary-v1.json","results/candidate-v8/protected-execution-record-v1.json"],f"candidate-v8: protected validation {ps['verdict']}")
    if prc or ps["verdict"]!="PASS": terminal("CANDIDATE_V8_PROTECTED_VALIDATION_FAIL","protected",ps,L); return
    identities(); dump("results/candidate-v8/confirmatory-freeze-manifest-v1.json",{"schema_version":"candidate-v8-confirmatory-freeze-manifest-v1","status":"FROZEN_FOR_CONFIRMATORY","protected_result_commit":L["p_res"],"protected_verdict":"PASS","source_sha256":V8S,"generator_sha256":GEN,"evaluator_sha256":EVAL,"confirmatory_dataset_seed":2026081522,"confirmatory_bootstrap_seed":2026081502,"historical_v7_confirmatory_excluded":True,"workflow_run_id":RID,"created_at":now()})
    L["c_freeze"]=commit(["results/candidate-v8/confirmatory-freeze-manifest-v1.json"],"candidate-v8: freeze before fresh confirmatory materialization")
    c=gen("confirmatory","experiments/benchmarks/candidate-v8-confirmatory-v1.json")
    if c["seed"]!=2026081522 or c["case_count"]!=200: raise RuntimeError(c)
    dump("experiments/benchmarks/candidate-v8-confirmatory-lock-v1.json",{"schema_version":"candidate-v8-confirmatory-lock-v1","status":"FROZEN_BEFORE_FORMAL_EXECUTION","confirmatory_freeze_commit":L["c_freeze"],"dataset_seed":2026081522,"bootstrap_seed":2026081502,"dataset_sha256":c["sha256"],"source_sha256":V8S,"generator_sha256":GEN,"evaluator_sha256":EVAL,"formal_execution_count":0,"rerun":False,"payload_manually_inspected":False,"created_at":now()})
    L["c_mat"]=commit(["experiments/benchmarks/candidate-v8-confirmatory-v1.json","experiments/benchmarks/candidate-v8-confirmatory-lock-v1.json"],"candidate-v8: materialize and lock fresh confirmatory")
    dump("results/candidate-v8/confirmatory-execution-authorization-v1.json",{"schema_version":"candidate-v8-confirmatory-execution-authorization-v1","status":"AUTHORIZED_ONCE","materialization_commit":L["c_mat"],"dataset_sha256":c["sha256"],"formal_execution_limit":1,"workflow_run_id":RID,"created_at":now()})
    ca=commit(["results/candidate-v8/confirmatory-execution-authorization-v1.json"],"candidate-v8: authorize confirmatory once")
    L["counts"]["confirmatory"]=1; crc,cs=ev("confirmatory","experiments/benchmarks/candidate-v8-confirmatory-v1.json","results/candidate-v8/confirmatory-summary-v1.json",2026081502)
    dump("results/candidate-v8/confirmatory-execution-record-v1.json",{"schema_version":"candidate-v8-confirmatory-execution-record-v1","formal_execution_count":1,"rerun":False,"authorization_commit":ca,"materialization_commit":L["c_mat"],"dataset_sha256":c["sha256"],"workflow_run_id":RID,"return_code":crc,"verdict":cs["verdict"],"executed_at":now()})
    commit(["results/candidate-v8/confirmatory-summary-v1.json","results/candidate-v8/confirmatory-execution-record-v1.json"],f"candidate-v8: confirmatory {cs['verdict']}")
    terminal("READY_FOR_FRESH_FINAL_GATE_F_AUTHORIZATION" if not crc and cs["verdict"]=="PASS" else "CANDIDATE_V8_CONFIRMATORY_FAIL","confirmatory",cs,L)

if __name__=="__main__": main()
