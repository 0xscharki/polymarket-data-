"""
BACKTEST realistico usando i dati reali di BoshBashBish
"""

import json
from dataclasses import dataclass, field
from typing import Optional, List

@dataclass
class Position:
    shares: float = 0
    cost: float = 0

    @property
    def avg_price(self) -> float:
        return self.cost / self.shares if self.shares > 0 else 0

    def add(self, shares: float, price: float):
        self.shares += shares
        self.cost += shares * price


@dataclass
class BotState:
    up: Position = field(default_factory=Position)
    down: Position = field(default_factory=Position)
    trades: List[dict] = field(default_factory=list)

    @property
    def matched(self) -> float:
        return min(self.up.shares, self.down.shares)

    @property
    def unmatched(self) -> float:
        return abs(self.up.shares - self.down.shares)

    @property
    def combined_vwap(self) -> float:
        if self.up.shares > 0 and self.down.shares > 0:
            return self.up.avg_price + self.down.avg_price
        elif self.up.shares > 0:
            return self.up.avg_price
        elif self.down.shares > 0:
            return self.down.avg_price
        return 0


# =============================================================================
# BOT LOGIC - Replica della strategia BoshBashBish
# =============================================================================

class SimpleArbitrageBot:
    """
    Strategia semplice basata sui dati reali:
    - Compra se prezzo <= threshold
    - Gestisce unmatched ratio
    """

    def __init__(self):
        # Thresholds derivati dai dati
        self.UP_BUY_THRESHOLD = 0.50      # Compra UP se <= $0.50
        self.DOWN_BUY_THRESHOLD = 0.75    # Compra DOWN se <= $0.75 (più permissivo)
        self.MAX_UNMATCHED_RATIO = 0.40   # Max 40% sbilanciamento
        self.MAX_POSITION = 15000
        self.ORDER_SIZE = 100

    def should_buy(self, state: BotState, outcome: str, price: float) -> tuple[bool, str]:
        """Decide se comprare"""

        side = state.up if outcome == "up" else state.down
        other = state.down if outcome == "up" else state.up
        threshold = self.UP_BUY_THRESHOLD if outcome == "up" else self.DOWN_BUY_THRESHOLD

        # Position limit
        if side.shares >= self.MAX_POSITION:
            return False, "max position"

        # Price check
        if price > threshold:
            return False, f"price ${price:.2f} > threshold ${threshold:.2f}"

        # Unmatched ratio check
        total = state.up.shares + state.down.shares
        if total > 0:
            current_unmatched_ratio = state.unmatched / total

            # Se siamo già sbilanciati su questo lato, sii più cauto
            unmatched_side = "up" if state.up.shares > state.down.shares else "down" if state.down.shares > state.up.shares else None

            if unmatched_side == outcome and current_unmatched_ratio > self.MAX_UNMATCHED_RATIO:
                # Compra solo se prezzo MOLTO buono
                if price > 0.30:
                    return False, f"unmatched {current_unmatched_ratio:.1%} > max, price not cheap enough"

        return True, f"BUY @ ${price:.2f}"


def replay_market(bot: SimpleArbitrageBot, trades: List[dict], market_name: str):
    """Replay trades e simula decisioni del bot"""

    state = BotState()
    trades.sort(key=lambda x: x.get("timestamp", 0))

    print(f"\n{'='*70}")
    print(f"MARKET: {market_name}")
    print(f"{'='*70}")

    for t in trades:
        outcome = t.get("outcome", "").lower()
        price = float(t.get("price", 0))
        size = float(t.get("size", 0))

        # Il bot decide se comprare
        should_buy, reason = bot.should_buy(state, outcome, price)

        if should_buy:
            buy_size = min(bot.ORDER_SIZE, size)  # Compra al massimo quello disponibile

            if outcome == "up":
                state.up.add(buy_size, price)
            else:
                state.down.add(buy_size, price)

            state.trades.append({
                "outcome": outcome,
                "price": price,
                "size": buy_size,
                "reason": reason
            })

    # Results
    print(f"\nTrades reali: {len(trades)}")
    print(f"Trades bot: {len(state.trades)}")

    print(f"\nPOSIZIONE BOT:")
    print(f"  UP:   {state.up.shares:.0f} shares @ ${state.up.avg_price:.3f} = ${state.up.cost:.2f}")
    print(f"  DOWN: {state.down.shares:.0f} shares @ ${state.down.avg_price:.3f} = ${state.down.cost:.2f}")
    print(f"  Total cost: ${state.up.cost + state.down.cost:.2f}")

    print(f"\nARBITRAGGIO:")
    print(f"  Matched: {state.matched:.0f}")
    print(f"  Unmatched: {state.unmatched:.0f} ({state.unmatched/(state.up.shares+state.down.shares)*100:.1f}%)")
    print(f"  Combined VWAP: ${state.combined_vwap:.3f}")

    # P&L calculation
    total_cost = state.up.cost + state.down.cost
    pnl_if_up = state.up.shares - total_cost
    pnl_if_down = state.down.shares - total_cost

    print(f"\nP&L SIMULATION:")
    print(f"  Se UP vince:   ${pnl_if_up:+.2f}")
    print(f"  Se DOWN vince: ${pnl_if_down:+.2f}")

    return state, pnl_if_up, pnl_if_down


def compare_with_real(state: BotState, trades: List[dict]):
    """Compara risultato bot con quello reale di BoshBashBish"""

    # Real position
    real_up_shares = sum(float(t.get("size", 0)) for t in trades if t.get("outcome") == "Up")
    real_up_cost = sum(float(t.get("size", 0)) * float(t.get("price", 0)) for t in trades if t.get("outcome") == "Up")
    real_down_shares = sum(float(t.get("size", 0)) for t in trades if t.get("outcome") == "Down")
    real_down_cost = sum(float(t.get("size", 0)) * float(t.get("price", 0)) for t in trades if t.get("outcome") == "Down")

    print(f"\nCONFRONTO CON BOSHBASHBISH:")
    print(f"  {'':20} {'BOT':>15} {'REAL':>15}")
    print(f"  {'UP shares':20} {state.up.shares:>15.0f} {real_up_shares:>15.0f}")
    print(f"  {'DOWN shares':20} {state.down.shares:>15.0f} {real_down_shares:>15.0f}")
    print(f"  {'Total cost':20} ${state.up.cost + state.down.cost:>14.0f} ${real_up_cost + real_down_cost:>14.0f}")


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    BACKTEST BOT ARBITRAGGIO                                  ║
║                    Replay dati reali BoshBashBish                            ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """)

    # Load data
    with open("boshbashbish_btc_december_REAL.json") as f:
        all_trades = json.load(f)

    # Group by market
    by_market = {}
    for t in all_trades:
        title = t.get("title", "")
        if title not in by_market:
            by_market[title] = []
        by_market[title].append(t)

    # Test bot
    bot = SimpleArbitrageBot()

    total_pnl_up = 0
    total_pnl_down = 0

    for market_name in sorted(by_market.keys()):
        trades = by_market[market_name]
        if len(trades) < 20:
            continue

        state, pnl_up, pnl_down = replay_market(bot, trades, market_name)
        compare_with_real(state, trades)

        total_pnl_up += pnl_up
        total_pnl_down += pnl_down

    print(f"\n{'='*70}")
    print(f"TOTALE P&L SIMULATO (tutti i mercati):")
    print(f"  Se tutti UP vincono:   ${total_pnl_up:+.2f}")
    print(f"  Se tutti DOWN vincono: ${total_pnl_down:+.2f}")
    print(f"{'='*70}")
