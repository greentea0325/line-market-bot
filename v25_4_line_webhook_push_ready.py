from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import pandas as pd
import os, json

signal_df = pd.read_csv("output/daily_signals.csv")
backtest_df = pd.read_csv("output/backtest_summary.csv")
backtest_df["win"] = backtest_df["Return"] > 0
win_rate_df = backtest_df.groupby("symbol")["win"].mean().reset_index()
win_rate_df["win_rate"] = (win_rate_df["win"] * 100).round(2)
win_rate_df.drop(columns=["win"], inplace=True)
merged_df = signal_df.merge(win_rate_df, on="symbol", how="left")
all_symbols = merged_df["symbol"].unique().tolist()

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

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    text = event.message.text.strip().upper()
    if text in ["市場", "MARKET"]:
        reply = generate_market_summary()
    elif text.startswith("查詢"):
        keyword = text.replace("查詢", "").strip()
        reply = generate_stock_summary(keyword)
    elif text.startswith("勝率"):
        keyword = text.replace("勝率", "").strip()
        reply = generate_winrate_summary(keyword)
    elif "前三" in text:
        reply = generate_top3()
    else:
        reply = "請輸入：\n查詢 AAPL\n勝率 TSLA\n推薦前三名\n市場"
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))

def generate_market_summary():
    try:
        with open("output/market.txt", "r", encoding="utf-8") as f:
            return f.read()
    except:
        return "找不到市場資訊"

def generate_top3():
    try:
        top3 = backtest_df.groupby("symbol")["Return"].mean().sort_values(ascending=False).head(3)
        lines = ["🏆 回測前三名："]
        for i, (symbol, win) in enumerate(top3.items()):
            lines.append(f"{i+1}. {symbol} - {win:.1f}%")
        return "\n".join(lines)
    except:
        return "找不到回測資料"

def generate_stock_summary(symbol):
    symbol = symbol.upper()
    if symbol not in all_symbols:
        return f"找不到代碼 {symbol} 的分析資料。\n可查詢股票：\n" + "、".join(all_symbols[:15]) + "..."
    row = merged_df[merged_df["symbol"] == symbol].iloc[0]
    return f"""📊 {symbol} 分析：
技術評估：{row['signal']}
回測勝率：{row['win_rate']}%
"""

def generate_winrate_summary(symbol):
    symbol = symbol.upper()
    if symbol not in all_symbols:
        return f"查無勝率資料 {symbol}。"
    row = merged_df[merged_df["symbol"] == symbol].iloc[0]
    return f"{symbol} 勝率為 {row['win_rate']}%"

if __name__ == "__main__":
    app.run()
