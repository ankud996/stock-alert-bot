from flask import Flask, request
import yfinance as yf
import pandas as pd
import requests
from ta.trend import EMAIndicator
from ta.momentum import RSIIndicator

app = Flask(__name__)

# Apna Telegram Bot Token aur Chat ID yahan daalo
BOT_TOKEN = "8971900274:AAGZVWOioaCkAJ3DuM_RAYT-MgoRxu9vavM"
CHAT_ID = "1249990076"


def send_telegram(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={
        "chat_id": CHAT_ID,
        "text": msg
    })


def check_setup(symbol):
    # NSE stock data (5 min)
    df = yf.download(symbol + ".NS", interval="5m", period="2d")

    # Indicators
    df['EMA9'] = EMAIndicator(df['Close'], 9).ema_indicator()
    df['EMA21'] = EMAIndicator(df['Close'], 21).ema_indicator()
    df['RSI'] = RSIIndicator(df['Close'], 14).rsi()

    # VWAP
    df['VWAP'] = (
        (df['Volume'] * ((df['High'] + df['Low'] + df['Close']) / 3)).cumsum()
        / df['Volume'].cumsum()
    )

    # Avg Volume
    df['AvgVol'] = df['Volume'].rolling(20).mean()

    # First 15 min high (first 3 candles of 5m)
    first_15_high = df.iloc[:3]['High'].max()

    latest = df.iloc[-1]

    # Setup conditions
    if (
        latest['Close'] > first_15_high and
        latest['EMA9'] > latest['VWAP'] and
        latest['RSI'] > 60 and
        latest['Volume'] > (latest['AvgVol'] * 1.5)
    ):
        msg = f"""🟢 VALID LONG SETUP

{symbol}

Entry: {round(latest['Close'],2)}
SL: {round(latest['EMA21'],2)}
RSI: {round(latest['RSI'],2)}
Volume: Strong
"""
    else:
        msg = f"🔴 {symbol} rejected"

    send_telegram(msg)


@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    symbol = data.get("stocks")

    if symbol:
        check_setup(symbol)

    return {"status": "ok"}

send_telegram(f"🚀 Scanner Triggered\nStock: {symbol}")
app.run(host="0.0.0.0", port=5000)
