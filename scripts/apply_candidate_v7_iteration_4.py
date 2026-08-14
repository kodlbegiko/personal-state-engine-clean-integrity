from __future__ import annotations

import hashlib
from pathlib import Path

PATH = Path("src/personal_state_engine/candidate_v7.py")
EXPECTED_SHA256 = "5b8c008176cec2480ddefee5d713f24f5450143e124a278d98ff1605a7b4c0e8"

text = PATH.read_text()

text = text.replace(
    'STALE_CUES = {_stem(x) for x in {"old", "previous", "prior", "formerly", "used", "before", "stale", "superseded", "obsolete"}}',
    'STALE_CUES = {_stem(x) for x in {"old", "previous", "prior", "formerly", "stale", "superseded", "obsolete"}}',
)
text = text.replace(
    '    "activity_hobby": {"hobby", "activity", "play", "plays", "practice", "practices", "train", "training", "read", "run", "hike", "climb", "swim", "paint", "cook"},\n',
    '    "activity_hobby": {"hobby", "activity", "play", "plays", "practice", "practices", "train", "training", "read", "run", "hike", "climb", "swim", "paint", "cook", "perform", "performs", "performing"},\n',
)
text = text.replace(
    '    "relationship": {"mother", "father", "sister", "brother", "partner", "spouse", "friend", "colleague", "child", "children", "family"},\n',
    '    "relationship": {"mother", "father", "sister", "brother", "partner", "spouse", "friend", "colleague", "child", "children", "family", "married", "marry"},\n',
)
text = text.replace(
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
)
text = text.replace(
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
)
text = text.replace(
'''def _current_query(query: str) -> bool:
    return bool(_stems(query) & CURRENT_CUES)
''',
'''def _current_query(query: str) -> bool:
    stems = _stems(query)
    if stems & STALE_CUES or re.search(r"\\b(?:used to|formerly|previously|historical|old|prior)\\b", query, re.I):
        return False
    return bool(stems & CURRENT_CUES) or bool(re.search(r"\\b(?:does|is|are|has|have)\\b", query, re.I))
''',
)

PATH.write_text(text)
actual = hashlib.sha256(PATH.read_bytes()).hexdigest()
if actual != EXPECTED_SHA256:
    raise SystemExit(f"candidate_v7 iteration-4 hash mismatch: {actual} != {EXPECTED_SHA256}")
print(actual)
