
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

import pandas as pd
import yfinance as yf
import os

# 資料載入
signal_df = pd.read_csv("output/daily_signals.csv")
backtest_df = pd.read_csv("output/backtest_summary.csv")
backtest_df["Win"] = backtest_df["Return"] > 0
win_rate_df = backtest_df.groupby("Symbol")["Win"].mean().reset_index()
win_rate_df["WinRate(%)"] = (win_rate_df["Win"] * 100).round(2)
win_rate_df.drop(columns=["Win"], inplace=True)
merged_df = signal_df.merge(win_rate_df, on="Symbol", how="left")

# LINE Bot 初始化
app = Flask(__name__)
line_bot_api = LineBotApi(os.environ["YOUR_CHANNEL_ACCESS_TOKEN"])
handler = WebhookHandler(os.environ["YOUR_CHANNEL_SECRET"])

@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers["X-Line-Signature"]
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK"

def get_symbol_summary(symbol):
    row = merged_df[merged_df["Symbol"].str.upper() == symbol.upper()]
    if row.empty:
        return f"找不到代碼 {symbol} 的分析資料。"
    r = row.iloc[0]
    return (
        f"📊 個股分析：{symbol.upper()}\n"
        f"建議：{r['Signal']}（{r['Reason']}）\n"
        f"收盤價：{round(r['Close'], 2)}\n"
        f"回測勝率：{r['WinRate(%)']}%"
    )

def get_symbol_winrate(symbol):
    row = win_rate_df[win_rate_df["Symbol"].str.upper() == symbol.upper()]
    if row.empty:
        return f"找不到代碼 {symbol} 的回測資料。"
    r = row.iloc[0]
    return f"📈 {symbol.upper()} 回測勝率：{r['WinRate(%)']}%"

def get_top3():
    top3 = win_rate_df.sort_values("WinRate(%)", ascending=False).head(3)
    msg = "🏆 回測勝率前三名：\n"
    for i, row in enumerate(top3.itertuples(), start=1):
        msg += f"{i}. {row.Symbol} - 勝率 {row._2:.2f}%\n"
    return msg

def get_market_summary():
    try:
        def get(symbol):
            info = yf.Ticker(symbol).info
            price = info.get("regularMarketPrice", None)
            change = info.get("regularMarketChangePercent", None)
            if price is None or change is None:
                return "資料不足"
            return f"{price:.2f}（{change:+.2f}%）"
        spx = get("^GSPC")
        ixic = get("^IXIC")
        vix = get("^VIX")
        dxy = get("DX-Y.NYB")
        tnx = yf.Ticker("^TNX").info.get("regularMarketPrice", None)
        tnx_str = f"{tnx:.2f}%" if tnx else "資料不足"

        return (
            "📊 今日市場概況：\n"
            f"S&P500：{spx}\n"
            f"NASDAQ：{ixic}\n"
            f"VIX：{vix}\n"
            f"DXY 美元指數：{dxy}\n"
            f"10Y 殖利率：{tnx_str}"
        )
    except Exception as e:
        return f"❌ 市場資訊讀取失敗：{e}"

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    text = event.message.text.strip().lower()

    if text.startswith("查詢") or text.startswith("分析"):
        symbol = text.split(" ")[-1]
        reply = get_symbol_summary(symbol)
    elif text.startswith("勝率"):
        symbol = text.split(" ")[-1]
        reply = get_symbol_winrate(symbol)
    elif "推薦前" in text:
        reply = get_top3()
    elif any(t in text for t in ["市場", "today", "大盤"]):
        reply = get_market_summary()
    elif text in ["hi", "你好", "help", "指令"]:
        reply = "可用指令：\n市場 / today / 大盤\n查詢 TSLA\n勝率 AAPL\n推薦前3名"
    else:
        reply = "請輸入「市場」或「查詢 TSLA」等指令，取得市場或個股建議📈"

    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
