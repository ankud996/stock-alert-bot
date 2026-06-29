from flask import Flask, request
import os
import yfinance as yf
import pandas as pd
import requests
from ta.trend import EMAIndicator
from ta.momentum import RSIIndicator

app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = "1249990076"

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    response = requests.post(url, data={
        "chat_id": CHAT_ID,
        "text": msg
    })

    print("SENDING:", msg)
    print("STATUS:", response.status_code)
    print("BODY:", response.text)

  
def check_setup(symbol):
    symbol = symbol.strip().upper()
    symbol = symbol.replace("&", "%26")

    df = yf.download(
        f"{symbol}.NS",
        period="2d",
        interval="15m",
        auto_adjust=True,
        progress=False
    )

    if df.empty:
        send_telegram(f"No data for {symbol}")
        return

    # Indicators
    close = df["Close"].squeeze()

    df["EMA9"] = EMAIndicator(close, window=9).ema_indicator()
    df["EMA21"] = EMAIndicator(close, window=21).ema_indicator()
    df["RSI"] = RSIIndicator(close).rsi()

    # VWAP
    df["TP"] = (df["High"] + df["Low"] + df["Close"]) / 3
    volume = df["Volume"].squeeze()
    df["VWAP"] = (df["TP"] * volume).cumsum() / volume.cumsum()
    # Avg Volume
    df["AvgVol"] = df["Volume"].rolling(20).mean()

    latest = df.iloc[-2]

    # Today's first candle
    today_df = df[df.index.date == df.index[-1].date()]

    if today_df.empty:
        send_telegram(f"No intraday data for {symbol}")
        return

    first_candle_high = today_df.iloc[0]["High"]

    # Logic
    breakout = latest["Close"] > first_candle_high
    ema_above_vwap = latest["EMA9"] > latest["VWAP"]

    vol_percent = ((latest["Volume"] - latest["AvgVol"]) / latest["AvgVol"]) * 100

    msg = f"""
🚨 {symbol}

💰 Price: {round(latest['Close'],2)}

📊 Volume: {round(latest['Volume']/100000,2)}L
📉 Avg Vol: {round(latest['AvgVol']/100000,2)}L
📌 Vol vs Avg: {round(vol_percent,2)}%

⚡ RSI: {round(latest['RSI'],2)}

🔥 First 15m Breakout: {"YES ✅" if breakout else "NO ❌"}
📍 EMA9 > VWAP: {"YES ✅" if ema_above_vwap else "NO ❌"}

📊 VWAP: {round(latest['VWAP'],2)}
📈 EMA9: {round(latest['EMA9'],2)}
📉 EMA21: {round(latest['EMA21'],2)}

🟢 Resistance: {round(latest['High'],2)}
🔴 Support: {round(latest['Low'],2)}

🎯 Setup Valid: {"YES 🚀" if breakout and ema_above_vwap else "WAIT ⏳"}
"""
    send_telegram(msg)

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
