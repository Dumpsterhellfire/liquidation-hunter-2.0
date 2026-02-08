import time
from src.execution.executor import Executor
from src.utils.logger import setup_logger

logger = setup_logger("executor.paper")


class PaperExecutor(Executor):
    """Simulated trade executor — tracks virtual PnL."""

    def __init__(self):
        self.open_trades: list[dict] = []
        self.closed_trades: list[dict] = []
        self.total_pnl: float = 0.0

    def execute_trade(self, decision: dict, capital: float, config: dict) -> dict | None:
        trade = {
            "coin": decision["coin"],
            "direction": decision["direction"],
            "confidence": decision["confidence"],
            "entry_capital": capital,
            "entry_time": time.time(),
            "take_profit_pct": config.get("take_profit_pct", 2.0),
            "stop_loss_pct": config.get("stop_loss_pct", 1.0),
            "timeout_minutes": config.get("timeout_minutes", 30),
            "entry_price": None,  # Set on first price check
            "status": "open",
        }

        self.open_trades.append(trade)
        logger.info(
            f"PAPER TRADE: {decision['coin']} {decision['direction'].upper()} "
            f"${capital:.2f} confidence={decision['confidence']:.1%}"
        )
        return trade

    def check_open_trades(self, current_prices: dict[str, float]) -> list[dict]:
        closed = []
        still_open = []

        for trade in self.open_trades:
            coin = trade["coin"]
            price = current_prices.get(coin)
            if price is None:
                still_open.append(trade)
                continue

            # Set entry price on first check
            if trade["entry_price"] is None:
                trade["entry_price"] = price
                still_open.append(trade)
                continue

            entry = trade["entry_price"]
            direction = trade["direction"]
            elapsed_min = (time.time() - trade["entry_time"]) / 60

            # Calculate PnL %
            if direction == "long":
                pnl_pct = (price - entry) / entry * 100
            else:
                pnl_pct = (entry - price) / entry * 100

            # Check exit conditions
            reason = None
            if pnl_pct >= trade["take_profit_pct"]:
                reason = "take_profit"
            elif pnl_pct <= -trade["stop_loss_pct"]:
                reason = "stop_loss"
            elif elapsed_min >= trade["timeout_minutes"]:
                reason = "timeout"

            if reason:
                pnl_usd = trade["entry_capital"] * pnl_pct / 100
                trade["exit_price"] = price
                trade["exit_time"] = time.time()
                trade["pnl_pct"] = pnl_pct
                trade["pnl_usd"] = pnl_usd
                trade["exit_reason"] = reason
                trade["status"] = "closed"

                self.total_pnl += pnl_usd
                self.closed_trades.append(trade)
                closed.append(trade)

                logger.info(
                    f"PAPER CLOSE: {coin} {direction} {reason} "
                    f"PnL={pnl_pct:+.2f}% (${pnl_usd:+.2f}) Total=${self.total_pnl:+.2f}"
                )
            else:
                still_open.append(trade)

        self.open_trades = still_open
        return closed

    def get_open_positions(self) -> list[dict]:
        return list(self.open_trades)
