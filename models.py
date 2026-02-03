from dataclasses import dataclass, field
from typing import Optional

@dataclass
class Trade:
    symbol: str
    side: str
    qty: int
    entry_price: float
    sl_price: float
    target_price: float
    entry_id: str
    sl_id: str
    target_id: str
    status: str = "ACTIVE"
    
    def __post_init__(self):
        self.symbol = self.symbol.upper()
        self.side = self.side.upper()
