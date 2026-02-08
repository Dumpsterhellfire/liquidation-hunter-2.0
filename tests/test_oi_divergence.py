from src.signals.oi_divergence import evaluate_oi_signal


def test_no_signal_below_threshold():
    oi_deltas = {"BTC": 2.0}
    price_deltas = {"BTC": 0.5}
    result = evaluate_oi_signal(oi_deltas, price_deltas, oi_threshold=5.0)
    assert result == {}


def test_no_signal_when_price_follows_oi():
    oi_deltas = {"BTC": 8.0}
    price_deltas = {"BTC": 7.0}  # Price keeping up
    result = evaluate_oi_signal(oi_deltas, price_deltas, oi_threshold=5.0)
    assert result == {}


def test_divergence_oi_up_price_flat():
    oi_deltas = {"BTC": 10.0}
    price_deltas = {"BTC": 0.5}
    result = evaluate_oi_signal(oi_deltas, price_deltas, oi_threshold=5.0)
    assert "BTC" in result
    assert result["BTC"]["direction"] == "short"
    assert result["BTC"]["strength"] > 0


def test_divergence_oi_up_price_down():
    oi_deltas = {"ETH": 8.0}
    price_deltas = {"ETH": -2.0}
    result = evaluate_oi_signal(oi_deltas, price_deltas, oi_threshold=5.0)
    assert "ETH" in result
    assert result["ETH"]["direction"] == "short"


def test_none_values_skipped():
    oi_deltas = {"BTC": None, "ETH": 10.0}
    price_deltas = {"BTC": 1.0, "ETH": None}
    result = evaluate_oi_signal(oi_deltas, price_deltas, oi_threshold=5.0)
    assert result == {}


def test_strength_scales_with_divergence():
    oi_deltas_small = {"BTC": 7.0}
    oi_deltas_large = {"BTC": 15.0}
    price_deltas = {"BTC": 0.0}

    small = evaluate_oi_signal(oi_deltas_small, price_deltas, oi_threshold=5.0)
    large = evaluate_oi_signal(oi_deltas_large, price_deltas, oi_threshold=5.0)

    assert large["BTC"]["strength"] > small["BTC"]["strength"]
