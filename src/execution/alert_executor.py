from src.execution.executor import Executor
from src.utils.logger import setup_logger

logger = setup_logger("executor.alert")


class AlertExecutor(Executor):
    """Executor that only logs/alerts on signals — no trading."""

    def __init__(self):
        self.alert_history = []

    def execute_trade(self, decision: dict, capital: float, config: dict) -> dict | None:
        alert = {
            "coin": decision["coin"],
            "direction": decision["direction"],
            "confidence": decision["confidence"],
            "allocated_capital": capital,
            "target_price": decision.get("target_price"),
            "signals": list(decision.get("signals", {}).keys()),
        }

        self.alert_history.append(alert)

        logger.info(
            f"{'='*60}\n"
            f"  ALERT: {decision['coin']} {decision['direction'].upper()}\n"
            f"  Confidence: {decision['confidence']:.1%}\n"
            f"  Capital: ${capital:.2f}\n"
            f"  Target: {decision.get('target_price', 'N/A')}\n"
            f"  Active signals: {', '.join(alert['signals'])}\n"
            f"{'='*60}"
        )
        return alert

    def check_open_trades(self, current_prices: dict[str, float]) -> list[dict]:
        return []  # No real trades to check

    def get_open_positions(self) -> list[dict]:
        return []  # No real positions
