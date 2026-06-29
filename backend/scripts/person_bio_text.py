"""
Нормализация текстов биографий персон (TMDB → entity_translation).

- без эмодзи и markdown-разметки TMDB
- без дублирующихся абзацев
- без блока «фильмография / главные проекты» (есть отдельная вкладка)
- с блоком наград (из TMDB или из award_nomination в БД)
- summary = первый абзац, description = остальное (без пересечения → нет дублей на фронте)
"""
from __future__ import annotations

import re
from typing import Literal

LangCode = Literal["ru", "en"]

FILMOGRAPHY_SECTION = re.compile(
    r"^(?:\*{0,2}\s*)?"
    r"(?:основные проекты|главные (?:роли|работы)|фильмография|"
    r"filmography|main projects|notable (?:works|films)|selected filmography)",
    re.IGNORECASE,
)
AWARDS_SECTION = re.compile(
    r"^(?:\*{0,2}\s*)?"
    r"(?:главные награды|номинации|награды|премии|"
    r"awards?(?:\s+and\s+nominations)?|nominations?)",
    re.IGNORECASE,
)
FACT_SECTION = re.compile(
    r"^(?:\*{0,2}\s*)?"
    r"(?:интересн(?:ый|ая) факт|fun fact|did you know)",
    re.IGNORECASE,
)
FILM_LIST_ITEM = re.compile(
    r"^[-•*·]\s|"
    r"^[\u00ab\u201c\u201d].*\(\d{4}\)|"
    r"^[\w\u00ab\u201c\u201d].{2,60}\s*\(\d{4}\)"
)


def strip_emojis(text: str) -> str:
    out: list[str] = []
    for ch in text:
        cp = ord(ch)
        if 0x1F000 <= cp <= 0x1FAFF:
            continue
        if 0x2600 <= cp <= 0x27BF:
            continue
        if cp in (0x200D, 0xFE0F):
            continue
        out.append(ch)
    cleaned = "".join(out)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def strip_markdown(text: str) -> str:
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    return text


def _norm_key(text: str) -> str:
    return re.sub(r"\s+", " ", strip_emojis(text).lower()).strip()


def looks_like_film_list_item(line: str) -> bool:
    t = strip_emojis(line).strip()
    if not t or len(t) > 220:
        return False
    return bool(FILM_LIST_ITEM.search(t))


def _dedupe_paragraphs(paragraphs: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for p in paragraphs:
        key = _norm_key(p)
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(p.strip())
    return out


def _split_paragraphs(text: str) -> list[str]:
    blocks = re.split(r"\n\s*\n", text.strip())
    return [b.strip() for b in blocks if b.strip()]


def _lines_to_paragraphs(lines: list[str]) -> list[str]:
    """Склеивает строки в абзацы; пустая строка — граница абзаца."""
    paragraphs: list[str] = []
    buf: list[str] = []
    for line in lines:
        t = line.strip()
        if not t:
            if buf:
                paragraphs.append(" ".join(buf))
                buf = []
            continue
        buf.append(t)
    if buf:
        paragraphs.append(" ".join(buf))
    return paragraphs


def parse_tmdb_biography(raw: str) -> tuple[list[str], list[str]]:
    """
    Разбирает сырой TMDB biography.
    Возвращает (bio_paragraphs, awards_lines).
    """
    text = strip_markdown(strip_emojis(raw))
    lines = text.splitlines()

    bio_parts: list[str] = []
    awards_lines: list[str] = []
    mode: Literal["bio", "awards", "skip"] = "bio"

    for line in lines:
        trimmed = line.strip()
        if not trimmed:
            if mode == "bio" and bio_parts and not bio_parts[-1].endswith("\n"):
                bio_parts.append("")
            continue

        if FILMOGRAPHY_SECTION.match(strip_emojis(trimmed)) or FACT_SECTION.match(
            strip_emojis(trimmed)
        ):
            mode = "skip"
            continue

        if AWARDS_SECTION.match(strip_emojis(trimmed)):
            mode = "awards"
            header = re.sub(r"^[*·\s]+|[*·\s]+$", "", strip_emojis(trimmed)).strip()
            if header:
                awards_lines.append(header)
            continue

        if mode == "skip":
            if looks_like_film_list_item(trimmed):
                continue
            if len(trimmed) > 80 and not looks_like_film_list_item(trimmed):
                mode = "bio"
            else:
                continue

        if mode == "awards":
            if looks_like_film_list_item(trimmed):
                continue
            awards_lines.append(trimmed)
            continue

        # bio
        if looks_like_film_list_item(trimmed):
            continue
        bio_parts.append(trimmed)

    bio_paragraphs = _dedupe_paragraphs(_lines_to_paragraphs(bio_parts))
    return bio_paragraphs, awards_lines


def format_awards_block(lines: list[str], *, lang: LangCode) -> str:
    if not lines:
        return ""
    header = lines[0]
    if not AWARDS_SECTION.match(strip_emojis(header)):
        header = "Главные награды" if lang == "ru" else "Main awards"
        body_lines = lines
    else:
        body_lines = lines[1:]
    body = "\n".join(body_lines).strip()
    if not body:
        return header
    return f"{header}\n{body}"


def format_db_awards(
    items: list[dict],
    *,
    lang: LangCode,
    max_items: int = 12,
) -> str:
    if not items:
        return ""
    header = "Главные награды" if lang == "ru" else "Main awards"
    lines: list[str] = [header]
    for row in items[:max_items]:
        status = row.get("status")
        year = row.get("year")
        award = row.get("award_name") or "—"
        film = (row.get("film_title") or "").strip()
        if status == "won":
            prefix = "Победа" if lang == "ru" else "Won"
        else:
            prefix = "Номинация" if lang == "ru" else "Nominated"
        line = f"{prefix}: {award} ({year})"
        if film:
            line += f" — «{film}»"
        lines.append(line)
    return "\n".join(lines)


def build_person_bio_fields(
    raw_bio: str,
    *,
    lang: LangCode,
    db_awards: list[dict] | None = None,
) -> tuple[str | None, str | None]:
    """
    Готовит (summary, description) без пересечения текста.
    summary — первый абзац биографии; description — остальные абзацы + награды.
    """
    bio_paragraphs, awards_lines = parse_tmdb_biography(raw_bio)

    awards_block = format_awards_block(awards_lines, lang=lang)
    if not awards_block and db_awards:
        awards_block = format_db_awards(db_awards, lang=lang)

    if not bio_paragraphs and not awards_block:
        return None, None

    if not bio_paragraphs:
        return None, awards_block or None

    summary = bio_paragraphs[0]
    body_parts = bio_paragraphs[1:]
    if awards_block:
        body_parts.append(awards_block)

    description = "\n\n".join(body_parts).strip() or None
    return summary, description
