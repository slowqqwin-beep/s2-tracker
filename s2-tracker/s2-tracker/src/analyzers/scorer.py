"""
1→10 阶段评分器
==================
把 Claude 解析出的信号映射到 4 个阶段:
  - STILL_0_TO_1     0-3分   还在画饼
  - ENTERING_1_TO_10 4-6分   黄金窗口 ⭐
  - SCALING_10_TO_100 7-8分  规模化中
  - MATURE           9-10分  α走完
  - FADING           任意维度异常下滑

与前端 dashboard 的算法完全一致, 保证 Python 跑出的 JSON 前端直接能用.
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class ScoreBreakdown:
    ai_growth: int
    nrr: int
    gross_margin: int
    deployment: int
    total: int


@dataclass
class Evaluation:
    score: int
    breakdown: ScoreBreakdown
    stage: str
    stage_label: str
    reasoning: list


def _score_ai_growth(ai_growth: Optional[float], total_growth: Optional[float]) -> tuple[int, str]:
    """AI ARR 增速倍数 (0-3 分)"""
    if ai_growth is None or ai_growth == 0:
        return 0, "AI 收入未单独披露 → 故事大于现实"
    if total_growth is None or total_growth == 0:
        return 1, f"AI 增长 {ai_growth}% (无整体增速对比)"
    ratio = ai_growth / total_growth
    if ratio >= 2.0:
        return 3, f"AI 增速 {ai_growth}% 是整体 {total_growth}% 的 {ratio:.1f}x → 强信号"
    if ratio >= 1.3:
        return 2, f"AI 增速 {ai_growth}% > 整体 {total_growth}% → 健康"
    return 1, f"AI 增速 {ai_growth}% ≈ 整体 {total_growth}% → 平庸"


def _score_nrr(nrr: Optional[float]) -> tuple[int, str]:
    """NRR 净留存 (0-3 分)"""
    if nrr is None:
        return 0, "NRR 未披露"
    if nrr >= 125:
        return 3, f"NRR {nrr}% → 老客户大幅加买"
    if nrr >= 115:
        return 2, f"NRR {nrr}% → 健康扩张"
    if nrr >= 105:
        return 1, f"NRR {nrr}% → 勉强留存"
    return 0, f"NRR {nrr}% → 流失警告"


def _score_gross_margin(delta: Optional[float]) -> tuple[int, str]:
    """毛利率稳定性 (0-2 分)"""
    if delta is None:
        return 1, "毛利率变化未披露"
    if delta > 0:
        return 2, f"毛利率 YoY +{delta}pp → 规模效应"
    if delta >= -1:
        return 1, f"毛利率 YoY {delta}pp → 大致稳定"
    return 0, f"毛利率 YoY {delta}pp → 推理成本失控警告"


def _score_deployment(lang: Optional[str]) -> tuple[int, str]:
    """客户部署语言 (0-2 分)"""
    mapping = {
        "company-wide": (2, "客户全员部署 → 真实进入 1→10"),
        "expanding":    (1, "客户扩张中 → 验证早期"),
        "pilot":        (0, "仍是 POC/pilot → 还在 0→1"),
    }
    if lang is None:
        return 0, "无法识别部署阶段"
    return mapping.get(lang, (0, f"未知部署语言: {lang}"))


def evaluate(signals) -> Evaluation:
    """
    输入: Signals (来自 claude_analyzer)
    输出: Evaluation
    """
    reasoning = []

    ai_score, ai_reason = _score_ai_growth(
        signals.ai_arr_growth_pct, signals.total_revenue_growth_pct
    )
    reasoning.append(f"[AI增速] {ai_reason}")

    nrr_score, nrr_reason = _score_nrr(signals.nrr_pct)
    reasoning.append(f"[NRR] {nrr_reason}")

    gm_score, gm_reason = _score_gross_margin(signals.gross_margin_yoy_delta_pp)
    reasoning.append(f"[毛利率] {gm_reason}")

    dep_score, dep_reason = _score_deployment(signals.deployment_language)
    reasoning.append(f"[部署] {dep_reason}")

    breakdown = ScoreBreakdown(
        ai_growth=ai_score,
        nrr=nrr_score,
        gross_margin=gm_score,
        deployment=dep_score,
        total=ai_score + nrr_score + gm_score + dep_score,
    )

    # FADING 红牌优先 - 即使总分高, 毛利率大跌也直接降级
    if signals.gross_margin_yoy_delta_pp is not None and signals.gross_margin_yoy_delta_pp < -2:
        stage = "FADING"
        label = "⚠ FADING"
        reasoning.append("[判定] 毛利率下滑 >2pp, 触发 FADING 红牌")
    elif breakdown.total >= 9:
        stage, label = "MATURE", "MATURE"
    elif breakdown.total >= 7:
        stage, label = "SCALING", "SCALING 10→100"
    elif breakdown.total >= 4:
        stage, label = "ENTERING_1_TO_10", "ENTERING 1→10 ⭐"
    else:
        stage, label = "STILL_0_TO_1", "STILL 0→1"

    reasoning.append(f"[最终] 总分 {breakdown.total}/10 → {label}")

    return Evaluation(
        score=breakdown.total,
        breakdown=breakdown,
        stage=stage,
        stage_label=label,
        reasoning=reasoning,
    )


def to_frontend_dict(signals, evaluation, company_meta: dict) -> dict:
    """
    把 signals + evaluation 拼成前端 dashboard 期望的 JSON 结构.
    与 s2_dashboard.jsx 里的 companies 数组结构完全对齐.
    """
    return {
        "ticker": signals.ticker,
        "name": company_meta.get("name", ""),
        "category": company_meta.get("category", ""),
        "aiProduct": company_meta.get("ai_product", ""),
        "lastEarnings": company_meta.get("last_earnings", ""),
        "metrics": {
            "aiArrGrowth": signals.ai_arr_growth_pct or 0,
            "totalArrGrowth": signals.total_revenue_growth_pct or 0,
            "nrr": signals.nrr_pct or 0,
            "grossMargin": signals.gross_margin_pct or 0,
            "gmDeltaYoY": signals.gross_margin_yoy_delta_pp or 0,
            "deploymentLang": signals.deployment_language or "pilot",
        },
        "narrative": signals.key_quote_on_ai,
        "catalyst": signals.next_q_catalyst,
        "redFlags": signals.red_flags,
        "evidence": signals.evidence,
        "score": evaluation.score,
        "stage": evaluation.stage,
        "stageLabel": evaluation.stage_label,
        "reasoning": evaluation.reasoning,
    }
