from abc import ABC, abstractmethod


class Executor(ABC):
    """Base class for trade executors."""

    @abstractmethod
    def execute_trade(self, decision: dict, capital: float, config: dict) -> dict | None:
        """Execute a trade based on the signal decision.

        Args:
            decision: {coin, direction, confidence, signals, target_price}
            capital: USD amount allocated for this trade
            config: execution config (take_profit_pct, stop_loss_pct, timeout_minutes)

        Returns:
            Trade record dict or None if skipped.
        """
        pass

    @abstractmethod
    def check_open_trades(self, current_prices: dict[str, float]) -> list[dict]:
        """Check and manage open trades. Returns list of closed trade records."""
        pass

    @abstractmethod
    def get_open_positions(self) -> list[dict]:
        """Return list of currently open positions."""
        pass
