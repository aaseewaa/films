"""Тесты парсера афиши Кинопоиска (без сети)."""
from app.integrations.city_ref import default_city
from app.integrations.kinopoisk_afisha import parse_afisha_html


SAMPLE_HTML = """
<html><body>
  <a href="/film/301/"><span>Матрица</span></a>
  <a href="/film/301/">Матрица</a>
  <a href="/afisha/city/1/cinema/77/">Кинотеатр Октябрь</a>
  <div class="schedule">
    <a href="/film/326/">Титаник</a>
    <a href="/afisha/city/1/cinema/77/">Кинотеатр Октябрь</a>
  </div>
</body></html>
"""


def test_parse_afisha_extracts_films_and_ticket_url():
    city = default_city()
    films = parse_afisha_html(SAMPLE_HTML, city=city)
    by_id = {f.kinopoisk_id: f for f in films}
    assert 301 in by_id
    assert 326 in by_id
    assert "301" in by_id[301].ticket_url
    assert "afisha/city/1" in by_id[301].ticket_url
