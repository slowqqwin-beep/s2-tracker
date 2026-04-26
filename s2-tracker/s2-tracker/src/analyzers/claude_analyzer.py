"""
Claude 财报电话会解析器
==========================
把 earnings call transcript 喂给 Claude, 提取 4 维评分需要的结构化信号:
  1. AI 产品 ARR 增速 (vs 整体增速)
  2. NRR 净留存率
  3. 毛利率 + 同比变化
  4. 客户部署成熟度 (pilot / expanding / company-wide)

设计要点:
- 强制 JSON 输出, 失败重试
- 每个数字字段都要求 Claude 给出原文 evidence (防止幻觉)
- 用 Haiku 做批量, Opus 留给复杂场景
"""
import json
import os
from dataclasses import dataclass, asdict
from typing import Optional

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

CLIENT = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
MODEL_CHEAP = os.getenv("CLAUDE_MODEL_CHEAP", "claude-haiku-4-5-20251001")
MODEL_SMART = os.getenv("CLAUDE_MODEL_SMART", "claude-opus-4-7")


# ============================================================
# 提示词 - 这是整个系统最关键的工程
# ============================================================
SYSTEM_PROMPT = """You are a buy-side equity analyst specialized in US AI software stocks.

Your job: extract structured signals from an earnings call transcript that will feed
a "1→10 stage detector" for AI software companies.

CRITICAL RULES:
1. Be CONSERVATIVE. If a metric is not explicitly stated by management, return null.
   Do NOT estimate or infer.
2. For every numeric field, you MUST also provide the supporting quote from the
   transcript in the `evidence` object. No quote = null.
3. Distinguish between:
   - Hard disclosure ("AIP grew 75% YoY") → use the number
   - Marketing language ("strong AI momentum") → null, mention in red_flags
   - Forward-looking guidance ("expect AI to be 20% by 2026") → null, mention in catalysts
4. For deployment_language, classify the dominant tone across multiple customer mentions:
   - "pilot": words like "POC", "pilot", "evaluating", "testing", "exploring"
   - "expanding": words like "expanding", "rolling out", "increasing adoption"
   - "company-wide": words like "standardized", "company-wide", "all employees", "default"

Output ONLY valid JSON matching the schema. No prose before or after."""


EXTRACTION_SCHEMA = """
{
  "ai_product_disclosed": true|false,
  "ai_arr_growth_pct": <number or null, YoY % growth of AI-specific revenue/ARR>,
  "total_revenue_growth_pct": <number or null>,
  "nrr_pct": <number or null, Net Revenue Retention or Dollar-Based Net Retention>,
  "gross_margin_pct": <number or null, non-GAAP preferred>,
  "gross_margin_yoy_delta_pp": <number or null, YoY change in percentage points>,
  "deployment_language": "pilot"|"expanding"|"company-wide"|null,
  "key_quote_on_ai": "<single most important quote about AI traction, max 40 words>",
  "next_q_catalyst": "<what to watch next quarter based on guidance, max 30 words>",
  "red_flags": [<list of concerning observations, e.g. "refused to disclose AI revenue", "GM down 200bps">],
  "evidence": {
    "ai_arr": "<verbatim quote supporting ai_arr_growth_pct, or null>",
    "nrr": "<verbatim quote supporting nrr_pct, or null>",
    "gross_margin": "<verbatim quote supporting GM, or null>",
    "deployment": "<verbatim quote supporting deployment_language, or null>"
  }
}
"""


@dataclass
class Signals:
    """Claude 解析输出的标准结构"""
    ticker: str
    period: str
    ai_product_disclosed: bool = False
    ai_arr_growth_pct: Optional[float] = None
    total_revenue_growth_pct: Optional[float] = None
    nrr_pct: Optional[float] = None
    gross_margin_pct: Optional[float] = None
    gross_margin_yoy_delta_pp: Optional[float] = None
    deployment_language: Optional[str] = None
    key_quote_on_ai: str = ""
    next_q_catalyst: str = ""
    red_flags: list = None
    evidence: dict = None

    def __post_init__(self):
        if self.red_flags is None:
            self.red_flags = []
        if self.evidence is None:
            self.evidence = {}


def analyze_transcript(
    ticker: str,
    company_name: str,
    period: str,
    ai_product: str,
    ai_keywords: list,
    transcript: str,
    smart: bool = False,
) -> Signals:
    """
    解析一份 earnings call transcript, 返回 Signals.

    Args:
        ticker: 股票代码 (e.g. "PLTR")
        company_name: 公司名 (e.g. "Palantir")
        period: 报告期 (e.g. "Q1 2026")
        ai_product: AI 产品名 (e.g. "AIP")
        ai_keywords: 该公司 AI 相关关键词, 帮助 Claude 聚焦
        transcript: 全文文本
        smart: True 用 Opus, False 用 Haiku
    """
    model = MODEL_SMART if smart else MODEL_CHEAP

    user_msg = f"""TICKER: {ticker}
COMPANY: {company_name}
PERIOD: {period}
AI PRODUCT TO TRACK: {ai_product}
AI KEYWORDS: {', '.join(ai_keywords)}

When extracting AI-specific metrics, focus on data points related to the AI product
and keywords above. For NRR/gross margin, use company-wide figures.

TRANSCRIPT:
\"\"\"
{transcript}
\"\"\"

Output JSON matching this schema:
{EXTRACTION_SCHEMA}
"""

    response = CLIENT.messages.create(
        model=model,
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_msg}],
    )

    raw = response.content[0].text.strip()

    # 容错: 去掉可能的 markdown fence
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as e:
        # 一次重试 - 让 Claude 修复自己的 JSON
        retry = CLIENT.messages.create(
            model=model,
            max_tokens=2048,
            messages=[{
                "role": "user",
                "content": f"This JSON is malformed:\n{raw}\n\nReturn corrected JSON only.",
            }],
        )
        parsed = json.loads(retry.content[0].text.strip())

    return Signals(
        ticker=ticker,
        period=period,
        ai_product_disclosed=parsed.get("ai_product_disclosed", False),
        ai_arr_growth_pct=parsed.get("ai_arr_growth_pct"),
        total_revenue_growth_pct=parsed.get("total_revenue_growth_pct"),
        nrr_pct=parsed.get("nrr_pct"),
        gross_margin_pct=parsed.get("gross_margin_pct"),
        gross_margin_yoy_delta_pp=parsed.get("gross_margin_yoy_delta_pp"),
        deployment_language=parsed.get("deployment_language"),
        key_quote_on_ai=parsed.get("key_quote_on_ai", ""),
        next_q_catalyst=parsed.get("next_q_catalyst", ""),
        red_flags=parsed.get("red_flags", []),
        evidence=parsed.get("evidence", {}),
    )


def signals_to_dict(s: Signals) -> dict:
    return asdict(s)
