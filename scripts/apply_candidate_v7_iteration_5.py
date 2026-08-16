from __future__ import annotations

import hashlib
from pathlib import Path

PATH = Path("src/personal_state_engine/candidate_v7.py")
SHA_RECORD = Path("results/candidate-v7/iteration-5-source-sha256.txt")

text = PATH.read_text()

replacements = [
    (
        '    r"(?:do|does|did)\\s+not\\s+know|not\\s+known|hasn[\'’]?t\\s+been\\s+decided|not\\s+decided|cannot\\s+determine)\\b",\n',
        '    r"(?:do|does|did)\\s+not\\s+know|not\\s+known|hasn[\'’]?t\\s+been\\s+decided|not\\s+decided|cannot\\s+determine|"\n'
        '    r"(?:is|are|remains?)\\s+(?:unknown|unavailable|unspecified|unclear))\\b",\n',
    ),
    (
        '    "education": {"university", "college", "school", "course", "class", "study", "studies", "learning", "learn", "enrolled", "graduated", "degree"},\n',
        '    "education_institution": {"university", "college", "school", "campus", "attend", "attends", "student", "graduated", "degree", "studies"},\n'
        '    "education_course": {"course", "class", "module", "subject", "enrolled", "taking", "study", "studying", "learning", "learn"},\n',
    ),
    (
'''def _relation_compatible(query: str, text: str) -> tuple[bool, set[str]]:
    qf = _families(query)
    mf = _families(text)
    if not qf:
        return True, set()
    shared = qf & mf
    return bool(shared), shared
''',
'''def _relation_compatible(query: str, text: str) -> tuple[bool, set[str]]:
    qf = _families(query)
    mf = _families(text)
    if not qf:
        return True, set()
    shared = qf & mf
    if shared:
        return True, shared

    # Open-valued attributes (colour/name/type/version/size) often omit the
    # relation word in the evidence itself: "the backpack is cobalt blue".
    # Permit that deterministic form only when there is no conflicting typed
    # family, the entity/content anchor is strong, and the surface is copular.
    if qf == {"identity_attribute"} and not mf:
        copular = bool(re.search(r"\\b(?:is|are|was|were|called|named)\\b", text, re.I))
        if copular and _anchor_coverage(query, text) >= 0.50:
            return True, {"identity_attribute:implicit"}
    return False, set()
''',
    ),
]

for old, new in replacements:
    if old not in text:
        raise SystemExit(f"required iteration-5 patch anchor missing: {old[:120]!r}")
    text = text.replace(old, new, 1)

required = [
    'education_institution',
    'education_course',
    'identity_attribute:implicit',
    '(?:is|are|remains?)\\s+(?:unknown|unavailable|unspecified|unclear)',
]
for marker in required:
    if marker not in text:
        raise SystemExit(f"iteration-5 postcondition missing: {marker}")
if '    "education": {' in text:
    raise SystemExit("broad education family must be removed")

PATH.write_text(text)
actual = hashlib.sha256(PATH.read_bytes()).hexdigest()
SHA_RECORD.parent.mkdir(parents=True, exist_ok=True)
SHA_RECORD.write_text(actual + "\n")
print(actual)
