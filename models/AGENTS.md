# AGENTS.md — Models Directory

## OVERVIEW
Pydantic data models for market data and analysis results.

## MODULES
| Module | Purpose |
|--------|---------|
| `market_data.py` | Price, economic, news data models + multi-window containers |
| `analysis.py` | Alert levels, market signals, analysis results |

## KEY MODELS

### Market Data (`market_data.py`)
| Model | Purpose |
|-------|---------|
| `PriceData` | Ticker price with OHLCV, change %, MA5 |
| `EconomicData` | FRED indicator values |
| `NewsItem` | News with title, summary, source, impact_tag, window_type |
| `FlashWindowData` | 24h window: VIX, DXY, US10Y, gold/silver, breaking news |
| `CycleWindowData` | 7d window: CPI, PCE, NFP, fed_rate, weekly news |
| `TrendWindowData` | 30d window: central bank buying, ETF flows, trend news |
| `MultiWindowData` | Aggregates Flash + Cycle + Trend |

### Analysis (`analysis.py`)
| Model | Purpose |
|-------|---------|
| `AlertLevel` | Enum: `NORMAL`, `WARNING`, `CRITICAL` |
| `MacroBias` | Enum: `利多` (bullish), `利空` (bearish), `中性` (neutral) |
| `MarketSignal` | Rule engine output: VIX/DXY/US10Y values, alerts, sentiment_score |
| `AnalysisResult` | Complete result: signal + email content + stats |

## CONVENTIONS
- All models use `class Config: extra = "allow"` for flexibility
- `Field(...)` with Chinese descriptions
- `default_factory=datetime.now` for timestamps
- Use `Optional[...]` for nullable fields

## ADDING MODELS
1. Define Pydantic model in appropriate module
2. Export in `models/__init__.py`
3. Update dependent code (analyzers, storage)
