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
    send_telegram(f"Direct test: {symbol}")
    return
       
@app.route("/webhook", methods=["POST"])
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    print("Incoming:", data)
    send_telegram(str(data))
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
