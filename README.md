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
