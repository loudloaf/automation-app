# navigation/dashboard_data/doi_data.py
"""Lapisan data untuk Dashboard DOI.

Membaca file Excel hasil `doi_cabang.py` (satu atau banyak cabang). File dari aplikasi belum punya nilai rumus
tersimpan, jadi yang dibaca hanya sel INPUT (Parameter, Master SKU, Data Stok, daftar SKU di DOI SKU) lalu
DOI dihitung ulang dengan rumus yang sama seperti di Excel. Hasilnya tetap benar walau file belum pernah dibuka di Excel,
dan ikut berubah bila Ya/Tidak gudang atau standar DOI di sheet Parameter sudah diedit.
"""
import re
import numpy as np
import pandas as pd
from openpyxl import load_workbook
from .format_rp import fmt_rp

BUCKETS = [("< 14", 0, 14), ("14 - 30", 14, 30), ("30 - 60", 30, 60), ("60 - 180", 60, 180), ("180 - 365", 180, 365), ("> 365", 365, None)]
TOLERANSI_HARI = 5   # sama dengan kolom "No. Melebihi Standar" di Excel (DOI > standar + 5)


def _kode(x):
    if x is None or (isinstance(x, float) and np.isnan(x)): return ""
    x = str(x).strip()
    return x[:-2] if x.endswith(".0") else x


def _num(s):
    return pd.to_numeric(s, errors="coerce")


def baca_laporan_doi(src, nama_file=None):
    """src = path atau file-like (UploadedFile Streamlit). Return dict: sku, bulanan, gudang, param."""
    wb = load_workbook(src, data_only=True)
    need = ["Parameter", "Master SKU", "Data Stok", "DOI SKU"]
    miss = [n for n in need if n not in wb.sheetnames]
    if miss:
        raise ValueError(f"Bukan file laporan DOI dari aplikasi ini. Sheet tidak ditemukan: {', '.join(miss)}")

    # ---------- Parameter ----------
    P = wb["Parameter"]
    judul = str(P["B2"].value or "")
    cabang = judul.split("CABANG", 1)[-1].strip().title() if "CABANG" in judul else (nama_file or "Cabang")
    hk = float(P["C5"].value or 26); N = int(P["C6"].value or 1); ambang = float(P["C7"].value or 0)
    tgl = pd.Timestamp(P["C4"].value) if P["C4"].value else pd.NaT
    bulan_ams = [str(c.value) for c in P[9][2:] if c.value not in (None, "")]
    oms_txt = str(P["C10"].value or "")
    pakai_oms = not oms_txt.lower().startswith("tidak dipakai")
    gflag, gnama, r = {}, {}, 14
    while P.cell(r, 2).value not in (None, ""):
        g = str(P.cell(r, 2).value).strip(); gnama[g] = str(P.cell(r, 3).value or ""); gflag[g] = str(P.cell(r, 4).value or "Ya").strip().lower() == "ya"; r += 1
    standar, urutan, r = {}, [], 14
    while P.cell(r, 7).value not in (None, ""):
        p = str(P.cell(r, 7).value).strip(); standar[p] = float(P.cell(r, 8).value or 30); urutan.append(p); r += 1

    # ---------- Peringatan dari sheet Catatan (bila ada) ----------
    peringatan = []
    if "Catatan" in wb.sheetnames:
        ambil = False
        for (v,) in wb["Catatan"].iter_rows(min_col=2, max_col=2, values_only=True):
            t = str(v or "")
            if t.startswith("PERINGATAN DATA"): ambil = True; continue
            if ambil:
                if not t.strip() or not t.startswith("- "): break
                peringatan.append(t[2:])

    # ---------- Master SKU ----------
    ms = pd.DataFrame(list(wb["Master SKU"].iter_rows(min_row=5, values_only=True)), columns=[c.value for c in wb["Master SKU"][4]])
    ms = ms[ms["Kode"].notna()].copy(); ms["Kode"] = ms["Kode"].map(_kode)
    ms["Konversi"] = _num(ms["Konversi"]).fillna(1)
    kols = list(ms.columns)
    qty_cols = [c for c in kols if str(c).startswith("Qty ")]; rp_cols = [c for c in kols if str(c).startswith("Rp ")]
    for c in qty_cols + rp_cols: ms[c] = _num(ms[c])
    oms_rp = [c for c in rp_cols if "(s/d" in str(c)]; oms_q = [c for c in qty_cols if "(s/d" in str(c)]
    ams_rp = [c for c in rp_cols if c not in oms_rp]; ams_q = [c for c in qty_cols if c not in oms_q]
    sq = ms[qty_cols].sum(axis=1, min_count=1).fillna(0); sr = ms[rp_cols].sum(axis=1, min_count=1).fillna(0)
    ms["harga"] = np.where(sq > 0, sr / sq.replace(0, np.nan), 0.0); ms["harga"] = ms["harga"].fillna(0)
    ms["ams"] = ms[ams_rp].sum(axis=1, min_count=1).fillna(0) / N
    mi = ms.set_index("Kode")

    # ---------- Data Stok ----------
    ds = pd.DataFrame(list(wb["Data Stok"].iter_rows(min_row=5, values_only=True)), columns=[c.value for c in wb["Data Stok"][4]])
    ds = ds[ds["Kode"].notna()].copy(); ds["Kode"] = ds["Kode"].map(_kode); ds["Gudang"] = ds["Gudang"].astype(str).str.strip()
    for c in ["Stok Akhir (Besar)", "Stok Akhir (Kecil)", "Penj. Ecer (Besar)", "Penj. Ecer (Kecil)", "Retur Jual (Besar)", "Retur Jual (Kecil)"]: ds[c] = _num(ds[c]).fillna(0)
    ds["konv"] = ds["Kode"].map(mi["Konversi"]).fillna(1)
    ds["stok"] = ds["Stok Akhir (Besar)"] + ds["Stok Akhir (Kecil)"] / ds["konv"]
    ds["hitung"] = ds["Gudang"].map(gflag).fillna(True)
    ds["stok_hit"] = np.where(ds["hitung"], ds["stok"], 0.0)
    ds["oms_q"] = -(ds["Penj. Ecer (Besar)"] + ds["Retur Jual (Besar)"] + (ds["Penj. Ecer (Kecil)"] + ds["Retur Jual (Kecil)"]) / ds["konv"])
    ds["harga"] = ds["Kode"].map(mi["harga"]).fillna(0)
    ds["nilai"] = ds["stok"] * ds["harga"]

    # ---------- DOI SKU (daftar SKU + hitung ulang) ----------
    rows = [(r[0], r[1]) for r in wb["DOI SKU"].iter_rows(min_row=7, min_col=2, max_col=3, values_only=True) if r[1]]
    sk = pd.DataFrame(rows, columns=["principal", "kode"]); sk["kode"] = sk["kode"].map(_kode)
    agg = ds.groupby("Kode").agg(stok=("stok_hit", "sum"), oms_q=("oms_q", "sum"))
    sk = sk.join(agg, on="kode"); sk[["stok", "oms_q"]] = sk[["stok", "oms_q"]].fillna(0)
    sk["nama"] = sk["kode"].map(mi["Nama Barang"]); sk["sat"] = sk["kode"].map(mi["Satuan Besar"])
    sk["divisi"] = sk["kode"].map(mi["Divisi"]); sk["grup"] = sk["kode"].map(mi["Group"])
    sk["harga"] = sk["kode"].map(mi["harga"]).fillna(0); sk["ams"] = sk["kode"].map(mi["ams"]).fillna(0)
    sk["saldo"] = sk["stok"] * sk["harga"]
    if oms_rp: sk["oms"] = sk["kode"].map(mi[oms_rp[0]]).fillna(0)
    elif pakai_oms: sk["oms"] = sk["oms_q"] * sk["harga"]
    else: sk["oms"] = 0.0
    sk["doi"] = np.where(sk["ams"] > ambang, np.maximum(sk["saldo"], 0) / (sk["ams"] / hk).replace(0, np.nan), np.nan)
    ai = (sk["ams"] * N + sk["oms"]) / (N + 1)
    sk["doi_inc"] = np.where(pakai_oms & (ai > ambang), np.maximum(sk["saldo"], 0) / (ai / hk).replace(0, np.nan), np.nan)
    sk["std"] = sk["principal"].map(standar).fillna(30.0)
    sk["lebih_kurang"] = np.where(sk["doi"].notna(), (sk["doi"] - sk["std"]) * sk["ams"] / hk, np.nan)
    sk["batas_kritis"] = np.maximum(3.0, (0.25 * sk["std"]).round())
    sk["status"] = np.select(
        [sk["stok"] < 0, (sk["ams"] < 0) & (sk["stok"] <= 0), (sk["ams"] <= ambang) & (sk["stok"] > 0), (sk["ams"] > ambang) & (sk["stok"] <= 0),
         sk["doi"] < sk["batas_kritis"], sk["doi"] > sk["std"] + TOLERANSI_HARI, sk["doi"] < sk["std"] - TOLERANSI_HARI, sk["doi"].notna()],
        ["Stok minus (cek pencatatan)", "AMS minus (retur > penjualan)", "Stok mati (tanpa penjualan)", "Stok kosong", "Kritis (hampir habis)",
         "Kelebihan stok", "Di bawah standar", "Sesuai standar"], default="Tidak aktif")
    sk["tanpa_harga"] = (sk["harga"] == 0) & (sk["stok"] != 0)
    sk.insert(0, "cabang", cabang)
    for d in (sk,): d["cabang"] = cabang

    # ---------- tren bulanan ----------
    b = ms[["Kode", "Principal"] + ams_rp + oms_rp].melt(id_vars=["Kode", "Principal"], var_name="bulan", value_name="rp").dropna(subset=["rp"])
    b["bulan"] = b["bulan"].str.replace("Rp ", "", regex=False); b["cabang"] = cabang
    b["parsial"] = b["bulan"].str.contains(r"\(s/d")
    b["bulan_urut"] = b["bulan"].map({m: i for i, m in enumerate(bulan_ams + [x for x in b["bulan"].unique() if x not in bulan_ams])})
    bulanan = b.rename(columns={"Principal": "principal", "Kode": "kode"})

    # ---------- gudang ----------
    gd = ds.groupby("Gudang").agg(nilai=("nilai", "sum"), sku=("Kode", "nunique")).reset_index()
    gd["keterangan"] = gd["Gudang"].map(gnama); gd["dihitung"] = gd["Gudang"].map(gflag).fillna(True); gd["cabang"] = cabang
    gd = gd.rename(columns={"Gudang": "gudang"})

    param = dict(cabang=cabang, tanggal=tgl, hari_kerja=hk, n_bulan=N, ambang=ambang, bulan=bulan_ams, pakai_oms=pakai_oms,
                 oms_txt=oms_txt, peringatan=peringatan, standar=standar, urutan=urutan, file=nama_file)
    return dict(sku=sk, bulanan=bulanan, gudang=gd, param=param)


def gabung(hasil_list):
    """Gabungkan beberapa file (cabang berbeda). Bila nama cabang kembar, ditambah nomor."""
    seen, sku, bln, gud, params = {}, [], [], [], []
    for h in hasil_list:
        c = h["param"]["cabang"]; seen[c] = seen.get(c, 0) + 1
        if seen[c] > 1:
            nc = f"{c} ({seen[c]})"
            for k in ("sku", "bulanan", "gudang"): h[k] = h[k].assign(cabang=nc)
            h["param"]["cabang"] = nc
        sku.append(h["sku"]); bln.append(h["bulanan"]); gud.append(h["gudang"]); params.append(h["param"])
    return dict(sku=pd.concat(sku, ignore_index=True), bulanan=pd.concat(bln, ignore_index=True), gudang=pd.concat(gud, ignore_index=True), param=params)


# ---------------- ringkasan (dipakai KPI & grafik) ----------------
def ringkas(sku, hk, by=("principal",)):
    by = list(by)
    g = sku.groupby(by).agg(sku=("kode", "count"), saldo=("saldo", "sum"), ams=("ams", "sum"), std_n=("std", "mean")).reset_index()
    g["doi"] = np.where(g["ams"] > 0, g["saldo"].clip(lower=0) / (g["ams"] / hk), np.nan)
    sj = sku.assign(w=sku["std"] * sku["ams"]).groupby(by).agg(w=("w", "sum")).reset_index()
    g = g.merge(sj, on=by); g["std"] = np.where(g["ams"] > 0, g["w"] / g["ams"].replace(0, np.nan), g["std_n"])
    g["lebih_kurang"] = np.where(g["doi"].notna(), (g["doi"] - g["std"]) * g["ams"] / hk, np.nan)
    g["porsi_ams"] = g["ams"] / g["ams"].sum() * 100 if g["ams"].sum() else 0
    g["porsi_saldo"] = g["saldo"] / g["saldo"].sum() * 100 if g["saldo"].sum() else 0
    return g.drop(columns=["w", "std_n"])


def kpi(sku, hk):
    ams, saldo = sku["ams"].sum(), sku["saldo"].sum()
    pos = sku.loc[sku["lebih_kurang"] > 0, "lebih_kurang"].sum(); neg = sku.loc[sku["lebih_kurang"] < 0, "lebih_kurang"].sum()
    return dict(
        saldo=saldo, ams=ams, doi=(max(saldo, 0) / (ams / hk) if ams > 0 else np.nan), n_sku=len(sku), kelebihan=pos, kekurangan=neg,
        n_kritis=int((sku["status"] == "Kritis (hampir habis)").sum()), n_kosong=int((sku["status"] == "Stok kosong").sum()),
        n_mati=int((sku["status"] == "Stok mati (tanpa penjualan)").sum()), n_tanpa_harga=int(sku["tanpa_harga"].sum()),
        ams_kosong=sku.loc[sku["status"].isin(["Stok kosong", "Kritis (hampir habis)"]), "ams"].sum())


def bucket_doi(sku, col="principal"):
    rows = []
    for lab, lo, hi in BUCKETS:
        m = sku["doi"].ge(lo) & (sku["doi"].lt(hi) if hi else True)
        rows.append((lab, m))
    out = sku[[col]].copy()
    out["rentang"] = "Tanpa AMS"
    for lab, m in rows: out.loc[m, "rentang"] = lab
    return out.groupby([col, "rentang"]).size().reset_index(name="n")


def insight(sku, rk, bulanan, gudang, hk):
    """Temuan otomatis (teks) dari data yang sedang difilter. rk = hasil ringkas(by principal) dengan kolom 'label'."""
    out = []
    rk = rk[rk["doi"].notna()]
    if len(rk):
        a = rk.sort_values("lebih_kurang", ascending=False).iloc[0]
        if a["lebih_kurang"] > 0:
            out.append(f"**Kelebihan stok terbesar: {a['label']}**. DOI {a['doi']:,.1f} hari vs standar {a['std']:,.0f} hari, "
                       f"atau sekitar {fmt_rp(a['lebih_kurang'])} stok di atas standar.")
        b = rk.sort_values("lebih_kurang").iloc[0]
        if b["lebih_kurang"] < 0:
            out.append(f"**Paling kekurangan stok: {b['label']}**. DOI {b['doi']:,.1f} hari vs standar {b['std']:,.0f} hari "
                       f"(kurang sekitar {fmt_rp(abs(b['lebih_kurang']))}).")
        r = rk.assign(selisih=rk["porsi_saldo"] - rk["porsi_ams"]).sort_values("selisih", ascending=False).iloc[0]
        if r["selisih"] > 5:
            out.append(f"**Stok tidak sebanding dengan penjualan: {r['label']}**. Menyumbang {r['porsi_ams']:,.1f}% omset, "
                       f"tetapi memegang {r['porsi_saldo']:,.1f}% nilai stok.")
    k = kpi(sku, hk)
    if k["n_kritis"] + k["n_kosong"]:
        out.append(f"**{k['n_kritis'] + k['n_kosong']:,} SKU hampir habis atau kosong** ({k['n_kosong']:,} kosong). "
                   f"Omsetnya sekitar {fmt_rp(k['ams_kosong'])} per bulan, jadi berisiko kehilangan penjualan.")
    if k["n_mati"]:
        out.append(f"**{k['n_mati']:,} SKU stok mati**: ada stok tetapi tidak ada penjualan pada bulan data.")
    if k["n_tanpa_harga"]:
        out.append(f"{k['n_tanpa_harga']:,} SKU punya stok tanpa harga (tidak terjual di bulan data), jadi nilainya terhitung Rp 0 dan total saldo cenderung lebih rendah dari aslinya.")
    g = gudang[gudang["nilai"] < -1]
    for _, x in g.iterrows():
        out.append(f"**Gudang {x['gudang']} bersaldo minus {fmt_rp(abs(x['nilai']))}** ({x['cabang']}). Bila ini hanya selisih pencatatan, stok sebenarnya lebih besar dan DOI bisa terlalu rendah. Cek ke gudang.")
    b = bulanan[~bulanan["parsial"]]
    if b["bulan_urut"].nunique() >= 2:
        pv = b.groupby(["principal", "bulan_urut"])["rp"].sum().unstack()
        akhir = pv.columns.max(); lalu = pv.drop(columns=[akhir]).mean(axis=1)
        d = pd.DataFrame({"akhir": pv[akhir], "lalu": lalu}); d = d[d["lalu"] >= 1e8]; d["pct"] = (d["akhir"] / d["lalu"] - 1) * 100
        if len(d):
            lo, hi = d.sort_values("pct").iloc[0], d.sort_values("pct").iloc[-1]
            if lo["pct"] < -15: out.append(f"**Omset turun: {lo.name}** {lo['pct']:,.0f}% pada bulan terakhir dibanding rata-rata bulan sebelumnya ({fmt_rp(lo['akhir'])} vs {fmt_rp(lo['lalu'])}). Pantau stoknya, DOI bisa terlihat lebih rendah dari kenyataan.")
            if hi["pct"] > 15 and hi.name != lo.name: out.append(f"**Omset naik: {hi.name}** +{hi['pct']:,.0f}% pada bulan terakhir ({fmt_rp(hi['akhir'])} vs rata-rata {fmt_rp(hi['lalu'])}). Pastikan stok cukup.")
    return out