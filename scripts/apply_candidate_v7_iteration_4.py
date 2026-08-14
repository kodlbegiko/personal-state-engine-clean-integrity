from __future__ import annotations

import hashlib
from pathlib import Path

PATH = Path("src/personal_state_engine/candidate_v7.py")
SHA_RECORD = Path("results/candidate-v7/iteration-4-source-sha256.txt")

text = PATH.read_text()

replacements = [
    (
        'STALE_CUES = {_stem(x) for x in {"old", "previous", "prior", "formerly", "used", "before", "stale", "superseded", "obsolete"}}',
        'STALE_CUES = {_stem(x) for x in {"old", "previous", "prior", "formerly", "stale", "superseded", "obsolete"}}',
    ),
    (
        '    "activity_hobby": {"hobby", "activity", "play", "plays", "practice", "practices", "train", "training", "read", "run", "hike", "climb", "swim", "paint", "cook"},\n',
        '    "activity_hobby": {"hobby", "activity", "play", "plays", "practice", "practices", "train", "training", "read", "run", "hike", "climb", "swim", "paint", "cook", "perform", "performs", "performing"},\n',
    ),
    (
        '    "relationship": {"mother", "father", "sister", "brother", "partner", "spouse", "friend", "colleague", "child", "children", "family"},\n',
        '    "relationship": {"mother", "father", "sister", "brother", "partner", "spouse", "friend", "colleague", "child", "children", "family", "married", "marry"},\n',
    ),
    (
        '    "status_state": {"status", "state", "current", "latest", "now", "became", "changed", "updated", "completed", "active", "inactive"},\n',
        '    "status_state": {"status", "state", "current", "latest", "now", "became", "changed", "updated", "completed", "active", "inactive"},\n'
        '    "music_media": {"music", "song", "songs", "listen", "listens", "listening", "album", "movie", "film", "watch", "watches", "book", "reading"},\n'
        '    "health": {"health", "allergy", "allergic", "medication", "medicine", "doctor", "condition", "takes", "taking"},\n'
        '    "device": {"laptop", "computer", "phone", "device", "tablet", "macbook", "uses", "use", "carry", "carries", "carrying"},\n'
        '    "goal": {"goal", "target", "aim", "training", "train", "working", "toward", "prepare", "preparing"},\n'
        '    "transport": {"car", "drive", "drives", "driving", "bus", "route", "commute", "ride", "rides", "bike", "bicycle"},\n'
        '    "education": {"university", "college", "school", "course", "class", "study", "studies", "learning", "learn", "enrolled", "graduated", "degree"},\n'
        '    "language": {"language", "speak", "speaks", "fluent", "learning", "learn", "study", "studies"},\n'
        '    "identity_attribute": {"name", "called", "color", "colour", "size", "type", "kind", "version"},\n'
        '    "membership": {"club", "team", "member", "membership", "join", "joined"},\n',
    ),
    (
'''def _temporal_scope(text: str) -> str:
    stems = _stems(text)
    if stems & UPDATE_CUES:
        return "CURRENT"
    if stems & STALE_CUES:
        return "STALE"
    return "UNSPECIFIED"
''',
'''def _temporal_scope(text: str) -> str:
    stems = _stems(text)
    if stems & UPDATE_CUES:
        return "CURRENT"
    if stems & STALE_CUES or re.search(r"\\b(?:used to|previously|formerly|no longer|before (?:that|the change|it was))\\b", text, re.I):
        return "STALE"
    return "UNSPECIFIED"
''',
    ),
    (
'''def _current_query(query: str) -> bool:
    return bool(_stems(query) & CURRENT_CUES)
''',
'''def _current_query(query: str) -> bool:
    stems = _stems(query)
    if stems & STALE_CUES or re.search(r"\\b(?:used to|formerly|previously|historical|old|prior)\\b", query, re.I):
        return False
    return bool(stems & CURRENT_CUES) or bool(re.search(r"\\b(?:does|is|are|has|have)\\b", query, re.I))
''',
    ),
]

for old, new in replacements:
    if old not in text:
        raise SystemExit(f"required iteration-4 patch anchor missing: {old[:100]!r}")
    text = text.replace(old, new, 1)

required_markers = [
    '"music_media"', '"health"', '"device"', '"goal"', '"transport"',
    '"education"', '"language"', '"identity_attribute"', '"membership"',
    'performing', 'married', 'before (?:that|the change|it was)',
    'bool(re.search(r"\\b(?:does|is|are|has|have)\\b", query, re.I))',
]
for marker in required_markers:
    if marker not in text:
        raise SystemExit(f"iteration-4 postcondition missing: {marker}")

stale_line = next(line for line in text.splitlines() if line.startswith("STALE_CUES ="))
if '"used"' in stale_line or '"before"' in stale_line:
    raise SystemExit("generic used/before must not remain in STALE_CUES")

PATH.write_text(text)
actual = hashlib.sha256(PATH.read_bytes()).hexdigest()
SHA_RECORD.parent.mkdir(parents=True, exist_ok=True)
SHA_RECORD.write_text(actual + "\n")
print(actual)
