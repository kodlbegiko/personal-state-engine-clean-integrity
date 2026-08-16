from __future__ import annotations

import hashlib
import importlib
import json
import math
import random
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from personal_state_engine.candidate_v2 import pse_candidate_v2_rank
from personal_state_engine.candidate_v7 import pse_candidate_v7_rank
from personal_state_engine.zero_cost_baselines import parse_timestamp, tokens

BENCH = ROOT / "experiments" / "benchmarks" / "candidate-v7-confirmatory-v1.json"
LOCK = ROOT / "experiments" / "benchmarks" / "candidate-v7-confirmatory-lock-v1.json"
PROTOCOL = ROOT / "experiments" / "protocols" / "candidate-v7-confirmatory-v1.json"
SOURCE = ROOT / "src" / "personal_state_engine" / "candidate_v7.py"
CONFIG = ROOT / "experiments" / "configs" / "candidate-v7-v1.json"
V6_SOURCE = ROOT / "src" / "personal_state_engine" / "candidate_v6_historical.py"
RDIR = ROOT / "results" / "candidate-v7"
EXPECTED_V7 = "c9bc8a5cf70cca5e2f97240bb427d1ad1cd8d60d14af922a4e634ec9c870bdae"
EXPECTED_CONFIG = "7acc9a99938efa0d361791191960a60cf8a88b6a2ec022d60f54da3df29b7e62"
EXPECTED_V6 = "c540056c6f30f0145ab8ef8c10be3abcae2ed24e6a087a2d9a3531bc5e545325"
SEED = 20260815


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def content_terms(text: str) -> list[str]:
    stop = {"the","a","an","is","are","was","were","what","which","who","where","when","how","does","do","did","to","of","in","on","at","for","with","and","or","my","your","his","her","their","current","currently","now"}
    return [t for t in tokens(text) if t not in stop and len(t) > 1]


def bm25_rank(case: dict, k: int = 5) -> list[str]:
    docs = [content_terms(m["text"]) for m in case["memories"]]
    q = content_terms(case["query"])
    n = max(len(docs), 1)
    avgdl = sum(map(len, docs)) / n or 1.0
    df = Counter(term for term in set(q) for doc in docs if term in set(doc))
    scores = []
    for idx, (memory, doc) in enumerate(zip(case["memories"], docs)):
        tf = Counter(doc)
        score = 0.0
        for term in q:
            if term not in tf:
                continue
            idf = math.log(1.0 + (n - df[term] + 0.5) / (df[term] + 0.5))
            denom = tf[term] + 1.5 * (1 - 0.75 + 0.75 * len(doc) / avgdl)
            score += idf * tf[term] * 2.5 / denom
        scores.append((score, -idx, memory["id"]))
    scores.sort(reverse=True)
    return [mid for _, _, mid in scores[:k]]


def tfidf_rank(case: dict, k: int = 5) -> list[str]:
    q = content_terms(case["query"])
    docs = [content_terms(m["text"]) for m in case["memories"]]
    vocab = set(q)
    for doc in docs:
        vocab.update(doc)
    n = max(len(docs), 1)
    df = {term: sum(term in set(doc) for doc in docs) for term in vocab}
    idf = {term: math.log((1 + n) / (1 + df[term])) + 1.0 for term in vocab}
    qv = Counter(q)
    qnorm = math.sqrt(sum((qv[t] * idf[t]) ** 2 for t in qv)) or 1.0
    scores = []
    for idx, (memory, doc) in enumerate(zip(case["memories"], docs)):
        dv = Counter(doc)
        dot = sum(qv[t] * idf[t] * dv.get(t, 0) * idf[t] for t in qv)
        dnorm = math.sqrt(sum((dv[t] * idf[t]) ** 2 for t in dv)) or 1.0
        scores.append((dot / (qnorm * dnorm), -idx, memory["id"]))
    scores.sort(reverse=True)
    return [mid for _, _, mid in scores[:k]]


def recency_rank(case: dict, k: int = 5) -> list[str]:
    rows = [(parse_timestamp(m.get("timestamp")), -i, m["id"]) for i, m in enumerate(case["memories"])]
    rows.sort(reverse=True)
    return [mid for _, _, mid in rows[:k]]


def deterministic_random_rank(case: dict, k: int = 5) -> list[str]:
    mids = [m["id"] for m in case["memories"]]
    material = case["query"] + "\n" + "\n".join(sorted(mids)) + f"\n{SEED}"
    seed = int.from_bytes(hashlib.sha256(material.encode()).digest()[:8], "big")
    rng = random.Random(seed)
    rng.shuffle(mids)
    return mids[:k]


def reciprocal_rank(case: dict, ranking: list[str]) -> float:
    rel = set(case["relevant_memory_ids"])
    return next((1.0 / (i + 1) for i, mid in enumerate(ranking) if mid in rel), 0.0)


def evaluate(cases: list[dict], ranker) -> dict:
    answerable = [c for c in cases if c["relevant_memory_ids"]]
    negatives = [c for c in cases if not c["relevant_memory_ids"]]
    rr, r1, r3, r5 = [], [], [], []
    false_abs = 0
    for c in answerable:
        ranking = ranker(c, 5)
        rel = set(c["relevant_memory_ids"])
        rr.append(reciprocal_rank(c, ranking))
        r1.append(float(bool(rel & set(ranking[:1]))))
        r3.append(float(bool(rel & set(ranking[:3]))))
        r5.append(float(bool(rel & set(ranking[:5]))))
        false_abs += int(not ranking)
    false_ret = sum(bool(ranker(c, 5)) for c in negatives) / len(negatives)
    return {
        "MRR": sum(rr) / len(rr),
        "R@1": sum(r1) / len(r1),
        "R@3": sum(r3) / len(r3),
        "R@5": sum(r5) / len(r5),
        "answerable_recall": 1.0 - false_abs / len(answerable),
        "false_abstention": false_abs / len(answerable),
        "abstention_accuracy": 1.0 - false_ret,
        "false_retrieval": false_ret,
    }


def bootstrap(cases: list[dict]) -> dict:
    answerable = [c for c in cases if c["relevant_memory_ids"]]
    deltas = [
        reciprocal_rank(c, pse_candidate_v7_rank(c, 5)) - reciprocal_rank(c, pse_candidate_v2_rank(c, 5))
        for c in answerable
    ]
    rng = random.Random(SEED)
    samples = sorted(sum(deltas[rng.randrange(len(deltas))] for _ in deltas) / len(deltas) for _ in range(10000))
    lo = samples[int(0.025 * (len(samples) - 1))]
    hi = samples[int(0.975 * (len(samples) - 1))]
    return {"iterations":10000,"seed":SEED,"delta":sum(deltas)/len(deltas),"ci95":[lo,hi],"margin":0.03,"pass":lo >= -0.03}


def main() -> None:
    summary_path = RDIR / "confirmatory-summary-v1.json"
    stats_path = RDIR / "confirmatory-statistics-v1.json"
    if summary_path.exists() or stats_path.exists():
        raise SystemExit("confirmatory execution refused: result already exists")
    if sha(SOURCE) != EXPECTED_V7 or sha(CONFIG) != EXPECTED_CONFIG:
        raise SystemExit("confirmatory execution refused: frozen Candidate-v7 identity changed")
    if not V6_SOURCE.exists() or sha(V6_SOURCE) != EXPECTED_V6:
        raise SystemExit("confirmatory execution refused: historical Candidate-v6 identity unavailable/mismatched")

    lock = json.loads(LOCK.read_text())
    if lock.get("status") != "FROZEN_BEFORE_CONFIRMATORY_EXECUTION":
        raise SystemExit("confirmatory execution refused: lock invalid")
    if sha(BENCH) != lock["dataset_sha256"] or sha(Path(__file__)) != lock["evaluator_sha256"]:
        raise SystemExit("confirmatory execution refused: dataset/evaluator identity mismatch")
    generator = ROOT / lock["generator_path"]
    if sha(generator) != lock["generator_sha256"]:
        raise SystemExit("confirmatory execution refused: generator identity mismatch")

    importlib.invalidate_caches()
    v6_module = importlib.import_module("personal_state_engine.candidate_v6_historical")
    v6_rank = v6_module.pse_candidate_v6_rank

    payload = json.loads(BENCH.read_text())
    cases = payload["cases"]
    if len(cases) != 140 or sum(bool(c["relevant_memory_ids"]) for c in cases) != 85:
        raise SystemExit("confirmatory execution refused: case counts mismatch")

    rankers = {
        "candidate_v2": pse_candidate_v2_rank,
        "candidate_v6_historical": v6_rank,
        "candidate_v7": pse_candidate_v7_rank,
        "bm25": bm25_rank,
        "tfidf": tfidf_rank,
        "recency": recency_rank,
        "deterministic_random": deterministic_random_rank,
    }
    metrics = {name: evaluate(cases, fn) for name, fn in rankers.items()}
    v2, v7 = metrics["candidate_v2"], metrics["candidate_v7"]
    deficits = {key: v2[key] - v7[key] for key in ["MRR","R@1","R@3","R@5"]}
    reduction = v2["false_retrieval"] - v7["false_retrieval"]
    boot = bootstrap(cases)
    protocol = json.loads(PROTOCOL.read_text())
    t = protocol["candidate_v7_success_rule"]
    checks = {
        "mrr_noninferiority": deficits["MRR"] <= t["mrr_deficit_vs_candidate_v2_max"],
        "r1_noninferiority": deficits["R@1"] <= t["r1_deficit_vs_candidate_v2_max"],
        "r3_noninferiority": deficits["R@3"] <= t["r3_deficit_vs_candidate_v2_max"],
        "r5_noninferiority": deficits["R@5"] <= t["r5_deficit_vs_candidate_v2_max"],
        "answerable_recall": v7["answerable_recall"] >= t["answerable_recall_min"],
        "false_abstention": v7["false_abstention"] <= t["false_abstention_max"],
        "abstention_accuracy": v7["abstention_accuracy"] >= t["abstention_accuracy_min"],
        "false_retrieval": v7["false_retrieval"] <= t["false_retrieval_max"],
        "absolute_false_retrieval_reduction": reduction >= t["absolute_false_retrieval_reduction_vs_candidate_v2_min"],
        "natural_language_support": v7["answerable_recall"] >= t["natural_language_support_min"],
        "paired_bootstrap_noninferiority": boot["pass"],
    }
    verdict = "PASS" if all(checks.values()) else "FAIL"
    stats = {
        "schema_version":"candidate-v7-confirmatory-statistics-v1",
        "candidate_source_sha256":sha(SOURCE),
        "config_sha256":sha(CONFIG),
        "candidate_v6_source_sha256":sha(V6_SOURCE),
        "dataset_sha256":sha(BENCH),
        "generator_sha256":lock["generator_sha256"],
        "evaluator_sha256":lock["evaluator_sha256"],
        "metrics":metrics,
        "candidate_v7_deficits_vs_candidate_v2":deficits,
        "candidate_v7_absolute_false_retrieval_reduction_vs_candidate_v2":reduction,
        "paired_bootstrap":boot,
        "success_checks":checks,
        "verdict":verdict,
    }
    summary = {
        "schema_version":"candidate-v7-confirmatory-summary-v1",
        "benchmark":{"name":payload["name"],"case_count":140,"answerable_count":85,"no_evidence_count":55,"dataset_sha256":sha(BENCH)},
        "candidate_v2":v2,
        "candidate_v6_historical":metrics["candidate_v6_historical"],
        "candidate_v7":v7,
        "baselines":{"bm25":metrics["bm25"],"tfidf":metrics["tfidf"],"recency":metrics["recency"],"deterministic_random":metrics["deterministic_random"]},
        "paired_bootstrap":boot,
        "success_checks":checks,
        "verdict":verdict,
        "candidate_v7_modified_after_freeze":False,
        "algorithm_parity":"NO",
        "historical_gate_f_status":"GATE_F_SELECTION_FAIL / FORMAL NOT COMPLETE",
        "next_legal_action_if_pass":"QUALIFY_GENUINELY_FRESH_FINAL_SURFACE",
        "terminal_state_if_fail":"CANDIDATE_V7_CONFIRMATORY_FAIL"
    }
    RDIR.mkdir(parents=True, exist_ok=True)
    stats_path.write_text(json.dumps(stats, indent=2) + "\n")
    summary_path.write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({"verdict":verdict,"candidate_v7":v7,"candidate_v6":metrics["candidate_v6_historical"],"bootstrap":boot}, indent=2))
    if verdict != "PASS":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
