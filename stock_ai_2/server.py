import asyncio
import json
import math
import os
import time
from typing import Dict, List, Optional

import httpx
import yfinance as yf
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

app = FastAPI(title="NSE Live Trading & AI Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OLLAMA_HOST = "http://localhost:11434"

NSE_STOCKS = [
    {"symbol": "RELIANCE", "name": "Reliance Industries Ltd.", "sector": "Energy"},
    {"symbol": "TCS", "name": "Tata Consultancy Services Ltd.", "sector": "IT"},
    {"symbol": "HDFCBANK", "name": "HDFC Bank Ltd.", "sector": "Financials"},
    {"symbol": "INFY", "name": "Infosys Ltd.", "sector": "IT"},
    {"symbol": "ICICIBANK", "name": "ICICI Bank Ltd.", "sector": "Financials"},
    {"symbol": "BHARTIARTL", "name": "Bharti Airtel Ltd.", "sector": "Telecom"},
    {"symbol": "SBIN", "name": "State Bank of India", "sector": "Financials"},
    {"symbol": "LTIM", "name": "LTIMindtree Ltd.", "sector": "IT"},
    {"symbol": "ITC", "name": "ITC Ltd.", "sector": "FMCG"},
    {"symbol": "LT", "name": "Larsen & Toubro Ltd.", "sector": "Construction"},
    {"symbol": "HINDUNILVR", "name": "Hindustan Unilever Ltd.", "sector": "FMCG"},
    {"symbol": "AXISBANK", "name": "Axis Bank Ltd.", "sector": "Financials"},
    {"symbol": "KOTAKBANK", "name": "Kotak Mahindra Bank Ltd.", "sector": "Financials"},
    {"symbol": "M&M", "name": "Mahindra & Mahindra Ltd.", "sector": "Automobile"},
    {"symbol": "TATAMOTORS", "name": "Tata Motors Ltd.", "sector": "Automobile"},
    {"symbol": "SUNPHARMA", "name": "Sun Pharmaceutical Ind. Ltd.", "sector": "Pharma"},
    {"symbol": "NTPC", "name": "NTPC Ltd.", "sector": "Power"},
    {"symbol": "POWERGRID", "name": "Power Grid Corp of India", "sector": "Power"},
    {"symbol": "TITAN", "name": "Titan Company Ltd.", "sector": "Consumer Durables"},
    {"symbol": "BAJFINANCE", "name": "Bajaj Finance Ltd.", "sector": "Financials"},
    {"symbol": "MARUTI", "name": "Maruti Suzuki India Ltd.", "sector": "Automobile"},
    {"symbol": "ADANIENT", "name": "Adani Enterprises Ltd.", "sector": "Metals & Mining"},
    {"symbol": "ULTRACEMCO", "name": "UltraTech Cement Ltd.", "sector": "Construction"},
    {"symbol": "COALINDIA", "name": "Coal India Ltd.", "sector": "Energy"},
    {"symbol": "TATASTEEL", "name": "Tata Steel Ltd.", "sector": "Metals"}
]

# Welford's Algorithm for Real-Time Analytics
class StreamingStats:
    def __init__(self, window_size: int = 50):
        self.window_size = window_size
        self.history: List[float] = []

    def update(self, price: float) -> dict:
        self.history.append(price)
        if len(self.history) > self.window_size:
            self.history.pop(0)

        count = len(self.history)
        mean = sum(self.history) / count
        variance = sum((x - mean) ** 2 for x in self.history) / count if count > 1 else 1.0
        std_dev = math.sqrt(variance) if variance > 0 else 0.001
        z_score = (price - mean) / std_dev if std_dev > 0 else 0.0

        return {
            "mean": round(mean, 2),
            "std_dev": round(std_dev, 2),
            "z_score": round(z_score, 2),
            "anomaly": abs(z_score) > 2.0
        }

class LiveMarketEngine:
    def __init__(self):
        self.stats = {s["symbol"]: StreamingStats() for s in NSE_STOCKS}
        self.last_known_ticks: Dict[str, dict] = {}

    async def fetch_live_tick(self, symbol: str) -> dict:
        ticker_symbol = f"{symbol}.NS"
        try:
            loop = asyncio.get_event_loop()
            ticker = yf.Ticker(ticker_symbol)
            df = await loop.run_in_executor(None, lambda: ticker.history(period="1d", interval="1m"))

            if not df.empty:
                current_price = round(float(df['Close'].iloc[-1]), 2)
                open_price = round(float(df['Open'].iloc[0]), 2)
                change = round(current_price - open_price, 2)
                change_pct = round((change / open_price) * 100, 2)
            else:
                current_price, change, change_pct = 1000.0, 0.0, 0.0

            analytics = self.stats[symbol].update(current_price)

            tick_data = {
                "symbol": symbol,
                "price": current_price,
                "change": change,
                "change_pct": change_pct,
                "timestamp": int(time.time() * 1000),
                "analytics": analytics
            }
            self.last_known_ticks[symbol] = tick_data
            return tick_data

        except Exception:
            if symbol in self.last_known_ticks:
                return self.last_known_ticks[symbol]
            return {
                "symbol": symbol,
                "price": 0.0,
                "change": 0.0,
                "change_pct": 0.0,
                "timestamp": int(time.time() * 1000),
                "analytics": {"mean": 0.0, "std_dev": 0.0, "z_score": 0.0, "anomaly": False}
            }

engine = LiveMarketEngine()

class OllamaAnalysisRequest(BaseModel):
    model: str
    symbol: str
    price: float
    z_score: float
    rsi: float
    inserted_capital: float
    trade_amount: float

@app.get("/")
async def serve_index():
    if os.path.exists("index.html"):
        return FileResponse("index.html")
    return {"message": "Server running. Keep index.html in the same directory."}

@app.get("/api/stocks")
def get_stock_list():
    return NSE_STOCKS

@app.get("/api/history/{symbol}")
async def get_historical_candles(symbol: str, timeframe: str = "1d"):
    # Map timeframes to yfinance parameters
    tf_map = {
        "1d": ("1d", "5m"),
        "5d": ("5d", "15m"),
        "1m": ("1mo", "1d"),
        "3m": ("3mo", "1d")
    }
    period, interval = tf_map.get(timeframe, ("1d", "5m"))
    ticker_symbol = f"{symbol}.NS"

    try:
        loop = asyncio.get_event_loop()
        ticker = yf.Ticker(ticker_symbol)
        df = await loop.run_in_executor(None, lambda: ticker.history(period=period, interval=interval))

        candles = []
        if not df.empty:
            for idx, row in df.iterrows():
                candles.append({
                    "time": idx.strftime("%Y-%m-%d %H:%M"),
                    "close": round(float(row['Close']), 2),
                    "open": round(float(row['Open']), 2),
                    "high": round(float(row['High']), 2),
                    "low": round(float(row['Low']), 2),
                    "volume": int(row['Volume'])
                })
        return {"symbol": symbol, "timeframe": timeframe, "candles": candles}
    except Exception as e:
        return {"error": str(e), "candles": []}

@app.post("/api/analyze")
async def analyze_stock_signal(req: OllamaAnalysisRequest):
    prompt = f"""
    You are an automated algorithmic stock trading model.
    Analyze live market data for NSE symbol {req.symbol}:
    - Current Price: ₹{req.price}
    - Dynamic Streaming Z-Score: {req.z_score}
    - RSI (14): {req.rsi}
    - Total Portfolio Capital: ₹{req.inserted_capital}
    - Target Order Amount: ₹{req.trade_amount}

    Provide an execution decision. Respond STRICTLY in valid JSON without markdown:
    {{
        "symbol": "{req.symbol}",
        "action": "BUY" | "SELL" | "HOLD",
        "confidence": <float between 0.0 and 1.0>,
        "suggested_amount": <recommended order amount in INR>,
        "stop_loss": <target stop loss price in INR>,
        "take_profit": <target take profit price in INR>,
        "reasoning": "<technical rationale for decision>"
    }}
    """

    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            res = await client.post(
                f"{OLLAMA_HOST}/api/generate",
                json={
                    "model": req.model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json"
                }
            )
            if res.status_code == 200:
                raw_text = res.json().get("response", "{}")
                return json.loads(raw_text)
            return {"error": f"Ollama HTTP {res.status_code}", "action": "HOLD", "reasoning": "Model call failed"}
    except Exception as e:
        return {"error": str(e), "action": "HOLD", "reasoning": "Ollama service timeout or unavailable."}

@app.websocket("/ws/market")
async def websocket_market(websocket: WebSocket):
    await websocket.accept()
    active_symbols = ["RELIANCE", "TCS", "HDFCBANK"]
    try:
        while True:
            try:
                msg = await asyncio.wait_for(websocket.receive_text(), timeout=0.1)
                data = json.loads(msg)
                if data.get("action") == "subscribe":
                    active_symbols = data.get("symbols", active_symbols)
            except asyncio.TimeoutError:
                pass

            for sym in active_symbols:
                tick = await engine.fetch_live_tick(sym)
                await websocket.send_json(tick)

            await asyncio.sleep(3.0)
    except WebSocketDisconnect:
        pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)