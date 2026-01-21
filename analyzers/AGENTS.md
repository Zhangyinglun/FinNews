# AGENTS.md — Analyzers Directory

## OVERVIEW
Rule-based market analysis layer. Processes price data into signals before LLM consumption.

## MODULES
| Module | Purpose | Lines |
|--------|---------|-------|
| `rule_engine.py` | Threshold-based market signal generation | 258 |
| `market_analyzer.py` | Multi-window data organization + LLM prompt builder | 347 |

## RULE ENGINE (`rule_engine.py`)

Generates `MarketSignal` from price data:

**VIX Analysis:**
- `VIX > 20` → `AlertLevel.WARNING`
- `VIX change > 5%` → `AlertLevel.CRITICAL` + `is_urgent=True`

**Macro Bias:**
- DXY↑ + US10Y↑ → `MacroBias.BEARISH` (bearish for gold)
- DXY↓ + US10Y↓ → `MacroBias.BULLISH` (bullish for gold)

**Sentiment Score:** -1.0 to +1.0 based on VIX, DXY, US10Y, gold price changes.

**Thresholds** configured in `config/config.py`:
- `VIX_ALERT_THRESHOLD`, `VIX_SPIKE_PERCENT`
- `DXY_CHANGE_THRESHOLD`, `US10Y_CHANGE_THRESHOLD`

## MARKET ANALYZER (`market_analyzer.py`)

Organizes data into three time windows:

| Window | Duration | Data Types |
|--------|----------|------------|
| Flash | 24 hours | VIX, DXY, US10Y, breaking news |
| Cycle | 7 days | CPI, PCE, NFP, weekly news |
| Trend | 30 days | Long-term trends, ETF flows |

**Key methods:**
- `organize_data(records, signal)` → `MultiWindowData`
- `build_llm_prompt(data, signal)` → formatted string for LLM

## ADDING RULES
1. Add threshold constants to `config/config.py`
2. Add analysis logic to `RuleEngine.analyze()`
3. Update `MarketSignal` model in `models/analysis.py` if new fields needed
