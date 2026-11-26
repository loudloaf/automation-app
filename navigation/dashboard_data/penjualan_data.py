# navigation/dashboard_data/penjualan_data.py
"""Lapisan data & analitik untuk Dashboard Penjualan: pembacaan file Orlan/Zeta, ringkasan KPI, deteksi hari kosong, forecast, dan insight."""
import numpy as np
import pandas as pd
import scripts.rangkuman_penjualan as rk
from .format_rp import fmt_rp
from .konstanta import HARI


def rp(x):
    """Rupiah singkat: T (triliun), M (miliar), JT (juta), RB (ribu)."""
    return fmt_rp(x)


# ----------------------------------------------------------------------------- DATA
def muat_data(paths):
    """Baca file -> DataFrame bersih. Jika Supplier.xlsx ikut diupload, pakai pipeline laporan (angka sama persis)."""
    jenis = {p: rk.deteksi_file(p) for p in paths}
    sup = next((p for p, j in jenis.items() if j == "SUPPLIER"), None)
    master = rk.baca_supplier(sup) if sup else None
    frames = []
    for p, j in jenis.items():
        if j not in ("ORLAN", "ZETA"):
            continue
        d = rk.baca_orlan(p) if j == "ORLAN" else rk.baca_zeta(p)
        if master is not None:
            d, _, _ = rk.bersihkan(d, master)
            d = d[d["DipakaiLaporan"]]
        else:  # aturan inti yang sama dengan laporan, Principal = Grup Barang
            d = d.dropna(subset=["Tanggal"]).drop_duplicates()
            d = d[(d["Batal"] == 0) & (d["Net"] != 0)]
            d = d[~d["Gudang"].fillna("").astype(str).str.upper().str.contains("GRATIS|FREE")]
            d = d[d["Tanggal"].dt.to_period("M") == d["Tanggal"].dt.to_period("M").mode()[0]]
            d["Jenis"] = np.where((d["Qty"] < 0) | (d["Net"] < 0), "RETUR", "PENJUALAN")
            d["Principal"] = d["NamaGrup"].astype(str).str.replace(r"^\d+\s+", "", regex=True).str.strip()
        frames.append(
            d[["Sumber", "Cabang", "Tanggal", "NoFaktur", "KodeCust", "Customer", "Salesman", "Principal", "Jenis", "Net"]].astype(
                {"Sumber": "category", "Cabang": "category"}
            )
        )
    if not frames:
        raise ValueError("Tidak ada file Orlan/Zeta yang dikenali.")
    df = pd.concat(frames, ignore_index=True)
    df["Tanggal"] = df["Tanggal"].dt.normalize()
    return df


# ----------------------------------------------------------------------------- HARI NORMAL
def _ambang(seri, frac=0.10):
    """Batas omset harian 'normal'. Hari dengan omset di bawah 10% median hari berjualan dianggap data belum lengkap
    (mis. file penjualan periode itu belum diupload), bukan hari kerja sungguhan."""
    pos = seri[seri > 0]
    return float(frac * pos.median()) if len(pos) else 0.0


def hari_kosong(df, min_hari=3):
    """Daftar rentang hari kerja (Senin-Sabtu) berturut-turut dengan omset sangat kecil: [(awal, akhir, jumlah_hari), ...]."""
    harian = df.groupby("Tanggal")["Net"].sum()
    if harian.empty:
        return []
    full = harian.reindex(pd.date_range(harian.index.min(), harian.index.max()), fill_value=0)
    amb = _ambang(full)
    runs, start, last, n = [], None, None, 0
    for t, v in full.items():
        if t.dayofweek == 6:
            continue  # Minggu libur, tidak memutus rentang
        if v < amb:
            if start is None:
                start, n = t, 0
            last, n = t, n + 1
        else:
            if start is not None and n >= min_hari:
                runs.append((start, last, n))
            start = None
    if start is not None and n >= min_hari:
        runs.append((start, last, n))
    return runs


# ----------------------------------------------------------------------------- FORECAST
def _fit(seri, horizon):
    """Level (rata-rata ter-deseasonalisasi) x indeks hari-dalam-minggu."""
    s = seri[seri >= _ambang(seri)]  # hari dengan data tidak lengkap tidak ikut melatih model
    s = s[s > 0]
    idx = (s.groupby(s.index.dayofweek).mean() / s.mean()).reindex(range(7)).fillna(1.0)
    rec = s.iloc[-28:] if len(s) >= 56 else s  # riwayat pendek: pakai seluruh data agar lonjakan akhir bulan tidak terbawa
    level = (rec / idx.reindex(rec.index.dayofweek).values).mean()
    sd = (s / (level * idx.reindex(s.index.dayofweek).values)).std()
    tgl = pd.date_range(seri.index[-1] + pd.Timedelta(days=1), periods=horizon)
    yhat = np.array([level * idx[t.dayofweek] for t in tgl]) * (idx[tgl.dayofweek].values > 0)
    yhat[tgl.dayofweek == 6] = 0  # Minggu libur
    sd = 0.15 if np.isnan(sd) else sd
    return pd.DataFrame({"yhat": yhat, "lo": yhat * max(1 - 1.28 * sd, 0), "hi": yhat * (1 + 1.28 * sd)}, index=tgl), idx


def prakiraan(df, horizon=30):
    seri = df.groupby("Tanggal")["Net"].sum()
    seri = seri.reindex(pd.date_range(seri.index.min(), seri.index.max()), fill_value=0)
    n_normal = int((seri >= _ambang(seri)).sum())
    if n_normal < 10:
        return None
    fc, idx = _fit(seri, horizon)
    bt = None  # backtest: latih tanpa 7 hari terakhir, uji pada 7 hari itu
    if len(seri) >= 21:
        f7, _ = _fit(seri.iloc[:-7], 7)
        real = seri.iloc[-7:]
        bt = float(np.abs(real.values - f7["yhat"].values).sum() / max(real.sum(), 1))
    return {"fc": fc, "idx": idx, "wape": bt, "hist_days": n_normal}


# ----------------------------------------------------------------------------- RINGKASAN
def ringkas(df):
    jual = df.loc[df.Jenis == "PENJUALAN", "Net"].sum()
    retur = -df.loc[df.Jenis == "RETUR", "Net"].sum()
    harian = df.groupby("Tanggal")["Net"].sum()
    amb = _ambang(harian)
    h = harian[harian >= amb]  # hari kerja normal
    akhir = harian.index.max()
    skrg = harian[harian.index > akhir - pd.Timedelta(days=7)]
    lalu = harian[(harian.index > akhir - pd.Timedelta(days=14)) & (harian.index <= akhir - pd.Timedelta(days=7))]
    n_skrg, n_lalu = int((skrg >= amb).sum()), int((lalu >= amb).sum())
    d7, p7 = float(skrg.sum()), float(lalu.sum())
    valid = n_skrg >= 4 and n_lalu >= 4 and p7 > 0
    return dict(
        omset=df["Net"].sum(),
        faktur=df["NoFaktur"].nunique(),
        outlet=df["KodeCust"].nunique(),
        rata=h.mean() if len(h) else 0,
        hari=len(h),
        retur_pct=retur / jual * 100 if jual else 0,
        delta=(d7 / p7 - 1) * 100 if valid else None,
        d7=d7,
        p7=p7,
        n_skrg=n_skrg,
        n_lalu=n_lalu,
        kosong=hari_kosong(df),
        awal=df.Tanggal.min(),
        akhir=df.Tanggal.max(),
    )


def insight(df, k, fx):
    out, tot = [], df["Net"].sum()
    for a, b, n in k.get("kosong", []):
        out.append(
            f"<b>Data tidak lengkap:</b> {n} hari kerja ({a:%d %b} – {b:%d %b}) omsetnya sangat kecil (di bawah 10% median harian). "
            f"Dianggap file penjualan periode itu belum diupload, jadi tidak dipakai untuk rata-rata, perbandingan 7 hari, dan forecast."
        )
    c = df.groupby("Cabang", observed=True)["Net"].sum().sort_values(ascending=False)
    out.append(
        f"<b>{c.index[0]}</b> cabang terbesar: {rp(c.iloc[0])} ({c.iloc[0]/tot*100:.0f}% dari total). "
        f"3 cabang teratas menyumbang {c.iloc[:3].sum()/tot*100:.0f}%."
    )
    p = df.groupby("Principal")["Net"].sum().sort_values(ascending=False)
    out.append(f"Principal/grup teratas <b>{p.index[0]}</b> ({p.iloc[0]/tot*100:.0f}%); 5 teratas = {p.iloc[:5].sum()/tot*100:.0f}% omset.")
    cu = df.groupby("KodeCust")["Net"].sum().sort_values(ascending=False)
    out.append(f"Dari {len(cu):,} outlet, 10% outlet teratas menghasilkan <b>{cu.iloc[:max(len(cu)//10,1)].sum()/tot*100:.0f}%</b> omset.")
    hr = df.groupby(df.Tanggal.dt.dayofweek)["Net"].sum()
    hr = hr[hr.index < 6]
    if len(hr) > 1:
        out.append(f"Hari terkuat <b>{HARI[hr.idxmax()]}</b>, terlemah <b>{HARI[hr.idxmin()]}</b> (selisih {hr.max()/hr.min():.1f}x per total hari tsb).")
    rc = (
        df.assign(r=df.Net.where(df.Jenis == "RETUR", 0).abs(), j=df.Net.where(df.Jenis == "PENJUALAN", 0))
        .groupby("Cabang", observed=True)[["r", "j"]]
        .sum()
    )
    rc = (rc.r / rc.j.replace(0, np.nan) * 100).dropna().sort_values(ascending=False)
    if len(rc):
        out.append(f"Retur {k['retur_pct']:.2f}% dari penjualan; tertinggi di <b>{rc.index[0]}</b> ({rc.iloc[0]:.2f}%).")
    if k["delta"] is not None:
        out.append(
            f"7 hari terakhir {'naik' if k['delta'] >= 0 else 'turun'} <b>{abs(k['delta']):.1f}%</b> dibanding 7 hari sebelumnya "
            f"({rp(k['d7'])} vs {rp(k['p7'])})."
        )
    else:
        out.append("Perbandingan 7 hari terakhir vs sebelumnya tidak ditampilkan karena data salah satu periode belum lengkap.")
    if fx:
        s = fx["fc"]["yhat"].sum()
        w = f"; backtest 7 hari terakhir: error (WAPE) {fx['wape']*100:.0f}%" if fx["wape"] is not None else ""
        out.append(f"Proyeksi 30 hari ke depan <b>{rp(s)}</b> (kisaran {rp(fx['fc'].lo.sum())} – {rp(fx['fc'].hi.sum())}){w}.")
        if fx["hist_days"] < 56:
            out.append(
                f"<i>Catatan: riwayat baru {fx['hist_days']} hari kerja. Upload beberapa bulan agar tren musiman "
                f"(gajian, hari raya) ikut terbaca dan forecast lebih akurat.</i>"
            )
    return out