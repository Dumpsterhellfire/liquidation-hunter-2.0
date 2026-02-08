from src.signals.signal_aggregator import aggregate_signals


def test_no_signals_no_decisions():
    result = aggregate_signals({}, {}, {}, min_confidence=0.6)
    assert result == []


def test_single_strong_signal():
    funding = {"BTC": {"strength": 0.9, "direction": "short", "rate": 0.001}}
    result = aggregate_signals(funding, {}, {}, min_confidence=0.5)
    assert len(result) == 1
    assert result[0]["coin"] == "BTC"
    assert result[0]["direction"] == "short"
    assert result[0]["confidence"] > 0.5


def test_below_confidence_filtered():
    funding = {"BTC": {"strength": 0.3, "direction": "short", "rate": 0.0006}}
    result = aggregate_signals(funding, {}, {}, min_confidence=0.9)
    assert result == []


def test_aligned_signals_boost_confidence():
    funding = {"BTC": {"strength": 0.8, "direction": "short", "rate": 0.001}}
    oi = {"BTC": {"strength": 0.7, "direction": "short", "oi_delta": 10.0, "price_delta": 0.0}}
    result = aggregate_signals(funding, oi, {}, min_confidence=0.3)
    assert len(result) == 1
    assert result[0]["confidence"] > 0.5


def test_conflicting_signals_reduce_confidence():
    funding = {"BTC": {"strength": 0.8, "direction": "short", "rate": 0.001}}
    oi = {"BTC": {"strength": 0.8, "direction": "long", "oi_delta": 10.0, "price_delta": 0.0}}
    result = aggregate_signals(funding, oi, {}, min_confidence=0.1)
    if result:
        # Confidence should be reduced due to conflict
        assert result[0]["confidence"] < 0.8


def test_multiple_coins_sorted_by_confidence():
    funding = {
        "BTC": {"strength": 0.5, "direction": "short", "rate": 0.0008},
        "ETH": {"strength": 0.9, "direction": "short", "rate": 0.002},
    }
    result = aggregate_signals(funding, {}, {}, min_confidence=0.3)
    assert len(result) == 2
    assert result[0]["coin"] == "ETH"  # Higher confidence first


def test_liquidation_signal_provides_target():
    liq = {
        "BTC": {
            "strength": 0.8,
            "direction": "short",
            "cluster_price": 95_000,
            "cluster_volume": 200_000,
            "distance_pct": 1.0,
        }
    }
    result = aggregate_signals({}, {}, liq, min_confidence=0.3)
    assert len(result) == 1
    assert result[0]["target_price"] == 95_000


def test_all_three_signals_aligned():
    funding = {"BTC": {"strength": 0.8, "direction": "short", "rate": 0.001}}
    oi = {"BTC": {"strength": 0.7, "direction": "short", "oi_delta": 10.0, "price_delta": 0.0}}
    liq = {
        "BTC": {
            "strength": 0.9,
            "direction": "short",
            "cluster_price": 95_000,
            "cluster_volume": 300_000,
            "distance_pct": 0.5,
        }
    }
    result = aggregate_signals(funding, oi, liq, min_confidence=0.5)
    assert len(result) == 1
    assert result[0]["direction"] == "short"
    assert result[0]["confidence"] > 0.7
