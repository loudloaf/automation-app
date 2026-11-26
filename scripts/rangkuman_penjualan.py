# scripts/rangkuman_penjualan.py
import os, re, io, zipfile, warnings, contextlib
import numpy as np
import pandas as pd
from scripts.excel_utils import pastikan_xlsx
import openpyxl
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.chart import BarChart, Reference
from openpyxl.worksheet.properties import PageSetupProperties
from openpyxl.utils import get_column_letter
import gspread
from gspread.exceptions import WorksheetNotFound
from gspread.utils import rowcol_to_a1
from google.auth import default as google_auth_default
from google.oauth2.service_account import Credentials

warnings.filterwarnings('ignore')

# ==============================================================================
# SEL 1-2: KONFIGURASI (100% Sama dengan Colab)
# ==============================================================================
NAMA_CABANG_ORLAN = {'BB': 'Sempidi', 'BF': 'Negara', 'BK': 'Sokong', 'BL': 'Panji', 'BM': 'Mengwi'}
KODE_CABANG_ZETA = {'NSD': 'Nusa Dua', 'KLK': 'Klungkung', 'SGR': 'Singaraja',
                    'MTR': 'Mataram', 'PRY': 'Praya', 'CRG': 'Cargo', 'Cargo': 'Cargo'}
NAMA_CABANG_ZETA = 'Nusa Dua'

OMSET_BASIS = 'Net'
KECUALIKAN_GUDANG_GRATIS = True
KECUALIKAN_NILAI_NOL     = True
KECUALIKAN_LUAR_PERIODE  = True
TOLERANSI_HARGA_UNIT     = 0.05

NICKNAME = {
    'MBI': 'Bintang', 'IBN': 'Mayora', 'FFI': 'Susu Bendera', 'BWI': 'Pronas', 'ABC': 'Nu Green Tea',
    'SATP': 'Sovia', 'BDY': 'Bandulan', 'OWI': 'Oasis', 'UCI': 'Unicharm', 'MTI': 'Motasa',
    'SLM': 'Garam', 'EPM': 'Sun Kara', 'SWT': 'Pristine', 'KMI': 'Zoda', 'KDM': 'Camel',
    'CCOD': 'Coca-Cola', 'FRI': 'Fokus Ritel', 'AKD': 'Kin', 'KINO': 'Kino', 'MALEE': 'Malee',
    'LBP': 'Wangs', 'CBN': 'Umma', 'SLN': 'AMDK',
}

UNIT_MAP = {
    'CAR': 'CTN', 'CTN': 'CTN', 'CS': 'CTN',
    'CR': 'CRT', 'CRT': 'CRT',
    'PCS': 'PCS', 'PC': 'PCS',
    'PAK': 'PACK', 'PAC': 'PACK', 'PACK': 'PACK',
    'BRL': 'BRL', 'BARREL': 'BRL',
    'SCH': 'SCH', 'PCH': 'PCH', 'BKS': 'BKS', 'ZAK': 'ZAK', 'STK': 'STK', 'RCG': 'RCG',
    'BAG': 'BAG', 'ROL': 'ROL', 'JRG': 'JRG', 'BOX': 'BOX', 'JAR': 'JAR', 'KLG': 'KLG', 'TUBE': 'TUBE',
}

BULAN_PANJANG = ['JANUARI','FEBRUARI','MARET','APRIL','MEI','JUNI','JULI','AGUSTUS','SEPTEMBER','OKTOBER','NOVEMBER','DESEMBER']
BULAN_SINGKAT = ['JAN','FEB','MAR','APR','MEI','JUN','JUL','AGU','SEP','OKT','NOV','DES']

# Konfigurasi Google Sheets (Sel 10, 10b, 11, 11c)
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1TF1pqnT4Ok6Rma43YJiJicMxUujzIWPqkeNT7GmT2bA/edit"
SPREADSHEET_PENDUKUNG_URL = "https://docs.google.com/spreadsheets/d/1vPqhOCbmrqFW8TqxOfzEfK38AE7tdhm8tKGEDcG7h-8/edit?gid=0#gid=0"
NAMA_KOLOM_BULAN = ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun', 'Jul', 'Agt', 'Sep', 'Okt', 'Nov', 'Des']
MIN_HARI_BULAN_LAIN = 10
OMSET_BERSIH = True
DAFTAR_CABANG = ["Sempidi", "Singaraja", "Cargo", "Klungkung", "Nusa Dua", "Negara", "Panji", "Mengwi", "Mataram", "Praya", "Sokong"]
CABANG_WAJIB = ["Sempidi", "Singaraja", "Cargo", "Klungkung", "Nusa Dua", "Negara", "Panji", "Mengwi", "Mataram", "Praya", "Sokong"]
LIBUR_MANUAL = {}
WD_SETAHUN_MANUAL = None
HARI_ACUAN = 'terakhir'

_HARI = ['Senin', 'Selasa', 'Rabu', 'Kamis', 'Jumat', 'Sabtu', 'Minggu']
_BLN = ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun', 'Jul', 'Agt', 'Sep', 'Okt', 'Nov', 'Des']
_BLN_NAMA = ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun', 'Jul', 'Agt', 'Sep', 'Okt', 'Nov', 'Des']
_KATA_STATUS = {'KERJA', 'LIBUR', 'ESTIMASI'}

# ==============================================================================
# SEL 3: FUNGSI MASTER SUPPLIER, PEMBACA FILE, PEMBERSIHAN
# ==============================================================================
def deteksi_file(path):
    pastikan_xlsx(path)  # dukung .xls/HTML/CSV yang menyamar sebagai .xlsx
    with open(path, 'rb') as fh:
        buf = io.BytesIO(fh.read())
    wb = load_workbook(buf, read_only=True, data_only=True)
    try:
        sheets = [s.lower() for s in wb.sheetnames]
        if 'rekap' in sheets and 'per cabang' in sheets:
            return 'SUPPLIER'
        baris = list(wb.worksheets[0].iter_rows(min_row=1, max_row=6, values_only=True))
    finally:
        wb.close()
    teks = ' '.join(str(c) for r in baris for c in r if c is not None)
    if 'EntityID_' in teks and 'No_SI' in teks:
        return 'ORLAN'
    if 'Laporan Rincian Penjualan' in teks:
        return 'ZETA'
    return 'TIDAK DIKENAL'

def teks_bersih(s):
    return (s.fillna('').astype(str)
             .str.replace(r'_x000D_|\r|\n', ' ', regex=True)
             .str.replace(r'\s+', ' ', regex=True).str.strip().str.upper())

def angka(s):
    return pd.to_numeric(s, errors='coerce').fillna(0.0)

def baca_supplier(path):
    pastikan_xlsx(path)
    with open(path, 'rb') as fh:
        buf = io.BytesIO(fh.read())
    with pd.ExcelFile(buf) as xl:
        rekap = pd.read_excel(xl, sheet_name='Rekap', header=2, dtype=str).iloc[:, 1:5]
        percab = pd.read_excel(xl, sheet_name='Per Cabang', header=1, dtype=str).iloc[:, :5]
    rekap.columns = ['KodeSupp', 'Supp', 'KodeGrup', 'NamaGrup']
    rekap = rekap[rekap['KodeSupp'].fillna('').str.fullmatch(r'\d+')].copy()
    for c in rekap.columns:
        rekap[c] = rekap[c].astype(str).str.strip()
    percab.columns = ['Cabang', 'KodeGrup', 'NamaGrup', 'KodeSupp', 'Supp']
    percab = percab.dropna(subset=['KodeSupp'])
    for c in percab.columns:
        percab[c] = percab[c].astype(str).str.strip()
    prin = rekap.drop_duplicates('KodeSupp')[['KodeSupp', 'Supp']].reset_index(drop=True)
    namagrup = rekap.drop_duplicates('KodeSupp').set_index('KodeSupp')['NamaGrup'].to_dict()
    prin['Label'] = [f"{s} ({NICKNAME.get(s, str(namagrup.get(k, s)).title())})"
                     for k, s in zip(prin.KodeSupp, prin.Supp)]
    return {'rekap': rekap, 'percab': percab, 'prin': prin,
            'label': prin.set_index('KodeSupp')['Label'].to_dict(),
            'supp': prin.set_index('KodeSupp')['Supp'].to_dict()}

def cabang_zeta(path):
    nama_file = os.path.basename(path).upper()
    for kode in KODE_CABANG_ZETA:
        if kode in nama_file:
            return KODE_CABANG_ZETA[kode]
    if 'CARGO' in nama_file:
        return 'Cargo'
    print(f'  PERINGATAN: kode cabang tidak dikenal di nama file {os.path.basename(path)}; '
          f'dipakai "{NAMA_CABANG_ZETA}". Tambahkan di KODE_CABANG_ZETA (sel 2).')
    return NAMA_CABANG_ZETA

def baca_zeta(path):
    pastikan_xlsx(path)
    raw = pd.read_excel(path, header=None, dtype=object)
    h = raw.index[raw[0].astype(str).str.strip().str.lower() == 'salesman'][0]
    df = raw.iloc[h + 1:].reset_index(drop=True)
    df.columns = [str(c).strip() for c in raw.iloc[h]]
    df = df.dropna(how='all')
    return pd.DataFrame({
        'Sumber': 'ZETA', 'Cabang': cabang_zeta(path),
        'Tanggal': pd.to_datetime(df['Tanggal Faktur'], errors='coerce'),
        'NoFaktur': df['No Faktur'], 'KodeCust': df['Kode Customer'], 'Customer': df['Customer'],
        'Alamat': df['Alamat'], 'Wilayah': df['Wilayah'], 'Salesman': df['Salesman'],
        'KodeBarang': df['Kode Barang'], 'NamaBarang': df['Nama Barang'],
        'KodeGrup': df['Kode Grup Barang'], 'NamaGrup': df['Nama Grup Barang'],
        'SuppAsli': np.nan, 'GrupSuppAsli': np.nan,
        'Unit_Asli': df['Satuan'], 'Qty': angka(df['Qty Sales']), 'Bonus': angka(df['Qty Bonus']),
        'Gross': angka(df['Gross Sales (incl. PPN)']), 'Diskon': angka(df['Discount (incl. PPN)']),
        'Net': angka(df['Net Sales (incl. PPN)']), 'DPP': angka(df['DPP']), 'PPN': angka(df['PPN']),
        'Gudang': df['Nama Gudang'], 'Pembayaran': df['Jenis Pembayaran'], 'Batal': 0,
    }).reset_index(drop=True)

def baca_orlan(path):
    pastikan_xlsx(path)
    pakai = {'EntityID_','No_SI','SI_Date','ItemID','ItemDesc','SuppID','SalesName','CustID','CustName',
             'Approved','Void','ItemGroupID','ItemGroupDesc','LocationDesc','Qty','Bonus_','UnitID',
             'GrossAmt','DiscAmt','NetAmt','DPP','PPN','KodeAreaDesc','Address','JenisPembayaran1'}
    df = pd.read_excel(path, usecols=lambda c: c in pakai)
    ent = df['EntityID_'].astype(str).str.strip().str.upper()
    return pd.DataFrame({
        'Sumber': 'ORLAN', 'Cabang': ent.map(NAMA_CABANG_ORLAN).fillna('ENTITY ' + ent),
        'Tanggal': pd.to_datetime(df['SI_Date'], errors='coerce'),
        'NoFaktur': df['No_SI'], 'KodeCust': df['CustID'], 'Customer': df['CustName'],
        'Alamat': df['Address'], 'Wilayah': df['KodeAreaDesc'], 'Salesman': df['SalesName'],
        'KodeBarang': df['ItemID'], 'NamaBarang': df['ItemDesc'],
        'KodeGrup': df['ItemGroupID'], 'NamaGrup': df['ItemGroupDesc'],
        'SuppAsli': df['SuppID'], 'GrupSuppAsli': df['ItemGroupDesc'],
        'Unit_Asli': df['UnitID'], 'Qty': angka(df['Qty']), 'Bonus': angka(df['Bonus_']),
        'Gross': angka(df['GrossAmt']), 'Diskon': angka(df['DiscAmt']), 'Net': angka(df['NetAmt']),
        'DPP': angka(df['DPP']), 'PPN': angka(df['PPN']),
        'Gudang': df['LocationDesc'], 'Pembayaran': df['JenisPembayaran1'],
        'Batal': ((angka(df['Void']) != 0) | (angka(df['Approved']) != 1)).astype(int),
    }).reset_index(drop=True)

def _catat(log, pemeriksaan, jumlah, tindakan):
    log.append({'Pemeriksaan': pemeriksaan, 'Jumlah baris': int(jumlah), 'Tindakan': tindakan})

def bersihkan(df, master):
    log = []
    n_awal = len(df)
    _catat(log, 'Jumlah baris awal', n_awal, '-')
    for c in ['NoFaktur','KodeCust','Customer','Alamat','Wilayah','Salesman','KodeBarang','NamaBarang',
              'NamaGrup','Unit_Asli','Gudang','Pembayaran','Cabang']:
        asli = df[c].fillna('').astype(str)
        rapi = asli.str.replace(r'_x000D_|\r|\n', ' ', regex=True).str.replace(r'\s+', ' ', regex=True).str.strip()
        n_kotor = (asli != rapi).sum()
        df[c] = teks_bersih(df[c])
        if n_kotor:
            _catat(log, f'Teks kotor di kolom {c} (_x000D_, enter, spasi ganda/spasi ujung)', n_kotor, 'Dirapikan')
    df['KodeCust'] = df['KodeCust'].str.replace(r'\.0$', '', regex=True)
    df['KodeBarang'] = df['KodeBarang'].str.replace(r'\.0$', '', regex=True)
    df['KodeGrup'] = df['KodeGrup'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip().str.upper()

    bad = df['Tanggal'].isna()
    _catat(log, 'Tanggal tidak valid (mis. baris total/footer)', bad.sum(), 'Dibuang')
    df = df[~bad].copy()

    dup = df.duplicated()
    _catat(log, 'Baris duplikat persis', dup.sum(), 'Dibuang')
    df = df[~dup].copy()

    _catat(log, 'Void / belum Approved', (df['Batal'] == 1).sum(), 'Dibuang')
    df = df[df['Batal'] == 0].copy()

    per = df['Tanggal'].dt.to_period('M')
    periode = per.mode()[0]
    df['LuarPeriode'] = per != periode
    _catat(log, f'Tanggal di luar periode utama ({periode})', df['LuarPeriode'].sum(),
           'Dikeluarkan dari laporan' if KECUALIKAN_LUAR_PERIODE else 'Dibiarkan')

    if df['Sumber'].iloc[0] == 'ORLAN':
        df['KodeSupp'] = df['SuppAsli'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
        lbl = df['GrupSuppAsli'].fillna('').astype(str).str.split().str[-1].str.upper()
        ref = df['KodeSupp'].map(master['supp']).fillna('?').str.upper()
        beda = (lbl != ref)
        _catat(log, 'Label ItemGroupDesc tidak cocok dengan kode SuppID menurut Supplier.xlsx '
                    '(mis. CEP vs CCOD, SAP vs SATP, BDD vs BDY, 2101025/26 berlabel MTI)',
               beda.sum(), 'Principal ditentukan dari SuppID + Supplier.xlsx')
    else:
        pc = master['percab']
        pc = pc[pc['Cabang'].str.upper() == df['Cabang'].iloc[0]]
        peta_cab = pc.drop_duplicates('KodeGrup').set_index('KodeGrup')['KodeSupp'].to_dict()
        peta_rek = master['rekap'].drop_duplicates('KodeGrup').set_index('KodeGrup')['KodeSupp'].to_dict()
        df['KodeSupp'] = df['KodeGrup'].map(peta_cab)
        pakai_rekap = df['KodeSupp'].isna()
        df.loc[pakai_rekap, 'KodeSupp'] = df.loc[pakai_rekap, 'KodeGrup'].map(peta_rek)
        _catat(log, 'Kode grup barang tidak ada di sheet Per Cabang (dipetakan lewat sheet Rekap)',
               (pakai_rekap & df['KodeSupp'].notna()).sum(), 'Dipetakan via Rekap')
    tak = ~df['KodeSupp'].isin(master['label'])
    _catat(log, 'Kode supplier tidak ditemukan di Supplier.xlsx', tak.sum(),
           'Diberi label "TIDAK ADA DI MASTER" (cek Supplier.xlsx)')
    df['KodeSupp'] = df['KodeSupp'].fillna('TIDAK ADA')
    df['Principal'] = df['KodeSupp'].map(master['label']).fillna('TIDAK ADA DI MASTER')

    df['Unit'] = df['Unit_Asli'].map(UNIT_MAP).fillna(df['Unit_Asli'])
    _catat(log, 'UnitID/Satuan berbeda penulisan (CAR/CTN/CS, PC/PCS, PAK/PAC/PACK, BRL/BARREL, CR/CRT)',
           (df['Unit'] != df['Unit_Asli']).sum(), 'Diseragamkan ke kode standar (lihat UNIT_MAP)')
    df['Harga'] = np.where(df['Qty'] != 0, (df['Gross'] / df['Qty']).abs(), 0.0)
    g = df.groupby(['KodeBarang', 'Unit']).agg(n=('Qty', 'size'), h=('Harga', 'median')).reset_index()
    dom = (g.sort_values(['KodeBarang', 'n'], ascending=[True, False]).drop_duplicates('KodeBarang')
             .rename(columns={'Unit': 'UnitDominan', 'h': 'HargaDominan'})[['KodeBarang', 'UnitDominan', 'HargaDominan']])
    df = df.merge(dom, on='KodeBarang', how='left')
    beda = df['Unit'] != df['UnitDominan']
    mirip = beda & (df['HargaDominan'] > 0) & ((df['Harga'] / df['HargaDominan'] - 1).abs() <= TOLERANSI_HARGA_UNIT)
    df.loc[mirip, 'Unit'] = df.loc[mirip, 'UnitDominan']
    _catat(log, 'Satuan salah label (harga/unit sama dengan satuan dominan barang tsb)', mirip.sum(),
           'Dikoreksi ke satuan dominan barang')
    df['FlagUnitBeda'] = df['Unit'] != df['UnitDominan']
    _catat(log, 'Barang yang sama dijual dengan satuan berbeda & harga berbeda (mis. CTN vs PCS)',
           df['FlagUnitBeda'].sum(), 'Dibiarkan (qty bisa jadi memang pcs), diberi FlagUnitBeda=True. Mohon cek manual')

    df['Jenis'] = np.where((df['Qty'] < 0) | (df['Net'] < 0), 'RETUR', 'PENJUALAN')
    _catat(log, 'Baris RETUR (qty/nilai negatif)', (df['Jenis'] == 'RETUR').sum(), 'Dipisahkan ke kolom Retur')

    df['Gratis'] = df['Gudang'].str.contains(r'GRATIS|FREE', regex=True)
    _catat(log, 'Transaksi dari gudang GRATIS / FREE', df['Gratis'].sum(),
           'Dikeluarkan dari laporan' if KECUALIKAN_GUDANG_GRATIS else 'Dibiarkan')
    df['NilaiNol'] = (df['Net'] == 0)
    _catat(log, 'Baris bernilai Net = 0', df['NilaiNol'].sum(),
           'Dikeluarkan dari laporan' if KECUALIKAN_NILAI_NOL else 'Dibiarkan')

    _catat(log, 'Baris dengan DPP + PPN != Net (selisih > Rp1)', ((df['DPP'] + df['PPN'] - df['Net']).abs() > 1).sum(),
           'Informasi saja. Omset memakai kolom ' + ('Net' if OMSET_BASIS == 'Net' else 'DPP'))
    _catat(log, 'Pelanggan dengan >1 nama / alamat berbeda', int((df.groupby('KodeCust')['Customer'].nunique() > 1).sum()),
           'Informasi saja (pelanggan dihitung per kode)')

    pakai = pd.Series(True, index=df.index)
    if KECUALIKAN_LUAR_PERIODE:  pakai &= ~df['LuarPeriode']
    if KECUALIKAN_GUDANG_GRATIS: pakai &= ~df['Gratis']
    if KECUALIKAN_NILAI_NOL:     pakai &= ~df['NilaiNol']
    df['DipakaiLaporan'] = pakai
    _catat(log, 'Baris akhir yang masuk laporan', pakai.sum(), f'dari {n_awal} baris awal')
    return df.reset_index(drop=True), pd.DataFrame(log), periode

def hitung_metrik(df):
    kol = 'Net' if OMSET_BASIS == 'Net' else 'DPP'
    d = df[df['DipakaiLaporan']]
    jual, retur = d[d['Jenis'] == 'PENJUALAN'], d[d['Jenis'] == 'RETUR']
    hasil = {}
    for cab, dc in d.groupby('Cabang'):
        j, r = jual[jual['Cabang'] == cab], retur[retur['Cabang'] == cab]
        m = j.groupby('KodeSupp').agg(Omset=(kol, 'sum'), Outlet=('KodeCust', 'nunique'), SKU=('KodeBarang', 'nunique'))
        m['Retur'] = r.groupby('KodeSupp')[kol].sum()
        m = m.reindex(m.index.union(r['KodeSupp'].unique())).fillna(0)
        hasil[cab] = {'tabel': m, 'outlet_unik': j['KodeCust'].nunique(), 'sku_unik': j['KodeBarang'].nunique()}
    return hasil

def metrik_bulan(df, per):
    d = df.copy()
    pakai = (d['Tanggal'].dt.to_period('M') == per)
    if KECUALIKAN_GUDANG_GRATIS: pakai &= ~d['Gratis']
    if KECUALIKAN_NILAI_NOL:     pakai &= ~d['NilaiNol']
    d['DipakaiLaporan'] = pakai
    return hitung_metrik(d)

def proses_file(path, master):
    jenis = deteksi_file(path)
    if jenis not in ('ORLAN', 'ZETA'):
        raise ValueError(f'File {os.path.basename(path)} tidak dikenali sebagai data Orlan / Zeta.')
    df = baca_orlan(path) if jenis == 'ORLAN' else baca_zeta(path)
    df, log, periode = bersihkan(df, master)
    return {'sumber': jenis, 'df': df, 'log': log, 'periode': periode, 'metrik': hitung_metrik(df)}


# ==============================================================================
# SEL 4: FUNGSI MEMBUAT LAPORAN EXCEL FORMAT "LAPORAN CABANG"
# ==============================================================================
FN   = Font(name='Calibri', size=11)
FB   = Font(name='Calibri', size=11, bold=True)
FB12 = Font(name='Calibri', size=12, bold=True)
FW   = Font(name='Calibri', size=12, bold=True, color='FFFFFF')
FIN  = Font(name='Calibri', size=11, color='0000FF')
FLK  = Font(name='Calibri', size=11, color='008000')
FRED = Font(name='Calibri', size=11, bold=True, color='FF0000')
FNOTE = Font(name='Calibri', size=9, italic=True, color='595959')
CYAN = PatternFill('solid', fgColor='00FFFF'); TOT = PatternFill('solid', fgColor='D9D2E9')
INP  = PatternFill('solid', fgColor='FFF2CC')
RED  = PatternFill('solid', fgColor='FF0000'); NAVY = PatternFill('solid', fgColor='20124D')
th, md = Side(style='thin'), Side(style='medium')
CEN = Alignment(horizontal='center', vertical='center', wrap_text=True)
RGT = Alignment(horizontal='right', vertical='center')
NUM, PCT1, PCT2 = '#,##0.00', '0.0%', '0.00%'

def _fmt_auto(v):
    a = abs(v) if v is not None else 0
    if a == 0 or a >= 0.01: return '0.0%'
    return '0.000%' if a >= 0.0001 else '0.0000%'

def _c(ws, ref, v=None, font=FN, fill=None, fmt=None, al=None, bd=None):
    c = ws[ref]
    if v is not None: c.value = v
    c.font = font
    if fill: c.fill = fill
    if fmt: c.number_format = fmt
    if al: c.alignment = al
    if bd: c.border = bd
    return c

def _hdr(ws, ref, v, fill=CYAN, font=FB):
    return _c(ws, ref, v, font, fill, al=CEN, bd=Border(left=th, right=th, top=th, bottom=th))

def _isi(ws, ref, v, fmt, al=None, bd=None):
    return _c(ws, ref, v, FIN, INP, fmt, al or RGT, bd or Border(bottom=th))

def _total_row(ws, r, c1, c2):
    for ci in range(c1, c2 + 1):
        c = ws.cell(row=r, column=ci); c.fill = TOT
        c.font = FB12; c.border = Border(top=md, bottom=md)

def _bd(): return Border(bottom=th)

def susun_baris(metrik_cab, master, pemb_py, pemb_pm):
    m = metrik_cab['tabel'].sort_values('Omset', ascending=False)
    rows = []
    for kode, r in m.iterrows():
        rows.append({'kode': kode, 'label': master['label'].get(kode, f'{kode} (TIDAK ADA DI MASTER)'),
                     'omset': float(r['Omset']), 'retur': float(r['Retur']),
                     'outlet': int(r['Outlet']), 'sku': int(r['SKU']),
                     'py': (pemb_py or {}).get(kode, {}), 'pm': (pemb_pm or {}).get(kode, {})})
    ada = {r['kode'] for r in rows}
    tidak = [{'kode': k, 'label': master['label'][k]} for k in master['prin']['KodeSupp'] if k not in ada]
    return rows, tidak

def buat_workbook(cabang, rows, tidak, periode, lab_py, lab_pm, outlet_unik, sku_unik):
    from openpyxl.utils import get_column_letter as GL, column_index_from_string as CI
    cab = cabang.upper()
    cur = f'{BULAN_SINGKAT[periode.month-1]} {periode.year}'
    namabulan = f'{BULAN_PANJANG[periode.month-1]} {periode.year}'
    n = len(rows)
    sp, sm = lab_py is not None, lab_pm is not None
    kodeint = lambda k: int(k) if str(k).isdigit() else k
    wb = Workbook(); wb.calculation.fullCalcOnLoad = True
    NOTE = 'Sel biru/kuning = input manual (stok, listing, DOI). Kolom bulan pembanding hanya tampil jika datanya ada.'

    def peta(*keys):
        out, ci = {}, 4
        for k in keys:
            if k is None: continue
            out[k] = GL(ci); ci += 1
        return out, GL(ci - 1)

    def gabung(ws, a, b, baris):
        if CI(a) < CI(b): ws.merge_cells(f'{a}{baris}:{b}{baris}')

    # OMSET
    om, omL = peta('py' if sp else None, 'pm' if sm else None, 'cur', 'pct', 'vpy' if sp else None, 'vpm' if sm else None)
    ws = wb.active; ws.title = 'Omset'; ws.sheet_view.showGridLines = False
    r0 = 7; rt = r0 + n
    tot_omset = sum(r['omset'] for r in rows)
    _c(ws, 'B2', f'CABANG {cab}', FB); _c(ws, f'{omL}2', 'OMSET', FB, al=CEN)
    _c(ws, 'B3', f'BULAN     : {namabulan}', FB)
    _hdr(ws, 'B4', 'PRINCIPAL'); _hdr(ws, 'C4', 'KODE SUPPLIER')
    for ref in ('B5', 'C5'): _hdr(ws, ref, None)
    if sp: _hdr(ws, f"{om['py']}4", lab_py); _hdr(ws, f"{om['py']}5", 'Omset (Rp)')
    if sm: _hdr(ws, f"{om['pm']}4", lab_pm); _hdr(ws, f"{om['pm']}5", 'Omset (Rp)')
    _hdr(ws, f"{om['cur']}4", cur); _hdr(ws, f"{om['pct']}4", None); gabung(ws, om['cur'], om['pct'], 4)
    _hdr(ws, f"{om['cur']}5", 'Omset (Rp)')
    _hdr(ws, f"{om['pct']}5", '% PRINCIPAL VS TOTAL CABANG'); _hdr(ws, f"{om['pct']}6", None); ws.merge_cells(f"{om['pct']}5:{om['pct']}6")
    if sp or sm:
        a_ = om.get('vpy', om.get('vpm')); b_ = om.get('vpm', om.get('vpy'))
        _hdr(ws, f'{a_}4', f'% {cur} vs')
        if a_ != b_: _hdr(ws, f'{b_}4', None); gabung(ws, a_, b_, 4)
        if sp: _hdr(ws, f"{om['vpy']}5", lab_py)
        if sm: _hdr(ws, f"{om['vpm']}5", lab_pm)
    for i, r in enumerate(rows):
        rr = r0 + i
        _c(ws, f'B{rr}', r['label'], bd=_bd()); _c(ws, f'C{rr}', kodeint(r['kode']), al=CEN, bd=_bd())
        if sp: _isi(ws, f"{om['py']}{rr}", r['py'].get('omset'), NUM)
        if sm: _isi(ws, f"{om['pm']}{rr}", r['pm'].get('omset'), NUM)
        _c(ws, f"{om['cur']}{rr}", r['omset'], fmt=NUM, al=RGT, bd=_bd())
        _c(ws, f"{om['pct']}{rr}", f"=IFERROR({om['cur']}{rr}/{om['cur']}${rt},\"\")", fmt=_fmt_auto(r['omset'] / tot_omset if tot_omset else 0), al=RGT, bd=_bd())
        if sp: _c(ws, f"{om['vpy']}{rr}", f"=IFERROR({om['cur']}{rr}/{om['py']}{rr},\"\")", fmt='0.00%', al=RGT, bd=_bd())
        if sm: _c(ws, f"{om['vpm']}{rr}", f"=IFERROR({om['cur']}{rr}/{om['pm']}{rr},\"\")", fmt='0.00%', al=RGT, bd=_bd())
    _c(ws, f'B{rt}', 'TOTAL', FB12)
    for k in ('py', 'pm', 'cur'):
        if k in om: _c(ws, f'{om[k]}{rt}', f'=SUM({om[k]}{r0}:{om[k]}{rt-1})', FB12, fmt=NUM, al=RGT)
    _c(ws, f"{om['pct']}{rt}", f"=SUM({om['pct']}{r0}:{om['pct']}{rt-1})", FB12, fmt='0%', al=RGT)
    if sp: _c(ws, f"{om['vpy']}{rt}", f"=IFERROR({om['cur']}{rt}/{om['py']}{rt},\"\")", FB12, fmt='0.00%', al=RGT)
    if sm: _c(ws, f"{om['vpm']}{rt}", f"=IFERROR({om['cur']}{rt}/{om['pm']}{rt},\"\")", FB12, fmt='0.00%', al=RGT)
    _total_row(ws, rt, 2, CI(omL))
    _c(ws, f'B{rt+2}', NOTE, FNOTE)
    ws.column_dimensions['A'].width = 3; ws.column_dimensions['B'].width = 30; ws.column_dimensions['C'].width = 16
    for k, col in om.items(): ws.column_dimensions[col].width = {'py': 20, 'pm': 20, 'cur': 20, 'pct': 16}.get(k, 12)
    ws.row_dimensions[5].height = 30; ws.freeze_panes = 'D7'
    if n:
        ch = BarChart(); ch.type = 'bar'; ch.title = f'Omset per Principal - {cur}'; ch.legend = None
        ch.add_data(Reference(ws, min_col=CI(om['cur']), min_row=r0, max_row=rt - 1), titles_from_data=False)
        ch.set_categories(Reference(ws, min_col=2, min_row=r0, max_row=rt - 1))
        ch.height, ch.width = 8, 16; ws.add_chart(ch, f'{GL(CI(omL)+2)}4')

    # RETUR
    ws = wb.create_sheet('Retur'); ws.sheet_view.showGridLines = False
    q0 = 6; qt = q0 + n
    _c(ws, 'B2', f'CABANG {cab}', FB); _c(ws, 'G2', 'RETUR', FB, al=CEN)
    _c(ws, 'B3', f'BULAN     : {namabulan}', FB)
    _hdr(ws, 'B4', 'PRINCIPAL'); _hdr(ws, 'C4', 'KODE SUPPLIER'); _hdr(ws, 'D4', cur)
    for ref in ('E4', 'F4', 'G4'): _hdr(ws, ref, None)
    ws.merge_cells('D4:G4')
    for ref in ('B5', 'C5'): _hdr(ws, ref, None)
    for ref, v in [('D5', 'Omset'), ('E5', 'Retur'), ('F5', 'Retur vs Omset'), ('G5', 'Omset Netto (setelah retur)')]: _hdr(ws, ref, v)
    for i, r in enumerate(rows):
        rr = q0 + i
        _c(ws, f'B{rr}', r['label'], bd=_bd()); _c(ws, f'C{rr}', kodeint(r['kode']), al=CEN, bd=_bd())
        _c(ws, f'D{rr}', f"=Omset!{om['cur']}{r0+i}", FLK, fmt=NUM, al=RGT, bd=_bd())
        _c(ws, f'E{rr}', r['retur'], fmt=NUM, al=RGT, bd=_bd())
        _c(ws, f'F{rr}', f'=IFERROR(E{rr}/D{rr},"")', fmt=_fmt_auto(r['retur'] / r['omset'] if r['omset'] else 0), al=CEN, bd=_bd())
        _c(ws, f'G{rr}', f'=D{rr}+E{rr}', fmt=NUM, al=RGT, bd=_bd())
    _c(ws, f'B{qt}', 'TOTAL', FB12)
    for col in 'DEG': _c(ws, f'{col}{qt}', f'=SUM({col}{q0}:{col}{qt-1})', FB12, fmt=NUM, al=RGT)
    _c(ws, f'F{qt}', f'=IFERROR(E{qt}/D{qt},"")', FB12, fmt=_fmt_auto(sum(r['retur'] for r in rows) / tot_omset if tot_omset else 0), al=CEN)
    _total_row(ws, qt, 2, 7)
    _c(ws, f'B{qt+2}', 'Retur = baris dengan qty/nilai negatif. Omset tidak dikurangi retur; lihat kolom Omset Netto.', FNOTE)
    for col, w in zip('ABCDEFG', [3, 30, 16, 20, 18, 16, 22]): ws.column_dimensions[col].width = w
    ws.row_dimensions[5].height = 30; ws.freeze_panes = 'C6'

    # PELANGGAN
    pl, plL = peta('py' if sp else None, 'pm' if sm else None, 'list', 'cur', 'gr' if sm else None, 'akt')
    ws = wb.create_sheet('Pelanggan'); ws.sheet_view.showGridLines = False
    _c(ws, 'B2', f'CABANG {cab}', FB); _c(ws, f'{plL}2', 'HORIZONTAL GROWTH', FB, al=CEN)
    _c(ws, 'B3', f'BULAN     : {namabulan}', FB)
    _hdr(ws, 'B4', 'PRINCIPAL'); _hdr(ws, 'C4', 'KODE SUPPLIER'); _hdr(ws, 'D4', 'TOTAL PELANGGAN AKTIF')
    for ci in range(5, CI(plL) + 1): _hdr(ws, f'{GL(ci)}4', None)
    gabung(ws, 'D', plL, 4)
    for ref in ('B5', 'C5'): _hdr(ws, ref, None)
    if sp: _hdr(ws, f"{pl['py']}5", lab_py)
    if sm: _hdr(ws, f"{pl['pm']}5", lab_pm)
    _hdr(ws, f"{pl['list']}5", 'LANGGANAN LISTING'); _hdr(ws, f"{pl['cur']}5", cur)
    if sm: _hdr(ws, f"{pl['gr']}5", 'GROWTH')
    _hdr(ws, f"{pl['akt']}5", '% AKTIF vs LISTING')
    for i, r in enumerate(rows):
        rr = q0 + i
        _c(ws, f'B{rr}', r['label'], bd=_bd()); _c(ws, f'C{rr}', kodeint(r['kode']), al=CEN, bd=_bd())
        if sp: _isi(ws, f"{pl['py']}{rr}", r['py'].get('outlet'), '0')
        if sm: _isi(ws, f"{pl['pm']}{rr}", r['pm'].get('outlet'), '0')
        _isi(ws, f"{pl['list']}{rr}", None, '0')
        _c(ws, f"{pl['cur']}{rr}", r['outlet'], fmt='0', al=RGT, bd=_bd())
        if sm: _c(ws, f"{pl['gr']}{rr}", f"=IFERROR({pl['cur']}{rr}/{pl['pm']}{rr}-1,\"\")", fmt=PCT2, al=CEN, bd=_bd())
        _c(ws, f"{pl['akt']}{rr}", f"=IFERROR({pl['cur']}{rr}/{pl['list']}{rr},\"\")", fmt=PCT1, al=CEN, bd=_bd())
    _c(ws, f'B{qt}', 'TOTAL', FB12)
    for k in ('py', 'pm', 'list', 'cur'):
        if k in pl: _c(ws, f'{pl[k]}{qt}', f'=SUM({pl[k]}{q0}:{pl[k]}{qt-1})', FB12, fmt='0', al=RGT)
    if sm: _c(ws, f"{pl['gr']}{qt}", f"=IFERROR({pl['cur']}{qt}/{pl['pm']}{qt}-1,\"\")", FB12, fmt=PCT2, al=CEN)
    _c(ws, f"{pl['akt']}{qt}", f"=IFERROR({pl['cur']}{qt}/{pl['list']}{qt},\"\")", FB12, fmt=PCT1, al=CEN)
    _total_row(ws, qt, 2, CI(plL))
    _c(ws, f'B{qt+1}', 'Outlet unik cabang (tanpa hitung ganda antar principal)', FB); _c(ws, f"{pl['cur']}{qt+1}", int(outlet_unik), FB, fmt='0', al=RGT)
    _c(ws, f'B{qt+3}', 'TOTAL = jumlah per principal (satu outlet yg beli >1 principal dihitung per principal), sesuai format Laporan Cabang. ' + NOTE, FNOTE)
    ws.column_dimensions['A'].width = 3; ws.column_dimensions['B'].width = 30; ws.column_dimensions['C'].width = 16
    for k, col in pl.items(): ws.column_dimensions[col].width = {'list': 20, 'akt': 18}.get(k, 14)
    ws.row_dimensions[5].height = 30; ws.freeze_panes = 'D6'

    # SKU
    sk, skL = peta('av', 'py' if sp else None, 'pm' if sm else None, 'cur', 'pav', 'vpm' if sm else None)
    ws = wb.create_sheet('SKU'); ws.sheet_view.showGridLines = False
    _c(ws, 'B2', f'CABANG {cab}', FB); _c(ws, f'{skL}2', 'VERTICAL GROWTH', FB, al=CEN)
    _c(ws, 'B3', f'BULAN     : {namabulan}', FB)
    _hdr(ws, 'B4', 'PRINCIPAL'); _hdr(ws, 'C4', 'KODE SUPPLIER'); _hdr(ws, f"{sk['av']}4", f'SKU TERSEDIA {cur}')
    _hdr(ws, f"{sk['av']}5", '(STOCK>0)')
    for ref in ('B5', 'C5'): _hdr(ws, ref, None)
    a_ = sk.get('py', sk.get('pm', sk['cur']))
    _hdr(ws, f'{a_}4', 'SKU TRANSAKSI')
    for ci in range(CI(a_) + 1, CI(sk['cur']) + 1): _hdr(ws, f'{GL(ci)}4', None)
    gabung(ws, a_, sk['cur'], 4)
    if sp: _hdr(ws, f"{sk['py']}5", lab_py)
    if sm: _hdr(ws, f"{sk['pm']}5", lab_pm)
    _hdr(ws, f"{sk['cur']}5", cur)
    _hdr(ws, f"{sk['pav']}4", f'% {cur} vs'); _hdr(ws, f"{sk['pav']}5", 'SKU TERSEDIA')
    if sm:
        _hdr(ws, f"{sk['vpm']}4", None); gabung(ws, sk['pav'], sk['vpm'], 4); _hdr(ws, f"{sk['vpm']}5", lab_pm)
    for i, r in enumerate(rows):
        rr = q0 + i
        _c(ws, f'B{rr}', r['label'], bd=_bd()); _c(ws, f'C{rr}', kodeint(r['kode']), al=CEN, bd=_bd())
        _isi(ws, f"{sk['av']}{rr}", None, '0', CEN)
        if sp: _isi(ws, f"{sk['py']}{rr}", r['py'].get('sku'), '0', CEN)
        if sm: _isi(ws, f"{sk['pm']}{rr}", r['pm'].get('sku'), '0', CEN)
        _c(ws, f"{sk['cur']}{rr}", r['sku'], fmt='0', al=CEN, bd=_bd())
        _c(ws, f"{sk['pav']}{rr}", f"=IFERROR({sk['cur']}{rr}/{sk['av']}{rr},\"\")", fmt=PCT1, al=CEN, bd=_bd())
        if sm: _c(ws, f"{sk['vpm']}{rr}", f"=IFERROR({sk['cur']}{rr}/{sk['pm']}{rr},\"\")", fmt=PCT1, al=CEN, bd=_bd())
    _c(ws, f'B{qt}', 'TOTAL', FB12)
    for k in ('av', 'py', 'pm', 'cur'):
        if k in sk: _c(ws, f'{sk[k]}{qt}', f'=SUM({sk[k]}{q0}:{sk[k]}{qt-1})', FB12, fmt='0', al=CEN)
    _c(ws, f"{sk['pav']}{qt}", f"=IFERROR({sk['cur']}{qt}/{sk['av']}{qt},\"\")", FB12, fmt=PCT2, al=CEN)
    if sm: _c(ws, f"{sk['vpm']}{qt}", f"=IFERROR({sk['cur']}{qt}/{sk['pm']}{qt},\"\")", FB12, fmt=PCT2, al=CEN)
    _total_row(ws, qt, 2, CI(skL))
    _c(ws, f'B{qt+1}', 'SKU unik cabang (tanpa hitung ganda)', FB); _c(ws, f"{sk['cur']}{qt+1}", int(sku_unik), FB, fmt='0', al=CEN)
    _c(ws, f'B{qt+3}', 'SKU transaksi = jumlah kode barang unik yang terjual pada bulan tsb. ' + NOTE, FNOTE)
    ws.column_dimensions['A'].width = 3; ws.column_dimensions['B'].width = 30; ws.column_dimensions['C'].width = 16
    for k, col in sk.items(): ws.column_dimensions[col].width = {'av': 24}.get(k, 14)
    ws.row_dimensions[5].height = 30; ws.freeze_panes = f"{GL(CI(sk['av'])+1)}6"

    # DASHBOARD
    ws = wb.create_sheet('Dashboard', 0); ws.sheet_view.showGridLines = False
    _c(ws, 'B2', f'CABANG {cab}', FB); _c(ws, 'B3', f'PERIODE: {namabulan}', FB)
    labs3 = ([lab_py] if sp else []) + ([lab_pm] if sm else []) + [cur]
    blok = [('OMSET', RED, labs3), ('OUTLET TRANSAKSI', NAVY, labs3), ('DOI', NAVY, [cur]), ('SKU TRANSAKSI', NAVY, labs3)]
    d0 = 6; N = n + len(tidak); dt = d0 + N
    mulai = {}; ci = 2
    for judul, fill, labs in blok:
        a, b = ci, ci + 1 + len(labs); mulai[judul] = a
        for k in range(a, b + 1): _hdr(ws, f'{GL(k)}4', None, fill, FW)
        ws[f'{GL(a)}4'].value = judul; ws.merge_cells(f'{GL(a)}4:{GL(b)}4')
        _hdr(ws, f'{GL(a)}5', 'PRINCIPAL'); _hdr(ws, f'{GL(a+1)}5', 'KODE SUPPLIER', CYAN)
        for k, lb in enumerate(labs): _hdr(ws, f'{GL(a+2+k)}5', lb)
        ci = b + 2
    def kol(judul, k):
        return GL(mulai[judul] + k)
    src = {'OMSET': ('Omset', [om[k] for k in ('py', 'pm', 'cur') if k in om], r0),
           'OUTLET TRANSAKSI': ('Pelanggan', [pl[k] for k in ('py', 'pm', 'cur') if k in pl], q0),
           'SKU TRANSAKSI': ('SKU', [sk[k] for k in ('py', 'pm', 'cur') if k in sk], q0)}
    semua = rows + tidak
    for i, r in enumerate(semua):
        rr = d0 + i; ada = i < n
        for judul in mulai:
            _c(ws, f"{kol(judul,0)}{rr}", r['label'], al=CEN, bd=Border(left=th, bottom=th))
            _c(ws, f"{kol(judul,1)}{rr}", kodeint(r['kode']), al=CEN, bd=_bd())
        if ada:
            for judul, (sh_name, cols, base) in src.items():
                for k, sc in enumerate(cols):
                    _c(ws, f"{kol(judul,2+k)}{rr}", f'=IF({sh_name}!{sc}{base+i}="","",{sh_name}!{sc}{base+i})', FLK, fmt=NUM, al=RGT, bd=_bd())
            _isi(ws, f"{kol('DOI',2)}{rr}", None, '0.0')
        else:
            _c(ws, f'A{rr}', 'Tidak Distribusi', FRED, al=RGT)
            for judul, fill, labs in blok:
                for k in range(len(labs)): _c(ws, f"{kol(judul,2+k)}{rr}", None, fmt=NUM, bd=_bd())
    for judul, fill, labs in blok:
        _c(ws, f'{kol(judul,0)}{dt}', 'TOTAL', FB, al=CEN, bd=Border(left=th, bottom=th)); _c(ws, f'{kol(judul,1)}{dt}', None, bd=_bd())
        for k in range(len(labs)):
            c_ = kol(judul, 2 + k)
            if judul == 'DOI': _c(ws, f'{c_}{dt}', None, bd=_bd())
            else: _c(ws, f'{c_}{dt}', f'=SUM({c_}{d0}:{c_}{dt-1})', FB, fmt=NUM, al=RGT, bd=_bd())
    _c(ws, f'B{dt+2}', NOTE + ' DOI butuh data stok.', FNOTE)
    ws.column_dimensions['A'].width = 16
    for judul, fill, labs in blok:
        ws.column_dimensions[kol(judul, 0)].width = 24; ws.column_dimensions[kol(judul, 1)].width = 14
        for k in range(len(labs)): ws.column_dimensions[kol(judul, 2 + k)].width = 20 if judul == 'OMSET' else 12
        ws.column_dimensions[GL(mulai[judul] + 2 + len(labs))].width = 3
    ws.row_dimensions[4].height = 18; ws.row_dimensions[5].height = 30; ws.freeze_panes = 'D6'
    for s in wb.worksheets:
        s.page_setup.orientation = 'landscape'; s.page_setup.fitToWidth = 1; s.page_setup.fitToHeight = 0
        s.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)
    wb._sheets = [wb['Dashboard'], wb['Omset'], wb['Retur'], wb['Pelanggan'], wb['SKU']]
    return wb


# ==============================================================================
# SEL 7 & SEL 8: BACA + BERSIHKAN DATA & BULAN PEMBANDING
# ==============================================================================
def run_sel7_and_sel8(supplier_path, data_files, files_bulan_lalu=None, files_tahun_lalu=None):
    """Menjalankan Sel 5-6 (Master), Sel 7 (Pembersihan & Gabung per Sumber), dan Sel 8 (Bulan Pembanding)."""
    log_stream = io.StringIO()
    per_file_reports = []

    with contextlib.redirect_stdout(log_stream):
        MASTER = baca_supplier(supplier_path)
        print(f"Supplier dibaca: {len(MASTER['prin'])} principal ({os.path.basename(supplier_path)}).")

        HASIL = {}
        for p in data_files:
            print('Memproses', os.path.basename(p), '... (file besar bisa 1-2 menit)')
            h = proses_file(p, MASTER)
            h['log'].insert(0, 'File', os.path.basename(p))

            # Simpan ringkasan per file untuk ditampilkan di UI
            ringkas = []
            for cab, v in h['metrik'].items():
                t = v['tabel']
                ringkas.append({'Cabang': cab.title(), 'Omset': t['Omset'].sum(), 'Retur': t['Retur'].sum(),
                                'Outlet unik': v['outlet_unik'], 'SKU unik': v['sku_unik'], 'Jumlah principal': len(t)})
            per_file_reports.append({
                'file': os.path.basename(p),
                'sumber': h['sumber'],
                'periode': str(h['periode']),
                'log_df': h['log'].copy(),
                'ringkas_df': pd.DataFrame(ringkas)
            })

            if h['sumber'] in HASIL:
                g = HASIL[h['sumber']]
                g['log'] = pd.concat([g['log'], h['log']], ignore_index=True)
                n_sebelum = len(g['df']) + len(h['df'])
                g['df'] = pd.concat([g['df'], h['df']], ignore_index=True).drop_duplicates().reset_index(drop=True)
                if len(g['df']) < n_sebelum:
                    print(f"  PERINGATAN: {n_sebelum - len(g['df'])} baris dobel antar file (data yang sama terupload dua kali) dibuang.")
                per_baris = g['df']['Tanggal'].dt.to_period('M')
                g['periode'] = per_baris.max()
                g['df']['LuarPeriode'] = per_baris != g['periode']
                pakai = pd.Series(True, index=g['df'].index)
                if KECUALIKAN_LUAR_PERIODE:  pakai &= ~g['df']['LuarPeriode']
                if KECUALIKAN_GUDANG_GRATIS: pakai &= ~g['df']['Gratis']
                if KECUALIKAN_NILAI_NOL:     pakai &= ~g['df']['NilaiNol']
                g['df']['DipakaiLaporan'] = pakai
                g['metrik'] = hitung_metrik(g['df'])
                g.pop('_cache_bulan', None)
                bln = sorted(per_baris.unique())
                if len(bln) > 1:
                    print(f"  Info: file berisi beberapa bulan {[str(x) for x in bln]}; laporan utama = {g['periode']}, bulan lain jadi kolom pembanding.")
            else:
                HASIL[h['sumber']] = h

        # Sel 8: Bulan Pembanding (Opsional)
        PEMB = {'bulan_lalu': {}, 'tahun_lalu': {}}
        for slot, flist in [('bulan_lalu', files_bulan_lalu or []), ('tahun_lalu', files_tahun_lalu or [])]:
            for p in flist:
                if deteksi_file(p) in ('ORLAN', 'ZETA'):
                    hp = proses_file(p, MASTER)
                    lab = f'{BULAN_SINGKAT[hp["periode"].month-1]} {hp["periode"].year}'
                    for cab, v in hp['metrik'].items():
                        PEMB[slot][(hp['sumber'], cab)] = {'label': lab, 'tabel': v['tabel']}
                    print(f"  {hp['sumber']} periode {lab}: {len(hp['metrik'])} cabang dimuat ke slot {slot}")

    return {
        'MASTER': MASTER,
        'HASIL': HASIL,
        'PEMB': PEMB,
        'per_file_reports': per_file_reports,
        'logs': log_stream.getvalue()
    }


# ==============================================================================
# SEL 9: BUAT LAPORAN PER CABANG + KEMAS ZIP PER SUMBER
# ==============================================================================
def _pemb(PEMB, slot, sumber, cab, per_target, h):
    d = PEMB[slot].get((sumber, cab))
    if d:
        lab, t = d['label'], d['tabel']
    else:
        cache = h.setdefault('_cache_bulan', {})
        if per_target not in cache:
            cache[per_target] = metrik_bulan(h['df'], per_target)
        m = cache[per_target].get(cab)
        if not m or m['tabel'].empty:
            return None, {}
        lab, t = f'{BULAN_SINGKAT[per_target.month-1]} {per_target.year}', m['tabel']
    return lab, {k: {'omset': float(r['Omset']), 'outlet': int(r['Outlet']), 'sku': int(r['SKU'])} for k, r in t.iterrows()}

def run_sel9_zip_reports(MASTER, HASIL, PEMB, output_dir="output"):
    """Menjalankan Sel 9: membuat file Excel per cabang, CSV bersih, Log Excel, dan mengemas ZIP per sumber."""
    os.makedirs(output_dir, exist_ok=True)
    log_stream = io.StringIO()
    zip_files = []

    with contextlib.redirect_stdout(log_stream):
        for sumber, h in HASIL.items():
            per = h['periode']
            tag = f'{BULAN_SINGKAT[per.month-1]}{per.year}'
            daftar = []
            for cab, v in h['metrik'].items():
                lab_py, p_py = _pemb(PEMB, 'tahun_lalu', sumber, cab, per - 12, h)
                lab_pm, p_pm = _pemb(PEMB, 'bulan_lalu', sumber, cab, per - 1, h)
                rows, tidak = susun_baris(v, MASTER, p_py, p_pm)
                wb = buat_workbook(cab.title(), rows, tidak, per, lab_py, lab_pm, v['outlet_unik'], v['sku_unik'])
                f = os.path.join(output_dir, f'Rangkuman_{sumber.title()}_{cab.title().replace(" ", "_")}_{tag}.xlsx')
                wb.save(f); daftar.append(f)
                print('Dibuat:', os.path.basename(f))
            f_data = os.path.join(output_dir, f'Data_Bersih_{sumber.title()}_{tag}.csv')
            h['df'].to_csv(f_data, index=False, encoding='utf-8-sig'); daftar.append(f_data)
            f_log = os.path.join(output_dir, f'Log_Pembersihan_{sumber.title()}_{tag}.xlsx')
            h['log'].to_excel(f_log, index=False); daftar.append(f_log)
            zpath = os.path.join(output_dir, f'Rangkuman_{sumber.title()}_{tag}.zip')
            with zipfile.ZipFile(zpath, 'w', zipfile.ZIP_DEFLATED) as z:
                for f in daftar: z.write(f, os.path.basename(f))
            print('ZIP siap:', zpath)
            zip_files.append(zpath)

    return {'zip_files': zip_files, 'logs': log_stream.getvalue()}


# ==============================================================================
# SEL 10, 10b, 11, 11b, 11c: FUNGSI HELPER & SINKRONISASI GOOGLE SHEETS
# ==============================================================================

def get_local_gspread_client(user_creds=None, service_account_path=None):
    """Uses the logged-in user's Google account credentials first (just like Colab), or falls back to a JSON file."""
    if user_creds is not None:
        return gspread.authorize(user_creds)
    scopes = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    if service_account_path and os.path.exists(service_account_path):
        creds = Credentials.from_service_account_file(service_account_path, scopes=scopes)
        return gspread.authorize(creds)
    if os.path.exists("service_account.json"):
        creds = Credentials.from_service_account_file("service_account.json", scopes=scopes)
        return gspread.authorize(creds)
    if os.path.exists("credentials.json"):
        try:
            creds = Credentials.from_service_account_file("credentials.json", scopes=scopes)
            return gspread.authorize(creds)
        except Exception:
            return gspread.oauth(credentials_filename="credentials.json")
    creds, _ = google_auth_default(scopes=scopes)
    return gspread.authorize(creds)

def bulan_untuk_dicatat(h, tahun, tampil=True):
    hasil, utama, df = {}, h['periode'], h.get('df')
    if utama.year == tahun:
        hasil[utama] = h['metrik']
    if df is None or 'Tanggal' not in df.columns:
        return hasil
    per_baris = df['Tanggal'].dt.to_period('M')
    for per in sorted(per_baris.unique()):
        if per == utama or per.year != tahun:
            continue
        d = df[per_baris == per]
        hari = d.groupby('Cabang')['Tanggal'].apply(lambda s: s.dt.normalize().nunique())
        layak = {c for c, n in hari.items() if n >= MIN_HARI_BULAN_LAIN}
        sisa = {str(c).title(): int(n) for c, n in hari.items() if n < MIN_HARI_BULAN_LAIN}
        m = {c: v for c, v in metrik_bulan(df, per).items() if c in layak}
        if m:
            hasil[per] = m
        if tampil and sisa:
            print(f"  Info: bulan {per} di file {h.get('sumber', '')} hanya {sisa} hari transaksi untuk cabang tsb "
                  f"(< {MIN_HARI_BULAN_LAIN}); dianggap data sisa dan TIDAK dicatat agar tidak menimpa data bulan itu.")
    return hasil

def omset_dicatat(tabel):
    if OMSET_BERSIH and 'Retur' in tabel.columns:
        return tabel['Omset'] + tabel['Retur']
    return tabel['Omset']

def rapikan_tampilan_omset(sh, ws, baris_akhir, kolom_akhir=14):
    try:
        sid, n = ws.id, baris_akhir
        def R(r1, r2, c1, c2):
            return {"sheetId": sid, "startRowIndex": r1, "endRowIndex": r2, "startColumnIndex": c1, "endColumnIndex": c2}
        KREM, EMAS, KREM_MUDA = (1, 0.949, 0.8), (1, 0.898, 0.6), (1, 0.976, 0.91)
        rgb = lambda c: {"red": c[0], "green": c[1], "blue": c[2]}
        HITAM = rgb((0, 0, 0))
        FMT = "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,verticalAlignment,wrapStrategy,numberFormat)"
        def gaya(rentang, bg=None, tebal=False, ukuran=11, rata="RIGHT", angka=False):
            f = {"textFormat": {"fontFamily": "Arial", "fontSize": ukuran, "bold": tebal, "foregroundColor": HITAM},
                 "horizontalAlignment": rata, "verticalAlignment": "MIDDLE", "wrapStrategy": "WRAP" if rata == "CENTER" else "OVERFLOW_CELL"}
            if bg: f["backgroundColor"] = rgb(bg)
            if angka: f["numberFormat"] = {"type": "NUMBER", "pattern": "#,##0"}
            return {"repeatCell": {"range": rentang, "cell": {"userEnteredFormat": f}, "fields": FMT}}
        def tinggi(r1, r2, px):
            return {"updateDimensionProperties": {"range": {"sheetId": sid, "dimension": "ROWS", "startIndex": r1, "endIndex": r2},
                                                  "properties": {"pixelSize": px}, "fields": "pixelSize"}}
        def lebar(c1, c2, px):
            return {"updateDimensionProperties": {"range": {"sheetId": sid, "dimension": "COLUMNS", "startIndex": c1, "endIndex": c2},
                                                  "properties": {"pixelSize": px}, "fields": "pixelSize"}}
        reqs = [
            {"repeatCell": {"range": R(0, n, 0, kolom_akhir), "cell": {}, "fields": "userEnteredFormat"}},
            gaya(R(0, 1, 0, kolom_akhir), KREM, True, 11, "CENTER"),
            gaya(R(0, 1, kolom_akhir - 1, kolom_akhir), EMAS, True, 11, "CENTER"),
            gaya(R(1, n, 0, 1), None, True, 11, "LEFT"),
            gaya(R(1, n, 1, kolom_akhir - 1), None, False, 11, "RIGHT", True),
            gaya(R(1, n, kolom_akhir - 1, kolom_akhir), KREM, True, 11, "RIGHT", True),
        ]
        for r in range(2, n, 2):
            reqs.append(gaya(R(r, r + 1, 0, 1), KREM_MUDA, True, 11, "LEFT"))
            reqs.append(gaya(R(r, r + 1, 1, kolom_akhir - 1), KREM_MUDA, False, 11, "RIGHT", True))
        garis = {"style": "SOLID", "color": HITAM}
        reqs += [
            {"updateBorders": {"range": R(0, n, 0, kolom_akhir), "top": garis, "bottom": garis, "left": garis, "right": garis,
                               "innerHorizontal": garis, "innerVertical": garis}},
            lebar(0, 1, 140), lebar(1, kolom_akhir - 1, 130), lebar(kolom_akhir - 1, kolom_akhir, 165),
            tinggi(0, 1, 38), tinggi(1, n, 30),
            {"updateSheetProperties": {"properties": {"sheetId": sid, "gridProperties": {"frozenRowCount": 1, "frozenColumnCount": 1}},
                                       "fields": "gridProperties(frozenRowCount,frozenColumnCount)"}},
        ]
        sh.batch_update({"requests": reqs})
    except Exception as e:
        print(f"Catatan: desain tabel tidak diterapkan ({e}). Data tetap tercatat normal.")

# ---- Fungsi Sel 10b ----
def _gabung_cakupan(daftar):
    hasil = []
    for s, e in sorted(daftar):
        if hasil:
            ps, pe = hasil[-1]
            if s <= pe + pd.Timedelta(days=1):
                hasil[-1] = (ps, max(pe, e)); continue
            jeda = pd.date_range(pe + pd.Timedelta(days=1), s - pd.Timedelta(days=1))
            if all(d.dayofweek == 6 for d in jeda):
                hasil[-1] = (ps, max(pe, e)); continue
        hasil.append((s, e))
    return hasil

def _tercakup(tgl, cakupan, cabang_wajib):
    for cab in cabang_wajib:
        if not any(s <= tgl <= e for s, e in cakupan.get(cab, [])):
            return False
    return True

def _sel(baris, i):
    return str(baris[i]).strip() if i is not None and len(baris) > i and baris[i] is not None else ''

def _buka_atau_buat(sh, nama):
    try:
        return sh.worksheet(nama), False
    except WorksheetNotFound:
        print(f"Sheet '{nama}' belum ada, dibuat baru.")
        return sh.add_worksheet(title=nama, rows=400, cols=6), True

def _buka_pendukung(sh, gc_client):
    url = str(SPREADSHEET_PENDUKUNG_URL).strip()
    if not url:
        print("Peringatan: SPREADSHEET_PENDUKUNG_URL kosong, data pendukung disimpan di spreadsheet master.")
        return sh
    try:
        return gc_client.open_by_url(url)
    except Exception as e:
        raise RuntimeError(f"Tidak bisa membuka SPREADSHEET_PENDUKUNG_URL. Detail: {e}")

def _tulis(ws, isi, kolom):
    ws.clear()
    try:
        ws.resize(rows=max(len(isi) + 20, 50), cols=kolom)
    except Exception:
        pass
    ws.update(range_name=f"A1:{chr(64 + kolom)}{len(isi)}", values=isi, value_input_option='RAW')
    try:
        ws.freeze(rows=1)
        ws.format(f"A1:{chr(64 + kolom)}1", {"textFormat": {"bold": True}})
    except Exception:
        pass

def perbarui_hari_kerja(HASIL, sh, gc_client, tampil=True):
    periode = list(HASIL.values())[0]['periode']
    tahun = periode.year
    nama_utama, nama_data = f"Hari Kerja {tahun}", f"Data Hari Kerja {tahun}"
    akhir_bulan = pd.Timestamp(year=periode.year, month=periode.month, day=periode.days_in_month)

    ws, baru_utama = _buka_atau_buat(sh, nama_utama)
    sh_p = _buka_pendukung(sh, gc_client)
    wp, _ = _buka_atau_buat(sh_p, nama_data)

    override, status_lama = {}, {}
    nilai = [] if baru_utama else ws.get_all_values()
    if nilai:
        kepala = [str(x).strip().lower() for x in nilai[0]]
        i_tgl = next((i for i, k in enumerate(kepala) if k == 'tanggal'), 0)
        i_ov = next((i for i, k in enumerate(kepala) if 'override' in k), None)
        i_st = next((i for i, k in enumerate(kepala) if k == 'status'), None)
        for r in nilai[1:]:
            t = pd.to_datetime(_sel(r, i_tgl), errors='coerce')
            if pd.isna(t): continue
            ov = _sel(r, i_ov).upper()
            if ov in ('LIBUR', 'KERJA'):
                override[t] = ov
            status_lama[t] = _sel(r, i_st).upper()

    aktif, cakupan = {}, {}
    baris_p = wp.get_all_values()
    if sh_p is not sh and len(baris_p) <= 1:
        try:
            lama = sh.worksheet(nama_data).get_all_values()
            if len(lama) > 1:
                baris_p = lama
                print(f"Data pendukung dipindahkan dari spreadsheet master ke spreadsheet terpisah ({len(lama) - 1} baris).")
        except WorksheetNotFound:
            pass
    for r in baris_p[1:]:
        jenis = _sel(r, 0).upper()
        if jenis == 'CAKUPAN':
            s, e = pd.to_datetime(_sel(r, 2), errors='coerce'), pd.to_datetime(_sel(r, 3), errors='coerce')
            if _sel(r, 1) and pd.notna(s) and pd.notna(e):
                cakupan.setdefault(_sel(r, 1).title(), []).append((s, e))
        elif jenis == 'AKTIF':
            t = pd.to_datetime(_sel(r, 1), errors='coerce')
            nama = {x.strip().title() for x in _sel(r, 2).split(',') if x.strip()} - {k.title() for k in _KATA_STATUS}
            if pd.notna(t) and nama:
                aktif.setdefault(t, set()).update(nama)

    for sumber, h in HASIL.items():
        df = h['df']
        if 'Tanggal' not in df.columns or 'Cabang' not in df.columns:
            continue
        d = pd.DataFrame({'T': pd.to_datetime(df['Tanggal'], errors='coerce').dt.normalize(),
                          'C': df['Cabang'].astype(str).str.strip().str.title()}).dropna()
        d = d[d['T'].dt.year == tahun]
        for cab, g in d.groupby('C'):
            for t in g['T'].drop_duplicates():
                aktif.setdefault(t, set()).add(cab)
            cakupan.setdefault(cab, []).append((g['T'].min(), g['T'].max()))
    cakupan = {cab: _gabung_cakupan(v) for cab, v in cakupan.items()}

    tanggal = {t for t in pd.date_range(f'{tahun}-01-01', f'{tahun}-12-31') if t.dayofweek != 6}
    tanggal |= {t for t in aktif if t.year == tahun}
    ket = {}
    for k, v in LIBUR_MANUAL.items():
        t = pd.Timestamp(k)
        if t.year == tahun:
            tanggal.add(t); ket[t] = v
            override.setdefault(t, 'LIBUR')
    tanggal = sorted(tanggal)

    status, catatan = {}, {}
    for t in tanggal:
        ov, akt = override.get(t, ''), aktif.get(t, set())
        if ov == 'LIBUR':
            status[t], catatan[t] = 'LIBUR', ket.get(t) or 'Override manual'
        elif ov == 'KERJA':
            status[t], catatan[t] = 'KERJA', 'Override manual'
        elif akt:
            status[t] = 'KERJA'
            catatan[t] = f"{len(akt)} cabang ada transaksi" + (" (Minggu)" if t.dayofweek == 6 else "")
        elif _tercakup(t, cakupan, CABANG_WAJIB):
            status[t], catatan[t] = 'LIBUR', 'Tidak ada transaksi di seluruh cabang (terdeteksi otomatis)'
        else:
            status[t], catatan[t] = 'ESTIMASI', 'Belum ada data, dihitung sebagai hari kerja'

    non_libur = [t for t in tanggal if status[t] != 'LIBUR']
    lengkap = [t for t in tanggal if _tercakup(t, cakupan, CABANG_WAJIB)]
    tgl_lengkap = min(max(lengkap), akhir_bulan) if lengkap else None
    ada_data = [t for t in tanggal if aktif.get(t) and t <= akhir_bulan]
    tgl_terakhir = max(ada_data) if ada_data else None
    if HARI_ACUAN == 'lengkap':
        tgl_acuan = tgl_lengkap or tgl_terakhir
    else:
        tgl_acuan = tgl_terakhir or tgl_lengkap
    if tgl_acuan is None:
        tgl_acuan = pd.Timestamp(year=tahun, month=1, day=1)

    wd_setahun = int(WD_SETAHUN_MANUAL) if WD_SETAHUN_MANUAL else len(non_libur)
    wd_akhir_bulan = sum(1 for t in non_libur if t <= akhir_bulan)
    wd_hari_ini = sum(1 for t in non_libur if t <= tgl_acuan)

    isi = [["Tanggal", "Hari", "Status", "Override (ketik LIBUR atau KERJA)", "Catatan (otomatis)"]]
    for t in tanggal:
        isi.append([t.strftime('%Y-%m-%d'), _HARI[t.dayofweek], status[t], override.get(t, ''), catatan[t]])
    _tulis(ws, isi, 5)

    pend = [["Jenis", "Kunci", "Isi 1", "Isi 2"]]
    for cab in sorted(cakupan):
        for s, e in cakupan[cab]:
            pend.append(["CAKUPAN", cab, s.strftime('%Y-%m-%d'), e.strftime('%Y-%m-%d')])
    for t in sorted(aktif):
        pend.append(["AKTIF", t.strftime('%Y-%m-%d'), ", ".join(sorted(aktif[t])), ""])
    _tulis(wp, pend, 4)

    if tampil:
        print(f"\nHari kerja {tahun} (sheet '{nama_utama}') berhasil diperbarui.")
        print(f"01 Jan - 31 Des       : {wd_setahun} hari")
        print(f"01 Jan - {akhir_bulan:%d %b %Y} : {wd_akhir_bulan} hari")
        print(f"01 Jan - {tgl_acuan:%d %b %Y} : {wd_hari_ini} hari")

    return {'tahun': tahun, 'setahun': wd_setahun, 'sampai_akhir_bulan': wd_akhir_bulan, 'sampai_hari_ini': wd_hari_ini,
            'tgl_acuan': tgl_acuan, 'tgl_terakhir': tgl_terakhir, 'tgl_lengkap': tgl_lengkap,
            'akhir_bulan': akhir_bulan, 'nama_sheet': nama_utama}

# ---- Fungsi Sel 11 & 11c ----
def ke_angka(x):
    if isinstance(x, (int, float)) and not isinstance(x, bool):
        return float(x)
    s = str(x).strip().replace('Rp', '').replace(' ', '').replace('\xa0', '')
    if not s or s.startswith('='):
        return None
    neg = (s.startswith('(') and s.endswith(')')) or s.startswith('-')
    s = s.strip('()-')
    if ',' in s and '.' in s:
        desimal = ',' if s.rfind(',') > s.rfind('.') else '.'
        ribuan = '.' if desimal == ',' else ','
        s = s.replace(ribuan, '').replace(desimal, '.')
    elif ',' in s:
        s = s.replace(',', '') if re.fullmatch(r'\d{1,3}(,\d{3})+', s) else s.replace(',', '.')
    elif '.' in s and re.fullmatch(r'\d{1,3}(\.\d{3})+', s):
        s = s.replace('.', '')
    try:
        v = float(s)
    except ValueError:
        return None
    return -v if neg else v

def baca_sheet_mentah(ws):
    try:
        return ws.get_all_values(value_render_option='UNFORMATTED_VALUE')
    except TypeError:
        return ws.get_all_values()

def _norm_kode(x):
    s = str(x).strip().lower()
    return s[:-2] if s.endswith('.0') else s

def _sheet(sh, nama, baris=100, kolom=8):
    try:
        return sh.worksheet(nama), False
    except WorksheetNotFound:
        return sh.add_worksheet(title=nama, rows=baris, cols=kolom), True

def perbarui_omset_principal(HASIL, sh, master, gc_client, tampil=True):
    periode = list(HASIL.values())[0]['periode']
    tahun, bln = periode.year, periode.month
    nama_tampil, nama_target, nama_data = f"Omset per Principal {tahun}", f"Target {tahun}", f"Data Principal {tahun}"
    batas = f"{tahun}-{bln:02d}"
    bulan_upload = batas

    sh_p = _buka_pendukung(sh, gc_client)
    wd, _ = _sheet(sh_p, nama_data)
    def baca_baris(rows):
        hasil = []
        for r in rows:
            if len(r) >= 6 and str(r[0]).strip() and ke_angka(r[5]) is not None:
                hasil.append([str(r[0]).strip(), str(r[1]).strip().title(), _norm_kode(r[2]), str(r[3]).strip(),
                              str(r[4]).strip(), ke_angka(r[5])])
        return hasil
    riwayat = baca_baris(baca_sheet_mentah(wd)[1:])
    if sh_p is not sh:
        try:
            sisa = baca_baris(baca_sheet_mentah(sh.worksheet(nama_data))[1:])
        except WorksheetNotFound:
            sisa = []
        ada = {(r[0], r[1]) for r in riwayat}
        tambahan = [r for r in sisa if (r[0], r[1]) not in ada]
        if tambahan:
            riwayat += tambahan

    baru, diganti = [], set()
    ITEM_BULAN = [(sm, {'periode': p, 'metrik': m}) for sm, hh in HASIL.items()
                  for p, m in bulan_untuk_dicatat({**hh, 'sumber': sm}, tahun, tampil=tampil).items()]
    for sumber, h in ITEM_BULAN:
        per = h['periode']
        if per.year != tahun: continue
        bulan = f"{per.year}-{per.month:02d}"
        for cab, v in h['metrik'].items():
            cab_t = str(cab).strip().title()
            diganti.add((bulan, cab_t))
            nilai_bersih = omset_dicatat(v['tabel'])
            for kode, row in v['tabel'].iterrows():
                nilai = float(nilai_bersih[kode])
                if not nilai: continue
                kd = str(kode).strip()
                supp = master['supp'].get(kd, kd)
                label = master['label'].get(kd, f"{kd} (tidak ada di master)")
                baru.append([bulan, cab_t, _norm_kode(kd), supp, label, nilai])
    riwayat = [r for r in riwayat if (r[0], r[1]) not in diganti] + baru
    if riwayat:
        batas = max(r[0] for r in riwayat)
        bln = int(batas[5:7])
    isi = [["Bulan", "Cabang", "KodeSupp", "Supp", "Principal", "Omset (Rp)"]] + [
        [b, c, k, s, p, o] for b, c, k, s, p, o in sorted(riwayat, key=lambda x: (x[0], x[1], x[2]))]
    wd.clear()
    try: wd.resize(rows=max(len(isi) + 20, 50), cols=6)
    except Exception: pass
    wd.update(range_name=f"A1:F{len(isi)}", values=isi, value_input_option='RAW')
    bulan_ada = sorted({r[0] for r in riwayat if r[0] <= batas})

    om, cab_bulan = {}, set()
    for bl, c, k, s, p, o in riwayat:
        cab_bulan.add((bl, c))
        if bl <= batas:
            d = om.setdefault((c, k), {'cab': c, 'kode': k, 'supp': s, 'label': p, 'bln': {}})
            m = int(bl[5:7]); d['bln'][m] = d['bln'].get(m, 0.0) + o

    try:
        data_t = baca_sheet_mentah(sh.worksheet(nama_target))
    except WorksheetNotFound:
        raise RuntimeError(f"Sheet '{nama_target}' tidak ditemukan di Spreadsheet Master.")
    cari = f"Jan - {_BLN_NAMA[bln - 1]}"
    idx = next((i for i, hd in enumerate(data_t[0]) if cari in str(hd)), 3 + bln - 1)
    target = []
    for r in data_t[1:]:
        if len(r) < 3 or not str(r[0]).strip() or str(r[1]).strip() == '' or str(r[0]).upper().startswith('TOTAL'):
            continue
        v = ke_angka(r[idx]) if len(r) > idx else None
        supp = str(r[2]).strip()
        target.append({'cab': str(r[0]).strip().title(), 'kode': _norm_kode(r[1]), 'supp': supp,
                       'label': f"{supp} ({NICKNAME[supp]})" if supp in NICKNAME else supp, 'target': (v or 0.0)})

    baris, terpakai, tanpa_omset = {}, set(), []
    def ambil(label, cab):
        return baris.setdefault((label, cab), {'bln': {}, 'target': 0.0})
    def tambah(x, d):
        for m, v in d['bln'].items():
            x['bln'][m] = x['bln'].get(m, 0.0) + v
    for t in target:
        cocok = om.get((t['cab'], t['kode']))
        if cocok is None:
            cocok = next((d for (c, k), d in om.items()
                          if c == t['cab'] and (c, k) not in terpakai and d['supp'].strip().upper() == t['supp'].upper()), None)
        if cocok is not None:
            terpakai.add((cocok['cab'], cocok['kode']))
            x = ambil(cocok['label'], t['cab']); tambah(x, cocok); x['target'] += t['target']
        else:
            x = ambil(t['label'], t['cab']); x['target'] += t['target']
            if t['target']: tanpa_omset.append(f"{t['label']} - {t['cab']}")
    tanpa_target = []
    for key, d in om.items():
        if key not in terpakai:
            x = ambil(d['label'], d['cab']); tambah(x, d)
            if sum(d['bln'].values()): tanpa_target.append(f"{d['label']} - {d['cab']}")

    KB, KT, KP = 2, 14, 15
    L = lambda i: chr(65 + i)
    per_cab = {}
    for (label, cab), x in baris.items():
        if sum(x['bln'].values()) or x['target']:
            per_cab.setdefault(cab, []).append((label, x))
    urut_cab = sorted(per_cab, key=lambda c: (-sum(sum(x['bln'].values()) for _, x in per_cab[c]), c))
    out, jenis = [], []
    for cab in urut_cab:
        awal = len(out) + 2
        for label, x in sorted(per_cab[cab], key=lambda z: (-sum(z[1]['bln'].values()), z[0])):
            r = len(out) + 2
            sel_bln = [(x['bln'].get(m, 0.0) if (f"{tahun}-{m:02d}", cab) in cab_bulan else '') if m <= bln else '' for m in range(1, 13)]
            out.append([cab, label] + sel_bln + [f"=SUM({L(KB)}{r}:{L(KB + 11)}{r})", x['target'], f'=IF({L(KP)}{r}>0,{L(KT)}{r}/{L(KP)}{r},"")']); jenis.append('d')
        r = len(out) + 2
        out.append([cab, "TOTAL"] + [f"=SUM({L(i)}{awal}:{L(i)}{r - 1})" for i in range(KB, KP + 1)]
                   + [f'=IF({L(KP)}{r}>0,{L(KT)}{r}/{L(KP)}{r},"")']); jenis.append('s')
    n_akhir = len(out) + 1
    r = len(out) + 2
    out.append(["TOTAL SEMUA CABANG", ""] + [f'=SUMIF($B$2:$B${n_akhir},"TOTAL",{L(i)}$2:{L(i)}${n_akhir})' for i in range(KB, KP + 1)]
               + [f'=IF({L(KP)}{r}>0,{L(KT)}{r}/{L(KP)}{r},"")']); jenis.append('g')
    n = len(out) + 1
    kepala = ["Cabang", "Principal"] + _BLN_NAMA + ["Total Omset (Rp)", "Target (Rp)", "% Pencapaian"]
    NK = len(kepala)
    cat = (f"Catatan: kolom Jan-Des = omset tiap bulan (Rp); sel kosong = bulan itu belum diupload, bukan nol. "
           f"Total Omset = Jan s/d {_BLN_NAMA[bln - 1]} dari bulan yang sudah diupload ({', '.join(bulan_ada) or '-'}); target = {cari} {tahun}. "
           f"Persentase baru akurat bila semua bulan Jan s/d {_BLN_NAMA[bln - 1]} sudah diupload.")

    ws, baru_ws = _sheet(sh, nama_tampil, baris=max(n + 20, 60), kolom=NK)
    try: ws.resize(rows=max(n + 20, 60), cols=NK)
    except Exception: pass
    try: ws.batch_clear([f"A1:{L(NK - 1)}{max(getattr(ws, 'row_count', 500), n + 20)}"])
    except Exception: ws.clear()
    ws.update(range_name=f"A1:{L(NK - 1)}1", values=[kepala], value_input_option='USER_ENTERED')
    ws.update(range_name=f"A2:{L(NK - 1)}{n}", values=out, value_input_option='USER_ENTERED')
    ws.update(range_name=f"A{n + 2}", values=[[cat]], value_input_option='USER_ENTERED')

    def rng(r1, r2, c1=0, c2=NK):
        return {"sheetId": ws.id, "startRowIndex": r1, "endRowIndex": r2, "startColumnIndex": c1, "endColumnIndex": c2}
    def warna(r, rgb, tebal=True):
        return {"repeatCell": {"range": rng(r - 1, r), "cell": {"userEnteredFormat": {
            "backgroundColor": {"red": rgb[0], "green": rgb[1], "blue": rgb[2]}, "textFormat": {"bold": tebal}}},
            "fields": "userEnteredFormat(backgroundColor,textFormat)"}}
    def lebar(c1, c2, px):
        return {"updateDimensionProperties": {"range": {"sheetId": ws.id, "dimension": "COLUMNS", "startIndex": c1, "endIndex": c2},
                                              "properties": {"pixelSize": px}, "fields": "pixelSize"}}
    reqs = [
        {"repeatCell": {"range": rng(1, max(n + 20, 200)), "cell": {"userEnteredFormat": {}}, "fields": "userEnteredFormat"}},
        {"repeatCell": {"range": rng(1, n, KB, KP + 1), "cell": {"userEnteredFormat": {"numberFormat": {"type": "NUMBER", "pattern": '#,##0;-#,##0;"-"'}}},
                        "fields": "userEnteredFormat.numberFormat"}},
        {"repeatCell": {"range": rng(1, n, KP + 1, NK), "cell": {"userEnteredFormat": {"numberFormat": {"type": "PERCENT", "pattern": "0.0%"}}},
                        "fields": "userEnteredFormat.numberFormat"}},
        {"repeatCell": {"range": rng(0, 1), "cell": {"userEnteredFormat": {
            "backgroundColor": {"red": 1, "green": 0.949, "blue": 0.8}, "textFormat": {"bold": True}, "horizontalAlignment": "CENTER"}},
            "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)"}},
        lebar(0, 1, 130), lebar(1, 2, 170), lebar(KB, KP + 1, 120), lebar(KP + 1, NK, 105),
    ]
    for i, j in enumerate(jenis):
        if j == 's': reqs.append(warna(i + 2, (0.851, 0.824, 0.914)))
        elif j == 'g': reqs.append(warna(i + 2, (1, 0.902, 0.6)))
    garis = {"style": "SOLID"}
    reqs.append({"updateBorders": {"range": rng(0, n), "top": garis, "bottom": garis, "left": garis, "right": garis,
                                   "innerHorizontal": garis, "innerVertical": garis}})
    sh.batch_update({"requests": reqs})

    if tampil:
        print(f"Sheet '{nama_tampil}' diperbarui: {len(per_cab)} cabang, {sum(1 for j in jenis if j == 'd')} baris principal.")
    return pd.DataFrame(out, columns=kepala)


def run_sel10_to_11c_gsheets_and_summary(
    MASTER,
    HASIL,
    output_dir="output",
    user_creds=None,
    service_account_path=None,
    paksa_summary_bulan_lama=False
):
    """Menjalankan Sel 10, Sel 10b, Sel 11, Sel 11b (simpan Summary Target Excel lokal), dan Sel 11c."""
    os.makedirs(output_dir, exist_ok=True)
    log_stream = io.StringIO()
    summary_excel_path = None
    summary_excel_name = None

    with contextlib.redirect_stdout(log_stream):
        gc = get_local_gspread_client(user_creds=user_creds, service_account_path=service_account_path)
        sh = gc.open_by_url(SPREADSHEET_URL)
        print(f"Berhasil terhubung ke Spreadsheet: {sh.title}")

        # ==== SEL 10: SINKRONISASI OMSET <TAHUN> ====
        ITEM_BULAN = [(sm, {'periode': p, 'metrik': m}) for sm, hh in HASIL.items()
                      for p, m in bulan_untuk_dicatat({**hh, 'sumber': sm}, hh['periode'].year).items()]
        for sumber, h in ITEM_BULAN:
            periode = h['periode']
            tahun = str(periode.year)
            idx_bulan = periode.month - 1
            nama_bulan_str = NAMA_KOLOM_BULAN[idx_bulan]
            nama_sheet_omset = f"Omset {tahun}"

            try:
                ws = sh.worksheet(nama_sheet_omset)
                print(f"Sheet '{nama_sheet_omset}' ditemukan. Memproses...")
            except WorksheetNotFound:
                print(f"Sheet '{nama_sheet_omset}' belum ada. Membuat sheet baru...")
                ws = sh.add_worksheet(title=nama_sheet_omset, rows=50, cols=20)
                headers = ["Cabang"] + NAMA_KOLOM_BULAN + ["TOTAL YTD"]
                ws.update('A1:N1', [headers])
                kolom_cabang = [[c] for c in DAFTAR_CABANG]
                ws.update(f'A2:A{len(DAFTAR_CABANG)+1}', kolom_cabang)
                ws.format("A1:N1", {"textFormat": {"bold": True}})

            semua_data = ws.get_all_values()
            header_sheet = semua_data[0] if len(semua_data) > 0 else []
            if nama_bulan_str in header_sheet:
                col_idx = header_sheet.index(nama_bulan_str) + 1
            else:
                print(f"Error: Kolom bulan {nama_bulan_str} tidak ditemukan di Sheet!")
                continue

            baris_cabang = {}
            for row_num, row_data in enumerate(semua_data):
                if row_num == 0 or not row_data: continue
                nama_cab_sheet = str(row_data[0]).strip().title()
                baris_cabang[nama_cab_sheet] = row_num + 1

            print(f"Mencatat data {sumber} untuk bulan {nama_bulan_str} {tahun}...")
            data_batch = []
            for cab, v in h['metrik'].items():
                nama_cabang = cab.title()
                if nama_cabang not in baris_cabang:
                    baris_baru = len(baris_cabang) + 2
                    ws.update_cell(baris_baru, 1, nama_cabang)
                    baris_cabang[nama_cabang] = baris_baru
                row_idx = baris_cabang[nama_cabang]
                total_omset = float(omset_dicatat(v['tabel']).sum())
                data_batch.append({"range": rowcol_to_a1(row_idx, col_idx), "values": [[total_omset]]})
                huruf_baris = str(row_idx)
                data_batch.append({"range": rowcol_to_a1(row_idx, 14), "values": [[f"=SUM(B{huruf_baris}:M{huruf_baris})"]]})
            if data_batch:
                ws.batch_update(data_batch, value_input_option='USER_ENTERED')
            rapikan_tampilan_omset(sh, ws, max(baris_cabang.values()))

        print("✅ Sel 10: Pencatatan Omset selesai.")

        # ==== SEL 10b: HARI KERJA OTOMATIS ====
        WD_INFO = perbarui_hari_kerja(HASIL, sh, gc, tampil=True)

        # ==== SEL 11 & 11b: SUMMARY TARGET (GSHEETS + EXCEL LOKAL) ====
        _LEWATI_SUMMARY, _PESAN_LEWATI = False, ""
        try:
            _bn = ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun', 'Jul', 'Agt', 'Sep', 'Okt', 'Nov', 'Des']
            _p = list(HASIL.values())[0]['periode']
            _b6 = str(sh.worksheet("Summary Target").get_all_values()[5][1]).strip()
            _m = re.fullmatch(r'(\w{3}) (\d{4})', _b6)
            if _m and _m.group(1) in _bn and not paksa_summary_bulan_lama:
                if (int(_m.group(2)), _bn.index(_m.group(1)) + 1) > (_p.year, _p.month):
                    _LEWATI_SUMMARY = True
                    _PESAN_LEWATI = (f"Summary Target tetap menampilkan {_b6}; data yang diupload ({_bn[_p.month - 1]} {_p.year}) lebih lama.")
        except Exception:
            pass

        if _LEWATI_SUMMARY:
            print(_PESAN_LEWATI)
        else:
            print("\nMemulai pembuatan Summary Target (Sel 11)...")
            sumber_pertama = list(HASIL.keys())[0]
            periode = HASIL[sumber_pertama]['periode']
            tahun_berjalan = str(periode.year)
            idx_bulan = periode.month - 1
            nama_bulan = ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun', 'Jul', 'Agt', 'Sep', 'Okt', 'Nov', 'Des']

            WD_SETAHUN = WD_INFO['setahun']
            WD_SAMPAI_AKHIR_BULAN = WD_INFO['sampai_akhir_bulan']
            WD_SAMPAI_HARI_INI = WD_INFO['sampai_hari_ini']
            tgl_terakhir = WD_INFO['tgl_acuan']
            tgl_akhir_bulan = WD_INFO['akhir_bulan']

            str_tgl_berjalan = tgl_terakhir.strftime('%d %b %Y')
            str_akhir_bulan = tgl_akhir_bulan.strftime('%d %b %Y')
            target_persen_wd = round(WD_SAMPAI_HARI_INI / WD_SETAHUN, 4)

            sheet_omset = sh.worksheet(f"Omset {tahun_berjalan}")
            data_omset = baca_sheet_mentah(sheet_omset)
            header_omset = data_omset[0]

            sheet_target = sh.worksheet(f"Target {tahun_berjalan}")
            data_target = baca_sheet_mentah(sheet_target)
            header_target = data_target[0]

            db_cabang = {cab: {"omset_bulan_ini": 0.0, "omset_ytd": 0.0, "target_ytd": 0.0, "target_full": 0.0} for cab in DAFTAR_CABANG}

            for sumber, h in HASIL.items():
                for cab, v in h['metrik'].items():
                    if cab.title() in db_cabang:
                        db_cabang[cab.title()]["omset_bulan_ini"] += float(omset_dicatat(v['tabel']).sum()) / 1e9

            idx_ytd_omset = header_omset.index("TOTAL YTD") if "TOTAL YTD" in header_omset else 13
            for row in data_omset[1:]:
                if not row[0]: continue
                cab_name = str(row[0]).strip().title()
                if cab_name in db_cabang:
                    try:
                        val_ytd = ke_angka(row[idx_ytd_omset])
                        if val_ytd is not None:
                            db_cabang[cab_name]["omset_ytd"] = val_ytd / 1e9
                    except IndexError:
                        pass

            str_cari_ytd = f"Jan - {nama_bulan[idx_bulan]}"
            idx_target_ytd, idx_target_full = -1, -1
            for i, head in enumerate(header_target):
                if str_cari_ytd in str(head): idx_target_ytd = i
                if "Jan - Des" in str(head): idx_target_full = i
            if idx_target_ytd == -1: idx_target_ytd = 3 + idx_bulan
            if idx_target_full == -1: idx_target_full = 14

            for row in data_target[1:]:
                if not row[0]: continue
                cab_name = str(row[0]).strip().title()
                if cab_name in db_cabang:
                    try:
                        v_ytd = ke_angka(row[idx_target_ytd])
                        if v_ytd is not None: db_cabang[cab_name]["target_ytd"] += v_ytd / 1e9
                    except IndexError: pass
                    try:
                        v_full = ke_angka(row[idx_target_full])
                        if v_full is not None: db_cabang[cab_name]["target_full"] += v_full / 1e9
                    except IndexError: pass

            def style_cell(ws_xl, row, col, val, font=None, fill=None, align=None, num_fmt=None, border=None):
                c = ws_xl.cell(row=row, column=col)
                if val is not None: c.value = val
                if font: c.font = font
                if fill: c.fill = fill
                if align: c.alignment = align
                if num_fmt: c.number_format = num_fmt
                if border: c.border = border
                return c

            wb = openpyxl.Workbook()
            ws_xl = wb.active
            ws_xl.title = "Summary Target"
            ws_xl.sheet_view.showGridLines = False

            BORD = Border(left=th, right=th, top=th, bottom=th)
            F_B = Font(name='Calibri', size=11, bold=True)
            F_N = Font(name='Calibri', size=11)
            FILL_Y = PatternFill('solid', fgColor='FFF2CC')
            FILL_G = PatternFill('solid', fgColor='E2EFDA')
            FILL_TOT = PatternFill('solid', fgColor='FFE699')
            AL_C = Alignment(horizontal='center', vertical='center', wrap_text=True)
            AL_R = Alignment(horizontal='right', vertical='center')
            AL_L = Alignment(horizontal='left', vertical='center')

            style_cell(ws_xl, 1, 6, str_tgl_berjalan, F_B, align=AL_C)
            ws_xl.merge_cells("F1:G1")
            style_cell(ws_xl, 2, 5, "Working Days", F_B, border=BORD, align=AL_C)
            ws_xl.merge_cells("E2:E4")

            wd_data_excel = [("01 Jan - 31 Des", WD_SETAHUN), (f"01 Jan - {str_akhir_bulan}", WD_SAMPAI_AKHIR_BULAN), (f"01 Jan - {str_tgl_berjalan}", WD_SAMPAI_HARI_INI)]
            for i, (label, val) in enumerate(wd_data_excel):
                style_cell(ws_xl, 2+i, 6, label, F_B, border=BORD, align=AL_C)
                style_cell(ws_xl, 2+i, 7, val, F_B, border=BORD, align=AL_R)

            col_str_bln_berjalan = f"{nama_bulan[idx_bulan]} {tahun_berjalan}"
            headers = [
                (6, 1, "Cabang", "A6:A7", FILL_Y), (6, 2, col_str_bln_berjalan, None, FILL_Y), (7, 2, "Omset (M)", None, FILL_Y),
                (6, 3, f"Jan - {col_str_bln_berjalan}", "C6:E6", FILL_Y), (7, 3, "Omset (M)", None, FILL_Y), (7, 4, "Target (M)", None, FILL_Y), (7, 5, "%", None, FILL_Y),
                (6, 6, f"TARGET {tahun_berjalan}", "F6:G6", FILL_G), (7, 6, "Rp (M)", None, FILL_G), (7, 7, "%", None, FILL_G),
                (5, 8, "Working Days", "H5:I5", FILL_Y), (6, 8, str_tgl_berjalan, None, FILL_Y), (7, 8, "100%", None, FILL_Y),
                (6, 9, f"31 Des {tahun_berjalan}", None, FILL_Y), (7, 9, target_persen_wd, None, FILL_Y),
            ]
            for r, c, val, merge, fill in headers:
                style_cell(ws_xl, r, c, val, F_B, fill, AL_C, border=BORD)
                if merge: ws_xl.merge_cells(merge)

            ws_xl["I7"].number_format = "0.0%"
            for m in ["A6:A7", "C6:E6", "F6:G6", "H5:I5"]:
                for r in ws_xl[m]:
                    for c in r: c.border = BORD

            row_idx = 8
            for cab in DAFTAR_CABANG:
                d = db_cabang[cab]
                style_cell(ws_xl, row_idx, 1, cab, F_B, align=AL_L, border=BORD)
                style_cell(ws_xl, row_idx, 2, d["omset_bulan_ini"], F_N, align=AL_R, num_fmt="#,##0.00", border=BORD)
                style_cell(ws_xl, row_idx, 3, d["omset_ytd"], F_B, align=AL_R, num_fmt="#,##0.00", border=BORD)
                style_cell(ws_xl, row_idx, 4, d["target_ytd"], F_N, align=AL_R, num_fmt="#,##0.00", border=BORD)
                style_cell(ws_xl, row_idx, 5, f"=IFERROR(C{row_idx}/D{row_idx}, 0)", F_B, align=AL_C, num_fmt="0.0%", border=BORD)
                style_cell(ws_xl, row_idx, 6, d["target_full"], F_N, align=AL_R, num_fmt="#,##0.00", border=BORD)
                style_cell(ws_xl, row_idx, 7, f"=IFERROR(C{row_idx}/F{row_idx}, 0)", F_B, align=AL_C, num_fmt="0.0%", border=BORD)
                style_cell(ws_xl, row_idx, 8, f"=E{row_idx}-1", F_B, align=AL_C, num_fmt="0.0%", border=BORD)
                style_cell(ws_xl, row_idx, 9, f"=G{row_idx}-$I$7", F_B, align=AL_C, num_fmt="0.0%", border=BORD)
                row_idx += 1

            style_cell(ws_xl, row_idx, 1, "TOTAL", F_B, FILL_TOT, AL_C, border=BORD)
            for col_idx_xl in [2, 3, 4, 6]:
                col_let = get_column_letter(col_idx_xl)
                style_cell(ws_xl, row_idx, col_idx_xl, f"=SUM({col_let}8:{col_let}{row_idx-1})", F_B, FILL_TOT, AL_R, num_fmt="#,##0.00", border=BORD)
            for c_idx, ref_col in [(5, 'D'), (7, 'F')]:
                style_cell(ws_xl, row_idx, c_idx, f"=IFERROR(C{row_idx}/{ref_col}{row_idx}, 0)", F_B, FILL_TOT, AL_C, num_fmt="0.0%", border=BORD)
            style_cell(ws_xl, row_idx, 8, f"=E{row_idx}-1", F_B, FILL_TOT, AL_C, num_fmt="0.0%", border=BORD)
            style_cell(ws_xl, row_idx, 9, f"=G{row_idx}-$I$7", F_B, FILL_TOT, AL_C, num_fmt="0.0%", border=BORD)

            # Simpan file Excel lokal (Sel 11b)
            summary_excel_name = f"Summary_Target_{nama_bulan[idx_bulan]}_{tahun_berjalan}.xlsx"
            summary_excel_path = os.path.join(output_dir, summary_excel_name)
            wb.save(summary_excel_path)
            print(f"✅ Sel 11b: Laporan lokal disimpan ke {summary_excel_path}")

            # Sinkronisasi ke Google Sheets (Sel 11)
            try: ws_gs = sh.worksheet("Summary Target")
            except Exception: ws_gs = sh.add_worksheet(title="Summary Target", rows=50, cols=15)

            existing_summary = ws_gs.get_all_values()
            existing_month = str(existing_summary[5][1]).strip() if len(existing_summary) >= 6 and len(existing_summary[5]) >= 2 else ""
            is_new_month = existing_month != col_str_bln_berjalan

            old_omset_bulan = {}
            if existing_summary:
                for row in existing_summary[7:]:
                    if len(row) >= 2 and row[0]:
                        old_omset_bulan[str(row[0]).strip().title()] = row[1]

            gsheets_data = []
            for row in ws_xl.iter_rows(min_row=1, max_row=row_idx, min_col=1, max_col=9):
                gsheets_data.append([c.value if c.value is not None else "" for c in row])

            uploaded_cabang = {str(cab).strip().title() for _, h in HASIL.items() for cab in h['metrik'].keys() if str(cab).strip().title() in db_cabang}

            # Permintaan merge/unmerge & format header: dipakai di KEDUA jalur (bulan sama & bulan baru),
            # supaya judul header (mis. 'Jan - Sep 2026') selalu ditulis ulang & tidak bisa 'bolong'.
            unmerge_requests = [
                {"unmergeCells": {"range": {"sheetId": ws_gs.id, "startRowIndex": 0, "endRowIndex": 1, "startColumnIndex": 5, "endColumnIndex": 7}}},
                {"unmergeCells": {"range": {"sheetId": ws_gs.id, "startRowIndex": 1, "endRowIndex": 4, "startColumnIndex": 4, "endColumnIndex": 5}}},
                {"unmergeCells": {"range": {"sheetId": ws_gs.id, "startRowIndex": 5, "endRowIndex": 7, "startColumnIndex": 0, "endColumnIndex": 1}}},
                {"unmergeCells": {"range": {"sheetId": ws_gs.id, "startRowIndex": 5, "endRowIndex": 6, "startColumnIndex": 2, "endColumnIndex": 5}}},
                {"unmergeCells": {"range": {"sheetId": ws_gs.id, "startRowIndex": 5, "endRowIndex": 6, "startColumnIndex": 5, "endColumnIndex": 7}}},
                {"unmergeCells": {"range": {"sheetId": ws_gs.id, "startRowIndex": 4, "endRowIndex": 5, "startColumnIndex": 7, "endColumnIndex": 9}}}
            ]
            format_requests = [
                {"mergeCells": {"range": {"sheetId": ws_gs.id, "startRowIndex": 0, "endRowIndex": 1, "startColumnIndex": 5, "endColumnIndex": 7}, "mergeType": "MERGE_ALL"}},
                {"mergeCells": {"range": {"sheetId": ws_gs.id, "startRowIndex": 1, "endRowIndex": 4, "startColumnIndex": 4, "endColumnIndex": 5}, "mergeType": "MERGE_ALL"}},
                {"mergeCells": {"range": {"sheetId": ws_gs.id, "startRowIndex": 5, "endRowIndex": 7, "startColumnIndex": 0, "endColumnIndex": 1}, "mergeType": "MERGE_ALL"}},
                {"mergeCells": {"range": {"sheetId": ws_gs.id, "startRowIndex": 5, "endRowIndex": 6, "startColumnIndex": 2, "endColumnIndex": 5}, "mergeType": "MERGE_ALL"}},
                {"mergeCells": {"range": {"sheetId": ws_gs.id, "startRowIndex": 5, "endRowIndex": 6, "startColumnIndex": 5, "endColumnIndex": 7}, "mergeType": "MERGE_ALL"}},
                {"mergeCells": {"range": {"sheetId": ws_gs.id, "startRowIndex": 4, "endRowIndex": 5, "startColumnIndex": 7, "endColumnIndex": 9}, "mergeType": "MERGE_ALL"}},
                {"repeatCell": {"range": {"sheetId": ws_gs.id, "startRowIndex": 5, "endRowIndex": 7, "startColumnIndex": 0, "endColumnIndex": 5}, "cell": {"userEnteredFormat": {"backgroundColor": {"red": 1.0, "green": 0.95, "blue": 0.8}, "textFormat": {"bold": True}, "horizontalAlignment": "CENTER", "borders": {"top": {"style": "SOLID"}, "bottom": {"style": "SOLID"}, "left": {"style": "SOLID"}, "right": {"style": "SOLID"}}}}, "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,borders)"}},
                {"repeatCell": {"range": {"sheetId": ws_gs.id, "startRowIndex": 5, "endRowIndex": 7, "startColumnIndex": 5, "endColumnIndex": 7}, "cell": {"userEnteredFormat": {"backgroundColor": {"red": 0.88, "green": 0.93, "blue": 0.85}, "textFormat": {"bold": True}, "horizontalAlignment": "CENTER", "borders": {"top": {"style": "SOLID"}, "bottom": {"style": "SOLID"}, "left": {"style": "SOLID"}, "right": {"style": "SOLID"}}}}, "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,borders)"}},
                {"repeatCell": {"range": {"sheetId": ws_gs.id, "startRowIndex": 4, "endRowIndex": 7, "startColumnIndex": 7, "endColumnIndex": 9}, "cell": {"userEnteredFormat": {"backgroundColor": {"red": 1.0, "green": 0.95, "blue": 0.8}, "textFormat": {"bold": True}, "horizontalAlignment": "CENTER", "borders": {"top": {"style": "SOLID"}, "bottom": {"style": "SOLID"}, "left": {"style": "SOLID"}, "right": {"style": "SOLID"}}}}, "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,borders)"}},
                {"repeatCell": {"range": {"sheetId": ws_gs.id, "startRowIndex": row_idx-1, "endRowIndex": row_idx, "startColumnIndex": 0, "endColumnIndex": 9}, "cell": {"userEnteredFormat": {"backgroundColor": {"red": 1.0, "green": 0.9, "blue": 0.6}, "textFormat": {"bold": True}, "horizontalAlignment": "RIGHT", "borders": {"top": {"style": "SOLID"}, "bottom": {"style": "SOLID"}, "left": {"style": "SOLID"}, "right": {"style": "SOLID"}}}}, "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,borders)"}},
                {"repeatCell": {"range": {"sheetId": ws_gs.id, "startRowIndex": 7, "endRowIndex": row_idx-1, "startColumnIndex": 0, "endColumnIndex": 9}, "cell": {"userEnteredFormat": {"borders": {"top": {"style": "SOLID"}, "bottom": {"style": "SOLID"}, "left": {"style": "SOLID"}, "right": {"style": "SOLID"}}}}, "fields": "userEnteredFormat(borders)"}},
                {"repeatCell": {"range": {"sheetId": ws_gs.id, "startRowIndex": 7, "endRowIndex": row_idx, "startColumnIndex": 1, "endColumnIndex": 4}, "cell": {"userEnteredFormat": {"numberFormat": {"type": "NUMBER", "pattern": "#,##0.00"}}}, "fields": "userEnteredFormat(numberFormat)"}},
                {"repeatCell": {"range": {"sheetId": ws_gs.id, "startRowIndex": 7, "endRowIndex": row_idx, "startColumnIndex": 5, "endColumnIndex": 6}, "cell": {"userEnteredFormat": {"numberFormat": {"type": "NUMBER", "pattern": "#,##0.00"}}}, "fields": "userEnteredFormat(numberFormat)"}},
                {"repeatCell": {"range": {"sheetId": ws_gs.id, "startRowIndex": 7, "endRowIndex": row_idx, "startColumnIndex": 4, "endColumnIndex": 5}, "cell": {"userEnteredFormat": {"numberFormat": {"type": "PERCENT", "pattern": "0.0%"}, "horizontalAlignment": "CENTER"}}, "fields": "userEnteredFormat(numberFormat,horizontalAlignment)"}},
                {"repeatCell": {"range": {"sheetId": ws_gs.id, "startRowIndex": 7, "endRowIndex": row_idx, "startColumnIndex": 6, "endColumnIndex": 9}, "cell": {"userEnteredFormat": {"numberFormat": {"type": "PERCENT", "pattern": "0.0%"}, "horizontalAlignment": "CENTER"}}, "fields": "userEnteredFormat(numberFormat,horizontalAlignment)"}}
            ]

            if not is_new_month:
                for i in range(7, len(gsheets_data) - 1):
                    cab_name = str(gsheets_data[i][0]).strip().title()
                    if cab_name and cab_name not in uploaded_cabang and cab_name in old_omset_bulan:
                        gsheets_data[i][1] = old_omset_bulan[cab_name]
                top_updates = [
                    {"range": "F1", "values": [[str_tgl_berjalan]]},
                    {"range": "E2", "values": [["Working Days"]]},
                    {"range": "F2:G4", "values": [[wd_data_excel[0][0], wd_data_excel[0][1]], [wd_data_excel[1][0], wd_data_excel[1][1]], [wd_data_excel[2][0], wd_data_excel[2][1]]]},
                    {"range": "A6", "values": [["Cabang"]]},
                    {"range": "B6", "values": [[col_str_bln_berjalan]]},
                    {"range": "C6", "values": [[f"Jan - {col_str_bln_berjalan}"]]},
                    {"range": "B7:E7", "values": [["Omset (M)", "Omset (M)", "Target (M)", "%"]]},
                    {"range": "F6", "values": [[f"TARGET {tahun_berjalan}"]]},
                    {"range": "F7:G7", "values": [["Rp (M)", "%"]]},
                    {"range": "H5", "values": [["Working Days"]]},
                    {"range": "H6:I6", "values": [[str_tgl_berjalan, f"31 Des {tahun_berjalan}"]]},
                    {"range": "H7:I7", "values": [["100%", target_persen_wd]]}
                ]
                ws_gs.batch_update(top_updates, value_input_option='USER_ENTERED')
                ws_gs.update(f"A8:I{row_idx}", gsheets_data[7:], value_input_option='USER_ENTERED')
                try: sh.batch_update({"requests": unmerge_requests})
                except Exception: pass
                sh.batch_update({"requests": format_requests})
                print("✅ Sel 11: Summary Target (bulan yang sama) diperbarui di Google Sheets.")
            else:
                if existing_summary:
                    try: sh.batch_update({"requests": unmerge_requests})
                    except Exception: pass
                ws_gs.clear()
                ws_gs.update(f'A1:I{row_idx}', gsheets_data, value_input_option='USER_ENTERED')
                sh.batch_update({"requests": format_requests})
                print("✅ Sel 11: Summary Target (bulan baru) diperbarui & diformat di Google Sheets.")

            sh.batch_update({"requests": [{"repeatCell": {
                "range": {"sheetId": ws_gs.id, "startRowIndex": 6, "endRowIndex": 7, "startColumnIndex": 8, "endColumnIndex": 9},
                "cell": {"userEnteredFormat": {"numberFormat": {"type": "PERCENT", "pattern": "0.0%"}}},
                "fields": "userEnteredFormat.numberFormat"}}]})

        # ==== SEL 11c: OMSET PER PRINCIPAL ====
        print("\nMemperbarui Omset per Principal (Sel 11c)...")
        opp_df = perbarui_omset_principal(HASIL, sh, MASTER, gc, tampil=True)

    return {
        "logs": log_stream.getvalue(),
        "summary_excel_path": summary_excel_path,
        "summary_excel_name": summary_excel_name,
        "opp_df": opp_df
    }