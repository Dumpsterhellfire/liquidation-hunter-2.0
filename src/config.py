import os
import yaml


DEFAULT_CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.yaml")


def load_config(path: str = None) -> dict:
    path = path or DEFAULT_CONFIG_PATH
    with open(path, "r") as f:
        cfg = yaml.safe_load(f)

    # Defaults
    cfg.setdefault("mode", "alert")
    cfg.setdefault("poll_interval_seconds", 30)
    cfg.setdefault("total_capital_usd", 500)
    cfg.setdefault("coins", ["BTC", "ETH"])
    cfg.setdefault("whale_wallets", [])

    signals = cfg.setdefault("signals", {})
    signals.setdefault("funding_rate_threshold", 0.0005)
    signals.setdefault("oi_delta_threshold", 5.0)
    signals.setdefault("liquidation_proximity", 1.5)
    signals.setdefault("min_confidence", 0.6)

    execution = cfg.setdefault("execution", {})
    execution.setdefault("position_size_pct", 20)
    execution.setdefault("max_positions", 3)
    execution.setdefault("take_profit_pct", 2.0)
    execution.setdefault("stop_loss_pct", 1.0)
    execution.setdefault("timeout_minutes", 30)

    return cfg
