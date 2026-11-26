# scripts/doi_cabang.py
import os, re, glob, io, contextlib, datetime as dt
import numpy as np, pandas as pd
from scripts.excel_utils import pastikan_xlsx
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter as L

# ==== SEL 1: PENGATURAN DEFAULT (persis seperti di Colab) ====
CABANG_DEFAULT              = ""
HARI_KERJA_DEFAULT          = 26
MAKS_BULAN_AMS_DEFAULT      = None
AMBANG_AMS_MIN_DEFAULT      = 0
STANDAR_DOI_DEFAULT_VAL     = 30
STANDAR_DOI_DICT            = {'KDM (Camel)': 7}

GUDANG_KATA_KUNCI_TIDAK_DIHITUNG = ['BADSTOCK', 'BAD STOCK', 'PEMUSNAHAN', 'DISPOSAL', 'RUSAK', 'EXPIRED']
GUDANG_KODE_TIDAK_DIHITUNG       = []

PRINCIPAL_BY_GROUP  = {'PRISTINE': 'SWT (Pristine)', 'ZODA': 'KMI (Zoda)', 'ROOTBEER': 'SDN (Rootbeer)'}
PRINCIPAL_BY_DIVISI = {'UNICHARM': 'UCI (Unicharm)', 'KDM': 'KDM (Camel)', 'BENDERA': 'FFI (Susu Bendera)',
                       'ABC PRESIDENT': 'ABC (Nu Green Tea)', 'ABC KOGEN (KIN)': 'ABC Kogen (KIN)'}
URUTAN_PRINCIPAL    = ['FFI (Susu Bendera)', 'ABC (Nu Green Tea)', 'UCI (Unicharm)', 'SWT (Pristine)',
                       'KMI (Zoda)', 'KDM (Camel)']
GROUP_DIKECUALIKAN  = ['NON SELL ITEM']
# Bulan yang sama dengan tanggal akhir Mutasi Stok:
#   'auto'  = masuk AMS bila posisi stok tepat akhir bulan DAN penjualan bulan itu sudah diupload; kalau tidak, jadi OMS
#   'ya'    = selalu masuk AMS (bila penjualannya ada)    'tidak' = selalu jadi OMS (aturan lama)
BULAN_STOK_MASUK_AMS_DEFAULT = 'auto'
BLN = ['Jan','Feb','Mar','Apr','Mei','Jun','Jul','Agu','Sep','Okt','Nov','Des']
def label_bulan(p): return f"{BLN[p.month-1]} {p.year}"
def k(x):
    if pd.isna(x): return ''
    x = str(x).strip()
    return x[:-2] if x.endswith('.0') else x

# ==== SEL 2 & 3: FUNGSI PEMBACA ====
def jenis_file(path):
    pastikan_xlsx(path)  # dukung .xls/HTML/CSV yang menyamar sebagai .xlsx
    try:
        wb = load_workbook(path, read_only=True, data_only=True)
        rows = list(wb.worksheets[0].iter_rows(min_row=1, max_row=3, values_only=True)); wb.close()
    except Exception:
        return None
    a1 = str(rows[0][0] or '')
    if 'Mutasi Stok' in a1: return 'mutasi'
    if 'Penjualan' in a1 and 'Customer' in a1: return 'penjualan'
    hdr = [str(x) for x in rows[0] if x]
    if 'Kode' in hdr and 'Konversi' in hdr: return 'daftar'
    return None

MUT_COLS = ['gud','div','tipe','kode','nama','sing','sa_b','sa_k','lpb_b','lpb_k','sik_b','sik_k','sib_b','sib_k','dok_b','dok_k',
 'dob_b','dob_k','tj_b','tj_k','ti_b','ti_k','rp_b','rp_k','mi_b','mi_k','tm_b','tm_k','rb_b','rb_k','pe_b','pe_k','pt_b','pt_k',
 'fs_b','fs_k','bn_b','bn_k','sik2_b','sik2_k','sib2_b','sib2_k','dok2_b','dok2_k','dob2_b','dob2_k','ta_b','ta_k','to_b','to_k',
 'mo_b','mo_k','bon_b','bon_k','tit_b','tit_k','sk_b','sk_k','ak_b','ak_k','sat_b','sat_k']

def baca_mutasi(path):
    pastikan_xlsx(path)
    raw = pd.read_excel(path, header=None, sheet_name=0)
    tgl = None
    for i in range(min(8, len(raw))):
        v = [x for x in raw.iloc[i, :2] if isinstance(x, (pd.Timestamp, dt.datetime))]
        if len(v) == 2: tgl = (pd.Timestamp(v[0]), pd.Timestamp(v[1])); break
    assert tgl, "Periode (tanggal awal/akhir) tidak ditemukan di baris atas Laporan Mutasi Stok"
    hdr_end = next(i for i in range(min(15, len(raw))) if str(raw.iloc[i, 6]).strip().lower().startswith('satuan besar'))
    m = raw.iloc[hdr_end+1:, :62].copy(); m.columns = MUT_COLS
    m = m[m['kode'].notna()].copy()
    m['kode'] = m['kode'].map(k); m['gud'] = m['gud'].astype(str).str.strip()
    for c in MUT_COLS[6:60]: m[c] = pd.to_numeric(m[c], errors='coerce').fillna(0)
    m['sat_b'] = m['sat_b'].astype(str).str.strip(); m['sat_k'] = m['sat_k'].astype(str).str.replace(r'_x000D_|\s+', '', regex=True)
    return m[m['tipe'] == 'Produk Jadi'].reset_index(drop=True), tgl

def baca_penjualan(path):
    pastikan_xlsx(path)
    raw = pd.read_excel(path, header=None)
    i = raw.index[raw.iloc[:, 0].astype(str).str.strip() == 'Salesman'][0]
    df = raw.iloc[i+1:].copy(); df.columns = [str(c).strip() for c in raw.iloc[i]]
    df['Tanggal Faktur'] = pd.to_datetime(df['Tanggal Faktur'], errors='coerce')
    df = df[df['Tanggal Faktur'].notna()].copy()
    for c in ['Qty Sales', 'Net Sales (incl. PPN)']: df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
    df['kode'] = df['Kode Barang'].map(k); df['file'] = os.path.basename(path)
    return df[['kode','Nama Barang','Satuan','Tanggal Faktur','Qty Sales','Net Sales (incl. PPN)','Kode Gudang','Nama Gudang','file']]


def run_doi_pipeline(
    file_paths,
    output_dir="output",
    CABANG=CABANG_DEFAULT,
    HARI_KERJA=HARI_KERJA_DEFAULT,
    MAKS_BULAN_AMS=MAKS_BULAN_AMS_DEFAULT,
    AMBANG_AMS_MIN=AMBANG_AMS_MIN_DEFAULT,
    STANDAR_DOI_DEFAULT=STANDAR_DOI_DEFAULT_VAL,
    BULAN_STOK_MASUK_AMS=BULAN_STOK_MASUK_AMS_DEFAULT
):
    STANDAR_DOI = dict(STANDAR_DOI_DICT)
    log_stream = io.StringIO()
    PERINGATAN = []
    def warn(msg):
        print(msg); PERINGATAN.append(msg)

    with contextlib.redirect_stdout(log_stream):
        FILES = sorted(file_paths)
        F_MUT, F_JUAL, F_DAFTAR = [], [], []
        for f in FILES:
            j = jenis_file(f)
            print(f"{os.path.basename(f):70s} -> {j or 'DIABAIKAN (tidak dikenali)'}")
            {'mutasi': F_MUT, 'penjualan': F_JUAL, 'daftar': F_DAFTAR}.get(j, []).append(f)
        assert len(F_MUT) == 1,    f"Harus ada tepat 1 Laporan Mutasi Stok (terbaca {len(F_MUT)})"
        assert len(F_DAFTAR) == 1, f"Harus ada tepat 1 Daftar Barang (terbaca {len(F_DAFTAR)})"
        assert len(F_JUAL) >= 1,   "Minimal 1 Laporan Penjualan"

        # ==== SEL 3: BACA & OLAH DATA ====
        mut, (mut_awal, mut_akhir) = baca_mutasi(F_MUT[0])
        sales = pd.concat([baca_penjualan(f) for f in F_JUAL], ignore_index=True)
        daftar = pd.read_excel(F_DAFTAR[0]); daftar['kode'] = daftar['Kode'].map(k); daftar = daftar[daftar.kode != '']
        if not CABANG:
            CABANG = re.sub(r'(?i)laporan[_ ]mutasi[_ ]stok[_ ]?|\(\d+\)|\.xlsx', '', os.path.basename(F_MUT[0])).strip('_ -') or 'Cabang'
            CABANG = re.sub(r'(?i)(?<=[_ -])(jan|feb|mar|apr|mei|jun|jul|agu|agt|sep|okt|nov|des|oct|dec|aug)[a-z]*(?=[_ -]|$|\d)', '', CABANG)
            CABANG = re.sub(r'(?<=[_ -])\d{4}(?=[_ -]|$)|^\d{4}[_ -]', '', CABANG)
            CABANG = re.sub(r'[_ -]{2,}', '_', CABANG).strip('_ -') or 'Cabang'

        # ---- cek rentang tanggal tiap file penjualan (peringatan dobel-hitung) ----
        print(f"\nMutasi stok : {mut_awal:%d-%m-%Y} s/d {mut_akhir:%d-%m-%Y}  | {len(mut):,} baris produk jadi | cabang: {CABANG}")
        rg = sales.groupby('file')['Tanggal Faktur'].agg(['min','max','count']).sort_values('min')
        print(rg.to_string())
        prev = None
        for f, r in rg.iterrows():
            if prev is not None and r['min'] <= prev[1]:
                warn(f"!! PERINGATAN: rentang tanggal '{f}' tumpang tindih dengan '{prev[0]}' -> kemungkinan omset terhitung ganda.")
            prev = (f, r['max'])

        # ---- cek kecocokan gudang tiap file penjualan dengan Mutasi Stok (deteksi file cabang lain) ----
        gud_mut = set(mut.gud)
        sales['_gok'] = sales['Kode Gudang'].map(k).isin(gud_mut)
        cocok = sales.groupby('file')['_gok'].mean(); rp_file = sales.groupby('file')['Net Sales (incl. PPN)'].sum()
        for f_, v_ in cocok.items():
            if v_ < 0.8: warn(f"!! PERINGATAN: file '{f_}' hanya {v_:.0%} barisnya memakai gudang yang ada di Laporan Mutasi Stok -> KEMUNGKINAN FILE CABANG LAIN. Periksa dan keluarkan bila salah cabang.")

        # ---- tentukan bulan AMS & OMS ----
        bln_ini = pd.Period(mut_akhir, 'M')
        sales['bulan'] = sales['Tanggal Faktur'].dt.to_period('M')
        ada_bln_ini = bool((sales['bulan'] == bln_ini).any())
        akhir_bulan = (mut_akhir + pd.Timedelta(days=1)).month != mut_akhir.month
        if BULAN_STOK_MASUK_AMS == 'ya': BLN_INI_MASUK_AMS = ada_bln_ini
        elif BULAN_STOK_MASUK_AMS == 'tidak': BLN_INI_MASUK_AMS = False
        else: BLN_INI_MASUK_AMS = akhir_bulan and ada_bln_ini
        if BLN_INI_MASUK_AMS and not akhir_bulan:
            warn(f"!! PERINGATAN: {label_bulan(bln_ini)} dipaksa masuk AMS padahal posisi stok {mut_akhir:%d-%m-%Y} belum akhir bulan (bulan belum penuh).")
        PAKAI_OMS = not BLN_INI_MASUK_AMS
        bulan_ams = [b for b in sorted(sales['bulan'].unique()) if b < bln_ini or (BLN_INI_MASUK_AMS and b == bln_ini)]
        if MAKS_BULAN_AMS: bulan_ams = bulan_ams[-MAKS_BULAN_AMS:]
        assert bulan_ams, "Tidak ada data penjualan SEBELUM bulan berjalan (bulan mutasi stok). Upload penjualan bulan-bulan sebelumnya."
        if len(bulan_ams) > 1:
            gap = [str(b) for b in pd.period_range(bulan_ams[0], bulan_ams[-1], freq='M') if b not in bulan_ams]
            if gap: warn('!! PERINGATAN: bulan berikut tidak ada di data penjualan: ' + str(gap))
        OMS_DARI_PENJUALAN = PAKAI_OMS and ada_bln_ini
        s_oms = sales[(sales['Tanggal Faktur'] >= mut_awal) & (sales['Tanggal Faktur'] <= mut_akhir)] if OMS_DARI_PENJUALAN else sales.iloc[0:0]
        N = len(bulan_ams)
        print(f"\nBulan AMS ({N}): {', '.join(label_bulan(b) for b in bulan_ams)}")
        print(f"Bulan stok: {label_bulan(bln_ini)} s/d {mut_akhir:%d-%m} | " + ('MASUK AMS (bulan penuh), OMS tidak dipakai' if BLN_INI_MASUK_AMS else
              f"jadi OMS, sumber: {'Laporan Penjualan' if OMS_DARI_PENJUALAN else 'Laporan Mutasi Stok (ESTIMASI: Penjualan Ecer + Retur x harga)'}"))

        # ---- master SKU ----
        s_pakai = sales[sales['bulan'].isin(bulan_ams)]
        dm = daftar.drop_duplicates('kode').set_index('kode')[['Nama','Group','Divisi']]
        kon = daftar.set_index(['kode','Sat'])['Konversi']; kon = kon[~kon.index.duplicated()]
        sat_b = mut.groupby('kode')['sat_b'].first()
        sat_s = sales.groupby('kode')['Satuan'].first()
        sat = pd.concat([sat_b, sat_s[~sat_s.index.isin(sat_b.index)]])
        nama_s = sales.groupby('kode')['Nama Barang'].first()
        kodes = sorted(set(mut.kode) | set(s_pakai.kode) | set(s_oms.kode))
        def principal(div, grp):
            return PRINCIPAL_BY_GROUP.get(grp) or PRINCIPAL_BY_DIVISI.get(div) or str(div)
        rows, tanpa_daftar, tanpa_konv = [], [], []
        for kd in kodes:
            if kd in dm.index: nm, gr, dv = dm.loc[kd, 'Nama'], dm.loc[kd, 'Group'], dm.loc[kd, 'Divisi']
            else: nm, gr, dv = nama_s.get(kd, kd), '-', 'TIDAK ADA DI DAFTAR BARANG'; tanpa_daftar.append(kd)
            kv = kon.get((kd, sat.get(kd)), np.nan)
            if pd.isna(kv): kv = 1; tanpa_konv.append(kd)
            rows.append(dict(kode=kd, nama=nm, div=dv, grp=gr, prin=principal(dv, gr), sat=sat.get(kd), konv=float(kv)))
        M = pd.DataFrame(rows)
        if tanpa_daftar: warn(f"!! {len(tanpa_daftar)} kode tidak ada di Daftar Barang (principal = 'TIDAK ADA DI DAFTAR BARANG'): {tanpa_daftar[:8]}")
        if tanpa_konv:   warn(f"!! {len(tanpa_konv)} kode tanpa konversi untuk satuan besarnya (dianggap 1): {tanpa_konv[:8]}")
        bad_sat = sales.merge(sat_b.rename('sb'), left_on='kode', right_index=True)
        bad_sat = bad_sat[bad_sat['Satuan'].str.strip() != bad_sat['sb']]['kode'].unique()
        if len(bad_sat): warn(f"!! {len(bad_sat)} kode satuan di laporan penjualan berbeda dengan satuan besar mutasi (qty bisa tidak sebanding): {list(bad_sat[:8])}")

        q_m = s_pakai.groupby(['kode','bulan'])['Qty Sales'].sum().unstack()
        r_m = s_pakai.groupby(['kode','bulan'])['Net Sales (incl. PPN)'].sum().unstack()
        q_o = s_oms.groupby('kode')['Qty Sales'].sum(); r_o = s_oms.groupby('kode')['Net Sales (incl. PPN)'].sum()

        # ---- gudang ----
        nama_gud = sales.drop_duplicates('Kode Gudang').set_index('Kode Gudang')['Nama Gudang'].to_dict()
        gl = sorted(mut.gud.unique())
        def hitung_gudang(g):
            nm = str(nama_gud.get(g, '')).upper()
            return not (g in GUDANG_KODE_TIDAK_DIHITUNG or any(w in nm for w in GUDANG_KATA_KUNCI_TIDAK_DIHITUNG))
        gflag = {g: hitung_gudang(g) for g in gl}
        print('\nGudang tidak dihitung sebagai stok:', [f"{g} ({nama_gud.get(g,'?')})" for g in gl if not gflag[g]] or 'tidak ada')
        print('Gudang tanpa nama di laporan penjualan (dihitung, periksa manual bila perlu):', [g for g in gl if g not in nama_gud])

        # ---- stok & OMS (pandas, untuk cek & ringkasan) ----
        mut = mut.merge(M[['kode','konv']], on='kode', how='left')
        mut['stok']  = mut.ak_b + mut.ak_k / mut.konv
        mut['stokh'] = np.where(mut.gud.map(gflag), mut.stok, 0)
        mut['oms']   = -(mut.pe_b + mut.rp_b + (mut.pe_k + mut.rp_k) / mut.konv)
        st = mut.groupby('kode').agg(stok=('stokh','sum'), oms_mut=('oms','sum'))
        M = M.join(st, on='kode'); M[['stok','oms_mut']] = M[['stok','oms_mut']].fillna(0)
        qs = q_m.reindex(M.kode).fillna(0).sum(axis=1).values + (q_o.reindex(M.kode).fillna(0).values if OMS_DARI_PENJUALAN else 0)
        rs = r_m.reindex(M.kode).fillna(0).sum(axis=1).values + (r_o.reindex(M.kode).fillna(0).values if OMS_DARI_PENJUALAN else 0)
        M['harga'] = np.where(qs > 0, rs / np.where(qs == 0, np.nan, qs), 0)
        M['ams']   = r_m.reindex(M.kode).fillna(0).sum(axis=1).values / N
        M['oms_rp'] = (r_o.reindex(M.kode).fillna(0).values if OMS_DARI_PENJUALAN else M.oms_mut * M.harga)
        if not PAKAI_OMS: M['oms_rp'] = 0.0
        M['saldo'] = M.stok * M.harga
        # gudang bersaldo minus (nilai) -> peringatan
        mut['nilai'] = mut['stok'] * mut['kode'].map(M.set_index('kode')['harga']).fillna(0)
        for g_, v_ in mut[mut.gud.map(gflag)].groupby('gud')['nilai'].sum().items():
            if v_ < 0: warn(f"!! PERINGATAN: gudang {g_} ({nama_gud.get(g_, '?')}) bersaldo MINUS Rp {v_:,.0f}. Stok antar gudang dijumlahkan (net). Bila minus ini hanya selisih pencatatan (mis. penerimaan belum diinput), stok sebenarnya lebih besar dan DOI bisa terlalu rendah. Cek ke gudang.")
        M['doi']   = np.where(M.ams > AMBANG_AMS_MIN, np.maximum(M.saldo, 0) / (M.ams / HARI_KERJA), np.nan)
        ams_inc    = (M.ams * N + M.oms_rp) / (N + 1)
        M['doi_inc'] = np.where(ams_inc > AMBANG_AMS_MIN, np.maximum(M.saldo, 0) / (ams_inc / HARI_KERJA), np.nan)
        if not PAKAI_OMS: M['doi_inc'] = np.nan
        M['std'] = M.prin.map(lambda p: STANDAR_DOI.get(p, STANDAR_DOI_DEFAULT))

        prins_all = list(M.prin.unique())
        prins = [p for p in URUTAN_PRINCIPAL if p in prins_all] + sorted(p for p in prins_all if p not in URUTAN_PRINCIPAL)
        inc = M[~M.grp.isin(GROUP_DIKECUALIKAN) & ((M.stok.abs() > 1e-9) | (M.ams != 0) | (M.oms_rp.abs() > 1e-9) | ((M.oms_mut.abs() > 1e-9) & PAKAI_OMS))].copy()
        inc['pi'] = inc.prin.map({p: i for i, p in enumerate(prins)}); inc['dk'] = inc.doi.fillna(-1)
        inc = inc.sort_values(['pi','dk'], ascending=[True, False])
        prins = [p for p in prins if p in set(inc.prin)]
        print(f"\nSKU masuk laporan: {len(inc):,}")

        # ==== SEL 4: SUSUN FILE EXCEL (rumus hidup) ====
        wb = Workbook()
        Fn = lambda **kw: Font(name='Arial', size=kw.pop('size', 10), **kw)
        HDR = PatternFill('solid', start_color='1F3864'); HF = Font(name='Arial', size=10, bold=True, color='FFFFFF')
        INP = Font(name='Arial', size=10, color='0000FF'); YEL = PatternFill('solid', start_color='FFFF00'); GR = PatternFill('solid', start_color='D9E1F2')
        thin = Side(style='thin', color='BFBFBF'); BD = Border(top=thin, bottom=thin, left=thin, right=thin)
        NOTE = Fn(italic=True, color='595959')
        def hdr(ws, row, c0, vals, h=30):
            for i, v in enumerate(vals):
                c = ws.cell(row, c0+i, v); c.font = HF; c.fill = HDR; c.border = BD
                c.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
            ws.row_dimensions[row].height = h
        def widths(ws, w):
            for i, x in enumerate(w, 1): ws.column_dimensions[L(i)].width = x
        fv = lambda v: None if (v is None or (isinstance(v, float) and np.isnan(v))) else (float(v) if isinstance(v, (np.floating, np.integer)) else v)
        lbl_ams = [label_bulan(b) for b in bulan_ams]; lbl_oms = f"{label_bulan(bln_ini)} (s/d {mut_akhir:%d %b})"

        # ===== Parameter =====
        P = wb.active; P.title = 'Parameter'
        P['B2'] = f'PARAMETER LAPORAN DOI - CABANG {CABANG.upper()}'; P['B2'].font = Fn(bold=True, size=13)
        par = [('Tanggal posisi stok (Laporan Mutasi Stok s/d)', mut_akhir.date(), 'dd-mm-yyyy', f'Periode mutasi stok {mut_awal:%d-%m-%Y} s/d {mut_akhir:%d-%m-%Y}'),
               ('Hari kerja per bulan', HARI_KERJA, '0', 'DOI = Saldo / (AMS / hari kerja)'),
               ('Jumlah bulan pembagi AMS', N, '0', 'Otomatis = jumlah bulan penjualan yang dipakai. Jangan ubah kecuali Anda mengosongkan kolom bulan di Master SKU.'),
               ('Ambang AMS minimum (Rp/bulan)', AMBANG_AMS_MIN, '#,##0', 'SKU dengan AMS <= ambang ini masuk kolom "AMS Min"')]
        for i, (a, b, fm, n) in enumerate(par):
            r = 4 + i; P.cell(r, 2, a).font = Fn(); c = P.cell(r, 3, b); c.font = INP; c.fill = YEL; c.number_format = fm; P.cell(r, 4, n).font = NOTE
        P['B9'] = 'Bulan penyusun AMS'; P['B9'].font = Fn(bold=True)
        for i, t in enumerate(lbl_ams): c = P.cell(9, 3+i, t); c.font = INP; c.alignment = Alignment(horizontal='center')
        P['B10'] = 'Bulan OMS (bulan berjalan)'; P['B10'].font = Fn(); P['C10'] = (lbl_oms if PAKAI_OMS else f'Tidak dipakai ({label_bulan(bln_ini)} sudah penuh dan masuk AMS)'); P['C10'].font = INP
        P['D10'] = ('Bulan stok sudah penuh dan penjualannya diupload -> masuk AMS; kolom OMS & DOI incl OMS disembunyikan' if not PAKAI_OMS else
                    'OMS = Net Sales dari Laporan Penjualan pada periode mutasi stok' if OMS_DARI_PENJUALAN else
                    'OMS = ESTIMASI: penjualan bersih (Penjualan Ecer + Retur Penjualan) dari Mutasi Stok x harga per SKU'); P['D10'].font = NOTE
        P['B12'] = 'Gudang yang dihitung sebagai stok'; P['B12'].font = Fn(bold=True)
        hdr(P, 13, 2, ['Kode Gudang', 'Keterangan', 'Hitung stok? (Ya/Tidak)'])
        G0 = 14
        for i, g in enumerate(gl):
            r = G0 + i; P.cell(r, 2, g).font = Fn(); P.cell(r, 3, nama_gud.get(g, '(nama tidak ada di laporan penjualan)')).font = Fn()
            c = P.cell(r, 4, 'Ya' if gflag[g] else 'Tidak'); c.font = INP; c.fill = YEL; c.alignment = Alignment(horizontal='center')
        G1 = G0 + len(gl) - 1
        P['G12'] = 'Standar DOI per principal (hari)'; P['G12'].font = Fn(bold=True)
        hdr(P, 13, 7, ['Principal', 'Standar DOI (hari)', 'Sumber'])
        S0 = 14
        for i, p in enumerate(prins):
            r = S0 + i; P.cell(r, 7, p).font = Fn()
            c = P.cell(r, 8, STANDAR_DOI.get(p, STANDAR_DOI_DEFAULT)); c.font = INP; c.fill = YEL; c.alignment = Alignment(horizontal='center')
            P.cell(r, 9, 'Pengaturan STANDAR_DOI' if p in STANDAR_DOI else 'Standar default').font = NOTE
        S1 = S0 + len(prins) - 1
        widths(P, [2, 44, 34, 24, 16, 3, 24, 18, 26])
        PAR_HK, PAR_N, PAR_MIN = 'Parameter!$C$5', 'Parameter!$C$6', 'Parameter!$C$7'

        # ===== Master SKU =====
        MS = wb.create_sheet('Master SKU'); M0 = 5
        Ms = M.sort_values(['prin', 'kode']).reset_index(drop=True); M1 = M0 + len(Ms) - 1
        MS['A1'] = 'MASTER SKU & OMSET BULANAN'; MS['A1'].font = Fn(bold=True, size=13)
        MS['A2'] = 'Kolom biru = input dari file sumber. Omset = Net Sales (incl. PPN) dijumlah per SKU per bulan. Harga/Sat. Besar = total Rp / total Qty semua bulan data.'; MS['A2'].font = NOTE
        heads = ['Kode', 'Nama Barang', 'Divisi', 'Group', 'Principal', 'Satuan Besar', 'Konversi']
        qc, rc = [], []
        for i, b in enumerate(lbl_ams): qc.append(8 + 2*i); rc.append(9 + 2*i); heads += [f'Qty {b}', f'Rp {b}']
        nxt = 8 + 2*N
        if OMS_DARI_PENJUALAN: oq, orc = nxt, nxt + 1; heads += [f'Qty {lbl_oms}', f'Rp {lbl_oms}']; nxt += 2
        cP, cA = nxt, nxt + 1; heads += ['Harga / Sat. Besar (Rp)', 'AMS (Rp/bulan)']
        hdr(MS, 4, 1, heads, 42)
        qall = qc + ([oq] if OMS_DARI_PENJUALAN else []); rall = rc + ([orc] if OMS_DARI_PENJUALAN else [])
        for i, r in Ms.iterrows():
            x = M0 + i
            base = [r.kode, r.nama, r['div'], r.grp, r.prin, r.sat, r.konv]
            for j, v in enumerate(base, 1): c = MS.cell(x, j, fv(v)); c.font = INP if j == 7 else Fn()
            for b, qcol, rcol in zip(bulan_ams, qc, rc):
                qv = q_m.at[r.kode, b] if (r.kode in q_m.index and b in q_m.columns) else np.nan
                rv = r_m.at[r.kode, b] if (r.kode in r_m.index and b in r_m.columns) else np.nan
                for col, v, fm in ((qcol, qv, '#,##0.00'), (rcol, rv, '#,##0')):
                    c = MS.cell(x, col, None if pd.isna(v) else round(float(v), 4)); c.font = INP; c.number_format = fm
            if OMS_DARI_PENJUALAN:
                for col, ser, fm in ((oq, q_o, '#,##0.00'), (orc, r_o, '#,##0')):
                    v = ser.get(r.kode, np.nan); c = MS.cell(x, col, None if pd.isna(v) else round(float(v), 4)); c.font = INP; c.number_format = fm
            sq = ','.join(f'{L(c)}{x}' for c in qall); sr = ','.join(f'{L(c)}{x}' for c in rall); sa = ','.join(f'{L(c)}{x}' for c in rc)
            MS.cell(x, cP, f'=IF(SUM({sq})>0,SUM({sr})/SUM({sq}),0)').number_format = '#,##0'
            MS.cell(x, cA, f'=SUM({sa})/{PAR_N}').number_format = '#,##0'
            MS.cell(x, cP).font = Fn(); MS.cell(x, cA).font = Fn()
        MS.freeze_panes = 'C5'; widths(MS, [16, 44, 16, 18, 20, 9, 9] + [13]*(2*N + (2 if OMS_DARI_PENJUALAN else 0)) + [16, 16])
        MK = f"'Master SKU'!$A${M0}:$A${M1}"
        mcol = lambda c: f"'Master SKU'!${c if isinstance(c, str) else L(c)}${M0}:${c if isinstance(c, str) else L(c)}${M1}"

        # ===== Data Stok =====
        DS = wb.create_sheet('Data Stok'); D0 = 5
        DS['A1'] = f'DATA STOK & PENJUALAN PER GUDANG (Laporan Mutasi Stok {mut_awal:%d-%m-%Y} s/d {mut_akhir:%d-%m-%Y}, Produk Jadi)'; DS['A1'].font = Fn(bold=True, size=13)
        DS['A2'] = 'Kolom biru = input. Stok Satuan Besar = Besar + Kecil / Konversi. OMS Qty = -(Penjualan Ecer + Retur Penjualan).'; DS['A2'].font = NOTE
        hdr(DS, 4, 1, ['Gudang','Divisi','Kode','Nama Barang','Stok Akhir (Besar)','Stok Akhir (Kecil)','Sat. Besar','Sat. Kecil','Konversi','Stok (Sat. Besar)','Hitung?','Stok Dihitung','Penj. Ecer (Besar)','Penj. Ecer (Kecil)','Retur Jual (Besar)','Retur Jual (Kecil)','OMS Qty (Sat. Besar)'], 42)
        mu = mut.sort_values(['gud', 'kode']).reset_index(drop=True); D1 = D0 + len(mu) - 1
        for i, r in mu.iterrows():
            x = D0 + i
            for j, v in enumerate([r.gud, r['div'], r.kode, r.nama, r.ak_b, r.ak_k, r.sat_b, r.sat_k], 1): DS.cell(x, j, fv(v)).font = INP
            DS.cell(x, 9, f'=IFERROR(INDEX({mcol("G")},MATCH(C{x},{MK},0)),1)').font = Fn()
            DS.cell(x, 10, f'=E{x}+F{x}/I{x}').font = Fn()
            DS.cell(x, 11, f'=IFERROR(INDEX(Parameter!$D${G0}:$D${G1},MATCH(A{x},Parameter!$B${G0}:$B${G1},0)),"Ya")').font = Fn()
            DS.cell(x, 12, f'=IF(K{x}="Ya",J{x},0)').font = Fn()
            for j, v in zip((13, 14, 15, 16), (r.pe_b, r.pe_k, r.rp_b, r.rp_k)): DS.cell(x, j, fv(v)).font = INP
            DS.cell(x, 17, f'=-(M{x}+O{x}+(N{x}+P{x})/I{x})').font = Fn()
            for j in (10, 12, 17): DS.cell(x, j).number_format = '#,##0.00'
        DS.freeze_panes = 'E5'; widths(DS, [14, 16, 16, 44, 11, 11, 8, 8, 9, 13, 8, 13, 11, 11, 11, 11, 14])

        # ===== DOI SKU =====
        SK = wb.create_sheet('DOI SKU'); SK0 = 7; SK1 = SK0 + len(inc) - 1
        oms_txt = '&"   |   OMS = "&Parameter!C10' if PAKAI_OMS else ''
        SK['B2'] = f'CABANG {CABANG.upper()}'; SK['B2'].font = Fn(bold=True, size=13)
        SK['B3'] = (f'="Posisi stok: "&TEXT(Parameter!C4,"dd-mm-yyyy")&"   |   AMS = rata-rata omset "&Parameter!C6&" bulan ({lbl_ams[0]} s/d {lbl_ams[-1]})"{oms_txt}')
        SK['B3'].font = Fn(italic=True)
        hdr(SK, 5, 2, ['PRINCIPAL','KODE','NAMA','STOCK (QTY)','SATUAN','SALDO (Rp)','AMS (Rp/bln)','OMS (Rp)','DOI (HARI)','DOI incl OMS','STANDAR DOI','KETERANGAN','No. Melebihi Standar','idx'], 36)
        for i, (_, r) in enumerate(inc.iterrows()):
            x = SK0 + i
            SK.cell(x, 2, r.prin); SK.cell(x, 3, r.kode)
            SK.cell(x, 15, f'=MATCH(C{x},{MK},0)')
            SK.cell(x, 4, f'=INDEX({mcol("B")},O{x})')
            SK.cell(x, 5, f"=SUMIFS('Data Stok'!$L${D0}:$L${D1},'Data Stok'!$C${D0}:$C${D1},C{x})")
            SK.cell(x, 6, f'=INDEX({mcol("F")},O{x})')
            SK.cell(x, 7, f'=E{x}*INDEX({mcol(cP)},O{x})')
            SK.cell(x, 8, f'=INDEX({mcol(cA)},O{x})')
            if OMS_DARI_PENJUALAN: SK.cell(x, 9, f'=N(INDEX({mcol(orc)},O{x}))')
            elif not PAKAI_OMS: SK.cell(x, 9, 0)
            else: SK.cell(x, 9, f"=SUMIFS('Data Stok'!$Q${D0}:$Q${D1},'Data Stok'!$C${D0}:$C${D1},C{x})*INDEX({mcol(cP)},O{x})")
            SK.cell(x, 10, f'=IF(H{x}>{PAR_MIN},MAX(G{x},0)/(H{x}/{PAR_HK}),"")')
            SK.cell(x, 11, f'=IF((H{x}*{PAR_N}+I{x})/({PAR_N}+1)>{PAR_MIN},MAX(G{x},0)/(((H{x}*{PAR_N}+I{x})/({PAR_N}+1))/{PAR_HK}),"")')
            SK.cell(x, 12, f'=INDEX(Parameter!$H${S0}:$H${S1},MATCH(B{x},Parameter!$G${S0}:$G${S1},0))')
            SK.cell(x, 13, f'=IF(AND(INDEX({mcol(cP)},O{x})=0,OR(E{x}<>0,I{x}<>0)),"Harga tidak tersedia (tidak terjual di bulan data) - saldo Rp belum dihitung",IF(AND(H{x}<={PAR_MIN},E{x}>0),"Tidak ada penjualan, stok ada",""))')
            SK.cell(x, 14, f'=IF(ISNUMBER(J{x}),IF(J{x}>L{x}+5,IF(B{x}=B{x-1},N{x-1}+1,1),0),0)')
            for j in range(2, 16): SK.cell(x, j).font = Fn()
            for j, fm in ((5,'#,##0.00'),(7,'#,##0'),(8,'#,##0'),(9,'#,##0'),(10,'#,##0.0'),(11,'#,##0.0'),(12,'0')): SK.cell(x, j).number_format = fm
        SK.freeze_panes = 'E7'; widths(SK, [2, 22, 16, 44, 12, 8, 16, 15, 15, 11, 11, 9, 50, 12, 8]); SK.auto_filter.ref = f'B5:O{SK1}'
        SKB = f"'DOI SKU'!$B${SK0}:$B${SK1}"; sk = lambda c: f"'DOI SKU'!${c}${SK0}:${c}${SK1}"

        # ===== DOI Principal =====
        PR = wb.create_sheet('DOI Principal')
        PR['B2'] = f'CABANG {CABANG.upper()}'; PR['B2'].font = Fn(bold=True, size=13)
        PR['B3'] = '="Posisi stok: "&TEXT(Parameter!C4,"dd-mm-yyyy")&"  |  AMS = rata-rata omset "&Parameter!C6&" bulan"' + ('&"  |  OMS = "&Parameter!C10' if PAKAI_OMS else ''); PR['B3'].font = Fn(italic=True)
        hdr(PR, 5, 2, ['PRINCIPAL','SKU','SALDO STOCK (Rp)','AMS (Rp/bln)','OMS (Rp)','DOI (HARI)','DOI incl OMS','STANDAR DOI','+/- vs STANDAR (Rp)','SKU STOK TANPA HARGA*'], 36)
        dg = lambda x: f'=IFERROR(IF(E{x}>0,MAX(D{x},0)/(E{x}/{PAR_HK}),""),"")'
        di = lambda x: f'=IFERROR(IF((E{x}*{PAR_N}+F{x})>0,MAX(D{x},0)/(((E{x}*{PAR_N}+F{x})/({PAR_N}+1))/{PAR_HK}),""),"")'
        for i, p in enumerate(prins):
            x = 7 + i
            PR.cell(x, 2, p); PR.cell(x, 3, f'=COUNTIF({SKB},B{x})')
            for col, c in ((4, 'G'), (5, 'H'), (6, 'I')): PR.cell(x, col, f'=SUMIFS({sk(c)},{SKB},B{x})')
            PR.cell(x, 7, dg(x)); PR.cell(x, 8, di(x))
            PR.cell(x, 9, f'=INDEX(Parameter!$H${S0}:$H${S1},MATCH(B{x},Parameter!$G${S0}:$G${S1},0))')
            PR.cell(x, 10, f'=IF(ISNUMBER(G{x}),(G{x}-I{x})*E{x}/{PAR_HK},"")')
            PR.cell(x, 11, f'=COUNTIFS({SKB},B{x},{sk("M")},"Harga tidak*",{sk("E")},">0")')
        PRe = 7 + len(prins) - 1; T = PRe + 1
        PR.cell(T, 2, 'TOTAL')
        for c in 'CDEFJK': PR[f'{c}{T}'] = f'=SUM({c}7:{c}{PRe})'
        PR[f'G{T}'] = dg(T); PR[f'H{T}'] = di(T)
        for x in range(7, T + 1):
            for j in range(2, 12):
                c = PR.cell(x, j); c.font = Fn(bold=(x == T))
                if x == T: c.fill = GR
            for j, fm in ((3,'#,##0'),(4,'#,##0'),(5,'#,##0'),(6,'#,##0'),(7,'#,##0.0'),(8,'#,##0.0'),(9,'0'),(10,'#,##0;(#,##0);-'),(11,'#,##0')): PR.cell(x, j).number_format = fm
        PR.cell(T+2, 2, '+/- vs Standar = (DOI - Standar) x AMS / hari kerja. Positif = kelebihan stok (Rp) di atas standar; negatif = kekurangan.').font = NOTE
        PR.cell(T+3, 2, '* SKU yang ada stoknya tetapi tidak terjual di bulan data omset: tidak ada harga, sehingga Saldo Rp-nya terhitung 0 (Saldo Rp cenderung lebih rendah dari nilai sebenarnya).').font = Fn(italic=True, color='C00000')
        widths(PR, [2, 24, 8, 19, 17, 17, 11, 13, 11, 19, 16]); PR.freeze_panes = 'C7'

        # ===== DOI Principal (2) =====
        P2 = wb.create_sheet('DOI Principal (2)')
        P2['B2'] = f'CABANG {CABANG.upper()}'; P2['B2'].font = Fn(bold=True, size=13)
        P2['B3'] = '="Jumlah SKU / Rentang DOI - posisi "&TEXT(Parameter!C4,"dd-mm-yyyy")'; P2['B3'].font = Fn(italic=True)
        hdr(P2, 5, 2, ['PRINCIPAL','STANDAR DOI','< 14','14 - 30','30 - 60','60 - 180','180 - 365','> 365','AMS Min','AMS 0, Stock >0','AMS>0, Stock 0'], 36)
        rng = [(0, 14), (14, 30), (30, 60), (60, 180), (180, 365), (365, None)]
        for i, p in enumerate(prins):
            x = 7 + i
            P2.cell(x, 2, p); P2.cell(x, 3, f'=INDEX(Parameter!$H${S0}:$H${S1},MATCH(B{x},Parameter!$G${S0}:$G${S1},0))')
            for j, (lo, hi) in enumerate(rng):
                P2.cell(x, 4 + j, f'=COUNTIFS({SKB},$B{x},{sk("J")},">="&{lo}' + (f',{sk("J")},"<"&{hi})' if hi else ')'))
            P2.cell(x, 10, f'=COUNTIFS({SKB},$B{x},{sk("H")},"<="&{PAR_MIN})')
            P2.cell(x, 11, f'=COUNTIFS({SKB},$B{x},{sk("H")},"<="&{PAR_MIN},{sk("E")},">0")')
            P2.cell(x, 12, f'=COUNTIFS({SKB},$B{x},{sk("H")},">"&{PAR_MIN},{sk("E")},"<=0")')
        T2 = 7 + len(prins); P2.cell(T2, 2, 'TOTAL')
        for j in range(4, 13): P2.cell(T2, j, f'=SUM({L(j)}7:{L(j)}{T2-1})')
        for x in range(7, T2 + 1):
            for j in range(2, 13):
                c = P2.cell(x, j); c.font = Fn(bold=(x == T2))
                if x == T2: c.fill = GR
                if j > 2: c.alignment = Alignment(horizontal='center')
        P2.cell(T2+2, 2, 'Rentang DOI memakai kolom DOI (hari) di DOI SKU. AMS Min = SKU dengan AMS <= ambang (termasuk AMS 0); jumlah rentang + AMS Min = total SKU.').font = NOTE
        widths(P2, [2, 24, 12, 9, 9, 9, 9, 10, 9, 11, 15, 15])

        # ===== Catatan (disusun otomatis dari data & pengaturan) =====
        C = wb.create_sheet('Catatan'); C['B2'] = 'CATATAN, ASUMSI & SUMBER DATA (disusun otomatis dari data yang diupload)'; C['B2'].font = Fn(bold=True, size=13)
        TXT = []
        add = lambda t='', g='n': TXT.append((t, g))
        bln_txt = label_bulan(bln_ini)
        add(f'Dibuat {dt.datetime.now():%d-%m-%Y %H:%M} | Cabang: {CABANG} | Posisi stok: {mut_akhir:%d-%m-%Y}')
        add()
        if PERINGATAN:
            add('PERINGATAN DATA - PERIKSA DULU', 'w')
            for w_ in PERINGATAN: add('- ' + w_.replace('!! PERINGATAN: ', '').replace('!! ', ''), 'w')
            add()
        add('FILE YANG DIPAKAI', 'h')
        for f_, r_ in rg.iterrows():
            bl_ = sorted(sales.loc[sales['file'] == f_, 'bulan'].unique())
            peran = ', '.join(f"{label_bulan(b)}: " + ('AMS' if b in bulan_ams else ('OMS' if (PAKAI_OMS and b == bln_ini) else 'tidak dipakai')) for b in bl_)
            add(f"- Penjualan: {f_} | {r_['min']:%d-%m-%Y} s/d {r_['max']:%d-%m-%Y} | {int(r_['count']):,} baris | Rp {rp_file[f_]/1e9:,.2f} M | {peran}")
        add(f"- Mutasi stok: {os.path.basename(F_MUT[0])} | {mut_awal:%d-%m-%Y} s/d {mut_akhir:%d-%m-%Y} | {len(mut):,} baris produk jadi")
        add(f"- Daftar barang: {os.path.basename(F_DAFTAR[0])} (konversi satuan, Divisi, Group)")
        add()
        add('BULAN APA YANG DIHITUNG SEBAGAI AMS & OMS', 'h')
        add(f"- AMS = rata-rata omset bulanan dari {N} bulan: {', '.join(lbl_ams)}." + (f" (dibatasi {MAKS_BULAN_AMS} bulan terakhir)" if MAKS_BULAN_AMS else ' (semua bulan penjualan yang tersedia sebelum/hingga bulan stok)'))
        if BLN_INI_MASUK_AMS:
            add(f"- Posisi stok {mut_akhir:%d-%m-%Y} adalah akhir bulan dan penjualan {bln_txt} sudah diupload, jadi {bln_txt} dianggap bulan PENUH dan ikut AMS. Kolom OMS & DOI incl OMS tidak dipakai (disembunyikan).")
        elif OMS_DARI_PENJUALAN:
            add(f"- {bln_txt} adalah bulan berjalan (stok per {mut_akhir:%d-%m-%Y}, belum akhir bulan atau diatur 'tidak') sehingga tidak masuk AMS. Penjualannya ({mut_awal:%d-%m} s/d {mut_akhir:%d-%m}) dipakai sebagai OMS.")
        else:
            add(f"- Penjualan {bln_txt} TIDAK diupload. OMS hanya ESTIMASI: qty dari Mutasi Stok = -(Penjualan Ecer + Retur Penjualan), dikali harga rata-rata per SKU dari bulan AMS. Upload penjualan {bln_txt} untuk angka sebenarnya.")
        add(f"- Pengaturan BULAN_STOK_MASUK_AMS = '{BULAN_STOK_MASUK_AMS}' ('auto' = otomatis; 'ya' = selalu masuk AMS; 'tidak' = selalu jadi OMS).")
        add()
        add('RUMUS (versi sederhana)', 'h')
        add(f"- AMS = total Net Sales (incl. PPN) {N} bulan / {N}. Itu kecepatan jual normal per bulan.")
        add("- Harga per satuan besar = total Rp / total Qty Sales per SKU. Saldo stok (Rp) = stok x harga (nilai jual, bukan HPP).")
        add(f"- DOI (hari) = Saldo / (AMS / {HARI_KERJA}) = berapa hari stok sekarang cukup bila terjual secepat AMS.")
        if PAKAI_OMS:
            add(f"- OMS = penjualan {bln_txt} sejauh ini (s/d {mut_akhir:%d-%m}). DOI incl OMS = DOI bila {bln_txt} ikut dihitung: rata-rata = (AMS x {N} + OMS) / {N + 1}. Dipakai untuk melihat apakah penjualan bulan berjalan menyimpang dari biasanya.")
        add()
        add('PENGATURAN YANG DIPAKAI', 'h')
        add(f"- Hari kerja {HARI_KERJA} | ambang AMS minimum Rp {AMBANG_AMS_MIN:,} | standar DOI default {STANDAR_DOI_DEFAULT} hari | khusus: " + (', '.join(f'{p_} {v_} hari' for p_, v_ in STANDAR_DOI.items()) or '-'))
        add(f"- Pemetaan principal: Group {PRINCIPAL_BY_GROUP}; Divisi {PRINCIPAL_BY_DIVISI}; lainnya memakai nama Divisi apa adanya.")
        add(f"- Group dikeluarkan dari laporan: {', '.join(GROUP_DIKECUALIKAN) or '-'} ({int(M.grp.isin(GROUP_DIKECUALIKAN).sum())} SKU); barang tipe selain Produk Jadi (mis. Embalase) tidak dibaca.")
        add()
        add('GUDANG', 'h')
        add(f"- Stok dihitung dari {sum(gflag.values())} gudang. Tidak dihitung: " + ('; '.join(f"{g_} ({nama_gud.get(g_, '?')})" for g_ in gl if not gflag[g_]) or 'tidak ada') + ". Ubah Ya/Tidak di sheet Parameter, semua angka ikut berubah.")
        _tn = [g_ for g_ in gl if g_ not in nama_gud]
        if _tn: add(f"- Gudang tanpa nama di laporan penjualan (dihitung sebagai stok): {', '.join(_tn)}")
        add()
        add('KUALITAS DATA', 'h')
        _tp = int(((inc.harga == 0) & (inc.stok > 0)).sum()); _n0 = int(((inc.ams <= AMBANG_AMS_MIN) & (inc.stok > 0)).sum())
        add(f"- {len(inc):,} SKU masuk laporan. {_tp:,} SKU punya stok tetapi tidak punya harga (tidak terjual di bulan data) -> saldo Rp = 0, jadi total saldo cenderung lebih rendah dari nilai sebenarnya. {_n0:,} SKU stok ada tetapi AMS <= ambang.")
        _z = s_pakai[(s_pakai['Qty Sales'] == 0) & (s_pakai['Net Sales (incl. PPN)'] > 0)]; _tot = s_pakai['Net Sales (incl. PPN)'].sum()
        if len(_z): add(f"- {len(_z):,} baris penjualan bulan AMS berqty 0.00 tetapi ada Rp (pembulatan 2 desimal pada penjualan eceran): Rp {_z['Net Sales (incl. PPN)'].sum()/1e9:,.2f} M atau {_z['Net Sales (incl. PPN)'].sum()/_tot:.1%} dari omset. Harga per satuan besar bisa sedikit lebih tinggi untuk SKU yang banyak dijual eceran.")
        for w_ in PERINGATAN:
            if 'MINUS' in w_: pass
        STY = {'h': Fn(bold=True), 'w': Fn(bold=True, color='C00000'), 'n': Fn()}
        for i_, (t_, g_) in enumerate(TXT): C.cell(4 + i_, 2, t_).font = STY[g_]
        C.column_dimensions['B'].width = 190
        if not PAKAI_OMS:
            SK.column_dimensions['I'].hidden = True; SK.column_dimensions['K'].hidden = True
            PR.column_dimensions['F'].hidden = True; PR.column_dimensions['H'].hidden = True
        wb._sheets = [wb[n] for n in ['DOI Principal','DOI Principal (2)','DOI SKU','Master SKU','Data Stok','Parameter','Catatan']]
        wb.active = 0; wb.calculation.fullCalcOnLoad = True

        os.makedirs(output_dir, exist_ok=True)
        out_name = f"Laporan_DOI_{re.sub(r'[^A-Za-z0-9]+','_',CABANG)}_{mut_akhir:%d%b%Y}.xlsx"
        OUT = os.path.join(output_dir, out_name)
        wb.save(OUT); print('File tersimpan:', OUT)

        # ==== SEL 5: RINGKASAN ====
        rk = inc.groupby('prin').agg(SKU=('kode','count'), Saldo_Rp=('saldo','sum'), AMS_Rp=('ams','sum'), OMS_Rp=('oms_rp','sum')).reindex(prins)
        rk['DOI_hari'] = np.where(rk.AMS_Rp > 0, rk.Saldo_Rp.clip(lower=0) / (rk.AMS_Rp / HARI_KERJA), np.nan)
        rk['Standar'] = [STANDAR_DOI.get(p, STANDAR_DOI_DEFAULT) for p in rk.index]
        rk['Lebih/Kurang_Rp'] = (rk.DOI_hari - rk.Standar) * rk.AMS_Rp / HARI_KERJA
        rk['SKU_stok_tanpa_harga'] = inc[(inc.harga == 0) & (inc.stok > 0)].groupby('prin').size().reindex(prins).fillna(0).astype(int)
        rk.loc['TOTAL'] = [rk.SKU.sum(), rk.Saldo_Rp.sum(), rk.AMS_Rp.sum(), rk.OMS_Rp.sum(),
                           rk.Saldo_Rp.clip(lower=0).sum() / (rk.AMS_Rp.sum() / HARI_KERJA), np.nan, rk['Lebih/Kurang_Rp'].sum(), rk.SKU_stok_tanpa_harga.sum()]
        if not PAKAI_OMS: rk = rk.drop(columns=['OMS_Rp'])
        print(f"Ringkasan DOI - cabang {CABANG} | AMS {N} bulan ({lbl_ams[0]} s/d {lbl_ams[-1]}) | stok per {mut_akhir:%d-%m-%Y}")

    return {
        "out_path": OUT,
        "out_name": out_name,
        "summary_df": rk,
        "logs": log_stream.getvalue(),
        "cabang": CABANG,
        "sku_count": len(inc),
        "ams_months": f"{lbl_ams[0]} s/d {lbl_ams[-1]} ({N} bln)",
        "peringatan": PERINGATAN,
        "oms_mode": ("Bulan stok masuk AMS (OMS tidak dipakai)" if not PAKAI_OMS else ("OMS dari Laporan Penjualan" if OMS_DARI_PENJUALAN else "OMS estimasi dari Mutasi Stok"))
    }