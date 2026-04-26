# S2 Tracker — 美股 AI 应用层 1→10 自动判定

财报事件驱动的量化信息系统后端，配合 `s2_dashboard.jsx` 前端使用。

## 它做什么

把 earnings call transcript → 喂给 Claude → 提取 4 维信号 → 自动评分 → 输出 JSON 给前端。

每只股票判定为 5 个阶段之一：
- `STILL_0_TO_1` 还在画饼（0–3 分）
- `ENTERING_1_TO_10` ⭐ 黄金窗口（4–6 分）
- `SCALING` 规模化中（7–8 分）
- `MATURE` α 走完（9–10 分）
- `FADING` 推理成本失控警告

## 快速开始

### 1. 安装

```bash
cd s2-tracker
pip install -r requirements.txt
cp .env.example .env
# 编辑 .env 填入 ANTHROPIC_API_KEY
```

API key 从 https://console.anthropic.com/settings/keys 获取。

### 2. 离线 demo（不需要 API key）

```bash
python -m src.demo
```

会用预设的真实数据跑完整个 pipeline，输出 `data/processed/dashboard_data.json`，
供前端 dashboard 消费。可以借此验证安装是否正确。

### 3. 跑真实数据

**单只股票，提供 transcript URL：**
```bash
python -m src.pipeline --ticker PLTR \
  --period "Q4 2025" \
  --url https://www.fool.com/earnings/call-transcripts/2026/02/03/palantir-pltr-q4-2025-earnings-call-transcript/
```

**单只股票，本地文件：**
把 transcript 文本存到 `data/transcripts/PLTR_Q4_2025.txt`，然后：
```bash
python -m src.pipeline --ticker PLTR --period "Q4 2025"
```

**全部 watchlist：**
```bash
python -m src.pipeline --period "Q1 2026"
```

**用 Opus（更准但慢且贵）：**
```bash
python -m src.pipeline --smart
```

## 4 维评分算法

| 维度 | 分值 | 阈值 |
|---|---|---|
| **AI ARR 增速倍数** | 0–3 | ≥2× 整体 → 3；≥1.3× → 2；接近 → 1；未单拆 → 0 |
| **NRR 净留存** | 0–3 | ≥125% → 3；≥115% → 2；≥105% → 1；<105% → 0 |
| **毛利率稳定性** | 0–2 | YoY +正 → 2；持平 ±1pp → 1；下滑 → 0 |
| **客户部署语言** | 0–2 | company-wide → 2；expanding → 1；pilot → 0 |

特殊规则：**毛利率 YoY 下滑超过 2pp** 直接触发 FADING 红牌（不管总分多高）。
理由：AI 软件最大的雷区是营收涨毛利跌——推理成本失控是 α 幻觉破灭的前奏。

## 文件结构

```
s2-tracker/
├── config/
│   └── companies.json           # watchlist (8 只 S2 股票, 可加)
├── src/
│   ├── analyzers/
│   │   ├── claude_analyzer.py   # ⭐ Claude 提取信号 (含 prompt)
│   │   └── scorer.py            # 4 维评分
│   ├── collectors/
│   │   ├── transcript_fetcher.py  # 抓 transcript (URL/本地)
│   │   └── financial_fetcher.py   # yfinance 交叉验证
│   ├── pipeline.py              # 主流程
│   └── demo.py                  # 离线 demo
└── data/
    ├── transcripts/             # transcript 缓存
    └── processed/
        └── dashboard_data.json  # ⭐ 前端消费的输出
```

## Claude API 使用

- **默认用 Haiku 4.5** (`CLAUDE_MODEL_CHEAP`) — 批量解析便宜快
- **复杂判断切 Opus 4.7** (`CLAUDE_MODEL_SMART`) — 用 `--smart` 触发

每只股票一次解析约消耗 8K input + 1K output tokens。Haiku 跑 8 只全 watchlist，
单次成本约 $0.05–0.10。

## Prompt 设计要点

`claude_analyzer.py` 里的 prompt 强制了三条防幻觉规则：

1. **保守原则**：未明确披露的指标返回 null，禁止估算
2. **证据要求**：每个数字字段必须配 transcript 原文 quote（在 `evidence` 字段）
3. **区分硬披露 vs 营销话术**：
   - "AIP grew 75% YoY" → 取数
   - "strong AI momentum" → null + red_flag
   - "expect AI to be 20% by 2026" → null + 写入 catalyst

## 接前端 Dashboard

输出的 `data/processed/dashboard_data.json` 与 `s2_dashboard.jsx` 里的 `companies`
数组结构一一对应。前端只要 fetch 这个 JSON 就能渲染。

部署模式：
- **本地测试**：把 JSON 直接 import 进前端组件
- **生产**：JSON 推到 S3/Vercel KV/Supabase，前端定时 fetch
- **GitHub Actions**：每周日跑一次 pipeline，commit JSON 到仓库

## 扩展方向

- **加自动财报日历推送**：用 yfinance 的 `earnings_dates` 提前 1 天提醒
- **加 transcript 实时抓取**：监听 Motley Fool RSS / Seeking Alpha
- **加跨季度对比**：把多季度 JSON 合并，画 score 趋势线
- **加更多 S2 公司**：编辑 `config/companies.json`

## 已知限制

- **NRR 和 AI ARR 必须从 transcript 拿**：财务 API 没这两个字段
- **transcript 抓取对 paywall 无效**：建议手动复制粘贴到本地文件
- **Claude API 不是确定性的**：同一份 transcript 跑两次结果可能略有差异
  （但用了证据 quote 约束后差异主要在 narrative 措辞，数字基本稳定）

## 不构成投资建议

这是一个信号提取工具，不是交易系统。所有数字仅基于公开披露，所有判定逻辑都是
启发式规则。任何投资决策风险自担。
