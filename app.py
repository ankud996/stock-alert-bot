from flask import Flask, request
import os
import yfinance as yf
import requests
from ta.trend import EMAIndicator
from ta.momentum import RSIIndicator

app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = "1249990076"


def send_telegram(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    requests.post(url, data={
        "chat_id": CHAT_ID,
        "text": msg
    })


def check_setup(symbol):
    symbol = symbol.strip().upper()

    try:
        df = yf.download(
            f"{symbol}.NS",
            period="2d",
            interval="15m",
            auto_adjust=True,
            progress=False
        )

        if df.empty:
            send_telegram(f"❌ No data for {symbol}")
            return

        # Single series
        close = df["Close"].squeeze()
        high = df["High"].squeeze()
        low = df["Low"].squeeze()
        volume = df["Volume"].squeeze()

        # Indicators
        df["EMA9"] = EMAIndicator(close, window=9).ema_indicator()
        df["EMA21"] = EMAIndicator(close, window=21).ema_indicator()
        df["RSI"] = RSIIndicator(close).rsi()

        # VWAP
        tp = (high + low + close) / 3
        df["VWAP"] = (tp * volume).cumsum() / volume.cumsum()

        # Avg Volume
        df["AvgVol"] = volume.rolling(20).mean()

        latest = df.iloc[-2]

        # Volume fix
        current_vol = float(latest["Volume"])
        avg_vol = float(latest["AvgVol"]) if latest["AvgVol"] > 0 else 0

        if avg_vol == 0:
            vol_percent = 0
        else:
            vol_percent = ((current_vol - avg_vol) / avg_vol) * 100

        msg = f"""
🚨 {symbol}

💰 Price: {round(float(latest['Close']), 2)}

📊 Volume: {round(current_vol / 100000, 2)}L
📉 Avg Vol: {round(avg_vol / 100000, 2)}L
📌 Vol vs Avg: {round(vol_percent, 2)}%

⚡ RSI: {round(float(latest['RSI']), 2)}

📍 VWAP: {round(float(latest['VWAP']), 2)}
📈 EMA9: {round(float(latest['EMA9']), 2)}
📉 EMA21: {round(float(latest['EMA21']), 2)}

🟢 Resistance: {round(float(latest['High']), 2)}
🔴 Support: {round(float(latest['Low']), 2)}
"""
        send_telegram(msg)

    except Exception as e:
        send_telegram(f"⚠️ Error in {symbol}: {str(e)}")


@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(force=True)

    stocks = data.get("stocks")

    if stocks:
        stock_list = [s.strip() for s in stocks.split(",")]

        for symbol in stock_list:
            check_setup(symbol)

    return {"status": "ok"}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
