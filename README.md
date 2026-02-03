# Anti-Gravity Kotak Neo CLI 🚀

A professional, non-blocking, event-driven trading CLI for Kotak Neo, built with Python `asyncio`.

## Core Philosophy: "Anti-Gravity"
**"The CLI never gets pulled down."**
Most trading scripts block the main thread while waiting for API responses or user input. This project uses a pure **Event Loop architecture** where:
1.  **LTP Streaming** runs as an independent background task.
2.  **User Input** is offloaded to a non-blocking thread.
3.  **Trade Execution** is asynchronous and "fire-and-forget" from the UI perspective.
4.  **OCO Monitoring** spawns a dedicated, self-managing task for each trade position.

## 🏗 Architecture

### Component Diagram
```
Main Event Loop (main.py)
 ├── UI Layer (Input/Output)
 │    ├── Async Input (Threaded)
 │    └── LTP Streamer (Task)
 │
 └── TradeManager (trade_manager.py)
      ├── Validation & Risk Controls
      ├── Order Placement (via async_neo.py)
      └── Task Registry (active_monitors)
           ├── Monitor Task (Trade 1)
           ├── Monitor Task (Trade 2)
           └── ...
```

### Key Modules
| File | Responsibility |
| :--- | :--- |
| `main.py` | Entry point. Handles UI, Event Loop, and user commands. |
| `trade_manager.py` | **Business Logic Core**. Manages Trade lifecycle, OCO monitoring, and Risk validation. |
| `models.py` | Data definitions (e.g., `Trade` dataclass) for type safety. |
| `async_neo.py` | Async wrapper for the broker API with **Resilience (Retries)** and Mock support. |

## 🛡️ Risk Controls
The system implements strict pre-trade validation:
*   **Max Quantity Check**: Rejects orders > `MAX_ALLOWED_QTY` (1000).
*   **Price Logic Validation**:
    *   *Buy*: SL < Entry < Target
    *   *Sell*: Target < Entry < SL

## ⚡ Concurrency Model
*   **Method**: `asyncio` Event Loop + `run_in_executor` (threads) for blocking I/O.
*   **Task Management**: A robust `Task Registry` pattern tracks all background monitors to ensure **Graceful Shutdown** without orphaned threads.
*   **Resilience**: API calls are wrapped in an exponential backoff retry mechanism.

## 🚀 How to Run

1.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
2.  **Execute**:
    ```bash
    python main.py
    ```
3.  **Usage**:
    *   Enter a Symbol (e.g., `NIFTY`).
    *   Follow the interactive prompts to Buy/Sell.
    *   The system handles the rest in the background.

## 🔮 Future Roadmap (Production)
*   **WebSockets**: Replace polling `LTP` and `Order Status` with pure WebSocket streaming for sub-millisecond latency.
*   **Database**: Persist `Trade` objects to SQLite/Postgres instead of in-memory.
