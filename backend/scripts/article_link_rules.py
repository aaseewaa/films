"""Общие правила автолинковки режиссёров в тексте статей (см. front/src/lib/articleLinkRules.ts)."""
from __future__ import annotations

import re

GLOBAL_SURNAME_DENY = frozenset({
    "джонс",
    "миранда",
    "ривз",
    "оппенгеймер",
    "экзюпери",
})

GLOBAL_PERSON_TITLE_DENY = (
    "кеану ривз",
    "keanu reeves",
    "тейлор-джой",
    "anya taylor-joy",
    "эдгар райт",
    "edgar wright",
    "антoine de saint-exupery",
    "сент-экзюпери",
    "оппенгеймер",
    "oppenheimer",
)

ARTICLE_PERSON_DENY: dict[str, tuple[str, ...]] = {
    "marvel-fastfud-ili-iskusstvo": (
        "кеану ривз",
        "тейлор-джой",
        "эдгар райт",
    ),
    "secs-v-bolshom-gorode-pochemu-aktualen": ("миранда", "джонс", "саманта джонс"),
    "secs-v-bolshom-gorode-do-sih-por": ("миранда", "джонс", "саманта джонс"),
    "kino-povernutoe-na-bok": ("сент-экзюпери", "экзюпери"),
}

MIN_SURNAME_LENGTH = 4
MIN_FULL_NAME_LENGTH = 4


def normalize_for_deny(s: str) -> str:
    return " ".join(s.strip().lower().split())


def person_title_denied(slug: str | None, title: str) -> bool:
    t = normalize_for_deny(title)
    if any(d in t or t in d for d in GLOBAL_PERSON_TITLE_DENY):
        return True
    if not slug:
        return False
    per = ARTICLE_PERSON_DENY.get(slug)
    if not per:
        return False
    return any(d in t or t in d for d in per)


def surname_denied(surname: str) -> bool:
    return normalize_for_deny(surname) in GLOBAL_SURNAME_DENY


def guillemet_ranges(text: str) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    i = 0
    while i < len(text):
        open_ = text.find("«", i)
        if open_ == -1:
            break
        close = text.find("»", open_ + 1)
        if close == -1:
            break
        ranges.append((open_, close + 1))
        i = close + 1
    return ranges


def is_inside_guillemets(start: int, end: int, ranges: list[tuple[int, int]]) -> bool:
    return any(a <= start and end <= b for a, b in ranges)


def starts_with_capital(s: str) -> bool:
    return bool(re.match(r"^[A-ZА-ЯЁ]", s))


def is_word_char(ch: str) -> bool:
    return bool(ch) and (ch.isalnum() or ch == "_")


def surname_from_title(title: str) -> str | None:
    parts = title.strip().split()
    if len(parts) < 2:
        return None
    last = parts[-1]
    if len(last) < MIN_SURNAME_LENGTH or not starts_with_capital(last):
        return None
    if surname_denied(last):
        return None
    return last


def is_valid_match(body: str, m: re.Match[str], quote_ranges: list[tuple[int, int]]) -> bool:
    slice_ = m.group(0)
    if not starts_with_capital(slice_):
        return False
    start, end = m.start(), m.end()
    if is_inside_guillemets(start, end, quote_ranges):
        return False
    before = body[start - 1] if start > 0 else ""
    after = body[end] if end < len(body) else ""
    if is_word_char(before) or is_word_char(after):
        return False
    return True
