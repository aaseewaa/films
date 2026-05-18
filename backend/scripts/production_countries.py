"""Извлечение стран производства из ответа TMDB movie_full."""


def build_production_countries(en: dict, ru: dict | None) -> list[dict]:
    ru_names: dict[str, str] = {}
    if ru:
        for c in ru.get("production_countries") or []:
            code = c.get("iso_3166_1")
            if code and c.get("name"):
                ru_names[code] = c["name"]

    out: list[dict] = []
    seen: set[str] = set()
    for c in en.get("production_countries") or []:
        code = c.get("iso_3166_1")
        if not code or code in seen:
            continue
        seen.add(code)
        out.append({
            "code": code,
            "name_en": c.get("name") or code,
            "name_ru": ru_names.get(code) or c.get("name") or code,
        })
    return out
