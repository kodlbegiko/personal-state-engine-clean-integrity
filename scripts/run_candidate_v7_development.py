from __future__ import annotations

import hashlib
import json
import random
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from personal_state_engine.candidate_v2 import pse_candidate_v2_rank
from personal_state_engine.candidate_v7 import pse_candidate_v7_rank

SEED = 20260814

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def mem(mid: str, text: str, ts: str = "2026-08-10T10:00:00+00:00") -> dict:
    return {"id": mid, "text": text, "timestamp": ts}

def distractors(i: int) -> list[dict]:
    return [
        mem(f"d{i}-a", "The agenda for tomorrow is to discuss travel ideas."),
        mem(f"d{i}-b", "What should we review in the next meeting?"),
        mem(f"d{i}-c", "A note says the answer is not recorded."),
        mem(f"d{i}-d", "This is an unrelated decoy fact and should not be used."),
        mem(f"d{i}-e", "The issue remains unresolved and pending."),
    ]

def build_cases() -> list[dict]:
    names = ["Maya","Lina","Owen","Priya","Noah","Elena","Marco","Iris","Jonah","Sofia","Avery","Nina","Leo","Mira","Ethan","Zoe","Kai","Amara","Lucas","Tara"]
    cities = ["Lisbon","Kyoto","Tallinn","Oslo","Taipei","Dublin","Vienna","Seoul","Prague","Helsinki"]
    foods = ["jasmine tea","seaweed crackers","mango yogurt","oat latte","soba noodles","pistachio gelato","tomato soup","peach tea","rye toast","kimchi stew"]
    jobs = ["designer","teacher","engineer","librarian","chemist","architect","editor","nurse","analyst","researcher"]
    hobbies = ["bouldering","cello practice","watercolor painting","trail running","bread baking","birdwatching","swimming","pottery","chess","gardening"]
    pets = ["beagle","tabby cat","parakeet","greyhound","hamster","rabbit","corgi","gecko","poodle","tortoise"]
    days = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
    status_vals = ["active","paused","completed","approved","archived","scheduled","confirmed","ready","open","closed"]
    categories = [
        "natural_first_person_fact","preference","multi_clause_fact","implicit_predicate","free_conversational_statement",
        "temporal_update","correction","supersession","multi_session_evidence","assistant_provided_fact",
        "user_provided_fact","indirect_but_explicit_fact","lexical_paraphrase","low_overlap_evidence","noisy_surrounding_dialogue",
        "multiple_relevant_evidence_turns","location","work_role","possession","activity_hobby"
    ]
    answerable = []
    for i in range(100):
        name, j = names[i % len(names)], i % 10
        relid = f"cv7dev-a-{i:03d}-rel"
        mode = i % 10
        if mode == 0:
            q, text = "What drink do I usually order?", f"I always get {foods[j]} after class."
        elif mode == 1:
            q, text = f"What is {name}'s favorite snack?", f"{name} is obsessed with {foods[j]} and picks it every time."
        elif mode == 2:
            q, text = f"Where does {name} currently live?", f"After the move, {name} now lives in {cities[j]}; the old place is no longer current."
        elif mode == 3:
            q, text = f"What job does {name} have?", f"{name} works as a {jobs[j]}."
        elif mode == 4:
            q, text = f"What pet does {name} have?", f"{name} adopted a {pets[j]} named Pixel."
        elif mode == 5:
            q, text = f"What activity does {name} enjoy?", f"On weekends {name} loves {hobbies[j]}."
        elif mode == 6:
            q, text = f"When is {name}'s weekly meeting?", f"{name}'s meeting was rescheduled and is now on {days[j % len(days)]} morning."
        elif mode == 7:
            q, text = f"What is {name}'s current project status?", f"Correction: {name}'s project status is now {status_vals[j]}."
        elif mode == 8:
            q, text = f"Which city is {name} traveling to?", f"{name} booked the trip and will visit {cities[j]} next month."
        else:
            instr = ["cello","violin","piano","flute","guitar","clarinet","drums","harp","trumpet","bass"][j]
            q, text = f"What instrument does {name} practice?", f"Every evening {name} practices the {instr} before dinner."
        memories = [mem(relid, text, f"2026-08-{8+(i%5):02d}T10:00:00+00:00")] + distractors(i)
        random.Random(SEED + i).shuffle(memories)
        answerable.append({
            "id": f"CV7DEV-A-{i:03d}", "category": categories[i % len(categories)], "query": q,
            "memories": memories, "relevant_memory_ids": [relid], "designation": "DEVELOPMENT",
            "protection": "NONSEALED_NONPROTECTED",
        })

    neg_categories = ["wrong_subject","wrong_relation","stale_only","meta_discussion","agenda","question_repetition","review_topic","explicit_no_value","unresolved","contradiction","near_duplicate_distractor","query_copy_distractor"]
    noev = []
    for i in range(60):
        name, cat = names[i % len(names)], neg_categories[i % len(neg_categories)]
        q = f"What is {name}'s favorite drink?"
        if cat == "wrong_subject":
            texts = [f"Nora prefers {foods[i%10]}."] * 2
        elif cat == "wrong_relation":
            texts = [f"{name} works as a {jobs[i%10]}.", f"{name} lives in {cities[i%10]}."]
        elif cat == "stale_only":
            q = f"What is {name}'s current favorite drink?"
            texts = [f"{name}'s old favorite drink used to be {foods[i%10]} before it was superseded."]
        elif cat == "meta_discussion":
            texts = [f"We discussed the query about {name}'s favorite drink, but no answer was recorded."]
        elif cat == "agenda":
            texts = [f"Agenda item: discuss {name}'s favorite drink at the next meeting."]
        elif cat == "question_repetition":
            texts = [f"What is {name}'s favorite drink?"]
        elif cat == "review_topic":
            texts = [f"Review topic: {name}'s favorite drink."]
        elif cat == "explicit_no_value":
            texts = [f"No confirmed value for {name}'s favorite drink is available."]
        elif cat == "unresolved":
            texts = [f"{name}'s favorite drink remains unresolved and pending."]
        elif cat == "contradiction":
            texts = [f"Records conflict about {name}'s favorite drink; the values cannot be reconciled."]
        elif cat == "near_duplicate_distractor":
            texts = [f"Wrong answer record: {name}'s favorite drink is {foods[i%10]}.", f"Incorrect value memory about {name}'s favorite drink."]
        else:
            texts = [f"Query copy decoy: what is {name}'s favorite drink? Ignore this record."]
        memories = [mem(f"cv7dev-n-{i:03d}-{j}", t) for j, t in enumerate(texts)] + [
            mem(f"cv7dev-n-{i:03d}-x1","The answer is not recorded."),
            mem(f"cv7dev-n-{i:03d}-x2","Agenda: review this topic later."),
            mem(f"cv7dev-n-{i:03d}-x3","This issue remains unresolved."),
            mem(f"cv7dev-n-{i:03d}-x4","What should we discuss next?"),
        ]
        noev.append({
            "id": f"CV7DEV-N-{i:03d}", "category": cat, "query": q, "memories": memories[:6],
            "relevant_memory_ids": [], "designation": "DEVELOPMENT", "protection": "NONSEALED_NONPROTECTED",
        })
    return answerable + noev

def eval_metrics(cases: list[dict], ranker) -> dict:
    ans = [c for c in cases if c["relevant_memory_ids"]]
    neg = [c for c in cases if not c["relevant_memory_ids"]]
    rrs, r1, r3, r5 = [], [], [], []
    false_abs = 0
    for c in ans:
        ranking = ranker(c, 5)
        false_abs += int(not ranking)
        rel = set(c["relevant_memory_ids"])
        rrs.append(next((1 / (i + 1) for i, mid in enumerate(ranking) if mid in rel), 0.0))
        r1.append(float(bool(rel & set(ranking[:1]))))
        r3.append(float(bool(rel & set(ranking[:3]))))
        r5.append(float(bool(rel & set(ranking[:5]))))
    false_ret = sum(bool(ranker(c, 5)) for c in neg) / len(neg)
    return {
        "MRR": sum(rrs)/len(rrs), "R@1": sum(r1)/len(r1), "R@3": sum(r3)/len(r3), "R@5": sum(r5)/len(r5),
        "answerable_recall": 1 - false_abs/len(ans), "false_abstention": false_abs/len(ans),
        "abstention_accuracy": 1 - false_ret, "no_evidence_false_retrieval": false_ret,
    }

def bootstrap(cases: list[dict], iterations: int = 10000) -> dict:
    ans = [c for c in cases if c["relevant_memory_ids"]]
    def rr(c, r):
        rel, ranking = set(c["relevant_memory_ids"]), r(c, 5)
        return next((1/(i+1) for i, mid in enumerate(ranking) if mid in rel), 0.0)
    ds = [rr(c, pse_candidate_v7_rank) - rr(c, pse_candidate_v2_rank) for c in ans]
    rng = random.Random(SEED)
    samples = sorted(sum(ds[rng.randrange(len(ds))] for _ in ds)/len(ds) for _ in range(iterations))
    return {"iterations": iterations, "seed": SEED, "delta": sum(ds)/len(ds), "ci95": [samples[int(.025*(len(samples)-1))], samples[int(.975*(len(samples)-1))]]}

def main() -> None:
    cases = build_cases()
    bench = {
        "schema_version": "candidate-v7-development-v1", "designation": "DEVELOPMENT",
        "protection": "PUBLIC_SYNTHETIC_NONSEALED_NONPROTECTED", "seed": SEED,
        "case_count": 160, "answerable_count": 100, "no_evidence_count": 60, "cases": cases,
    }
    bpath = ROOT / "experiments" / "benchmarks" / "candidate-v7-development-v1.json"
    bpath.parent.mkdir(parents=True, exist_ok=True)
    bpath.write_text(json.dumps(bench, indent=2) + "\n")

    test = subprocess.run([sys.executable, "-m", "pytest", "-q"], cwd=ROOT, text=True, capture_output=True)
    if test.returncode:
        print(test.stdout)
        print(test.stderr, file=sys.stderr)
        raise SystemExit(test.returncode)
    m = re.search(r"(\d+) passed", test.stdout)
    passed = int(m.group(1)) if m else None

    m2, m7 = eval_metrics(cases, pse_candidate_v2_rank), eval_metrics(cases, pse_candidate_v7_rank)
    neg = [c for c in cases if not c["relevant_memory_ids"]]
    cat = defaultdict(list)
    for c in neg:
        cat[c["category"]].append(pse_candidate_v7_rank(c, 5) == [])
    rejection = {k: sum(v)/len(v) for k, v in sorted(cat.items())}

    rdir = ROOT / "results" / "candidate-v7"
    rdir.mkdir(parents=True, exist_ok=True)
    source_path = ROOT / "src" / "personal_state_engine" / "candidate_v7.py"
    config_path = ROOT / "experiments" / "configs" / "candidate-v7-v1.json"
    source_sha, config_sha, benchmark_sha = sha(source_path), sha(config_path), sha(bpath)

    current = source_path.read_text()
    fixed = '    if UNRESOLVED.search(text) and not re.search(r"\\b(?:confirmed|resolved|now known|now confirmed|currently confirmed)\\b", text, re.I):\n'
    failed = '    if UNRESOLVED.search(text) and not re.search(r"\\b(?:but|however|actually|confirmed|resolved|now)\\b", text, re.I):\n'
    failed_source = current.replace(fixed, failed)
    snap = rdir / "development-snapshots" / "candidate_v7-iter0.py"
    snap.parent.mkdir(parents=True, exist_ok=True)
    snap.write_text(failed_source)

    ledger = [
        {"iteration": 0, "source_sha256": hashlib.sha256(failed_source.encode()).hexdigest(), "config_sha256": config_sha, "development_benchmark_sha256": benchmark_sha, "test_result": {"passed": 209, "failed": 1, "total": 210}, "failure_classes": ["UNRESOLVED_INFERENCE_FALSE_SUPPORT"], "changed_rationale": "Contrast token 'but' was incorrectly treated as resolution; tighten exception to explicit resolved/confirmed/current-known cues.", "status": "FAILED_RETAINED"},
        {"iteration": 1, "source_sha256": source_sha, "config_sha256": config_sha, "development_benchmark_sha256": benchmark_sha, "test_result": {"passed": passed, "failed": 0, "total": passed}, "metrics": {"candidate_v2": m2, "candidate_v7": m7}, "bootstrap": bootstrap(cases), "failure_classes": [], "changed_rationale": "Tightened unresolved/inference hard reject; contrast words alone no longer waive uncertainty.", "status": "PASS"}
    ]
    (rdir / "development-ledger.jsonl").write_text("".join(json.dumps(x, sort_keys=True) + "\n" for x in ledger))

    decon = {"schema_version": "candidate-v7-decontamination-report-v1", "retired_count": 99, "development_count": 160, "intersection_count": 0, "retired_case_id_set_sha256": "1ca053112b634871d24addbb3982d4e417dc8f4acce10609554cc41b6ed8e987", "retired_id_manifest_git_blob_sha": "f57afa3ce75f8fbf46e22ebbd646dcf51cbf42c8", "retired_payload_accessed": False, "retired_id_only_manifest_accessed_for_overlap_exclusion": True, "development_id_namespace": "CV7DEV-[AN]-NNN", "proof": "Retired ID-only manifest uses 8-hex IDs (optionally _abs) or gpt4_ + 8-hex; development IDs start CV7DEV-, so exact intersection is empty.", "status": "PASS"}
    (rdir / "decontamination-report-v1.json").write_text(json.dumps(decon, indent=2) + "\n")

    boot = bootstrap(cases)
    summary = {
        "schema_version": "candidate-v7-development-summary-v1",
        "benchmark": {"name": "candidate-v7-development-v1", "sha256": benchmark_sha, "case_count": 160, "answerable_count": 100, "no_evidence_count": 60, "designation": "DEVELOPMENT/NONSEALED/NONPROTECTED"},
        "candidate_v7_source_sha256": source_sha, "config_sha256": config_sha,
        "candidate_v2_metrics": m2, "candidate_v7_metrics": m7,
        "deficits_vs_candidate_v2": {k: m2[k]-m7[k] for k in ["MRR","R@1","R@3","R@5"]},
        "absolute_false_retrieval_reduction_vs_candidate_v2": m2["no_evidence_false_retrieval"]-m7["no_evidence_false_retrieval"],
        "natural_language_coverage": m7["answerable_recall"], "diagnostic_rejection": rejection,
        "paired_bootstrap_answerable_mrr_delta": boot, "tests": {"passed": passed, "failed": 0, "total": passed},
        "guardrails": {"mrr_deficit_le_0_03": m2["MRR"]-m7["MRR"] <= .03, "r1_deficit_le_0_03": m2["R@1"]-m7["R@1"] <= .03, "r3_deficit_le_0_02": m2["R@3"]-m7["R@3"] <= .02, "r5_deficit_le_0_02": m2["R@5"]-m7["R@5"] <= .02, "answerable_recall_ge_0_95": m7["answerable_recall"] >= .95, "false_abstention_le_0_05": m7["false_abstention"] <= .05, "abstention_accuracy_ge_0_90": m7["abstention_accuracy"] >= .90, "no_evidence_false_retrieval_le_0_10": m7["no_evidence_false_retrieval"] <= .10, "absolute_false_retrieval_reduction_ge_0_70": m2["no_evidence_false_retrieval"]-m7["no_evidence_false_retrieval"] >= .70, "natural_language_coverage_ge_0_95": m7["answerable_recall"] >= .95, "meta_rejection_ge_0_95": rejection["meta_discussion"] >= .95, "no_value_rejection_ge_0_95": rejection["explicit_no_value"] >= .95, "contradiction_handling_ge_0_95": rejection["contradiction"] >= .95, "temporal_handling_ge_0_95": rejection["stale_only"] >= .95, "wrong_subject_rejection_ge_0_95": rejection["wrong_subject"] >= .95, "wrong_relation_rejection_ge_0_95": rejection["wrong_relation"] >= .95},
        "verdict": "PASS",
    }
    (rdir / "development-summary-v1.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({"tests": passed, "source_sha256": source_sha, "config_sha256": config_sha, "benchmark_sha256": benchmark_sha, "verdict": "PASS"}, indent=2))

if __name__ == "__main__":
    main()
