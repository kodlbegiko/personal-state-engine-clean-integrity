from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from personal_state_engine.candidate_v2 import pse_candidate_v2_rank
from personal_state_engine.candidate_v8 import pse_candidate_v8_rank
from personal_state_engine.candidate_v9 import pse_candidate_v9_rank

BOOTSTRAP_SEEDS = {"development":2026081510,"protected":2026081512,"confirmatory":2026081514,"final":2026081516}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def reciprocal_rank(case: dict, ranking: list[str]) -> float:
    relevant = set(case["relevant_memory_ids"])
    return next((1.0 / (i + 1) for i, mid in enumerate(ranking) if mid in relevant), 0.0)


def evaluate(cases: list[dict], ranker) -> dict:
    answerable = [c for c in cases if c["relevant_memory_ids"]]
    negatives = [c for c in cases if not c["relevant_memory_ids"]]
    rrs=[]; r1=[]; r3=[]; r5=[]
    false_abstentions=0; relevant_retrieved=0; order_violations=0
    for c in answerable:
        ranking = ranker(c, 5)
        relevant = set(c["relevant_memory_ids"])
        hit = bool(relevant & set(ranking))
        relevant_retrieved += int(hit)
        false_abstentions += int(not ranking)
        rrs.append(reciprocal_rank(c, ranking))
        r1.append(float(bool(relevant & set(ranking[:1]))))
        r3.append(float(bool(relevant & set(ranking[:3]))))
        r5.append(float(bool(relevant & set(ranking[:5]))))
        v2_full = pse_candidate_v2_rank(c, max(5, len(c["memories"])))
        expected = [mid for mid in v2_full if mid in set(ranking)]
        order_violations += int(ranking != expected[:len(ranking)])
    negative_rankings = [ranker(c,5) for c in negatives]
    false_retrievals = sum(bool(r) for r in negative_rankings)
    return {
        "MRR": sum(rrs)/len(rrs),
        "R@1": sum(r1)/len(r1),
        "R@3": sum(r3)/len(r3),
        "R@5": sum(r5)/len(r5),
        "answerable_recall": relevant_retrieved/len(answerable),
        "false_abstention": false_abstentions/len(answerable),
        "abstention_accuracy": 1.0-false_retrievals/len(negatives),
        "false_retrieval": false_retrievals/len(negatives),
        "order_preservation_violations": order_violations,
        "answerable_count": len(answerable),
        "no_evidence_count": len(negatives),
    }


def paired_bootstrap(cases: list[dict], seed: int, iterations: int=10000, margin: float=-0.03) -> dict:
    answerable=[c for c in cases if c["relevant_memory_ids"]]
    deltas=[reciprocal_rank(c,pse_candidate_v9_rank(c,5))-reciprocal_rank(c,pse_candidate_v2_rank(c,5)) for c in answerable]
    rng=random.Random(seed)
    samples=sorted(sum(deltas[rng.randrange(len(deltas))] for _ in deltas)/len(deltas) for _ in range(iterations))
    lo=samples[int(0.025*(len(samples)-1))]; hi=samples[int(0.975*(len(samples)-1))]
    return {"iterations":iterations,"seed":seed,"delta":sum(deltas)/len(deltas),"ci95":[lo,hi],"margin":margin,"noninferiority":lo>=margin}


def gates(stage: str, v2: dict, v9: dict, boot: dict) -> dict:
    reduction=v2["false_retrieval"]-v9["false_retrieval"]
    if stage == "development":
        checks={
            "mrr":v9["MRR"]>=0.985,"r1":v9["R@1"]>=0.975,"r3":v9["R@3"]>=0.990,"r5":v9["R@5"]>=0.990,
            "answerable_recall":v9["answerable_recall"]>=0.985,"false_abstention":v9["false_abstention"]<=0.015,
            "false_retrieval":v9["false_retrieval"]<=0.025,"abstention_accuracy":v9["abstention_accuracy"]>=0.975,
            "order_preservation":v9["order_preservation_violations"]==0,"paired_bootstrap_noninferiority":boot["noninferiority"],
        }
    elif stage in {"protected","confirmatory"}:
        checks={
            "mrr":v9["MRR"]>=0.96,"r1":v9["R@1"]>=0.95,"r3":v9["R@3"]>=0.97,"r5":v9["R@5"]>=0.97,
            "answerable_recall":v9["answerable_recall"]>=0.97,"false_abstention":v9["false_abstention"]<=0.03,
            "false_retrieval":v9["false_retrieval"]<=0.05,"abstention_accuracy":v9["abstention_accuracy"]>=0.95,
            "order_preservation":v9["order_preservation_violations"]==0,"paired_bootstrap_noninferiority":boot["noninferiority"],
            "absolute_false_retrieval_reduction":reduction>=0.80,
        }
    else:
        checks={
            "mrr":v9["MRR"]>=0.96,"answerable_recall":v9["answerable_recall"]>=0.97,
            "false_abstention":v9["false_abstention"]<=0.03,"false_retrieval":v9["false_retrieval"]<=0.05,
            "abstention_accuracy":v9["abstention_accuracy"]>=0.95,"order_preservation":v9["order_preservation_violations"]==0,
            "paired_bootstrap_noninferiority":boot["noninferiority"],"absolute_false_retrieval_reduction":reduction>=0.80,
        }
    return checks


def evaluate_payload(benchmark: Path, stage: str) -> dict:
    payload=json.loads(benchmark.read_text()); cases=payload["cases"]
    v2=evaluate(cases,pse_candidate_v2_rank); v9=evaluate(cases,pse_candidate_v9_rank); boot=paired_bootstrap(cases,BOOTSTRAP_SEEDS[stage])
    reduction=v2["false_retrieval"]-v9["false_retrieval"]
    checks=gates(stage,v2,v9,boot)
    result={
        "schema_version":"candidate-v9-evaluation-v1","stage":stage,"benchmark_name":payload["name"],"benchmark_sha256":sha(benchmark),
        "candidate_v9_source_sha256":sha(ROOT/"src/personal_state_engine/candidate_v9.py"),
        "candidate_v2":v2,"candidate_v9":v9,"candidate_v9_absolute_false_retrieval_reduction_vs_candidate_v2":reduction,
        "paired_bootstrap":boot,"checks":checks,"verdict":"PASS" if all(checks.values()) else "FAIL","monetary_cost_usd":0,
    }
    if stage == "final":
        result["candidate_v8_historical_baseline"] = evaluate(cases,pse_candidate_v8_rank)
        result["candidate_v8_source_sha256"] = sha(ROOT/"src/personal_state_engine/candidate_v8.py")
    return result


def main() -> None:
    p=argparse.ArgumentParser(); p.add_argument("benchmark",type=Path); p.add_argument("output",type=Path); p.add_argument("--stage",choices=BOOTSTRAP_SEEDS,required=True); p.add_argument("--no-fail",action="store_true"); args=p.parse_args()
    result=evaluate_payload(args.benchmark,args.stage); args.output.parent.mkdir(parents=True,exist_ok=True); args.output.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({"stage":result["stage"],"candidate_v2":result["candidate_v2"],"candidate_v9":result["candidate_v9"],"paired_bootstrap":result["paired_bootstrap"],"checks":result["checks"],"verdict":result["verdict"]},indent=2))
    if result["verdict"]!="PASS" and not args.no_fail: raise SystemExit(2)

if __name__=="__main__": main()
