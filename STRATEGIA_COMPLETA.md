# 🎯 Strategia Arbitraggio BTC Up/Down - Polymarket

## Reverse Engineering di BoshBashBish

Basato su analisi di 1,164 trades reali dal wallet `0x29bc82f761749e67fa00d62896bc6855097b683c`

---

## 📊 Risultati Analizzati

| Metrica | Valore |
|---------|--------|
| VWAP UP | $0.324 |
| VWAP DOWN | $0.558 |
| **VWAP Combinato** | **$0.883** |
| Profitto per coppia | $0.117 (13.2%) |
| Win rate | 7/10 (70%) |
| Profitto totale campione | +$5,828 |

---

## 🧠 La Formula

### Regola Base
```
SE puoi comprare UP + DOWN con costo combinato < $1.00
ALLORA hai profitto garantito
```

### Implementazione Pratica

```python
# THRESHOLDS (derivati dai dati)
UP_BUY_MAX = 0.50      # Compra UP se prezzo <= $0.50
DOWN_BUY_MAX = 0.75    # Compra DOWN se prezzo <= $0.75
AGGRESSIVE_BUY = 0.20  # Sotto questo, compra MOLTO

# POSITION LIMITS
MAX_UNMATCHED_RATIO = 0.30  # Max 30% sbilanciamento
ORDER_SIZE = 100            # Size standard per trade

# LOGICA DECISIONALE
def should_buy(outcome, price, position):

    # 1. Check threshold
    threshold = UP_BUY_MAX if outcome == "up" else DOWN_BUY_MAX
    if price > threshold:
        return False

    # 2. Check unmatched ratio
    if position.unmatched_ratio > MAX_UNMATCHED_RATIO:
        if position.unmatched_side == outcome:
            # Compra solo se MOLTO cheap
            if price > 0.20:
                return False

    # 3. BUY!
    return True
```

---

## 📈 Fasi della Strategia

### Fase 1: Apertura Mercato (minuto 0-2)
```
Prezzo UP ≈ $0.50, Prezzo DOWN ≈ $0.50

→ Compra il lato più vicino a $0.50
→ Di solito DOWN (il bot sembra preferire DOWN inizialmente)
→ Size: 100 shares ogni 2 secondi circa
```

### Fase 2: Il Mercato si Muove (minuto 3-10)
```
Scenario A: BTC sale → UP va a $0.70+, DOWN crolla a $0.30
Scenario B: BTC scende → DOWN va a $0.70+, UP crolla a $0.30

→ Il bot compra AGGRESSIVAMENTE il lato che crolla
→ Obiettivo: accumulare shares a < $0.20
```

### Fase 3: Completamento Arbitraggio (minuto 10-15)
```
Il bot ha comprato:
- Un lato a ~$0.50-0.60 (iniziale)
- L'altro lato a ~$0.15-0.30 (quando è crollato)

Costo combinato: ~$0.70-0.85 < $1.00 ✓
```

---

## 💰 Calcolo P&L

```
MATCHED PAIRS (arbitraggio puro):
  Costo: matched_pairs × combined_avg_price
  Payout: matched_pairs × $1.00
  Profitto: matched_pairs × (1 - combined_avg)

  Esempio: 1000 pairs @ $0.85 = $850 costo → $1000 payout = $150 profitto

UNMATCHED (scommessa direzionale):
  Se il lato unmatched VINCE: bonus profitto
  Se il lato unmatched PERDE: riduce il profitto (o piccola perdita)
```

---

## ⚠️ Gestione del Rischio

### Scenario Peggiore
```
Compri UP a $0.50
UP continua a scendere a $0.05
DOWN sale a $0.95 e NON scende mai

Risultato:
- Non riesci a comprare DOWN a prezzo ragionevole
- UP perde → perdi tutto il costo UP
- Ma: hai comprato a $0.50, non $0.90!
```

### Mitigazione
1. **Non comprare MAI sopra threshold** ($0.50 UP, $0.75 DOWN)
2. **Limita unmatched ratio** (max 30%)
3. **Il lato che crolla diventa MOLTO cheap** ($0.10-0.20)
4. **Perdita massima = costo posizione sbilanciata**

---

## 🛠️ Implementazione Tecnica

### Requisiti
1. **Wallet Polygon** con USDC
2. **API Polymarket** per ordini
3. **WebSocket** per prezzi real-time
4. **Bot** sempre attivo durante i mercati 15-min

### Stack Suggerito
```
- Python 3.10+
- py-clob-client (Polymarket SDK)
- websockets per prezzi real-time
- asyncio per gestione concorrente
```

### Flow Operativo
```
1. Ogni 15 minuti → nuovo mercato BTC Up/Down
2. Bot si connette al nuovo mercato
3. Monitora prezzi ogni 100ms
4. Esegue trades quando condizioni soddisfatte
5. Al settlement → incassa profitto
6. Ripeti
```

---

## 📁 File in questo Repository

| File | Descrizione |
|------|-------------|
| `boshbashbish_btc_december_REAL.json` | 1,164 trades reali del bot |
| `ciclo_VERO_4_30_4_45.json` | Un ciclo completo analizzato |
| `arbitrage_bot.py` | Bot completo (template) |
| `backtest_bot.py` | Backtest con dati reali |
| `fetch_trades.py` | Script per scaricare trades |

---

## ⚡ Quick Start

```bash
# 1. Backtest con dati reali
python3 backtest_bot.py

# 2. Modifica parametri in arbitrage_bot.py

# 3. Per produzione: aggiungi credenziali Polymarket
```

---

## 🚨 DISCLAIMER

Questo è un progetto educativo basato su analisi di dati pubblici.

- Il trading comporta rischi finanziari
- Performance passate non garantiscono risultati futuri
- L'arbitraggio richiede capitale e velocità di esecuzione
- Gas fees su Polygon riducono i margini
- Altri bot competono per le stesse opportunità

**Usa a tuo rischio e pericolo.**

---

## 📊 Statistiche Chiave da Ricordare

```
✓ VWAP combinato target: < $0.90 (= 10%+ profit)
✓ UP: compra sotto $0.50, idealmente $0.20
✓ DOWN: compra sotto $0.75, idealmente $0.50
✓ Max unmatched: 30%
✓ Order size: 100 shares
✓ Frequenza: burst trading (77% trades < 2s apart)
```
