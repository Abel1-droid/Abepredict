import math
import predictor

def test_parse_date():
    result = predictor.parse_date("18/11/2026")
    assert result is not None
    assert result.isoformat() == "2026-11-18"

def test_poisson_probability():
    result = predictor.poisson(1.0, 0)
    assert math.isclose(result, math.exp(-1))

def test_prediction_markets_are_valid():
    markets = predictor.calculate_probabilities(1.4, 1.1)
    assert "Home win" in markets
    assert "Draw" in markets
    assert "Away win" in markets
    assert all(0 <= value <= 1 for value in markets.values())

def test_match_outcomes_sum_to_one():
    markets = predictor.calculate_probabilities(1.4, 1.1)
    total = markets["Home win"] + markets["Draw"] + markets["Away win"]
    assert math.isclose(total, 1.0, abs_tol=1e-9)

def test_empty_date_is_rejected():
    assert predictor.parse_date("") is None
