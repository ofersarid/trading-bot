# Trading Diary: $100 → $1,000 Challenge

**Starting Balance:** $100  
**Current Balance:** $100

---

## January 11, 2026

### 🧠 Mindset Established

- This is a **learning exercise** - gaining experience and skill is the primary goal
- It's OK to blow the account - that's what paper trading is for
- Focus on understanding mechanics, not just profits
- Every loss is a lesson, every win should be analyzed

### 📋 Trading Setup Configured

| Parameter | Value |
|-----------|-------|
| **Instrument** | BTC Perpetuals |
| **Exchange** | Bybit |
| **Max Leverage** | 10x |
| **Timeframe** | 15m |
| **Account Type** | Paper Trading |

**TradingView Paper Account Settings:**

| Setting | Value |
|---------|-------|
| Account Name | ofersarid |
| Futures Leverage | 10:1 |
| Crypto Leverage | 1:1 |
| Commission (Others) | 0.06% |
| Commission (Futures) | $0.075/contract |

### 🛠️ Strategy Development

**Craig Percoco Strategy (3-Step Setup)**  
Source: "The Perfect Beginner DAY TRADING Strategy (Step-by-Step)"

| Indicator | Status | File |
|-----------|--------|------|
| Fair Value Gap (FVG) | ✅ Complete | `indicators/fvg_indicator_v1.pine` |
| Market Structure (BOS + CHoCH) | ✅ Complete | `indicators/market_structure_v1.pine` |
| Combined Strategy | 📋 Ready to test | `strategies/choch_fvg_strategy_v1.pine` |

**Work completed:**

*FVG Indicator:*
- ✅ Created FVG indicator with customizable constants
- ✅ Added 50% midline (Consequential Encroachment - Craig's entry level)
- ✅ Added mitigation tracking (FVGs turn gray when filled)
- ✅ Added age/count limits to keep chart clean (Craig focuses on recent FVGs only)

*Market Structure Indicator:*
- ✅ Swing point detection (HH, HL, LH, LL labels)
- ✅ Break of Structure (BOS) detection with lines
- ✅ Change of Character (CHoCH) detection for trend reversals
- ✅ Added constants section for easy customization
- ✅ Increased label size for readability

---
