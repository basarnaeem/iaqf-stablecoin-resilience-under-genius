# Crypto Market Microstructure & High-Frequency Data Pipeline  
**IAQF 2026 Research Project**

## Overview
This repository contains a full data pipeline for collecting, processing, and analyzing **high-frequency cryptocurrency market data**, with a focus on **market microstructure**.


The goal is to build clean, reproducible datasets suitable for **quantitative research, feature engineering, and predictive modeling**.

---

## Exchanges Covered
- **Coinbase** — historical 1-minute candles (primary historical source)
- **Binance** — Level-2 order book via WebSocket (optional / region dependent)
- **OKX** — Level-2 order book via WebSocket
- **Crypto.com** — Level-2 order book via WebSocket
- **Bitfinex** — Level-2 order book via WebSocket

---

## Assets & Instruments
Base assets:
- BTC
- ETH

Quote currencies (availability varies by exchange):
- USD
- USDT
- USDC
- EUR

---

## Time Period
- **Historical window:**  
  **March 1, 2023 → March 21, 2023 (UTC)**

---

## Repository Structure


