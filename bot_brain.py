"""
IL CERVELLO DEL BOT - Versione semplificata e commentata
"""

class BotBrain:
    """
    Il cervello del bot.
    Unica regola: COMPRA se il combined VWAP resta sotto la soglia.
    """

    def __init__(self):
        # === STATO POSIZIONE ===
        self.up_shares = 0
        self.up_cost = 0
        self.down_shares = 0
        self.down_cost = 0

        # === CONFIGURAZIONE ===
        self.TARGET_VWAP = 0.90      # Combined deve stare sotto questo
        self.ORDER_SIZE = 100        # Shares per ordine
        self.MAX_POSITION = 15000    # Max shares per lato

    # =========================================================================
    # QUESTA È LA FUNZIONE CHIAVE - IL CERVELLO
    # =========================================================================

    def should_buy(self, outcome: str, current_price: float) -> bool:
        """
        Decide se comprare.

        Args:
            outcome: "up" o "down"
            current_price: prezzo attuale ask

        Returns:
            True se dovrei comprare, False altrimenti
        """

        # --- STEP 1: Check limiti posizione ---
        if outcome == "up" and self.up_shares >= self.MAX_POSITION:
            return False
        if outcome == "down" and self.down_shares >= self.MAX_POSITION:
            return False

        # --- STEP 2: Simula il trade ---
        new_combined = self._simulate_trade(outcome, current_price)

        # --- STEP 3: Compra se combined resta sotto soglia ---
        if new_combined < self.TARGET_VWAP:
            return True

        return False

    def _simulate_trade(self, outcome: str, price: float) -> float:
        """
        Calcola quale sarebbe il combined VWAP dopo questo trade.
        NON esegue il trade, solo simula.
        """

        if outcome == "up":
            # Nuovo stato UP dopo il trade
            new_up_shares = self.up_shares + self.ORDER_SIZE
            new_up_cost = self.up_cost + (self.ORDER_SIZE * price)
            new_up_avg = new_up_cost / new_up_shares

            # DOWN resta uguale
            down_avg = self.down_cost / self.down_shares if self.down_shares > 0 else 0

        else:  # down
            # UP resta uguale
            up_avg = self.up_cost / self.up_shares if self.up_shares > 0 else 0

            # Nuovo stato DOWN dopo il trade
            new_down_shares = self.down_shares + self.ORDER_SIZE
            new_down_cost = self.down_cost + (self.ORDER_SIZE * price)
            new_down_avg = new_down_cost / new_down_shares
            down_avg = new_down_avg
            new_up_avg = up_avg

        # Combined VWAP
        if outcome == "up":
            return new_up_avg + down_avg
        else:
            return new_up_avg + down_avg

    def execute_buy(self, outcome: str, price: float):
        """Esegue l'acquisto e aggiorna lo stato."""

        if outcome == "up":
            self.up_shares += self.ORDER_SIZE
            self.up_cost += self.ORDER_SIZE * price
        else:
            self.down_shares += self.ORDER_SIZE
            self.down_cost += self.ORDER_SIZE * price

        # Log
        combined = self.get_combined_vwap()
        print(f"BUY {self.ORDER_SIZE} {outcome.upper()} @ ${price:.2f} | "
              f"Combined VWAP: ${combined:.3f}")

    def get_combined_vwap(self) -> float:
        """Calcola il combined VWAP attuale."""
        up_avg = self.up_cost / self.up_shares if self.up_shares > 0 else 0
        down_avg = self.down_cost / self.down_shares if self.down_shares > 0 else 0
        return up_avg + down_avg


# =============================================================================
# SIMULAZIONE DEL LOOP PRINCIPALE
# =============================================================================

def run_simulation():
    """
    Simula il bot durante un mercato 15-min.
    """

    print("=" * 70)
    print("SIMULAZIONE BOT")
    print("=" * 70)

    brain = BotBrain()

    # Simuliamo una sequenza di prezzi (semplificata)
    price_sequence = [
        # (minuto, up_price, down_price)
        (0, 0.50, 0.50),   # Inizio: 50/50
        (1, 0.48, 0.52),
        (2, 0.45, 0.55),
        (3, 0.40, 0.60),   # UP scende
        (4, 0.35, 0.65),
        (5, 0.30, 0.70),
        (6, 0.25, 0.75),
        (7, 0.20, 0.80),   # UP molto cheap
        (8, 0.15, 0.85),
        (9, 0.12, 0.88),
        (10, 0.10, 0.90),  # UP super cheap
        (11, 0.08, 0.92),
        (12, 0.06, 0.94),
        (13, 0.05, 0.95),
        (14, 0.04, 0.96),  # Fine: quasi certo DOWN vince
    ]

    print(f"\nTarget VWAP: ${brain.TARGET_VWAP}")
    print(f"Order size: {brain.ORDER_SIZE}\n")

    for minute, up_price, down_price in price_sequence:
        print(f"\n--- Minuto {minute} | UP=${up_price:.2f} DOWN=${down_price:.2f} ---")

        # Check UP
        if brain.should_buy("up", up_price):
            brain.execute_buy("up", up_price)
        else:
            proj = brain._simulate_trade("up", up_price)
            print(f"SKIP UP @ ${up_price:.2f} (projected VWAP ${proj:.3f} >= ${brain.TARGET_VWAP})")

        # Check DOWN
        if brain.should_buy("down", down_price):
            brain.execute_buy("down", down_price)
        else:
            proj = brain._simulate_trade("down", down_price)
            print(f"SKIP DOWN @ ${down_price:.2f} (projected VWAP ${proj:.3f} >= ${brain.TARGET_VWAP})")

    # Risultato finale
    print("\n" + "=" * 70)
    print("RISULTATO FINALE")
    print("=" * 70)

    up_avg = brain.up_cost / brain.up_shares if brain.up_shares > 0 else 0
    down_avg = brain.down_cost / brain.down_shares if brain.down_shares > 0 else 0
    combined = up_avg + down_avg

    print(f"\nUP:   {brain.up_shares:.0f} shares @ ${up_avg:.3f} = ${brain.up_cost:.2f}")
    print(f"DOWN: {brain.down_shares:.0f} shares @ ${down_avg:.3f} = ${brain.down_cost:.2f}")
    print(f"\nCombined VWAP: ${combined:.3f}")

    matched = min(brain.up_shares, brain.down_shares)
    total_cost = brain.up_cost + brain.down_cost

    print(f"\nMatched pairs: {matched:.0f}")
    print(f"Guaranteed payout: ${matched:.2f}")
    print(f"Total cost: ${total_cost:.2f}")
    print(f"Guaranteed profit: ${matched - total_cost:.2f}")


if __name__ == "__main__":
    run_simulation()
