from flask import Flask, request
import os
import yfinance as yf
import pandas as pd
import requests
from ta.trend import EMAIndicator
from ta.momentum import RSIIndicator

app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = "-1002632083710"

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    print("SENDING:", msg)

    response = requests.post(url, data={
        "chat_id": CHAT_ID,
        "text": msg
    })

    print("STATUS:", response.status_code)
    print("BODY:", response.text)

def check_setup(symbol):
    try:
        time:sleep(2)
        df = yf.download(
            tickers=symbol + ".NS",
            interval="15m",
            period="5d",
            auto_adjust=False,
            progress=False
        )

        if df.empty:
            send_telegram(f"No data for {symbol}")
            return

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df["EMA9"] = EMAIndicator(df["Close"], 9).ema_indicator()
        df["EMA21"] = EMAIndicator(df["Close"], 21).ema_indicator()
        df["RSI"] = RSIIndicator(df["Close"], 14).rsi()

        df["VWAP"] = (
            (df["Volume"] * ((df["High"] + df["Low"] + df["Close"]) / 3)).cumsum()
            / df["Volume"].cumsum()
        )

        df["AvgVol"] = df["Volume"].rolling(20).mean()

        if len(df) < 3:
            send_telegram(f"Not enough candles for {symbol}")
            return

        first_15_high = df.iloc[:3]["High"].max()
        latest = df.iloc[-1]

        if (
            latest["Close"] > first_15_high
            and latest["EMA9"] > latest["VWAP"]
            and latest["RSI"] > 60
            and latest["Volume"] > (latest["AvgVol"] * 1.5)
        ):

            msg = f"""
🟢 VALID LONG SETUP

{symbol}

Entry: {round(latest['Close'],2)}
SL: {round(latest['EMA21'],2)}
RSI: {round(latest['RSI'],2)}
Volume: Strong
"""
        else:
            msg = f"🔴 {symbol} rejected"

        send_telegram(msg)

    except Exception as e:
        send_telegram(f"Error in {symbol}: {str(e)}")


@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json

    print("Incoming data:", data)
    send_telegram("Payload: " + str(data))

    symbol = data.get("stock") or data.get("stocks") or data.get("symbol")

    if symbol:
        send_telegram(f"Webhook hit: {symbol}")
    
    else:
        send_telegram("No symbol found in payload")

    return {"status": "ok"}


@app.route("/")
def home():
     return "NEW VERSION LIVE"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
