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

    response = requests.post(url, data={
        "chat_id": CHAT_ID,
        "text": msg
    })

    print("SENDING:", msg)
    print("STATUS:", response.status_code)
    print("BODY:", response.text)


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

        # Convert columns to single series
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

        # Today's data
        today_df = df[df.index.date == df.index[-1].date()]

        if today_df.empty:
            send_telegram(f"⚠ No intraday data for {symbol}")
            return

        first_candle_high = today_df.iloc[0]["High"]

        # Logic
        breakout = latest["Close"] > first_candle_high
        ema_above_vwap = latest["EMA9"] > latest["VWAP"]

        if latest["AvgVol"] == 0:
            vol_percent = 0
        else:
            vol_percent = ((latest["Volume"] - latest["AvgVol"]) / latest["AvgVol"]) * 100

        msg = f"""
🔥 Ankita Trade Setup 🔥
🚨 {symbol}

💰 Price: {round(float(latest['Close']), 2)}

📊 Volume: {round(float(latest['Volume']) / 100000, 2)}L
📉 Avg Vol: {round(float(latest['AvgVol']) / 100000, 2)}L
📌 Vol vs Avg: {round(float(vol_percent), 2)}%

⚡ RSI: {round(float(latest['RSI']), 2)}

🔥 First 15m Breakout: {"YES ✅" if breakout else "NO ❌"}
📍 EMA9 > VWAP: {"YES ✅" if ema_above_vwap else "NO ❌"}

📊 VWAP: {round(float(latest['VWAP']), 2)}
📈 EMA9: {round(float(latest['EMA9']), 2)}
📉 EMA21: {round(float(latest['EMA21']), 2)}

🟢 Resistance: {round(float(latest['High']), 2)}
🔴 Support: {round(float(latest['Low']), 2)}

🎯 Setup Valid: {"YES 🚀" if breakout and ema_above_vwap else "WAIT ⏳"}
"""

        send_telegram(msg)

    except Exception as e:
        send_telegram(f"⚠ Error in {symbol}: {str(e)}")


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
