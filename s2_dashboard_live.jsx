import React, { useState, useMemo, useEffect } from "react";
import {
  Sparkles, AlertTriangle, Calendar, ChevronRight, Filter,
  Info, Layers, RefreshCw, Github, AlertCircle
} from "lucide-react";

// ========== 配置: 改成你的 GitHub 仓库 ==========
// 格式: https://raw.githubusercontent.com/<用户名>/<仓库名>/<分支>/<文件路径>
const DATA_URL = "https://raw.githubusercontent.com/YOUR_USERNAME/s2-tracker/main/data/processed/dashboard_data.json";

export default function S2Dashboard() {
  const [filter, setFilter] = useState("ALL");
  const [sortBy, setSortBy] = useState("score");
  const [selected, setSelected] = useState(null);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastFetch, setLastFetch] = useState(null);

  // ============ 远程加载数据 ============
  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(DATA_URL + "?t=" + Date.now()); // 防缓存
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = await res.json();
      setData(json);
      setLastFetch(new Date());
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, []);

  const companies = data?.companies || [];

  const filtered = useMemo(() => {
    let arr = companies;
    if (filter !== "ALL") arr = arr.filter(c => c.stage === filter);
    if (sortBy === "score") arr = [...arr].sort((a, b) => b.score - a.score);
    if (sortBy === "nrr") arr = [...arr].sort((a, b) => (b.metrics?.nrr || 0) - (a.metrics?.nrr || 0));
    if (sortBy === "ai") arr = [...arr].sort((a, b) => (b.metrics?.aiArrGrowth || 0) - (a.metrics?.aiArrGrowth || 0));
    return arr;
  }, [companies, filter, sortBy]);

  const stageStats = useMemo(() => {
    const stats = { ENTERING_1_TO_10: 0, SCALING: 0, STILL_0_TO_1: 0, FADING: 0, MATURE: 0 };
    companies.forEach(c => { if (stats[c.stage] !== undefined) stats[c.stage]++; });
    return stats;
  }, [companies]);

  return (
    <div className="min-h-screen bg-[#05070d] text-stone-50 antialiased relative overflow-hidden font-body">
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,300;9..144,400;9..144,500;9..144,600;9..144,700&family=Geist:wght@300;400;500;600;700&family=JetBrains+Mono:wght@300;400;500;600;700&display=swap');
        .font-display { font-family: 'Fraunces', serif; font-optical-sizing: auto; letter-spacing: -0.02em; }
        .font-body    { font-family: 'Geist', sans-serif; }
        .font-mono    { font-family: 'JetBrains Mono', monospace; }
        .digit { font-feature-settings: "tnum"; font-variant-numeric: tabular-nums; }
        .grain::before {
          content: ""; position: absolute; inset: 0; pointer-events: none;
          background-image: radial-gradient(rgba(212,165,116,0.05) 1px, transparent 1px);
          background-size: 28px 28px; opacity: 0.4;
        }
        .hover-lift { transition: all .25s ease; }
        .hover-lift:hover { transform: translateY(-2px); }
        .glow-emerald { box-shadow: 0 0 0 1px rgba(52,211,153,0.3), 0 0 30px -8px rgba(52,211,153,0.4); }
        .pulse-ring { animation: pulseRing 2s ease-in-out infinite; }
        @keyframes pulseRing { 0%,100% { opacity: 1; } 50% { opacity: 0.5; } }
        .spin { animation: spin 1s linear infinite; }
        @keyframes spin { to { transform: rotate(360deg); } }
      `}</style>

      <div className="grain absolute inset-0" />
      <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-amber-400/60 to-transparent" />

      <div className="relative max-w-[1400px] mx-auto px-8 py-8">

        {/* ─────────── 顶部 ─────────── */}
        <header className="flex items-center justify-between mb-10 pb-6 border-b border-stone-700">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 border border-amber-400/60 flex items-center justify-center bg-amber-500/10">
              <Sparkles className="w-5 h-5 text-amber-200" />
            </div>
            <div>
              <div className="font-display text-2xl text-stone-50 leading-none">S2 Tracker</div>
              <div className="text-[11px] tracking-[0.25em] text-stone-300 mt-1.5 uppercase font-medium">
                美股 AI 应用层 · 1 → 10 自动判定
              </div>
            </div>
          </div>
          <div className="flex items-center gap-5 text-xs">
            <div className="flex items-center gap-2">
              <span className={`w-1.5 h-1.5 rounded-full ${error ? "bg-rose-400" : "bg-emerald-400"} pulse-ring`} />
              <span className={`font-mono tracking-widest font-semibold ${error ? "text-rose-300" : "text-emerald-300"}`}>
                {error ? "ERROR" : loading ? "LOADING" : "LIVE"}
              </span>
            </div>
            {data?.generated_at && (
              <div className="font-mono text-stone-300">
                数据生成 {new Date(data.generated_at).toLocaleString("zh-CN")}
              </div>
            )}
            <button
              onClick={fetchData}
              disabled={loading}
              className="font-mono text-[11px] px-3 py-1.5 border border-stone-600 hover:border-amber-400/60 text-stone-200 hover:text-amber-200 flex items-center gap-1.5"
            >
              <RefreshCw className={`w-3 h-3 ${loading ? "spin" : ""}`} />
              刷新
            </button>
          </div>
        </header>

        {/* ─────────── 错误 / 加载状态 ─────────── */}
        {error && (
          <div className="mb-8 border border-rose-400/60 bg-rose-500/10 p-5 flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-rose-300 flex-shrink-0 mt-0.5" />
            <div>
              <div className="font-display text-lg text-rose-200 mb-1">数据加载失败</div>
              <div className="text-sm text-stone-200 mb-2">错误信息: <span className="font-mono">{error}</span></div>
              <div className="text-xs text-stone-300 leading-relaxed">
                请检查 <span className="font-mono text-amber-200">DATA_URL</span> 是否指向你的 GitHub 仓库.
                确认仓库为 public, 且 <span className="font-mono">data/processed/dashboard_data.json</span> 存在.
              </div>
            </div>
          </div>
        )}

        {loading && !data && (
          <div className="mb-8 border border-stone-700 bg-stone-900/40 p-8 text-center">
            <RefreshCw className="w-6 h-6 text-amber-200 spin mx-auto mb-3" />
            <div className="text-stone-200">从 GitHub 加载最新数据中...</div>
          </div>
        )}

        {/* ─────────── 阶段分布 ─────────── */}
        {data && (
        <section className="mb-8">
          <div className="flex items-center gap-2 mb-4">
            <Layers className="w-3.5 h-3.5 text-stone-200" />
            <span className="text-[11px] tracking-[0.25em] text-stone-200 uppercase font-medium">阶段分布 · Stage Distribution</span>
          </div>
          <div className="grid grid-cols-5 gap-3">
            <StageCard label="STILL 0→1"     chinese="还在画饼"     count={stageStats.STILL_0_TO_1}     color="stone"   desc="AI收入未单拆/无明显增量" />
            <StageCard label="ENTERING 1→10" chinese="黄金窗口 ⭐"  count={stageStats.ENTERING_1_TO_10} color="emerald" desc="AI产品开始独立兑现 · α集中区" highlight />
            <StageCard label="SCALING 10→100" chinese="规模化中"    count={stageStats.SCALING}          color="amber"   desc="已被定价 · 仍有结构性α" />
            <StageCard label="MATURE"        chinese="α走完"        count={stageStats.MATURE}           color="stone"   desc="AI叙事完全反映在估值" />
            <StageCard label="FADING"        chinese="警示信号"     count={stageStats.FADING}           color="rose"    desc="毛利率被推理成本吃掉" />
          </div>
        </section>
        )}

        {/* ─────────── 控制栏 ─────────── */}
        {data && (
        <section className="mb-6 flex items-center justify-between">
          <div className="flex items-center gap-2 flex-wrap">
            <Filter className="w-3.5 h-3.5 text-stone-300" />
            <span className="text-[11px] tracking-widest text-stone-300 uppercase mr-2">阶段</span>
            {["ALL", "ENTERING_1_TO_10", "SCALING", "STILL_0_TO_1", "FADING"].map(f => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`font-mono text-[11px] px-3 py-1.5 border transition-all ${
                  filter === f
                    ? "border-amber-400/70 bg-amber-500/15 text-amber-200"
                    : "border-stone-700 text-stone-300 hover:border-stone-500"
                }`}
              >
                {f === "ALL" ? "全部" : f}
              </button>
            ))}
          </div>
          <div className="flex items-center gap-2">
            <span className="text-[11px] tracking-widest text-stone-300 uppercase mr-1">排序</span>
            {[["score", "综合分"], ["nrr", "NRR"], ["ai", "AI增速"]].map(([k, v]) => (
              <button
                key={k}
                onClick={() => setSortBy(k)}
                className={`font-mono text-[11px] px-3 py-1.5 border transition-all ${
                  sortBy === k
                    ? "border-stone-300 bg-stone-700/50 text-stone-50"
                    : "border-stone-700 text-stone-300 hover:border-stone-500"
                }`}
              >
                {v}
              </button>
            ))}
          </div>
        </section>
        )}

        {/* ─────────── 公司矩阵 ─────────── */}
        {data && (
        <section className="mb-10">
          <div className="grid grid-cols-2 gap-4">
            {filtered.map(c => (
              <CompanyCard
                key={c.ticker}
                company={c}
                onSelect={() => setSelected(c.ticker === selected ? null : c.ticker)}
                expanded={selected === c.ticker}
              />
            ))}
          </div>
          {filtered.length === 0 && (
            <div className="text-center text-stone-400 py-10">该阶段暂无标的</div>
          )}
        </section>
        )}

        {/* ─────────── 算法说明 ─────────── */}
        {data && (
        <section className="mb-10">
          <div className="flex items-center gap-2 mb-4">
            <Info className="w-3.5 h-3.5 text-stone-300" />
            <span className="text-[11px] tracking-[0.25em] text-stone-300 uppercase font-medium">算法说明 · Methodology</span>
          </div>
          <div className="border border-stone-700 bg-stone-900/40 p-6">
            <div className="grid grid-cols-4 gap-6">
              <MethodologyItem title="AI ARR 增速倍数" weight="0–3 分" desc="AI产品ARR增速 ÷ 整体ARR增速。≥2× 满分 · 未单独披露则 0 分。这是最硬指标 — 公司不愿单拆 = 故事大于现实。" />
              <MethodologyItem title="NRR 净留存"     weight="0–3 分" desc="老客户加买AI模块的最直接证据。≥125% 满分 · <105% 零分。比新客户增速更能说明 1→10 阶段。" />
              <MethodologyItem title="毛利率稳定性"   weight="0–2 分" desc="同比变化方向。AI软件最大雷区是营收涨毛利跌 — 推理成本失控会让α幻觉破灭。下滑>2pp 触发 FADING 红牌。" />
              <MethodologyItem title="客户部署语言"   weight="0–2 分" desc="解析 earnings call 描述。pilot=0 · expanding=1 · company-wide=2。从 POC 到全员部署是 1→10 的本质特征。" />
            </div>
          </div>
        </section>
        )}

        <footer className="pt-6 border-t border-stone-700 flex items-center justify-between text-[11px] text-stone-300">
          <div className="font-mono flex items-center gap-2">
            <Github className="w-3 h-3" />
            <span>auto-updated by GitHub Actions</span>
          </div>
          <div className="font-mono">DATA : 公司财报披露 · 不构成投资建议</div>
        </footer>
      </div>
    </div>
  );
}

/* ─────────── 子组件 ─────────── */

function StageCard({ label, chinese, count, color, desc, highlight }) {
  const colorMap = {
    stone:   "border-stone-600 text-stone-200",
    emerald: "border-emerald-400/60 text-emerald-200",
    amber:   "border-amber-400/60 text-amber-200",
    rose:    "border-rose-400/60 text-rose-200"
  };
  return (
    <div className={`border ${colorMap[color]} ${highlight ? "glow-emerald" : ""} bg-stone-900/40 p-4 hover-lift`}>
      <div className="font-mono text-[10px] tracking-widest font-bold mb-1">{label}</div>
      <div className="font-display italic text-sm text-stone-100 mb-3">{chinese}</div>
      <div className="font-display digit text-4xl text-stone-50 mb-2">{count}</div>
      <div className="text-[11px] text-stone-300 leading-snug">{desc}</div>
    </div>
  );
}

function CompanyCard({ company, onSelect, expanded }) {
  const c = company;
  const m = c.metrics || {};

  const stageStyle = {
    ENTERING_1_TO_10: "border-emerald-400/60 bg-emerald-500/10",
    SCALING:          "border-amber-400/60 bg-amber-500/10",
    STILL_0_TO_1:     "border-stone-600 bg-stone-800/30",
    MATURE:           "border-stone-500 bg-stone-700/30",
    FADING:           "border-rose-400/60 bg-rose-500/10"
  }[c.stage] || "border-stone-600 bg-stone-800/30";

  const stageBadgeStyle = {
    ENTERING_1_TO_10: "bg-emerald-500/20 text-emerald-200 border-emerald-400/60",
    SCALING:          "bg-amber-500/20 text-amber-200 border-amber-400/60",
    STILL_0_TO_1:     "bg-stone-700/50 text-stone-200 border-stone-500",
    MATURE:           "bg-stone-600/40 text-stone-200 border-stone-500",
    FADING:           "bg-rose-500/20 text-rose-200 border-rose-400/60"
  }[c.stage] || "bg-stone-700/50 text-stone-200 border-stone-500";

  return (
    <div className={`border ${stageStyle} hover-lift cursor-pointer`} onClick={onSelect}>
      <div className="p-5">
        <div className="flex items-start justify-between mb-3">
          <div>
            <div className="flex items-baseline gap-3 mb-1">
              <span className="font-mono text-xl text-stone-50 font-bold">{c.ticker}</span>
              <span className="font-display text-lg text-stone-100">{c.name}</span>
            </div>
            <div className="flex items-center gap-2 text-[11px]">
              <span className="text-stone-300 font-mono">{c.category}</span>
              <span className="text-stone-500">·</span>
              <span className="text-amber-200 font-mono">{c.aiProduct}</span>
            </div>
          </div>
          <span className={`font-mono text-[10px] tracking-widest px-2.5 py-1 border font-bold ${stageBadgeStyle}`}>
            {c.stageLabel}
          </span>
        </div>

        <div className="flex items-center gap-3 mb-4 pb-4 border-b border-stone-700/60">
          <div className="font-display digit text-4xl text-stone-50 leading-none">{c.score}</div>
          <div className="text-stone-400 font-display text-2xl">/</div>
          <div className="font-display digit text-2xl text-stone-300 leading-none">10</div>
          <div className="flex-1 ml-3"><ScoreBar score={c.score} stage={c.stage} /></div>
        </div>

        <div className="grid grid-cols-4 gap-2 mb-3">
          <MetricChip label="AI 增速" value={(m.aiArrGrowth === 0 || !m.aiArrGrowth) ? "未拆" : `${m.aiArrGrowth}%`} good={m.aiArrGrowth > 0} />
          <MetricChip label="NRR"     value={`${m.nrr || 0}%`} good={m.nrr >= 115} />
          <MetricChip label="毛利率"  value={`${(m.gmDeltaYoY || 0) > 0 ? "+" : ""}${m.gmDeltaYoY || 0}pp`} warn={m.gmDeltaYoY < -1} good={m.gmDeltaYoY > 0} />
          <MetricChip label="部署"    value={m.deploymentLang === "company-wide" ? "全员" : m.deploymentLang === "expanding" ? "扩张" : "试点"} good={m.deploymentLang === "company-wide"} />
        </div>

        <div className="text-[12px] text-stone-200 leading-relaxed mb-2">{c.narrative}</div>

        {expanded && (
          <div className="mt-4 pt-4 border-t border-stone-700/60 space-y-2">
            <div className="text-[11px]">
              <span className="font-mono text-amber-200 font-semibold">下季度 CATALYST · </span>
              <span className="text-stone-200">{c.catalyst}</span>
            </div>
            {c.redFlags && c.redFlags.length > 0 && (
              <div className="text-[11px]">
                <span className="font-mono text-rose-300 font-semibold">RED FLAGS · </span>
                <span className="text-stone-200">{c.redFlags.join(" · ")}</span>
              </div>
            )}
            {c.reasoning && (
              <div className="text-[10px] text-stone-400 font-mono space-y-0.5 mt-2 pt-2 border-t border-stone-800">
                {c.reasoning.map((r, i) => <div key={i}>{r}</div>)}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function ScoreBar({ score, stage }) {
  const colorMap = {
    ENTERING_1_TO_10: "bg-emerald-400",
    SCALING:          "bg-amber-400",
    STILL_0_TO_1:     "bg-stone-500",
    MATURE:           "bg-stone-400",
    FADING:           "bg-rose-400"
  };
  return (
    <div className="flex gap-0.5 h-2">
      {Array.from({ length: 10 }).map((_, i) => (
        <div key={i} className={`flex-1 ${i < score ? (colorMap[stage] || "bg-stone-500") : "bg-stone-700/60"}`} />
      ))}
    </div>
  );
}

function MetricChip({ label, value, warn, good }) {
  return (
    <div className="border border-stone-700 bg-stone-900/60 px-2 py-2">
      <div className="font-mono text-[10px] text-stone-300 mb-1 tracking-wider uppercase">{label}</div>
      <div className={`font-mono digit text-sm font-bold ${warn ? "text-rose-300" : good ? "text-emerald-300" : "text-stone-100"}`}>{value}</div>
    </div>
  );
}

function MethodologyItem({ title, weight, desc }) {
  return (
    <div>
      <div className="flex items-baseline justify-between mb-2">
        <span className="font-display text-base text-stone-50">{title}</span>
        <span className="font-mono text-[10px] text-amber-200 font-semibold">{weight}</span>
      </div>
      <p className="text-[12px] text-stone-300 leading-relaxed">{desc}</p>
    </div>
  );
}
