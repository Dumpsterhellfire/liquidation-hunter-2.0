from src.data.positions import fetch_positions
from src.utils.logger import setup_logger

logger = setup_logger("whale_tracker")


def scan_whale_wallets(client, wallets: list[str], coins: list[str]) -> dict[str, list[dict]]:
    """Scan whale wallets and collect positions for target coins.

    Returns {coin: [position_dicts]} aggregated across all wallets.
    """
    result: dict[str, list[dict]] = {coin: [] for coin in coins}

    for wallet in wallets:
        try:
            positions = fetch_positions(client, wallet)
            for pos in positions:
                if pos["coin"] in coins:
                    pos["wallet"] = wallet
                    result[pos["coin"]].append(pos)
        except Exception as e:
            logger.warning(f"Failed to scan wallet {wallet[:10]}...: {e}")

    for coin in coins:
        count = len(result[coin])
        if count > 0:
            logger.info(f"{coin}: {count} whale positions found")

    return result


def scan_whale_orders(client, wallets: list[str], coins: list[str]) -> dict[str, list[dict]]:
    """Scan whale wallets for open orders (including TP/SL triggers).

    Returns {coin: [order_dicts]} with trigger info.
    """
    result: dict[str, list[dict]] = {coin: [] for coin in coins}

    for wallet in wallets:
        try:
            orders = client.get_open_orders(wallet)
            for order in orders:
                coin = order.get("coin", "")
                if coin in coins:
                    result[coin].append({
                        "wallet": wallet,
                        "coin": coin,
                        "side": order.get("side", ""),
                        "price": float(order.get("limitPx", 0)),
                        "size": float(order.get("sz", 0)),
                        "order_type": order.get("orderType", ""),
                        "trigger_condition": order.get("triggerCondition", ""),
                        "trigger_px": order.get("triggerPx", ""),
                    })
        except Exception as e:
            logger.warning(f"Failed to scan orders for {wallet[:10]}...: {e}")

    return result
