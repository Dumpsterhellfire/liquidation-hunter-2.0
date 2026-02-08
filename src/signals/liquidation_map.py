from src.utils.logger import setup_logger

logger = setup_logger("signal.liqmap")


def build_liquidation_clusters(
    positions: list[dict], current_price: float, bin_pct: float = 0.5
) -> list[dict]:
    """Build liquidation price clusters from whale positions.

    Groups liquidation prices into bins of bin_pct width and calculates
    total volume at each level.

    Returns sorted list of:
    {"price": float, "volume": float, "count": int, "distance_pct": float, "direction": "long"|"short"}

    direction = what type of positions would be liquidated at that level
    - liquidation price below current = long liquidations (longs get rekt on drop)
    - liquidation price above current = short liquidations (shorts get rekt on pump)
    """
    if not positions or current_price <= 0:
        return []

    bins: dict[float, dict] = {}

    for pos in positions:
        liq_px = pos.get("liquidation_price")
        if not liq_px or liq_px <= 0:
            continue

        size = abs(pos.get("size", 0))
        margin = pos.get("margin_used", 0)
        volume = margin if margin > 0 else size * liq_px

        # Round to bin
        bin_key = round(liq_px / (current_price * bin_pct / 100)) * (current_price * bin_pct / 100)

        if bin_key not in bins:
            direction = "long" if liq_px < current_price else "short"
            bins[bin_key] = {"price": bin_key, "volume": 0, "count": 0, "direction": direction}

        bins[bin_key]["volume"] += volume
        bins[bin_key]["count"] += 1

    clusters = list(bins.values())
    for c in clusters:
        c["distance_pct"] = abs(c["price"] - current_price) / current_price * 100

    clusters.sort(key=lambda x: x["volume"], reverse=True)
    return clusters


def evaluate_liquidation_signal(
    clusters: list[dict], current_price: float, proximity_pct: float
) -> dict | None:
    """Check if a dense liquidation cluster is within proximity of current price.

    Returns signal dict or None:
    {"strength": 0-1, "direction": "short"|"long", "cluster_price": float,
     "cluster_volume": float, "distance_pct": float}

    Cascade direction:
    - If cluster is long liquidations below price → price dropping will cascade → direction = "short"
    - If cluster is short liquidations above price → price pumping will cascade → direction = "long"
    """
    nearby = [c for c in clusters if c["distance_pct"] <= proximity_pct]

    if not nearby:
        return None

    # Pick the densest nearby cluster
    best = nearby[0]  # Already sorted by volume

    # Strength based on how close and how dense
    distance_factor = 1.0 - (best["distance_pct"] / proximity_pct)
    # Normalize volume — anything above 100k is considered significant
    volume_factor = min(best["volume"] / 100_000, 1.0)
    strength = (distance_factor * 0.6 + volume_factor * 0.4)

    # Cascade direction is the same as what gets liquidated
    # Long liquidation cluster → price drops → we go short
    # Short liquidation cluster → price pumps → we go long
    direction = "short" if best["direction"] == "long" else "long"

    signal = {
        "strength": strength,
        "direction": direction,
        "cluster_price": best["price"],
        "cluster_volume": best["volume"],
        "distance_pct": best["distance_pct"],
    }
    logger.info(
        f"Liq signal: cluster @ {best['price']:.2f} ({best['distance_pct']:.2f}% away) "
        f"vol={best['volume']:.0f} dir={direction} strength={strength:.2f}"
    )
    return signal
