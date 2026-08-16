from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from candidate_v13_external_runtime_eval import evaluate

ROOT=Path(__file__).resolve().parents[1]
R=ROOT/'results/candidate-v13-external-validity'
D=ROOT/'docs/research/candidate-v13-external-validity'
THRESH=json.loads((D/'formal-thresholds-v1.json').read_text())
COLLAPSE=json.loads((D/'anti-collapse-policy-v1.json').read_text())
FEAS=json.loads((R/'joint-feasibility.json').read_text())
CONT=json.loads((R/'contamination-audit.json').read_text())
QUAL=json.loads((R/'evermembench-dynamic-qualification.json').read_text())


def combined(group:dict[str,Any])->dict[str,Any]:
    n=int(group.get('count',0)); a=int(group.get('answerable',0)); z=int(group.get('no_evidence',0))
    r1=float(group.get('R@1',0.0)); fr=float(group.get('false_retrieval_rate',0.0)); fa=float(group.get('false_abstention_rate',0.0))
    correct_rank1=r1*a; correct_abstain=(1-fr)*z; decision=(correct_rank1+correct_abstain)/n if n else 0.0
    abst=( (1-fa)*a + (1-fr)*z )/n if n else 0.0
    return {**group,'combined_decision_accuracy':decision,'abstention_accuracy':abst}


def anti_collapse(result:dict[str,Any], structural:dict[str,Any], domains:dict[str,Any])->dict[str,Any]:
    c=result['case_counts']; total=int(c['total']); a=int(c['answerable']); z=int(c['no_evidence']); m=result['metrics']
    retrieved=a*(1-float(m['false_abstention_rate'])) + z*float(m['false_retrieval_rate'])
    retrieval_prop=retrieved/total if total else 0.0; abstain_prop=1-retrieval_prop
    structural_bad=[k for k,v in structural.items() if float(v['combined_decision_accuracy'])<0.70]
    domain_bad=[k for k,v in domains.items() if float(v['combined_decision_accuracy'])<0.70]
    flags={
      'universal_retrieval': retrieval_prop>=1-1e-12,
      'universal_abstention': abstain_prop>=1-1e-12,
      'near_universal_retrieval': retrieval_prop>=0.98,
      'near_universal_abstention': abstain_prop>=0.98,
      'single_class_prediction_collapse': retrieval_prop>=0.98 or abstain_prop>=0.98,
      'structural_family_collapse':bool(structural_bad),
      'domain_specific_collapse':bool(domain_bad),
    }
    passed=not any([flags['universal_retrieval'],flags['universal_abstention'],flags['single_class_prediction_collapse'],flags['structural_family_collapse'],flags['domain_specific_collapse']])
    return {'retrieval_proportion':retrieval_prop,'abstention_proportion':abstain_prop,'flags':flags,'structural_families_below_0_70':structural_bad,'domains_below_0_70':domain_bad,'pass':passed}


def aggregate_checks(stage:str,m:dict[str,float])->dict[str,bool]:
    t=THRESH[stage]['aggregate']; checks={}
    for key,val in t.items():
        if key.endswith('_min'):
            metric=key[:-4]; checks[key]=float(m[metric])>=float(val)
        elif key.endswith('_max'):
            metric=key[:-4]; checks[key]=float(m[metric])<=float(val)
    return checks


def frame_checks(stage:str,m:dict[str,float])->dict[str,bool]:
    if stage!='ev_b': return {}
    t=THRESH['ev_b']['frame']; checks={}
    for key,val in t.items():
        if key.endswith('_min'): checks[key]=float(m[key[:-4]])>=float(val)
        elif key.endswith('_max'): checks[key]=float(m[key[:-4]])<=float(val)
    return checks


def structural_checks(stage:str,structural:dict[str,Any])->dict[str,bool]:
    if stage=='ev_b':
        floors=THRESH['ev_b']['structural_accuracy_floors']; return {fam:float(structural[fam]['combined_decision_accuracy'])>=float(floor) for fam,floor in floors.items()}
    catastrophic=float(THRESH['ev_c']['catastrophic_structural_accuracy_below']); return {fam:float(v['combined_decision_accuracy'])>=catastrophic for fam,v in structural.items()}


def freshness(stage:str,result:dict[str,Any])->dict[str,Any]:
    selected=result['selection_digest']; expected=FEAS['stages'][stage]['selected_base_id_digest']
    other={s:FEAS['stages'][s]['selected_base_id_digest'] for s in FEAS['stages'] if s!=stage}
    return {
      'schema_version':'candidate-v13-external-freshness-audit-v1',
      'stage':stage,
      'selection_digest_matches_preperformance_feasibility':selected==expected,
      'selection_digest':selected,
      'other_stage_selection_digests':other,
      'digest_distinct_from_other_stages':all(selected!=x for x in other.values()),
      'preperformance_contamination_status':CONT['status'],
      'preperformance_material_contamination_count':CONT['material_contaminated_base_count'],
      'evermembench_revision':QUAL['revision'],
      'evermembench_qualified_pre_candidate_execution':QUAL['status']=='QUALIFIED_PRE_CANDIDATE_EXECUTION',
      'source_stage_disjointness_preproved':True,
      'normalized_query_reuse_across_stages_preproved':False,
      'pass': selected==expected and all(selected!=x for x in other.values()) and CONT['status']=='PASS_NO_MATERIAL_CONTAMINATION' and CONT['material_contaminated_base_count']==0 and QUAL['status']=='QUALIFIED_PRE_CANDIDATE_EXECUTION'
    }


def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('--stage',choices=['ev_b','ev_c'],required=True); args=ap.parse_args(); stage=args.stage
    result=evaluate(stage,execute=True)
    structural={k:combined(v) for k,v in result['breakdown']['family'].items()}; domains={k:combined(v) for k,v in result['breakdown']['domain'].items()}; sources={k:combined(v) for k,v in result['breakdown']['source'].items()}
    anti=anti_collapse(result,structural,domains); integ=result['integrity']; fresh=freshness(stage,result)
    achecks=aggregate_checks(stage,result['metrics']); fchecks=frame_checks(stage,result['metrics']); schecks=structural_checks(stage,structural)
    core_integrity=bool(integ['candidate_source_invariant_pass'] and integ['determinism_pass'] and integ['metadata_firewall_pass'] and fresh['pass'])
    anti_ok=anti['pass']; integrity_ok=core_integrity and anti_ok
    performance_ok=all(achecks.values()) and all(fchecks.values()) and all(schecks.values())
    if not core_integrity:
        decision='EXTERNAL_VALIDITY_INVALID — RESEARCH_INTEGRITY_FAILURE'
    elif not anti_ok:
        decision='CANDIDATE_V13_EXTERNAL_VALIDITY_FAIL — CANDIDATE_V14_AUTHORIZED'
    elif not performance_ok:
        decision='CANDIDATE_V13_EXTERNAL_VALIDITY_FAIL — CANDIDATE_V14_AUTHORIZED'
    elif stage=='ev_b':
        decision='EV_B_PASS — EV_C_AUTHORIZED'
    else:
        decision='CANDIDATE_V13_EXTERNAL_VALIDITY_PASS'
    prefix=stage.replace('_','-')
    summary={k:v for k,v in result.items() if k not in {'breakdown','integrity'}}; summary.update({'formal_stage':True,'aggregate_threshold_checks':achecks,'frame_threshold_checks':fchecks,'structural_threshold_checks':schecks,'performance_pass':performance_ok,'decision':decision})
    integrity={'schema_version':'candidate-v13-external-formal-integrity-v1','stage':stage,**integ,'freshness_pass':fresh['pass'],'anti_collapse':anti,'anti_collapse_pass':anti_ok,'core_integrity_pass':core_integrity,'formal_integrity_pass':integrity_ok,'decision':decision}
    structural_out={'schema_version':'candidate-v13-external-structural-v1','stage':stage,'families':structural,'threshold_checks':schecks}
    domain_out={'schema_version':'candidate-v13-external-domain-v1','stage':stage,'domains':domains,'sources':sources}
    (R/f'{prefix}-summary.json').write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n')
    (R/f'{prefix}-integrity.json').write_text(json.dumps(integrity,indent=2,sort_keys=True)+'\n')
    (R/f'{prefix}-structural.json').write_text(json.dumps(structural_out,indent=2,sort_keys=True)+'\n')
    (R/f'{prefix}-domain.json').write_text(json.dumps(domain_out,indent=2,sort_keys=True)+'\n')
    (R/f'{prefix}-freshness-audit.json').write_text(json.dumps(fresh,indent=2,sort_keys=True)+'\n')
    return 0

if __name__=='__main__': raise SystemExit(main())
