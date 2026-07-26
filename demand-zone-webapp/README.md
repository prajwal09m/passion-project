# Demand Zone AI - Web Application

A professional web application showcasing the ML-powered demand zone trading system. Built with Next.js, TypeScript, and Tailwind CSS, featuring TradingView charts, Motion.dev animations, and a dark fintech-inspired design.

## Overview

This application visualizes the machine learning pipeline for demand zone detection and prediction on US stocks. It includes:

- **Landing Page**: System overview with key metrics (AUC, signals analyzed, model performance)
- **Stock Analysis Dashboard**: Interactive chart with demand zone overlays and ML predictions
- **Model Performance Page**: Model comparison (Random Forest, XGBoost, LightGBM) with feature importance
- **Backtesting Page**: Equity curve visualization and trade history

## Tech Stack

- **Frontend**: Next.js 14.2.5 + React 18 + TypeScript
- **Styling**: Tailwind CSS with custom dark theme
- **Charts**: TradingView Lightweight Charts
- **Animations**: Framer Motion (Motion.dev)
- **Icons**: Lucide React

## Installation

```bash
cd demand-zone-webapp
npm install
```

## Development

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

## Build

```bash
npm run build
npm start
```

## Project Structure

```
demand-zone-webapp/
├── src/
│   ├── app/
│   │   ├── page.tsx              # Landing page
│   │   ├── analysis/
│   │   │   └── page.tsx          # Stock analysis dashboard
│   │   ├── performance/
│   │   │   └── page.tsx          # Model performance page
│   │   ├── backtest/
│   │   │   └── page.tsx          # Backtesting page
│   │   ├── layout.tsx            # Root layout
│   │   └── globals.css           # Global styles
│   └── components/              # Reusable components (to be added)
├── public/                       # Static assets
├── tailwind.config.ts           # Tailwind configuration
├── tsconfig.json                # TypeScript configuration
├── next.config.js               # Next.js configuration
└── package.json                 # Dependencies
```

## Design System

### Colors
- **Background**: `#0a0a0a`
- **Surface**: `#1a1a1a`
- **Surface2**: `#252525`
- **Border**: `#333333`
- **Accent**: `#3b82f6` (blue)
- **Text**: `#f5f5f5`
- **Text2**: `#a3a3a3`
- **Success**: `#22c55e`
- **Danger**: `#ef4444`
- **Warning**: `#f59e0b`

### Typography
- **Sans**: Inter (primary)
- **Mono**: JetBrains Mono (code/numbers)

## Pages

### Landing Page (`/`)
- System overview and architecture explanation
- Key metrics display (AUC, signals, precision, supported stocks)
- Feature highlights
- Navigation to other pages

### Stock Analysis (`/analysis`)
- Stock ticker search
- TradingView candlestick chart with demand zone overlay
- ML prediction metrics (confidence score, expected return, risk level)
- Demand zone details (price, width, touches, strength)

### Model Performance (`/performance`)
- Model comparison table (Random Forest vs XGBoost vs LightGBM)
- Top 10 feature importance visualization
- Key metrics (AUC, precision, recall, F1 score)

### Backtesting (`/backtest`)
- Equity curve chart
- Key backtest metrics (total return, win rate, Sharpe ratio, max drawdown)
- Recent trade history table

## Data Sources

Currently uses mock data for demonstration. The application is designed to connect to the existing ML pipeline:

- **Dataset**: V10 with 57,848 signals and 118 features
- **Models**: Random Forest (best), XGBoost, LightGBM
- **Performance**: AUC 0.6849, Precision 23.0%, Recall 72.7%

## Backend Integration (Future)

The application is structured to integrate with a FastAPI backend for real ML predictions:

```python
# Planned backend endpoints
POST /api/analyze          # Analyze stock ticker
GET  /api/stock/{ticker}   # Get stock data with demand zones
GET  /api/predict/{ticker} # Get ML prediction
GET  /api/performance      # Get model metrics
GET  /api/features         # Get feature importance
GET  /api/backtest         # Get backtest results
```

## ML Pipeline Integration

The web application connects to the existing ML pipeline located in `../Python/`:

- `generate_ml_dataset.py` - Dataset generation
- `ml_demand_zone_trainer.py` - Model training
- `run_pipeline.py` - Pipeline orchestration

## Deployment

### Vercel (Recommended)
```bash
npm install -g vercel
vercel
```

### Docker
```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build
EXPOSE 3000
CMD ["npm", "start"]
```

## License

MIT

## Notes

- The application uses mock data for demonstration purposes
- Real ML integration requires backend API development
- Charts use TradingView Lightweight Charts for professional financial visualization
- Animations use Framer Motion for smooth UI transitions
- Design inspired by Bloomberg Terminal, TradingView, and Linear
