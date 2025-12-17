#!/usr/bin/env python3
"""
Polymarket Trade Fetcher for BoshBashBish Bot
Scarica tutti i trades di un wallet da Polymarket e li formatta per l'analisi
"""

import requests
import json
import time
from datetime import datetime
from collections import defaultdict

# Configurazione
WALLET_ADDRESS = "0x29bc82f761749e67fa00d62896bc6855097b683c"
USERNAME = "BoshBashBish"
BASE_URL = "https://data-api.polymarket.com"
OUTPUT_FILE = "boshbashbish_btc_december_trades.json"
ANALYSIS_FILE = "boshbashbish_btc_december_analysis.json"

# Filtro per mercato (None = tutti)
# Filtro su TITLE per prendere solo "Bitcoin Up or Down - December"
MARKET_FILTER = None  # Disabilito il filtro slug
TITLE_FILTER = "Bitcoin Up or Down - December"


def fetch_all_trades(wallet_address: str, limit: int = 100, start_offset: int = 0, title_filter: str = None, max_empty_pages: int = 50) -> list:
    """Scarica trades di un wallet con paginazione, retry e filtro on-the-fly"""
    all_trades = []
    offset = start_offset
    max_retries = 3
    empty_pages_count = 0  # Contatore pagine senza match

    print(f"🔄 Scaricando trades per wallet: {wallet_address}")
    if title_filter:
        print(f"🔍 Filtro attivo: {title_filter}")

    while True:
        url = f"{BASE_URL}/trades"
        params = {
            "maker": wallet_address,
            "limit": limit,
            "offset": offset
        }

        success = False
        for retry in range(max_retries):
            try:
                response = requests.get(url, params=params, timeout=30)
                response.raise_for_status()
                trades = response.json()
                success = True
                break
            except requests.exceptions.RequestException as e:
                print(f"⚠️  Retry {retry+1}/{max_retries} per offset {offset}: {e}")
                time.sleep(2 ** retry)  # Exponential backoff

        if not success:
            print(f"❌ Max retries raggiunto per offset {offset}, salvando trades correnti...")
            break

        if not trades:
            break

        # Filtra on-the-fly se specificato
        if title_filter:
            filtered = [t for t in trades if title_filter in t.get("title", "")]
            if filtered:
                all_trades.extend(filtered)
                empty_pages_count = 0  # Reset counter
                print(f"  📦 Trovati {len(filtered)} trades (totale: {len(all_trades)})")
            else:
                empty_pages_count += 1
                if empty_pages_count >= max_empty_pages:
                    print(f"  ⏹️  {max_empty_pages} pagine senza match, fermando...")
                    break
        else:
            all_trades.extend(trades)
            print(f"  📦 Scaricati {len(all_trades)} trades...")

        if len(trades) < limit:
            break

        offset += limit
        time.sleep(0.3)  # Rate limiting

    print(f"✅ Totale trades filtrati: {len(all_trades)}")
    return all_trades


def format_trade(trade: dict) -> dict:
    """Formatta un singolo trade nel formato richiesto"""
    size = float(trade.get("size", 0))
    price = float(trade.get("price", 0))

    return {
        "timestamp": trade.get("timestamp"),
        "datetime": datetime.fromtimestamp(trade.get("timestamp", 0)).strftime("%Y-%m-%d %H:%M:%S"),
        "side": trade.get("side"),
        "outcome": trade.get("outcome"),
        "size": size,
        "price": price,
        "value": round(size * price, 4),
        "transactionHash": trade.get("transactionHash"),
        "asset": trade.get("asset"),
        "market": {
            "title": trade.get("title"),
            "slug": trade.get("slug"),
            "eventSlug": trade.get("eventSlug"),
            "conditionId": trade.get("conditionId")
        }
    }


def analyze_trades(trades: list) -> dict:
    """Analizza i trades per estrarre statistiche sulla strategia"""

    analysis = {
        "summary": {
            "total_trades": len(trades),
            "total_buy_trades": 0,
            "total_sell_trades": 0,
            "total_volume_usd": 0,
            "avg_trade_size": 0,
            "avg_price": 0,
            "unique_markets": 0,
            "first_trade": None,
            "last_trade": None,
        },
        "by_side": {
            "BUY": {"count": 0, "volume": 0, "avg_price": 0},
            "SELL": {"count": 0, "volume": 0, "avg_price": 0}
        },
        "by_outcome": {
            "Yes": {"count": 0, "volume": 0},
            "No": {"count": 0, "volume": 0}
        },
        "price_distribution": {
            "0-0.1": 0,
            "0.1-0.2": 0,
            "0.2-0.3": 0,
            "0.3-0.4": 0,
            "0.4-0.5": 0,
            "0.5-0.6": 0,
            "0.6-0.7": 0,
            "0.7-0.8": 0,
            "0.8-0.9": 0,
            "0.9-1.0": 0
        },
        "markets_traded": [],
        "hourly_activity": defaultdict(int),
        "daily_activity": defaultdict(int),
        "strategy_indicators": {}
    }

    if not trades:
        return analysis

    markets = set()
    prices = []
    sizes = []
    buy_prices = []
    sell_prices = []

    for trade in trades:
        side = trade.get("side", "")
        price = float(trade.get("price", 0))
        size = float(trade.get("size", 0))
        value = size * price
        outcome = trade.get("outcome", "")
        timestamp = trade.get("timestamp", 0)
        title = trade.get("title", "")

        # Summary stats
        analysis["summary"]["total_volume_usd"] += value
        prices.append(price)
        sizes.append(size)

        # By side
        if side in analysis["by_side"]:
            analysis["by_side"][side]["count"] += 1
            analysis["by_side"][side]["volume"] += value
            if side == "BUY":
                analysis["summary"]["total_buy_trades"] += 1
                buy_prices.append(price)
            else:
                analysis["summary"]["total_sell_trades"] += 1
                sell_prices.append(price)

        # By outcome
        if outcome in analysis["by_outcome"]:
            analysis["by_outcome"][outcome]["count"] += 1
            analysis["by_outcome"][outcome]["volume"] += value

        # Price distribution
        price_bucket = min(int(price * 10), 9)
        bucket_key = f"{price_bucket/10}-{(price_bucket+1)/10}"
        if bucket_key in analysis["price_distribution"]:
            analysis["price_distribution"][bucket_key] += 1

        # Markets
        markets.add(title)

        # Time activity
        if timestamp:
            dt = datetime.fromtimestamp(timestamp)
            analysis["hourly_activity"][dt.hour] += 1
            analysis["daily_activity"][dt.strftime("%Y-%m-%d")] += 1

    # Finalize summary
    analysis["summary"]["unique_markets"] = len(markets)
    analysis["summary"]["avg_trade_size"] = round(sum(sizes) / len(sizes), 2) if sizes else 0
    analysis["summary"]["avg_price"] = round(sum(prices) / len(prices), 4) if prices else 0
    analysis["summary"]["total_volume_usd"] = round(analysis["summary"]["total_volume_usd"], 2)

    # First and last trade
    sorted_trades = sorted(trades, key=lambda x: x.get("timestamp", 0))
    if sorted_trades:
        analysis["summary"]["first_trade"] = datetime.fromtimestamp(sorted_trades[0].get("timestamp", 0)).strftime("%Y-%m-%d %H:%M:%S")
        analysis["summary"]["last_trade"] = datetime.fromtimestamp(sorted_trades[-1].get("timestamp", 0)).strftime("%Y-%m-%d %H:%M:%S")

    # Average prices by side
    if buy_prices:
        analysis["by_side"]["BUY"]["avg_price"] = round(sum(buy_prices) / len(buy_prices), 4)
    if sell_prices:
        analysis["by_side"]["SELL"]["avg_price"] = round(sum(sell_prices) / len(sell_prices), 4)

    # Markets list (top 20 by frequency)
    market_counts = defaultdict(int)
    for trade in trades:
        market_counts[trade.get("title", "Unknown")] += 1

    analysis["markets_traded"] = [
        {"title": title, "trade_count": count}
        for title, count in sorted(market_counts.items(), key=lambda x: -x[1])[:20]
    ]

    # Strategy indicators
    analysis["strategy_indicators"] = {
        "prefers_low_prices": sum(1 for p in prices if p < 0.3) / len(prices) if prices else 0,
        "prefers_high_prices": sum(1 for p in prices if p > 0.7) / len(prices) if prices else 0,
        "buy_sell_ratio": analysis["summary"]["total_buy_trades"] / max(analysis["summary"]["total_sell_trades"], 1),
        "yes_no_ratio": analysis["by_outcome"]["Yes"]["count"] / max(analysis["by_outcome"]["No"]["count"], 1),
        "avg_trades_per_day": len(trades) / max(len(analysis["daily_activity"]), 1),
        "most_active_hour": max(analysis["hourly_activity"].items(), key=lambda x: x[1])[0] if analysis["hourly_activity"] else None,
    }

    # Round strategy indicators
    for key in ["prefers_low_prices", "prefers_high_prices", "buy_sell_ratio", "yes_no_ratio", "avg_trades_per_day"]:
        if key in analysis["strategy_indicators"]:
            analysis["strategy_indicators"][key] = round(analysis["strategy_indicators"][key], 3)

    # Convert defaultdicts to regular dicts for JSON serialization
    analysis["hourly_activity"] = dict(sorted(analysis["hourly_activity"].items()))
    analysis["daily_activity"] = dict(sorted(analysis["daily_activity"].items()))

    return analysis


def main():
    print("=" * 60)
    print(f"  POLYMARKET TRADE FETCHER - {USERNAME}")
    print("=" * 60)
    print()

    # Fetch all trades con filtro on-the-fly
    raw_trades = fetch_all_trades(WALLET_ADDRESS, title_filter=TITLE_FILTER)

    if not raw_trades:
        print("❌ Nessun trade trovato!")
        return

    # Filter by market slug if specified
    if MARKET_FILTER:
        print(f"\n🔍 Filtrando per slug mercato: {MARKET_FILTER}")
        original_count = len(raw_trades)
        raw_trades = [t for t in raw_trades if MARKET_FILTER in t.get("slug", "")]
        print(f"   Trades filtrati: {len(raw_trades)} / {original_count}")

    # Filter by title - già fatto on-the-fly se TITLE_FILTER era specificato
    # in fetch_all_trades(), quindi qui non serve più

    if not raw_trades:
        print("❌ Nessun trade trovato dopo il filtro!")
        return

    # Format trades
    print("\n🔧 Formattando i trades...")
    formatted_trades = [format_trade(t) for t in raw_trades]

    # Sort by timestamp (most recent first)
    formatted_trades.sort(key=lambda x: x["timestamp"] or 0, reverse=True)

    # Analyze trades
    print("📊 Analizzando la strategia...")
    analysis = analyze_trades(raw_trades)

    # Prepare output
    output = {
        "metadata": {
            "username": USERNAME,
            "wallet_address": WALLET_ADDRESS,
            "fetched_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_trades": len(formatted_trades)
        },
        "trades": formatted_trades
    }

    # Save trades
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"\n💾 Trades salvati in: {OUTPUT_FILE}")

    # Save analysis
    analysis_output = {
        "metadata": {
            "username": USERNAME,
            "wallet_address": WALLET_ADDRESS,
            "analyzed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        },
        "analysis": analysis
    }

    with open(ANALYSIS_FILE, "w", encoding="utf-8") as f:
        json.dump(analysis_output, f, indent=2, ensure_ascii=False)
    print(f"📈 Analisi salvata in: {ANALYSIS_FILE}")

    # Print summary
    print("\n" + "=" * 60)
    print("  RIEPILOGO STRATEGIA")
    print("=" * 60)
    print(f"\n📊 Statistiche Generali:")
    print(f"   • Totale trades: {analysis['summary']['total_trades']}")
    print(f"   • Volume totale: ${analysis['summary']['total_volume_usd']:,.2f}")
    print(f"   • Mercati unici: {analysis['summary']['unique_markets']}")
    print(f"   • Primo trade: {analysis['summary']['first_trade']}")
    print(f"   • Ultimo trade: {analysis['summary']['last_trade']}")

    print(f"\n💰 Per Tipo:")
    print(f"   • BUY: {analysis['by_side']['BUY']['count']} trades (avg price: {analysis['by_side']['BUY']['avg_price']})")
    print(f"   • SELL: {analysis['by_side']['SELL']['count']} trades (avg price: {analysis['by_side']['SELL']['avg_price']})")

    print(f"\n🎯 Per Outcome:")
    print(f"   • Yes: {analysis['by_outcome']['Yes']['count']} trades")
    print(f"   • No: {analysis['by_outcome']['No']['count']} trades")

    print(f"\n🔍 Indicatori Strategia:")
    indicators = analysis['strategy_indicators']
    print(f"   • Preferenza prezzi bassi (<0.3): {indicators['prefers_low_prices']*100:.1f}%")
    print(f"   • Preferenza prezzi alti (>0.7): {indicators['prefers_high_prices']*100:.1f}%")
    print(f"   • Ratio BUY/SELL: {indicators['buy_sell_ratio']:.2f}")
    print(f"   • Ratio Yes/No: {indicators['yes_no_ratio']:.2f}")
    print(f"   • Media trades/giorno: {indicators['avg_trades_per_day']:.1f}")
    print(f"   • Ora più attiva: {indicators['most_active_hour']}:00")

    print("\n" + "=" * 60)
    print("  DONE!")
    print("=" * 60)


if __name__ == "__main__":
    main()
