from src.utils.logger import setup_logger

logger = setup_logger("signal.oi")


def evaluate_oi_signal(
    oi_deltas: dict[str, float | None],
    price_deltas: dict[str, float | None],
    oi_threshold: float,
) -> dict[str, dict]:
    """Evaluate OI vs Price divergence signal.

    Returns {coin: {"strength": 0-1, "direction": "short"|"long", "oi_delta": float, "price_delta": float}}

    Divergence = OI rising significantly while price is flat or falling.
    - OI up + price flat/down → fragile longs → expect short cascade
    - OI up + price flat/up could mean shorts building → context dependent
    """
    signals = {}

    for coin, oi_delta in oi_deltas.items():
        if oi_delta is None:
            continue

        price_delta = price_deltas.get(coin)
        if price_delta is None:
            continue

        abs_oi = abs(oi_delta)
        if abs_oi < oi_threshold:
            continue

        # Divergence: OI rising but price not following proportionally
        # The bigger the gap between OI change and price change, the more fragile
        divergence = abs_oi - abs(price_delta)
        if divergence <= 0:
            continue  # Price moving with OI = healthy, no signal

        strength = min(divergence / (oi_threshold * 2), 1.0)

        # Direction logic:
        # OI rising + price flat/down = longs being built at bad levels → short cascade likely
        # OI rising + price barely up = could go either way, lean toward reversal
        if price_delta <= 0:
            direction = "short"
        elif price_delta > 0 and price_delta < oi_delta * 0.3:
            direction = "short"  # Price not keeping up with OI buildup
        else:
            continue  # Price following OI, no divergence

        signals[coin] = {
            "strength": strength,
            "direction": direction,
            "oi_delta": oi_delta,
            "price_delta": price_delta,
        }
        logger.info(
            f"{coin} OI signal: oi_delta={oi_delta:.2f}% price_delta={price_delta:.2f}% "
            f"dir={direction} strength={strength:.2f}"
        )

    return signals
