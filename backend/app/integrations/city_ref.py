"""
Справочник городов для афиши Кинопоиска.

kp_city_id — числовой id в URL /afisha/city/{id}/
"""
from __future__ import annotations

import re
import unicodedata

from pydantic import BaseModel


class CityRef(BaseModel):
    name: str
    kp_city_id: str
    slug: str


# Основные города РФ (id из структуры /afisha/city/{id}/ на Кинопоиске).
CITIES: list[CityRef] = [
    CityRef(name="Москва", kp_city_id="1", slug="moscow"),
    CityRef(name="Санкт-Петербург", kp_city_id="2", slug="spb"),
    CityRef(name="Новосибирск", kp_city_id="65", slug="novosibirsk"),
    CityRef(name="Екатеринбург", kp_city_id="54", slug="ekaterinburg"),
    CityRef(name="Казань", kp_city_id="43", slug="kazan"),
    CityRef(name="Нижний Новгород", kp_city_id="47", slug="nizhny-novgorod"),
    CityRef(name="Челябинск", kp_city_id="56", slug="chelyabinsk"),
    CityRef(name="Самара", kp_city_id="51", slug="samara"),
    CityRef(name="Омск", kp_city_id="66", slug="omsk"),
    CityRef(name="Ростов-на-Дону", kp_city_id="49", slug="rostov"),
    CityRef(name="Уфа", kp_city_id="172", slug="ufa"),
    CityRef(name="Красноярск", kp_city_id="62", slug="krasnoyarsk"),
    CityRef(name="Воронеж", kp_city_id="36", slug="voronezh"),
    CityRef(name="Пермь", kp_city_id="50", slug="perm"),
    CityRef(name="Волгоград", kp_city_id="38", slug="volgograd"),
    CityRef(name="Краснодар", kp_city_id="35", slug="krasnodar"),
    CityRef(name="Саратов", kp_city_id="194", slug="saratov"),
    CityRef(name="Тюмень", kp_city_id="55", slug="tyumen"),
    CityRef(name="Тольятти", kp_city_id="134", slug="tolyatti"),
    CityRef(name="Ижевск", kp_city_id="44", slug="izhevsk"),
    CityRef(name="Барнаул", kp_city_id="22", slug="barnaul"),
    CityRef(name="Иркутск", kp_city_id="63", slug="irkutsk"),
    CityRef(name="Хабаровск", kp_city_id="76", slug="khabarovsk"),
    CityRef(name="Владивосток", kp_city_id="75", slug="vladivostok"),
]


def _normalize_key(value: str) -> str:
    text = value.strip().lower().replace("ё", "е")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-z0-9а-я\-]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


_ALIASES: dict[str, str] = {}
for c in CITIES:
    keys = {
        c.name.lower(),
        c.slug.lower(),
        _normalize_key(c.name),
    }
    if c.name == "Санкт-Петербург":
        keys.update({"спб", "питер", "saint-petersburg", "st-petersburg", "st petersburg"})
    if c.name == "Москва":
        keys.update({"мск", "msk"})
    for k in keys:
        _ALIASES[k] = c.kp_city_id

_BY_KP_ID = {c.kp_city_id: c for c in CITIES}


def resolve_city(raw: str | None) -> CityRef | None:
    """Находит город по строке из профиля или query."""
    if not raw or not raw.strip():
        return None
    key = _normalize_key(raw)
    kp_id = _ALIASES.get(key)
    if kp_id:
        return _BY_KP_ID[kp_id]
    # Частичное совпадение: «Новосибирск, Россия»
    for alias, kid in _ALIASES.items():
        if alias in key or key in alias:
            return _BY_KP_ID[kid]
    return None


def default_city() -> CityRef:
    return _BY_KP_ID["1"]


def list_cities() -> list[CityRef]:
    return list(CITIES)
