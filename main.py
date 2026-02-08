import sys
import time
import signal as sig

from src.config import load_config
from src.utils.logger import setup_logger
from src.data.hyperliquid_client import HyperliquidClient
from src.data.funding import fetch_funding_rates
from src.data.open_interest import fetch_open_interest, get_oi_delta
from src.data.orderbook import fetch_orderbook, find_depth_clusters
from src.data.whale_tracker import scan_whale_wallets
from src.signals.funding_signal import evaluate_funding_signal
from src.signals.oi_divergence import evaluate_oi_signal
from src.signals.liquidation_map import build_liquidation_clusters, evaluate_liquidation_signal
from src.signals.signal_aggregator import aggregate_signals
from src.execution.alert_executor import AlertExecutor
from src.execution.paper_executor import PaperExecutor
from src.execution.live_executor import LiveExecutor

logger = setup_logger("main")

# Price history for OI divergence calculation
_price_history: dict[str, list[tuple[float, float]]] = {}
_running = True


def get_price_delta(coin: str, current_price: float, lookback_hours: float = 4.0) -> float | None:
    now = time.time()
    if coin not in _price_history:
        _price_history[coin] = []
    _price_history[coin].append((now, current_price))

    # Keep 6 hours
    cutoff = now - 6 * 3600
    _price_history[coin] = [(t, p) for t, p in _price_history[coin] if t > cutoff]

    history = _price_history[coin]
    if len(history) < 2:
        return None

    lookback_cutoff = now - lookback_hours * 3600
    old = [p for t, p in history if t <= lookback_cutoff + 300]
    if not old:
        old = [history[0][1]]

    old_price = old[0]
    if old_price == 0:
        return None
    return ((current_price - old_price) / old_price) * 100


def create_executor(config: dict):
    mode = config.get("mode", "alert")
    if mode == "paper":
        logger.info("Mode: PAPER TRADING")
        return PaperExecutor()
    elif mode == "live":
        logger.info("Mode: LIVE TRADING")
        return LiveExecutor()
    else:
        logger.info("Mode: ALERT ONLY")
        return AlertExecutor()


def run_cycle(client: HyperliquidClient, config: dict, executor):
    coins = config["coins"]
    sig_cfg = config["signals"]
    exe_cfg = config["execution"]
    capital = config["total_capital_usd"]

    # 1. Fetch current prices
    try:
        mids = client.get_all_mids()
    except Exception as e:
        logger.error(f"Failed to fetch prices: {e}")
        return

    current_prices = {}
    for coin in coins:
        price = mids.get(coin)
        if price:
            current_prices[coin] = float(price)
    logger.info(f"Prices: {current_prices}")

    # 2. Check open trades first
    closed = executor.check_open_trades(current_prices)
    if closed:
        for t in closed:
            logger.info(f"Closed: {t['coin']} {t.get('exit_reason', '')} PnL={t.get('pnl_pct', 0):+.2f}%")

    # 3. Check position limits
    open_positions = executor.get_open_positions()
    max_positions = exe_cfg.get("max_positions", 3)
    if len(open_positions) >= max_positions:
        logger.info(f"Max positions reached ({len(open_positions)}/{max_positions}), skipping signals")
        return

    # 4. Fetch funding rates
    try:
        funding_rates = fetch_funding_rates(client, coins)
    except Exception as e:
        logger.error(f"Failed to fetch funding: {e}")
        funding_rates = {}

    # 5. Fetch open interest
    try:
        fetch_open_interest(client, coins)
    except Exception as e:
        logger.error(f"Failed to fetch OI: {e}")

    # 6. Calculate deltas
    oi_deltas = {}
    price_deltas = {}
    for coin in coins:
        oi_deltas[coin] = get_oi_delta(coin)
        price = current_prices.get(coin, 0)
        price_deltas[coin] = get_price_delta(coin, price) if price else None

    # 7. Scan whale wallets for liquidation map
    whale_wallets = config.get("whale_wallets", [])
    liq_signals = {}
    if whale_wallets:
        whale_positions = scan_whale_wallets(client, whale_wallets, coins)
        for coin in coins:
            positions = whale_positions.get(coin, [])
            price = current_prices.get(coin, 0)
            if positions and price:
                clusters = build_liquidation_clusters(positions, price)
                sig_result = evaluate_liquidation_signal(
                    clusters, price, sig_cfg["liquidation_proximity"]
                )
                if sig_result:
                    liq_signals[coin] = sig_result

    # 8. Evaluate signals
    funding_sigs = evaluate_funding_signal(funding_rates, sig_cfg["funding_rate_threshold"])
    oi_sigs = evaluate_oi_signal(oi_deltas, price_deltas, sig_cfg["oi_delta_threshold"])

    # 9. Aggregate
    decisions = aggregate_signals(
        funding_sigs, oi_sigs, liq_signals, sig_cfg["min_confidence"]
    )

    if not decisions:
        logger.info("No trade signals this cycle")
        return

    # 10. Execute trades
    position_size = capital * exe_cfg["position_size_pct"] / 100
    slots_available = max_positions - len(open_positions)

    for decision in decisions[:slots_available]:
        # Skip if we already have a position in this coin
        existing_coins = {p.get("coin") for p in open_positions}
        if decision["coin"] in existing_coins:
            logger.info(f"Already positioned in {decision['coin']}, skipping")
            continue

        executor.execute_trade(decision, position_size, exe_cfg)

    # 11. Log order book depth for context
    for coin in coins:
        try:
            book = fetch_orderbook(client, coin)
            walls = find_depth_clusters(book)
            if walls["bid_walls"]:
                best_bid = walls["bid_walls"][0]
                logger.debug(f"{coin} biggest bid wall: {best_bid[1]:.2f} @ {best_bid[0]:.2f}")
            if walls["ask_walls"]:
                best_ask = walls["ask_walls"][0]
                logger.debug(f"{coin} biggest ask wall: {best_ask[1]:.2f} @ {best_ask[0]:.2f}")
        except Exception:
            pass


def shutdown(signum, frame):
    global _running
    logger.info("Shutting down...")
    _running = False


def main():
    global _running
    sig.signal(sig.SIGINT, shutdown)
    sig.signal(sig.SIGTERM, shutdown)

    config_path = sys.argv[1] if len(sys.argv) > 1 else None
    config = load_config(config_path)

    logger.info(f"Liquidation Hunter starting — mode={config['mode']} coins={config['coins']}")
    logger.info(f"Capital: ${config['total_capital_usd']} | Position size: {config['execution']['position_size_pct']}%")

    client = HyperliquidClient()
    executor = create_executor(config)
    interval = config["poll_interval_seconds"]

    cycle = 0
    while _running:
        cycle += 1
        logger.info(f"--- Cycle {cycle} ---")
        try:
            run_cycle(client, config, executor)
        except Exception as e:
            logger.error(f"Cycle error: {e}", exc_info=True)

        if _running:
            logger.info(f"Sleeping {interval}s...")
            for _ in range(interval):
                if not _running:
                    break
                time.sleep(1)

    logger.info("Liquidation Hunter stopped")


if __name__ == "__main__":
    main()
