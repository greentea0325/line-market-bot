
import yfinance as yf

def fetch_market_indicators_v22():
    try:
        def get_info(symbol):
            return yf.Ticker(symbol).info

        gspc = get_info("^GSPC")
        ixic = get_info("^IXIC")
        vix = get_info("^VIX")
        dxy = get_info("DX-Y.NYB")
        tnx = get_info("^TNX")

        def format_item(name, info, unit=""):
            price = info.get("regularMarketPrice", None)
            change = info.get("regularMarketChangePercent", None)
            if price is not None and change is not None:
                return f"{name}：{price:.2f}（{change:+.2f}％）{unit}"
            return f"{name}：資料不足"

        sp500 = format_item("S&P 500", gspc)
        nasdaq = format_item("NASDAQ", ixic)
        vix = format_item("VIX", vix)
        dxy = format_item("美元指數 DXY", dxy)

        tnx_val = tnx.get("regularMarketPrice", None)
        tnx_text = f"10Y 美債殖利率：{tnx_val:.2f}％" if tnx_val else "10Y 美債殖利率：資料不足"

        return sp500, nasdaq, vix, dxy, tnx_text
    except Exception as e:
        return [f"指標讀取錯誤：{e}"] * 5
