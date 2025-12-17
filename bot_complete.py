"""
BOT BOSHBASHBISH - LOGICA COMPLETA
==================================

Reverse-engineered da 1,164 trades reali.
Questa è la formula che orchestra TUTTI gli scenari.
"""

import time
from dataclasses import dataclass, field
from typing import Optional, List, Dict
from enum import Enum


# =============================================================================
# CONFIGURAZIONE (derivata dai dati reali)
# =============================================================================

class Config:
    # Soglie prezzo
    ENTRY_THRESHOLD = 0.55          # Compra se prezzo <= questo all'inizio
    AGGRESSIVE_THRESHOLD = 0.30     # Compra SEMPRE se prezzo <= questo
    MAX_BUY_PRICE = 0.95            # Non comprare MAI sopra questo

    # Timing (in secondi dall'apertura mercato)
    PHASE1_END = 300                # Primi 5 minuti = fase entry
    PHASE2_END = 720                # Minuti 5-12 = fase principale
    # Dopo 720 = fase finale

    # Position sizing
    ORDER_SIZE = 100                # Shares per ordine
    MAX_POSITION = 15000            # Max shares per lato

    # Risk management
    MAX_UNMATCHED_RATIO = 0.60      # Massimo 60% sbilanciamento

    # Target (NON è un hard limit!)
    TARGET_COMBINED = 0.90          # Obiettivo, ma può essere superato


# =============================================================================
# STATO DEL BOT
# =============================================================================

@dataclass
class Position:
    """Posizione su un singolo outcome"""
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
    """Stato completo del bot"""
    up: Position = field(default_factory=Position)
    down: Position = field(default_factory=Position)
    market_start_time: float = 0
    trades: List[dict] = field(default_factory=list)

    @property
    def total_shares(self) -> float:
        return self.up.shares + self.down.shares

    @property
    def matched(self) -> float:
        return min(self.up.shares, self.down.shares)

    @property
    def unmatched(self) -> float:
        return abs(self.up.shares - self.down.shares)

    @property
    def unmatched_ratio(self) -> float:
        if self.total_shares == 0:
            return 0
        return self.unmatched / self.total_shares

    @property
    def unmatched_side(self) -> Optional[str]:
        if self.up.shares > self.down.shares:
            return "up"
        elif self.down.shares > self.up.shares:
            return "down"
        return None

    @property
    def combined_vwap(self) -> float:
        if self.up.shares > 0 and self.down.shares > 0:
            return self.up.avg_price + self.down.avg_price
        return 0

    def market_time(self, current_time: float) -> float:
        """Secondi dall'apertura del mercato"""
        return current_time - self.market_start_time


# =============================================================================
# IL CERVELLO - DECISIONE COMPLETA
# =============================================================================

class BotBrain:
    """
    LA FORMULA COMPLETA CHE ORCHESTRA TUTTI GLI SCENARI
    """

    def __init__(self, config: Config = None):
        self.config = config or Config()

    def should_buy(
        self,
        outcome: str,           # "up" o "down"
        price: float,           # Prezzo corrente ask
        state: BotState,        # Stato attuale
        current_time: float     # Timestamp corrente
    ) -> tuple[bool, str]:
        """
        DECISIONE PRINCIPALE

        Returns:
            (should_buy: bool, reason: str)
        """

        market_time = state.market_time(current_time)
        other_outcome = "down" if outcome == "up" else "up"
        my_position = state.up if outcome == "up" else state.down
        other_position = state.down if outcome == "up" else state.up

        # =====================================================================
        # REGOLA 0: Limiti assoluti
        # =====================================================================

        if price > self.config.MAX_BUY_PRICE:
            return False, f"SKIP: prezzo ${price:.2f} > max ${self.config.MAX_BUY_PRICE}"

        if my_position.shares >= self.config.MAX_POSITION:
            return False, f"SKIP: max position raggiunta"

        # =====================================================================
        # REGOLA 1: SUPER CHEAP - Compra SEMPRE
        # =====================================================================

        if price <= self.config.AGGRESSIVE_THRESHOLD:
            return True, f"BUY AGGRESSIVE: ${price:.2f} <= ${self.config.AGGRESSIVE_THRESHOLD}"

        # =====================================================================
        # REGOLA 2: FASE 1 (primi 5 min) - Entry su entrambi i lati
        # =====================================================================

        if market_time < self.config.PHASE1_END:
            if price <= self.config.ENTRY_THRESHOLD:
                # All'inizio, compra entrambi i lati intorno a $0.50
                return True, f"BUY ENTRY: ${price:.2f} <= ${self.config.ENTRY_THRESHOLD} (fase 1)"

        # =====================================================================
        # REGOLA 3: Non ho questo lato - Entra prima che sia troppo tardi
        # =====================================================================

        if my_position.shares == 0:
            if price <= 0.60:
                return True, f"BUY FIRST: primo {outcome} @ ${price:.2f}"
            elif price <= 0.70 and market_time > 300:
                # Dopo 5 min, se non ho ancora questo lato, compra anche a $0.70
                return True, f"BUY LATE ENTRY: primo {outcome} @ ${price:.2f} (tardi)"

        # =====================================================================
        # REGOLA 4: Sotto $0.50 - Compra se non troppo sbilanciato
        # =====================================================================

        if price <= 0.50:
            # Check sbilanciamento
            if state.unmatched_side == outcome and state.unmatched_ratio > self.config.MAX_UNMATCHED_RATIO:
                return False, f"SKIP: già sbilanciato su {outcome} ({state.unmatched_ratio:.0%})"
            return True, f"BUY NORMAL: ${price:.2f} <= $0.50"

        # =====================================================================
        # REGOLA 5: Bilanciamento - Compra il lato minore anche se caro
        # =====================================================================

        if state.unmatched_side == other_outcome:
            # L'altro lato è maggiore, questo è il lato minore
            if state.unmatched_ratio > 0.30 and price <= 0.70:
                return True, f"BUY REBALANCE: {outcome} è il lato minore, ratio {state.unmatched_ratio:.0%}"

        # =====================================================================
        # REGOLA 6: FASE 3 (ultimi 3 min) - Ultima chance di bilanciare
        # =====================================================================

        if market_time > self.config.PHASE2_END:
            if state.unmatched_side == other_outcome and price <= 0.80:
                return True, f"BUY FINAL: ultima chance di bilanciare {outcome}"

        # =====================================================================
        # DEFAULT: Non comprare
        # =====================================================================

        return False, f"SKIP: nessuna regola soddisfatta per {outcome} @ ${price:.2f}"


# =============================================================================
# SIMULAZIONE COMPLETA
# =============================================================================

def simulate_market(price_sequence: List[tuple], verbose: bool = True):
    """
    Simula un mercato completo con la sequenza di prezzi.

    price_sequence: [(timestamp, up_price, down_price), ...]
    """

    brain = BotBrain()
    state = BotState()
    state.market_start_time = price_sequence[0][0]

    if verbose:
        print(f"{'Sec':>4} | {'UP$':>5} | {'DN$':>5} | {'Azione':40} | {'Combined':>8}")
        print("-" * 85)

    for ts, up_price, down_price in price_sequence:
        market_time = ts - state.market_start_time

        actions = []

        # Check UP
        should_buy_up, reason_up = brain.should_buy("up", up_price, state, ts)
        if should_buy_up:
            state.up.add(Config.ORDER_SIZE, up_price)
            actions.append(f"UP@{up_price:.2f}")
            state.trades.append({"outcome": "up", "price": up_price, "reason": reason_up})

        # Check DOWN
        should_buy_down, reason_down = brain.should_buy("down", down_price, state, ts)
        if should_buy_down:
            state.down.add(Config.ORDER_SIZE, down_price)
            actions.append(f"DN@{down_price:.2f}")
            state.trades.append({"outcome": "down", "price": down_price, "reason": reason_down})

        if verbose and actions:
            action_str = ", ".join(actions)
            combined = f"${state.combined_vwap:.3f}" if state.combined_vwap > 0 else "-"
            print(f"{market_time:>4.0f} | ${up_price:.2f} | ${down_price:.2f} | {action_str:40} | {combined:>8}")

    return state


def print_results(state: BotState):
    """Stampa risultati finali"""

    print("\n" + "=" * 60)
    print("RISULTATO FINALE")
    print("=" * 60)

    print(f"\nPOSIZIONE:")
    print(f"  UP:   {state.up.shares:>6.0f} shares @ ${state.up.avg_price:.3f} = ${state.up.cost:>8.2f}")
    print(f"  DOWN: {state.down.shares:>6.0f} shares @ ${state.down.avg_price:.3f} = ${state.down.cost:>8.2f}")

    total_cost = state.up.cost + state.down.cost
    print(f"\n  Total cost: ${total_cost:.2f}")
    print(f"  Combined VWAP: ${state.combined_vwap:.3f}")
    print(f"  Matched: {state.matched:.0f}, Unmatched: {state.unmatched:.0f} ({state.unmatched_ratio:.0%})")

    print(f"\nP&L:")
    pnl_up = state.up.shares - total_cost
    pnl_down = state.down.shares - total_cost
    print(f"  Se UP vince:   ${pnl_up:>+8.2f}")
    print(f"  Se DOWN vince: ${pnl_down:>+8.2f}")

    # Expected value (assumendo 50/50)
    ev = (pnl_up + pnl_down) / 2
    print(f"\n  Expected Value (50/50): ${ev:>+8.2f}")


# =============================================================================
# TEST CON SCENARI DIVERSI
# =============================================================================

if __name__ == "__main__":

    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    BOT BOSHBASHBISH - SIMULAZIONE COMPLETA                   ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """)

    # SCENARIO 1: UP crolla, DOWN sale (caso tipico)
    print("\n" + "=" * 60)
    print("SCENARIO 1: UP crolla, DOWN sale")
    print("=" * 60)

    scenario1 = [
        # (timestamp, up_price, down_price)
        (0,   0.50, 0.50),
        (60,  0.48, 0.52),
        (120, 0.45, 0.55),
        (180, 0.42, 0.58),
        (240, 0.40, 0.60),
        (300, 0.35, 0.65),
        (360, 0.30, 0.70),
        (420, 0.25, 0.75),
        (480, 0.20, 0.80),
        (540, 0.15, 0.85),
        (600, 0.12, 0.88),
        (660, 0.10, 0.90),
        (720, 0.08, 0.92),
        (780, 0.06, 0.94),
        (840, 0.05, 0.95),
    ]

    state1 = simulate_market(scenario1)
    print_results(state1)

    # SCENARIO 2: DOWN crolla, UP sale
    print("\n" + "=" * 60)
    print("SCENARIO 2: DOWN crolla, UP sale")
    print("=" * 60)

    scenario2 = [
        (0,   0.50, 0.50),
        (60,  0.52, 0.48),
        (120, 0.55, 0.45),
        (180, 0.58, 0.42),
        (240, 0.60, 0.40),
        (300, 0.65, 0.35),
        (360, 0.70, 0.30),
        (420, 0.75, 0.25),
        (480, 0.80, 0.20),
        (540, 0.85, 0.15),
        (600, 0.88, 0.12),
        (660, 0.90, 0.10),
        (720, 0.92, 0.08),
        (780, 0.94, 0.06),
        (840, 0.95, 0.05),
    ]

    state2 = simulate_market(scenario2)
    print_results(state2)

    # SCENARIO 3: Oscillazione (entrambi salgono e scendono)
    print("\n" + "=" * 60)
    print("SCENARIO 3: Oscillazione")
    print("=" * 60)

    scenario3 = [
        (0,   0.50, 0.50),
        (60,  0.48, 0.52),
        (120, 0.45, 0.55),
        (180, 0.40, 0.60),
        (240, 0.35, 0.65),
        (300, 0.40, 0.60),  # UP rimonta
        (360, 0.50, 0.50),  # Torna pari
        (420, 0.55, 0.45),  # DOWN scende
        (480, 0.60, 0.40),
        (540, 0.65, 0.35),
        (600, 0.60, 0.40),  # DOWN rimonta
        (660, 0.55, 0.45),
        (720, 0.50, 0.50),
        (780, 0.48, 0.52),
        (840, 0.45, 0.55),
    ]

    state3 = simulate_market(scenario3)
    print_results(state3)

    # SCENARIO 4: Mercato piatto (caso peggiore)
    print("\n" + "=" * 60)
    print("SCENARIO 4: Mercato piatto (WORST CASE)")
    print("=" * 60)

    scenario4 = [
        (0,   0.50, 0.50),
        (60,  0.51, 0.49),
        (120, 0.50, 0.50),
        (180, 0.49, 0.51),
        (240, 0.50, 0.50),
        (300, 0.51, 0.49),
        (360, 0.50, 0.50),
        (420, 0.49, 0.51),
        (480, 0.50, 0.50),
        (540, 0.51, 0.49),
        (600, 0.50, 0.50),
        (660, 0.49, 0.51),
        (720, 0.50, 0.50),
        (780, 0.51, 0.49),
        (840, 0.52, 0.48),
    ]

    state4 = simulate_market(scenario4)
    print_results(state4)
