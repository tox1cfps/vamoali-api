from services.place_service import PlaceService


def test_is_truthy_returns_true_for_boolean_true():
    assert PlaceService._is_truthy(True) is True


def test_is_truthy_returns_true_for_string_true_ignoring_case_and_spaces():
    assert PlaceService._is_truthy("  TrUe  ") is True


def test_is_truthy_returns_false_for_boolean_false():
    assert PlaceService._is_truthy(False) is False


def test_is_truthy_returns_false_for_other_strings():
    assert PlaceService._is_truthy("false") is False
