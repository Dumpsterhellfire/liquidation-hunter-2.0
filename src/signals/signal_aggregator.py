from src.utils.logger import setup_logger

logger = setup_logger("signal.aggregator")

# Signal weights
WEIGHTS = {
    "funding": 0.35,
    "oi_divergence": 0.30,
    "liquidation": 0.35,
}


def aggregate_signals(
    funding_signals: dict[str, dict],
    oi_signals: dict[str, dict],
    liq_signals: dict[str, dict | None],
    min_confidence: float,
) -> list[dict]:
    """Combine all signals into trade decisions.

    Returns list of trade decisions:
    {
        "coin": str,
        "direction": "long" | "short",
        "confidence": float (0-1),
        "signals": {signal_name: detail_dict},
        "target_price": float | None,
    }
    """
    all_coins = set(funding_signals) | set(oi_signals) | set(liq_signals)
    decisions = []

    for coin in all_coins:
        funding = funding_signals.get(coin)
        oi = oi_signals.get(coin)
        liq = liq_signals.get(coin)

        # Collect directions and weighted strengths
        direction_votes = {"long": 0.0, "short": 0.0}
        total_weight = 0.0
        active_signals = {}

        if funding:
            w = WEIGHTS["funding"]
            direction_votes[funding["direction"]] += funding["strength"] * w
            total_weight += w
            active_signals["funding"] = funding

        if oi:
            w = WEIGHTS["oi_divergence"]
            direction_votes[oi["direction"]] += oi["strength"] * w
            total_weight += w
            active_signals["oi_divergence"] = oi

        if liq:
            w = WEIGHTS["liquidation"]
            direction_votes[liq["direction"]] += liq["strength"] * w
            total_weight += w
            active_signals["liquidation"] = liq

        if total_weight == 0:
            continue

        # Direction = whichever has more weighted votes
        direction = max(direction_votes, key=direction_votes.get)
        # Confidence = how aligned the signals are (0-1)
        confidence = direction_votes[direction] / total_weight

        # Check for conflicting signals — reduce confidence
        opposing = direction_votes["long" if direction == "short" else "short"]
        if opposing > 0:
            conflict_ratio = opposing / (direction_votes[direction] + opposing)
            confidence *= (1.0 - conflict_ratio)

        target_price = None
        if liq and liq.get("cluster_price"):
            target_price = liq["cluster_price"]

        if confidence >= min_confidence:
            decision = {
                "coin": coin,
                "direction": direction,
                "confidence": round(confidence, 3),
                "signals": active_signals,
                "target_price": target_price,
            }
            decisions.append(decision)
            logger.info(
                f"TRADE SIGNAL: {coin} {direction.upper()} "
                f"confidence={confidence:.3f} target={target_price}"
            )
        else:
            logger.debug(
                f"{coin}: confidence {confidence:.3f} below threshold {min_confidence}"
            )

    # Sort by confidence
    decisions.sort(key=lambda x: x["confidence"], reverse=True)
    return decisions
