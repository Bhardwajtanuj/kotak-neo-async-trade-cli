import asyncio
import sys
import logging
from async_neo import AsyncNeoAPI, MockNeoClient
from trade_manager import TradeManager
from datetime import datetime

USE_MOCK = True  

logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("MainCLI")

logging.getLogger("AsyncNeo").setLevel(logging.WARNING)

async def stream_ltp(api, symbol):
    try:
        while True:
            ltp = await api.get_ltp(symbol)
            timestamp = datetime.now().strftime("%H:%M:%S")
            sys.stdout.write(f"\r ⚡ [{timestamp}] {symbol}: {ltp:.2f}      ")
            sys.stdout.flush()
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        pass

async def async_input(prompt):
    sys.stdout.write("\r" + " " * 60 + "\r")
    sys.stdout.flush()
    return await asyncio.to_thread(input, prompt)

async def main():
    print("--- Anti-Gravity Kotak CLI (v2.0 Pro) ---")
    
    if USE_MOCK:
        logger.info("Initializing MOCK Environment...")
        client = MockNeoClient()
    else:
        client = None 
        
    api = AsyncNeoAPI(client)
    manager = TradeManager(api)
    
    symbol = await async_input("Enter Symbol to Track (e.g. NIFTY): ")
    symbol = symbol.strip().upper() or "NIFTY"
    
    ltp_task = None

    try:
        while True:
            if not ltp_task or ltp_task.done():
                ltp_task = asyncio.create_task(stream_ltp(api, symbol))

            print(f"\n[Tracking {symbol}] Press Enter to Trade, 'CHANGE' to switch, 'EXIT' to quit.")
            user_choice = await async_input("Command > ")
            
            cmd = user_choice.strip().upper()
            
            if cmd == 'EXIT':
                break
            
            if cmd == 'CHANGE':
                ltp_task.cancel()
                symbol = await async_input("New Symbol: ")
                symbol = symbol.strip().upper()
                continue
            
            ltp_task.cancel()
            
            try:
                side = await async_input("Buy/Sell (B/S)?: ")
                side = side.strip().upper()
                if side not in ['B', 'S']:
                    print("❌ Invalid side.")
                    continue
                    
                qty_str = await async_input("Quantity?: ")
                qty = int(qty_str)

                sl_str = await async_input("SL Points?: ")
                tgt_str = await async_input("Target Points?: ")
                sl_pts = float(sl_str)
                tgt_pts = float(tgt_str)

                await manager.execute_trade(symbol, side, qty, sl_pts, tgt_pts)
                
            except ValueError as e:
                print(f"⚠️ Input Error: {e}")
            except Exception as e:
                logger.error(f"Trade Error: {e}")
            
    except asyncio.CancelledError:
        print("\nMain loop cancelled.")
    finally:
        if ltp_task:
            ltp_task.cancel()
        await manager.shutdown()
        print("\n👋 System Shutdown Complete.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass 
