# Liquidation Hunter

## Core Idea

When leveraged traders get liquidated, their positions are force-closed at market, creating predictable price cascades. Position before the cascade and ride the wave.

## How It Works

The system monitors open interest, funding rates, and leverage ratios across perps platforms (Hyperliquid, Binance Futures, dYdX). When conditions are ripe for a liquidation cascade, take a position aligned with the expected cascade direction.

## Signal Stack

### 1. Funding Rate Extremes
When funding is heavily positive (longs paying shorts), the market is over-leveraged long. A small dip triggers cascading long liquidations.

### 2. Open Interest vs. Price Divergence
OI rising while price stalls = fragile positioning. A breakout in either direction will be violent.

### 3. Liquidation Heatmaps
Map out price levels where liquidation density is highest, then calculate the "gravitational pull" of each cluster. Turn heatmap data into a trigger system.

### 4. Exchange-Specific Liquidation Engines
Each exchange handles liquidations differently:
- **Hyperliquid** — On-chain liquidation engine, fully observable
- **Binance** — Insurance fund behavior creates different dynamics

## Execution Logic

```
IF funding_rate > threshold (e.g., 0.05%)
AND open_interest_delta > X% in last 4h
AND price approaching liquidation_cluster within 1.5%
THEN:
  - Open position aligned with cascade direction
  - Size: proportional to estimated liquidation volume
  - Take profit: at the liquidation cluster center
  - Stop loss: tight, above the entry zone
  - Time limit: close if no cascade within N minutes
```

## The Nudge Trade

Layer in a small "nudge" trade — if price is sitting just above a massive liquidation cluster, a well-timed market sell can be the domino that starts the cascade. This is legal on most crypto venues (unlike in TradFi) but ethically gray.

## Expected Edge

55-65% win rate with 2:1+ reward/risk when cascades trigger. The key is patience — only take setups where the liquidation map is dense.

## Hyperliquid Data Visibility

### What IS Visible On-Chain

- **Open orders** — The order book is fully on-chain. You can query any wallet's open orders via the `frontendOpenOrders` API endpoint, which includes `orderType` and `triggerCondition` for conditional orders (TP/SL).
- **Positions** — Every wallet's position size, entry price, and liquidation price is public.
- **Trade history** — All fills are on-chain and queryable.

### Stop Loss Visibility

TP/SL orders on Hyperliquid are **trigger orders** — they only become market orders when the price threshold is hit. They use the **mark price** to trigger. These trigger orders are stored on-chain and can be queried per wallet.

However:
- There is **no single API endpoint** that aggregates all traders' SL levels into a heatmap
- You need to **scan wallets individually** to build an aggregate SL map
- Big whale wallets can be tracked via tools like CoinGlass

### Building the Edge

Combine these on-chain data sources:
1. **Liquidation levels** — Calculated from position + leverage, available via heatmap tools
2. **Individual whale SL levels** — Queryable per wallet via Hyperliquid API
3. **Order book depth** — On-chain, shows where limit orders cluster

This gives more data than any CEX — you can build a custom SL heatmap by scanning known active wallets via the Hyperliquid API.

## Free Liquidation Heatmap Tools

| Tool | URL |
|------|-----|
| CoinGlass | https://www.coinglass.com/hyperliquid-liquidation-map |
| HyperDash | https://hyperdash.info/liqmap |
| Kiyotaka | https://kiyotaka.ai |
| Trading Different | https://tradingdifferent.com/dashboard/liquidation-heatmap |
| CoinAnk | https://coinank.com/chart/derivatives/liq-heat-map |
