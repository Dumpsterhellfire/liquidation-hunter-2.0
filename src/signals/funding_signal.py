from src.utils.logger import setup_logger

logger = setup_logger("signal.funding")


def evaluate_funding_signal(funding_rates: dict[str, float], threshold: float) -> dict[str, dict]:
    """Evaluate funding rate signal for each coin.

    Returns {coin: {"strength": 0-1, "direction": "short"|"long", "rate": float}}

    - Positive extreme → longs over-leveraged → expect short cascade
    - Negative extreme → shorts over-leveraged → expect long cascade
    - Strength scales from 0 at threshold to 1.0 at 3x threshold
    """
    signals = {}

    for coin, rate in funding_rates.items():
        abs_rate = abs(rate)
        if abs_rate < threshold:
            continue

        # Scale strength: 0 at threshold, 1.0 at 3x threshold
        strength = min((abs_rate - threshold) / (2 * threshold), 1.0)
        direction = "short" if rate > 0 else "long"

        signals[coin] = {
            "strength": strength,
            "direction": direction,
            "rate": rate,
        }
        logger.info(f"{coin} funding signal: rate={rate:.6f} dir={direction} strength={strength:.2f}")

    return signals
