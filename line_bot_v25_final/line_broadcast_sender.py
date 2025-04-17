
from linebot import LineBotApi
from linebot.models import TextSendMessage
import os, pandas as pd, yfinance as yf

def load_users():
    if not os.path.exists("subscribers.txt"): return []
    with open("subscribers.txt", "r") as f:
        return list(set([line.strip() for line in f if line.strip()]))

def get_market_summary():
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

def get_top3():
    df = pd.read_csv("output/backtest_summary.csv")
    df["Win"] = df["Return"] > 0
    win = df.groupby("Symbol")["Win"].mean().reset_index()
    win["WinRate(%)"] = (win["Win"] * 100).round(2)
    top3 = win.sort_values("WinRate(%)", ascending=False).head(3)
    return "🏆 回測前三名：\n" + "\n".join([f"{i+1}. {r.Symbol} - {r['WinRate(%)']:.1f}%" for i, r in top3.iterrows()])

if __name__ == "__main__":
    users = load_users()
    msg = get_market_summary() + "\n\n" + get_top3()
    line_bot_api = LineBotApi(os.environ["YOUR_CHANNEL_ACCESS_TOKEN"])
    for uid in users:
        try:
            line_bot_api.push_message(uid, TextSendMessage(text=msg))
            print("✅ sent to", uid)
        except Exception as e:
            print("❌", uid, e)
