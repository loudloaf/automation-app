# navigation/dashboard_visual/doi.py
"""Visualisasi, antarmuka Streamlit, dan ekspor HTML untuk Dashboard DOI (Stok vs Omset)."""
import io, re, datetime as dt
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as _st

from navigation.dashboard_data.format_rp import fmt_rp, fmt_num, rp_ticks
from navigation.dashboard_data.doi_data import baca_laporan_doi, gabung, ringkas, kpi, bucket_doi, insight, BUCKETS, TOLERANSI_HARI
from .visual_common import (
    CSS, BG, CONFIG, PALET, C_LEBIH, C_KURANG, C_OK, C_MERAH, C_ABU,
    kartu, _tema, _layout, _pad_x_range, _kpi_grid, _html, _potong, _cd
)

STATUS_URUT = [
    "Kritis (hampir habis)",
    "Stok kosong",
    "Di bawah standar",
    "Sesuai standar",
    "Kelebihan stok",
    "Stok mati (tanpa penjualan)",
    "Stok minus (cek pencatatan)",
    "AMS minus (retur > penjualan)",
    "Tidak aktif",
]
WARNA_BUCKET = {
    "< 14": "#38bdf8",
    "14 - 30": "#34d399",
    "30 - 60": "#a3e635",
    "60 - 180": "#fbbf24",
    "180 - 365": "#fb923c",
    "> 365": "#ef4444",
    "Tanpa AMS": "#64748b",
}
_BLN = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]


@_st.cache_data(show_spinner="Membaca laporan DOI...")
def _muat(nama, data):
    return baca_laporan_doi(io.BytesIO(data), nama)


def _tgl_id(t):
    return f"{t.day:02d} {_BLN[t.month - 1]} {t.year}"


# ------------------------------------------------------------------ grafik
def fig_doi_std(rk):
    d = rk[rk["doi"].notna()].sort_values("doi")
    warna = [
        C_LEBIH if a > s + TOLERANSI_HARI else (C_KURANG if a < s - TOLERANSI_HARI else C_OK)
        for a, s in zip(d["doi"], d["std"])
    ]
    cd = _cd([d["std"], [fmt_rp(v) for v in d["saldo"]], [fmt_rp(v) for v in d["ams"]]])
    vmax = float(max(d["doi"].max(), d["std"].max())) if len(d) else 10.0
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            y=d["label"],
            x=d["doi"],
            orientation="h",
            marker=dict(color=warna),
            name="DOI",
            text=[f"{v:,.1f}" for v in d["doi"]],
            textposition="outside",
            cliponaxis=False,
            customdata=cd,
            hovertemplate="<b>%{y}</b><br>DOI %{x:,.1f} hari<br>Standar %{customdata[0]:,.0f} hari<br>Saldo stok %{customdata[1]}<br>AMS %{customdata[2]} / bln<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            y=d["label"],
            x=d["std"],
            mode="markers",
            name="Standar DOI",
            marker=dict(symbol="line-ns", size=24, line=dict(width=3, color="#ffffff")),
            hoverinfo="skip",
        )
    )
    fig.update_xaxes(title_text="Hari", range=[0, vmax * 1.22])
    return _layout(fig, max(340, 46 * len(d) + 100), legend=True, r=65)


def fig_lebih_kurang(rk):
    d = rk[rk["lebih_kurang"].notna()].sort_values("lebih_kurang")
    vmin = float(min(0, d["lebih_kurang"].min())) if len(d) else 0.0
    vmax = float(max(0, d["lebih_kurang"].max())) if len(d) else 0.0
    tv, tt = rp_ticks(vmin, vmax)
    fig = go.Figure(
        go.Bar(
            y=d["label"],
            x=d["lebih_kurang"],
            orientation="h",
            showlegend=False,
            marker=dict(color=[C_LEBIH if v > 0 else C_KURANG for v in d["lebih_kurang"]]),
            text=[fmt_rp(v, prefix="") for v in d["lebih_kurang"]],
            textposition="outside",
            cliponaxis=False,
            customdata=[fmt_rp(v) for v in d["lebih_kurang"]],
            hovertemplate="<b>%{y}</b><br>%{customdata}<extra></extra>",
        )
    )
    if tv:
        fig.update_xaxes(tickvals=tv, ticktext=tt)
    fig.update_xaxes(
        title_text="Kelebihan (+) / kekurangan (-) stok vs standar (Rp)",
        range=_pad_x_range(vmin, vmax, pad_left=0.25, pad_right=0.25),
    )
    return _layout(fig, max(340, 46 * len(d) + 100), legend=False, r=70)


def fig_porsi(rk):
    d = rk[rk["ams"] > 0].sort_values("porsi_ams", ascending=False)
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=d["label"],
            y=d["porsi_ams"],
            name="Porsi omset (AMS)",
            marker=dict(color="#a78bfa"),
            hovertemplate="<b>%{x}</b><br>Porsi omset %{y:,.1f}%<extra></extra>",
        )
    )
    fig.add_trace(
        go.Bar(
            x=d["label"],
            y=d["porsi_saldo"],
            name="Porsi nilai stok",
            marker=dict(color=C_LEBIH),
            hovertemplate="<b>%{x}</b><br>Porsi stok %{y:,.1f}%<extra></extra>",
        )
    )
    fig.update_layout(barmode="group")
    fig.update_xaxes(tickangle=-30)
    fig.update_yaxes(title_text="% dari total")
    return _layout(fig, 400, legend=True, b=80)


def fig_bucket(sku, col):
    b = bucket_doi(sku, col)
    urut = [x[0] for x in BUCKETS] + ["Tanpa AMS"]
    fig = go.Figure()
    for r in urut:
        x = b[b["rentang"] == r]
        if len(x):
            fig.add_trace(
                go.Bar(
                    x=x[col],
                    y=x["n"],
                    name=f"{r} hari" if r != "Tanpa AMS" else r,
                    marker=dict(color=WARNA_BUCKET[r]),
                    hovertemplate="<b>%{x}</b><br>" + r + ": %{y:,} SKU<extra></extra>",
                )
            )
    fig.update_layout(barmode="stack")
    fig.update_xaxes(tickangle=-30)
    fig.update_yaxes(title_text="Jumlah SKU")
    return _layout(fig, 420, legend=True, t=75, b=80)


def fig_scatter(df, hk):
    d = df[(df["ams"] > 0) & (df["saldo"] > 0)]
    if d.empty:
        return None, len(df)
    fig = go.Figure()
    for i, (p, x) in enumerate(d.groupby("principal")):
        cd = _cd([
            x["nama"].map(_potong),
            [f"{v:,.1f}" if pd.notna(v) else "-" for v in x["doi"]],
            x["status"],
            [fmt_rp(v) for v in x["saldo"]],
            [fmt_rp(v) for v in x["ams"]],
        ])
        fig.add_trace(
            go.Scatter(
                x=x["ams"],
                y=x["saldo"],
                mode="markers",
                name=p,
                customdata=cd,
                marker=dict(size=7, opacity=0.75, color=PALET[i % len(PALET)]),
                hovertemplate="<b>%{customdata[0]}</b><br>DOI %{customdata[1]} hari | %{customdata[2]}<br>Omset %{customdata[4]} / bln<br>Stok %{customdata[3]}<extra>" + p + "</extra>",
            )
        )
    x0, x1 = d["ams"].min(), d["ams"].max()
    for hari in (7, 30, 90, 180):
        fig.add_trace(
            go.Scatter(
                x=[x0, x1],
                y=[x0 * hari / hk, x1 * hari / hk],
                mode="lines+text",
                showlegend=False,
                line=dict(dash="dash", width=1, color="#94a3b8"),
                text=["", f"DOI {hari} hari"],
                textposition="top left",
                hoverinfo="skip",
            )
        )
    lo = int(np.floor(np.log10(min(d["ams"].min(), d["saldo"].min()))))
    hi = int(np.ceil(np.log10(max(d["ams"].max(), d["saldo"].max()))))
    tv = [10 ** e for e in range(lo, hi + 1)]
    tt = [fmt_rp(v, prefix="", dec=0, trim=True) for v in tv]
    fig.update_xaxes(type="log", tickvals=tv, ticktext=tt, title_text="Omset per bulan (AMS), Rp")
    fig.update_yaxes(type="log", tickvals=tv, ticktext=tt, title_text="Nilai stok, Rp")
    return _layout(fig, 560, legend=True, t=75, r=40), len(df) - len(d)


def fig_top_lebih(df, n=15):
    d = df[df["lebih_kurang"] > 0].nlargest(n, "lebih_kurang").sort_values("lebih_kurang")
    if d.empty:
        return None
    vmax = float(d["lebih_kurang"].max())
    cd = _cd([d["nama"], [f"{v:,.1f}" for v in d["doi"]], [fmt_rp(v) for v in d["saldo"]], [fmt_rp(v) for v in d["ams"]], d["principal"]])
    fig = go.Figure(
        go.Bar(
            y=d["nama"].map(lambda t: _potong(t, 34)),
            x=d["lebih_kurang"],
            orientation="h",
            marker=dict(color=C_LEBIH),
            customdata=cd,
            text=[fmt_rp(v, prefix="") for v in d["lebih_kurang"]],
            textposition="outside",
            cliponaxis=False,
            hovertemplate="<b>%{customdata[0]}</b> (%{customdata[4]})<br>DOI %{customdata[1]} hari<br>Stok %{customdata[2]} | Omset %{customdata[3]} / bln<extra></extra>",
        )
    )
    tv, tt = rp_ticks(0, vmax)
    if tv:
        fig.update_xaxes(tickvals=tv, ticktext=tt)
    fig.update_xaxes(title_text="Kelebihan stok di atas standar (Rp)", range=[0, vmax * 1.25])
    return _layout(fig, max(360, 32 * len(d) + 90), legend=False, r=70)


def fig_top_kritis(df, n=15):
    d = df[df["status"].isin(["Kritis (hampir habis)", "Stok kosong"])].nlargest(n, "ams").sort_values("ams")
    if d.empty:
        return None
    vmax = float(d["ams"].max())
    cd = _cd([d["nama"], [f"{v:,.1f}" for v in d["stok"]], d["sat"], [f"{v:,.1f}" if pd.notna(v) else "-" for v in d["doi"]], d["status"], d["principal"]])
    fig = go.Figure(
        go.Bar(
            y=d["nama"].map(lambda t: _potong(t, 34)),
            x=d["ams"],
            orientation="h",
            customdata=cd,
            marker=dict(color=[C_MERAH if s == "Stok kosong" else C_LEBIH for s in d["status"]]),
            text=[fmt_rp(v, prefix="") for v in d["ams"]],
            textposition="outside",
            cliponaxis=False,
            hovertemplate="<b>%{customdata[0]}</b> (%{customdata[5]})<br>%{customdata[4]}<br>Stok %{customdata[1]} %{customdata[2]} | DOI %{customdata[3]} hari<extra></extra>",
        )
    )
    tv, tt = rp_ticks(0, vmax)
    if tv:
        fig.update_xaxes(tickvals=tv, ticktext=tt)
    fig.update_xaxes(title_text="Omset per bulan yang terancam (Rp)", range=[0, vmax * 1.25])
    return _layout(fig, max(360, 32 * len(d) + 90), legend=False, r=70)


def fig_tren(b):
    if b.empty:
        return None
    tot = b.groupby("principal")["rp"].sum().sort_values(ascending=False)
    top = list(tot.index[:8])
    b = b.assign(grup=np.where(b["principal"].isin(top), b["principal"], "Lainnya"))
    g = b.groupby(["grup", "bulan", "bulan_urut"])["rp"].sum().reset_index().sort_values("bulan_urut")
    fig = go.Figure()
    for i, (p, x) in enumerate(g.groupby("grup")):
        fig.add_trace(
            go.Scatter(
                x=x["bulan"],
                y=x["rp"],
                mode="lines+markers",
                name=p,
                line=dict(color=PALET[i % len(PALET)], width=2),
                customdata=[fmt_rp(v) for v in x["rp"]],
                hovertemplate="<b>" + p + "</b><br>%{x}: %{customdata}<extra></extra>",
            )
        )
    tv, tt = rp_ticks(0, g["rp"].max())
    if tv:
        fig.update_yaxes(tickvals=tv, ticktext=tt)
    fig.update_yaxes(title_text="Omset per bulan, Rp")
    return _layout(fig, 430, legend=True, t=75, r=35)


def fig_gudang(gd):
    d = gd[gd["nilai"].abs() > 1].sort_values("nilai")
    if d.empty:
        return None
    vmin = float(min(0, d["nilai"].min()))
    vmax = float(max(0, d["nilai"].max()))
    warna = [C_MERAH if v < 0 else (C_ABU if not ok else "#a78bfa") for v, ok in zip(d["nilai"], d["dihitung"])]
    cd = _cd([[fmt_rp(v) for v in d["nilai"]], d["sku"], ["Ya" if x else "Tidak" for x in d["dihitung"]], d["keterangan"]])
    lab = [
        f"{g} {_potong(k, 22)}".strip() if k and not str(k).startswith("(") else str(g)
        for g, k in zip(d["gudang"], d["keterangan"])
    ]
    fig = go.Figure(
        go.Bar(
            y=lab,
            x=d["nilai"],
            orientation="h",
            marker=dict(color=warna),
            customdata=cd,
            text=[fmt_rp(v, prefix="") for v in d["nilai"]],
            textposition="outside",
            cliponaxis=False,
            hovertemplate="<b>%{y}</b><br>Nilai stok %{customdata[0]}<br>%{customdata[1]} SKU | dihitung: %{customdata[2]}<extra></extra>",
        )
    )
    tv, tt = rp_ticks(vmin, vmax)
    if tv:
        fig.update_xaxes(tickvals=tv, ticktext=tt)
    fig.update_xaxes(
        title_text="Nilai stok per gudang (Rp) · Merah = minus, Abu = tidak dihitung",
        range=_pad_x_range(vmin, vmax, pad_left=0.25, pad_right=0.25),
    )
    return _layout(fig, max(360, 34 * len(d) + 100), legend=False, r=70)


def html_dashboard_doi(kpi_1, kpi_2, ins, F, cab_list, tgl_txt):
    state = {"first": True}

    def g(key, kosong="Tidak ada data untuk grafik ini."):
        fig = F.get(key)
        if fig is None:
            return f"<p class='s' style='padding:14px 0'>{kosong}</p>"
        inc = "cdn" if state["first"] else False
        state["first"] = False
        return fig.to_html(full_html=False, include_plotlyjs=inc, config=CONFIG)

    cab_str = ", ".join(cab_list) if cab_list else "Semua Cabang"
    ins_html = "<ul class='ins'>" + "".join(f"<li>{_html(t)}</li>" for t in ins) + "</ul>"

    isi = [
        _kpi_grid(kpi_1),
        _kpi_grid(kpi_2),
        kartu("💡 Temuan otomatis", "Disusun dari data dan filter yang sedang dipilih.", ins_html),
        "<div style='display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px;margin-top:16px'>"
        + kartu("DOI vs standar", "Garis putih = standar. Oranye lebih dari standar, biru kurang, hijau sesuai.", g("doi_std"))
        + kartu("Kelebihan / kekurangan stok", "Selisih stok terhadap standar DOI, dalam Rupiah.", g("lebih_kurang"))
        + "</div>",
        "<div style='display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px;margin-top:16px'>"
        + kartu("Porsi omset vs porsi stok", "Perbandingan kontribusi omset (AMS) dengan nilai stok.", g("porsi"))
        + kartu("Sebaran SKU per rentang DOI", "Jumlah SKU per rentang hari.", g("bucket"))
        + "</div>",
        "<div style='margin-top:16px'>"
        + kartu("Peta SKU: omset vs nilai stok", "Tiap titik satu SKU. Di atas garis DOI 90 hari berarti stok terlalu banyak.", g("scatter"))
        + "</div>",
        "<div style='display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px;margin-top:16px'>"
        + kartu("15 SKU kelebihan stok terbesar", "Urut berdasarkan Rupiah di atas standar DOI.", g("top_lebih", "Tidak ada SKU kelebihan stok."))
        + kartu("15 SKU hampir habis dengan omset terbesar", "Merah = stok kosong, oranye = kritis.", g("top_kritis", "Tidak ada SKU hampir habis."))
        + "</div>",
        "<div style='display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px;margin-top:16px'>"
        + kartu("Tren omset per bulan", "Dari bulan-bulan yang dipakai menghitung AMS.", g("tren", "Data bulanan tidak tersedia."))
        + kartu("Nilai stok per gudang", "Nilai stok (stok x harga) per gudang.", g("gudang", "Tidak ada data gudang."))
        + "</div>",
    ]
    return (
        f"<!doctype html><html><head><meta charset='utf-8'><title>Dashboard DOI - {cab_str}</title>"
        f"<style>body{{margin:0;padding:28px;background:{BG};min-height:100vh}}{CSS}</style></head>"
        f"<body><div class='dash'><h2 style='margin:0 0 4px'>Dashboard DOI (Stok vs Omset)</h2>"
        f"<p style='color:#8A85A0;margin:0 0 12px'>Cabang: <b>{cab_str}</b> · Posisi stok: {tgl_txt} · "
        f"Dibuat {dt.datetime.now():%d %b %Y %H:%M}</p>" + "".join(isi) + "</div></body></html>"
    )


# ------------------------------------------------------------------ halaman
def render_dashboard_doi(st=None):
    if st is None:
        st = _st
    st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)
    st.markdown("<div class='ptitle'>Dashboard DOI <span class='chip'>Stok vs Omset</span></div>", unsafe_allow_html=True)

    d_ver = st.session_state.get("doi_dash_ver", 0)
    last = st.session_state.get("doi_last_excel")

    with st.container(border=True):
        u_head, u_clr = st.columns([3.2, 1], vertical_alignment="center")
        with u_head:
            st.markdown("**Upload File `Laporan_DOI_*.xlsx`** — Boleh upload beberapa cabang sekaligus untuk perbandingan")
        files = st.file_uploader(
            "Upload file Laporan_DOI_*.xlsx (hasil halaman Laporan DOI per Cabang). Boleh beberapa cabang sekaligus.",
            type=["xlsx"],
            accept_multiple_files=True,
            key=f"doi_dash_files_{d_ver}",
            label_visibility="collapsed",
        )
        pakai_last = False
        if last:
            default_use_last = (not files) and not st.session_state.get("doi_dash_cleared", False)
            pakai_last = st.checkbox(
                f"Pakai laporan terakhir dari halaman Laporan DOI ({last[0]})",
                value=default_use_last,
                key=f"doi_dash_last_{d_ver}",
            )
        with u_clr:
            if st.button(
                "🗑️ Bersihkan File",
                use_container_width=True,
                disabled=not (files or pakai_last),
                key="btn_clr_doi_dash",
            ):
                st.session_state["doi_dash_ver"] = d_ver + 1
                st.session_state["doi_dash_cleared"] = True
                st.rerun()

    sumber, seen = [], set()
    for f in (files or []):
        st.session_state.pop("doi_dash_cleared", None)
        sumber.append((f.name, f.getvalue()))
    if last and pakai_last:
        sumber.append(tuple(last))
    sumber = [s for s in sumber if not ((s[0], len(s[1])) in seen or seen.add((s[0], len(s[1]))))]
    if not sumber:
        st.info("ℹ️ Belum ada data. Jalankan **Laporan DOI per Cabang** lebih dulu atau upload file hasilnya di atas.")
        return

    hasil = []
    for nama, data in sumber:
        try:
            hasil.append(_muat(nama, data))
        except Exception as e:
            st.error(f"{nama}: {e}")
    if not hasil:
        return

    data = gabung([dict(h, param=dict(h["param"])) for h in hasil])
    sku_all, bln_all, gud_all, params = data["sku"], data["bulanan"], data["gudang"], data["param"]
    hk = float(np.mean([p["hari_kerja"] for p in params]))

    # ---- filter ----
    cab_opt = sorted(sku_all["cabang"].unique())
    prin_opt = sorted(sku_all["principal"].unique())
    st_opt = [s for s in STATUS_URUT if s in set(sku_all["status"])]

    c1, c2, c3 = st.columns([1, 1.5, 1.2])
    sel_cab = c1.multiselect("Cabang", cab_opt, default=cab_opt, key="doi_f_cab")
    sel_prin = c2.multiselect("Principal", prin_opt, default=prin_opt, key="doi_f_prin")
    sel_status = c3.multiselect("Status SKU (tab Peta SKU & Tabel)", st_opt, default=st_opt, key="doi_f_status")
    d1, d2 = st.columns([2, 1])
    cari = d1.text_input("Cari SKU atau kode (tab Peta SKU & Tabel)", key="doi_f_cari")
    per_cab = d2.toggle("Pisahkan per cabang", value=False, key="doi_f_percab") if len(cab_opt) > 1 else False

    f = sku_all[sku_all["cabang"].isin(sel_cab) & sku_all["principal"].isin(sel_prin)].copy()
    if f.empty:
        st.warning("Tidak ada data untuk filter ini.")
        return
    f["label"] = (f["cabang"] + " · " + f["principal"]) if per_cab else f["principal"]
    fs = f[f["status"].isin(sel_status)]
    if cari.strip():
        q = cari.strip().lower()
        fs = fs[fs["nama"].str.lower().str.contains(q, regex=False, na=False) | fs["kode"].str.lower().str.contains(q, regex=False, na=False)]
    bln = bln_all[bln_all["cabang"].isin(sel_cab) & bln_all["principal"].isin(sel_prin)]
    gud = gud_all[gud_all["cabang"].isin(sel_cab)]

    by = ["cabang", "principal"] if per_cab else ["principal"]
    rk = ringkas(f, hk, by=by)
    rk["label"] = (rk["cabang"] + " · " + rk["principal"]) if per_cab else rk["principal"]
    K = kpi(f, hk)
    std_w = float((f["std"] * f["ams"]).sum() / f["ams"].sum()) if f["ams"].sum() > 0 else np.nan
    tgl = sorted({p["tanggal"] for p in params if pd.notna(p["tanggal"])})
    tgl_txt = _tgl_id(tgl[-1]) if len(tgl) == 1 else "tanggal tiap laporan"
    n_set = {p["n_bulan"] for p in params}

    for p in params:
        for w in p["peringatan"]:
            st.warning(f"{p['cabang']}: {w}")

    # ---- KPI ----
    kpi_1 = [
        ("Nilai stok", fmt_rp(K["saldo"]), f"Nilai jual, per {tgl_txt}"),
        ("Omset per bulan (AMS)", fmt_rp(K["ams"]), f"Rata-rata {next(iter(n_set))} bulan" if len(n_set) == 1 else "Rata-rata omset bulanan"),
        ("DOI total", f"{K['doi']:,.1f} hari" if pd.notna(K["doi"]) else "-", f"Standar tertimbang {std_w:,.1f} hari" if pd.notna(std_w) else "&nbsp;"),
        ("SKU aktif", fmt_num(K["n_sku"]), f"{K['n_mati']:,} stok mati | {K['n_tanpa_harga']:,} tanpa harga"),
    ]
    kpi_2 = [
        ("Kelebihan stok", fmt_rp(K["kelebihan"]), "Di atas standar DOI"),
        ("Kekurangan stok", fmt_rp(K["kekurangan"]), "Di bawah standar DOI"),
        ("Hampir habis / kosong", fmt_num(K["n_kritis"] + K["n_kosong"]), f"Omset {fmt_rp(K['ams_kosong'])} / bln terancam"),
        ("Stok mati", fmt_num(K["n_mati"]), "Ada stok, tanpa penjualan di bulan data"),
    ]
    st.markdown(_kpi_grid(kpi_1), unsafe_allow_html=True)
    st.markdown(_kpi_grid(kpi_2), unsafe_allow_html=True)

    # ---- insight otomatis ----
    ins = insight(f, rk, bln, gud, hk)
    st.markdown(
        "<div class='dash'>"
        + kartu("💡 Temuan otomatis", "Disusun dari data dan filter yang sedang dipilih.", "<ul class='ins'>" + "".join(f"<li>{_html(t)}</li>" for t in ins) + "</ul>")
        + "</div>",
        unsafe_allow_html=True,
    )

    def kartu_chart(judul, sub, fig, key, kosong="Tidak ada data."):
        st.markdown(kartu(judul, sub, ""), unsafe_allow_html=True)
        if fig is None:
            st.info(kosong)
        else:
            st.plotly_chart(fig, use_container_width=True, config=CONFIG, key=key)

    F = {
        "doi_std": fig_doi_std(rk),
        "lebih_kurang": fig_lebih_kurang(rk),
        "porsi": fig_porsi(rk),
        "bucket": fig_bucket(f, "label"),
        "top_lebih": fig_top_lebih(fs),
        "top_kritis": fig_top_kritis(fs),
        "tren": fig_tren(bln),
        "gudang": fig_gudang(gud),
    }
    F["scatter"], n_out = (None, 0) if fs.empty else fig_scatter(fs, hk)

    tab1, tab2, tab3, tab4 = st.tabs(["Ringkasan principal", "Peta SKU", "Tren & gudang", "Tabel SKU"])
    with tab1:
        a, b = st.columns(2)
        with a:
            kartu_chart("DOI vs standar", "Garis putih = standar. Oranye lebih dari standar, biru kurang, hijau sesuai (toleransi 5 hari).", F["doi_std"], "doi_c1")
        with b:
            kartu_chart("Kelebihan / kekurangan stok", "Selisih stok terhadap standar DOI, dalam Rupiah.", F["lebih_kurang"], "doi_c2")
        a, b = st.columns(2)
        with a:
            kartu_chart("Porsi omset vs porsi stok", "Batang stok jauh di atas batang omset berarti stok tidak sebanding penjualan.", F["porsi"], "doi_c3")
        with b:
            kartu_chart("Sebaran SKU per rentang DOI", "Jumlah SKU per rentang hari. Tanpa AMS = tidak ada penjualan.", F["bucket"], "doi_c4")

    with tab2:
        kartu_chart(
            "Peta SKU: omset vs nilai stok",
            "Tiap titik satu SKU. Di atas garis DOI 90 hari berarti stoknya terlalu banyak. Klik legenda untuk menyembunyikan principal.",
            F["scatter"],
            "doi_c5",
            "Tidak ada SKU dengan omset dan stok sekaligus untuk filter ini.",
        )
        if F["scatter"] is not None and n_out:
            st.caption(f"{n_out:,} SKU tidak tampil di peta karena tidak punya omset atau nilai stok.")
        a, b = st.columns(2)
        with a:
            kartu_chart("15 SKU kelebihan stok terbesar", "Urut berdasarkan Rupiah di atas standar DOI.", F["top_lebih"], "doi_c6", "Tidak ada SKU kelebihan stok.")
        with b:
            kartu_chart(
                "15 SKU hampir habis dengan omset terbesar",
                "Merah = stok kosong, oranye = DOI kurang dari 25% standar (minimal 3 hari).",
                F["top_kritis"],
                "doi_c7",
                "Tidak ada SKU hampir habis.",
            )

    with tab3:
        kartu_chart("Tren omset per bulan", "Dari bulan-bulan yang dipakai menghitung AMS. Delapan principal terbesar, sisanya digabung.", F["tren"], "doi_c8", "Data bulanan tidak tersedia.")
        kartu_chart("Nilai stok per gudang", "Gudang bersaldo minus perlu dicek: bisa jadi hanya selisih pencatatan.", F["gudang"], "doi_c9", "Tidak ada data gudang.")

    with tab4:
        st.markdown(kartu("Tabel SKU", "Urutkan, saring dengan filter di atas, lalu unduh.", ""), unsafe_allow_html=True)
        u1, u2 = st.columns([2, 1])
        kolom = {"Nilai stok": "saldo", "Omset per bulan (AMS)": "ams", "DOI (hari)": "doi", "Lebih / kurang (Rp)": "lebih_kurang", "Nama": "nama"}
        urut = u1.selectbox("Urutkan berdasarkan", list(kolom), index=3, key="doi_t_urut")
        turun = u2.toggle("Terbesar dulu", value=True, key="doi_t_turun")
        t = fs.sort_values(kolom[urut], ascending=not turun, na_position="last")
        tampil = pd.DataFrame({
            "Cabang": t["cabang"],
            "Principal": t["principal"],
            "Kode": t["kode"],
            "Nama": t["nama"],
            "Stok": [f"{v:,.1f}" for v in t["stok"]],
            "Sat": t["sat"],
            "Nilai stok": [fmt_rp(v) for v in t["saldo"]],
            "AMS / bln": [fmt_rp(v) for v in t["ams"]],
            "DOI (hari)": [f"{v:,.1f}" if pd.notna(v) else "-" for v in t["doi"]],
            "Standar": [f"{v:,.0f}" for v in t["std"]],
            "Lebih / kurang": [fmt_rp(v) for v in t["lebih_kurang"]],
            "Status": t["status"],
        })
        st.dataframe(tampil.head(1000), use_container_width=True, hide_index=True)
        st.caption(f"{len(t):,} SKU" + (" (tabel menampilkan 1.000 teratas, unduhan memuat semuanya)" if len(t) > 1000 else ""))
        mentah = t[["cabang", "principal", "kode", "nama", "stok", "sat", "harga", "saldo", "ams", "doi", "std", "lebih_kurang", "status", "tanpa_harga"]]
        st.download_button("⬇️ Unduh CSV (angka penuh)", data=mentah.to_csv(index=False).encode("utf-8-sig"), file_name="sku_doi.csv", mime="text/csv", key="doi_t_dl")

    with st.expander("Cara membaca dashboard ini"):
        st.markdown(
            "- **AMS**: rata-rata omset bulanan dari bulan-bulan yang dipakai di laporan. **DOI** = nilai stok / (AMS / hari kerja), yaitu berapa hari stok cukup bila terjual secepat AMS.\n"
            "- **Nilai stok** = stok x harga jual rata-rata (bukan HPP). SKU yang tidak terjual di bulan data tidak punya harga, jadi nilainya terhitung Rp 0.\n"
            "- **Kelebihan / kekurangan** = (DOI - standar) x AMS / hari kerja.\n"
            "- **Hampir habis**: DOI kurang dari 25% standar (minimal 3 hari). **Stok mati**: tidak ada penjualan tetapi ada stok.\n"
            "- Angka dihitung ulang dari data di file Excel, jadi perubahan Ya/Tidak gudang atau standar DOI di sheet Parameter ikut terbawa."
        )

    cab_file = "_".join(sel_cab) if len(sel_cab) <= 3 else f"{len(sel_cab)}_Cabang"
    st.download_button(
        "⬇️ Unduh dashboard DOI (HTML interaktif)",
        data=html_dashboard_doi(kpi_1, kpi_2, ins, F, sel_cab, tgl_txt).encode("utf-8"),
        file_name=f"Dashboard_DOI_{re.sub(r'[^A-Za-z0-9]+', '_', cab_file)}_{dt.datetime.now():%Y%m%d}.html",
        mime="text/html",
        type="primary",
        key="doi_html_dl",
    )