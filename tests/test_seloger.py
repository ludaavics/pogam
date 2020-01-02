import pytest

from pogam.scrapers.seloger import _to_code_insee


@pytest.mark.parametrize(
    "post_code,code_insee",
    [(92200, "920051"), ("92200", "920051"), (75016, "750116"), (75116, "750116")],
)
def test_known_to_code_insee(post_code, code_insee):
    """
    Known valid post code should yield known (modified) insee codes.
    """
    expected = code_insee
    actual = _to_code_insee(post_code)
    assert expected == actual


@pytest.mark.parametrize("post_code", [-1, "hello", None, 9999])
def test_invalid_post_code(post_code):
    """
    Invalide post codes should raise ValueError.
    """
    expected_error_message = f"Unknown post code '{post_code}'."
    with pytest.raises(ValueError, match=expected_error_message):
        _to_code_insee(post_code)
