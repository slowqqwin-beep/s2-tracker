"""
主管道
=======
端到端流程:
  1. 从 config/companies.json 读取监控池
  2. 对每只股票:
     a. 获取 transcript (本地缓存 / URL / 用户粘贴)
     b. 调用 Claude API 提取信号
     c. 跑 4 维评分算法
     d. 拿 yfinance 数据交叉验证
  3. 输出 data/processed/dashboard_data.json (前端直接消费)

CLI 用法:
  python -m src.pipeline                      # 跑全部, 用本地缓存
  python -m src.pipeline --ticker PLTR        # 只跑 PLTR
  python -m src.pipeline --url URL --ticker X --period "Q1 2026"  # 抓 URL
  python -m src.pipeline --smart              # 用 Opus (慢但准)
"""
import argparse
import json
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.table import Table

from src.analyzers.claude_analyzer import analyze_transcript, signals_to_dict
from src.analyzers.scorer import evaluate, to_frontend_dict
from src.collectors.transcript_fetcher import get_transcript
from src.collectors.financial_fetcher import get_fundamentals

ROOT = Path(__file__).parent.parent
CONFIG_PATH = ROOT / "config" / "companies.json"
OUTPUT_PATH = ROOT / "data" / "processed" / "dashboard_data.json"
LOG_PATH = ROOT / "data" / "processed" / "run_log.json"

console = Console()


def load_companies() -> list[dict]:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))["companies"]


def process_one(
    company: dict,
    period: str = "Q1 2026",
    url: str = None,
    text: str = None,
    smart: bool = False,
) -> dict:
    """处理单只股票的完整流程"""
    ticker = company["ticker"]
    console.print(f"\n[bold cyan]▸ {ticker}[/] · {company['name']}")

    # 1. 取 transcript
    try:
        transcript = get_transcript(ticker, period, url=url, text=text)
        console.print(f"  [green]✓[/] transcript loaded ({len(transcript)} chars)")
    except ValueError as e:
        console.print(f"  [yellow]![/] {e}")
        return None

    # 2. Claude 解析
    console.print(f"  [dim]· calling Claude ({'Opus' if smart else 'Haiku'})...[/]")
    signals = analyze_transcript(
        ticker=ticker,
        company_name=company["name"],
        period=period,
        ai_product=company["ai_product"],
        ai_keywords=company["ai_keywords"],
        transcript=transcript,
        smart=smart,
    )
    console.print(
        f"  [green]✓[/] signals: AI={signals.ai_arr_growth_pct} "
        f"NRR={signals.nrr_pct} GM_delta={signals.gross_margin_yoy_delta_pp} "
        f"deploy={signals.deployment_language}"
    )

    # 3. 评分
    ev = evaluate(signals)
    console.print(f"  [bold]→ {ev.stage_label}[/]  ({ev.score}/10)")
    for r in ev.reasoning:
        console.print(f"    [dim]· {r}[/]")

    # 4. 交叉验证 (可选, 失败不阻塞)
    fund = {}
    try:
        fund = get_fundamentals(ticker)
    except Exception as e:
        console.print(f"  [yellow]·[/] yfinance skipped: {e}")

    company_meta = {
        **company,
        "last_earnings": fund.get("last_earnings", ""),
    }

    return to_frontend_dict(signals, ev, company_meta)


def run_all(period: str = "Q1 2026", smart: bool = False, only_ticker: str = None):
    """跑全部 watchlist"""
    companies = load_companies()
    if only_ticker:
        companies = [c for c in companies if c["ticker"] == only_ticker.upper()]
        if not companies:
            console.print(f"[red]✗ {only_ticker} not in watchlist[/]")
            return

    results = []
    for c in companies:
        result = process_one(c, period=period, smart=smart)
        if result:
            results.append(result)

    # 输出 JSON 给前端
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    output = {
        "generated_at": datetime.now().isoformat(),
        "period": period,
        "companies": results,
    }
    OUTPUT_PATH.write_text(json.dumps(output, ensure_ascii=False, indent=2))
    console.print(f"\n[bold green]✓[/] dashboard_data.json written ({len(results)} companies)")

    # 摘要表格
    print_summary(results)


def print_summary(results: list[dict]):
    """打印阶段分布摘要"""
    table = Table(title="\n判定结果汇总", show_header=True, header_style="bold")
    table.add_column("Ticker", style="cyan")
    table.add_column("Name", style="white")
    table.add_column("Score", justify="right")
    table.add_column("Stage", style="bold")
    table.add_column("Quote", style="dim", max_width=50)

    stage_color = {
        "ENTERING_1_TO_10": "green",
        "SCALING": "yellow",
        "STILL_0_TO_1": "white",
        "MATURE": "white",
        "FADING": "red",
    }
    # 按 score 降序
    for r in sorted(results, key=lambda x: -x["score"]):
        color = stage_color.get(r["stage"], "white")
        table.add_row(
            r["ticker"],
            r["name"],
            f"{r['score']}/10",
            f"[{color}]{r['stageLabel']}[/]",
            (r["narrative"] or "")[:80],
        )
    console.print(table)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", help="只跑指定 ticker (e.g. PLTR)")
    parser.add_argument("--period", default="Q1 2026", help="财报期 (e.g. 'Q1 2026')")
    parser.add_argument("--url", help="transcript URL (单只股票时使用)")
    parser.add_argument("--smart", action="store_true", help="使用 Opus 而不是 Haiku")
    args = parser.parse_args()

    if args.url and not args.ticker:
        console.print("[red]✗ --url 必须配合 --ticker 使用[/]")
        return

    if args.url:
        # 单只股票 + URL 模式
        companies = load_companies()
        match = [c for c in companies if c["ticker"] == args.ticker.upper()]
        if not match:
            console.print(f"[red]✗ {args.ticker} 不在监控池[/]")
            return
        result = process_one(match[0], period=args.period, url=args.url, smart=args.smart)
        if result:
            # 单只更新 - 合并到现有 JSON
            if OUTPUT_PATH.exists():
                existing = json.loads(OUTPUT_PATH.read_text())
                existing["companies"] = [
                    c for c in existing.get("companies", []) if c["ticker"] != args.ticker.upper()
                ]
                existing["companies"].append(result)
                existing["generated_at"] = datetime.now().isoformat()
                OUTPUT_PATH.write_text(json.dumps(existing, ensure_ascii=False, indent=2))
            else:
                OUTPUT_PATH.write_text(json.dumps({
                    "generated_at": datetime.now().isoformat(),
                    "period": args.period,
                    "companies": [result],
                }, ensure_ascii=False, indent=2))
            console.print(f"\n[bold green]✓[/] {args.ticker} updated in dashboard_data.json")
    else:
        run_all(period=args.period, smart=args.smart, only_ticker=args.ticker)


if __name__ == "__main__":
    main()
