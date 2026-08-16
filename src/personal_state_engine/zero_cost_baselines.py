from __future__ import annotations

import math
import re
from collections import Counter
from datetime import datetime, timezone
from typing import Any

TOKEN_RE = re.compile(r"[\w\u4e00-\u9fff]+", re.UNICODE)
REFERENCE_TIME = datetime(2026, 8, 8, tzinfo=timezone.utc)


def tokens(text: str) -> list[str]:
    return [token.casefold() for token in TOKEN_RE.findall(text)]


def _stem(token: str) -> str:
    token = token.casefold()
    if len(token) > 4 and token.endswith("ing"):
        return token[:-3]
    if len(token) > 3 and token.endswith("ed"):
        return token[:-2]
    if len(token) > 3 and token.endswith("s"):
        return token[:-1]
    return token


def cosine_overlap(left: str, right: str) -> float:
    a, b = Counter(tokens(left)), Counter(tokens(right))
    if not a or not b:
        return 0.0
    numerator = sum(a[key] * b.get(key, 0) for key in a)
    denominator = math.sqrt(sum(v * v for v in a.values())) * math.sqrt(sum(v * v for v in b.values()))
    return numerator / denominator if denominator else 0.0


def parse_timestamp(value: str | None) -> datetime:
    if not value:
        return REFERENCE_TIME
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return REFERENCE_TIME
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def recency(memory: dict[str, Any]) -> float:
    age_days = max(0.0, (REFERENCE_TIME - parse_timestamp(memory.get("timestamp"))).total_seconds() / 86400)
    return 1.0 / (1.0 + age_days / 30.0)
