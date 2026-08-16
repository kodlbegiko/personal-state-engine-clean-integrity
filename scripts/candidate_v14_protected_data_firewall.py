from __future__ import annotations
import hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SCAN_ROOTS=[ROOT/'src',ROOT/'scripts',ROOT/'tests',ROOT/'data/candidate-v14-development']
FORBIDDEN=[re.compile(r'ev[-_]?a[-_]?v4.*(?:case|query|memory|assignment|seed)',re.I),re.compile(r'ev[-_]?[bc][-_]?v4.*(?:assignment|case|seed)',re.I),re.compile(r'protected.*(?:case[_ -]?id|query[_ -]?text|memory[_ -]?text|assignment|seed)',re.I),re.compile(r'formal[_ -]?assignment',re.I)]
ALLOW_FILES={'candidate_v14_protected_data_firewall.py'};TEXT_SUFFIXES={'.py','.json','.md','.txt','.toml','.yaml','.yml'}
def sha256(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest()
def main()->int:
    violations=[];scanned=[]
    for root in SCAN_ROOTS:
        if not root.exists():continue
        for p in sorted(root.rglob('*')):
            if not p.is_file() or p.suffix.lower() not in TEXT_SUFFIXES or '__pycache__' in p.parts:continue
            rel=p.relative_to(ROOT).as_posix();scanned.append({'path':rel,'sha256':sha256(p)})
            if p.name in ALLOW_FILES:continue
            # Holdout is hashed but not content-inspected before qualification freeze.
            if rel=='data/candidate-v14-development/untouched-internal-holdout.json':continue
            text=p.read_text(encoding='utf-8',errors='replace')
            for rx in FORBIDDEN:
                for m in rx.finditer(text):violations.append({'path':rel,'pattern':rx.pattern,'match':m.group(0)[:160]})
    out={'schema_version':'candidate-v14-protected-firewall-v1','scope':'Candidate-v14 executable/development assets; holdout content excluded pre-freeze; historical aggregate evidence allowed','scanned_file_count':len(scanned),'violations':violations,'protected_case_level_data_used':False if not violations else None,'protected_assignment_reconstruction':False if not violations else None,'status':'PASS' if not violations else 'FAIL','files':scanned}
    path=ROOT/'results/candidate-v14/protected-data-firewall.json';path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n');print(json.dumps(out,indent=2));return 0 if not violations else 2
if __name__=='__main__':raise SystemExit(main())
