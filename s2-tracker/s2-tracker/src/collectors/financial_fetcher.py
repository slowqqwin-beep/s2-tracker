"""
财务数据抓取
==============
用 yfinance 拿基本面 (免费, 但延迟和准确度有限)
- 营收增速, 毛利率, 财报日期 等"硬"数字
- AI ARR 和 NRR 这些"软"指标必须从 transcript 拿

如果有 FMP / Polygon.io 的 API key, 可以替换这里的实现.
"""
from datetime import datetime
from typing import Optional

import yfinance as yf


def get_fundamentals(ticker: str) -> dict:
    """
    返回基础财务数据, 用于交叉验证 Claude 从 transcript 提取的数字.
    """
    t = yf.Ticker(ticker)
    info = t.info
    earnings_dates = t.earnings_dates

    # 取最近一次已发布的财报日期
    last_earnings = None
    if earnings_dates is not None and not earnings_dates.empty:
        past = earnings_dates[earnings_dates.index < datetime.now(earnings_dates.index.tz)]
        if not past.empty:
            last_earnings = past.index[0].strftime("%Y-%m-%d")

    return {
        "ticker": ticker,
        "name": info.get("longName", ""),
        "market_cap": info.get("marketCap"),
        "revenue_growth": (info.get("revenueGrowth") or 0) * 100,  # 转换为百分比
        "gross_margin": (info.get("grossMargins") or 0) * 100,
        "current_price": info.get("currentPrice"),
        "last_earnings": last_earnings,
    }


def get_upcoming_earnings(ticker: str) -> Optional[str]:
    """获取下次财报日期"""
    t = yf.Ticker(ticker)
    cal = t.calendar
    if cal and "Earnings Date" in cal:
        dates = cal["Earnings Date"]
        if dates and len(dates) > 0:
            return dates[0].strftime("%Y-%m-%d")
    return None
