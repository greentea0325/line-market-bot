
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import pandas as pd
import os, json

signal_df = pd.read_csv("output/daily_signals.csv")
backtest_df = pd.read_csv("output/backtest_summary.csv")

symbol_col = "Symbol" if "Symbol" in backtest_df.columns else "symbol"
backtest_df[symbol_col] = backtest_df[symbol_col].str.upper()
backtest_df["win"] = backtest_df["Return"] > 0
win_rate_df = backtest_df.groupby(symbol_col)["win"].mean().reset_index()
win_rate_df["win_rate"] = (win_rate_df["win"] * 100).round(2)
win_rate_df.drop(columns=["win"], inplace=True)

signal_df["Symbol"] = signal_df["Symbol"].str.upper()
merged_df = signal_df.merge(win_rate_df, left_on="Symbol", right_on=symbol_col, how="left")
all_symbols = merged_df["Symbol"].unique().tolist()

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
    raw_text = event.message.text
    text = raw_text.strip().upper()
    reply = ""
    if text in ["市場", "MARKET"]:
        reply = "📊 市場資訊功能啟用中（請整合 market.txt 或自定義）"
    elif text.startswith("查詢"):
        keyword = text.replace("查詢", "").strip().upper()
        reply = generate_stock_summary(keyword, raw_text)
    elif text.startswith("勝率"):
        keyword = text.replace("勝率", "").strip().upper()
        reply = generate_winrate_summary(keyword)
    elif "前三" in text:
        reply = generate_top3()
    else:
        reply = f"請輸入：\n查詢 AAPL\n勝率 TSLA\n推薦前三名\n市場\n你輸入的是：{raw_text}"
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))

def generate_stock_summary(symbol, raw):
    if symbol not in all_symbols:
        preview = "、".join(all_symbols[:10])
        return f"""❗ 查詢失敗
輸入文字：{raw}
轉換代碼：{symbol}
目前可查前10名：{preview}
"""
    row = merged_df[merged_df["Symbol"] == symbol].iloc[0]
    return f"""📊 {symbol} 分析：
技術評估：{row['Signal']}
回測勝率：{row['win_rate']}%
"""

def generate_winrate_summary(symbol):
    if symbol not in all_symbols:
        return f"查無勝率資料：{symbol}"
    row = merged_df[merged_df["Symbol"] == symbol].iloc[0]
    return f"{symbol} 勝率為 {row['win_rate']}%"

def generate_top3():
    top3 = win_rate_df.sort_values("win_rate", ascending=False).head(3)
    return "🏆 回測前三名：\n" + "\n".join([f"{i+1}. {r[symbol_col]} - {r['win_rate']:.1f}%" for i, r in top3.iterrows()])

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
