import pytest

from pogam.scrapers.seloger import _to_code_insee


@pytest.mark.parametrize(
    "code_postal,code_insee",
    [(92200, "920051"), ("92200", "920051"), (75016, "750116"), (75116, "750116")],
)
def test_known_to_code_insee(code_postal, code_insee):
    expected = code_insee
    actual = _to_code_insee(code_postal)
    assert expected == actual
