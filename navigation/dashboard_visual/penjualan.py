# navigation/dashboard_visual/penjualan.py
"""Visualisasi, antarmuka Streamlit, dan ekspor HTML untuk Dashboard Penjualan."""
import os, tempfile, datetime as dt
import numpy as np
import pandas as pd
from scripts.excel_utils import pastikan_xlsx
from navigation.dashboard_data.format_rp import fmt_rp, rp_ticks
from .visual_common import UNGU, UNGU2, MERAH, HIJAU, HARI, CSS, BG, CONFIG, kartu, _tema
# Ubah dari: from .penjualan_data import ...
from navigation.dashboard_data.penjualan_data import rp, muat_data, _ambang, hari_kosong, _fit, prakiraan, ringkas, insight


# ----------------------------------------------------------------------------- GRAFIK
def _bar_h(go, serie, warna, h=360, label=None):
    """Bar horizontal berlabel Rupiah singkat (T/M/JT/RB) dengan ruang ekstra di kanan agar angka tidak terpotong."""
    lab = label if label is not None else [str(i) for i in serie.index]
    vmax = float(serie.max()) if len(serie) else 0.0
    f = go.Figure(
        go.Bar(
            x=serie.values,
            y=lab,
            orientation="h",
            marker_color=warna,
            text=[fmt_rp(v, prefix="", dec=1) for v in serie.values],
            textposition="outside",
            cliponaxis=False,
            customdata=[fmt_rp(v) for v in serie.values],
            hovertemplate="<b>%{y}</b>: %{customdata}<extra></extra>",
        )
    )
    f = _tema(f, h)
    tv, tt = rp_ticks(0, vmax)
    if tv:
        f.update_xaxes(tickvals=tv, ticktext=tt)
    if vmax > 0:
        f.update_xaxes(range=[0, vmax * 1.25])  # Ruang ekstra 25% di kanan agar teks angka tidak terpotong
    f.update_xaxes(title_text="Rp", automargin=True)
    f.update_yaxes(automargin=True)
    f.update_layout(margin=dict(l=20, r=65, t=25, b=45))
    return f


def figur(df, k, fx):
    import plotly.graph_objects as go
    F = {}
    h = df.pivot_table(index="Tanggal", columns="Sumber", values="Net", aggfunc="sum", observed=True).fillna(0)
    f = go.Figure()
    for i, col in enumerate(h.columns):
        f.add_bar(
            x=h.index,
            y=h[col],
            name=str(col),
            marker_color=[UNGU, UNGU2][i % 2],
            customdata=[fmt_rp(v) for v in h[col]],
            hovertemplate="%{x|%d %b}<br>%{customdata}<extra>" + str(col) + "</extra>",
        )
    total = h.sum(axis=1)
    f.add_scatter(
        x=h.index,
        y=total.rolling(7, min_periods=3).mean(),
        name="Rata-rata 7 hari",
        line=dict(color="#1F1B2E", width=2),
    )
    ymax = float(total.max()) if len(total) else 0.0
    if fx:
        fc = fx["fc"]
        f.add_scatter(
            x=list(fc.index) + list(fc.index[::-1]),
            y=list(fc.hi) + list(fc.lo[::-1]),
            fill="toself",
            fillcolor="rgba(239,90,60,.12)",
            line=dict(width=0),
            name="Kisaran 80%",
            hoverinfo="skip",
        )
        f.add_scatter(
            x=fc.index,
            y=fc.yhat,
            name="Forecast",
            line=dict(color=MERAH, width=2.5, dash="dot"),
            customdata=[fmt_rp(v) for v in fc.yhat],
            hovertemplate="%{x|%d %b}<br>%{customdata}<extra>Forecast</extra>",
        )
        ymax = max(ymax, float(fc.hi.max()))
    f.update_layout(barmode="stack", yaxis_title="Rp")
    F["tren"] = _tema(f, 400)
    tv, tt = rp_ticks(0, ymax)
    if tv:
        F["tren"].update_yaxes(tickvals=tv, ticktext=tt)

    c = df.groupby("Cabang", observed=True)["Net"].sum().sort_values()
    F["cabang"] = _bar_h(go, c, UNGU, h=max(360, 34 * len(c) + 80))

    p = df.groupby("Principal")["Net"].sum().sort_values().tail(10)
    F["principal"] = _bar_h(go, p, UNGU2, h=380)

    hh = df.groupby(["Tanggal"])["Net"].sum()
    hh = hh.groupby(hh.index.dayofweek).mean().reindex(range(6))
    F["hari"] = _tema(
        go.Figure(
            go.Bar(
                x=HARI[:6],
                y=hh,
                marker_color=[UNGU if v == hh.max() else UNGU2 for v in hh],
                customdata=[fmt_rp(v) for v in hh],
                hovertemplate="%{x}: rata-rata %{customdata} / hari<extra></extra>",
            )
        ),
        380,
    )
    tv, tt = rp_ticks(0, float(hh.max()))
    if tv:
        F["hari"].update_yaxes(tickvals=tv, ticktext=tt)
    F["hari"].update_yaxes(title_text="Rata-rata Rp / hari", automargin=True)

    cu = df.groupby(["KodeCust", "Customer"])["Net"].sum().sort_values(ascending=False)
    n = cu.head(10)[::-1]
    F["customer"] = _bar_h(
        go,
        pd.Series(n.values, index=[i[1] for i in n.index]),
        UNGU,
        400,
        label=[str(i[1])[:32] for i in n.index],
    )

    cum = cu.cumsum() / cu.sum() * 100
    F["pareto"] = _tema(
        go.Figure(
            go.Scatter(
                x=np.arange(1, len(cum) + 1) / len(cum) * 100,
                y=cum.values,
                fill="tozeroy",
                line=dict(color=UNGU),
                fillcolor="rgba(124,108,224,.18)",
                hovertemplate="%{x:.0f}% outlet = %{y:.0f}% omset<extra></extra>",
            )
        ),
        400,
    )
    F["pareto"].update_layout(xaxis_title="% outlet (terbesar → terkecil)", yaxis_title="% omset kumulatif")

    F["retur"] = _tema(
        go.Figure(
            go.Indicator(
                mode="gauge+number",
                value=k["retur_pct"],
                number=dict(suffix="%", valueformat=".2f"),
                gauge=dict(
                    axis=dict(range=[0, max(5, k["retur_pct"] * 2)]),
                    bar=dict(color=UNGU),
                    steps=[dict(range=[0, 2], color="#E6F6D7"), dict(range=[2, 5], color="#FDE9C9")],
                ),
            )
        ),
        260,
    )
    F["retur"].update_layout(margin=dict(l=35, r=35, t=35, b=25))
    return F


# ----------------------------------------------------------------------------- HTML
def kpi_html(k, fx):
    if k["delta"] is not None:
        dl = (
            f"<span class='badge' style='background:{HIJAU if k['delta']>=0 else MERAH}'>{k['delta']:+.1f}%</span> "
            f"<small>7 hari vs sebelumnya</small><br><small>{rp(k['d7'])} vs {rp(k['p7'])}</small>"
        )
    else:
        dl = "<small>7 hari vs sebelumnya: data pembanding belum lengkap</small>"
    kartu_ = [
        ("Omset bersih", rp(k["omset"]), dl),
        ("Faktur", f"{k['faktur']:,}", f"<small>{k['awal']:%d %b} – {k['akhir']:%d %b %Y}</small>"),
        ("Outlet aktif", f"{k['outlet']:,}", "<small>pelanggan unik bertransaksi</small>"),
        ("Rata-rata / hari kerja", rp(k["rata"]), f"<small>{k['hari']} hari kerja</small>"),
    ]
    return "<div class='dash-grid'>" + "".join(f"<div class='kpi'><small>{a}</small><b>{b}</b>{c}</div>" for a, b, c in kartu_) + "</div>"


def html_dashboard(df, k, fx, F, ins):
    g = lambda key, first=False: F[key].to_html(
        full_html=False, include_plotlyjs="cdn" if first else False, config=CONFIG
    )
    isi = [
        kpi_html(k, fx),
        "<div style='display:grid;grid-template-columns:minmax(0,2fr) minmax(0,1fr);gap:16px'>"
        + kartu("Tren omset harian & forecast", "Batang = omset per sumber, garis putus-putus = proyeksi 30 hari", g("tren", True))
        + kartu("Retur", "% retur terhadap penjualan", g("retur"))
        + "</div>",
        "<div style='display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px;margin-top:16px'>"
        + kartu("Omset per cabang", "Rp", g("cabang"))
        + kartu("Top 10 principal / grup", "Rp", g("principal"))
        + kartu("Pola per hari", "Rata-rata omset harian", g("hari"))
        + "</div>",
        "<div style='display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px;margin-top:16px'>"
        + kartu("Top 10 customer", "Rp", g("customer"))
        + kartu("Konsentrasi outlet (Pareto)", "Berapa outlet menopang omset", g("pareto"))
        + kartu("Insight otomatis", "Dibuat dari data yang diupload", "<ul class='ins'>" + "".join(f"<li>{i}</li>" for i in ins) + "</ul>")
        + "</div>",
    ]
    return (
        f"<!doctype html><html><head><meta charset='utf-8'><title>Dashboard Penjualan</title><style>body{{margin:0;padding:28px;"
        f"background:{BG};min-height:100vh}}{CSS}</style></head><body><div class='dash'><h2 style='margin:0 0 4px'>Dashboard Penjualan</h2>"
        f"<p style='color:#8A85A0;margin:0 0 12px'>Dibuat {dt.datetime.now():%d %b %Y %H:%M}</p>" + "".join(isi) + "</div></body></html>"
    )


def render_dashboard(st):
    st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)
    st.markdown("<div class='ptitle'>Dashboard Penjualan <span class='chip'>Insight & Forecast</span></div>", unsafe_allow_html=True)

    up_ver = st.session_state.get("dash_up_ver", 0)

    rk_state = st.session_state.get("rk_state")
    if rk_state and "HASIL" in rk_state and not st.session_state.get("dash_cleared"):
        if "dash_df" not in st.session_state:
            try:
                frames = []
                cols = ["Sumber", "Cabang", "Tanggal", "NoFaktur", "KodeCust", "Customer", "Salesman", "Principal", "Jenis", "Net"]
                for h in rk_state["HASIL"].values():
                    d = h["df"]
                    d = d[d["DipakaiLaporan"]].copy()
                    frames.append(d[cols].astype({"Sumber": "category", "Cabang": "category"}))
                if frames:
                    df_auto = pd.concat(frames, ignore_index=True)
                    df_auto["Tanggal"] = df_auto["Tanggal"].dt.normalize()
                    st.session_state["dash_df"] = df_auto
                    st.session_state["dash_source"] = "rangkuman"
            except Exception:
                pass

    with st.container(border=True):
        if st.session_state.get("dash_source") == "rangkuman":
            c_info, c_btn = st.columns([3, 1], vertical_alignment="center")
            c_info.success("✅ Menggunakan data penjualan & Supplier.xlsx dari menu **Rangkuman Penjualan**.")
            if c_btn.button("🗑️ Ganti / Reset Data", use_container_width=True, key="clr_dash_rk"):
                st.session_state["dash_up_ver"] = up_ver + 1
                st.session_state["dash_cleared"] = True
                for k in ("dash_df", "dash_key", "dash_source"):
                    st.session_state.pop(k, None)
                st.rerun()
            with st.expander("🔄 Ingin mengupload file penjualan lain secara manual?"):
                ups = st.file_uploader(
                    "Upload file penjualan Orlan/Zeta (.xlsx)",
                    type=["xlsx", "xls", "xlsm", "csv"],
                    accept_multiple_files=True,
                    key=f"dash_up_{up_ver}",
                )
        else:
            top_u1, top_u2 = st.columns([3.2, 1], vertical_alignment="center")
            with top_u1:
                st.markdown("**Upload File Penjualan (Orlan / Zeta)** — `Supplier.xlsx` opsional agar principal sesuai laporan")
            with top_u2:
                has_data = ("dash_df" in st.session_state) or bool(rk_state and "HASIL" in rk_state)
                if st.button("🗑️ Bersihkan File", use_container_width=True, disabled=not has_data, key="clr_dash_man"):
                    st.session_state["dash_up_ver"] = up_ver + 1
                    st.session_state["dash_cleared"] = True
                    for k in ("dash_df", "dash_key", "dash_source"):
                        st.session_state.pop(k, None)
                    st.rerun()

            ups = st.file_uploader(
                "Upload file penjualan Orlan/Zeta (.xlsx) — Supplier.xlsx opsional",
                type=["xlsx", "xls", "xlsm", "csv"],
                accept_multiple_files=True,
                key=f"dash_up_{up_ver}",
                label_visibility="collapsed",
            )
            if rk_state and "HASIL" in rk_state and st.session_state.get("dash_cleared"):
                if st.button("⚡ Gunakan kembali data dari Rangkuman Penjualan", key="restore_rk_data"):
                    st.session_state.pop("dash_cleared", None)
                    st.session_state.pop("dash_df", None)
                    st.rerun()

    if ups:
        kunci = tuple((u.name, u.size) for u in ups)
        if st.session_state.get("dash_key") != kunci:
            with st.spinner("Membaca & membersihkan data (file besar bisa 1-3 menit)..."):
                tmp = tempfile.mkdtemp()
                paths = []
                for u in ups:
                    p = os.path.join(tmp, u.name)
                    with open(p, "wb") as o:
                        o.write(u.getbuffer())
                    pastikan_xlsx(p)
                    paths.append(p)
                try:
                    st.session_state.update(dash_df=muat_data(paths), dash_key=kunci, dash_source="manual")
                except Exception as e:
                    st.error(f"Gagal membaca data: {e}")
                    return

    if "dash_df" not in st.session_state:
        st.info("⚠️ Belum ada data. Silakan jalankan script **Rangkuman Penjualan** terlebih dahulu atau upload file langsung di atas.")
        return

    df = st.session_state["dash_df"]
    c1, c2 = st.columns(2)
    cab = c1.multiselect("Cabang", sorted(df.Cabang.astype(str).unique()), default=sorted(df.Cabang.astype(str).unique()))
    src = c2.multiselect("Sumber", sorted(df.Sumber.astype(str).unique()), default=sorted(df.Sumber.astype(str).unique()))
    d = df[df.Cabang.astype(str).isin(cab) & df.Sumber.astype(str).isin(src)]
    if d.empty:
        st.warning("Tidak ada data untuk filter ini.")
        return
    k, fx = ringkas(d), prakiraan(d)
    for a, b, n in k["kosong"]:
        st.warning(
            f"Data tidak lengkap: {n} hari kerja ({a:%d %b} – {b:%d %b}) omsetnya sangat kecil. "
            f"Cek apakah file penjualan periode itu sudah diupload. Hari-hari ini tidak dipakai untuk rata-rata, perbandingan 7 hari, dan forecast."
        )
    try:
        F = figur(d, k, fx)
    except ImportError:
        st.error("Library plotly belum terpasang. Jalankan: pip install plotly")
        return
    ins = insight(d, k, fx)
    st.markdown(f"<div class='dash'>{kpi_html(k, fx)}</div>", unsafe_allow_html=True)
    a, b = st.columns([2, 1])
    with a:
        st.markdown(kartu("Tren omset harian & forecast", "Batang = omset per sumber · garis putus-putus = proyeksi 30 hari", ""), unsafe_allow_html=True)
        st.plotly_chart(F["tren"], use_container_width=True, config=CONFIG)
    with b:
        st.markdown(kartu("Retur", "% retur terhadap penjualan", ""), unsafe_allow_html=True)
        st.plotly_chart(F["retur"], use_container_width=True, config=CONFIG)
        if fx:
            st.metric("Proyeksi 30 hari", rp(fx["fc"].yhat.sum()), f"{rp(fx['fc'].lo.sum())} – {rp(fx['fc'].hi.sum())}", delta_color="off")
    for judul, keys in [
        ("Komposisi", [("cabang", "Omset per cabang"), ("principal", "Top 10 principal / grup"), ("hari", "Pola per hari")]),
        ("Pelanggan", [("customer", "Top 10 customer"), ("pareto", "Konsentrasi outlet (Pareto)")]),
    ]:
        cols = st.columns(len(keys))
        for col, (key, ttl) in zip(cols, keys):
            with col:
                st.markdown(f"<div class='dash'><h4 style='margin:6px 0'>{ttl}</h4></div>", unsafe_allow_html=True)
                st.plotly_chart(F[key], use_container_width=True, config=CONFIG)
    st.markdown("<div class='dash'>" + kartu("💡 Insight otomatis", "Dibuat dari data yang diupload", "<ul class='ins'>" + "".join(f"<li>{i}</li>" for i in ins) + "</ul>") + "</div>", unsafe_allow_html=True)
    st.download_button(
        "⬇️ Unduh dashboard (HTML interaktif)",
        html_dashboard(d, k, fx, F, ins).encode("utf-8"),
        file_name=f"Dashboard_Penjualan_{k['akhir']:%Y%m%d}.html",
        mime="text/html",
        type="primary",
    )