# navigation/dashboard_visual/visual_common.py
"""Komponen visual bersama (Shared): CSS, warna, tema Plotly, kartu UI, dan utilitas layout grafik."""
import re
from navigation.dashboard_data.konstanta import HARI

UNGU, UNGU2, MERAH, HIJAU = "#8B5CF6", "#C8B6FF", "#F43F5E", "#10B981"
PALET = ["#a78bfa", "#7c3aed", "#c4b5fd", "#34d399", "#38bdf8", "#f472b6", "#fbbf24", "#94a3b8", "#fb923c", "#60a5fa", "#e879f9", "#4ade80"]
C_LEBIH, C_KURANG, C_OK, C_MERAH, C_ABU = "#f59e0b", "#38bdf8", "#34d399", "#ef4444", "#64748b"
CONFIG = {"displaylogo": False, "responsive": True}

CSS = """
*{box-sizing:border-box}
.dash{font-family:'Plus Jakarta Sans',Inter,sans-serif;color:var(--text-primary,#14141F);width:100%}
.dash-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:18px;margin:10px 0 22px}
.kpi,.card{background:var(--bg-card,rgba(255,255,255,.78));backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px);
 border:1px solid var(--border-subtle,rgba(255,255,255,.9));border-radius:26px;
 box-shadow:var(--card-shadow,0 14px 36px -10px rgba(100,90,150,.09));padding:22px 24px;margin-bottom:8px;
 min-width:0;overflow:visible}
.kpi small{color:var(--text-secondary,#8E929F);font-size:13px;font-weight:500;display:block;word-wrap:break-word}
.kpi b{display:block;font-size:clamp(22px,2.2vw,30px);font-weight:700;letter-spacing:-0.03em;margin:8px 0 4px;
 color:var(--text-primary,#14141F);word-wrap:break-word}
.badge{font-size:12px;font-weight:700;color:#064E3B;background:#6EE7B7;border-radius:999px;padding:3px 10px;display:inline-block}
.card h4{margin:0 0 4px;font-size:17px;font-weight:700;letter-spacing:-0.015em;color:var(--text-primary,#14141F);word-wrap:break-word}
.card p.s{margin:0 0 12px;color:var(--text-secondary,#8E929F);font-size:13px;line-height:1.45;word-wrap:break-word}
.ins{margin:0;padding-left:18px;line-height:1.8;color:var(--text-primary,#3B3652);font-size:14px}
.js-plotly-plot,.plot-container,.svg-container{max-width:100% !important}
@media(max-width:1100px){.dash-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
"""
BG = "linear-gradient(135deg,#F4F1FA 0%,#FBE9EF 55%,#E3EEF5 100%)"


def kartu(judul, sub, isi):
    return f"<div class='card'><h4>{judul}</h4><p class='s'>{sub}</p>{isi}</div>"


def _kpi_grid(items):
    return (
        "<div class='dash'><div class='dash-grid'>"
        + "".join(f"<div class='kpi'><small>{a}</small><b>{b}</b><small>{c}</small></div>" for a, b, c in items)
        + "</div></div>"
    )


def _html(t):
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)


def _potong(t, n=40):
    t = str(t)
    return t if len(t) <= n else t[: n - 1] + "…"


def _cd(cols):
    return [list(r) for r in zip(*cols)]


def _pad_x_range(vmin, vmax, pad_left=0.22, pad_right=0.22):
    span = max(vmax - vmin, 1e-9)
    lo = vmin - span * pad_left if vmin < 0 else 0
    hi = vmax + span * pad_right if vmax > 0 else 0
    return [lo, hi]


def _tema(fig, h=360, dark=True):
    txt_col = "#94A3B8" if dark else "#64748B"
    grid_col = "rgba(255,255,255,0.06)" if dark else "rgba(124,108,224,0.10)"
    hover_bg = "#1B1E28" if dark else "#FFFFFF"
    hover_txt = "#F8FAFC" if dark else "#14141F"

    fig.update_layout(
        height=h,
        autosize=True,
        margin=dict(l=20, r=45, t=55, b=50, pad=4),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Plus Jakarta Sans, Inter, sans-serif", color=txt_col, size=12),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
            font=dict(color=txt_col, size=11),
        ),
        hoverlabel=dict(
            bgcolor=hover_bg,
            font=dict(color=hover_txt, family="Plus Jakarta Sans, sans-serif"),
            bordercolor="rgba(139,92,246,0.3)",
        ),
    )
    fig.update_xaxes(gridcolor=grid_col, zeroline=False, automargin=True, title_standoff=12)
    fig.update_yaxes(gridcolor=grid_col, zeroline=False, automargin=True, title_standoff=12)
    return fig


def _layout(fig, h=380, legend=True, l=25, r=60, t=55, b=55, dark=True):
    fig = _tema(fig, h, dark=dark)
    fig.update_layout(
        margin=dict(l=l, r=r, t=t if legend else 25, b=b, pad=4),
        showlegend=legend,
    )
    fig.update_xaxes(automargin=True, title_standoff=12)
    fig.update_yaxes(automargin=True, title_standoff=12)
    return fig