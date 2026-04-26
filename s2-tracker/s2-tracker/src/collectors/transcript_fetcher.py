"""
Earnings Call Transcript 获取器
=================================
支持三种来源:
  1. URL: 从公开网站抓取并提取正文 (Motley Fool / Seeking Alpha free / IR pages)
  2. 本地文件: data/transcripts/{ticker}_{period}.txt
  3. 直接传入文本

设计哲学:
- 不依赖任何收费 API
- 失败优雅降级, 提示用户手动粘贴
- 抓回的原始 HTML 落盘, 方便复盘
"""
import re
from pathlib import Path
from typing import Optional

import requests
from bs4 import BeautifulSoup

DATA_DIR = Path(__file__).parent.parent.parent / "data" / "transcripts"
DATA_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


def fetch_from_url(url: str) -> str:
    """
    从 URL 抓取 transcript 正文.
    对 Motley Fool / Seeking Alpha / 一般 IR 页面通用.
    """
    resp = requests.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    # 移除 noise
    for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
        tag.decompose()

    # 优先找 <article> 或主要内容容器
    candidates = (
        soup.find("article")
        or soup.find("div", class_=re.compile(r"(transcript|article|content|body)", re.I))
        or soup.find("main")
        or soup.body
    )
    text = candidates.get_text(separator="\n") if candidates else soup.get_text(separator="\n")

    # 清理多余空行
    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
    return "\n".join(lines)


def load_local(ticker: str, period: str) -> Optional[str]:
    """从 data/transcripts/{ticker}_{period}.txt 读取"""
    fname = f"{ticker.upper()}_{period.replace(' ', '_')}.txt"
    path = DATA_DIR / fname
    if path.exists():
        return path.read_text(encoding="utf-8")
    return None


def save_local(ticker: str, period: str, content: str) -> Path:
    """保存到本地, 方便重复使用"""
    fname = f"{ticker.upper()}_{period.replace(' ', '_')}.txt"
    path = DATA_DIR / fname
    path.write_text(content, encoding="utf-8")
    return path


def get_transcript(
    ticker: str,
    period: str,
    url: Optional[str] = None,
    text: Optional[str] = None,
    use_cache: bool = True,
) -> str:
    """
    统一入口. 优先级: text > cache > url
    """
    if text:
        save_local(ticker, period, text)
        return text

    if use_cache:
        cached = load_local(ticker, period)
        if cached:
            return cached

    if url:
        content = fetch_from_url(url)
        save_local(ticker, period, content)
        return content

    raise ValueError(
        f"找不到 {ticker} {period} 的 transcript. "
        f"请提供 url 或 text, 或把文件放到 data/transcripts/{ticker}_{period.replace(' ', '_')}.txt"
    )
