# TradeIQ

TradeIQ is a modular, high-precision institutional trading intelligence engine built in Python and React. It prioritizes identifying clear market structures over generating numerous, low-quality signals.

## Core Features

- **Multi-Factor Confidence Scoring**: Instead of basic indicators, TradeIQ uses a weighted scoring system based on trend alignment, VWAP acceptance, volume expansion, and higher timeframe confluence.
- **Strict Chop Filtration**: Built-in market regime detection uses ATR ratios, EMA slope, and failed breakout tracking to keep you out of choppy, sideways markets.
- **Honest Backtesting**: Integrated backtesting engine reports real win rates, Sharpe ratios, Max Drawdown, and profit factors without overfitting.
- **Explainable Decisions**: Every signal generated is accompanied by a transparent breakdown of reasons (green checks) and warnings (red flags).
- **Responsive Dashboard**: A sleek, dark-themed React dashboard built with `lightweight-charts` and Tailwind CSS.

## Project Structure

- `backend/`: FastAPI application containing all trading intelligence logic.
  - `engines/`: Modular computation engines (Data, Indicator, Regime, Signal, Confidence, Backtest).
- `frontend/`: React application powered by Vite for the user interface.

## Getting Started

### 1. Start the Backend

```bash
cd backend
pip install -r requirements.txt
python -m uvicorn main:app --reload
```

The backend API will be available at `http://localhost:8000`.

### 2. Start the Frontend

```bash
cd frontend
npm install
npm run dev
```

The React dashboard will be available at `http://localhost:5173`.

## Technical Philosophy

*   **Precision over volume:** The system is biased to reject weak setups.
*   **Simple charts:** No indicator bloat. Uses VWAP, EMA200, Volume, and ATR.
*   **Contextual awareness:** Signals are evaluated against the current market regime.

## Disclaimer

This software is for educational and research purposes only. It does not constitute financial advice. Always test strategies thoroughly before using them with real capital.
