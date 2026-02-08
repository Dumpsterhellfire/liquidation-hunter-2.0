from src.signals.funding_signal import evaluate_funding_signal


def test_no_signal_below_threshold():
    rates = {"BTC": 0.0001, "ETH": -0.0002}
    result = evaluate_funding_signal(rates, threshold=0.0005)
    assert result == {}


def test_positive_extreme_gives_short_direction():
    rates = {"BTC": 0.001}
    result = evaluate_funding_signal(rates, threshold=0.0005)
    assert "BTC" in result
    assert result["BTC"]["direction"] == "short"
    assert result["BTC"]["strength"] > 0


def test_negative_extreme_gives_long_direction():
    rates = {"ETH": -0.0008}
    result = evaluate_funding_signal(rates, threshold=0.0005)
    assert "ETH" in result
    assert result["ETH"]["direction"] == "long"


def test_strength_scales_with_magnitude():
    rates_mild = {"BTC": 0.0006}
    rates_extreme = {"BTC": 0.0015}
    threshold = 0.0005

    mild = evaluate_funding_signal(rates_mild, threshold)
    extreme = evaluate_funding_signal(rates_extreme, threshold)

    assert extreme["BTC"]["strength"] > mild["BTC"]["strength"]


def test_strength_caps_at_one():
    rates = {"BTC": 0.005}  # 10x threshold
    result = evaluate_funding_signal(rates, threshold=0.0005)
    assert result["BTC"]["strength"] == 1.0


def test_multiple_coins():
    rates = {"BTC": 0.001, "ETH": -0.001, "SOL": 0.0001}
    result = evaluate_funding_signal(rates, threshold=0.0005)
    assert "BTC" in result
    assert "ETH" in result
    assert "SOL" not in result
    assert result["BTC"]["direction"] == "short"
    assert result["ETH"]["direction"] == "long"
