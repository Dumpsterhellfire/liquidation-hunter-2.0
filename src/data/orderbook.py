from src.utils.logger import setup_logger

logger = setup_logger("orderbook")


def fetch_orderbook(client, coin: str) -> dict:
    """Fetch L2 order book. Returns {"bids": [(price, size)], "asks": [(price, size)]}."""
    raw = client.get_l2_book(coin)
    levels = raw.get("levels", [[], []])

    bids = [(float(b["px"]), float(b["sz"])) for b in levels[0]] if levels[0] else []
    asks = [(float(a["px"]), float(a["sz"])) for a in levels[1]] if levels[1] else []

    logger.debug(f"{coin} book: {len(bids)} bids, {len(asks)} asks")
    return {"bids": bids, "asks": asks}


def find_depth_clusters(book: dict, top_n: int = 5) -> dict:
    """Find the largest order clusters in the book.

    Returns {"bid_walls": [(price, size)], "ask_walls": [(price, size)]}
    sorted by size descending.
    """
    bid_walls = sorted(book["bids"], key=lambda x: x[1], reverse=True)[:top_n]
    ask_walls = sorted(book["asks"], key=lambda x: x[1], reverse=True)[:top_n]

    return {"bid_walls": bid_walls, "ask_walls": ask_walls}
