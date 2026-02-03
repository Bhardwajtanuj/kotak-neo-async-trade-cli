import asyncio
import logging
from typing import Set, Optional
from models import Trade
from async_neo import AsyncNeoAPI

logger = logging.getLogger("TradeManager")

MAX_ALLOWED_QTY = 1000

class TradeManager:
    def __init__(self, api: AsyncNeoAPI):
        self.api = api
        self.active_monitors: Set[asyncio.Task] = set()

    def validate_order(self, side: str, qty: int, entry: float, sl: float, tgt: float):
        if qty > MAX_ALLOWED_QTY:
            raise ValueError(f"Risk Limit: Quantity {qty} exceeds max {MAX_ALLOWED_QTY}")
        
        if qty <= 0:
             raise ValueError("Quantity must be positive")

        if side == "B":
            if sl >= entry:
                raise ValueError("BUY Order: SL must be below Entry price")
            if tgt <= entry:
                raise ValueError("BUY Order: Target must be above Entry price")
        elif side == "S":
            if sl <= entry:
                raise ValueError("SELL Order: SL must be above Entry price")
            if tgt >= entry:
                raise ValueError("SELL Order: Target must be below Entry price")

    def _register_task(self, coro):
        task = asyncio.create_task(coro)
        self.active_monitors.add(task)
        task.add_done_callback(self.active_monitors.discard)
        return task

    async def execute_trade(self, symbol: str, side: str, qty: int, sl_pts: float, tgt_pts: float):
        logger.info(f"Initiating Trade: {side} {qty} {symbol}")
        
        entry_id = await self.api.place_market_order(symbol, side, qty)
        entry_price = await self.api.get_fill_price(entry_id)
        
        if entry_price <= 0:
            logger.error("Failed to get valid entry price. Aborting OCO.")
            return

        if side == "B":
            sl_price = entry_price - sl_pts
            tgt_price = entry_price + tgt_pts
            exit_side = "S"
        else: 
            sl_price = entry_price + sl_pts
            tgt_price = entry_price - tgt_pts
            exit_side = "B"
            
        try:
            self.validate_order(side, qty, entry_price, sl_price, tgt_price)
        except ValueError as e:
            logger.error(f"Risk Validation Failed: {e}. closing position immediately.")
            return

        logger.info(f"Placing OCO -> SL: {sl_price:.2f} | TGT: {tgt_price:.2f}")
        sl_id = await self.api.place_sl_order(symbol, exit_side, qty, sl_price)
        tgt_id = await self.api.place_target_order(symbol, exit_side, qty, tgt_price)

        trade = Trade(
            symbol=symbol, side=side, qty=qty,
            entry_price=entry_price, sl_price=sl_price, target_price=tgt_price,
            entry_id=entry_id, sl_id=sl_id, target_id=tgt_id
        )

        self._register_task(asyncio.wait_for(self.monitor_oco(trade), timeout=86400))
        print(f"✅ Trade Active: {side} {qty} @ {entry_price:.2f}")

    async def monitor_oco(self, trade: Trade):
        log_ctx = {'symbol': trade.symbol, 'sl_id': trade.sl_id, 'tgt_id': trade.target_id}
        logger.info("Starting OCO Monitor", extra=log_ctx)
        
        try:
            while True:
                sl_status = await self.api.check_status(trade.sl_id)
                tgt_status = await self.api.check_status(trade.target_id)

                if tgt_status == "FILLED":
                    logger.info("Target Hit. Cancelling SL...", extra=log_ctx)
                    await self.api.cancel_order(trade.sl_id)
                    print(f"\n🎉 TARGET HIT: {trade.symbol} | Profit Locked.")
                    break

                if sl_status == "FILLED":
                    logger.info("SL Hit. Cancelling Target...", extra=log_ctx)
                    await self.api.cancel_order(trade.target_id)
                    print(f"\n🛡️ SL HIT: {trade.symbol} | Loss Limited.")
                    break

                if sl_status == "CANCELLED" and tgt_status == "CANCELLED":
                    logger.warning("Both orders cancelled externally.", extra=log_ctx)
                    break
                
                await asyncio.sleep(1)
                
        except asyncio.CancelledError:
            logger.info("Monitor Cancelled (Shutdown)", extra=log_ctx)
        except Exception as e:
            logger.error(f"Monitor Error: {e}", extra=log_ctx)

    async def shutdown(self):
        if not self.active_monitors:
            return
            
        print("\n[System] Shutting down background monitors...")
        for task in self.active_monitors:
            task.cancel()
        
        await asyncio.gather(*self.active_monitors, return_exceptions=True)
        print("[System] monitors cleaned up.")
