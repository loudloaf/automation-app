# core/engine.py — "tenaga tambahan" untuk data besar: baca Excel cepat, cache Parquet, SQL DuckDB.
# Semua opsional: bila library belum terpasang, otomatis kembali ke pandas biasa.
import hashlib, os
import pandas as pd

CACHE_DIR = os.path.abspath("cache"); os.makedirs(CACHE_DIR, exist_ok=True)


def baca_excel_cepat(path, **kw):
    """pandas + python-calamine (jauh lebih cepat dari openpyxl untuk file puluhan MB)."""
    try: return pd.read_excel(path, engine="calamine", **kw)
    except ImportError: return pd.read_excel(path, **kw)


def kunci_file(paths):
    h = hashlib.md5()
    for p in sorted(paths): h.update(f"{os.path.basename(p)}|{os.path.getsize(p)}".encode())
    return h.hexdigest()[:16]


def simpan_cache(df, kunci):
    df.to_parquet(os.path.join(CACHE_DIR, f"{kunci}.parquet"), index=False)


def muat_cache(kunci):
    p = os.path.join(CACHE_DIR, f"{kunci}.parquet")
    return pd.read_parquet(p) if os.path.exists(p) else None


def sql(query, **tabel):
    """Query SQL langsung pada DataFrame/Parquet, mis. sql('select Cabang, sum(Net) from d group by 1', d=df)."""
    import duckdb
    con = duckdb.connect()
    for nama, t in tabel.items(): con.register(nama, t)
    return con.execute(query).df()
