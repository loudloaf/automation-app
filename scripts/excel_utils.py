# scripts/excel_utils.py
"""
Normalisasi file "Excel" apa pun menjadi .xlsx asli.

Penyebab error "File is not a zip file": file berekstensi .xlsx tapi isinya BUKAN
format .xlsx (xlsx asli = arsip ZIP). Contoh yang sering terjadi pada hasil
export software akuntansi/ERP: .xls lama (OLE2), HTML, XML Spreadsheet 2003,
CSV/TSV yang cuma di-rename jadi .xlsx.
"""
import csv
import io
import os
import shutil
import subprocess
import tempfile
import zipfile
import xml.etree.ElementTree as ET

import pandas as pd

OLE_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"


def deteksi_format(path: str) -> str:
    """Kembalikan: 'xlsx' | 'ole' | 'html' | 'xml' | 'text' | 'pdf' | 'kosong'."""
    if os.path.getsize(path) == 0:
        return "kosong"
    with open(path, "rb") as f:
        head = f.read(4096)
    if head[:4] == b"PK\x03\x04":
        return "xlsx" if zipfile.is_zipfile(path) else "rusak"
    if head[:8] == OLE_MAGIC:
        return "ole"
    if head[:4] == b"%PDF":
        return "pdf"
    low = head.lower().lstrip(b"\xef\xbb\xbf\xff\xfe\xfe\xff \r\n\t")
    if b"<workbook" in low and b"urn:schemas-microsoft-com:office:spreadsheet" in low:
        return "xml"
    if low.startswith((b"<html", b"<!doctype", b"<table", b"<meta", b"<head", b"<body")) or b"<table" in low:
        return "html"
    return "text"


def _decode(raw: bytes) -> str:
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return raw.decode("utf-16")
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def _baca_xls_ole(path: str) -> dict:
    try:
        return pd.read_excel(path, sheet_name=None, header=None, engine="xlrd")
    except Exception as e_xlrd:
        # Fallback: LibreOffice (jika terpasang). Juga menangani .xls yang ekstensinya salah.
        soffice = shutil.which("soffice") or shutil.which("libreoffice")
        if soffice:
            with tempfile.TemporaryDirectory() as td:
                subprocess.run([soffice, "--headless", "--convert-to", "xlsx", "--outdir", td, path],
                               check=True, capture_output=True, timeout=180)
                out = os.path.join(td, os.path.splitext(os.path.basename(path))[0] + ".xlsx")
                return pd.read_excel(out, sheet_name=None, header=None, engine="openpyxl")
        raise RuntimeError(
            f"File berformat Excel lama (.xls) atau terkunci password dan gagal dibaca ({e_xlrd}). "
            "Jalankan: pip install xlrd  — atau buka di Excel lalu Save As .xlsx (tanpa password)."
        )


def _baca_html(path: str) -> dict:
    with open(path, "rb") as f:
        text = _decode(f.read())
    tables = pd.read_html(io.StringIO(text), header=None)
    if not tables:
        raise RuntimeError("File HTML tidak berisi tabel.")
    hasil = {}
    for i, t in enumerate(tables):
        if not isinstance(t.columns, pd.RangeIndex):  # baris <th> dijadikan baris pertama
            kolom = [" ".join(map(str, c)) if isinstance(c, tuple) else c for c in t.columns]
            t = pd.concat([pd.DataFrame([kolom]), t.set_axis(range(t.shape[1]), axis=1)], ignore_index=True)
        hasil[f"Sheet{i+1}"] = t
    return hasil


def _baca_xml_2003(path: str) -> dict:
    ns = {"ss": "urn:schemas-microsoft-com:office:spreadsheet"}
    key = "{urn:schemas-microsoft-com:office:spreadsheet}"
    root = ET.parse(path).getroot()
    out = {}
    for i, ws in enumerate(root.iterfind("ss:Worksheet", ns)):
        name = ws.get(key + "Name") or f"Sheet{i+1}"
        rows = []
        for row in ws.iterfind(".//ss:Row", ns):
            vals, col = [], 0
            for cell in row.iterfind("ss:Cell", ns):
                idx = cell.get(key + "Index")
                if idx:
                    while col < int(idx) - 1:
                        vals.append(None); col += 1
                d = cell.find("ss:Data", ns)
                v = d.text if d is not None else None
                if d is not None and d.get(key + "Type") == "Number" and v is not None:
                    try:
                        v = float(v)
                    except ValueError:
                        pass
                vals.append(v); col += 1
            rows.append(vals)
        out[name[:31]] = pd.DataFrame(rows)
    return out


def _baca_teks(path: str) -> dict:
    with open(path, "rb") as f:
        text = _decode(f.read())
    sample = text[:20000]
    try:
        delim = csv.Sniffer().sniff(sample, delimiters=",;\t|").delimiter
    except csv.Error:
        delim = "\t" if sample.count("\t") > sample.count(",") else ","
    df = pd.read_csv(io.StringIO(text), sep=delim, header=None, dtype=object, engine="python")
    return {"Sheet1": df}


def pastikan_xlsx(path: str) -> str:
    """
    Pastikan file di `path` adalah .xlsx asli. Jika bukan, konversi IN-PLACE
    (nama & lokasi file tetap sama, sehingga kode lain tidak perlu diubah).
    Mengembalikan format asli yang terdeteksi.
    """
    fmt = deteksi_format(path)
    nama = os.path.basename(path)
    if fmt == "xlsx":
        return fmt
    if fmt == "kosong":
        raise ValueError(f"File '{nama}' kosong (0 byte). Upload ulang / export ulang file tersebut.")
    if fmt == "rusak":
        raise ValueError(f"File '{nama}' rusak atau terpotong saat upload (header ZIP ada tapi arsip tidak lengkap).")
    if fmt == "pdf":
        raise ValueError(f"File '{nama}' sebenarnya PDF, bukan Excel.")

    try:
        sheets = {
            "ole": _baca_xls_ole, "html": _baca_html,
            "xml": _baca_xml_2003, "text": _baca_teks,
        }[fmt](path)
    except Exception as e:
        raise ValueError(f"File '{nama}' terdeteksi berformat '{fmt}' (bukan .xlsx asli) dan gagal dikonversi: {e}") from e

    tmp = path + ".tmp.xlsx"
    with pd.ExcelWriter(tmp, engine="openpyxl") as w:
        for nm, df in sheets.items():
            df.to_excel(w, sheet_name=str(nm)[:31], header=False, index=False)
    import gc, time
    gc.collect()
    for attempt in range(5):
        try:
            os.replace(tmp, path)
            break
        except PermissionError:
            if attempt == 4:
                with open(tmp, "rb") as src_f, open(path, "wb") as dst_f:
                    shutil.copyfileobj(src_f, dst_f)
                try:
                    os.remove(tmp)
                except OSError:
                    pass
            else:
                time.sleep(0.15)
    return fmt