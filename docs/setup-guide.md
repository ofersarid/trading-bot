# Hyperliquid Paper Trading Setup

This guide walks you through setting up the trading bot.

## Quick Start (Simulation Mode)

**No API keys needed!** For paper trading simulation, just run:

```bash
cd /Users/ofers/Documents/private/trading-bot
source venv/bin/activate
python bot/hyperliquid/public_data.py
```

## Prerequisites

- Python 3.8+
- A web browser (for testnet setup)
- MetaMask or another Ethereum wallet extension (for testnet/live only)

---

## Mode 1: Simulation (Recommended to Start)

Simulation mode uses live market data but simulates orders locally. No wallet or API keys needed.

1. Activate the virtual environment:
   ```bash
   source venv/bin/activate
   ```

2. Test market data:
   ```bash
   python bot/hyperliquid/public_data.py
   ```

You're ready to develop and test strategies!

---

## Mode 2: Testnet Trading

For testing real order execution with fake money.

### Step 1: Create Your Master Account

1. Go to **Hyperliquid Testnet**: https://app.hyperliquid-testnet.xyz
2. Connect your wallet (MetaMask recommended) or sign up with email
3. Your wallet address becomes your "master account"

> **Note**: If using email login, Privy generates different wallet addresses for mainnet vs testnet. For consistency, use a wallet extension.

### Step 2: Get Testnet Funds

1. **Important**: You must have deposited on mainnet with the same address first (even a tiny amount)
2. Go to the testnet faucet: https://app.hyperliquid-testnet.xyz/drip
3. Claim 1,000 mock USDC

### Step 3: Create an API Wallet

1. Go to: https://app.hyperliquid-testnet.xyz/API
2. Click **"Create API Wallet"** or **"Generate New Key"**
3. Give it a name (e.g., "paper-trading-bot")
4. **CRITICAL**: Copy the private key immediately - you'll only see it once!
5. Store the private key securely in `.env`

### Step 4: Configure Environment

Create a `.env` file with:
```
HYPERLIQUID_PRIVATE_KEY=your_api_wallet_private_key_here
HYPERLIQUID_ENV=testnet
```

---

## API Endpoints Reference

| Environment | REST API | WebSocket |
|-------------|----------|-----------|
| Testnet | `https://api.hyperliquid-testnet.xyz` | `wss://api.hyperliquid-testnet.xyz/ws` |
| Mainnet | `https://api.hyperliquid.xyz` | `wss://api.hyperliquid.xyz/ws` |

---

## Security Notes

- Never commit `.env` files or private keys to git
- API wallets can only trade, not withdraw - but still keep keys secure
- Use testnet for all development and testing
- The testnet uses mock funds - no real money at risk

---

## Troubleshooting

### "Insufficient balance" error
- Make sure you've claimed from the faucet
- Check your balance at https://app.hyperliquid-testnet.xyz

### "Invalid signature" error
- Verify your private key is correct (should start with `0x` or be 64 hex chars)
- Make sure you're using the API wallet key, not your main wallet

### "Rate limited" error
- Testnet has stricter rate limits
- Add delays between requests (the SDK handles this mostly)
