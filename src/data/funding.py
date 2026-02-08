from src.utils.logger import setup_logger

logger = setup_logger("funding")


def fetch_funding_rates(client, coins: list[str]) -> dict[str, float]:
    """Fetch current funding rates for given coins. Returns {coin: rate}."""
    data = client.get_meta_and_contexts()
    meta = data[0]  # universe metadata
    ctxs = data[1]  # asset contexts with funding, OI, etc.

    coin_index = {asset["name"]: i for i, asset in enumerate(meta["universe"])}
    rates = {}
    for coin in coins:
        idx = coin_index.get(coin)
        if idx is not None and idx < len(ctxs):
            rate = float(ctxs[idx].get("funding", 0))
            rates[coin] = rate
            logger.debug(f"{coin} funding rate: {rate:.6f}")
    return rates


def detect_funding_extreme(rates: dict[str, float], threshold: float) -> dict[str, dict]:
    """Detect coins with extreme funding rates.

    Returns {coin: {"rate": float, "direction": "short"|"long"}}
    - Positive extreme funding → longs are over-leveraged → cascade direction is SHORT
    - Negative extreme funding → shorts are over-leveraged → cascade direction is LONG
    """
    extremes = {}
    for coin, rate in rates.items():
        if abs(rate) >= threshold:
            direction = "short" if rate > 0 else "long"
            extremes[coin] = {"rate": rate, "direction": direction}
            logger.info(f"{coin} funding extreme: {rate:.6f} → cascade direction: {direction}")
    return extremes
