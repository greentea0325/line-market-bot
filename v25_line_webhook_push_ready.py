
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

import pandas as pd
import yfinance as yf
import os, json

signal_df = pd.read_csv("output/daily_signals.csv")
backtest_df = pd.read_csv("output/backtest_summary.csv")
backtest_df["Win"] = backtest_df["Return"] > 0
win_rate_df = backtest_df.groupby("Symbol")["Win"].mean().reset_index()
win_rate_df["WinRate(%)"] = (win_rate_df["Win"] * 100).round(2)
win_rate_df.drop(columns=["Win"], inplace=True)
merged_df = signal_df.merge(win_rate_df, on="Symbol", how="left")
all_symbols = merged_df["Symbol"].unique().tolist()

app = Flask(__name__)
line_bot_api = LineBotApi(os.environ["YOUR_CHANNEL_ACCESS_TOKEN"])
handler = WebhookHandler(os.environ["YOUR_CHANNEL_SECRET"])

@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers["X-Line-Signature"]
    body = request.get_data(as_text=True)
    try:
        uid = json.loads(body)["events"][0]["source"]["userId"]
        with open("subscribers.txt", "a") as f:
            f.write(uid + "\n")
    except:
        pass
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK"

def get_symbol_summary(symbol):
    row = merged_df[merged_df["Symbol"].str.upper() == symbol.upper()]
    if row.empty:
        return f"找不到代碼 {symbol.upper()} 的分析資料。\n可查詢股票：\n" + "、".join(all_symbols[:15]) + "..."
    r = row.iloc[0]
    return f"📊 {symbol.upper()}\n建議：{r['Signal']}（{r['Reason']}）\n收盤：{round(r['Close'], 2)}\n勝率：{r['WinRate(%)']}%"

def get_symbol_winrate(symbol):
    row = win_rate_df[win_rate_df["Symbol"].str.upper() == symbol.upper()]
    if row.empty:
        return f"查無回測資料：{symbol.upper()}\n可查詢：\n" + "、".join(all_symbols[:15]) + "..."
    r = row.iloc[0]
    return f"📈 {symbol.upper()} 回測勝率：{r['WinRate(%)']}%"

def get_top3():
    top3 = win_rate_df.sort_values("WinRate(%)", ascending=False).head(3)
    return "🏆 回測前三名：\n" + "\n".join([f"{i+1}. {r.Symbol} - {r['WinRate(%)']:.1f}%" for i, r in top3.iterrows()])

def get_market_summary():
    try:
        def get(symbol):
            info = yf.Ticker(symbol).info
            p = info.get("regularMarketPrice", None)
            c = info.get("regularMarketChangePercent", None)
            return f"{p:.2f}（{c:+.2f}%）" if p and c else "資料不足"
        spx = get("^GSPC")
        ixic = get("^IXIC")
        vix = get("^VIX")
        dxy = get("DX-Y.NYB")
        tnx = yf.Ticker("^TNX").info.get("regularMarketPrice", None)
        tnx_str = f"{tnx:.2f}%" if tnx else "資料不足"
        return f"📊 市場概況：\nS&P500：{spx}\nNASDAQ：{ixic}\nVIX：{vix}\nDXY：{dxy}\n10Y殖利率：{tnx_str}"
    except Exception as e:
        return f"❌ 市場資訊錯誤：{e}"

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    text = event.message.text.strip().lower()
    uid = event.source.user_id
    with open("subscribers.txt", "a") as f:
        f.write(uid + "\n")
    if text.startswith("查詢") or text.startswith("分析"):
        symbol = text.split(" ")[-1]
        reply = get_symbol_summary(symbol)
    elif text.startswith("勝率"):
        symbol = text.split(" ")[-1]
        reply = get_symbol_winrate(symbol)
    elif "推薦前" in text:
        reply = get_top3()
    elif any(x in text for x in ["市場", "today", "大盤"]):
        reply = get_market_summary()
    else:
        reply = "請輸入：市場、查詢 TSLA、勝率 AAPL、推薦前3名"
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
