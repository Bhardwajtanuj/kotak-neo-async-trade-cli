import asyncio
import random
import logging

logger = logging.getLogger("AsyncNeo")

class AsyncNeoAPI:
    def __init__(self, client):
        self.client = client

    async def safe_call(self, func, *args, retries=3):
        for i in range(retries):
            try:
                return await asyncio.to_thread(func, *args)
            except Exception as e:
                wait = 0.5 * (2 ** i)
                logger.warning(f"API Call failed ({e}). Retrying in {wait}s...")
                await asyncio.sleep(wait)
        logger.error("API failed after max retries.")
        raise Exception("API Call failed after retries")

    async def get_ltp(self, symbol: str) -> float:
        if hasattr(self.client, 'get_ltp'):
             return await self.safe_call(self.client.get_ltp, symbol)
        return 0.0

    async def place_market_order(self, symbol: str, side: str, qty: int) -> str:
        return await self.safe_call(self.client.place_order, symbol, side, qty, "MKT")

    async def place_sl_order(self, symbol: str, side: str, qty: int, price: float) -> str:
        return await self.safe_call(self.client.place_order, symbol, side, qty, "SL", price=price)

    async def place_target_order(self, symbol: str, side: str, qty: int, price: float) -> str:
        return await self.safe_call(self.client.place_order, symbol, side, qty, "LMT", price=price)

    async def check_status(self, order_id: str) -> str:
        return await self.safe_call(self.client.order_status, order_id)

    async def cancel_order(self, order_id: str):
        await self.safe_call(self.client.cancel_order, order_id)

    async def get_fill_price(self, order_id: str) -> float:
        return await self.safe_call(self.client.get_avg_price, order_id)


class MockNeoClient:
    def __init__(self):
        self.orders = {}
        self.market_prices = {}

    def get_ltp(self, symbol: str) -> float:
        base = self.market_prices.get(symbol, 100.0)
        movement = random.uniform(-0.5, 0.5)
        new_price = round(max(0.05, base + movement), 2)
        self.market_prices[symbol] = new_price
        
        self._simulate_market_fill(symbol, new_price)
        
        return new_price

    def place_order(self, symbol: str, side: str, qty: int, order_type: str, price: float = 0.0) -> str:
        order_id = f"ORD-{random.randint(10000, 99999)}"
        status = "FILLED" if order_type == "MKT" else "PENDING"
        
        avg_price = self.market_prices.get(symbol, 100.0) if status == "FILLED" else 0.0

        self.orders[order_id] = {
            "symbol": symbol,
            "side": side,
            "qty": qty,
            "type": order_type,
            "price": price, 
            "status": status,
            "avg_price": avg_price
        }
        import time
        time.sleep(0.5) 
        return order_id

    def order_status(self, order_id: str) -> str:
        import time
        time.sleep(0.2)
        return self.orders.get(order_id, {}).get("status", "UNKNOWN")

    def cancel_order(self, order_id: str):
        import time
        time.sleep(0.2)
        if order_id in self.orders:
            self.orders[order_id]["status"] = "CANCELLED"

    def get_avg_price(self, order_id: str) -> float:
        import time
        time.sleep(0.1)
        return self.orders.get(order_id, {}).get("avg_price", 0.0)

    def _simulate_market_fill(self, symbol, current_price):
        for oid, order in self.orders.items():
            if order["symbol"] == symbol and order["status"] == "PENDING":
                side = order["side"]
                trigger = order["price"]
                
                filled = False
                if side == "B": 
                    if order["type"] == "LMT" and current_price <= trigger:
                        filled = True
                    elif order["type"] == "SL" and current_price >= trigger:
                        filled = True
                
                elif side == "S": 
                    if order["type"] == "LMT" and current_price >= trigger:
                        filled = True
                    elif order["type"] == "SL" and current_price <= trigger:
                        filled = True
                
                if filled:
                    order["status"] = "FILLED"
                    order["avg_price"] = trigger
