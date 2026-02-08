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
                    clusters,
                    price,
                    sig_cfg["liquidation_proximity"],
                    sig_cfg.get("volume_baseline_usd", 100_000),
                )
                if sig_result:
                    liq_signals[coin] = sig_result

    # 8. Evaluate signals
    # Dynamic thresholds (rolling history)
    if not hasattr(run_cycle, "_fund_hist"):
        run_cycle._fund_hist = {}
        run_cycle._oi_hist = {}
    for coin, rate in funding_rates.items():
        run_cycle._fund_hist.setdefault(coin, []).append(rate)
        run_cycle._fund_hist[coin] = run_cycle._fund_hist[coin][-sig_cfg.get("dynamic_funding_window", 96):]
    for coin, od in oi_deltas.items():
        if od is not None:
            run_cycle._oi_hist.setdefault(coin, []).append(od)
            run_cycle._oi_hist[coin] = run_cycle._oi_hist[coin][-sig_cfg.get("dynamic_oi_window", 96):]

    def dynamic_threshold(hist: list[float], base: float) -> float:
        if len(hist) < 5:
            return base
        avg = sum(abs(x) for x in hist) / len(hist)
        return max(base, avg * 1.5)

    fund_thr = {}
    oi_thr = {}
    for coin in coins:
        fund_thr[coin] = dynamic_threshold(run_cycle._fund_hist.get(coin, []), sig_cfg["funding_rate_threshold"])
        oi_thr[coin] = dynamic_threshold(run_cycle._oi_hist.get(coin, []), sig_cfg["oi_delta_threshold"])

    funding_sigs = evaluate_funding_signal(funding_rates, 0)  # we'll filter by per-coin threshold below
    funding_sigs = {c: s for c, s in funding_sigs.items() if abs(s["rate"]) >= fund_thr.get(c, sig_cfg["funding_rate_threshold"])}
    oi_sigs = evaluate_oi_signal(oi_deltas, price_deltas, 0)
    oi_sigs = {c: s for c, s in oi_sigs.items() if abs(s["oi_delta"]) >= oi_thr.get(c, sig_cfg["oi_delta_threshold"])}

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

        # Order book wall confirmation
        wall = wall_confirm.get(decision["coin"], {}) if 'wall_confirm' in locals() else {}
        min_wall = sig_cfg.get("min_wall_notional", 0)
        if min_wall:
            if decision["direction"] == "long":
                ask = wall.get("ask")
                if not ask or ask[2] < min_wall:
                    logger.info(f"{decision['coin']} skipped: no strong ask wall >= ${min_wall}")
                    continue
            else:
                bid = wall.get("bid")
                if not bid or bid[2] < min_wall:
                    logger.info(f"{decision['coin']} skipped: no strong bid wall >= ${min_wall}")
                    continue

        # ATR/volatility filter (simple proxy using 1h candles)
        min_atr = sig_cfg.get("min_atr_pct", 0)
        if min_atr:
            try:
                # use 24h candle snapshot (1h interval)
                candles = client._post({"type": "candleSnapshot", "req": {"coin": decision["coin"], "interval": "1h", "startTime": int(time.time() - 26*3600)*1000, "endTime": int(time.time())*1000}})
                highs = [float(c["h"]) for c in candles]
                lows = [float(c["l"]) for c in candles]
                if highs and lows:
                    atr = sum((h-l) for h,l in zip(highs, lows)) / len(highs)
                    atr_pct = atr / current_prices.get(decision["coin"], 1) * 100
                    if atr_pct < min_atr:
                        logger.info(f"{decision['coin']} skipped: ATR {atr_pct:.2f}% < {min_atr}%")
                        continue
            except Exception:
                pass

        # Confidence-based sizing
        trade_capital = position_size
        if exe_cfg.get("size_by_confidence"):
            conf = decision.get("confidence", 0.5)
            min_pct = exe_cfg.get("min_size_pct", 10)
            max_pct = exe_cfg.get("max_size_pct", 30)
            scaled = min_pct + (max_pct - min_pct) * conf
            trade_capital = capital * scaled / 100

        executor.execute_trade(decision, trade_capital, exe_cfg)

    # 11. Order book wall confirmation (used as filter)
    wall_confirm = {}
    for coin in coins:
        try:
            book = fetch_orderbook(client, coin)
            walls = find_depth_clusters(book)
            best_bid = walls["bid_walls"][0] if walls["bid_walls"] else None
            best_ask = walls["ask_walls"][0] if walls["ask_walls"] else None
            wall_confirm[coin] = {"bid": best_bid, "ask": best_ask}
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
