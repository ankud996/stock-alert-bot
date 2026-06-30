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
    print("CHECK_SETUP HIT:", symbol)

    df = yf.download(symbol + ".NS", period="1d", interval="5m")

    if df.empty:
        send_telegram(f"No data for {symbol}")
        return

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    # Indicators
    df["EMA9"] = EMAIndicator(df["Close"], 9).ema_indicator()
    df["EMA21"] = EMAIndicator(df["Close"], 21).ema_indicator()
    df["RSI"] = RSIIndicator(df["Close"], 14).rsi()

    # VWAP
    df["VWAP"] = (
        (df["Volume"] * ((df["High"] + df["Low"] + df["Close"]) / 3)).cumsum()
        / df["Volume"].cumsum()
    )

    # Average Volume
    df["AvgVol"] = df["Volume"].rolling(20).mean()

    latest = df.iloc[-1]

    # Volume difference %
    vol_diff = ((latest["Volume"] - latest["AvgVol"]) / latest["AvgVol"]) * 100

    # Resistance = last 10 candles high
    resistance = df["High"].tail(10).max()

    # Support = last 10 candles low
    support = df["Low"].tail(10).min()

    msg = f"""
🚨 {symbol}

💰 Price: {round(latest['Close'],2)}
📊 Volume: {round(latest['Volume']/100000,2)}L ({round(vol_diff,2)}% vs avg)
⚡ RSI: {round(latest['RSI'],2)}
📍 VWAP: {round(latest['VWAP'],2)}
📈 EMA9: {round(latest['EMA9'],2)}
📉 EMA21: {round(latest['EMA21'],2)}
🟢 Resistance: {round(resistance,2)}
🔴 Support: {round(support,2)}
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
