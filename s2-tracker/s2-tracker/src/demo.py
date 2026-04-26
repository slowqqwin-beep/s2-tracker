"""
离线 Demo
==========
不调 Claude API, 用预设的 mock 信号跑完整个 pipeline.
用来:
  1. 在没有 API key 时验证安装是否正确
  2. 调试评分算法和前端 JSON schema

跑法: python -m src.demo
"""
import json
from datetime import datetime
from pathlib import Path

from rich.console import Console

from src.analyzers.claude_analyzer import Signals
from src.analyzers.scorer import evaluate, to_frontend_dict
from src.pipeline import load_companies, print_summary

ROOT = Path(__file__).parent.parent
OUTPUT_PATH = ROOT / "data" / "processed" / "dashboard_data.json"

console = Console()


# 模拟数据 - 来自 8 家公司公开财报披露
MOCK_SIGNALS = {
    "PLTR": dict(
        ai_product_disclosed=True,
        ai_arr_growth_pct=75, total_revenue_growth_pct=36,
        nrr_pct=124, gross_margin_pct=80.2, gross_margin_yoy_delta_pp=-0.3,
        deployment_language="company-wide",
        key_quote_on_ai="AIP 驱动 US Commercial 收入加速 75% YoY",
        next_q_catalyst="US Commercial 增速持续性 + 国际客户突破",
        red_flags=[],
    ),
    "NOW": dict(
        ai_product_disclosed=True,
        ai_arr_growth_pct=150, total_revenue_growth_pct=21,
        nrr_pct=128, gross_margin_pct=79.5, gross_margin_yoy_delta_pp=0.4,
        deployment_language="company-wide",
        key_quote_on_ai="Now Assist 净新增 ACV 同比翻倍",
        next_q_catalyst="Agentic workflows 商业化进度",
        red_flags=[],
    ),
    "CRM": dict(
        ai_product_disclosed=True,
        ai_arr_growth_pct=120, total_revenue_growth_pct=9,
        nrr_pct=107, gross_margin_pct=76.8, gross_margin_yoy_delta_pp=-0.8,
        deployment_language="expanding",
        key_quote_on_ai="Agentforce 增长强劲但占总营收<2%",
        next_q_catalyst="Data Cloud + Agentforce 套餐打包",
        red_flags=["整体增速仍温吞", "AI 产品占比小"],
    ),
    "SNOW": dict(
        ai_product_disclosed=False,
        ai_arr_growth_pct=None, total_revenue_growth_pct=27,
        nrr_pct=126, gross_margin_pct=67.4, gross_margin_yoy_delta_pp=-1.5,
        deployment_language="expanding",
        key_quote_on_ai="Cortex 客户数高速增长",
        next_q_catalyst="是否首次单拆 Cortex 收入",
        red_flags=["AI 收入未单独披露", "毛利率被推理成本压制"],
    ),
    "DDOG": dict(
        ai_product_disclosed=False,
        ai_arr_growth_pct=None, total_revenue_growth_pct=25,
        nrr_pct=115, gross_margin_pct=81.2, gross_margin_yoy_delta_pp=0.6,
        deployment_language="expanding",
        key_quote_on_ai="AI 原生客户营收占比约 12%",
        next_q_catalyst="AI 原生客户 ARR 占比能否突破 15%",
        red_flags=["未单独披露 AI 产品 ARR"],
    ),
    "MDB": dict(
        ai_product_disclosed=False,
        ai_arr_growth_pct=None, total_revenue_growth_pct=17,
        nrr_pct=118, gross_margin_pct=73.1, gross_margin_yoy_delta_pp=-2.1,
        deployment_language="pilot",
        key_quote_on_ai="向量数据库故事性强但变现节奏慢",
        next_q_catalyst="AI 工作负载贡献是否进入披露口径",
        red_flags=["毛利率持续下滑", "AI 用例仍以 pilot 为主"],
    ),
    "GTLB": dict(
        ai_product_disclosed=True,
        ai_arr_growth_pct=60, total_revenue_growth_pct=30,
        nrr_pct=119, gross_margin_pct=89.6, gross_margin_yoy_delta_pp=0.2,
        deployment_language="expanding",
        key_quote_on_ai="Duo Pro/Enterprise 渗透稳健",
        next_q_catalyst="Duo 自主代理产品发布",
        red_flags=[],
    ),
    "CRWD": dict(
        ai_product_disclosed=False,
        ai_arr_growth_pct=None, total_revenue_growth_pct=23,
        nrr_pct=112, gross_margin_pct=78.0, gross_margin_yoy_delta_pp=-0.5,
        deployment_language="expanding",
        key_quote_on_ai="Charlotte AI 嵌入 Falcon 平台",
        next_q_catalyst="NG-SIEM 业务 ARR 验证 AI 安全场景",
        red_flags=["AI 产品未单独披露收入"],
    ),
}


def main():
    console.print("[bold]🧪 Offline Demo Mode[/] - 不调用 Claude API\n")
    companies = load_companies()
    results = []

    for c in companies:
        ticker = c["ticker"]
        if ticker not in MOCK_SIGNALS:
            continue
        mock = MOCK_SIGNALS[ticker]
        signals = Signals(ticker=ticker, period="Q1 2026", evidence={}, **mock)
        ev = evaluate(signals)

        console.print(f"[cyan]{ticker}[/] · {c['name']}")
        for r in ev.reasoning:
            console.print(f"  [dim]{r}[/]")
        console.print()

        company_meta = {**c, "last_earnings": "2026-Q1"}
        results.append(to_frontend_dict(signals, ev, company_meta))

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    output = {
        "generated_at": datetime.now().isoformat(),
        "period": "Q1 2026",
        "mode": "demo",
        "companies": results,
    }
    OUTPUT_PATH.write_text(json.dumps(output, ensure_ascii=False, indent=2))
    console.print(f"[bold green]✓[/] Demo output written: {OUTPUT_PATH}\n")
    print_summary(results)


if __name__ == "__main__":
    main()
