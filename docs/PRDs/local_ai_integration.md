# PRD: Local AI Model Integration

**Version:** 1.0  
**Date:** 2026-01-17  
**Status:** Draft  

---

## 1. Overview

### 1.1 Problem Statement
We need AI-powered trade analysis but cannot afford cloud API costs (Claude, GPT-4, etc.). We need a solution that:
- Runs completely locally (no API costs)
- Works on consumer hardware (Mac M1/M2/M3)
- Provides fast inference for real-time decisions
- Can analyze market data and provide trading signals

### 1.2 Goals
- Integrate a free, open-source LLM for trade analysis
- Achieve <2 second response time for market analysis
- Run on 8GB+ RAM machines
- No internet required for inference

---

## 2. Local LLM Options

### 2.1 Recommended: Ollama + Mistral/Llama

| Option | Model Size | RAM Needed | Speed | Quality |
|--------|-----------|------------|-------|---------|
| **Mistral 7B** | 4GB | 8GB | ⚡ Fast | ★★★★☆ |
| **Llama 3.2 3B** | 2GB | 6GB | ⚡⚡ Very Fast | ★★★☆☆ |
| **Phi-3 Mini** | 2GB | 6GB | ⚡⚡ Very Fast | ★★★☆☆ |
| **Qwen2.5 7B** | 4GB | 8GB | ⚡ Fast | ★★★★☆ |
| **Llama 3.2 7B** | 4GB | 8GB | ⚡ Fast | ★★★★★ |

### 2.2 Why Ollama?
- **One-command install**: `brew install ollama`
- **Simple API**: REST endpoint at `localhost:11434`
- **Model management**: `ollama pull mistral`
- **Optimized for Mac**: Uses Metal GPU acceleration
- **Active community**: Regular updates and new models

### 2.3 Alternative Options
1. **llama.cpp** - Lower level, more control, harder setup
2. **LM Studio** - GUI app, good for testing models
3. **Hugging Face** - Python library, more complex

---

## 3. Technical Architecture

### 3.1 Integration Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    TRADING BOT                               │
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐   │
│  │ Market Data  │───►│ AI Analyzer  │───►│  Decision    │   │
│  │  (WebSocket) │    │   (Local)    │    │   Engine     │   │
│  └──────────────┘    └──────┬───────┘    └──────────────┘   │
│                             │                                │
└─────────────────────────────┼────────────────────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │     OLLAMA       │
                    │  localhost:11434 │
                    │                  │
                    │  ┌────────────┐  │
                    │  │ Mistral 7B │  │
                    │  └────────────┘  │
                    └──────────────────┘
```

### 3.2 New Components

```
bot/
├── ai/
│   ├── __init__.py
│   ├── ollama_client.py    # Ollama API wrapper
│   ├── prompts.py          # Trading analysis prompts
│   ├── analyzer.py         # Market analysis logic
│   └── models.py           # AI response models
```

### 3.3 API Interface

```python
# bot/ai/ollama_client.py
import httpx

class OllamaClient:
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self.model = "mistral"  # or llama3.2, phi3, etc.
    
    async def analyze(self, prompt: str) -> str:
        """Send prompt to local Ollama and get response."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,  # Lower = more consistent
                        "num_predict": 200,  # Limit response length
                    }
                },
                timeout=30.0
            )
            return response.json()["response"]
```

---

## 4. AI Analysis Features

### 4.1 Market Analysis Prompt

```python
MARKET_ANALYSIS_PROMPT = """
You are a crypto trading analyst. Analyze this market data and provide a brief assessment.

CURRENT PRICES:
{prices}

MOMENTUM (60s):
{momentum}

ORDER BOOK IMBALANCE:
{orderbook}

RECENT TRADES:
{recent_trades}

Respond in this exact format:
SENTIMENT: [BULLISH/BEARISH/NEUTRAL]
CONFIDENCE: [1-10]
SIGNAL: [LONG/SHORT/WAIT]
REASON: [One sentence explanation]
"""
```

### 4.2 Analysis Types

| Analysis | Frequency | Purpose |
|----------|-----------|---------|
| **Market Sentiment** | Every 30s | Overall market direction |
| **Entry Signal** | On opportunity | Should we enter this trade? |
| **Exit Signal** | While in position | Should we close? |
| **Risk Assessment** | Before trade | Position size recommendation |

### 4.3 Expected AI Response

```json
{
  "sentiment": "BULLISH",
  "confidence": 7,
  "signal": "LONG",
  "coin": "BTC",
  "reason": "Strong buying pressure with 3:1 bid/ask ratio and positive momentum"
}
```

---

## 5. Token Usage Tracking

### 5.1 Metrics to Track

```python
@dataclass
class AIMetrics:
    total_tokens: int = 0
    total_calls: int = 0
    avg_response_time_ms: float = 0
    model_name: str = ""
    
    # Per-session stats
    session_tokens: int = 0
    session_calls: int = 0
```

### 5.2 Display in UI

```
🧠 AI REASONING │ 🤖 LOCAL AI │ Model: mistral:7b │ Tokens: 12,450 │ Calls: 42 │ Avg: 850ms
```

---

## 6. Setup Instructions

### 6.1 Install Ollama

```bash
# macOS
brew install ollama

# Or download from https://ollama.ai
```

### 6.2 Download a Model

```bash
# Recommended for 8GB RAM
ollama pull mistral

# Lighter option for 6GB RAM  
ollama pull phi3

# Best quality (needs 16GB RAM)
ollama pull llama3.2
```

### 6.3 Start Ollama Server

```bash
# Runs in background, starts automatically on boot
ollama serve
```

### 6.4 Test Connection

```bash
curl http://localhost:11434/api/generate -d '{
  "model": "mistral",
  "prompt": "Say hello"
}'
```

---

## 7. Implementation Phases

### Phase 1: Basic Integration (MVP)
- [ ] Install Ollama and download Mistral
- [ ] Create `OllamaClient` class
- [ ] Add basic market analysis prompt
- [ ] Display AI output in dashboard
- [ ] Track token usage

### Phase 2: Smart Analysis
- [ ] Tune prompts for better trading signals
- [ ] Add entry/exit analysis
- [ ] Implement confidence scoring
- [ ] Add AI toggle in UI (Rule-based vs AI)

### Phase 3: Advanced Features
- [ ] Multi-model support (switch between models)
- [ ] Prompt caching for faster responses
- [ ] Historical analysis learning
- [ ] Custom fine-tuned model (if needed)

---

## 8. Performance Targets

| Metric | Target | Acceptable |
|--------|--------|------------|
| Response Time | <1s | <3s |
| Memory Usage | <4GB | <6GB |
| CPU Usage | <50% | <80% |
| Accuracy | >70% | >60% |

---

## 9. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Slow inference | Missed opportunities | Use smaller model, limit prompt size |
| Wrong signals | Bad trades | Always show confidence, require human confirmation |
| Model hallucinations | False analysis | Structured output format, validation |
| High RAM usage | System slowdown | Use quantized models (Q4_K_M) |

---

## 10. Success Criteria

1. ✅ AI responds in <2 seconds
2. ✅ No API costs incurred
3. ✅ Works offline
4. ✅ Token usage displayed in UI
5. ✅ Can toggle between Rule-based and AI mode
6. ✅ AI provides actionable trading signals

---

## 11. Open Questions

1. **Which model performs best for trading analysis?**
   - Need to test Mistral vs Llama vs Phi-3

2. **How often should AI analyze?**
   - Every tick? Every 30s? Only on opportunities?

3. **Should AI have veto power over rule-based signals?**
   - Or just advisory?

4. **Fine-tuning: Is it worth creating a custom model?**
   - Would need trading data for training

---

## Appendix A: Model Comparison Tests

*To be filled after testing*

| Model | Response Time | Quality Score | RAM Used |
|-------|--------------|---------------|----------|
| mistral:7b | TBD | TBD | TBD |
| llama3.2:3b | TBD | TBD | TBD |
| phi3:mini | TBD | TBD | TBD |

---

## Appendix B: Sample Prompts Library

### Quick Sentiment Check
```
BTC: $95,000 (+0.3% 1min), ETH: $3,300 (-0.1% 1min)
Order book: 60% bids. Recent: 5 buys, 2 sells.
One word: BULLISH, BEARISH, or NEUTRAL?
```

### Trade Entry Analysis
```
Opportunity: LONG BTC at $95,000
Momentum: +0.35% in 60s
Book: 65% bids
Risk: What's your confidence (1-10) and position size suggestion?
```
