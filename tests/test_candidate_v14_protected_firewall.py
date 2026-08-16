import json, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def test_protected_firewall_passes():
    p=subprocess.run([sys.executable,str(ROOT/'scripts/candidate_v14_protected_data_firewall.py')],cwd=ROOT,capture_output=True,text=True)
    assert p.returncode==0,p.stdout+p.stderr
    out=json.loads((ROOT/'results/candidate-v14/protected-data-firewall.json').read_text())
    assert out['status']=='PASS' and out['violations']==[]
