import time
from src.utils.logger import setup_logger

logger = setup_logger("open_interest")

# In-memory OI history for delta calculation
_oi_history: dict[str, list[tuple[float, float]]] = {}  # coin -> [(timestamp, oi)]


def fetch_open_interest(client, coins: list[str]) -> dict[str, float]:
    """Fetch current open interest for given coins. Returns {coin: oi_value}."""
    data = client.get_meta_and_contexts()
    meta = data[0]
    ctxs = data[1]

    coin_index = {asset["name"]: i for i, asset in enumerate(meta["universe"])}
    oi_data = {}
    now = time.time()

    for coin in coins:
        idx = coin_index.get(coin)
        if idx is not None and idx < len(ctxs):
            oi = float(ctxs[idx].get("openInterest", 0))
            oi_data[coin] = oi

            # Track history
            if coin not in _oi_history:
                _oi_history[coin] = []
            _oi_history[coin].append((now, oi))
            # Keep only last 6 hours
            cutoff = now - 6 * 3600
            _oi_history[coin] = [(t, v) for t, v in _oi_history[coin] if t > cutoff]

            logger.debug(f"{coin} OI: {oi:.2f}")
    return oi_data


def get_oi_delta(coin: str, lookback_hours: float = 4.0) -> float | None:
    """Calculate OI % change over the lookback period. Returns None if insufficient data."""
    history = _oi_history.get(coin, [])
    if len(history) < 2:
        return None

    now = time.time()
    cutoff = now - lookback_hours * 3600

    # Find the oldest reading within the lookback window
    old_readings = [(t, v) for t, v in history if t <= cutoff + 300]  # 5min tolerance
    if not old_readings:
        old_readings = [history[0]]

    old_oi = old_readings[0][1]
    current_oi = history[-1][1]

    if old_oi == 0:
        return None

    delta_pct = ((current_oi - old_oi) / old_oi) * 100
    logger.debug(f"{coin} OI delta ({lookback_hours}h): {delta_pct:.2f}%")
    return delta_pct


def clear_history():
    """Clear OI history (for testing)."""
    _oi_history.clear()
