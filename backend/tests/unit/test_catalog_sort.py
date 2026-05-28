"""Белый список сортировки каталога."""
from app.services.catalog_service import FILM_SORT_COLUMNS, PERSON_SORT_COLUMNS


def test_film_sort_whitelist_has_expected_keys():
    assert set(FILM_SORT_COLUMNS) == {
        "popularity",
        "vote_average",
        "year",
        "year_asc",
        "title",
    }
    for sql in FILM_SORT_COLUMNS.values():
        assert ";" not in sql
        assert "--" not in sql


def test_unknown_film_sort_falls_back_to_popularity():
    sort_col = FILM_SORT_COLUMNS.get("DROP TABLE", FILM_SORT_COLUMNS["popularity"])
    assert sort_col == FILM_SORT_COLUMNS["popularity"]


def test_person_sort_whitelist():
    assert set(PERSON_SORT_COLUMNS) == {"influences", "name", "birth_year"}
