from src.utils.logger import setup_logger

logger = setup_logger("positions")


def fetch_positions(client, wallet: str) -> list[dict]:
    """Fetch all open positions for a wallet.

    Returns list of:
    {
        "coin": str,
        "size": float (positive=long, negative=short),
        "entry_price": float,
        "liquidation_price": float | None,
        "leverage": float,
        "unrealized_pnl": float,
        "margin_used": float
    }
    """
    state = client.get_clearinghouse_state(wallet)
    positions = []

    for pos in state.get("assetPositions", []):
        p = pos.get("position", {})
        size = float(p.get("szi", 0))
        if size == 0:
            continue

        entry = float(p.get("entryPx", 0))
        liq_px = p.get("liquidationPx")
        liq_price = float(liq_px) if liq_px else None
        leverage_info = p.get("leverage", {})
        leverage = float(leverage_info.get("value", 1)) if isinstance(leverage_info, dict) else 1.0

        positions.append({
            "coin": p.get("coin", ""),
            "size": size,
            "entry_price": entry,
            "liquidation_price": liq_price,
            "leverage": leverage,
            "unrealized_pnl": float(p.get("unrealizedPnl", 0)),
            "margin_used": float(p.get("marginUsed", 0)),
        })

    logger.debug(f"Wallet {wallet[:10]}...: {len(positions)} positions")
    return positions
