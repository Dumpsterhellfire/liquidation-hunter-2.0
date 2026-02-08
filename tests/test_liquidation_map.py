from src.signals.liquidation_map import build_liquidation_clusters, evaluate_liquidation_signal


def _make_positions(liq_prices, current_price=100_000):
    """Helper to create position dicts with liquidation prices."""
    positions = []
    for liq_px in liq_prices:
        positions.append({
            "coin": "BTC",
            "size": 1.0,
            "entry_price": current_price,
            "liquidation_price": liq_px,
            "leverage": 10.0,
            "margin_used": 10_000,
        })
    return positions


def test_empty_positions():
    clusters = build_liquidation_clusters([], 100_000)
    assert clusters == []


def test_clusters_grouped_by_price():
    positions = _make_positions([95_000, 95_100, 95_200, 80_000])
    clusters = build_liquidation_clusters(positions, 100_000)
    assert len(clusters) > 0
    # The 95k cluster should have more volume than the 80k one
    volumes = {round(c["price"] / 1000): c["volume"] for c in clusters}
    assert len(volumes) >= 2


def test_long_liquidations_below_price():
    positions = _make_positions([95_000, 94_000])
    clusters = build_liquidation_clusters(positions, 100_000)
    for c in clusters:
        if c["price"] < 100_000:
            assert c["direction"] == "long"


def test_short_liquidations_above_price():
    positions = _make_positions([105_000, 106_000])
    clusters = build_liquidation_clusters(positions, 100_000)
    for c in clusters:
        if c["price"] > 100_000:
            assert c["direction"] == "short"


def test_distance_pct_calculated():
    positions = _make_positions([99_000])
    clusters = build_liquidation_clusters(positions, 100_000)
    assert len(clusters) > 0
    assert clusters[0]["distance_pct"] > 0


def test_evaluate_signal_nearby_cluster():
    clusters = [
        {"price": 99_000, "volume": 200_000, "count": 5, "distance_pct": 1.0, "direction": "long"},
    ]
    signal = evaluate_liquidation_signal(clusters, 100_000, proximity_pct=1.5)
    assert signal is not None
    assert signal["direction"] == "short"  # Long liq cluster → short cascade
    assert signal["strength"] > 0


def test_evaluate_signal_no_nearby():
    clusters = [
        {"price": 90_000, "volume": 500_000, "count": 10, "distance_pct": 10.0, "direction": "long"},
    ]
    signal = evaluate_liquidation_signal(clusters, 100_000, proximity_pct=1.5)
    assert signal is None


def test_evaluate_signal_short_cluster_gives_long():
    clusters = [
        {"price": 101_000, "volume": 150_000, "count": 3, "distance_pct": 1.0, "direction": "short"},
    ]
    signal = evaluate_liquidation_signal(clusters, 100_000, proximity_pct=1.5)
    assert signal is not None
    assert signal["direction"] == "long"  # Short liq cluster → long cascade
