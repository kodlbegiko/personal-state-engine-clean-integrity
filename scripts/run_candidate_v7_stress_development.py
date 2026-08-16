from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from personal_state_engine.candidate_v2 import pse_candidate_v2_rank
from personal_state_engine.candidate_v7 import pse_candidate_v7_rank


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def memory(mid: str, text: str, timestamp: str = "2026-08-12T10:00:00+00:00") -> dict:
    return {"id": mid, "text": text, "timestamp": timestamp}


def answerable_cases() -> list[dict]:
    rows = [
        ("language", "What language does Alina speak?", "Alina speaks Portuguese fluently."),
        ("education", "Which university does Bram attend?", "Bram studies at Redwood University."),
        ("music", "What music does Cora listen to?", "Cora listens to ambient jazz while working."),
        ("medication", "What medication does Dario take?", "Dario takes melatonin at night."),
        ("allergy", "What is Esme allergic to?", "Esme is allergic to shellfish."),
        ("device", "What laptop does Farah use?", "Farah uses a ThinkPad X1 Carbon."),
        ("color", "What color is Gio's backpack?", "Gio's backpack is cobalt blue."),
        ("size", "What shoe size does Hana wear?", "Hana's shoe size is 38 EU."),
        ("relationship", "Who is Ivan married to?", "Ivan is married to Noor."),
        ("pet_name", "What is Jules's dog's name?", "Jules has a dog called Mochi."),
        ("book", "What book is Kira reading?", "Kira is reading The Left Hand of Darkness."),
        ("course", "What course is Leon taking?", "Leon is enrolled in organic chemistry."),
        ("skill", "What skill does Mina practice?", "Mina practices conversational Japanese every morning."),
        ("goal", "What goal is Niko training toward?", "Niko is training toward a half marathon."),
        ("membership", "Which club did Orla join?", "Orla joined the astronomy club."),
        ("car", "What car does Pavel drive?", "Pavel drives a silver Corolla."),
        ("bus", "Which bus does Quinn take?", "Quinn rides bus 307 to work."),
        ("movie", "What movie does Rina watch often?", "Rina watches Arrival every winter."),
        ("game", "What game does Sami play?", "Sami plays Go with friends on Fridays."),
        ("perform", "What instrument does Tessa perform on?", "Tessa performs on the oboe in the community orchestra."),
    ]
    cases = []
    for i, (category, query, text) in enumerate(rows):
        rid = f"CV7STRESS-A-{i:03d}-rel"
        memories = [
            memory(rid, text),
            memory(f"CV7STRESS-A-{i:03d}-d1", "Agenda item: discuss unrelated travel details."),
            memory(f"CV7STRESS-A-{i:03d}-d2", "No confirmed answer is recorded for this unrelated topic."),
            memory(f"CV7STRESS-A-{i:03d}-d3", "What should be reviewed at the next meeting?"),
            memory(f"CV7STRESS-A-{i:03d}-d4", "This unrelated issue remains unresolved."),
        ]
        cases.append({
            "id": f"CV7STRESS-A-{i:03d}",
            "category": category,
            "query": query,
            "memories": memories,
            "relevant_memory_ids": [rid],
            "designation": "DEVELOPMENT",
            "protection": "NONSEALED_NONPROTECTED_PRE_FREEZE_STRESS",
        })
    return cases


def negative_cases() -> list[dict]:
    rows = [
        ("wrong_subject_language", "What language does Alina speak?", "Bea speaks Portuguese fluently."),
        ("wrong_relation_education", "Which university does Bram attend?", "Bram drives a blue sedan."),
        ("meta_music", "What music does Cora listen to?", "We discussed the query about Cora's music preference."),
        ("unresolved_medication", "What medication does Dario take?", "Dario probably takes melatonin, but this remains uncertain."),
        ("no_value_allergy", "What is Esme allergic to?", "No confirmed information about Esme's allergy is available."),
        ("question_device", "What laptop does Farah use?", "What laptop does Farah use?"),
        ("wrong_subject_color", "What color is Gio's backpack?", "Nora's backpack is cobalt blue."),
        ("wrong_subject_size", "What shoe size does Hana wear?", "Mira's shoe size is 38 EU."),
        ("agenda_relationship", "Who is Ivan married to?", "Agenda item: discuss whether Ivan is married."),
        ("no_value_pet", "What is Jules's dog's name?", "The dog's name is not recorded."),
        ("review_book", "What book is Kira reading?", "Review topic: Kira's current book."),
        ("wrong_relation_course", "What course is Leon taking?", "Leon lives near the university."),
        ("stale_skill", "What skill does Mina practice?", "Mina used to practice conversational Japanese, but no longer does."),
        ("unresolved_goal", "What goal is Niko training toward?", "Niko might train for a race; the target is unresolved."),
        ("meta_membership", "Which club did Orla join?", "The prompt mentions Orla and an astronomy club."),
        ("wrong_subject_car", "What car does Pavel drive?", "Iris drives a silver Corolla."),
        ("no_value_bus", "Which bus does Quinn take?", "Quinn's bus route is unknown."),
        ("question_movie", "What movie does Rina watch often?", "What movie does Rina watch often?"),
        ("wrong_subject_game", "What game does Sami play?", "Tariq plays Go with friends."),
        ("stale_perform", "What instrument does Tessa perform on?", "Tessa formerly performed on the oboe but no longer performs."),
    ]
    cases = []
    for i, (category, query, text) in enumerate(rows):
        cases.append({
            "id": f"CV7STRESS-N-{i:03d}",
            "category": category,
            "query": query,
            "memories": [
                memory(f"CV7STRESS-N-{i:03d}-x", text),
                memory(f"CV7STRESS-N-{i:03d}-d1", "Agenda: review an unrelated topic later."),
                memory(f"CV7STRESS-N-{i:03d}-d2", "No confirmed answer is recorded."),
                memory(f"CV7STRESS-N-{i:03d}-d3", "This issue remains unresolved."),
            ],
            "relevant_memory_ids": [],
            "designation": "DEVELOPMENT",
            "protection": "NONSEALED_NONPROTECTED_PRE_FREEZE_STRESS",
        })
    return cases


def main() -> None:
    answerable = answerable_cases()
    negatives = negative_cases()
    cases = answerable + negatives

    benchmark = {
        "schema_version": "candidate-v7-development-stress-v1",
        "designation": "DEVELOPMENT",
        "protection": "NONSEALED_NONPROTECTED_PRE_FREEZE_STRESS",
        "case_count": len(cases),
        "answerable_count": len(answerable),
        "no_evidence_count": len(negatives),
        "cases": cases,
    }
    benchmark_path = ROOT / "experiments" / "benchmarks" / "candidate-v7-development-stress-v1.json"
    benchmark_path.parent.mkdir(parents=True, exist_ok=True)
    benchmark_path.write_text(json.dumps(benchmark, indent=2) + "\n")

    positive_rows = []
    for case in answerable:
        v2 = pse_candidate_v2_rank(case, 5)
        v7 = pse_candidate_v7_rank(case, 5)
        positive_rows.append({
            "id": case["id"],
            "category": case["category"],
            "v2": v2,
            "v7": v7,
            "supported": bool(v7),
            "ranking_preserved": v7 == v2,
        })

    negative_rows = []
    for case in negatives:
        v7 = pse_candidate_v7_rank(case, 5)
        negative_rows.append({
            "id": case["id"],
            "category": case["category"],
            "v7": v7,
            "abstained": v7 == [],
        })

    positive_pass = sum(row["supported"] and row["ranking_preserved"] for row in positive_rows)
    negative_pass = sum(row["abstained"] for row in negative_rows)
    source_path = ROOT / "src" / "personal_state_engine" / "candidate_v7.py"
    config_path = ROOT / "experiments" / "configs" / "candidate-v7-v1.json"

    summary = {
        "schema_version": "candidate-v7-development-stress-summary-v1",
        "candidate_v7_source_sha256": sha(source_path),
        "config_sha256": sha(config_path),
        "benchmark_sha256": sha(benchmark_path),
        "answerable_supported_and_ranking_preserved": positive_pass,
        "answerable_total": len(answerable),
        "negative_correct_abstention": negative_pass,
        "negative_total": len(negatives),
        "answerable_rate": positive_pass / len(answerable),
        "negative_abstention_rate": negative_pass / len(negatives),
        "positive_rows": positive_rows,
        "negative_rows": negative_rows,
        "verdict": "PASS" if positive_pass == len(answerable) and negative_pass == len(negatives) else "FAIL",
    }
    result_dir = ROOT / "results" / "candidate-v7"
    result_dir.mkdir(parents=True, exist_ok=True)
    (result_dir / "development-stress-summary-v1.json").write_text(json.dumps(summary, indent=2) + "\n")

    if summary["verdict"] != "PASS":
        print(json.dumps(summary, indent=2))
        raise SystemExit(1)
    print(json.dumps({k: summary[k] for k in ["candidate_v7_source_sha256", "benchmark_sha256", "answerable_rate", "negative_abstention_rate", "verdict"]}, indent=2))


if __name__ == "__main__":
    main()
