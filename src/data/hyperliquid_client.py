import requests
from src.utils.logger import setup_logger

logger = setup_logger("hl_client")

API_URL = "https://api.hyperliquid.xyz/info"


class HyperliquidClient:
    def __init__(self, url: str = API_URL):
        self.url = url
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})

    def _post(self, payload: dict) -> dict:
        resp = self.session.post(self.url, json=payload, timeout=10)
        resp.raise_for_status()
        return resp.json()

    def get_meta_and_contexts(self) -> dict:
        return self._post({"type": "metaAndAssetCtxs"})

    def get_l2_book(self, coin: str) -> dict:
        return self._post({"type": "l2Book", "coin": coin})

    def get_all_mids(self) -> dict:
        return self._post({"type": "allMids"})

    def get_clearinghouse_state(self, user: str) -> dict:
        return self._post({"type": "clearinghouseState", "user": user})

    def get_open_orders(self, user: str) -> list:
        return self._post({"type": "frontendOpenOrders", "user": user})

    def get_user_funding(self, user: str, start_time: int) -> list:
        return self._post({"type": "userFunding", "user": user, "startTime": start_time})
