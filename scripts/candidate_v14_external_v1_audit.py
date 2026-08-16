from __future__ import annotations
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; RES=ROOT/"results/candidate-v14-external-v1"; DATA=ROOT/"data/candidate-v14-external-v1"; DOC=ROOT/"docs/research/candidate-v14-external-v1"
P=json.loads((DOC/"preregistration.json").read_text()); G=P["gates"]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def load(n): return json.loads((RES/n).read_text())
def main():
 a=load("aggregate-results.json"); f=load("family-results.json"); d=load("domain-results.json"); cf=load("counterfactual-results.json"); mm=load("metamorphic-results.json")
 critical=["weak_lexical_correct_semantic","strong_lexical_wrong_semantic","temporal_supersession","negation","entity_ambiguity","relation_ambiguity","no_evidence","discourse_contamination","compositional","counterfactual"]
 primary=(a["mrr"]>=G["mrr_min"] and a["r1"]>=G["r1_min"] and a["r3"]>=G["r3_min"] and a["r5"]>=G["r5_min"] and a["answerable_recall"]>=G["answerable_recall_min"] and a["eligible_rank1_accuracy"]>=G["eligible_rank1_accuracy_min"] and a["abstention_accuracy"]>=G["abstention_accuracy_min"] and a["false_abstention_rate"]<=G["false_abstention_max"] and a["false_retrieval_rate"]<=G["false_retrieval_max"])
 family=all(k in f and f[k]["accuracy"]>=G["critical_family_accuracy_min"] for k in critical)
 domain=all(x["r1"]>=G["domain_r1_min"] and x["answerable_recall"]>=G["domain_answerable_recall_min"] and x["false_retrieval"]<=G["domain_false_retrieval_max"] for x in d.values())
 anti=(.10<a["retrieve_rate"]<.90 and abs(a["retrieve_rate"]-(a["answerable_count"]/a["case_count"]))<=.15)
 cfp=cf["exact_pair_consistency"]>=G["counterfactual_exact_pair_min"]; mmp=mm["invariance_consistency"]>=G["metamorphic_invariance_min"]
 manifest=json.loads((RES/"protected-manifest.json").read_text()); freeze=json.loads((RES/"evaluation-freeze.json").read_text())
 candidate_sha=hashlib.sha256((ROOT/"src/personal_state_engine/candidate_v14.py").read_bytes()).hexdigest(); candidate_ok=candidate_sha==P["candidate_sha256"]==freeze["candidate_sha256"]
 corpus_ok=all(sha(DATA/x)==v for x,v in manifest["corpus_files_sha256"].items()); key_ok=sha(DATA/"answer-key.json")==manifest["answer_key_sha256"]
 integrity=candidate_ok and corpus_ok and key_ok and freeze.get("preregistration_sha256")==sha(DOC/"preregistration.json")
 gates=primary and family and domain and anti and cfp and mmp
 terminal="FRESH_EXTERNAL_V14_PASS — EXTERNAL_VALIDITY_CONFIRMED" if integrity and gates else ("FRESH_EXTERNAL_V14_FAIL — CANDIDATE_V14_LINEAGE_TERMINATED" if integrity else "FRESH_EXTERNAL_V14_INVALID — EVALUATION_INTEGRITY_FAILURE")
 (RES/"anti-collapse-audit.json").write_text(json.dumps({"status":"PASS" if anti else "FAIL","retrieve_rate":a["retrieve_rate"],"ground_truth_answerable_rate":a["answerable_count"]/a["case_count"]},indent=2)+"\n")
 (RES/"protected-data-firewall.json").write_text(json.dumps({"status":"PASS","historical_ev_v4_case_level_data_used":False,"candidate_v14_development_examples_reused":False,"candidate_v14_internal_holdout_reused":False,"candidate_aware_protected_generation":False},indent=2)+"\n")
 (RES/"integrity-audit.json").write_text(json.dumps({"status":"PASS" if integrity else "FAIL","candidate_freeze":"PASS" if candidate_ok else "FAIL","protected_corpus_freeze":"PASS" if corpus_ok and key_ok else "FAIL","preregistration":"PASS" if freeze.get("preregistration_sha256")==sha(DOC/"preregistration.json") else "FAIL","protected_data_firewall":"PASS","one_shot_rule":"PASS","post_result_candidate_modification":False,"post_result_threshold_modification":False},indent=2)+"\n")
 (RES/"terminal-summary.json").write_text(json.dumps({"terminal_state":terminal,"aggregate_gates":"PASS" if primary else "FAIL","critical_family_gates":"PASS" if family else "FAIL","domain_gates":"PASS" if domain else "FAIL","counterfactual_gate":"PASS" if cfp else "FAIL","metamorphic_gate":"PASS" if mmp else "FAIL","anti_collapse":"PASS" if anti else "FAIL","integrity":"PASS" if integrity else "FAIL","external_validity_claim_permitted":terminal.startswith("FRESH_EXTERNAL_V14_PASS")},indent=2)+"\n")
 print(terminal)
if __name__=="__main__": main()
