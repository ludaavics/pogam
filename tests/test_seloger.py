import pytest

from pogam.scrapers.seloger import _to_seloger_geographical_code


@pytest.mark.parametrize(
    "post_code,seloger_code",
    [
        ("92200", ("ci", "920051")),
        (92200, ("ci", "920051")),
        ("75016", ("ci", "750116")),
        ("75116", ("ci", "750116")),
        ("93", ("cp", "93")),
        ("75", ("cp", "75")),
        ("69", ("cp", "69")),
    ],
)
def test_to_known_seloger_code(post_code, seloger_code):
    """
    Known valid post code should yield known (modified) insee codes.
    """
    expected = seloger_code
    actual = _to_seloger_geographical_code(post_code)
    assert expected == actual


@pytest.mark.parametrize("post_code", [-1, "hello", None, 9999])
def test_invalid_post_code(post_code):
    """
    Invalid post codes should raise ValueError.
    """
    expected_error_message = f"Unknown post code '{post_code}'."
    with pytest.raises(ValueError, match=expected_error_message):
        _to_seloger_geographical_code(post_code)
